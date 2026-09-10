import pytest
from evalquill.metrics import normalized_exact_match, contains_substring


# normalized_exact_match tests
def test_exact_match_pass():
    assert normalized_exact_match("Paris", "Paris") == 1.0

def test_exact_match_case_insensitive():
    assert normalized_exact_match("paris", "Paris") == 1.0

def test_exact_match_fail():
    assert normalized_exact_match("London", "Paris") == 0.0

def test_exact_match_whitespace():
    assert normalized_exact_match("  Paris  ", "Paris") == 1.0

def test_exact_match_empty_expected():
    with pytest.raises(ValueError):
        normalized_exact_match("Paris", "")


# contains_substring tests
def test_contains_substring_pass():
    assert contains_substring("The capital of France is Paris.", "Paris") == 1.0

def test_contains_substring_fail():
    assert contains_substring("The capital of France is Paris.", "London") == 0.0

def test_contains_substring_case_insensitive():
    assert contains_substring("The capital of France is Paris.", "paris") == 1.0

def test_contains_substring_empty_expected():
    with pytest.raises(ValueError):
        contains_substring("Paris", "")