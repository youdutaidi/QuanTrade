"""Build a searchable factor catalogue from the Federal Reserve OpenSourceAP workbook."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "research/source/open_source_ap_signal_documentation.xlsx"
JSON_OUT = ROOT / "app/data/factors.json"
CSV_OUT = ROOT / "research/output/factor_catalog.csv"

DATA_LABELS = {
    "Accounting": "财务报表",
    "Market": "行情交易",
    "Price": "价格行为",
    "Trading": "交易微观结构",
    "Event": "公司事件",
    "Analyst": "分析师预期",
    "Options": "期权衍生品",
    "13F": "机构持仓",
    "Other": "另类数据",
}

ECON_LABELS = {
    "investment": "投资与增长",
    "investment growth": "投资与增长",
    "earnings growth": "盈利增长",
    "sales growth": "盈利增长",
    "profitability": "质量与盈利",
    "quality": "质量与盈利",
    "value": "估值",
    "valuation": "估值",
    "size": "规模",
    "momentum": "动量与反转",
    "reversal": "动量与反转",
    "default risk": "杠杆与偿债",
    "cash flow risk": "杠杆与偿债",
    "optionrisk": "衍生品风险",
    "risk": "低风险",
    "volatility": "低风险",
    "liquidity": "流动性",
    "turnover": "流动性",
    "volume": "流动性",
    "issuance": "融资与股本",
    "external financing": "融资与股本",
    "payout": "融资与股本",
    "ownership": "持仓与治理",
    "leverage": "杠杆与偿债",
    "accruals": "质量与盈利",
    "asset composition": "资产结构",
    "r&d": "研发创新",
    "earnings forecast": "分析师预期",
    "recommendation": "分析师预期",
    "short sale": "市场摩擦",
    "lead lag": "市场摩擦",
    "event": "事件驱动",
    "other": "其他",
}


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def economic_group(value: object) -> str:
    raw = clean(value).lower()
    for key, label in ECON_LABELS.items():
        if key in raw:
            return label
    return "其他"


def evidence_grade(signal: str, quality: str, t_stat: object) -> str:
    try:
        t_value = abs(float(t_stat))
    except (TypeError, ValueError):
        t_value = 0.0
    if signal == "Predictor" and quality.startswith("1_") and t_value >= 3:
        return "A"
    if signal == "Predictor" and (quality.startswith("1_") or t_value >= 2):
        return "B"
    if signal == "Predictor":
        return "C"
    return "D"


def availability(data_type: str) -> tuple[str, str]:
    if data_type in {"Market", "Price", "Trading"}:
        return "可直接首测", "日线行情可公开获得；仍需处理停牌、涨跌停与复权时点。"
    if data_type == "Accounting":
        return "需点时库", "必须保存公告发布日期与更正版本，不能用当前财务快照回填历史。"
    if data_type == "Analyst":
        return "需授权源", "一致预期通常需要有许可的点时数据库。"
    if data_type in {"Options", "13F"}:
        return "跨市场适配", "原定义偏美国市场，A/H 股需重写字段与制度口径。"
    if data_type == "Event":
        return "需事件时点库", "必须按首次公告时间建库，并区分预案、实施与撤回。"
    return "待定义", "需要单独确认数据许可、发布时间与历史覆盖。"


def main() -> None:
    basic = pd.read_excel(SOURCE, sheet_name="BasicInfo")
    extra = pd.read_excel(SOURCE, sheet_name="AddInfo")
    merged = basic.merge(extra, on=["Acronym", "Authors"], how="left", suffixes=("", "_extra"))

    rows: list[dict[str, object]] = []
    for _, row in merged.iterrows():
        data_type = clean(row.get("Cat.Data"))
        signal = clean(row.get("Cat.Signal"))
        quality = clean(row.get("Signal Rep Quality"))
        status, boundary = availability(data_type)
        t_stat = row.get("T-Stat")
        rows.append(
            {
                "id": clean(row.get("Acronym")),
                "name": clean(row.get("LongDescription")) or clean(row.get("Acronym")),
                "authors": clean(row.get("Authors")),
                "year": int(row["Year"]) if pd.notna(row.get("Year")) else None,
                "journal": clean(row.get("Journal")),
                "signalType": signal or "Unknown",
                "form": clean(row.get("Cat.Form")),
                "dataType": DATA_LABELS.get(data_type, data_type or "未知"),
                "dataTypeRaw": data_type,
                "economicGroup": economic_group(row.get("Cat.Economic")),
                "economicRaw": clean(row.get("Cat.Economic")),
                "formula": clean(row.get("Cat.Signal Formula")),
                "definition": clean(row.get("Detailed Definition")),
                "evidence": clean(row.get("Evidence Summary")),
                "replicationQuality": quality,
                "tStat": round(float(t_stat), 3) if pd.notna(t_stat) else None,
                "sign": int(row["Sign"]) if pd.notna(row.get("Sign")) else None,
                "grade": evidence_grade(signal, quality, t_stat),
                "ahStatus": status,
                "ahBoundary": boundary,
                "source": "Federal Reserve OpenSourceAP documentation",
            }
        )

    rows.sort(key=lambda item: (item["economicGroup"], item["name"]))
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(rows).to_csv(CSV_OUT, index=False)
    print(json.dumps({"factors": len(rows), "json": str(JSON_OUT), "csv": str(CSV_OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
