import math


def evaluate(expected: str, response: str, metrics: list) -> dict:
    _validate_metrics(metrics)
    results = {}
    for metric in metrics:
        score = metric(response, expected)
        _validate_score(score, metric.__name__)
        results[metric.__name__] = score
    return results


def evaluate_dataset(dataset: list, llm, metrics: list) -> list:
    _validate_metrics(metrics)
    results = []
    seen_ids = set()
    for i, item in enumerate(dataset):
        case_id = item.get("id", f"case_{i}")
        if case_id in seen_ids:
            raise ValueError(f"Duplicate case id: '{case_id}'. Each case must have a unique id.")
        seen_ids.add(case_id)

        response = llm(item["prompt"])
        try:
            result = evaluate(
                expected=item["expected"],
                response=response,
                metrics=metrics
            )
        except Exception as e:
            raise RuntimeError(
                f"Evaluation failed on case '{case_id}' "
                f"(prompt: '{item['prompt']}') — {e}"
            ) from e
        results.append({
            "id": case_id,
            "prompt": item["prompt"],
            "expected": item["expected"],
            "response": response,
            "scores": result
        })
    return results


def summary_scores(results: list) -> dict:
    """Mean of each metric across results, at full precision.

    Every row must carry the same metric set with valid scores. A row missing
    a metric is rejected rather than averaged as zero.
    """
    if not results:
        return {}

    metric_set = None
    totals = {}
    for index, result in enumerate(results):
        if not isinstance(result, dict) or not isinstance(result.get("scores"), dict):
            raise ValueError(f"Result {index} has no scores dict.")
        scores = result["scores"]

        names = set(scores)
        if metric_set is None:
            metric_set = names
        elif names != metric_set:
            raise ValueError(
                f"Inconsistent metric sets: result 0 has {sorted(metric_set)}, "
                f"result {index} has {sorted(names)}. A missing score would "
                "otherwise be averaged as zero."
            )

        for name, score in scores.items():
            _validate_score(score, name)
            totals[name] = totals.get(name, 0.0) + score

    return {name: total / len(results) for name, total in totals.items()}


def threshold_check(summary: dict, thresholds: dict) -> dict:
    """PASS, FAIL or NOT RUN per threshold.

    NOT RUN means the metric was never measured. Invalid thresholds or
    summary values are rejected rather than compared.
    """
    for metric, minimum in thresholds.items():
        try:
            _validate_score(minimum, metric)
        except ValueError as e:
            raise ValueError(f"Invalid threshold for '{metric}': {e}") from e

    results = {}
    for metric, minimum in thresholds.items():
        if metric not in summary:
            results[metric] = "NOT RUN"
            continue
        _validate_score(summary[metric], metric)
        results[metric] = "PASS" if summary[metric] >= minimum else "FAIL"
    return results


def _validate_metrics(metrics: list) -> None:
    seen = set()
    for metric in metrics:
        if metric.__name__ in seen:
            raise ValueError(f"Duplicate metric name: '{metric.__name__}'. Each metric must have a unique name.")
        seen.add(metric.__name__)


def _validate_score(value: float, name: str) -> None:
    if isinstance(value, bool):
        raise ValueError(f"Score '{name}' must be a float, not a boolean.")
    if not isinstance(value, (int, float)):
        raise ValueError(f"Score '{name}' must be a number, got {type(value).__name__}.")
    if math.isnan(value) or math.isinf(value):
        raise ValueError(f"Score '{name}' must be finite, got {value}.")
    if not (0.0 <= value <= 1.0):
        raise ValueError(f"Score '{name}' must be between 0 and 1, got {value}.")
