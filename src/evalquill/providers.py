"""Adapters turning provider clients into plain llm(prompt) -> str callables."""


def openai_llm(
    model: str,
    system_prompt: str | None = None,
    temperature: float = 0.0,
    client=None,
    **kwargs,
):
    """Build an llm(prompt) -> str callable backed by OpenAI chat completions.

    Returns (llm, metadata). Pass metadata to save_run so the run records
    which model and settings produced it.

    client is injectable for testing; when omitted, a real OpenAI client is
    constructed and the openai package must be installed.
    """
    if client is None:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError(
                "The openai package is required for openai_llm. "
                "Install it with: pip install openai"
            ) from e
        client = OpenAI()

    def llm(prompt: str) -> str:
        messages = []
        if system_prompt is not None:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            **kwargs,
        )

        content = response.choices[0].message.content
        if content is None:
            raise RuntimeError(
                f"Model '{model}' returned no content. "
                "This can happen when the response was filtered or truncated."
            )
        return content

    metadata = {
        "provider": "openai",
        "model": model,
        "temperature": temperature,
        "system_prompt": system_prompt,
        **kwargs,
    }

    return llm, metadata