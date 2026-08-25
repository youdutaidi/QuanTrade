"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import factorsJson from "./data/factors.json";
import backtestJson from "./data/backtest.json";
import factorBacktestJson from "./data/factor_backtest.json";
import minuteSystemJson from "./data/minute_system.json";

type Factor = {
  id: string;
  name: string;
  authors: string;
  year: number | null;
  journal: string;
  signalType: string;
  dataType: string;
  economicGroup: string;
  economicRaw: string;
  formula: string;
  definition: string;
  evidence: string;
  grade: string;
  ahStatus: string;
  ahBoundary: string;
};

type Point = { date: string; value: number };
type Strategy = (typeof backtestJson.strategies)[number];

const factors = factorsJson as Factor[];
const backtest = backtestJson;
const factorBacktest = factorBacktestJson;
const minuteSystem = minuteSystemJson;

const strategyAtlas = [
  ["截面动量", "买强、避弱", "趋势拥挤后急反转", "月度→周度稳定性"],
  ["短期反转", "流动性冲击修复", "跌停与坏消息延续", "排除事件日重测"],
  ["价值", "价格相对基本面偏低", "价值陷阱与口径滞后", "点时财务+行业中性"],
  ["质量", "盈利与现金流更耐久", "估值吞噬未来回报", "质量×估值二维排序"],
  ["低风险", "低波/低 beta 异常", "牛市显著落后", "加入市场状态条件"],
  ["事件驱动", "公告后的缓慢定价", "时间戳错一日即未来函数", "首次公告快照回放"],
  ["资金流", "订单失衡与持仓变化", "披露口径变更", "字段可用日审计"],
  ["行业轮动", "景气与相对强弱切换", "单一主题追高", "跨周期状态转移"],
  ["统计套利", "共整合/残差回归", "关系结构断裂", "滚动参数与断点检验"],
  ["机器学习", "非线性组合多特征", "高维过拟合", "嵌套走步验证"],
  ["组合配置", "风险预算与相关性", "相关性危机时上升", "压力相关矩阵"],
  ["尾部风控", "趋势过滤与现金状态", "频繁假信号", "危机/震荡双样本"],
];

const sources = [
  ["324 个因子定义", "Federal Reserve · Open Source Cross-Sectional Asset Pricing", "https://www.federalreserve.gov/econres/feds/open-source-cross-sectional-asset-pricing.htm"],
  ["全球 153 因子 / 93 市场", "Jensen, Kelly & Pedersen · Replication Crisis in Finance", "https://www.nber.org/papers/w28432"],
  ["A 股 469 个异常变量", "Replicating and Digesting Anomalies in the Chinese A-share Market", "https://ira.lib.polyu.edu.hk/bitstream/10397/115240/1/Li_Replicating_Digesting_Anomalies.pdf"],
  ["A 股交易费用口径", "上海证券交易所 · 股票投资与收费", "https://one.sse.com.cn/onething/gptz/"],
  ["港股交易费用口径", "HKEX · Securities transaction fees", "https://www.hkex.com.hk/Services/Rules-and-Forms-and-Fees/Fees/Securities-%28Hong-Kong%29/Trading/Transaction?sc_lang=en"],
  ["成份股快照", "中证指数 · CSI 300 / CSI 500", "https://www.csindex.com.cn/zh-CN/indices/index-detail/000300"],
  ["A 股免费 5–60 分钟", "BaoStock · 分钟 K 线下载方案", "https://github.com/zxygithub/baostock/blob/master/docs/data_download_plan.md"],
  ["A/H 历史分钟额度", "Futu OpenAPI · 历史 K 线权限与额度", "https://openapi.futunn.com/futu-api-doc/intro/authority.html"],
];

function pct(value: number, digits = 1) {
  const sign = value > 0 ? "+" : "";
  return `${sign}${(value * 100).toFixed(digits)}%`;
}

function number(value: number, digits = 2) {
  return value.toFixed(digits);
}

function familyName(name: string) {
  return ({
    momentum: "截面动量",
    risk_adjusted_momentum: "风险调整动量",
    breakout: "突破",
    reversal_in_trend: "趋势内反转",
  } as Record<string, string>)[name] ?? name;
}

