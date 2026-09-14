import json
import pytest
from evalquill.storage import save_run, load_run, SCHEMA_VERSION


def _results():
    return [{
        "id": "c1",
        "prompt": "q",
        "expected": "a",
        "response": "a",
        "scores": {"m": 1.0},
    }]


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "run.json"
    save_run(_results(), str(path))
    loaded = load_run(str(path))
    assert loaded["results"] == _results()


def test_save_preserves_metadata(tmp_path):
    path = tmp_path / "run.json"
    save_run(_results(), str(path), metadata={"model": "gpt-4o-mini", "prompt_version": "v1"})
    loaded = load_run(str(path))
    assert loaded["metadata"]["model"] == "gpt-4o-mini"
    assert loaded["metadata"]["prompt_version"] == "v1"


def test_save_records_schema_version(tmp_path):
    path = tmp_path / "run.json"
    save_run(_results(), str(path))
    loaded = load_run(str(path))
    assert loaded["schema_version"] == SCHEMA_VERSION


def test_save_creates_parent_directories(tmp_path):
    path = tmp_path / "nested" / "dir" / "run.json"
    save_run(_results(), str(path))
    assert path.exists()


def test_save_rejects_empty_run(tmp_path):
    with pytest.raises(ValueError, match="empty run"):
        save_run([], str(tmp_path / "run.json"))


def test_load_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_run(str(tmp_path / "nope.json"))


def test_load_rejects_foreign_json(tmp_path):
    path = tmp_path / "other.json"
    path.write_text(json.dumps({"some": "data"}), encoding="utf-8")
    with pytest.raises(ValueError, match="not an evalquill run file"):
        load_run(str(path))


def test_load_rejects_future_schema(tmp_path):
    path = tmp_path / "future.json"
    path.write_text(json.dumps({"schema_version": 999, "results": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="schema version 999"):
        load_run(str(path))


def test_float_precision_survives_roundtrip(tmp_path):
    path = tmp_path / "run.json"
    results = [{
        "id": "c1", "prompt": "q", "expected": "a", "response": "a",
        "scores": {"m": 0.7993333333333333},
    }]
    save_run(results, str(path))
    loaded = load_run(str(path))
    assert loaded["results"][0]["scores"]["m"] == 0.7993333333333333