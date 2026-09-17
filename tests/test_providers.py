import pytest
from evalquill.providers import openai_llm


class FakeMessage:
    def __init__(self, content):
        self.content = content


class FakeChoice:
    def __init__(self, content):
        self.message = FakeMessage(content)


class FakeResponse:
    def __init__(self, content):
        self.choices = [FakeChoice(content)]


class FakeCompletions:
    def __init__(self, content=None, error=None):
        self.content = content
        self.error = error
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return FakeResponse(self.content)


class FakeClient:
    def __init__(self, content=None, error=None):
        self.chat = type("Chat", (), {})()
        self.chat.completions = FakeCompletions(content, error)


def test_returns_model_content():
    client = FakeClient(content="Paris")
    llm, _ = openai_llm("gpt-4o-mini", client=client)
    assert llm("What is the capital of France?") == "Paris"


def test_sends_user_message():
    client = FakeClient(content="ok")
    llm, _ = openai_llm("gpt-4o-mini", client=client)
    llm("hello")
    messages = client.chat.completions.calls[0]["messages"]
    assert messages == [{"role": "user", "content": "hello"}]


def test_includes_system_prompt_when_given():
    client = FakeClient(content="ok")
    llm, _ = openai_llm("gpt-4o-mini", system_prompt="Answer in one word.", client=client)
    llm("hello")
    messages = client.chat.completions.calls[0]["messages"]
    assert messages[0] == {"role": "system", "content": "Answer in one word."}
    assert messages[1] == {"role": "user", "content": "hello"}


def test_defaults_to_temperature_zero():
    client = FakeClient(content="ok")
    llm, _ = openai_llm("gpt-4o-mini", client=client)
    llm("hello")
    assert client.chat.completions.calls[0]["temperature"] == 0.0


def test_passes_extra_kwargs_through():
    client = FakeClient(content="ok")
    llm, _ = openai_llm("gpt-4o-mini", client=client, max_tokens=50)
    llm("hello")
    assert client.chat.completions.calls[0]["max_tokens"] == 50


def test_metadata_records_settings():
    client = FakeClient(content="ok")
    _, metadata = openai_llm("gpt-4o-mini", system_prompt="Be terse.", temperature=0.2, client=client)
    assert metadata["provider"] == "openai"
    assert metadata["model"] == "gpt-4o-mini"
    assert metadata["temperature"] == 0.2
    assert metadata["system_prompt"] == "Be terse."


def test_none_content_raises():
    client = FakeClient(content=None)
    llm, _ = openai_llm("gpt-4o-mini", client=client)
    with pytest.raises(RuntimeError, match="returned no content"):
        llm("hello")


def test_api_errors_propagate():
    client = FakeClient(error=ConnectionError("network down"))
    llm, _ = openai_llm("gpt-4o-mini", client=client)
    with pytest.raises(ConnectionError):
        llm("hello")