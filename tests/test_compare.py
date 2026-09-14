import pytest
from evalquill.compare import compare


def _result(case_id, response, scores, prompt="q", expected="a"):
    return {
        "id": case_id,
        "prompt": prompt,
        "expected": expected,
        "response": response,
        "scores": scores,
    }


def test_compare_detects_improvement():
    baseline = [_result("c1", "wrong", {"m": 0.0})]
    candidate = [_result("c1", "right", {"m": 1.0})]
    diff = compare(baseline, candidate)
    assert diff["cases"][0]["deltas"]["m"] == 1.0


def test_compare_detects_regression():
    baseline = [_result("c1", "right", {"m": 1.0})]
    candidate = [_result("c1", "wrong", {"m": 0.0})]
    diff = compare(baseline, candidate)
    assert diff["cases"][0]["deltas"]["m"] == -1.0


def test_compare_flags_response_change():
    baseline = [_result("c1", "old text", {"m": 1.0})]
    candidate = [_result("c1", "new text", {"m": 1.0})]
    diff = compare(baseline, candidate)
    assert diff["cases"][0]["response_changed"] is True


def test_compare_identical_response_not_changed():
    baseline = [_result("c1", "same", {"m": 1.0})]
    candidate = [_result("c1", "same", {"m": 1.0})]
    diff = compare(baseline, candidate)
    assert diff["cases"][0]["response_changed"] is False


def test_compare_matches_by_id_not_position():
    baseline = [_result("a", "x", {"m": 1.0}), _result("b", "y", {"m": 0.0})]
    candidate = [_result("b", "y", {"m": 0.0}), _result("a", "x", {"m": 1.0})]
    diff = compare(baseline, candidate)
    for case in diff["cases"]:
        assert case["deltas"]["m"] == 0.0


def test_compare_rejects_mismatched_cases():
    baseline = [_result("a", "x", {"m": 1.0})]
    candidate = [_result("b", "y", {"m": 1.0})]
    with pytest.raises(ValueError, match="different cases"):
        compare(baseline, candidate)


def test_compare_rejects_mismatched_metrics():
    baseline = [_result("a", "x", {"m1": 1.0})]
    candidate = [_result("a", "x", {"m2": 1.0})]
    with pytest.raises(ValueError, match="different metrics"):
        compare(baseline, candidate)


def test_compare_rejects_empty_run():
    with pytest.raises(ValueError, match="at least one case"):
        compare([], [_result("a", "x", {"m": 1.0})])


def test_compare_rejects_duplicate_ids_in_baseline():
    baseline = [_result("dupe", "x", {"m": 1.0}), _result("dupe", "y", {"m": 0.0})]
    candidate = [_result("dupe", "x", {"m": 1.0})]
    with pytest.raises(ValueError, match="Duplicate case id"):
        compare(baseline, candidate)