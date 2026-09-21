"""summary_scores and threshold_check must reject invalid measurements
rather than invent zeros or pass invalid comparisons.
"""

import math
import pytest
from evalquill import summary_scores, threshold_check


# A missing score must not be averaged as zero.
def test_missing_metric_in_one_row_rejected():
    with pytest.raises(ValueError, match="metric"):
        summary_scores([{"scores": {"m": 1.0}}, {"scores": {}}])


def test_different_metric_sets_rejected():
    with pytest.raises(ValueError, match="metric"):
        summary_scores([{"scores": {"a": 1.0}}, {"scores": {"b": 1.0}}])


@pytest.mark.parametrize("bad", [math.nan, math.inf, 2.0, -0.1, True, None, "1"])
def test_invalid_score_rejected(bad):
    with pytest.raises(ValueError):
        summary_scores([{"scores": {"m": 1.0}}, {"scores": {"m": bad}}])


def test_row_without_scores_rejected():
    with pytest.raises(ValueError, match="scores"):
        summary_scores([{"scores": {"m": 1.0}}, {"id": "x"}])


def test_valid_rows_still_average_at_full_precision():
    rows = [{"scores": {"m": 0.798}}, {"scores": {"m": 0.8}}, {"scores": {"m": 0.8}}]
    assert summary_scores(rows)["m"] == pytest.approx(0.7993333333333333)


@pytest.mark.parametrize("bad", [-1.0, 1.5, math.nan, True, "0.8", None])
def test_invalid_threshold_rejected(bad):
    with pytest.raises(ValueError):
        threshold_check({"m": 0.9}, {"m": bad})


@pytest.mark.parametrize("bad", [2.0, -0.1, math.nan, True])
def test_invalid_summary_value_rejected(bad):
    with pytest.raises(ValueError):
        threshold_check({"m": bad}, {"m": 0.5})


def test_not_run_is_preserved():
    assert threshold_check({}, {"m": 0.5}) == {"m": "NOT RUN"}


def test_boundary_still_passes():
    assert threshold_check({"m": 0.8}, {"m": 0.8}) == {"m": "PASS"}
