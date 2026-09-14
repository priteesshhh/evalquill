def evaluate(prompt: str, expected: str, response: str, metrics: list) -> dict:
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
                prompt=item["prompt"],
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
    if not results:
        return {}
    
    totals = {}
    for result in results:
        for metric_name, score in result["scores"].items():
            if metric_name not in totals:
                totals[metric_name] = 0.0
            totals[metric_name] += score
    
    return {metric: total / len(results) for metric, total in totals.items()}
def threshold_check(summary: dict, thresholds: dict) -> dict:
    results = {}
    for metric, minimum in thresholds.items():
        if metric not in summary:
            results[metric] = "NOT RUN"
        else:
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
    import math
    if math.isnan(value) or math.isinf(value):
        raise ValueError(f"Score '{name}' must be finite, got {value}.")
    if not (0.0 <= value <= 1.0):
        raise ValueError(f"Score '{name}' must be between 0 and 1, got {value}.")