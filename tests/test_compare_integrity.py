"""Comparison contract: only responses and scores may differ between runs.

Reproduces failures from the independent review (F1, and the compare-side
parts of F2).
"""

import math
import pytest
from evalquill.compare import compare, diff_summary


def row(case_id, response, scores, prompt="q", expected="a"):
    return {"id": case_id, "prompt": prompt, "expected": expected,
            "response": response, "scores": scores}


# F1: changed reference answer must not look like an improvement.
def test_changed_expected_is_rejected():
    baseline = [row("c1", "yes", {"m": 0.0}, expected="no")]
    candidate = [row("c1", "yes", {"m": 1.0}, expected="yes")]
    with pytest.raises(ValueError, match="reference answer"):
        compare(baseline, candidate)


# F1: changed case input under the same id is a different test case.
def test_changed_input_is_rejected():
    baseline = [row("c1", "x", {"m": 1.0}, prompt="old ticket text")]
    candidate = [row("c1", "x", {"m": 1.0}, prompt="new ticket text")]
    with pytest.raises(ValueError, match="input"):
        compare(baseline, candidate)


# F2: same union of metric names, inconsistent per row. Previously KeyError.
def test_inconsistent_per_row_metrics_rejected():
    baseline = [row("a", "x", {"m1": 1.0, "m2": 1.0}), row("b", "y", {"m1": 1.0})]
    candidate = [row("a", "x", {"m1": 1.0}), row("b", "y", {"m1": 1.0, "m2": 1.0})]
    with pytest.raises(ValueError, match="metric"):
        compare(baseline, candidate)


@pytest.mark.parametrize("bad", [math.nan, math.inf, 1.5, -0.1, True, "1.0", None])
def test_invalid_scores_rejected(bad):
    baseline = [row("c1", "x", {"m": 1.0})]
    candidate = [row("c1", "x", {"m": bad})]
    with pytest.raises(ValueError):
        compare(baseline, candidate)


@pytest.mark.parametrize("field", ["id", "prompt", "expected", "response", "scores"])
def test_missing_field_rejected(field):
    good = row("c1", "x", {"m": 1.0})
    broken = dict(good)
    del broken[field]
    with pytest.raises(ValueError, match="missing"):
        compare([good], [broken])


def test_diff_is_a_snapshot():
    baseline = [row("c1", "x", {"m": 0.0})]
    candidate = [row("c1", "y", {"m": 1.0})]
    diff = compare(baseline, candidate)
    candidate[0]["scores"]["m"] = 0.0
    assert diff["cases"][0]["candidate_scores"]["m"] == 1.0


@pytest.mark.parametrize("bad", [1.5, -0.1, math.nan, True])
def test_invalid_pass_threshold_rejected(bad):
    diff = compare([row("c1", "x", {"m": 1.0})], [row("c1", "x", {"m": 1.0})])
    with pytest.raises(ValueError):
        diff_summary(diff, pass_threshold=bad)


def test_valid_comparison_still_works():
    baseline = [row("c1", "x", {"m": 0.0}), row("c2", "y", {"m": 1.0})]
    candidate = [row("c1", "x2", {"m": 1.0}), row("c2", "y2", {"m": 0.0})]
    summary = diff_summary(compare(baseline, candidate))
    assert summary["m"]["improved"] == ["c1"]
    assert summary["m"]["newly_failing"] == ["c2"]
