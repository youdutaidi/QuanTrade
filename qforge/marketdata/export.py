"""Atomic, bounded-memory writing of derived research panels."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


def write_panel_chunks(
    chunks: Iterator[pd.DataFrame], output_path: str | Path, metadata: dict[str, str],
) -> dict[str, object]:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    first = next(chunks, None)
    if first is None or first.empty:
        raise ValueError("cannot export an empty research panel")
    schema = pa.schema([
        (column, pa.timestamp("ns") if column == "date" else pa.string() if column == "symbol" else pa.float64())
        for column in first.columns
    ], metadata={key.encode(): value.encode() for key, value in metadata.items()})
    with TemporaryDirectory(prefix=f".{output.name}-", dir=output.parent) as staging:
        staged = Path(staging) / "panel.parquet"
        with pq.ParquetWriter(staged, schema, compression="zstd") as writer:
            stats = _write_frames(writer, schema, first, chunks)
        if pq.read_metadata(staged).num_rows != stats["rows"]:
            raise ValueError("exported Parquet row count differs from input")
        staged.replace(output)
    return {"output": str(output), **stats, "bytes": output.stat().st_size, "sha256": file_sha256(output)}


def _write_frames(writer, schema, first: pd.DataFrame, rest: Iterator[pd.DataFrame]) -> dict[str, object]:
    from itertools import chain

    rows = batches = 0
    symbols: set[str] = set()
    first_day = last_day = None
    for frame in chain([first], rest):
        if frame.empty:
            continue
        writer.write_table(pa.Table.from_pandas(frame, schema=schema, preserve_index=False))
        rows += len(frame)
        batches += 1
        symbols.update(frame["symbol"].unique())
        low, high = frame["date"].min(), frame["date"].max()
        first_day = low if first_day is None else min(first_day, low)
        last_day = high if last_day is None else max(last_day, high)
    return {
        "rows": rows, "symbols": len(symbols), "batches": batches,
        "firstDate": str(first_day.date()), "lastDate": str(last_day.date()),
    }


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
