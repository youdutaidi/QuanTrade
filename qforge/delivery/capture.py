"""Consistent per-database backups and a fixed, project-local data allowlist."""

from __future__ import annotations

import io
import json
import os
import sqlite3
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from ..marketdata.export import file_sha256


SOURCE_ROOTS = ("research/data", "research/source", "research/output", "research/demo", "research/evidence")
MANIFEST_NAME = "_snapshot_manifest.json"


def create_snapshot(root: Path, output: Path, code_identity: str, label: str) -> dict:
    root, output = root.resolve(), output.resolve()
    validate_destination(root, output)
    sources, excluded = selected_files(root)
    if not sources:
        raise ValueError("no project data found in the snapshot allowlist")
    output.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    with TemporaryDirectory(prefix=".staging-", dir=output) as temporary:
        staging = Path(temporary)
        entries = []
        for index, source in enumerate(sources):
            entry = capture_file(source, staging / source.relative_to(root))
            entries.append({"path": source.relative_to(root).as_posix(), **entry})
            if entry["kind"] == "sqlite-backup" or (index + 1) % 25 == 0:
                print(json.dumps({"capturedFiles": index + 1, "totalFiles": len(sources), "path": entries[-1]["path"]}), flush=True)
        manifest = {"version": 1, "label": label, "codeCommit": code_identity, "startedAt": started,
                    "capturedAt": datetime.now(timezone.utc).isoformat(), "files": entries, "excluded": excluded,
                    "claim": "byte-verifiable in-progress snapshot; no data-completeness or strategy admission; databases captured separately"}
        print(json.dumps({"state": "compressing", "files": len(entries)}), flush=True)
        bundle = write_bundle(staging, output, manifest)
    result = {"state": "captured-not-yet-verified", "bundle": str(bundle), "sha256": file_sha256(bundle),
              "bytes": bundle.stat().st_size, "fileCount": len(entries), "codeCommit": code_identity}
    (output / "delivery.json").write_text(json.dumps({**result, "bundle": bundle.name}, indent=2) + "\n", encoding="utf-8")
    return result


def validate_destination(root: Path, output: Path) -> None:
    if output == root or output in root.parents:
        raise ValueError("snapshot output cannot be the project root or its ancestor")
    delivery = root / "research/output/delivery"
    if output != delivery and delivery not in output.parents:
        for relative in SOURCE_ROOTS:
            source = root / relative
            if output == source or source in output.parents:
                raise ValueError("snapshot output would enter the data allowlist recursively")


def selected_files(root: Path) -> tuple[list[Path], list[dict]]:
    files, excluded = [], []
    for relative in SOURCE_ROOTS:
        base = root / relative
        if base.is_symlink():
            raise ValueError(f"symlink source root is not allowed: {relative}")
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            rel = path.relative_to(root)
            if rel.parts[:3] == ("research", "output", "delivery"):
                continue
            if path.is_symlink():
                raise ValueError(f"symlink is not allowed in a snapshot: {rel}")
            if not path.is_file():
                continue
            reason = excluded_reason(path)
            if reason:
                excluded.append({"path": rel.as_posix(), "reason": reason})
            else:
                files.append(path)
    return files, excluded


def excluded_reason(path: Path) -> str | None:
    if "yf_cache" in path.parts:
        return "Yahoo provider session/timezone cache, not the downloaded price archive"
    if path.name.lower() in {"cookies.db", "cookies.sqlite", "cookies.sqlite3", "cookies.json", "cookies.txt",
                             "credentials.json", "token.json", "auth.json", ".netrc"}:
        return "credential or session-cookie cache is never included"
    if path.name.endswith(("-wal", "-shm", "-journal", ".lock")):
        return "transient sidecar; committed SQLite content is captured through online backup"
    if path.name == ".DS_Store" or "__pycache__" in path.parts:
        return "operating-system or interpreter cache"
    if path.name.startswith(".env") or path.suffix.lower() in {".pem", ".key"}:
        return "credential-like filename is never included"
    return None


def capture_file(source: Path, target: Path) -> dict:
    target.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as stream:
        is_database = stream.read(16) == b"SQLite format 3\0"
    if source.suffix in {".sqlite", ".sqlite3", ".db"} and not is_database:
        raise ValueError(f"database-named source is not a valid SQLite file: {source}")
    if is_database:
        backup_sqlite(source, target)
        detail = {"kind": "sqlite-backup", "sqlite": database_inventory(target)}
    else:
        detail = {"kind": "stable-file-copy", **copy_stable(source, target)}
    return {**detail, "bytes": target.stat().st_size, "sha256": file_sha256(target),
            "capturedAt": datetime.now(timezone.utc).isoformat()}


def backup_sqlite(source: Path, target: Path) -> None:
    if target.exists():
        raise FileExistsError(target)
    deadline = time.monotonic() + 120
    def progress(_status, _remaining, _total):
        if time.monotonic() > deadline:
            raise TimeoutError("SQLite online backup exceeded its 120-second deadline")
    origin = sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True, timeout=30)
    destination = sqlite3.connect(target)
    try:
        origin.backup(destination, pages=4096, progress=progress, sleep=0.05)
        destination.execute("PRAGMA journal_mode=DELETE")
    finally:
        destination.close()
        origin.close()


def database_inventory(path: Path) -> dict:
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        integrity = [row[0] for row in connection.execute("PRAGMA integrity_check")]
        if integrity != ["ok"] or connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise ValueError("snapshot SQLite integrity or foreign-key check failed")
        tables = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        counts = {}
        for table in tables:
            quoted = '"' + table.replace('"', '""') + '"'
            counts[table] = connection.execute(f"SELECT COUNT(*) FROM {quoted}").fetchone()[0]
        return {"integrity": "ok", "tableRows": counts}
    finally:
        connection.close()


def copy_stable(source: Path, target: Path) -> dict:
    with source.open("rb") as origin, target.open("xb") as destination:
        before = os.fstat(origin.fileno())
        remaining = before.st_size
        while remaining:
            block = origin.read(min(8 * 1024 * 1024, remaining))
            if not block:
                raise ValueError(f"source shrank while capturing: {source}")
            destination.write(block)
            remaining -= len(block)
        after = os.fstat(origin.fileno())
    changed = before.st_mtime_ns != after.st_mtime_ns or before.st_size != after.st_size
    if changed:
        raise ValueError(f"source changed during capture; retry with a new output: {source}")
    return {"sourceBytes": before.st_size, "sourceMtimeNs": before.st_mtime_ns}


def write_bundle(staging: Path, output: Path, manifest: dict) -> Path:
    encoded = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    (output / "manifest.json").write_bytes(encoded)
    temporary, final = output / "quant-data.tar.gz.incomplete", output / "quant-data.tar.gz"
    with tarfile.open(temporary, "w:gz", compresslevel=6) as archive:
        info = tarfile.TarInfo(MANIFEST_NAME)
        info.size, info.mode = len(encoded), 0o644
        archive.addfile(info, io.BytesIO(encoded))
        for entry in manifest["files"]:
            archive.add(staging / entry["path"], arcname=entry["path"], recursive=False, filter=_portable_member)
    temporary.replace(final)
    return final


def _portable_member(member: tarfile.TarInfo) -> tarfile.TarInfo:
    member.uid = member.gid = 0
    member.uname = member.gname = ""
    member.mode = 0o644
    return member
