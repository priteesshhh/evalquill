"""load_run and save_run must reject structurally invalid runs at the
storage boundary, not let them fail later somewhere unrelated.
"""

import json
import pytest
from evalquill.storage import save_run, load_run

ROW = {"id": "c1", "prompt": "q", "expected": "a", "response": "a", "scores": {"m": 1.0}}


def _write(tmp_path, payload):
    p = tmp_path / "run.json"
    p.write_text(payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")
    return str(p)


def _envelope(**overrides):
    base = {"schema_version": 1, "created_at": "2026-09-21T00:00:00+00:00",
            "metadata": {}, "results": [dict(ROW)]}
    base.update(overrides)
    return base


# --- load: envelope ---

def test_version_only_file_rejected(tmp_path):
    with pytest.raises(ValueError, match="results"):
        load_run(_write(tmp_path, {"schema_version": 1}))


def test_results_not_a_list_rejected(tmp_path):
    with pytest.raises(ValueError, match="results"):
        load_run(_write(tmp_path, _envelope(results={"c1": ROW})))


def test_empty_results_rejected(tmp_path):
    with pytest.raises(ValueError, match="at least one case"):
        load_run(_write(tmp_path, _envelope(results=[])))


def test_metadata_not_a_dict_rejected(tmp_path):
    with pytest.raises(ValueError, match="metadata"):
        load_run(_write(tmp_path, _envelope(metadata=["x"])))


# --- load: rows ---

def test_row_missing_field_rejected(tmp_path):
    row = dict(ROW); del row["expected"]
    with pytest.raises(ValueError, match="missing"):
        load_run(_write(tmp_path, _envelope(results=[row])))


def test_duplicate_ids_rejected(tmp_path):
    with pytest.raises(ValueError, match="Duplicate case id"):
        load_run(_write(tmp_path, _envelope(results=[dict(ROW), dict(ROW)])))


def test_invalid_score_rejected(tmp_path):
    row = dict(ROW, scores={"m": 1.5})
    with pytest.raises(ValueError, match="between 0 and 1"):
        load_run(_write(tmp_path, _envelope(results=[row])))


def test_nan_literal_rejected(tmp_path):
    text = json.dumps(_envelope()).replace('"m": 1.0', '"m": NaN')
    with pytest.raises(ValueError):
        load_run(_write(tmp_path, text))


def test_inconsistent_metric_sets_rejected(tmp_path):
    r2 = dict(ROW, id="c2", scores={"other": 1.0})
    with pytest.raises(ValueError, match="metric"):
        load_run(_write(tmp_path, _envelope(results=[dict(ROW), r2])))


# --- load: already rejected before this change, must stay rejected ---

def test_top_level_list_rejected(tmp_path):
    with pytest.raises(ValueError):
        load_run(_write(tmp_path, [ROW]))


def test_malformed_json_rejected(tmp_path):
    with pytest.raises(ValueError):
        load_run(_write(tmp_path, "{not json"))


# --- save ---

def test_save_rejects_invalid_row(tmp_path):
    row = dict(ROW, scores={"m": 1.5})
    with pytest.raises(ValueError):
        save_run([row], str(tmp_path / "run.json"))
    assert not (tmp_path / "run.json").exists()


def test_valid_run_still_round_trips(tmp_path):
    p = str(tmp_path / "run.json")
    save_run([dict(ROW)], p, metadata={"model": "x"})
    assert load_run(p)["results"] == [ROW]
