"""Single-snapshot, date-bounded witness for conservative gross source terms."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from .audit import audit_action_connection
from .store import ActionStore
from .terms import resolve_source_group


def preview_action_terms(path: str | Path, plan: dict, daily_input: dict, start: str, end: str) -> dict:
    if any(date.fromisoformat(value).isoformat() != value for value in (start, end)):
        raise ValueError("noncanonical preview date")
    if not plan["start"] <= start <= end <= plan["end"]:
        raise ValueError("preview dates outside source scope")
    with ActionStore(path).connect(readonly=True) as connection:
        connection.execute("BEGIN")
        audit = audit_action_connection(connection, path, plan, daily_input)
        if not audit["archiveIntegrityPass"]:
            raise ValueError("action source archive failed integrity admission")
        groups, unlocated = _source_groups(connection, start, end)
        resolution = _summarize(groups)
    return {"state": "gross-terms-preview-only", "start": start, "end": end, "archive": audit,
            **resolution, "unlocatedSourceRows": unlocated, "ledgerReady": False, "investorTaxVerified": False,
            "claim": "same-source gross term interpretation only; no tax, fractional allocation, rights or P&L admission"}


def _source_groups(connection, start: str, end: str) -> tuple[dict, int]:
    groups, unlocated = defaultdict(list), 0
    for response in connection.execute("SELECT request_id,raw_sha256,raw_json FROM action_requests WHERE status='succeeded' ORDER BY code,year"):
        for index, row in enumerate(json.loads(response["raw_json"])["rows"]):
            ex_date = row["dividOperateDate"]
            try:
                canonical = date.fromisoformat(ex_date).isoformat() == ex_date
            except ValueError:
                canonical = False
            if not canonical:
                unlocated += 1
            elif start <= ex_date <= end:
                groups[(row["code"], ex_date)].append({"raw": row, "source": {"requestId": response["request_id"],
                    "rawSha256": response["raw_sha256"], "rowIndex": index}})
    return groups, unlocated


def _summarize(groups: dict) -> dict:
    counts, reasons, examples = Counter(), Counter(), []
    fingerprint = hashlib.sha256()
    for (code, ex_date), records in sorted(groups.items()):
        result = resolve_source_group([record["raw"] for record in records])
        witness = {"code": code, "exDate": ex_date, **result, "sources": [record["source"] for record in records]}
        fingerprint.update(json.dumps(witness, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode() + b"\n")
        counts["sourceRowsInWindow"] += len(records)
        counts["eventGroups"] += 1
        counts[result["state"]] += 1
        counts["multipleRowGroups"] += int(len(records) > 1)
        if result["state"] == "unresolved":
            reason = result["reason"]
            reasons[reason] += 1
            if reasons[reason] <= 2 and len(examples) < 30:
                examples.append(witness)
        elif len(records) > 1 and counts["resolvedMultipleRowGroups"] < 5:
            examples.append(witness)
        if len(records) > 1 and result["state"] != "unresolved":
            counts["resolvedMultipleRowGroups"] += 1
    return {"counts": dict(counts), "unresolvedReasons": dict(reasons), "examples": examples,
            "groupIndexSha256": fingerprint.hexdigest(), "resolutionVersion": 1}
