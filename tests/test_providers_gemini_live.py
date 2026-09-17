"""Live tests. Deselected by default; run with: uv run pytest -m live"""

import os
import pytest
from evalquill.providers import gemini_llm

pytestmark = pytest.mark.live

MODEL = "gemini-3.6-flash"


@pytest.fixture(autouse=True)
def require_key():
    if not os.environ.get("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set")


def test_live_returns_a_string():
    llm, metadata = gemini_llm(MODEL)
    response = llm("Reply with exactly the word: pong")
    assert isinstance(response, str)
    assert len(response) > 0
    print(f"\nmodel returned: {response!r}")
    print(f"metadata: {metadata}")