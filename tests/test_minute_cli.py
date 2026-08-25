from qforge.minute.cli import _summary


def test_status_summary_preserves_raw_database_fields() -> None:
    payload = {"barCount": 116_160, "symbolCount": 10, "tradeDays": 242}

    assert _summary(payload) == payload
