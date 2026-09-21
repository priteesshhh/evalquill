"""evaluate_dataset must reject a structurally invalid dataset before
making any model call, and identify the case when execution fails.
"""

import pytest
from evalquill import evaluate_dataset
from evalquill.metrics import contains_substring


class CountingLLM:
    def __init__(self, reply="a", fail_on=None, error=None):
        self.calls = 0
        self.reply = reply
        self.fail_on = fail_on
        self.error = error

    def __call__(self, prompt):
        self.calls += 1
        if self.fail_on is not None and prompt == self.fail_on:
            raise self.error
        return self.reply


def case(i, **overrides):
    base = {"id": f"c{i}", "prompt": f"p{i}", "expected": "a"}
    base.update(overrides)
    return base


# --- structural problems: zero calls ---

def test_duplicate_id_late_in_dataset_makes_zero_calls():
    llm = CountingLLM()
    data = [case(1), case(2), case(3, id="c1")]
    with pytest.raises(ValueError, match="Duplicate case id"):
        evaluate_dataset(data, llm, [contains_substring])
    assert llm.calls == 0


def test_explicit_id_colliding_with_generated_id_makes_zero_calls():
    llm = CountingLLM()
    data = [{"id": "case_1", "prompt": "p", "expected": "a"},
            {"prompt": "q", "expected": "a"}]          # generated id: case_1
    with pytest.raises(ValueError, match="Duplicate case id"):
        evaluate_dataset(data, llm, [contains_substring])
    assert llm.calls == 0


@pytest.mark.parametrize("field", ["prompt", "expected"])
def test_missing_field_makes_zero_calls(field):
    llm = CountingLLM()
    broken = case(2)
    del broken[field]
    with pytest.raises(ValueError, match="missing"):
        evaluate_dataset([case(1), broken], llm, [contains_substring])
    assert llm.calls == 0


@pytest.mark.parametrize("field,bad", [("prompt", None), ("prompt", 5),
                                       ("expected", None), ("expected", 9)])
def test_non_string_field_makes_zero_calls(field, bad):
    llm = CountingLLM()
    with pytest.raises(ValueError, match=field):
        evaluate_dataset([case(1), case(2, **{field: bad})], llm, [contains_substring])
    assert llm.calls == 0


def test_non_dict_row_makes_zero_calls():
    llm = CountingLLM()
    with pytest.raises(ValueError):
        evaluate_dataset([case(1), "not a row"], llm, [contains_substring])
    assert llm.calls == 0


def test_dataset_not_a_list_makes_zero_calls():
    llm = CountingLLM()
    with pytest.raises(ValueError):
        evaluate_dataset({"c1": case(1)}, llm, [contains_substring])
    assert llm.calls == 0


def test_empty_metric_list_makes_zero_calls():
    llm = CountingLLM()
    with pytest.raises(ValueError, match="metric"):
        evaluate_dataset([case(1)], llm, [])
    assert llm.calls == 0


def test_non_callable_metric_makes_zero_calls():
    llm = CountingLLM()
    with pytest.raises(ValueError, match="metric"):
        evaluate_dataset([case(1)], llm, ["not a function"])
    assert llm.calls == 0


# --- execution problems: identify the case ---

def test_llm_error_names_the_case_and_keeps_cause():
    llm = CountingLLM(fail_on="p2", error=ConnectionError("network down"))
    with pytest.raises(RuntimeError, match="c2") as info:
        evaluate_dataset([case(1), case(2), case(3)], llm, [contains_substring])
    assert isinstance(info.value.__cause__, ConnectionError)


def test_non_string_response_names_the_case():
    llm = CountingLLM(reply=None)
    with pytest.raises(RuntimeError, match="c1"):
        evaluate_dataset([case(1)], llm, [contains_substring])


# --- must keep working ---

def test_valid_dataset_calls_once_per_case():
    llm = CountingLLM()
    results = evaluate_dataset([case(1), case(2), case(3)], llm, [contains_substring])
    assert llm.calls == 3
    assert [r["id"] for r in results] == ["c1", "c2", "c3"]
