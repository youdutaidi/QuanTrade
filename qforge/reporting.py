"""Persist machine-readable results and a standalone local HTML report."""

from __future__ import annotations

import html
import json
from pathlib import Path

import pandas as pd


def write_outputs(payload: dict[str, object], output_dir: str | Path, app_output: str | None = None) -> dict[str, str]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    json_path = target / "results.json"
    html_path = target / "report.html"
    csv_path = target / "factor_summary.csv"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")
    pd.DataFrame(payload["ranking"]).to_csv(csv_path, index=False)
    if app_output:
        app_path = Path(app_output)
        app_path.parent.mkdir(parents=True, exist_ok=True)
        app_path.write_text(json.dumps(_app_payload(payload), ensure_ascii=False, indent=2), encoding="utf-8")
    return {"json": str(json_path), "html": str(html_path), "csv": str(csv_path)}


def render_html(payload: dict[str, object]) -> str:
    experiment = html.escape(str(payload["experimentId"]))
    rows = "".join(_ranking_row(row) for row in payload["ranking"])
    gates = "".join(_gate_card(gate) for gate in payload["gates"])
    top = payload["ranking"][0] if payload["ranking"] else {}
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{experiment} · Q-Forge</title><style>{_css()}</style></head>
<body><main><header><p class="eyebrow">Q-FORGE / LOCAL FACTOR ENGINE</p><h1>{experiment}</h1>
<p>点时信号、次日开盘执行、显式成本、IC/分层/组合三层证据。</p></header>
<section class="hero"><div><span>领先候选</span><strong>{html.escape(str(top.get('factor', '—')))}</strong></div>
<div><span>组合收益</span><strong>{_pct(top.get('totalReturn'))}</strong></div>
<div><span>最大回撤</span><strong>{_pct(top.get('maxDrawdown'))}</strong></div>
<div><span>Mean IC</span><strong>{_num(top.get('meanIC'))}</strong></div></section>
<section><h2>因子排行榜</h2><div class="table"><table><thead><tr><th>因子</th><th>Mean IC</th><th>ICIR</th><th>收益</th><th>回撤</th><th>Sharpe</th><th>换手</th></tr></thead><tbody>{rows}</tbody></table></div></section>
<section><h2>证据边界</h2><div class="gates">{gates}</div></section>
<footer>本报告由本地代码生成，仅用于研究，不构成投资建议。历史回测不代表未来收益。</footer>
</main></body></html>"""


def _ranking_row(row: dict[str, object]) -> str:
    return "<tr>" + "".join(
        f"<td>{value}</td>" for value in [
            html.escape(str(row["factor"])),
            _num(row["meanIC"]),
            _num(row["icIR"]),
            _pct(row["totalReturn"]),
            _pct(row["maxDrawdown"]),
            _num(row["sharpe"]),
            _num(row["turnover"]),
        ]
    ) + "</tr>"


def _gate_card(gate: dict[str, object]) -> str:
    return f"<article class='{html.escape(str(gate['status']))}'><b>{html.escape(str(gate['name']))}</b><p>{html.escape(str(gate['note']))}</p></article>"


def _app_payload(payload: dict[str, object]) -> dict[str, object]:
    factors = []
    for item in payload["factors"]:
        factors.append({
            "name": item["name"],
            "description": item["description"],
            "diagnostics": {key: value for key, value in item["diagnostics"].items() if key not in {"quantileCurves", "longShortCurve"}},
            "metrics": item["portfolio"]["metrics"],
            "designMetrics": item["portfolio"]["designMetrics"],
            "holdoutMetrics": item["portfolio"]["holdoutMetrics"],
        })
    return {
        "engineVersion": payload["engineVersion"],
        "experimentId": payload["experimentId"],
        "factorCount": payload["factorCount"],
        "config": payload["config"],
        "dataAudit": payload["dataAudit"],
        "ranking": payload["ranking"],
        "factors": factors,
        "gates": payload["gates"],
    }


def _pct(value: object) -> str:
    return f"{float(value or 0) * 100:+.1f}%"


def _num(value: object) -> str:
    return f"{float(value or 0):.3f}"


def _css() -> str:
    return """
:root{color-scheme:dark;--ink:#eef5db;--muted:#93a58b;--acid:#cbff35;--line:#294431;--panel:#102719}
*{box-sizing:border-box}body{margin:0;background:#07120b;color:var(--ink);font:15px/1.6 ui-sans-serif,system-ui}
main{max-width:1180px;margin:auto;padding:56px 24px}header{border-left:3px solid var(--acid);padding-left:22px}h1{font-size:clamp(35px,6vw,72px);margin:.05em 0;letter-spacing:-.05em}.eyebrow{color:var(--acid);font:12px ui-monospace;letter-spacing:.16em}
.hero{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--line);border:1px solid var(--line);margin:44px 0}.hero div{background:var(--panel);padding:22px}.hero span{display:block;color:var(--muted);font-size:12px}.hero strong{font:24px ui-monospace;color:var(--acid)}
section{margin:52px 0}h2{font-size:22px}.table{overflow:auto;border:1px solid var(--line)}table{width:100%;border-collapse:collapse;min-width:760px}th,td{padding:13px 16px;text-align:right;border-bottom:1px solid var(--line);font-family:ui-monospace}th:first-child,td:first-child{text-align:left}th{color:var(--muted);font-size:11px;text-transform:uppercase}
.gates{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.gates article{border:1px solid var(--line);background:var(--panel);padding:18px}.gates .fail{border-color:#d9614c}.gates .partial{border-color:#d5a829}.gates p,footer,header>p{color:var(--muted)}footer{border-top:1px solid var(--line);padding-top:24px}@media(max-width:760px){.hero,.gates{grid-template-columns:1fr 1fr}}
"""
