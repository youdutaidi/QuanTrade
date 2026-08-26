from types import SimpleNamespace
import subprocess
import sys

import pytest

from qforge.marketdata.provider import BaoStockMarketProvider
from qforge.marketdata.session import FileLock
from qforge.minute.provider import BaoStockProvider


def test_lock_excludes_second_handle_and_releases_on_error(tmp_path):
    path = tmp_path / "source.lock"
    with pytest.raises(ValueError):
        with FileLock(path):
            with pytest.raises(RuntimeError, match="another process"):
                with FileLock(path):
                    pytest.fail("second holder admitted")
            raise ValueError("interrupted")
    with FileLock(path):
        pass


@pytest.mark.parametrize("provider_type", [BaoStockMarketProvider, BaoStockProvider])
def test_login_failure_releases_lock(provider_type, tmp_path, monkeypatch):
    monkeypatch.setattr("qforge.marketdata.provider.time.sleep", lambda _: None)
    module = SimpleNamespace(login=lambda: SimpleNamespace(error_code="1", error_msg="fixture"))
    provider = provider_type(module=module)
    provider.session_lock = FileLock(tmp_path / "login.lock")
    with pytest.raises(RuntimeError, match="login failed"):
        with provider:
            pytest.fail("failed login admitted")
    with FileLock(tmp_path / "login.lock"):
        pass


def test_minute_and_daily_share_lock_before_login(tmp_path):
    called = []
    module = SimpleNamespace(login=lambda: (called.append("login") or SimpleNamespace(error_code="0")),
                             logout=lambda: called.append("logout"))
    daily, minute = BaoStockMarketProvider(module=module), BaoStockProvider(module=module)
    path = tmp_path / "shared.lock"
    daily.session_lock, minute.session_lock = FileLock(path), FileLock(path)
    with daily:
        with pytest.raises(RuntimeError, match="another process"):
            with minute:
                pytest.fail("concurrent minute session admitted")
    assert called == ["login", "logout"]


def test_logout_failure_still_releases_lock(tmp_path):
    def fail_logout():
        raise OSError("logout failed")
    module = SimpleNamespace(login=lambda: SimpleNamespace(error_code="0"), logout=fail_logout)
    provider = BaoStockMarketProvider(module=module)
    provider.session_lock = FileLock(tmp_path / "logout.lock")
    with pytest.raises(OSError, match="logout failed"):
        with provider:
            pass
    with FileLock(tmp_path / "logout.lock"):
        pass


def test_exclusion_across_processes(tmp_path):
    path = tmp_path / "process.lock"
    script = "from qforge.marketdata.session import FileLock\nwith FileLock(" + repr(str(path)) + "):\n pass\n"
    with FileLock(path):
        result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=10)
    assert result.returncode != 0 and "another process" in result.stderr
    released = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=10)
    assert released.returncode == 0
