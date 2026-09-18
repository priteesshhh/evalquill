# Verification status

## Gemini adapter - live verified 2026-09-17

Environment: google-genai 2.24.0, Python 3.14.4, model gemini-3.6-flash.

Single smoke test passed. Prompt "Reply with exactly the word: pong" returned
'pong'. Metadata recorded provider, model, temperature and system prompt.

Two failures preceded it, both environmental rather than code defects:

- 404 NOT_FOUND on gemini-2.5-flash. That model is no longer available to new
  users; the API response named gemini-3.6-flash as the replacement.
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
total of 3 attempts including the first. Retry-After is honoured when present.
The OpenAI client is constructed with max_retries=0 so SDK retries do not
multiply the wrapper's budget.

10 offline tests cover this, including a regression test asserting that an
error whose message text contains "503" and "insufficient_quota" is not
classified from those substrings.

## CI and packaging - verified 2026-09-17

GitHub Actions run 35279309174 passed both jobs on ubuntu-latest.

offline tests: uv sync --locked --dev, then uv run pytest. 67 tests passed,
2 live tests deselected. No extras installed, so this also confirms the core
and the mocked adapter tests need no provider SDK.

wheel install: uv build --no-sources, then the smoke script run against both
distributions via uv run --isolated --no-project. Both imported evalquill
from site-packages under the runner cache, confirming no reliance on the
source tree, an editable install, or PYTHONPATH.

No API keys are present in CI and no live calls are made.

## Case study - not started

The demo in examples/prompt_change_demo.py uses stub LLMs and is synthetic.
It illustrates the comparison workflow. It is not evidence about any real
model's behaviour.
