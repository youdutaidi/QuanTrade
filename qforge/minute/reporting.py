"""Local JSON and HTML reporting for minute data and paper execution."""

from __future__ import annotations

import html
import json
from pathlib import Path


def write_minute_outputs(payload: dict[str, object], output_dir: str | Path, app_output: str | None) -> dict[str, str]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    json_path = target / "results.json"
    html_path = target / "report.html"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")
    if app_output:
        app_path = Path(app_output)
        app_path.parent.mkdir(parents=True, exist_ok=True)
        app_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"json": str(json_path), "html": str(html_path)}


def write_status(payload: dict[str, object], app_output: str | Path) -> None:
    path = Path(app_output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def render_html(payload: dict[str, object]) -> str:
    metrics = payload.get("metrics", {})
    database = payload["database"]
    orders = "".join(_order_row(item) for item in payload.get("recentOrders", []))
    gates = "".join(_gate(item) for item in payload["gates"])
    return f"""<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Q-Forge Minute Lab</title><style>{_css()}</style></head><body><main>
<p class='eyebrow'>Q-FORGE / LOCAL MINUTE LAB</p><h1>{html.escape(str(payload['experimentId']))}</h1><p class='lead'>BaoStock 5分钟 → SQLite → 次根K线模拟撮合 → 本地账本</p>
<section class='stats'><div><span>Bars</span><b>{database.get('barCount',0):,}</b></div><div><span>Symbols</span><b>{database.get('symbolCount',0)}</b></div><div><span>Return</span><b>{_pct(metrics.get('totalReturn'))}</b></div><div><span>Max DD</span><b>{_pct(metrics.get('maxDrawdown'))}</b></div></section>
<section><h2>最近订单</h2><table><thead><tr><th>时间</th><th>代码</th><th>方向</th><th>请求/成交</th><th>状态</th></tr></thead><tbody>{orders}</tbody></table></section>
<section><h2>证据门槛</h2><div class='gates'>{gates}</div></section><footer>模拟交易，不连接券商，不构成投资建议。</footer>
</main></body></html>"""


def _order_row(item: dict[str, object]) -> str:
    values = [item["bar_time"], item["symbol"], item["side"], f"{item['requested_qty']}/{item['filled_qty']}", item["status"]]
    return "<tr>" + "".join(f"<td>{html.escape(str(value))}</td>" for value in values) + "</tr>"


def _gate(item: dict[str, object]) -> str:
    return f"<article class='{item['status']}'><b>{html.escape(str(item['name']))}</b><p>{html.escape(str(item['note']))}</p></article>"


def _pct(value: object) -> str:
    return f"{float(value or 0)*100:+.1f}%"


def _css() -> str:
    return """
:root{color-scheme:dark;--bg:#07120b;--panel:#102719;--line:#294431;--ink:#eef5db;--acid:#cbff35;--muted:#93a58b;--red:#ff805f}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 system-ui}main{max-width:1120px;margin:auto;padding:64px 24px}.eyebrow{color:var(--acid);font:12px monospace;letter-spacing:.15em}h1{font-size:clamp(38px,7vw,76px);margin:.1em 0;letter-spacing:-.05em}.lead{color:var(--muted)}.stats{display:grid;grid-template-columns:repeat(4,1fr);margin:42px 0;background:var(--line);gap:1px;border:1px solid var(--line)}.stats div{background:var(--panel);padding:20px}.stats span{display:block;color:var(--muted);font-size:11px}.stats b{font:26px monospace;color:var(--acid)}section{margin:50px 0}table{width:100%;border-collapse:collapse}th,td{padding:12px;border-bottom:1px solid var(--line);text-align:left;font:12px monospace}th{color:var(--muted)}.gates{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.gates article{padding:16px;background:var(--panel);border:1px solid var(--line)}.gates .fail{border-color:var(--red)}.gates p,footer{color:var(--muted);font-size:12px}@media(max-width:680px){.stats,.gates{grid-template-columns:1fr 1fr}}
"""

