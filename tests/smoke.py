"""Smoke test for a built distribution.

Run against an installed wheel, not the source tree:
    uv run --isolated --no-project --with dist/*.whl tests/smoke_test.py

Exercises the core API with no provider extras, no editable install, and no
PYTHONPATH manipulation. Deliberately not a pytest test - it must run as a
plain script against an installed package.
"""

import evalquill
from evalquill import evaluate, evaluate_dataset, summary_scores, threshold_check
from evalquill.metrics import normalized_exact_match, contains_substring
from evalquill.compare import compare, diff_summary
from evalquill.storage import save_run, load_run


def stub_llm_v1(prompt):
    return {"What is 2 + 2?": "2 + 2 equals 4.", "Capital of France?": "Paris"}[prompt]


def stub_llm_v2(prompt):
    return {"What is 2 + 2?": "four", "Capital of France?": "Paris"}[prompt]


dataset = [
    {"id": "math", "prompt": "What is 2 + 2?", "expected": "4"},
    {"id": "geo", "prompt": "Capital of France?", "expected": "Paris"},
]

baseline = evaluate_dataset(dataset, stub_llm_v1, [contains_substring])
candidate = evaluate_dataset(dataset, stub_llm_v2, [contains_substring])

assert baseline[0]["scores"]["contains_substring"] == 1.0
assert candidate[0]["scores"]["contains_substring"] == 0.0

summary = diff_summary(compare(baseline, candidate))
assert summary["contains_substring"]["regressed"] == ["math"]
assert summary["contains_substring"]["newly_failing"] == ["math"]

single = evaluate("4", "4", [normalized_exact_match])
assert single["normalized_exact_match"] == 1.0

means = summary_scores(baseline)
checks = threshold_check(means, {"contains_substring": 0.9})
assert checks["contains_substring"] == "PASS"

import tempfile, os
with tempfile.TemporaryDirectory() as d:
    path = os.path.join(d, "run.json")
    save_run(baseline, path, metadata={"prompt_version": "v1"})
    assert load_run(path)["metadata"]["prompt_version"] == "v1"

print(f"smoke test passed: evalquill {evalquill.__file__}")