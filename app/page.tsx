"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import factorsJson from "./data/factors.json";
import backtestJson from "./data/backtest.json";
import factorBacktestJson from "./data/factor_backtest.json";
import minuteSystemJson from "./data/minute_system.json";
import marketInventoryJson from "./data/data_inventory.json";
import validationRegistryJson from "./data/validation_registry.json";

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
const marketInventory = marketInventoryJson;
const validationRegistry = validationRegistryJson;

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
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("全部");
  const [grade, setGrade] = useState("全部");
  const [selectedFactor, setSelectedFactor] = useState<string | null>(null);
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
  const policy = validationRegistry.policy;
  const marketTaskTotal = marketInventory.tasks.reduce((sum, task) => sum + task.taskCount, 0);
  const marketTasksDone = marketInventory.tasks.find((task) => task.status === "succeeded")?.taskCount ?? 0;

  return (
    <main id="top">
      <nav className="nav-shell">
        <a className="brand" href="#top"><span className="brand-mark">Q</span><span>Q-FORGE</span></a>
        <div className="nav-links">
          <a href="#backtest">回测</a><a href="#engine">因子引擎</a><a href="#minute">分钟交易</a><a href="#audit">风险审计</a>
        </div>
        <div className="status-chip"><span /> {validationRegistry.summary.verified} VERIFIED · 本地研究</div>
      </nav>

      <header className="hero">
        <div className="hero-copy">
          <div className="eyebrow"><span>POLICY 1.0</span> 已验证策略注册表 · 截至 {backtest.asOf}</div>
          <h1>先通过验证，<br /><em>再谈翻倍。</em></h1>
          <p className="hero-lead">年化 100% 是准入门槛，不是宣传口号。点时股票池、多年份样本外、真实交易摩擦、独立复算和前向模拟缺一不可；未通过的历史高收益不会出现在可信策略列表。</p>
          <div className="hero-actions">
            <a className="button primary" href="#backtest">查看验证门禁 <span>↘</span></a>
            <a className="button ghost" href="#audit">查看研究边界</a>
          </div>
        </div>
        <aside className="signal-card" aria-label="已验证策略数量">
          <div className="card-topline"><span>VERIFIED STRATEGIES ONLY</span><span className="candidate-dot">ENFORCED</span></div>
          <div className="target-row"><strong>{validationRegistry.summary.verified}</strong><span>当前通过<br />完整门禁</span></div>
          <div className="mini-summary">
            <div><small>年化门槛</small><b>≥100%</b></div><div><small>回撤上限</small><b>≤35%</b></div>
            <div><small>最低数据</small><b>{policy.minimumDataYears} 年</b></div><div><small>前向模拟</small><b>{policy.minimumForwardPaperDays} 日</b></div>
          </div>
          <div className="verdict-line"><span>{validationRegistry.summary.rejected} 个候选已拒绝</span><p>没有通过者，就明确显示零</p></div>
        </aside>
      </header>

      <section className="metrics-strip">
        <div><small>已验证策略</small><strong>{validationRegistry.summary.verified}</strong><p>只有完整通过门禁才计数</p></div>
        <div><small>已审查候选</small><strong>{validationRegistry.summary.assessed}</strong><p>当前全部留在研究层</p></div>
        <div><small>最低数据年限</small><strong>{policy.minimumDataYears}</strong><p>覆盖不同市场状态</p></div>
        <div><small>滚动样本外</small><strong>{policy.minimumWalkForwardFolds}</strong><p>至少三折且参数冻结</p></div>
      </section>

      <section className="truth-banner">
        <span className="truth-code">ENFORCED / NO EXCEPTIONS</span>
        <strong>历史高收益候选已经从可信展示中撤下。</strong>
        <p>收益再高，只要存在幸存者偏差、样本外不足或没有前向模拟，状态就只能是 REJECTED。</p>
      </section>

      <section className="section-shell backtest-section" id="backtest">
        <div className="section-heading split-heading">
          <div><span className="section-kicker">01 / VALIDATION REGISTRY</span><h2>当前没有策略<br />获得可信认证。</h2></div>
          <p>这不是空白，而是门禁正常工作。只有所有检查同时通过，策略名称、收益曲线和回测指标才会进入本区域。</p>
        </div>
        <div className="registry-empty"><span>VERIFIED REGISTRY</span><strong>0</strong><h3>暂无通过者</h3><p>系统不会用历史搜索冠军填补这个空位。</p></div>
        <div className="policy-grid">
          {[
            ["01", "点时股票池", "不允许用今天的成份股倒推历史"],
            ["02", "多年份样本外", `${policy.minimumDataYears} 年数据 · ${policy.minimumWalkForwardFolds} 折走步`],
            ["03", "交易真实性", "成本、滑点、涨跌停、T+1 与容量"],
            ["04", "独立复算", "从成交账本重建现金与持仓"],
            ["05", "多重检验", "控制搜参与因子挖掘偏差"],
            ["06", "前向模拟", `至少 ${policy.minimumForwardPaperDays} 个未来交易日`],
          ].map((item) => <article key={item[0]}><span>{item[0]}</span><h3>{item[1]}</h3><p>{item[2]}</p></article>)}
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
          <div className="engine-table-head"><div><span className="section-kicker">RESEARCH ENGINE / {factorBacktest.experimentId}</span><h3>计算能力不等于策略认证</h3></div><p>因子结果仍保留在本地研究证据中，但未通过统一门禁前，网站不公开候选收益排名。</p></div>
          <div className="engine-verdict"><span>ENGINE STATUS</span><b>代码闭环可运行；可信策略注册表仍为空。</b><p>{factorBacktest.factorCount} 个可执行因子只用于生成待验证假设，不能自动升级为投资策略。</p></div>
        </div>
      </section>

      <section className="section-shell minute-section" id="minute">
        <div className="section-heading split-heading">
          <div><span className="section-kicker">03 / MINUTE DATA & PAPER BROKER</span><h2>分钟基础设施可用，<br />尚无认证策略。</h2></div>
          <p>BaoStock 5 分钟数据已经真实落入本机 SQLite；失败实验保留在本地证据中，但不会作为可用策略展示。</p>
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
            <div><span>VALIDATION STATUS</span><em>REJECTED</em></div>
            <strong>0</strong>
            <h3>分钟认证策略</h3>
            <p>当前分钟候选没有通过收益、回撤、数据年限、点时股票池和前向模拟门禁，因此不发布其收益曲线。</p>
            <dl><div><dt>本地K线</dt><dd>{minuteSystem.database.barCount.toLocaleString()}</dd></div><div><dt>交易日</dt><dd>{minuteSystem.database.tradeDays}</dd></div><div><dt>模拟订单</dt><dd>{minuteSystem.ledger.orderCount.toLocaleString()}</dd></div><div><dt>通过策略</dt><dd>0</dd></div></dl>
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
          <div><span className="section-kicker">06 / EVIDENCE GATES</span><h2>没有通过验证，<br />就不发布策略。</h2></div>
          <div className="audit-verdict"><span>VERDICT</span><b>{validationRegistry.summary.verified} VERIFIED</b><p>{validationRegistry.summary.rejected} rejected · policy {policy.policyVersion}</p></div>
        </div>
        <div className="gate-grid">{[
          ["年化收益", `样本外年化必须 ≥ ${pct(policy.minimumAnnualizedReturn)}`],
          ["风险约束", `最大回撤必须优于 ${pct(policy.maximumDrawdown)}`],
          ["点时数据", "股票池、公司行动和字段可用时间必须可追溯"],
          ["滚动样本外", `至少 ${policy.minimumWalkForwardFolds} 折，累计样本外不少于 ${policy.minimumOutOfSampleYears} 年`],
          ["独立复算", "必须从订单与成交账本重建现金、持仓和净值"],
          ["前向模拟", `冻结后连续运行不少于 ${policy.minimumForwardPaperDays} 个交易日`],
        ].map((gate, index) => (
          <article key={gate[0]} className="gate gate-partial"><div><span>G{index + 1}</span><em>REQUIRED</em></div><h3>{gate[0]}</h3><p>{gate[1]}</p></article>
        ))}</div>
        <div className="research-contract">
          <div><span className="section-kicker">FROZEN POLICY / 1.0</span><h3>可信准入口径</h3></div>
          <dl>
            <div><dt>收益门槛</dt><dd>样本外年化 ≥ {pct(policy.minimumAnnualizedReturn)}</dd></div>
            <div><dt>风险门槛</dt><dd>最大回撤 ≥ {pct(policy.maximumDrawdown)} · Sharpe ≥ {policy.minimumSharpe}</dd></div>
            <div><dt>数据门槛</dt><dd>至少 {policy.minimumDataYears} 年且使用历史点时股票池</dd></div>
            <div><dt>验证门槛</dt><dd>{policy.minimumWalkForwardFolds} 折走步 · 多重检验控制</dd></div>
            <div><dt>前向门槛</dt><dd>至少 {policy.minimumForwardPaperDays} 个未来交易日</dd></div>
            <div><dt>硬禁令</dt><dd>任一门禁失败，不在网站发布为可信策略</dd></div>
          </dl>
        </div>
        <div className="minute-status-grid" aria-label="本地点时数据库存">
          <div><small>证券生命周期</small><strong>{marketInventory.stockCount.toLocaleString()}</strong><p>含 {marketInventory.delistedStockCount} 只退市股票</p></div>
          <div><small>历史股票池核对</small><strong>{marketInventory.audits.filter((audit) => audit.status === "pass").length}/{marketInventory.audits.length}</strong><p>抽样日期与源数据零差异</p></div>
          <div><small>多年日线任务</small><strong>{marketTasksDone}/{marketTaskTotal}</strong><p>{marketInventory.dailyBarCount.toLocaleString()} 根 · 下载任务可恢复</p></div>
          <div><small>本地 SQLite</small><strong>{number(marketInventory.databaseBytes / 1024 / 1024, 1)} MB</strong><p>WAL · 幂等写入 · 不上传云端</p></div>
        </div>
        <p>库存快照：{marketInventory.snapshotAt.slice(0, 19).replace("T", " ")} UTC。此处不是实时数据库查询；下载完成后仍需完整性审计和源数据复核，不能直接视为已验证策略。</p>
        <div className="minute-roadmap">
          <div><span className="section-kicker">DATA EXPANSION ROUTE</span><h3>数据先于策略。</h3><p>现有分钟试点将扩展到多年份、点时股票池和本地增量数据库，再进入冻结候选回测。</p></div>
          <ol><li><span>01</span><b>点时股票池</b><p>历史每日证券列表</p></li><li><span>02</span><b>多年行情</b><p>日线发现 · 分钟执行</p></li><li><span>03</span><b>严格回测</b><p>走步 · 成本 · 复算</p></li><li><span>04</span><b>前向影子盘</b><p>通过后才计时</p></li></ol>
        </div>
        <div className="decision-ladder">
          {[["D0", "可信门禁", "已启用"], ["D1", "扩展本地数据", "进行中"], ["D2", "滚动样本外", "待数据"], ["D3", "独立复算", "待候选"], ["D4", "前向模拟", "待通过"]].map((item, index) => <div key={item[0]} className={index === 0 ? "active" : ""}><span>{item[0]}</span><b>{item[1]}</b><em>{item[2]}</em></div>)}
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
