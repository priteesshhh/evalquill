# Changelog

## 0.1.0

First release.

Compares two LLM evaluation runs case by case and reports which cases
improved, which regressed, and which went from passing to failing, so a
prompt change that raises the average while breaking individual cases is
visible.

Included:

- `evaluate` and `evaluate_dataset`, with any `llm(prompt) -> str` callable.
  The whole dataset is validated before the first model call.
- Two string metrics, `normalized_exact_match` and `contains_substring`, and
  support for custom metric functions.
- `compare` and `diff_summary`. Runs are joined on case ID and rejected if
  they differ in cases, metrics, inputs or expected answers.
- `summary_scores` and `threshold_check`, which reject missing or invalid
  scores rather than averaging them as zero.
- `save_run` and `load_run`. Saves are atomic, and loading validates the
  whole file.
- Optional OpenAI and Gemini adapters, installed as extras.
- No runtime dependencies. Tested on Python 3.10 and 3.14.

Known limitations: metrics are string comparisons only; model calls are
sequential; there are no RAG or model-graded metrics; the library has no
repeat-run tooling.
