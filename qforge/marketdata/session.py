"""Process-level exclusion for the anonymous BaoStock socket session."""

from __future__ import annotations

import fcntl
import os
import tempfile
from pathlib import Path


class FileLock:
    """Nonblocking advisory lock; the OS releases it when a process exits."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._handle = None

    def __enter__(self) -> "FileLock":
        if self._handle is not None:
            raise RuntimeError(f"lock already held: {self.path}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            handle.close()
            raise RuntimeError(f"another process holds the lock: {self.path}") from None
        self._handle = handle
        return self

    def __exit__(self, *_: object) -> None:
        if self._handle is not None:
            try:
                fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
            finally:
                self._handle.close()
                self._handle = None


def baostock_session_lock() -> FileLock:
    return FileLock(Path(tempfile.gettempdir()) / f"qforge-baostock-{os.getuid()}.lock")
