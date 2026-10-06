import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.service import ReturnsOptimizationService  # noqa: E402


@pytest.fixture(scope="session")
def service() -> ReturnsOptimizationService:
    return ReturnsOptimizationService()
