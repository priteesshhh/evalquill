def mock_llm(prompt: str) -> str:
    responses = {
        "what is the capital of france?": "The capital of France is Paris.",
        "what is 2 + 2?": "2 + 2 equals 4.",
        "what is the capital of germany?": "The capital of Germany is Berlin.",
        "what is the capital of india?": "The capital of India is Delhi.",
        "what is 7 + 2?": "7 + 2 equals 9.",
        "what is first president of united states of america?": "The first president of the United States of America is George Washington.",
    }
    return responses.get(prompt.strip().lower(), "I don't know.")