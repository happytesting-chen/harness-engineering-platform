"""Fixture-driven decision tests — one committed synthetic case per class.

Each fixture carries an ``expected`` oracle. The oracle is asserted against in
the test ONLY; it is never passed into decision logic (claims.decide reads the
claim, not expected). Covers: APPROVED, REJECTED, and PENDING_REVIEW (untrusted,
malformed, safety-flagged).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from claims import decide

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


ALL_FIXTURES = sorted(p.name for p in FIXTURE_DIR.glob("*.json"))


@pytest.mark.parametrize("fixture_name", ALL_FIXTURES)
def test_fixture_matches_expected_oracle(fixture_name: str) -> None:
    record = _load(fixture_name)
    expected = record["expected"]  # oracle — asserted, never fed to decide()

    outcome = decide(record)

    assert outcome.outcome == expected["outcome"], fixture_name
    assert outcome.reason_code == expected["reason_code"], fixture_name


def test_every_terminal_outcome_is_represented() -> None:
    """The committed set must exercise all three terminal outcomes."""
    seen = {decide(_load(name)).outcome for name in ALL_FIXTURES}
    assert seen == {"APPROVED", "REJECTED", "PENDING_REVIEW"}


def test_expected_block_does_not_influence_decision() -> None:
    """A lying oracle must not change the routed outcome (oracle is inert)."""
    record = _load("SYN-FIXTURE-001-approved.json")
    tampered = json.loads(json.dumps(record))
    tampered["expected"] = {"outcome": "REJECTED", "reason_code": "WHATEVER"}

    assert decide(tampered).outcome == "APPROVED"
