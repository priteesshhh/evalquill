"""Run one prompt version over one split and save the results.

Usage:
    uv run case_study/run.py v1_naive holdout
    uv run case_study/run.py v1_naive holdout 2      # repeat index

Writes to case_study/runs/<version>_<split>[_r<n>].json, or to an override
directory set by EVALQUILL_RUNS_DIR. Refuses an existing destination before
making any model calls.
"""

import csv
import hashlib
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from prompts import PROMPTS
from split import TRAIN, HOLDOUT
from retry import call_with_retry
from evalquill import evaluate
from evalquill.metrics import normalized_exact_match
from evalquill.providers import openai_llm
from evalquill.storage import save_run

MODEL = "gpt-4o-mini"
TEMPERATURE = 0.0
MAX_TOKENS = 10
SECONDS_BETWEEN_CALLS = 1.0

HERE = Path(__file__).parent


def runs_dir() -> Path:
    return Path(os.environ.get("EVALQUILL_RUNS_DIR", HERE / "runs"))


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_tickets() -> dict:
    text = (HERE / "tickets.md").read_text(encoding="utf-8")
    found = re.findall(r"\*\*(t\d\d)\*\* — (.+)", text)
    return {tid: body.strip() for tid, body in found}


def load_labels() -> dict:
    labels = {}
    with (HERE / "labels.csv").open(encoding="utf-8") as f:
        for row in csv.reader(line for line in f if not line.startswith("#")):
            if len(row) == 2 and row[0] != "id":
                labels[row[0]] = row[1].strip()
    return labels


def main() -> None:
    version, split_name = sys.argv[1], sys.argv[2]
    repeat = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else None

    ids = {"train": TRAIN, "holdout": HOLDOUT}[split_name]
    system_prompt = PROMPTS[version]

    tickets = load_tickets()
    labels = load_labels()

    missing = [i for i in ids if i not in tickets or i not in labels]
    if missing:
        raise SystemExit(f"Missing ticket text or label for: {missing}")

    dataset = [{"id": i, "prompt": tickets[i], "expected": labels[i]} for i in ids]

    # Resolve destinations and refuse collisions BEFORE any client or call.
    stem = f"{version}_{split_name}" + (f"_r{repeat}" if repeat else "")
    out = runs_dir() / f"{stem}.json"
    partial = runs_dir() / f"{stem}.partial.json"
    for path in (out, partial):
        if path.exists():
            raise SystemExit(
                f"Refusing to overwrite {path}. No model calls were made. "
                "Move or delete it, or pass a different repeat index."
            )

    from openai import OpenAI, RateLimitError, InternalServerError, APIConnectionError

    # max_retries=0: this module owns the retry budget, so SDK retries do not
    # multiply the wrapper's 3-attempt limit.
    client = OpenAI(max_retries=0)

    base_llm, metadata = openai_llm(
        MODEL,
        system_prompt=system_prompt,
        temperature=TEMPERATURE,
        client=client,
        max_tokens=MAX_TOKENS,
    )

    metadata["prompt_version"] = version
    metadata["split"] = split_name
    metadata["repeat"] = repeat
    metadata["sdk_max_retries"] = 0
    metadata["seconds_between_calls"] = SECONDS_BETWEEN_CALLS
    metadata["labels_sha256"] = _sha256_file(HERE / "labels.csv")
    metadata["tickets_sha256"] = _sha256_file(HERE / "tickets.md")

    calls = {"n": 0}

    def resilient_llm(prompt: str) -> str:
        if calls["n"]:
            time.sleep(SECONDS_BETWEEN_CALLS)
        calls["n"] += 1
        print(f"  {calls['n']}/{len(dataset)}", flush=True)
        return call_with_retry(
            lambda: base_llm(prompt),
            rate_limit_types=(RateLimitError,),
            server_error_types=(InternalServerError, APIConnectionError),
        )

    print(f"Running {version} on {split_name} ({len(dataset)} cases), model {MODEL}")

    results = []
    try:
        for case in dataset:
            response = resilient_llm(case["prompt"])
            results.append({
                "id": case["id"],
                "prompt": case["prompt"],
                "expected": case["expected"],
                "response": response,
                "scores": evaluate(case["expected"], response, [normalized_exact_match]),
            })
    except BaseException:
        if results:
            metadata["incomplete"] = True
            metadata["completed_cases"] = len(results)
            metadata["expected_cases"] = len(dataset)
            save_run(results, str(partial), metadata=metadata)
            print(f"Stopped after {len(results)}/{len(dataset)}. Partial saved to {partial}")
        raise

    metadata["incomplete"] = False
    save_run(results, str(out), metadata=metadata)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
