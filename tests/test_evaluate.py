import pytest
from evalquill import evaluate, evaluate_dataset, summary_scores, threshold_check
from evalquill.metrics import normalized_exact_match, contains_substring
from evalquill.llm import mock_llm


# evaluate() tests
def test_evaluate_exact_match_pass():
    result = evaluate("What is 2+2?", "4", "4", [normalized_exact_match])
    assert result["normalized_exact_match"] == 1.0

def test_evaluate_exact_match_fail():
    result = evaluate("What is 2+2?", "4", "5", [normalized_exact_match])
    assert result["normalized_exact_match"] == 0.0

def test_evaluate_multiple_metrics():
    result = evaluate("What is 2+2?", "4", "The answer is 4.", [normalized_exact_match, contains_substring])
    assert result["normalized_exact_match"] == 0.0
    assert result["contains_substring"] == 1.0


# summary_scores() tests
def test_summary_scores_empty():
    assert summary_scores([]) == {}

def test_summary_scores_averaging():
    results = [
        {"scores": {"normalized_exact_match": 0.0}},
        {"scores": {"normalized_exact_match": 1.0}},
    ]
    assert summary_scores(results)["normalized_exact_match"] == 0.5


# threshold_check() tests
def test_threshold_pass():
    summary = {"contains_substring": 1.0}
    result = threshold_check(summary, {"contains_substring": 0.8})
    assert result["contains_substring"] == "PASS"

def test_threshold_fail():
    summary = {"normalized_exact_match": 0.0}
    result = threshold_check(summary, {"normalized_exact_match": 0.5})
    assert result["normalized_exact_match"] == "FAIL"

def test_threshold_not_run():
    summary = {}
    result = threshold_check(summary, {"normalized_exact_match": 0.5})
    assert result["normalized_exact_match"] == "NOT RUN"

def test_rounding_bug_regression():
    results = [
        {"scores": {"normalized_exact_match": 1.0}},
        {"scores": {"normalized_exact_match": 1.0}},
        {"scores": {"normalized_exact_match": 0.0}},
        {"scores": {"normalized_exact_match": 0.797}},
    ]
    summary = summary_scores(results)
    check = threshold_check(summary, {"normalized_exact_match": 0.80})
    assert check["normalized_exact_match"] == "FAIL"

def test_rounding_false_pass_regression():
    # true average is 0.7993... — must FAIL against 0.80 threshold
    results = [
        {"scores": {"normalized_exact_match": 0.798}},
        {"scores": {"normalized_exact_match": 0.800}},
        {"scores": {"normalized_exact_match": 0.800}},
    ]
    summary = summary_scores(results)
    check = threshold_check(summary, {"normalized_exact_match": 0.80})
    assert check["normalized_exact_match"] == "FAIL"

def test_rounding_exact_boundary_passes():
    # exactly 0.80 must PASS
    results = [
        {"scores": {"normalized_exact_match": 0.80}},
        {"scores": {"normalized_exact_match": 0.80}},
        {"scores": {"normalized_exact_match": 0.80}},
    ]
    summary = summary_scores(results)
    check = threshold_check(summary, {"normalized_exact_match": 0.80})
    assert check["normalized_exact_match"] == "PASS"
def test_duplicate_metric_names_rejected():
    with pytest.raises(ValueError, match="Duplicate metric name"):
        evaluate("q", "a", "a", [normalized_exact_match, normalized_exact_match])

def test_score_rejects_boolean():
    def bad_metric(response, expected):
        return True
    with pytest.raises(ValueError, match="float, not a boolean"):
        evaluate("q", "a", "a", [bad_metric])

def test_score_rejects_nan():
    import math
    def bad_metric(response, expected):
        return math.nan
    with pytest.raises(ValueError, match="finite"):
        evaluate("q", "a", "a", [bad_metric])

def test_score_rejects_out_of_range():
    def bad_metric(response, expected):
        return 1.5
    with pytest.raises(ValueError, match="between 0 and 1"):
        evaluate("q", "a", "a", [bad_metric])

def test_metric_error_gives_useful_context():
    def crashing_metric(response, expected):
        raise RuntimeError("something went wrong")
    dataset = [{"prompt": "What is 2+2?", "expected": "4"}]
    with pytest.raises(RuntimeError, match="case .case_0."):
        evaluate_dataset(dataset, mock_llm, [crashing_metric])

def test_case_id_defaults_to_position():
    dataset = [{"prompt": "What is 2 + 2?", "expected": "4"}]
    results = evaluate_dataset(dataset, mock_llm, [contains_substring])
    assert results[0]["id"] == "case_0"

def test_case_id_uses_explicit_id():
    dataset = [{"id": "math_basic", "prompt": "What is 2 + 2?", "expected": "4"}]
    results = evaluate_dataset(dataset, mock_llm, [contains_substring])
    assert results[0]["id"] == "math_basic"

def test_duplicate_case_ids_rejected():
    dataset = [
        {"id": "dupe", "prompt": "What is 2 + 2?", "expected": "4"},
        {"id": "dupe", "prompt": "What is 7 + 2?", "expected": "9"},
    ]
    with pytest.raises(ValueError, match="Duplicate case id"):
        evaluate_dataset(dataset, mock_llm, [contains_substring])
