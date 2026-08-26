import pytest

from qforge.actions.planning import lifecycle_tasks


def security(code, ipo, out=None, kind="1", status="1"):
    return {"code": code, "ipo_date": ipo, "out_date": out, "security_type": kind, "current_status": status}


def test_lifecycle_plan_includes_delisted_and_empty_years_not_b_shares():
    securities = [security("sh.600000", "2019-01-01"), security("sz.000001", "2021-06-01", "2022-01-01", status="0"),
                  security("sh.900901", "2010-01-01"), security("sz.200001", "2010-01-01"),
                  security("sh.000300", "2010-01-01", kind="2"), security("sz.300001", "2024-01-01")]
    tasks = lifecycle_tasks(securities, "2020-08-25", "2022-08-24")
    assert tasks == [{"code": "sh.600000", "year": year} for year in (2020, 2021, 2022)] + [{"code": "sz.000001", "year": 2021}]


def test_lifecycle_requires_dates_and_unique_security_identity():
    with pytest.raises(ValueError, match="IPO date"):
        lifecycle_tasks([security("sh.600000", "")], "2020-01-01", "2021-01-01")
    row = security("sh.600000", "2019-01-01")
    with pytest.raises(ValueError, match="duplicate"):
        lifecycle_tasks([row, row], "2020-01-01", "2021-01-01")
