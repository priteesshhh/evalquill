"""Retry policy for live runs.

Lives in the case study, not the library: the adapter's contract is to
propagate errors faithfully, and its tests assert that. Retry policy is the
caller's decision.

Rules:
  - Quota exhausted or billing errors: stop immediately. Retrying cannot
    restore access, so retrying only wastes time and obscures the cause.
  - Temporary rate limits and transient server errors: retry, at most
    MAX_ATTEMPTS times in total including the first attempt.
  - Respect Retry-After when the provider sends it; otherwise back off.
  - Classification uses structured SDK exception types and error codes, never
    substring matching on the message text.

The SDK retries internally by default. Construct the client with
max_retries=0 so that total attempts equal MAX_ATTEMPTS rather than the
product of the two.
"""

import time

MAX_ATTEMPTS = 3
BASE_BACKOFF = 2.0

# error.code values that mean "stop", not "wait and try again".
TERMINAL_CODES = {
    "insufficient_quota",
    "billing_hard_limit_reached",
    "budget_exhausted",
}


class QuotaExhausted(RuntimeError):
    """Raised when the account is out of credit or over a hard limit."""


def _error_code(exc) -> str | None:
    """Structured error code from an SDK exception, or None."""
    code = getattr(exc, "code", None)
    if isinstance(code, str):
        return code
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict):
            inner = error.get("code")
            if isinstance(inner, str):
                return inner
    return None


def _retry_after(exc) -> float | None:
    """Seconds from a Retry-After header, or None."""
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    value = headers.get("retry-after")
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def classify(exc, rate_limit_types=(), server_error_types=()):
    """Return 'terminal', 'retryable', or 'unknown' for an exception."""
    if _error_code(exc) in TERMINAL_CODES:
        return "terminal"
    if rate_limit_types and isinstance(exc, rate_limit_types):
        return "retryable"
    if server_error_types and isinstance(exc, server_error_types):
        return "retryable"
    return "unknown"


def call_with_retry(fn, rate_limit_types=(), server_error_types=(), sleep=time.sleep):
    """Call fn(), retrying transient failures up to MAX_ATTEMPTS in total."""
    last = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            return fn()
        except Exception as exc:
            kind = classify(exc, rate_limit_types, server_error_types)
            if kind == "terminal":
                raise QuotaExhausted(
                    f"Quota or billing limit reached ({_error_code(exc)}). "
                    "Retrying cannot restore access; add credit or raise the "
                    "limit before running again."
                ) from exc
            if kind == "unknown":
                raise
            last = exc
            if attempt == MAX_ATTEMPTS - 1:
                break
            wait = _retry_after(exc)
            if wait is None:
                wait = BASE_BACKOFF * (2 ** attempt)
            sleep(wait)
    raise RuntimeError(
        f"Failed after {MAX_ATTEMPTS} attempts: {last}"
    ) from last
