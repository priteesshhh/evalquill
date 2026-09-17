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

## OpenAI adapter - live verification pending

8 offline unit tests passing against an injected fake client: message
construction, system prompt handling, default temperature, kwarg passthrough,
metadata, None-content handling, error propagation.

Live verification NOT completed. Attempted 2026-09-17 with openai SDK 3.14.1
and model gpt-4o-mini.

First attempt failed before reaching the API with an illegal header value,
caused by a trailing newline in OPENAI_API_KEY. Environment problem, not a
code defect.

Second attempt reached the API and was rejected on billing:

    HTTP 429
    type: insufficient_quota
    code: credit_balance_exhausted

Established: client construction, authentication, and the
chat.completions.create call signature work against SDK 3.14.1. API errors
propagate as exceptions rather than becoming scores.

Unverified: that a successful response parses correctly, that
choices[0].message.content is the right access path on this SDK version, and
token usage per call.

## Case study - not started

The demo in examples/prompt_change_demo.py uses stub LLMs and is synthetic.
It illustrates the comparison workflow. It is not evidence about any real
model's behaviour.
