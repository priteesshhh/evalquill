"""Offline verification of repeat storage safety.

Uses a stubbed OpenAI client and EVALQUILL_RUNS_DIR so no real API calls are
made and no real run artifact can be written.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).parent.parent
REAL_RUNS = REPO / "case_study" / "runs"

STUB = '''
import sys, json
from pathlib import Path

counter = Path(sys.argv.pop())          # last arg is the call counter path
sys.path.insert(0, str(Path.cwd() / "case_study"))

class _Msg:
    def __init__(self, c): self.content = c
class _Choice:
    def __init__(self, c): self.message = _Msg(c)
class _Resp:
    def __init__(self, c): self.choices = [_Choice(c)]
class _Completions:
    def create(self, **kw):
        n = json.loads(counter.read_text()) if counter.exists() else 0
        counter.write_text(json.dumps(n + 1))
        return _Resp("bug")
class _Chat:
    def __init__(self): self.completions = _Completions()
class _Client:
    def __init__(self, **kw): self.chat = _Chat()

# Install a stand-in openai module. The real SDK is an optional extra and is
# not installed in CI, so importing it here would make these tests depend on
# something the core does not require.
import types
fake = types.ModuleType("openai")
fake.OpenAI = _Client
class _Err(Exception): pass
fake.RateLimitError = type("RateLimitError", (_Err,), {})
fake.InternalServerError = type("InternalServerError", (_Err,), {})
fake.APIConnectionError = type("APIConnectionError", (_Err,), {})
sys.modules["openai"] = fake

import run
run.SECONDS_BETWEEN_CALLS = 0
run.main()
'''


def _invoke(args, runs_dir, counter, tmp_path):
    stub = tmp_path / "stub.py"
    stub.write_text(STUB)
    env = dict(os.environ, EVALQUILL_RUNS_DIR=str(runs_dir))
    return subprocess.run(
        [sys.executable, str(stub), *args, str(counter)],
        cwd=REPO, capture_output=True, text=True, env=env,
    )


def _calls(counter):
    return json.loads(counter.read_text()) if counter.exists() else 0


def test_repeat_index_writes_separate_file(tmp_path):
    runs, counter = tmp_path / "runs", tmp_path / "calls.json"
    runs.mkdir()

    r = _invoke(["v1_naive", "holdout", "2"], runs, counter, tmp_path)
    assert r.returncode == 0, r.stderr

    target = runs / "v1_naive_holdout_r2.json"
    assert target.exists()
    assert json.loads(target.read_text())["metadata"]["repeat"] == "2"


def test_each_repeat_calls_the_model(tmp_path):
    runs, counter = tmp_path / "runs", tmp_path / "calls.json"
    runs.mkdir()

    _invoke(["v1_naive", "holdout", "2"], runs, counter, tmp_path)
    assert _calls(counter) == 20, "expected one generation per ticket"

    _invoke(["v1_naive", "holdout", "3"], runs, counter, tmp_path)
    assert _calls(counter) == 40, "repeat 3 did not generate; results were reused"


def test_collision_causes_zero_model_calls(tmp_path):
    runs, counter = tmp_path / "runs", tmp_path / "calls.json"
    runs.mkdir()
    (runs / "v1_naive_holdout_r2.json").write_text("{}")

    r = _invoke(["v1_naive", "holdout", "2"], runs, counter, tmp_path)

    assert r.returncode != 0
    assert "Refusing to overwrite" in (r.stdout + r.stderr)
    assert _calls(counter) == 0, "model was called despite refusing to write"


def test_partial_file_also_blocks(tmp_path):
    runs, counter = tmp_path / "runs", tmp_path / "calls.json"
    runs.mkdir()
    (runs / "v1_naive_holdout_r2.partial.json").write_text("{}")

    r = _invoke(["v1_naive", "holdout", "2"], runs, counter, tmp_path)

    assert r.returncode != 0
    assert _calls(counter) == 0


def test_real_run_artifacts_are_untouched(tmp_path):
    runs, counter = tmp_path / "runs", tmp_path / "calls.json"
    runs.mkdir()

    before = {p.name: p.read_bytes() for p in REAL_RUNS.glob("*.json")}
    _invoke(["v1_naive", "holdout", "2"], runs, counter, tmp_path)
    after = {p.name: p.read_bytes() for p in REAL_RUNS.glob("*.json")}

    assert before == after, "a real run artifact was modified"
