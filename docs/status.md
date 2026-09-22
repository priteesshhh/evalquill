# Verification status

## Gemini adapter - live verified 2026-09-17

Environment: google-genai 2.24.0, Python 3.14.4, model gemini-3.6-flash.

Single smoke test passed. Prompt "Reply with exactly the word: pong" returned
'pong'. Metadata recorded provider, model, temperature and system prompt.

Two failures preceded it, both environmental rather than code defects:

- 404 NOT_FOUND on gemini-2.5-flash. The API response for this project said
  the model was not available to new users and named gemini-3.6-flash as the
  replacement. That is one project's response, not a general availability
  claim.
- 503 UNAVAILABLE on first attempt with the corrected model. Transient
  capacity, succeeded on retry.

8 offline unit tests cover the adapter against an injected fake client.

## OpenAI adapter - live verified 2026-09-18

Environment: openai SDK 3.14.1, Python 3.14.4, model gpt-4o-mini.

Smoke test passed. Prompt "Reply with exactly the word: pong" returned 'pong'.
Metadata recorded provider, model, temperature, system prompt and max_tokens.
choices[0].message.content confirmed as the correct access path on this SDK
version.

Token usage for a minimal call: 14 prompt, 1 completion, 15 total.

Earlier attempt on 2026-09-17 failed on billing (HTTP 429,
code: insufficient_quota) with an exhausted credit balance, and before that on
a malformed auth header caused by a trailing newline in OPENAI_API_KEY. Both
were environmental, not code defects.

8 offline unit tests cover the adapter against an injected fake client.

## Retry policy - offline verified 2026-09-18

case_study/retry.py classifies failures by structured SDK exception type and
error.code, never by substring matching on the message. Quota and billing
codes stop immediately; transient rate limits and server errors retry to a
total of 3 attempts including the first. A numeric Retry-After value is
honoured; the HTTP-date form is ignored and negative values are not rejected.
The OpenAI client is constructed with max_retries=0 so SDK retries do not
multiply the wrapper's budget.

10 offline tests cover this, including a regression test asserting that an
error whose message text contains "503" and "insufficient_quota" is not
classified from those substrings.

## CI and packaging

Current: GitHub Actions run 35736820917 passed all four jobs for commit
4a2e42d: offline tests and wheel install, each on Python 3.10 and 3.14. Each
job asserts the interpreter it ran (3.10.21 and 3.14.7 in that run), so the
matrix cannot silently fall back to a single version. The suite has 180
offline tests, with 2 live tests deselected.

Historical, 2026-09-17: run 35279309174 passed both jobs on ubuntu-latest.

offline tests: uv sync --locked --dev, then uv run pytest. 67 tests passed,
2 live tests deselected. No extras installed, so this also confirms the core
and the mocked adapter tests need no provider SDK.

wheel install: uv build --no-sources, then the smoke script run against both
distributions via uv run --isolated --no-project. Both imported evalquill
from site-packages under the runner cache, confirming no reliance on the
source tree, an editable install, or PYTHONPATH.

No API keys are present in CI and no live calls are made.

## Case study - complete

Method, results and limitations are in case_study/README.md. Six holdout
runs (three per prompt version) and two train runs are saved in
case_study/runs/. case_study/rescore.py recomputes all 180 stored scores from
the saved responses; at commit 38abed9 every score matched.

The demo in examples/prompt_change_demo.py uses stub LLMs and is synthetic.
It illustrates the comparison workflow. It is not evidence about any real
model's behaviour.

## Release 0.1.0 - in preparation

Prepared on branch release/0.1.0 and not yet published. Pending: a
TestPyPI upload and install, and a clean install on a second machine.
The release tag will point to the commit that passes those checks.
