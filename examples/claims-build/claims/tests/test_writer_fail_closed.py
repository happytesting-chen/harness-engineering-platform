"""Writer boundary tests — one minimal write, fail-closed on everything else.

A result is successful only when exactly one minimal write completes inside the
approved local boundary. Duplicate, out-of-bound, or unattributable writes fail
closed (WriteBoundaryError) and cannot support fixture success.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from claims.outcomes import APPROVED, PENDING_REVIEW, Outcome
from claims.writer import WriteBoundaryError, write_result


def test_one_minimal_result_is_written(tmp_path: Path) -> None:
    outcome = Outcome(APPROVED, "EXACT_COVERAGE", "SYN-CLAIM-001")

    path = write_result(outcome, tmp_path)

    # Exactly one file, inside the boundary.
    written = list(tmp_path.iterdir())
    assert written == [path]
    assert path.parent == tmp_path.resolve()

    # Minimal payload: only the three attributable fields, nothing else.
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload == {
        "claim_id": "SYN-CLAIM-001",
        "outcome": "APPROVED",
        "reason_code": "EXACT_COVERAGE",
    }


def test_duplicate_write_fails_closed(tmp_path: Path) -> None:
    outcome = Outcome(APPROVED, "EXACT_COVERAGE", "SYN-CLAIM-001")
    write_result(outcome, tmp_path)

    with pytest.raises(WriteBoundaryError):
        write_result(outcome, tmp_path)

    # The original result is untouched — still exactly one file.
    assert len(list(tmp_path.iterdir())) == 1


def test_unattributable_result_is_refused(tmp_path: Path) -> None:
    outcome = Outcome(PENDING_REVIEW, "MALFORMED_RECORD", None)

    with pytest.raises(WriteBoundaryError):
        write_result(outcome, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_claim_id_with_separator_cannot_escape_boundary(tmp_path: Path) -> None:
    boundary = tmp_path / "results"
    # A traversal-style id must not land outside the boundary.
    outcome = Outcome(APPROVED, "EXACT_COVERAGE", "../escape")

    with pytest.raises(WriteBoundaryError):
        write_result(outcome, boundary)
    # Nothing was written anywhere above the boundary.
    assert not (tmp_path / "escape.result.json").exists()
