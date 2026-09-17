"""Live tests. Deselected by default; run with: uv run pytest -m live"""

import os
import pytest
from evalquill.providers import openai_llm

pytestmark = pytest.mark.live

MODEL = "gpt-4o-mini"


@pytest.fixture(autouse=True)
def require_key():
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")


def test_live_returns_a_string():
    llm, metadata = openai_llm(MODEL, max_tokens=10)
    response = llm("Reply with exactly the word: pong")
    assert isinstance(response, str)
    assert len(response) > 0
    print(f"\nmodel returned: {response!r}")
    print(f"metadata: {metadata}")