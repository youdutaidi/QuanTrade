"""Trading-calendar coverage contracts; never invent missing market rows."""

from __future__ import annotations

import sqlite3

import pandas as pd


def validate_daily_coverage(
    connection: sqlite3.Connection, frame: pd.DataFrame, code: str, start: str, end: str,
) -> None:
    rows = connection.execute(
        """SELECT c.calendar_date FROM trade_calendar c JOIN securities s ON s.code=?
        WHERE c.is_trading_day=1 AND c.calendar_date BETWEEN ? AND ?
        AND c.calendar_date>=s.ipo_date AND (s.out_date IS NULL OR c.calendar_date<s.out_date)""",
        (code, start, end),
    ).fetchall()
    expected = {str(row[0]) for row in rows}
    actual = set(frame["trade_date"].astype(str)) if not frame.empty else set()
    missing = sorted(expected - actual)
    if missing:
        raise ValueError(f"Incomplete daily response for {code}: {len(missing)} missing dates; first={missing[:3]}")


def audit_daily_coverage(connection: sqlite3.Connection, adjustflag: int) -> dict[str, object]:
    # BaoStock sometimes retains a suspended row on out_date and sometimes
    # omits it. Neither is an executable trading day; all earlier days must exist.
    rows = connection.execute(
        """SELECT t.task_key,t.code,COUNT(*) expected_rows,
        SUM(CASE WHEN b.code IS NULL THEN 1 ELSE 0 END) missing_rows,
        MIN(CASE WHEN b.code IS NULL THEN c.calendar_date END) first_missing_date
        FROM market_download_tasks t JOIN securities s ON s.code=t.code
        JOIN trade_calendar c ON c.is_trading_day=1
          AND c.calendar_date BETWEEN t.start_date AND t.end_date
          AND c.calendar_date>=s.ipo_date AND (s.out_date IS NULL OR c.calendar_date<s.out_date)
        LEFT JOIN daily_bars b ON b.code=t.code AND b.trade_date=c.calendar_date AND b.adjustflag=?
        WHERE t.task_type='daily' AND t.status='succeeded'
        GROUP BY t.task_key,t.code ORDER BY t.code""",
        (adjustflag,),
    ).fetchall()
    mismatches = [dict(row) for row in rows if row["missing_rows"]]
    boundary = connection.execute(
        """SELECT COUNT(*) FROM daily_bars b JOIN securities s ON s.code=b.code
        WHERE b.trade_date=s.out_date AND b.trade_status=0 AND b.adjustflag=?""", (adjustflag,),
    ).fetchone()[0]
    return {
        "successfulTasksChecked": len(rows),
        "expectedRows": sum(row["expected_rows"] for row in rows),
        "missingRows": sum(row["missing_rows"] for row in rows),
        "tasksWithMissingDates": len(mismatches),
        "examples": mismatches[:20],
        "optionalSuspendedDelistingRows": int(boundary),
        "boundaryRule": "IPO inclusive; delisting date exclusive; raw suspended boundary rows retained",
        "pass": bool(rows) and not mismatches,
    }
