# evalquill

[![CI](https://github.com/priteesshhh/evalquill/actions/workflows/ci.yml/badge.svg)](https://github.com/priteesshhh/evalquill/actions/workflows/ci.yml)

A small Python library for checking what changed when you edit an LLM prompt.

You change a prompt, rerun your evals, and the average score moves from 0.72 to 0.75. Did it get better? Maybe. It might also have fixed four cases and broken two that used to work. The average won't tell you that.

evalquill compares two runs case by case and tells you which specific cases got worse.

## Install

Requires Python 3.10 or later. The core has no runtime dependencies.

It is not on PyPI yet, so install from GitHub (this needs git):

```bash
pip install git+https://github.com/priteesshhh/evalquill.git
```

The OpenAI and Gemini adapters are optional extras:

```bash
pip install "evalquill[openai] @ git+https://github.com/priteesshhh/evalquill.git"
pip install "evalquill[gemini] @ git+https://github.com/priteesshhh/evalquill.git"
```

To work on it locally:

```bash
git clone https://github.com/priteesshhh/evalquill.git
cd evalquill
uv sync
```

## Quickstart

A metric is a function `(response, expected) -> float` that returns a score from 0 to 1. An LLM is any function `(prompt) -> str`: a provider client, a wrapper around your own model, or a stub.

This example classifies support tickets. Two stub functions stand in for the same model under two versions of a prompt, so it runs without an API key.

```python
from evalquill import evaluate_dataset
from evalquill.metrics import normalized_exact_match
from evalquill.compare import compare, diff_summary

dataset = [
    {"id": "refund", "prompt": "I was charged twice this month.", "expected": "billing"},
    {"id": "login", "prompt": "The login page shows a 500 error.", "expected": "account"},
    {"id": "invite", "prompt": "My teammate never got the invite email.", "expected": "account"},
    {"id": "webhook", "prompt": "Our webhook stopped receiving events.", "expected": "integration"},
]

def llm_v1(prompt):
    return {
        "I was charged twice this month.": "billing",
        "The login page shows a 500 error.": "bug",
        "My teammate never got the invite email.": "account",
        "Our webhook stopped receiving events.": "bug",
    }[prompt]

def llm_v2(prompt):
    return {
        "I was charged twice this month.": "billing",
        "The login page shows a 500 error.": "account",
        "My teammate never got the invite email.": "integration",
        "Our webhook stopped receiving events.": "integration",
    }[prompt]

baseline = evaluate_dataset(dataset, llm_v1, [normalized_exact_match])
candidate = evaluate_dataset(dataset, llm_v2, [normalized_exact_match])

summary = diff_summary(compare(baseline, candidate))
print(summary["normalized_exact_match"])
```

```
{'baseline_mean': 0.5, 'candidate_mean': 0.75, 'mean_delta': 0.25, 'improved': ['login', 'webhook'], 'regressed': ['invite'], 'newly_failing': ['invite']}
```

Accuracy rose from 0.50 to 0.75. Two cases improved, and `invite`, which v1 classified correctly, v2 now gets wrong. The average alone would not have shown that.

Each result row keeps the input, the response and its scores:

```python
{"id": "invite", "prompt": "My teammate never got the invite email.",
 "expected": "account", "response": "integration",
 "scores": {"normalized_exact_match": 0.0}}
```

`examples/prompt_change_demo.py` runs the same comparison through saved runs and prints the responses behind each regression.

## Failing a build

A regression check belongs in your test suite. Continuing from the quickstart, with `dataset` and `llm_v2` imported from wherever your project defines them:

```python
from evalquill import evaluate_dataset, summary_scores, threshold_check
from evalquill.compare import compare, diff_summary
from evalquill.metrics import normalized_exact_match
from evalquill.storage import load_run

def test_accuracy_meets_threshold():
    candidate = evaluate_dataset(dataset, llm_v2, [normalized_exact_match])
    checks = threshold_check(summary_scores(candidate), {"normalized_exact_match": 0.7})
    assert checks == {"normalized_exact_match": "PASS"}

def test_no_case_stops_passing():
    baseline = load_run("runs/baseline.json")["results"]
    candidate = evaluate_dataset(dataset, llm_v2, [normalized_exact_match])
    summary = diff_summary(compare(baseline, candidate))["normalized_exact_match"]
    assert summary["newly_failing"] == [], f"stopped passing: {summary['newly_failing']}"
```

The baseline is a saved run (see Saving runs below). With the quickstart's v2 prompt, the first test passes, since 0.75 clears 0.7, and the second fails:

```
AssertionError: stopped passing: ['invite']
```

The accuracy bar was met and a case still broke. A threshold alone lets that through.

`threshold_check` returns the strings `"PASS"`, `"FAIL"` and `"NOT RUN"`, so compare them explicitly. `assert all(checks.values())` would pass on `"FAIL"`, because every non-empty string is truthy.

## Saving runs

Save a run once and compare against it later, without paying for the same model calls again:

```python
from evalquill.storage import save_run, load_run

save_run(baseline, "runs/baseline.json", metadata={"prompt_version": "v1"})
stored = load_run("runs/baseline.json")
compare(stored["results"], candidate)
```

Metadata is free-form. Record the model, its settings and the prompt version; that is what makes a saved run interpretable weeks later.

## Writing a metric

Any named function works. This one checks a field in a JSON response:

```python
import json
from evalquill import evaluate

def json_label(response: str, expected: str) -> float:
    try:
        return 1.0 if json.loads(response).get("label") == expected else 0.0
    except (json.JSONDecodeError, AttributeError):
        return 0.0

print(evaluate(expected="billing", response='{"label": "billing"}', metrics=[json_label]))
```

```
{'json_label': 1.0}
```

The rules: the function's name is the score's key and must be unique within a run. The return value must be a finite number from 0 to 1; booleans are rejected. If a metric raises, the run stops and the error names the case.

## Using a real model

Wrap your model in a function that takes a prompt and returns a string. For a self-hosted model, that is usually a few lines around your inference client.

For OpenAI and Gemini there are adapters. Install the matching extra; the key is read from `OPENAI_API_KEY` or `GEMINI_API_KEY`:

```python
from evalquill.providers import openai_llm

llm, metadata = openai_llm(
    "gpt-4o-mini",
    system_prompt="Classify the support ticket as billing, account, integration, feature, bug or other. Reply with one word.",
    temperature=0.0,
)
results = evaluate_dataset(dataset, llm, [normalized_exact_match])
save_run(results, "runs/gpt-4o-mini_v2.json", metadata=metadata)
```

`gemini_llm` works the same way. The returned `metadata` records the provider, model, temperature and system prompt, so a saved run says what produced it. The adapters add no retry logic of their own: the provider SDK's default retries apply, and any error that remains stops the run and names the case.

## Why case IDs matter

Comparisons join on case ID, not list position. If you reorder your dataset or insert a case, a positional comparison silently diffs unrelated rows and gives you a confident wrong answer.

IDs default to `case_0`, `case_1` and so on if you don't supply them. That's fine for a one-off run, but give real IDs to anything you'll compare across versions.

Two runs are rejected rather than compared if they cover different cases, use different metrics, or if any case's input or expected answer differs between them. Only the response and its scores may change.

## Case study

[case_study/](case_study/) contains a worked example: 50 fictional support tickets, hand-labeled against a written guide, classified by gpt-4o-mini under two prompt versions. Results are reported on a frozen 20-ticket held-out set, with three repeats per version on that set.

Accuracy rose from 80% to 95% on the held-out set, and one previously correct ticket failed in all three observed repeats. The aggregate score does not surface that; the per-case comparison does.

All runs are saved. `case_study/rescore.py` recomputes every stored score from the saved responses, with no API key. See [case_study/README.md](case_study/README.md) for method, results and limitations.

## What it doesn't do

- No semantic or model-graded metrics. The built-ins are string comparisons, named for what they check: `normalized_exact_match` ignores case and surrounding whitespace, and `contains_substring` checks for a substring and nothing more. `contains_substring("19", "9")` returns 1.0, and a correct answer in a different form, such as "nine" for "9", scores 0.0.
- No RAG metrics. Metrics receive only the response and the expected value, so anything needing retrieved context doesn't fit the signature yet.
- No concurrency. Model calls are made one at a time.
- No repeat-run tooling in the library. The case study has scripts for its own repeats.
- No dashboard, no hosted anything.

This isn't the only tool in this space. promptfoo, DeepEval, LangSmith and Braintrust all overlap with it and most do more.

## Design notes

Scores are stored at full precision and rounded only for display. Rounding before a threshold check lets a true score of 0.7993 pass a 0.80 threshold, a silent false pass. There's a regression test for it.

Metrics must return a finite number between 0 and 1. Booleans are rejected explicitly: `True == 1.0` in Python, so a metric returning booleans would otherwise pass validation while suggesting its author didn't mean to return a score.

Duplicate metric names and duplicate case IDs are rejected. Both silently overwrite results otherwise. A missing score is rejected rather than averaged as zero.

A comparison requires each case's input and expected answer to be identical in both runs. Otherwise a changed reference answer would show up as a model improvement.

The whole dataset is validated before the first model call, so a bad row near the end doesn't cost every call before it. When a model call or a metric fails, the run stops and the error names the case. Recording 0.0 instead would make a broken metric look like a failing model.

Saves are atomic: a failed save leaves any previous file intact. Loading validates the whole file, not just its schema version.

## Tests

```bash
uv run pytest
```

`tests/test_readme.py` runs every Python example in this README and checks the output shown, so the examples can't drift from the code. Live tests against real APIs are opt-in: `uv run pytest -m live`, with the provider keys set.

## Status

Early. Not on PyPI yet, and the API may change before a first release.

## License

MIT
