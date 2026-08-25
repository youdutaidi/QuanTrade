from qforge.config import BacktestConfig
from qforge.demo import create_demo
from qforge.pipeline import run_experiment


def test_demo_pipeline_writes_all_reports(tmp_path) -> None:
    config_path = create_demo(tmp_path)
    config = BacktestConfig.from_json(config_path)
    payload = run_experiment(config, tmp_path)
    assert payload["factorCount"] == 6
    assert len(payload["ranking"]) == 6
    assert all((tmp_path / path).exists() if not path.startswith("/") else __import__("pathlib").Path(path).exists() for path in payload["artifacts"].values())
    assert payload["gates"][1]["status"] == "fail"
