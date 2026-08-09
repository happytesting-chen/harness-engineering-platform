"""Repeat-run determinism.

Unchanged reviewed input and configuration must yield an equivalent outcome and
one equivalent minimal result on every run.
"""

from __future__ import annotations

import json
from pathlib import Path

from claims import decide, process

FIXTURE_DIR = Path(__file__).parent / "fixtures"
ALL = sorted(p.name for p in FIXTURE_DIR.glob("*.json"))


def _load(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_decision_is_stable_across_repeated_runs() -> None:
    for name in ALL:
        record = _load(name)
        first = decide(record)
        for _ in range(4):
            assert decide(record) == first, name


def test_written_result_is_byte_identical_across_runs(tmp_path: Path) -> None:
    record = _load("SYN-FIXTURE-001-approved.json")

    process(record, boundary=tmp_path / "run_a")
    process(record, boundary=tmp_path / "run_b")

    a = (tmp_path / "run_a" / "SYN-CLAIM-001.result.json").read_bytes()
    b = (tmp_path / "run_b" / "SYN-CLAIM-001.result.json").read_bytes()
    assert a == b
