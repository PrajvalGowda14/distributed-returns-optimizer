import pytest

from src.classifier import ReturnCauseClassifier


@pytest.fixture(scope="module")
def clf():
    return ReturnCauseClassifier()


@pytest.mark.parametrize("text,expected", [
    ("does not fit my phone", "COMPATIBILITY"),
    ("wrong device model", "COMPATIBILITY"),
    ("shoe was too tight", "FIT_TOO_SMALL"),
    ("shirt was much too large", "FIT_TOO_LARGE"),
    ("sleeves are too long", "FIT_TOO_LARGE"),
    ("table looked larger online", "DIMENSION_MISMATCH"),
    ("color looked different", "EXPECTATION_MISMATCH"),
    ("could not connect Bluetooth", "SETUP_DIFFICULTY"),
    ("arrived cracked", "DAMAGED"),
    ("package was delayed", "DELIVERY_PROBLEM"),
    ("package was late", "DELIVERY_PROBLEM"),
])
def test_spec_examples(clf, text, expected):
    assert clf.classify("", text).cause == expected


def test_case_insensitive_and_combines_reason(clf):
    r = clf.classify("Incompatible with device", "THE CASE DOES NOT FIT MY PHONE.")
    assert r.cause == "COMPATIBILITY" and r.confidence == 0.90


def test_confidence_rules(clf):
    assert clf.classify("", "sleeves are too long").confidence == 0.80
    assert clf.classify("", "shoe was too tight").confidence == 0.90  # "too tight" + "tight"
    other = clf.classify("", "Caused a rash on my skin.")
    assert other.cause == "OTHER" and other.confidence == 0.50


def test_word_boundaries(clf):
    # "late" must not match inside "chocolate" or "plate".
    assert clf.classify("", "chocolate plate").cause == "OTHER"
