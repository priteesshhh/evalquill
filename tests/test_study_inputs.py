"""Case-study scripts must refuse incomplete or inconsistent inputs, with a
clear error and nonzero exit, before printing any conclusion.

Runs the scripts as subprocesses against a temporary copy of case_study/,
so real artifacts are never modified.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

CASE_STUDY = Path(__file__).parent.parent / "case_study"


@pytest.fixture
def study(tmp_path):
    shutil.copytree(CASE_STUDY, tmp_path / "case_study",
                    ignore=shutil.ignore_patterns("__pycache__"))
    return tmp_path


def run(study, script, *args):
    r = subprocess.run(
        [sys.executable, str(study / "case_study" / script), *args],
        capture_output=True, text=True, cwd=study,
    )
    return r.returncode, r.stdout, r.stderr


def runs(study):
    return study / "case_study" / "runs"


def edit(path, fn):
    data = json.loads(path.read_text(encoding="utf-8"))
    fn(data)
    path.write_text(json.dumps(data), encoding="utf-8")


def drop_case(case_id):
    return lambda d: d.update(results=[r for r in d["results"] if r["id"] != case_id])


def assert_clean_failure(code, out, err, keyword, conclusion_marker):
    assert code != 0, "expected a nonzero exit"
    assert "Traceback" not in err, f"expected a clear error, got a traceback:\n{err}"
    assert keyword in (out + err).lower(), f"expected '{keyword}' in:\n{out}{err}"
    assert conclusion_marker not in out, "a conclusion was printed before failing"


# ---------------- compare_runs.py ----------------

def cmp(study, a, b):
    return run(study, "compare_runs.py", str(runs(study) / a), str(runs(study) / b))


def test_compare_valid_holdout_pair(study):
    code, out, err = cmp(study, "v1_naive_holdout.json", "v2_structured_holdout.json")
    assert code == 0, err
    assert "regressed:     ['t47']" in out


def test_compare_valid_train_pair(study):
    code, out, err = cmp(study, "v1_naive_train.json", "v2_structured_train.json")
    assert code == 0, err


def test_compare_rejects_incomplete_run(study):
    edit(runs(study) / "v2_structured_holdout.json", lambda d: d["metadata"].update(incomplete=True))
    assert_clean_failure(*cmp(study, "v1_naive_holdout.json", "v2_structured_holdout.json"),
                         "incomplete", "mean:")


def test_compare_rejects_missing_file(study):
    (runs(study) / "v2_structured_holdout.json").unlink()
    assert_clean_failure(*cmp(study, "v1_naive_holdout.json", "v2_structured_holdout.json"),
                         "missing", "mean:")


def test_compare_rejects_case_missing_from_split(study):
    for name in ("v1_naive_holdout.json", "v2_structured_holdout.json"):
        edit(runs(study) / name, drop_case("t47"))
    assert_clean_failure(*cmp(study, "v1_naive_holdout.json", "v2_structured_holdout.json"),
                         "t47", "mean:")


def test_compare_rejects_case_outside_split(study):
    extra = {"id": "t03", "prompt": "x", "expected": "billing",
             "response": "billing", "scores": {"normalized_exact_match": 1.0}}
    for name in ("v1_naive_holdout.json", "v2_structured_holdout.json"):
        edit(runs(study) / name, lambda d: d["results"].append(dict(extra)))
    assert_clean_failure(*cmp(study, "v1_naive_holdout.json", "v2_structured_holdout.json"),
                         "t03", "mean:")


def test_compare_rejects_duplicate_case(study):
    edit(runs(study) / "v2_structured_holdout.json",
         lambda d: d["results"].append(dict(d["results"][0])))
    assert_clean_failure(*cmp(study, "v1_naive_holdout.json", "v2_structured_holdout.json"),
                         "duplicate", "mean:")


def test_compare_rejects_mixed_splits(study):
    assert_clean_failure(*cmp(study, "v1_naive_holdout.json", "v2_structured_train.json"),
                         "split", "mean:")


def test_compare_rejects_missing_arguments(study):
    assert_clean_failure(*run(study, "compare_runs.py"), "usage", "mean:")


# ---------------- repeats.py ----------------

def test_repeats_valid_study_reports_expected_numbers(study):
    code, out, err = run(study, "repeats.py")
    assert code == 0, err
    assert "20 unique tickets" in out
    assert out.count("16/20") >= 3
    assert out.count("19/20") >= 3


def test_repeats_reports_t47_per_repeat(study):
    code, out, err = run(study, "repeats.py")
    assert code == 0, err
    for i in (1, 2, 3):
        line = next((l for l in out.splitlines() if l.strip().startswith(f"repeat {i}:")), None)
        assert line is not None, f"no per-repeat comparison line for repeat {i}"
        assert "regressed ['t47']" in line


def test_repeats_rejects_missing_run(study):
    (runs(study) / "v2_structured_holdout_r3.json").unlink()
    assert_clean_failure(*run(study, "repeats.py"), "missing", "Accuracy per run")


def test_repeats_rejects_incomplete_run(study):
    edit(runs(study) / "v1_naive_holdout_r2.json", lambda d: d["metadata"].update(incomplete=True))
    assert_clean_failure(*run(study, "repeats.py"), "incomplete", "Accuracy per run")


def test_repeats_rejects_case_missing_from_one_repeat(study):
    edit(runs(study) / "v2_structured_holdout_r3.json", drop_case("t01"))
    assert_clean_failure(*run(study, "repeats.py"), "t01", "Accuracy per run")


def test_repeats_rejects_run_saved_under_wrong_version(study):
    shutil.copy(runs(study) / "v1_naive_holdout_r2.json", runs(study) / "v2_structured_holdout_r2.json")
    assert_clean_failure(*run(study, "repeats.py"), "prompt_version", "Accuracy per run")


def test_repeats_rejects_changed_expected_answer(study):
    def change(d):
        d["results"][0]["expected"] = "not-the-frozen-label"
    edit(runs(study) / "v2_structured_holdout_r2.json", change)
    assert_clean_failure(*run(study, "repeats.py"), "reference answer", "Accuracy per run")
