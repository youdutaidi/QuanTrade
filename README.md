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

# 先查看公司行动的逐年采集范围；下载必须等日线验收通过。
.venv/bin/qforge actions plan --preview --config configs/corporate_actions.json
.venv/bin/qforge actions download --config configs/corporate_actions.json --max-tasks 10
.venv/bin/qforge actions status --config configs/corporate_actions.json

# 查看已冻结的候选，不读取市场收益。
.venv/bin/qforge walkforward plan --config configs/walk_forward.json

# 检查数据和配置是否准入；下载未结束时拒绝执行是预期行为。
.venv/bin/qforge walkforward preflight --config configs/walk_forward.json \
  --plan research/evidence/QF-WALKFORWARD-01/P1/frozen_plan.json

# 无网络合成账本测试。每次使用新输出目录，不覆盖旧证据。
.venv/bin/qforge walkforward ledger-demo --config configs/walk_forward.json \
  --output research/output/ledger-demo-local

# 冻结的 144 个候选在合成行情上逐日执行，并独立重放 SQLite 账本。
.venv/bin/qforge walkforward execution-demo --config configs/walk_forward.json \
  --output research/output/execution-demo-local --all-candidates

# 已有五分钟试验的数据状态。
.venv/bin/qforge minute status --config configs/minute_5m.json
```

`ledger-demo` 和 `execution-demo` 都是合成测试，不是真实市场收益；
20 个合成交易日不会被外推为年化收益率。
新的全量候选回测仍需完成数据验收、公司行动接入和市场执行验证。
已有日线和分钟研究入口保留在研究文档中，不会因新代码准备而被替换。

## 数据与复现

- `research/data/qforge_market.sqlite`：原始日线、交易日历、证券生命周期、
  历史股票池观察与复权因子。
- `research/data/qforge_minute.sqlite`：已下载的真实五分钟样本，以及旧试验账本。
- `research/data/qforge_walkforward.sqlite`：新账本的不可覆盖运行记录和事件。
- `research/data/qforge_actions.sqlite`：公司行动采集准入后创建，保存分红接口的
  原始返回、逐年空返回、失败记录和可恢复检查点；不代表税务或总回报已验证。
- `research/evidence/`：配置指纹、测试、审计、源数据重取检查与运行证据。
- `configs/validation_policy.json`：可信策略的统一门槛；通过单项不等于整体通过。

大数据文件不直接放进普通 Git 历史，而放在本仓库的 Releases，
包含一致性数据库备份、原始/派生数据清单、SHA256 和恢复说明。
较新的[数据快照 data-20260826-d3](https://github.com/youdutaidi/QuanTrade/releases/tag/data-20260826-d3)
已发布，归档大小 1,166,904,403 字节；318 个文件和四份 SQLite 数据库
均已从 GitHub 下载、校验并恢复到新的本地目录。附件包含恢复验证报告。
这份快照有 7,077,020 条日线和 116,160 条五分钟记录；分红库捕获时只有
721 次请求、571 条原始事件，仍不完整。新账本的145次运行均为合成数据测试。
不包含捕获后新增的数据；不要把它当作最终全量数据或已验证策略。
较早的[采集中快照 D2](https://github.com/youdutaidi/QuanTrade/releases/tag/data-20260826-d2)也保留不变。
本地数据库不会因上传而删除。

备份与恢复入口如下。输出目录必须是新的；恢复不会覆盖现有数据。
下载 Release 附件后，从 `delivery.json` 读取对应的 SHA256：

```bash
.venv/bin/qforge archive create --label in-progress \
  --output research/output/delivery/my-snapshot

.venv/bin/qforge archive verify --bundle /path/to/quant-data.tar.gz \
  --sha256 YOUR_SHA256
.venv/bin/qforge archive restore --bundle /path/to/quant-data.tar.gz \
  --sha256 YOUR_SHA256 --output /path/to/new-restored-directory
```

新目录内保留 `research/data` 等相对路径。先核对恢复报告，再在停止本地
下载进程后使用这些数据库；不要覆盖正在写入的库，也不要单独复制 WAL。
下载中的快照会保留当时的检查点，不能当作全量数据已验收。代码提交号、
逐文件校验值和每个数据库的表行数记录在附件清单中。

研究价格序列可用于信号计算，但不是现金和股份的经济总回报账本。
未来可得信息、交易费用、停牌/涨跌停、公司行动、重复试验偏差、独立
重放和实际前向模拟盘均需分别验证。历史回测不保证未来表现。
