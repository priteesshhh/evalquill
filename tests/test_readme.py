"""Every Python example in the README must run and print what it claims."""

import contextlib
import io
import os
import re
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent
README = REPO / os.environ.get("EVALQUILL_README", "README.md")
TICKS = "`" * 3
FENCE = re.compile(TICKS + r"(\w*)\n(.*?)" + TICKS, re.S)


def test_readme_examples_run_and_match_documented_output(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    blocks = FENCE.findall(README.read_text(encoding="utf-8"))
    namespace = {}
    ran = 0

    for i, (lang, body) in enumerate(blocks):
        if lang != "python" or "evalquill.providers" in body:
            continue
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            exec(compile(body, f"README python block {i}", "exec"), namespace)
        ran += 1
        printed = out.getvalue().strip()
        if printed:
            assert i + 1 < len(blocks), f"block {i} prints but no output block follows"
            documented = blocks[i + 1][1].strip()
            assert printed == documented, f"block {i} printed:\n{printed}\nREADME shows:\n{documented}"

    assert ran >= 4, f"expected at least 4 runnable python blocks, ran {ran}"

    # The README says the threshold test passes and the regression test fails.
    namespace["test_accuracy_meets_threshold"]()
    with pytest.raises(AssertionError, match="invite"):
        namespace["test_no_case_stops_passing"]()
