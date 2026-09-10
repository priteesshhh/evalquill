import pytest
from promptcheck import evaluate, evaluate_dataset, summary_scores, threshold_check
from promptcheck.metrics import normalized_exact_match, contains_substring
from promptcheck.llm import mock_llm

dataset = [
    {"prompt": "What is the capital of India?", "expected": "Delhi"},
    {"prompt": "What is 7 + 2?", "expected": "9"},
    {"prompt": "What is first president of United States of America?", "expected": "George Washington"},
]

results = evaluate_dataset(
    dataset=dataset,
    llm=mock_llm,
    metrics=[normalized_exact_match, contains_substring]
)

for r in results:
    print(f"\nPrompt: {r['prompt']}")
    print(f"Expected: {r['expected']}")
    print(f"Response: {r['response']}")
    print(f"Scores: {r['scores']}")

summary = summary_scores(results)
print("\n--- Summary ---")
print(summary)

thresholds = {
    "normalized_exact_match": 0.5,
    "contains_substring": 0.8,
}

print("\n--- Threshold Check ---")
print(threshold_check(summary, thresholds))

def test_duplicate_metric_names_rejected():
    from promptcheck.metrics import normalized_exact_match
    with pytest.raises(ValueError, match="Duplicate metric name"):
        evaluate("q", "a", "a", [normalized_exact_match, normalized_exact_match])

cat >> tests/test_evaluate.py << 'EOF'

def test_score_rejects_boolean():
    def bad_metric(response, expected):
        return True
    with pytest.raises(ValueError, match="float, not a boolean"):
        evaluate("q", "a", "a", [bad_metric])

def test_score_rejects_nan():
    import math
    def bad_metric(response, expected):
        return math.nan
    with pytest.raises(ValueError, match="finite"):
        evaluate("q", "a", "a", [bad_metric])

def test_score_rejects_out_of_range():
    def bad_metric(response, expected):
        return 1.5
    with pytest.raises(ValueError, match="between 0 and 1"):
        evaluate("q", "a", "a", [bad_metric])
EOF

cat >> tests/test_evaluate.py << 'EOF'

def test_metric_error_gives_useful_context():
    def crashing_metric(response, expected):
        raise RuntimeError("something went wrong")
    dataset = [{"prompt": "What is 2+2?", "expected": "4"}]
    with pytest.raises(RuntimeError, match="case 0"):
        evaluate_dataset(dataset, mock_llm, [crashing_metric])
EOF

