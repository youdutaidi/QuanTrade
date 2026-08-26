"""Read-only archival witness; raw capture readiness never certifies economics."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

from .normalization import NORMALIZATION_VERSION, normalize_response
from .store import ActionStore, utc_now


def audit_action_archive(path: str | Path, plan: dict, daily_input: dict) -> dict:
    problems = {"counts": Counter(), "examples": []}
    with ActionStore(path).connect(readonly=True) as connection:
        connection.execute("BEGIN")
        scope = connection.execute("SELECT scope_sha256,plan_json FROM action_scope WHERE singleton=1").fetchone()
        snapshot_at = utc_now()
        _check_scope(scope, plan, problems)
        integrity = [row[0] for row in connection.execute("PRAGMA quick_check")]
        foreign = connection.execute("PRAGMA foreign_key_check").fetchall()
        if integrity != ["ok"] or foreign:
            _problem(problems, "sqlite_integrity", {"quickCheck": integrity, "foreignKeys": len(foreign)})
        tasks = _audit_tasks(connection, plan, problems)
        sources = _audit_runs(connection, plan["scopeSha256"], daily_input, problems)
        _audit_ownership(connection, problems)
        responses = _audit_responses(connection, plan, problems)
    valid = not problems["counts"]
    task_problems = {"invalid_expected_plan", "missing_planned_task", "unexpected_task"}
    complete = (bool(plan["tasks"]) and tasks == {"succeeded": len(plan["tasks"])}
                and not task_problems.intersection(problems["counts"]))
    ready = valid and complete
    return {"state": "capture-ready" if ready else "capture-incomplete" if valid else "capture-invalid",
            "snapshotAt": snapshot_at, "database": str(Path(path).resolve()), "scopeSha256": plan["scopeSha256"],
            "dailyInputSha256": daily_input["sha256"], "expectedTasks": len(plan["tasks"]),
            "tasks": tasks, "tasksComplete": complete, "archiveIntegrityPass": valid,
            "captureReady": ready, "problems": problems, "sourceIdentities": sources,
            "normalizationVersion": NORMALIZATION_VERSION, **responses,
            "ledgerReady": False, "investorTaxVerified": False,
            "scope": "single-snapshot same-source archive checks; not independent source coverage or economic P&L"}


def _problem(problems: dict, reason: str, detail: object) -> None:
    problems["counts"][reason] += 1
    if len(problems["examples"]) < 20:
        problems["examples"].append({"reason": reason, "detail": detail})


def _object(raw: str) -> dict:
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("expected a JSON object")
    return value


def _check_scope(scope, plan: dict, problems: dict) -> None:
    try:
        if scope is None or scope["scope_sha256"] != plan["scopeSha256"] or _object(scope["plan_json"]) != plan:
            raise ValueError("stored scope differs from the current lifecycle plan")
    except (ValueError, TypeError) as error:
        _problem(problems, "scope_mismatch", str(error))


def _audit_tasks(connection, plan: dict, problems: dict) -> dict:
    rows = connection.execute("SELECT code,year,status FROM action_tasks ORDER BY code,year").fetchall()
    expected = {(task["code"], task["year"]) for task in plan["tasks"]}
    actual = {(row["code"], row["year"]) for row in rows}
    if len(expected) != len(plan["tasks"]) or not expected:
        _problem(problems, "invalid_expected_plan", "empty or duplicate expected tasks")
    for identity in sorted(expected - actual):
        _problem(problems, "missing_planned_task", identity)
    for identity in sorted(actual - expected):
        _problem(problems, "unexpected_task", identity)
    return dict(Counter(row["status"] for row in rows))


def _audit_runs(connection, scope_sha: str, daily_input: dict, problems: dict) -> list[dict]:
    identities = Counter()
    for row in connection.execute("SELECT * FROM action_runs ORDER BY started_at,run_id"):
        try:
            data = _object(row["input_evidence_json"])
            identity = data["sourceIdentity"]
            if data["scopeSha256"] != scope_sha or data["dailyInput"]["sha256"] != daily_input["sha256"]:
                raise ValueError("run references different source scope or daily panel")
            if identity["provider"] != "BaoStock" or not isinstance(identity["providerVersion"], str) or not identity["providerVersion"]:
                raise ValueError("missing source identity")
            if not re.fullmatch(r"[0-9a-f]{64}", identity["adapterSha256"]):
                raise ValueError("invalid source adapter fingerprint")
            identities[json.dumps(identity, sort_keys=True)] += 1
            if row["status"] not in {"running", "finished", "failed", "interrupted"}:
                raise ValueError("unknown run state")
            if (row["status"] == "running") != (row["completed_at"] is None):
                raise ValueError("run state and completion timestamp disagree")
        except (ValueError, TypeError, KeyError) as error:
            _problem(problems, "run_provenance", {"runId": row["run_id"], "error": str(error)})
    return [{"identity": json.loads(key), "runs": count} for key, count in sorted(identities.items())]


def _audit_ownership(connection, problems: dict) -> None:
    checks = {
        "task_request_ownership": """SELECT t.code,t.year FROM action_tasks t LEFT JOIN action_requests r
            ON r.request_id=t.active_request_id WHERE
            (t.status='pending' AND (t.attempts!=0 OR t.active_request_id IS NOT NULL)) OR
            (t.status!='pending' AND (r.request_id IS NULL OR r.code!=t.code OR r.year!=t.year OR
            r.attempt!=t.attempts OR (t.status='succeeded' AND r.status!='succeeded') OR
            (t.status='running' AND r.status!='running') OR (t.status='failed' AND r.status NOT IN ('failed','interrupted'))))""",
        "attempt_history": """SELECT t.code,t.year FROM action_tasks t WHERE
            t.attempts!=(SELECT COUNT(*) FROM action_requests r WHERE r.code=t.code AND r.year=t.year) OR
            (t.attempts>0 AND (t.attempts!=(SELECT MAX(attempt) FROM action_requests r WHERE r.code=t.code AND r.year=t.year)
            OR 1!=(SELECT MIN(attempt) FROM action_requests r WHERE r.code=t.code AND r.year=t.year)))""",
        "multiple_successes": """SELECT code,year FROM action_requests WHERE status='succeeded'
            GROUP BY code,year HAVING COUNT(*)>1""",
        "unowned_success": """SELECT r.code,r.year FROM action_requests r JOIN action_tasks t USING(code,year)
            WHERE r.status='succeeded' AND (t.status!='succeeded' OR t.active_request_id IS NOT r.request_id)""",
        "invalid_request_state": """SELECT code,year FROM action_requests WHERE
            status NOT IN ('running','succeeded','failed','interrupted') OR
            (status='running' AND completed_at IS NOT NULL) OR (status!='running' AND completed_at IS NULL)""",
        "events_without_success": """SELECT e.code,e.ex_date FROM action_events e JOIN action_requests r USING(request_id)
            WHERE r.status!='succeeded'""",
    }
    for reason, query in checks.items():
        for row in connection.execute(query):
            _problem(problems, reason, list(row))


def _audit_responses(connection, plan: dict, problems: dict) -> dict:
    stored = defaultdict(list)
    for row in connection.execute("SELECT * FROM action_events ORDER BY request_id,row_index"):
        stored[row["request_id"]].append(dict(row))
    issues, coverage, counters = Counter(), Counter(), Counter()
    fingerprint = hashlib.sha256()
    for row in connection.execute("SELECT * FROM action_requests ORDER BY code,year,attempt"):
        counters["requests"] += 1
        coverage[f"{row['year']}:{row['status']}"] += 1
        identity = [row[key] for key in ("request_id", "code", "year", "attempt", "status", "raw_sha256", "row_count")]
        fingerprint.update(json.dumps(identity, separators=(",", ":")).encode() + b"\n")
        if row["status"] != "succeeded":
            continue
        events = _check_response(row, stored[row["request_id"]], problems, counters)
        if events is None:
            continue
        counters["rawResponsesChecked"] += 1
        counters["queriedEmptyYears"] += int(not events)
        counters["sourceEvents"] += len(events)
        for event in events:
            issues.update(event["issues"])
            if event["ex_date"] and not plan["start"] <= event["ex_date"] <= plan["end"]:
                counters["eventsOutsideStudyDates"] += 1
    return {"counts": dict(counters), "yearRequestStates": dict(coverage), "requestIndexSha256": fingerprint.hexdigest(),
            "unresolvedFieldCounts": dict(issues),
            "legacyProjectionPolicy": "retained historical bytes are not certified or consumed; reparse checked raw source"}


def _check_response(row, stored: list[dict], problems: dict, counters: Counter) -> list[dict] | None:
    try:
        raw_json = row["raw_json"]
        if not isinstance(raw_json, str) or hashlib.sha256(raw_json.encode()).hexdigest() != row["raw_sha256"]:
            raise ValueError("raw response fingerprint mismatch")
        raw = _object(raw_json)
        if set(raw) != {"fields", "request", "rows"} or not isinstance(raw["rows"], list):
            raise ValueError("invalid raw response envelope")
        if any(set(record) != set(raw["fields"]) for record in raw["rows"]):
            raise ValueError("raw row fields differ from response schema")
        frame = pd.DataFrame(raw["rows"], columns=raw["fields"])
        frame.attrs["request"] = raw["request"]
        _, events = normalize_response(frame, row["code"], row["year"])
        if len(events) != row["row_count"]:
            raise ValueError("raw and recorded row counts differ")
        _check_projections(row["request_id"], events, stored, problems, counters)
        return events
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        _problem(problems, "raw_response_invalid", {"requestId": row["request_id"], "error": str(error)})
        return None


def _check_projections(request_id: str, events: list[dict], stored: list[dict], problems: dict, counters: Counter) -> None:
    if [row["row_index"] for row in stored] != list(range(len(events))):
        _problem(problems, "projection_row_indices", request_id)
        return
    for expected, row in zip(events, stored):
        try:
            original = _object(row["normalized_json"])
            if row["code"] != expected["code"] or row["ex_date"] != expected["ex_date"]:
                raise ValueError("derived row identity mismatch")
            if row["ledger_ready"] != 0 or original.get("ledger_ready") is not False or original.get("investor_tax_verified") is not False:
                raise ValueError("source archive cannot certify ledger or investor-tax readiness")
            version = original.get("normalization_version")
            if version is None:
                counters["legacyProjectionsUnchecked"] += 1
            elif version != NORMALIZATION_VERSION or original != expected:
                raise ValueError("stored current projection differs from raw re-normalization")
            else:
                counters["currentProjectionsChecked"] += 1
        except (ValueError, TypeError) as error:
            _problem(problems, "projection_invalid", {"requestId": request_id, "row": row["row_index"], "error": str(error)})
