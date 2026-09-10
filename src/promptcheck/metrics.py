def normalized_exact_match(response: str, expected: str) -> float:
    if not expected.strip():
        raise ValueError("expected string cannot be empty")
    return 1.0 if response.strip().lower() == expected.strip().lower() else 0.0


def contains_substring(response: str, expected: str) -> float:
    if not expected.strip():
        raise ValueError("expected string cannot be empty")
    return 1.0 if expected.strip().lower() in response.strip().lower() else 0.0