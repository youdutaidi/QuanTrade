# 恢复 D3 数据快照

固定代码：`ebce265f85f1ce76498104c60ccbee4ecd74a769`。
快照记录了 2026-08-26 14:43:57—14:44:18（上海时间）的逐文件捕获时刻，
不是四个数据库之间的一次全局事务。公司行动仍在采集，策略仍未通过验证。

## 1. 安装固定版本

```bash
git clone git@github.com:youdutaidi/QuanTrade.git
cd QuanTrade
git checkout ebce265f85f1ce76498104c60ccbee4ecd74a769
python3 -m venv .venv
.venv/bin/pip install -e '.[test,data]'
```

`python-packages.json` 和 `runtime.json` 记录实测依赖版本。若只使用持续更新
的版本，可以保留 `main`；复核这份快照应使用上述提交。

## 2. 下载与校验

下载 `quant-data.tar.gz`、`manifest.json`、`delivery.json`。压缩包大小
1,166,904,403 字节；SHA256 为：

```text
f7ec5a289494292d8133577b0cf6cefc3508d6fd73e649eb6d56e52434a5e024
```

```bash
.venv/bin/qforge archive verify \
  --bundle /absolute/path/quant-data.tar.gz \
  --sha256 f7ec5a289494292d8133577b0cf6cefc3508d6fd73e649eb6d56e52434a5e024

.venv/bin/qforge archive restore \
  --bundle /absolute/path/quant-data.tar.gz \
  --sha256 f7ec5a289494292d8133577b0cf6cefc3508d6fd73e649eb6d56e52434a5e024 \
  --output /absolute/path/QuanTrade-restored-data
```

把绝对路径换成实际位置。恢复目录必须尚不存在；工具不会覆盖旧目录。
它校验每个文件、SQLite 完整性/外键和全部表行数，不直接写入工作数据库。

## 3. 这份快照包含什么

- 318 个数据及证据文件。
- 日线：7,077,020 条原始记录、24,831 条复权因子；日历、生命周期、
  历史股票池、下载检查点齐全。冻结窗口为 2020-08-25 至 2026-08-24。
- 日线研究面板：7,076,844 行；176 条停牌退市边界记录仅留在原始数据库。
  面板 SHA256：`5c872434d4fddf066f6fb8f8e5e151cb25b5334aefd71b6d47f67524895717dc`。
  本机完整性、日历覆盖和 20 个同源重取样本已通过。不是跨数据商独立验证。
- 五分钟：116,160 条真实样本，10 只股票、242 个交易日；旧策略已被否决。
- 分红原始档案：34,476 个计划任务，当时记录 721 次请求、571 行事件，
  仍有未完成任务。描述原文、税后金额歧义和空字段保留，不能直接当作经济账本。
- 新策略账本：145 次**合成**运行、7356 个事件，包括 144 个冻结候选的
  合成执行测试，不是真实收益。
- 原始/派生价格文件、测试、审计、失败历史、研究报告和配置指纹。

## 4. 在新路径使用数据

仅在新克隆尚无 `research/data/` 时，将恢复目录内的整个 `research/data/`
复制到克隆的同名位置。不要覆盖、合并正在使用的数据库；已有数据时先停任务
并另行备份。恢复出的历史证据可留在恢复目录独立核对，不必覆盖 Git 中的证据。

历史 manifest 记录的是捕获机器的绝对路径。换机器或目录后，应在新克隆内运行：

```bash
.venv/bin/qforge market complete --config configs/market_data.json
.venv/bin/qforge market verify-panel --config configs/market_data.json
```

该流程保留成功下载检查点，重新进行审计、联网抽样和本地面板导出，生成新路径的
manifest；不要手改旧证据中的绝对路径或 SHA256。联网抽样失败时不会宣称准入。

确认该机器没有其他 BaoStock 进程后，再恢复未完分红任务：

```bash
.venv/bin/qforge actions download --config configs/corporate_actions.json
```

只能有一个数据源会话；中断记录会保留，成功记录不会重复下载。原机器若仍采集，
应先协调停止，不要同时对同一数据源加开采集进程。

网站：`npm ci` 后 `npm run dev`，打开 `http://localhost:3000/`。
当前没有通过全部验证的策略，没有实盘订单，也没有已验证年化 100% 的承诺。
这份固定快照不包含捕获后新增的数据；上传不删除原机器的本地数据库。
