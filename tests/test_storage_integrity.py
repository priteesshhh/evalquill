"""A failed save must never destroy an existing valid run or leave a
misleading artifact behind.
"""

import json
import math
import os
from pathlib import Path

import pytest
from evalquill.storage import save_run, load_run


def _results(score=1.0):
    return [{"id": "c1", "prompt": "q", "expected": "a",
             "response": "a", "scores": {"m": score}}]


def test_failed_serialization_preserves_existing_run(tmp_path):
    path = tmp_path / "run.json"
    save_run(_results(), str(path))
    original = path.read_bytes()

    with pytest.raises(TypeError):
        save_run(_results(0.0), str(path), metadata={"where": Path("x")})

    assert path.read_bytes() == original
    assert load_run(str(path))["results"] == _results()


def test_nan_score_rejected_and_existing_run_preserved(tmp_path):
    path = tmp_path / "run.json"
    save_run(_results(), str(path))
    original = path.read_bytes()

    with pytest.raises(ValueError):
        save_run(_results(math.nan), str(path))

    assert path.read_bytes() == original


def test_failed_new_save_leaves_nothing(tmp_path):
    path = tmp_path / "run.json"

    with pytest.raises(TypeError):
        save_run(_results(), str(path), metadata={"where": Path("x")})

    assert list(tmp_path.iterdir()) == []


def test_failure_during_replace_preserves_run_and_cleans_up(tmp_path, monkeypatch):
    path = tmp_path / "run.json"
    save_run(_results(), str(path))
    original = path.read_bytes()

    def boom(*args, **kwargs):
        raise OSError("simulated crash during replace")

    monkeypatch.setattr(os, "replace", boom)

    with pytest.raises(OSError, match="simulated crash"):
        save_run(_results(0.0), str(path))

    assert path.read_bytes() == original
    assert [p.name for p in tmp_path.iterdir()] == ["run.json"]


def test_successful_overwrite_replaces_content(tmp_path):
    path = tmp_path / "run.json"
    save_run(_results(1.0), str(path))
    save_run(_results(0.0), str(path))
    assert load_run(str(path))["results"][0]["scores"]["m"] == 0.0


def test_saved_file_is_standard_json(tmp_path):
    path = tmp_path / "run.json"
    save_run(_results(0.5), str(path))

    def reject(token):
        raise AssertionError(f"non-standard JSON constant: {token}")

    json.loads(path.read_text(encoding="utf-8"), parse_constant=reject)
