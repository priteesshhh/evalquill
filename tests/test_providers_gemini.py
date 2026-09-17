import pytest
from evalquill.providers import gemini_llm


class FakeResponse:
    def __init__(self, text):
        self.text = text


class FakeModels:
    def __init__(self, text=None, error=None):
        self.text = text
        self.error = error
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return FakeResponse(self.text)


class FakeClient:
    def __init__(self, text=None, error=None):
        self.models = FakeModels(text, error)


def test_returns_model_text():
    client = FakeClient(text="Paris")
    llm, _ = gemini_llm(client=client)
    assert llm("What is the capital of France?") == "Paris"


def test_sends_prompt_as_contents():
    client = FakeClient(text="ok")
    llm, _ = gemini_llm(client=client)
    llm("hello")
    assert client.models.calls[0]["contents"] == "hello"


def test_includes_system_instruction_when_given():
    client = FakeClient(text="ok")
    llm, _ = gemini_llm(system_prompt="Answer in one word.", client=client)
    llm("hello")
    assert client.models.calls[0]["config"]["system_instruction"] == "Answer in one word."


def test_omits_system_instruction_when_absent():
    client = FakeClient(text="ok")
    llm, _ = gemini_llm(client=client)
    llm("hello")
    assert "system_instruction" not in client.models.calls[0]["config"]


def test_defaults_to_temperature_zero():
    client = FakeClient(text="ok")
    llm, _ = gemini_llm(client=client)
    llm("hello")
    assert client.models.calls[0]["config"]["temperature"] == 0.0


def test_metadata_records_settings():
    client = FakeClient(text="ok")
    _, metadata = gemini_llm("gemini-3.6-flash", temperature=0.3, client=client)
    assert metadata["provider"] == "gemini"
    assert metadata["model"] == "gemini-3.6-flash"
    assert metadata["temperature"] == 0.3


def test_none_text_raises():
    client = FakeClient(text=None)
    llm, _ = gemini_llm(client=client)
    with pytest.raises(RuntimeError, match="returned no content"):
        llm("hello")


def test_api_errors_propagate():
    client = FakeClient(error=ConnectionError("network down"))
    llm, _ = gemini_llm(client=client)
    with pytest.raises(ConnectionError):
        llm("hello")