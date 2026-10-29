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

Current: GitHub Actions run 40810449980 passed on main at commit 474715a,
the released commit.

The workflow runs four jobs: offline tests and wheel install, each on Python
3.10 and 3.14, the declared floor and the development version. Each job
asserts the interpreter it actually ran, so the matrix cannot silently fall
back to a single version; run 35736820917 recorded 3.10.21 and 3.14.7 across
the four jobs. The suite has 180 offline tests, with 2 live tests deselected.

Historical, 2026-09-17: run 35279309174 passed both jobs on ubuntu-latest,
when the suite had 67 offline tests and the workflow tested one Python
version.

What the jobs do. offline tests: uv sync --locked --dev, then uv run pytest.
No extras are installed, so this also confirms that the core and the mocked
adapter tests need no provider SDK. wheel install: uv build --no-sources,
then the smoke script run against both distributions via uv run --isolated
--no-project; both import evalquill from site-packages under the runner
cache, confirming no reliance on the source tree, an editable install, or
PYTHONPATH.

No API keys are present in CI and no live calls are made.

## Case study - complete

Method, results and limitations are in case_study/README.md. Six holdout
runs (three per prompt version) and two train runs are saved in
case_study/runs/. case_study/rescore.py recomputes all 180 stored scores from
the saved responses; at commit 38abed9 every score matched.

The demo in examples/prompt_change_demo.py uses stub LLMs and is synthetic.
It illustrates the comparison workflow. It is not evidence about any real
model's behaviour.

## Release 0.1.0 - published 2026-10-28

Published to PyPI: https://pypi.org/project/evalquill/0.1.0/

One commit carries the whole chain. Tag v0.1.0, branch main, and the
published distributions are all commit
474715af81adc7191285e7a7ef150aa58e0f7f58.

Artifacts, built with uv build --no-sources and uploaded unchanged:

    8319c41492f78a37f09cb9dd5c6ed3c1f3692257e2c9873bdcf2435e3aba7b1d
      evalquill-0.1.0-py3-none-any.whl
    6693fd235d9e1efcc01f4f49059030d0802df84684fe7d01726b8c3497ebee33
      evalquill-0.1.0.tar.gz

The same hashes were recorded at build time on 2026-09-22 and re-checked
before upload, so the published files are the ones that were validated.

Before upload: twine check passed on both; metadata inspected (version,
requires-python, MIT with LICENSE packaged, both extras, markdown README);
each distribution installed separately into a clean Python 3.10 environment
outside the repository, where the README quickstart produced its documented
output.

After upload: pip install evalquill into a fresh Python 3.10.12 environment
outside the repository imported from site-packages, and the README quickstart
again produced its documented output.

TestPyPI was skipped deliberately. twine check had already applied the same
long-description render check PyPI uses, and both distributions had been
installed and exercised from disk, so a practice upload would have re-verified
what was already verified.

Not done: trials with developers other than the author.
