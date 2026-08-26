# QuanTrade / Q-Forge

本地 A 股量化研究网站、Python 因子研究工具和 SQLite 数据库。
代码与数据在本机运行，不连接券商，不发送真实订单。

当前没有通过全部验证门槛的策略，不能承诺年化 100%。仓库保留了
被否决的历史试验，不能把这些试验的高收益数字当作可实现业绩。
完整实验协议、证据边界与下一步见 [research/README.md](research/README.md)。

## 启动本地网站

需要 Node.js 22.13+。在项目目录执行：

```bash
npm ci
npm run dev
```

打开 <http://localhost:3000/>。macOS 也可以双击
`启动本地网站.command`。终端需保持开启；网站不需要发布到公网。
网页展示研究与验证结果，Python 命令负责数据采集和回测；网页不是
券商交易终端，也不能把按钮或演示界面当作已完成的真实回测。

## 安装 Python 研究工具

需要 Python 3.11+：

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[test,data]'
.venv/bin/python -m pytest -q
```

主要入口：

```bash
# 数据下载与断点恢复：同一时间只能有一个 BaoStock 下载进程。
.venv/bin/qforge market complete --config configs/market_data.json
.venv/bin/qforge market verify-panel --config configs/market_data.json

# 查看已冻结的候选，不读取市场收益。
.venv/bin/qforge walkforward plan --config configs/walk_forward.json

# 检查数据和配置是否准入；下载未结束时拒绝执行是预期行为。
.venv/bin/qforge walkforward preflight --config configs/walk_forward.json \
  --plan research/evidence/QF-WALKFORWARD-01/P1/frozen_plan.json

# 无网络合成账本测试。每次使用新输出目录，不覆盖旧证据。
.venv/bin/qforge walkforward ledger-demo --config configs/walk_forward.json \
  --output research/output/ledger-demo-local

# 已有五分钟试验的数据状态。
.venv/bin/qforge minute status --config configs/minute_5m.json
```

`ledger-demo` 是手工可核算的合成测试，不是真实市场收益。
新的全量候选回测仍需完成数据验收、公司行动接入和市场执行验证。
已有日线和分钟研究入口保留在研究文档中，不会因新代码准备而被替换。

## 数据与复现

- `research/data/qforge_market.sqlite`：原始日线、交易日历、证券生命周期、
  历史股票池观察与复权因子。
- `research/data/qforge_minute.sqlite`：已下载的真实五分钟样本，以及旧试验账本。
- `research/data/qforge_walkforward.sqlite`：新账本的不可覆盖运行记录和事件。
- `research/evidence/`：配置指纹、测试、审计、源数据重取检查与运行证据。
- `configs/validation_policy.json`：可信策略的统一门槛；通过单项不等于整体通过。

大数据文件不直接放进普通 Git 历史。最终交付目标是本仓库的 Releases，
包含一致性数据库备份、原始/派生数据清单、SHA256 和恢复说明。
在上传并回读验证前，不能仅凭这段说明认定数据已在远程可用。
本地数据库不会因上传而删除。

研究价格序列可用于信号计算，但不是现金和股份的经济总回报账本。
未来可得信息、交易费用、停牌/涨跌停、公司行动、重复试验偏差、独立
重放和实际前向模拟盘均需分别验证。历史回测不保证未来表现。
