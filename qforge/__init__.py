"""Q-Forge factor research engine."""

from .config import BacktestConfig
from .factors import FACTORS, FactorSpec
from .pipeline import run_experiment

__all__ = ["BacktestConfig", "FACTORS", "FactorSpec", "run_experiment"]
__version__ = "0.1.0"

