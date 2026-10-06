import pytest

from src.agents import ReturnsIntelligenceAgent
from src.forecasting import WARNING, ForecastingService


@pytest.fixture(scope="module")
def fc():
    return ForecastingService(ReturnsIntelligenceAgent())


def test_compatibility_demo_values(fc):
    r = fc.forecast("COMPATIBILITY", "compat_checker", 100)
    assert r.prevented_returns.expected == 20
    assert (r.prevented_returns.low, r.prevented_returns.high) == (12, 25)
    assert r.recommended_validation == "Two-week randomized A/B test"


@pytest.mark.parametrize("cause,iid", [("COMPATIBILITY", "device_model_confirmation"),
                                       ("DAMAGED", "offer_replacement"), ("FIT_TOO_SMALL", "runs_small_warning"),
                                       ("OTHER", "manual_review")])
@pytest.mark.parametrize("volume", [1, 7, 100, 1000])
def test_ordering_and_bounds(fc, cause, iid, volume):
    p = fc.forecast(cause, iid, volume).prevented_returns
    assert 0 <= p.low <= p.expected <= p.high <= volume


def test_zero_volume(fc):
    p = fc.forecast("COMPATIBILITY", "compat_checker", 0).prevented_returns
    assert (p.low, p.expected, p.high) == (0, 0, 0)


@pytest.mark.parametrize("bad", [-1, -100, 2.5, "100", True])
def test_invalid_volume_rejected(fc, bad):
    with pytest.raises(ValueError):
        fc.forecast("COMPATIBILITY", "compat_checker", bad)


def test_unknown_inputs_rejected(fc):
    with pytest.raises(ValueError):
        fc.forecast("NOT_A_CAUSE", "compat_checker", 10)
    with pytest.raises(ValueError):
        fc.forecast("COMPATIBILITY", "offer_replacement", 10)
    with pytest.raises(ValueError):
        fc.forecast("COMPATIBILITY", "compat_checker", 10, implementation_cost="Huge")


def test_warning_present(fc):
    assert fc.forecast("COMPATIBILITY", "compat_checker", 100).warning == WARNING


def test_custom_duration(fc):
    r = fc.forecast("COMPATIBILITY", "compat_checker", 100, test_duration_days=28)
    assert r.test_duration_days == 28 and "28-day" in r.recommended_validation
