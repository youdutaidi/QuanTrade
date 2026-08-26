"""Read-only verification and staged recovery into a previously absent folder."""

from __future__ import annotations

import hashlib
import json
import re
import tarfile
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory

from ..marketdata.export import file_sha256
from .capture import MANIFEST_NAME, SOURCE_ROOTS, database_inventory


def verify_snapshot(bundle: Path, expected_sha256: str) -> dict:
    check_bundle_hash(bundle, expected_sha256)
    manifest = inspect_stream(bundle, None)
    return {"state": "byte-verified", "sha256": expected_sha256, "fileCount": len(manifest["files"]),
            "codeCommit": manifest["codeCommit"], "claim": "archive integrity only; not market-data or strategy verification"}


def restore_snapshot(bundle: Path, expected_sha256: str, output: Path) -> dict:
    check_bundle_hash(bundle, expected_sha256)
    output = output.absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError("restore refuses an existing destination; choose a new directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".qforge-restore-", dir=output.parent) as temporary:
        staging = Path(temporary) / "restored"
        staging.mkdir()
        manifest = inspect_stream(bundle, staging)
        databases = {}
        for entry in manifest["files"]:
            if entry["kind"] == "sqlite-backup":
                inventory = database_inventory(staging / entry["path"])
                if inventory != entry["sqlite"]:
                    raise ValueError("restored SQLite inventory differs from snapshot manifest")
                databases[entry["path"]] = inventory
        if output.exists() or output.is_symlink():
            raise FileExistsError("restore target appeared during verification")
        staging.rename(output)
    return {"state": "restored-and-byte-verified", "output": str(output), "sha256": expected_sha256,
            "fileCount": len(manifest["files"]), "databases": databases, "codeCommit": manifest["codeCommit"],
            "claim": "recoverable data snapshot only; no strategy admission"}


def check_bundle_hash(bundle: Path, expected: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{64}", expected) or file_sha256(bundle) != expected:
        raise ValueError("archive SHA256 does not match the separately supplied fingerprint")


def inspect_stream(bundle: Path, destination: Path | None) -> dict:
    with tarfile.open(bundle, "r|gz") as archive:
        members = iter(archive)
        first = next(members, None)
        if first is None or first.name != MANIFEST_NAME or not first.isfile() or first.size > 32 * 1024 * 1024:
            raise ValueError("archive must begin with a bounded regular manifest file")
        manifest = json.load(archive.extractfile(first))
        expected = validate_manifest(manifest)
        seen = set()
        for member in members:
            if member.name not in expected or member.name in seen or not member.isfile():
                raise ValueError("unexpected, repeated or nonregular archive member")
            entry = expected[member.name]
            if member.size != entry["bytes"]:
                raise ValueError("archive member size mismatch")
            target = destination / member.name if destination else None
            fingerprint = consume_member(archive.extractfile(member), target)
            if fingerprint != entry["sha256"]:
                raise ValueError(f"archive member SHA256 mismatch: {member.name}")
            seen.add(member.name)
        if seen != set(expected):
            raise ValueError("archive is missing declared files")
    return manifest


def validate_manifest(manifest: dict) -> dict:
    if not isinstance(manifest, dict) or manifest.get("version") != 1 or not isinstance(manifest.get("files"), list):
        raise ValueError("unsupported archive manifest")
    expected = {}
    for entry in manifest["files"]:
        if not isinstance(entry, dict) or not {"path", "bytes", "sha256", "kind"} <= entry.keys():
            raise ValueError("incomplete archive file descriptor")
        name = entry["path"]
        if not isinstance(name, str) or entry["kind"] not in {"sqlite-backup", "stable-file-copy"}:
            raise ValueError("invalid archive file descriptor")
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != name or "\\" in name:
            raise ValueError("unsafe archive path")
        if not any(name.startswith(root + "/") for root in SOURCE_ROOTS) or name.startswith("research/output/delivery/"):
            raise ValueError("archive path is outside the data allowlist")
        if name in expected or type(entry["bytes"]) is not int or entry["bytes"] < 0:
            raise ValueError("duplicate archive path or invalid length")
        if not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]):
            raise ValueError("invalid member fingerprint")
        expected[name] = entry
    if not expected:
        raise ValueError("empty data manifest")
    return expected


def consume_member(stream, target: Path | None) -> str:
    digest = hashlib.sha256()
    destination = None
    try:
        if target is not None:
            target.parent.mkdir(parents=True, exist_ok=True)
            destination = target.open("xb")
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
            if destination is not None:
                destination.write(block)
    finally:
        if destination is not None:
            destination.close()
        stream.close()
    return digest.hexdigest()