function EvidenceBadge({ grade }: { grade: string }) {
  return <span className={`grade grade-${grade.toLowerCase()}`}>证据 {grade}</span>;
}

function EquityChart({ strategy }: { strategy: Strategy }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const holder = canvas.parentElement;
    if (!holder) return;

    const draw = () => {
      const dpr = window.devicePixelRatio || 1;
      const width = holder.clientWidth;
      const height = 330;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.scale(dpr, dpr);
      ctx.clearRect(0, 0, width, height);

      const padding = { left: 8, right: 10, top: 22, bottom: 28 };
      const plotW = width - padding.left - padding.right;
      const plotH = height - padding.top - padding.bottom;
      const benchmarkByDate = new Map(backtest.benchmark.curve.map((point) => [point.date, point.value]));
      const series = strategy.curve.map((point) => ({ ...point, benchmark: benchmarkByDate.get(point.date) ?? 1 }));
      const values = series.flatMap((point) => [point.value, point.benchmark]);
      const min = Math.min(...values, 0.75);
      const max = Math.max(...values, 1.15);
      const x = (index: number) => padding.left + (index / Math.max(series.length - 1, 1)) * plotW;
      const y = (value: number) => padding.top + (1 - (value - min) / (max - min)) * plotH;

      ctx.strokeStyle = "rgba(231, 237, 228, .10)";
      ctx.lineWidth = 1;
      ctx.setLineDash([3, 6]);
      for (let i = 0; i <= 4; i += 1) {
        const gy = padding.top + (i / 4) * plotH;
        ctx.beginPath(); ctx.moveTo(padding.left, gy); ctx.lineTo(width - padding.right, gy); ctx.stroke();
      }
      ctx.setLineDash([]);

      const drawLine = (key: "value" | "benchmark", color: string, lineWidth: number) => {
        ctx.beginPath();
        series.forEach((point, index) => {
          const py = y(point[key]);
          if (index === 0) ctx.moveTo(x(index), py); else ctx.lineTo(x(index), py);
        });
        ctx.strokeStyle = color;
        ctx.lineWidth = lineWidth;
        ctx.lineJoin = "round";
        ctx.stroke();
      };

      const gradient = ctx.createLinearGradient(0, padding.top, 0, height - padding.bottom);
      gradient.addColorStop(0, "rgba(184, 242, 59, .24)");
      gradient.addColorStop(1, "rgba(184, 242, 59, 0)");
      ctx.beginPath();
      series.forEach((point, index) => {
        if (index === 0) ctx.moveTo(x(index), y(point.value)); else ctx.lineTo(x(index), y(point.value));
      });
      ctx.lineTo(width - padding.right, height - padding.bottom);
      ctx.lineTo(padding.left, height - padding.bottom);
      ctx.closePath();
      ctx.fillStyle = gradient;
      ctx.fill();

      drawLine("benchmark", "rgba(223, 231, 226, .42)", 1.4);
      drawLine("value", "#b8f23b", 2.4);

      const splitIndex = series.findIndex((point) => point.date >= backtest.window.designEnd);
      if (splitIndex > 0) {
        ctx.strokeStyle = "rgba(255, 128, 95, .75)";
        ctx.setLineDash([4, 5]);
        ctx.beginPath(); ctx.moveTo(x(splitIndex), padding.top); ctx.lineTo(x(splitIndex), height - padding.bottom); ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = "rgba(255, 150, 120, .9)";
        ctx.font = "10px monospace";
        ctx.fillText("DESIGN / SECOND HALF", Math.min(x(splitIndex) + 7, width - 150), padding.top + 3);
      }

      ctx.fillStyle = "rgba(166, 180, 171, .8)";
      ctx.font = "10px monospace";
      ctx.fillText(series[0]?.date.slice(0, 7) ?? "", padding.left, height - 8);
      const endLabel = series.at(-1)?.date.slice(0, 7) ?? "";
      ctx.fillText(endLabel, width - padding.right - 45, height - 8);
    };

    draw();
    const observer = new ResizeObserver(draw);
    observer.observe(holder);
    return () => observer.disconnect();
  }, [strategy]);

  return <canvas ref={canvasRef} aria-label={`${strategy.role}净值曲线，与上证综指对比`} />;
}

