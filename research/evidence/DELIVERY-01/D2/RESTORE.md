# 恢复这份数据快照

本附件对应代码提交 `5368a6fe77aacec86e23a831338d82bd5b2a3ad5`。
它是下载过程中的备份：含真实历史数据，也含未通过验证的旧研究结果。
不要将“可以恢复”理解成“数据已完整”或“策略收益可信”。

## 1. 下载代码并安装本地工具

```bash
git clone git@github.com:youdutaidi/QuanTrade.git
cd QuanTrade
git checkout 5368a6fe77aacec86e23a831338d82bd5b2a3ad5
python3 -m venv .venv
.venv/bin/pip install -e '.[test,data]'
```

如只想使用持续更新的版本，可以保留 `main`；上面的固定提交用于复核本次快照。
`python-packages.json` 记录制作快照时的已安装版本，不包含凭据或虚拟环境本体。

## 2. 下载三个核心附件

将 `quant-data.tar.gz`、`manifest.json`、`delivery.json` 放在同一个下载目录。
`manifest.json` 是逐文件清单；`delivery.json` 包含压缩包指纹。
本快照的 SHA256 是：

```text
0799eda5a445a1228f63168a304355e64ae821b84799e5099d15ddc55f34c94f
```

## 3. 校验并恢复到一个不存在的新目录

把下面的绝对路径替换成你的下载文件位置和新的恢复目录：

```bash
.venv/bin/qforge archive verify \
  --bundle /absolute/path/quant-data.tar.gz \
  --sha256 0799eda5a445a1228f63168a304355e64ae821b84799e5099d15ddc55f34c94f

.venv/bin/qforge archive restore \
  --bundle /absolute/path/quant-data.tar.gz \
  --sha256 0799eda5a445a1228f63168a304355e64ae821b84799e5099d15ddc55f34c94f \
  --output /absolute/path/QuanTrade-restored-data
```

恢复工具检查压缩包及每个文件的 SHA256，并检查 SQLite 完整性、外键和表行数。
它拒绝已存在的输出目录、路径穿越、符号链接、Cookie 缓存和临时侧文件。
成功输出的 `research/data/` 保留相对路径，包含三份数据库以及价格表。

## 4. 使用数据前的约束

- 新克隆的代码目录若还没有 `research/data/`，可将恢复目录里的这一整个
  子目录复制过去。若已有数据库，先停止所有下载/回测进程并另行备份；
  不要合并或覆盖正在使用的 SQLite/WAL 文件。
- 这份快照的日线任务记录可能仍显示 `running`。确认原采集进程确已停止后，
  才能使用 `qforge market complete --config configs/market_data.json` 的恢复流程。
  同时只能有一个 BaoStock 会话，不能在旧进程仍运行时另开下载。
- 公司行动尚未下载，最终覆盖、源数据复核和全量面板仍待完成。
  `walkforward preflight` 在条件不足时拒绝执行是预期行为。
- 五分钟库里的旧策略已被否决；新账本库只有合成测试。当前没有通过全部
  门槛的年化 100% 策略，也不发送真实订单。
- 原机器上的数据库不会因上传或恢复而删除；后续新增数据不在这个固定快照内。
