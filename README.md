# evalquill

[![CI](https://github.com/priteesshhh/evalquill/actions/workflows/ci.yml/badge.svg)](https://github.com/priteesshhh/evalquill/actions/workflows/ci.yml)

A Python library for checking what changed when you edit an LLM prompt.

You change a prompt, rerun your evals, and the average score moves from 0.72 to 0.75. Did it get better? Maybe. It might also have fixed four cases and broken two that used to work. The average won't tell you that.

evalquill compares two runs case by case and tells you which specific cases regressed.

## Install

Not on PyPI yet.

```bash
pip install git+https://github.com/priteesshhh/evalquill.git
```

To work on it locally:

```bash
git clone https://github.com/priteesshhh/evalquill.git
cd evalquill
uv sync
```

## Quickstart

A metric is a function taking the response and the expected value, returning a score between 0 and 1. An LLM is any callable taking a prompt and returning a string - a real client, a wrapper, or a stub.

This example uses two stub LLMs standing in for the same model under two different prompts. The second prompt says "answer in one word", which makes it spell out the number.

```python
from evalquill import evaluate_dataset
from evalquill.metrics import contains_substring
from evalquill.compare import compare, diff_summary

dataset = [
    {"id": "capital_india", "prompt": "What is the capital of India?", "expected": "Delhi"},
    {"id": "capital_france", "prompt": "What is the capital of France?", "expected": "Paris"},
    {"id": "math_seven_two", "prompt": "What is 7 + 2?", "expected": "9"},
]

def llm_v1(prompt):
    return {
        "What is the capital of India?": "The capital of India is Delhi.",
        "What is the capital of France?": "The capital of France is Paris.",
        "What is 7 + 2?": "7 + 2 equals 9.",
    }[prompt]

def llm_v2(prompt):
    return {
        "What is the capital of India?": "Delhi",
        "What is the capital of France?": "Paris",
        "What is 7 + 2?": "nine",
    }[prompt]

baseline = evaluate_dataset(dataset, llm_v1, [contains_substring])
candidate = evaluate_dataset(dataset, llm_v2, [contains_substring])

summary = diff_summary(compare(baseline, candidate))
print(summary["contains_substring"])
```

```
{'baseline_mean': 1.0,
 'candidate_mean': 0.6666666666666666,
 'mean_delta': -0.33333333333333337,
 'improved': [],
 'regressed': ['math_seven_two'],
 'newly_failing': ['math_seven_two']}
```

The runnable version at `examples/prompt_change_demo.py` also prints the responses behind the regression:

```
contains_substring
  mean: 1.00 -> 0.67 (-0.33)
  improved:      none
  regressed:     ['math_seven_two']
  newly failing: ['math_seven_two']

Regressed cases:

  math_seven_two
    expected:  9
    v1 said:   7 + 2 equals 9.
    v2 said:   nine
```

## Saving runs

Runs can be saved and reloaded, so re-scoring or re-comparing doesn't mean paying for the same API calls again:

```python
from evalquill.storage import save_run, load_run

save_run(baseline, "runs/baseline.json", metadata={"model": "gpt-4o-mini", "prompt_version": "v1"})
stored = load_run("runs/baseline.json")
compare(stored["results"], candidate)
```

Metadata is free-form. Recording the model, its settings, and the prompt version is what makes a saved run interpretable weeks later.

## Why case IDs matter

Comparisons join on case ID, not list position. If you reorder your dataset or insert a case, a positional comparison silently diffs unrelated rows and gives you a confident wrong answer.

IDs default to `case_0`, `case_1` and so on if you don't supply them. That's fine for a one-off run, but give real IDs to anything you'll compare across versions.

Runs covering different cases, or using different metrics, are rejected rather than compared.

## What it doesn't do

- No semantic or model-graded metrics. The built-ins are string comparisons, named for what they actually check: `normalized_exact_match` ignores case and surrounding whitespace, `contains_substring` checks for a substring and nothing more. `contains_substring("19", "9")` returns 1.0 - correct for a substring check, wrong if you read it as answer correctness.
- No RAG metrics. Metrics receive only the response and the expected value, so anything needing retrieved context doesn't fit the signature yet.
- Two provider adapters, both optional extras: OpenAI and Gemini. The core
  has no runtime dependencies and takes any `llm(prompt) -> str` callable.
- No dashboard, no hosted anything.

This isn't the only tool in this space. promptfoo, DeepEval, LangSmith and Braintrust all overlap with it and most do more.

## Design notes

Scores are stored at full precision and rounded only for display. Rounding before a threshold check lets a true score of 0.7993 pass a 0.80 threshold - a silent false pass. There's a regression test for it.

Metrics must return a finite number between 0 and 1. Booleans are rejected explicitly: `True == 1.0` in Python, so a metric returning booleans would otherwise pass validation while suggesting its author didn't mean to return a score.

Duplicate metric names and duplicate case IDs are rejected. Both silently overwrite results otherwise.

When a metric raises, the run stops and the error names the case ID and prompt. Swallowing it and recording 0.0 would make a broken metric look like a failing model.

Saved runs carry a schema version. Loading a file with a different version fails rather than half-parsing into a wrong comparison.

## Tests

```bash
uv run pytest tests/ -v
```

## License

MIT

## Case study

[case_study/](case_study/) contains a worked example: 50 fictional support
tickets, hand-labeled against a written guide, classified by gpt-4o-mini
under two prompt versions over three repeats.

Accuracy rose from 80% to 95% on the held-out set, and one previously
correct ticket failed in all three observed repeats. The aggregate score
does not surface that; the per-case comparison does.

All runs are saved, so the results can be re-scored and re-compared with no
API key. See [case_study/README.md](case_study/README.md) for method,
results and limitations.

## Status

Early. The core works and is tested; the API will probably change.