export default function Home() {
  const [strategyIndex, setStrategyIndex] = useState(2);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("全部");
  const [grade, setGrade] = useState("全部");
  const [selectedFactor, setSelectedFactor] = useState<string | null>(null);
  const strategy = backtest.strategies[strategyIndex];

  const categoryCounts = useMemo(() => {
    const counts = new Map<string, number>();
    factors.forEach((factor) => counts.set(factor.economicGroup, (counts.get(factor.economicGroup) ?? 0) + 1));
    return [...counts.entries()].sort((a, b) => b[1] - a[1]);
  }, []);

  const filteredFactors = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return factors.filter((factor) => {
      const matchesQuery = !normalized || [factor.id, factor.name, factor.authors, factor.economicGroup, factor.dataType].join(" ").toLowerCase().includes(normalized);
      const matchesCategory = category === "全部" || factor.economicGroup === category;
      const matchesGrade = grade === "全部" || factor.grade === grade;
      return matchesQuery && matchesCategory && matchesGrade;
    });
  }, [query, category, grade]);

  const activeFactor = selectedFactor ? factors.find((factor) => factor.id === selectedFactor) : null;
  const predictors = factors.filter((factor) => factor.signalType === "Predictor").length;
  const directFactors = factors.filter((factor) => factor.ahStatus === "可直接首测").length;
  const strongEvidence = factors.filter((factor) => factor.grade === "A" || factor.grade === "B").length;
  const failedGates = backtest.gates.filter((gate) => gate.status === "fail").length;

  return (
    <main id="top">
      <nav className="nav-shell">
        <a className="brand" href="#top"><span className="brand-mark">Q</span><span>Q-FORGE</span></a>
        <div className="nav-links">
          <a href="#backtest">回测</a><a href="#engine">因子引擎</a><a href="#minute">分钟交易</a><a href="#audit">风险审计</a>
        </div>
        <div className="status-chip"><span /> DRAFT · 不接实盘</div>
      </nav>

      <header className="hero">
        <div className="hero-copy">
          <div className="eyebrow"><span>AH-01</span> A 股首轮候选 · 截至 {backtest.asOf}</div>
          <h1>先证明它不是幻觉，<br /><em>再追求翻倍。</em></h1>
          <p className="hero-lead">INTP 拆机制、找反例，INTJ 冻结目标、门槛与止损。我们筛过 {backtest.testedStrategies.toLocaleString()} 组价格策略，找到超过 100% 的历史候选；但幸存者偏差与实盘门禁仍未通过。</p>
          <div className="hero-actions">
            <a className="button primary" href="#backtest">查看真实回测 <span>↘</span></a>
            <a className="button ghost" href="#audit">为什么还不能实盘</a>
          </div>
        </div>
        <aside className="signal-card" aria-label="首轮候选结果">
          <div className="card-topline"><span>CANDIDATE / NOT VALIDATED</span><span className="candidate-dot">HIT</span></div>
          <div className="target-row"><strong>{pct(strategy.metrics.totalReturn)}</strong><span>一年历史<br />净收益候选</span></div>
          <div className="mini-summary">
            <div><small>目标</small><b>+100.0%</b></div><div><small>最大回撤</small><b className="loss">{pct(strategy.metrics.maxDrawdown)}</b></div>
            <div><small>Sharpe</small><b>{number(strategy.metrics.sharpe)}</b></div><div><small>状态</small><b className="warn">DRAFT</b></div>
          </div>
          <div className="verdict-line"><span>{failedGates} 个硬门槛失败</span><p>收益目标命中 ≠ 策略可信</p></div>
        </aside>
      </header>

      <section className="metrics-strip">
        <div><small>因子档案</small><strong>{factors.length}</strong><p>原始定义与复现证据</p></div>
        <div><small>明确预测因子</small><strong>{predictors}</strong><p>其余含 placebo 与 drop</p></div>
        <div><small>A/B 证据等级</small><strong>{strongEvidence}</strong><p>仍非 A/H 股本土验证</p></div>
        <div><small>可直接首测</small><strong>{directFactors}</strong><p>价格与交易类数据</p></div>
      </section>

      <section className="truth-banner">
        <span className="truth-code">INTP / COUNTEREXAMPLE</span>
        <strong>最强反例：回测使用 2026-08-24 的当前 CSI 800 成份股倒推历史。</strong>
        <p>这会漏掉已退市或被调出的失败者，因此 +143.5% 只能是“值得继续查”的候选，不能是“去年真的能做到”的结论。</p>
      </section>

      <section className="section-shell backtest-section" id="backtest">
        <div className="section-heading split-heading">
          <div><span className="section-kicker">01 / BACKTEST LAB</span><h2>三个答案，<br />三种证据身份。</h2></div>
          <p>同一条曲线必须交代它是全窗搜索、设计窗选择，还是跨两段都为正。我们不把搜索结果伪装成样本外结果。</p>
        </div>

        <div className="strategy-tabs" role="tablist" aria-label="回测候选">
          {backtest.strategies.map((item, index) => (
            <button key={item.label} className={strategyIndex === index ? "active" : ""} onClick={() => setStrategyIndex(index)} role="tab" aria-selected={strategyIndex === index}>
              <span>0{index + 1}</span><b>{item.role}</b><em>{pct(item.metrics.totalReturn)}</em>
            </button>
          ))}
        </div>

        <div className="chart-panel">
          <div className="chart-header">
            <div><span className="label">SELECTED MODEL</span><h3>{familyName(strategy.parameters.family)} · {strategy.parameters.lookback} 日回看 · Top {strategy.parameters.topN}</h3></div>
            <div className="chart-legend"><span className="candidate-line">候选</span><span className="benchmark-line">上证综指</span></div>
          </div>
          <div className="chart-canvas"><EquityChart strategy={strategy} /></div>
          <div className="chart-metrics">
            <div><small>全窗净收益</small><b>{pct(strategy.metrics.totalReturn)}</b></div>
            <div><small>设计窗</small><b>{pct(strategy.metrics.designReturn)}</b></div>
            <div><small>后半窗</small><b>{pct(strategy.metrics.holdoutReturn)}</b></div>
            <div><small>最大回撤</small><b className="loss">{pct(strategy.metrics.maxDrawdown)}</b></div>
            <div><small>总换手</small><b>{number(strategy.metrics.turnover, 1)}×</b></div>
            <div><small>调仓次数</small><b>{strategy.metrics.rebalanceCount}</b></div>
          </div>
        </div>

        <div className="result-table-wrap">
          <table className="result-table">
            <thead><tr><th>证据身份</th><th>全窗</th><th>设计窗</th><th>后半窗</th><th>最大回撤</th><th>判断</th></tr></thead>
            <tbody>{backtest.strategies.map((item, index) => (
              <tr key={item.label} onClick={() => setStrategyIndex(index)} className={strategyIndex === index ? "active" : ""}>
                <td><b>{item.role}</b><small>{familyName(item.parameters.family)} / Top {item.parameters.topN}</small></td>
                <td>{pct(item.metrics.totalReturn)}</td><td>{pct(item.metrics.designReturn)}</td><td className={item.metrics.holdoutReturn < 0 ? "loss" : ""}>{pct(item.metrics.holdoutReturn)}</td><td className="loss">{pct(item.metrics.maxDrawdown)}</td>
                <td><span className={`verdict-pill verdict-${index}`}>{index === 0 ? "上界" : index === 1 ? "过拟合警报" : "继续验证"}</span></td>
              </tr>
            ))}</tbody>
          </table>
        </div>

        <div className="trade-ledger">
          <div className="trade-intro"><span className="section-kicker">RECENT ALLOCATIONS</span><h3>这条曲线到底买过什么？</h3><p>展示最近调仓后的目标持仓；空列表表示 200 日市场过滤器切换为现金。</p></div>
          <div className="trade-list">{strategy.trades.slice(-4).reverse().map((trade) => (
            <div className="trade-row" key={trade.date}><time>{trade.date}</time><div>{trade.holdings.length ? trade.holdings.map((holding) => <span key={holding.symbol}>{holding.name}<small>{Math.round(holding.weight * 100)}%</small></span>) : <span className="cash">现金 100%</span>}</div></div>
          ))}</div>
        </div>
      </section>

      <section className="section-shell engine-section" id="engine">
        <div className="section-heading split-heading">
          <div><span className="section-kicker">02 / LOCAL FACTOR ENGINE</span><h2>不是结果截图，<br />是可运行代码库。</h2></div>
          <p>统一完成数据校验、因子计算、横截面清洗、IC 与五分组、Top 组合、交易摩擦、设计窗/后半窗和本地报告；新增因子只需注册一个纯函数。</p>
        </div>

        <div className="engine-overview">
          <div className="pipeline-map">
            {[["01", "DATA", "长表 OHLCV / 成份区间"], ["02", "FACTOR", "纯函数注册表 / 滞后信号"], ["03", "CROSS-SECTION", "流动性 / MAD / Z-score"], ["04", "EVIDENCE", "IC / 分层 / 组合净值"], ["05", "REPORT", "JSON / CSV / HTML"]].map((item) => (
              <div key={item[0]}><span>{item[0]}</span><b>{item[1]}</b><p>{item[2]}</p></div>
            ))}
          </div>
          <div className="run-card">
            <div><span>LOCAL RUN</span><em>Python 3.11+</em></div>
            <pre><code>{`python3 -m venv .venv
.venv/bin/pip install -e '.[test,data]'
.venv/bin/qforge demo
.venv/bin/qforge run \\
  --config configs/price_factors.json`}</code></pre>
            <p>演示命令不联网；真实命令读取本地 Parquet，并生成独立 HTML、JSON 与 CSV。</p>
          </div>
        </div>

        <div className="engine-stats">
          <div><small>可执行因子/复合</small><strong>{factorBacktest.factorCount}</strong><p>10 个 OHLCV + 1 个等权复合</p></div>
          <div><small>真实股票</small><strong>{factorBacktest.dataAudit.symbols}</strong><p>{factorBacktest.dataAudit.dates} 个交易日数据</p></div>
          <div><small>语义测试</small><strong>7/7</strong><p>含未来数据扰动反证</p></div>
          <div><small>报告格式</small><strong>3</strong><p>HTML · JSON · CSV</p></div>
        </div>

        <div className="engine-table-wrap">
          <div className="engine-table-head"><div><span className="section-kicker">REAL RUN / {factorBacktest.experimentId}</span><h3>当前可计算因子结果</h3></div><p>按组合净收益排序；Mean IC 与组合收益可能因市场状态过滤、持仓尾部和成本产生分歧。</p></div>
          <table className="result-table engine-table">
            <thead><tr><th>因子</th><th>Mean IC</th><th>ICIR</th><th>组合净收益</th><th>最大回撤</th><th>Sharpe</th></tr></thead>
            <tbody>{factorBacktest.ranking.slice(0, 7).map((item) => (
              <tr key={item.factor}><td><b>{item.factor}</b></td><td className={item.meanIC < 0 ? "loss" : ""}>{number(item.meanIC, 3)}</td><td className={item.icIR < 0 ? "loss" : ""}>{number(item.icIR, 2)}</td><td>{pct(item.totalReturn)}</td><td className="loss">{pct(item.maxDrawdown)}</td><td>{number(item.sharpe)}</td></tr>
            ))}</tbody>
          </table>
          <div className="engine-verdict"><span>ENGINE VERDICT</span><b>代码闭环已通过；研究证据仍是 DRAFT。</b><p>当前最佳通用因子组合收益为 {pct(factorBacktest.ranking[0].totalReturn)}，低于专项参数搜索的 +143.5%；这正是防止把“搜参上界”误当成“稳定因子能力”的必要分离。</p></div>
        </div>
      </section>

      <section className="section-shell minute-section" id="minute">
        <div className="section-heading split-heading">
          <div><span className="section-kicker">03 / MINUTE DATA & PAPER BROKER</span><h2>数据链路已打通，<br />第一条策略被证伪。</h2></div>
          <p>BaoStock 5 分钟数据已经真实落入本机 SQLite；订单只在本地账本中模拟撮合。负收益不是系统故障，而是“每日追逐临近收盘强势股”没有覆盖换手与摩擦成本。</p>
        </div>

        <div className="minute-status-grid">
          <div><small>5分钟 K 线</small><strong>{minuteSystem.database.barCount.toLocaleString()}</strong><p>{minuteSystem.database.tradeDays} 个交易日</p></div>
          <div><small>固定试点股票</small><strong>{minuteSystem.database.symbolCount}</strong><p>沪深主板、创业板、科创板</p></div>
          <div><small>本地数据库</small><strong>{number(minuteSystem.database.databaseBytes / 1024 / 1024, 1)} MB</strong><p>SQLite · WAL · 幂等写入</p></div>
          <div><small>模拟订单</small><strong>{minuteSystem.ledger.orderCount.toLocaleString()}</strong><p>{minuteSystem.ledger.fillCount.toLocaleString()} 笔成交</p></div>
        </div>

        <div className="minute-pipeline">
          {[["01", "BAOSTOCK", "匿名下载 5m OHLCV"], ["02", "SQLITE", "主键去重与下载审计"], ["03", "SIGNAL", "14:50 完成 K 线"], ["04", "PAPER BROKER", "14:55 次根开盘撮合"], ["05", "LEDGER", "订单·成交·持仓·净值"]].map((item) => (
            <div key={item[0]}><span>{item[0]}</span><b>{item[1]}</b><p>{item[2]}</p></div>
          ))}
        </div>

        <div className="minute-result-grid">
          <article className="minute-verdict-card">
            <div><span>CANDIDATE EVIDENCE</span><em>FALSIFIED 01</em></div>
            <strong>{pct(minuteSystem.metrics.totalReturn)}</strong>
            <h3>Close Strength · Top 3</h3>
            <p>每天 14:50 用已完成 K 线计算当日收益与 VWAP 强度，14:55 模拟成交；遵守 T+1 和 100 股整数手。</p>
            <dl><div><dt>最大回撤</dt><dd>{pct(minuteSystem.metrics.maxDrawdown)}</dd></div><div><dt>Sharpe</dt><dd>{number(minuteSystem.metrics.sharpe)}</dd></div><div><dt>试点等权</dt><dd>{pct(minuteSystem.benchmark.totalReturn)}</dd></div><div><dt>显式成本</dt><dd>¥{Math.round(minuteSystem.ledger.explicitCosts).toLocaleString()}</dd></div></dl>
          </article>
          <div className="minute-command-card">
            <div><span>LOCAL COMMANDS</span><em>不连接券商</em></div>
            <pre><code>{`.venv/bin/qforge minute init \\
  --config configs/minute_5m.json
.venv/bin/qforge minute download \\
  --config configs/minute_5m.json
.venv/bin/qforge minute backtest \\
  --config configs/minute_5m.json
.venv/bin/qforge minute status \\
  --config configs/minute_5m.json`}</code></pre>
            <ul>{minuteSystem.rules.map((rule) => <li key={rule}>{rule}</li>)}</ul>
          </div>
        </div>

        <div className="minute-ledger">
          <div className="engine-table-head"><div><span className="section-kicker">LOCAL ORDER LEDGER</span><h3>最近模拟订单</h3></div><p>数据库保留请求数量、成交数量、拒单原因和费用；这些记录不是券商委托。</p></div>
          <div className="result-table-wrap"><table className="result-table"><thead><tr><th>时间</th><th>证券</th><th>方向</th><th>请求</th><th>成交</th><th>状态</th></tr></thead><tbody>{minuteSystem.recentOrders.slice(0, 8).map((order, index) => (
            <tr key={`${order.bar_time}-${order.symbol}-${index}`}><td><b>{order.bar_time}</b></td><td>{order.symbol}</td><td className={order.side === "SELL" ? "loss" : ""}>{order.side}</td><td>{order.requested_qty}</td><td>{order.filled_qty}</td><td>{order.status}</td></tr>
          ))}</tbody></table></div>
        </div>

        <div className="minute-gates">{minuteSystem.gates.map((gate) => (
          <article key={gate.name} className={`gate-${gate.status}`}><span>{gate.status.toUpperCase()}</span><h3>{gate.name}</h3><p>{gate.note}</p></article>
        ))}</div>
      </section>

      <section className="section-shell factor-section" id="factors">
        <div className="section-heading split-heading">
          <div><span className="section-kicker">04 / FACTOR LIBRARY</span><h2>{factors.length} 个因子，<br />先分清数据债。</h2></div>
          <p>这里不是一张“都能赚钱”的清单。每个条目保留原始证据等级、数据类型，以及迁移到 A/H 股时最先遇到的口径障碍。</p>
        </div>

        <div className="factor-controls">
          <label className="search-box"><span>⌕</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索因子、作者、缩写或数据类型" aria-label="搜索因子" /></label>
          <div className="grade-filter" aria-label="证据等级筛选">{["全部", "A", "B", "C", "D"].map((item) => <button key={item} className={grade === item ? "active" : ""} onClick={() => setGrade(item)}>{item}</button>)}</div>
        </div>
        <div className="category-rail">
          <button className={category === "全部" ? "active" : ""} onClick={() => setCategory("全部")}>全部 <span>{factors.length}</span></button>
          {categoryCounts.map(([item, count]) => <button key={item} className={category === item ? "active" : ""} onClick={() => setCategory(item)}>{item} <span>{count}</span></button>)}
        </div>

        <div className="factor-result-line"><span>显示 {Math.min(filteredFactors.length, 12)} / {filteredFactors.length}</span><p>点击卡片查看定义与 A/H 迁移边界</p></div>
        <div className="factor-grid">
          {filteredFactors.slice(0, 12).map((factor) => (
            <button key={`${factor.id}-${factor.authors}`} className={`factor-card ${selectedFactor === factor.id ? "selected" : ""}`} onClick={() => setSelectedFactor(selectedFactor === factor.id ? null : factor.id)}>
              <div className="factor-top"><EvidenceBadge grade={factor.grade} /><span>{factor.ahStatus}</span></div>
              <h3>{factor.name}</h3><code>{factor.id}</code>
              <div className="factor-meta"><span>{factor.economicGroup}</span><span>{factor.dataType}</span></div>
              <p>{factor.evidence || factor.definition || "原始文档未给出简短证据摘要。"}</p>
              <footer><span>{factor.authors}</span><i>↗</i></footer>
            </button>
          ))}
        </div>
        {activeFactor && <aside className="factor-detail">
          <div><EvidenceBadge grade={activeFactor.grade} /><span className="detail-id">{activeFactor.id}</span></div><button onClick={() => setSelectedFactor(null)} aria-label="关闭因子详情">×</button>
          <h3>{activeFactor.name}</h3><p className="definition">{activeFactor.definition || "暂无详细定义。"}</p>
          <dl><div><dt>A/H 状态</dt><dd>{activeFactor.ahStatus}</dd></div><div><dt>迁移边界</dt><dd>{activeFactor.ahBoundary}</dd></div><div><dt>原始作者</dt><dd>{activeFactor.authors}{activeFactor.year ? ` · ${activeFactor.year}` : ""}</dd></div><div><dt>数据</dt><dd>{activeFactor.dataType}</dd></div></dl>
        </aside>}
      </section>

      <section className="section-shell strategy-section" id="strategies">
        <div className="section-heading split-heading">
          <div><span className="section-kicker">05 / STRATEGY ATLAS</span><h2>12 条母路径，<br />每条都有死法。</h2></div>
          <p>INTP 不问“它看起来聪明吗”，先问“什么情形会让它失效”；INTJ 则把最便宜的反证实验放进下一轮队列。</p>
        </div>
        <div className="atlas-grid">{strategyAtlas.map((item, index) => (
          <article key={item[0]}><span>{String(index + 1).padStart(2, "0")}</span><h3>{item[0]}</h3><dl><div><dt>机制</dt><dd>{item[1]}</dd></div><div><dt>主要死法</dt><dd>{item[2]}</dd></div><div><dt>最便宜反证</dt><dd>{item[3]}</dd></div></dl></article>
        ))}</div>
      </section>

      <section className="section-shell audit-section" id="audit">
        <div className="section-heading split-heading">
          <div><span className="section-kicker">06 / EVIDENCE GATES</span><h2>收益达标，<br />可信度不达标。</h2></div>
          <div className="audit-verdict"><span>VERDICT</span><b>DRAFT</b><p>{failedGates} fail · {backtest.gates.length - failedGates} partial · 0 pass</p></div>
        </div>
        <div className="gate-grid">{backtest.gates.map((gate, index) => (
          <article key={gate.name} className={`gate gate-${gate.status}`}><div><span>G{index + 1}</span><em>{gate.status.toUpperCase()}</em></div><h3>{gate.name}</h3><p>{gate.note}</p></article>
        ))}</div>
        <div className="research-contract">
          <div><span className="section-kicker">FROZEN CONTRACT / AH-01</span><h3>首轮口径</h3></div>
          <dl>
            <div><dt>窗口</dt><dd>{backtest.window.start} → {backtest.window.end}</dd></div>
            <div><dt>股票池</dt><dd>{backtest.universe.name} · {backtest.universe.count} 只</dd></div>
            <div><dt>成交</dt><dd>{backtest.costModel.execution}</dd></div>
            <div><dt>成本</dt><dd>买入 {(backtest.costModel.buy * 10000).toFixed(0)} bps / 卖出 {(backtest.costModel.sell * 10000).toFixed(0)} bps</dd></div>
            <div><dt>限制</dt><dd>长仓、日线、无杠杆；成交额后 30% 剔除</dd></div>
            <div><dt>硬禁令</dt><dd>风险承受参数未填前，不输出无条件实盘买卖表</dd></div>
          </dl>
        </div>
        <div className="minute-roadmap">
          <div><span className="section-kicker">MINUTE DATA ROUTE</span><h3>第一阶段已经落地。</h3><p>116,160 根真实 5 分钟 K 线已入本地库；第一条策略失败，下一轮应先降低换手，再扩充股票池。</p></div>
          <ol><li><span>01</span><b>日线发现</b><p>CSI 800 全市场筛候选</p></li><li><span>02</span><b>BaoStock 5m</b><p>已接入 · 10 股一年</p></li><li><span>03</span><b>本地模拟撮合</b><p>已接入 · T+1 与成本</p></li><li><span>04</span><b>前向影子盘</b><p>尚未开始</p></li></ol>
        </div>
        <div className="decision-ladder">
          {[["D0", "候选筛选", "现在"], ["D1", "历史成份点时化", "下一步"], ["D2", "多年份滚动样本外", "待完成"], ["D3", "仿真盘含涨跌停", "待完成"], ["D4", "小资金影子盘", "未授权"]].map((item, index) => <div key={item[0]} className={index === 0 ? "active" : ""}><span>{item[0]}</span><b>{item[1]}</b><em>{item[2]}</em></div>)}
        </div>
      </section>

      <section className="section-shell source-section">
        <div className="section-heading"><span className="section-kicker">07 / PROVENANCE</span><h2>能定位，才能反驳。</h2></div>
        <div className="source-list">{sources.map((source, index) => <a key={source[0]} href={source[2]} target="_blank" rel="noreferrer"><span>0{index + 1}</span><div><small>{source[0]}</small><b>{source[1]}</b></div><i>↗</i></a>)}</div>
      </section>

      <footer className="site-footer"><div className="brand"><span className="brand-mark">Q</span><span>Q-FORGE</span></div><p>本网站是研究草案，不构成投资建议，不承诺收益。历史回测不是未来表现保证。</p><a href="#top">BACK TO TOP ↑</a></footer>
    </main>
  );
}
