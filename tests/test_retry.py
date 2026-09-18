import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "case_study"))

from retry import (
    call_with_retry, classify, QuotaExhausted, MAX_ATTEMPTS, TERMINAL_CODES,
)


class FakeHeaders(dict):
    pass


class FakeResponse:
    def __init__(self, headers=None):
        self.headers = FakeHeaders(headers or {})


class FakeRateLimit(Exception):
    def __init__(self, code=None, retry_after=None):
        super().__init__(f"429 {code}")
        self.code = code
        self.response = FakeResponse(
            {"retry-after": str(retry_after)} if retry_after else {}
        )


class FakeServerError(Exception):
    def __init__(self):
        super().__init__("503")
        self.code = None
        self.response = FakeResponse()


class FakeBadRequest(Exception):
    def __init__(self):
        super().__init__("400")
        self.code = "invalid_request"


TYPES = {"rate_limit_types": (FakeRateLimit,), "server_error_types": (FakeServerError,)}


def test_quota_exhaustion_stops_immediately():
    calls = []

    def fn():
        calls.append(1)
        raise FakeRateLimit(code="insufficient_quota")

    with pytest.raises(QuotaExhausted, match="Retrying cannot restore access"):
        call_with_retry(fn, sleep=lambda s: None, **TYPES)
    assert len(calls) == 1


def test_all_terminal_codes_stop_immediately():
    for code in TERMINAL_CODES:
        calls = []

        def fn():
            calls.append(1)
            raise FakeRateLimit(code=code)

        with pytest.raises(QuotaExhausted):
            call_with_retry(fn, sleep=lambda s: None, **TYPES)
        assert len(calls) == 1, f"retried on terminal code {code}"


def test_transient_rate_limit_retries_then_succeeds():
    calls = []

    def fn():
        calls.append(1)
        if len(calls) < 3:
            raise FakeRateLimit(code="rate_limit_exceeded")
        return "ok"

    assert call_with_retry(fn, sleep=lambda s: None, **TYPES) == "ok"
    assert len(calls) == 3


def test_server_error_retries():
    calls = []

    def fn():
        calls.append(1)
        if len(calls) < 2:
            raise FakeServerError()
        return "ok"

    assert call_with_retry(fn, sleep=lambda s: None, **TYPES) == "ok"


def test_never_exceeds_max_attempts():
    calls = []

    def fn():
        calls.append(1)
        raise FakeServerError()

    with pytest.raises(RuntimeError, match=f"after {MAX_ATTEMPTS} attempts"):
        call_with_retry(fn, sleep=lambda s: None, **TYPES)
    assert len(calls) == MAX_ATTEMPTS


def test_respects_retry_after_header():
    waits = []
    calls = []

    def fn():
        calls.append(1)
        if len(calls) < 2:
            raise FakeRateLimit(code="rate_limit_exceeded", retry_after=42)
        return "ok"

    call_with_retry(fn, sleep=waits.append, **TYPES)
    assert waits == [42.0]


def test_backs_off_when_no_retry_after():
    waits = []

    def fn():
        raise FakeServerError()

    with pytest.raises(RuntimeError):
        call_with_retry(fn, sleep=waits.append, **TYPES)
    assert waits == [2.0, 4.0]


def test_unknown_errors_propagate_without_retry():
    calls = []

    def fn():
        calls.append(1)
        raise FakeBadRequest()

    with pytest.raises(FakeBadRequest):
        call_with_retry(fn, sleep=lambda s: None, **TYPES)
    assert len(calls) == 1


def test_classification_uses_codes_not_substrings():
    # A message containing "503" must not be treated as a server error.
    class Misleading(Exception):
        code = "invalid_request"

    exc = Misleading("ticket 503 failed with quota insufficient_quota in text")
    assert classify(exc, (FakeRateLimit,), (FakeServerError,)) == "unknown"


def test_code_read_from_body_when_attribute_absent():
    class BodyOnly(Exception):
        body = {"error": {"code": "insufficient_quota"}}

    calls = []

    def fn():
        calls.append(1)
        raise BodyOnly()

    with pytest.raises(QuotaExhausted):
        call_with_retry(fn, sleep=lambda s: None, **TYPES)
    assert len(calls) == 1
