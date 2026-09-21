"""rescore.py must recompute scores from saved data, not re-read them."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "case_study"))

import rescore

RUNS = Path(__file__).parent.parent / "case_study" / "runs"


def _copy_run(tmp_path, name="v1_naive_holdout.json"):
    return json.loads((RUNS / name).read_text(encoding="utf-8"))


def test_every_saved_run_rescores_cleanly():
    assert rescore.main([]) == 0


def test_altered_stored_score_is_detected(tmp_path, capsys):
    data = _copy_run(tmp_path)
    row = data["results"][0]
    row["scores"]["normalized_exact_match"] = 1.0 - row["scores"]["normalized_exact_match"]
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    assert rescore.main([str(path)]) == 1
    out = capsys.readouterr().out
    assert "MISMATCH" in out
    assert row["id"] in out


def test_unknown_metric_is_reported_not_skipped(tmp_path, capsys):
    data = _copy_run(tmp_path)
    for row in data["results"]:
        row["scores"] = {"mystery_metric": row["scores"]["normalized_exact_match"]}
    path = tmp_path / "unknown.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    assert rescore.main([str(path)]) == 1
    assert "cannot rescore" in capsys.readouterr().out
