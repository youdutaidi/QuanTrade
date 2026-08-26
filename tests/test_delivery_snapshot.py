import hashlib
import io
import json
import sqlite3
import tarfile
from pathlib import Path

import pytest

from qforge.delivery.capture import MANIFEST_NAME, create_snapshot
from qforge.delivery.recovery import restore_snapshot, verify_snapshot


def fixture_project(tmp_path):
    root = tmp_path / "project"
    data = root / "research/data"
    data.mkdir(parents=True)
    (data / "prices.csv").write_text("code,close\nsh.600000,10\n")
    return root


def test_live_wal_backup_is_complete_and_restore_is_non_overwriting(tmp_path):
    root = fixture_project(tmp_path)
    database = root / "research/data/market.sqlite"
    writer = sqlite3.connect(database)
    writer.execute("PRAGMA journal_mode=WAL")
    writer.execute("CREATE TABLE prices(value INTEGER)")
    writer.execute("INSERT INTO prices VALUES(10)")
    writer.commit()
    assert Path(str(database) + "-wal").stat().st_size > 0
    try:
        result = create_snapshot(root, tmp_path / "bundle", "a" * 40, "synthetic")
        writer.execute("INSERT INTO prices VALUES(20)")
        writer.commit()
        assert writer.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        bundle = Path(result["bundle"])
        assert verify_snapshot(bundle, result["sha256"])["fileCount"] == 2
        restored = restore_snapshot(bundle, result["sha256"], tmp_path / "restored")
        assert restored["databases"]["research/data/market.sqlite"]["tableRows"] == {"prices": 1}
        with sqlite3.connect(tmp_path / "restored/research/data/market.sqlite") as conn:
            assert conn.execute("SELECT value FROM prices").fetchall() == [(10,)]
        with pytest.raises(FileExistsError):
            restore_snapshot(bundle, result["sha256"], tmp_path / "restored")
        manifest = json.loads((tmp_path / "bundle/manifest.json").read_text())
        assert any(item["path"].endswith("-wal") for item in manifest["excluded"])
    finally:
        writer.close()


def test_allowlist_excludes_credentials_and_previous_delivery_bundles(tmp_path):
    root = fixture_project(tmp_path)
    (root / "research/data/.env").write_text("never-upload")
    old = root / "research/output/delivery/old"
    old.mkdir(parents=True)
    (old / "old.tar.gz").write_bytes(b"old snapshot")
    (root / "outside-secret.txt").write_text("not in allowlist")
    create_snapshot(root, root / "research/output/delivery/new", "a" * 40, "synthetic")
    manifest = json.loads((root / "research/output/delivery/new/manifest.json").read_text())
    assert [entry["path"] for entry in manifest["files"]] == ["research/data/prices.csv"]
    assert manifest["excluded"][0]["path"] == "research/data/.env"


def test_corruption_refuses_before_creating_restore_directory(tmp_path):
    root = fixture_project(tmp_path)
    result = create_snapshot(root, tmp_path / "bundle", "a" * 40, "synthetic")
    bundle = Path(result["bundle"])
    bundle.write_bytes(bundle.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="SHA256"):
        restore_snapshot(bundle, result["sha256"], tmp_path / "restored")
    assert not (tmp_path / "restored").exists()


def malicious_bundle(tmp_path, name, link=False, duplicate_manifest=False, content=b""):
    bundle = tmp_path / "unsafe.tar.gz"
    entry = {"path": name, "bytes": len(content), "sha256": hashlib.sha256(b"").hexdigest(), "kind": "stable-file-copy"}
    manifest = {"version": 1, "codeCommit": "a" * 40, "files": [entry]}
    with tarfile.open(bundle, "w:gz") as archive:
        body = json.dumps(manifest).encode()
        info = tarfile.TarInfo(MANIFEST_NAME)
        info.size = len(body)
        archive.addfile(info, io.BytesIO(body))
        if duplicate_manifest:
            archive.addfile(info, io.BytesIO(body))
        member = tarfile.TarInfo(name)
        member.size = len(content)
        if link:
            member.type, member.linkname = tarfile.SYMTYPE, "/tmp/outside"
        archive.addfile(member, io.BytesIO(content))
    return bundle, hashlib.sha256(bundle.read_bytes()).hexdigest()


@pytest.mark.parametrize("name,link,duplicate", [
    ("../../escaped", False, False), ("/tmp/escaped", False, False),
    ("research/data/link", True, False), ("research/data/safe", False, True),
    (".ssh/id_rsa", False, False),
])
def test_unsafe_archive_never_publishes_a_restore_tree(tmp_path, name, link, duplicate):
    bundle, fingerprint = malicious_bundle(tmp_path, name, link, duplicate)
    with pytest.raises(ValueError):
        restore_snapshot(bundle, fingerprint, tmp_path / "restored")
    assert not (tmp_path / "restored").exists()


def test_snapshot_refuses_recursive_destination_and_symlinks(tmp_path):
    root = fixture_project(tmp_path)
    with pytest.raises(ValueError, match="recursively"):
        create_snapshot(root, root / "research/data/snapshot", "a" * 40, "synthetic")
    (root / "research/data/link").symlink_to(root / "research/data/prices.csv")
    with pytest.raises(ValueError, match="symlink"):
        create_snapshot(root, tmp_path / "bundle", "a" * 40, "synthetic")


def test_member_corruption_detected_even_when_outer_archive_hash_is_updated(tmp_path):
    bundle, fingerprint = malicious_bundle(tmp_path, "research/data/corrupt.csv", content=b"x")
    with pytest.raises(ValueError, match="member SHA256 mismatch"):
        restore_snapshot(bundle, fingerprint, tmp_path / "restored")
    assert not (tmp_path / "restored").exists()
