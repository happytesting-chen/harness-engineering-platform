"""claims_runner entrypoint tests.

Proves the tool the governance allowlist names is a real, invokable, fail-closed
entrypoint — not just a policy token. Covers: decide-only, one-minimal-write,
duplicate-write fail-closed, and unreadable/invalid input fail-closed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from claims.runner import run

FIXTURE_DIR = Path(__file__).parent / "fixtures"
APPROVED = FIXTURE_DIR / "SYN-FIXTURE-001-approved.json"


def test_decide_only_returns_zero_no_write(tmp_path: Path, capsys) -> None:
    code = run(APPROVED, out_dir=None)
    assert code == 0
    line = json.loads(capsys.readouterr().out.strip())
    assert line == {
        "claim_id": "SYN-CLAIM-001",
        "outcome": "APPROVED",
        "reason_code": "EXACT_COVERAGE",
    }
    assert list(tmp_path.iterdir()) == []  # nothing written when out_dir is None


def test_writes_one_minimal_result(tmp_path: Path) -> None:
    code = run(APPROVED, out_dir=tmp_path)
    assert code == 0
    written = list(tmp_path.iterdir())
    assert len(written) == 1
    payload = json.loads(written[0].read_text(encoding="utf-8"))
    assert payload == {
        "claim_id": "SYN-CLAIM-001",
        "outcome": "APPROVED",
        "reason_code": "EXACT_COVERAGE",
    }


def test_duplicate_run_fails_closed(tmp_path: Path) -> None:
    assert run(APPROVED, out_dir=tmp_path) == 0
    # Second run against the same boundary must refuse (no overwrite).
    assert run(APPROVED, out_dir=tmp_path) == 2
    assert len(list(tmp_path.iterdir())) == 1


def test_unreadable_fixture_fails_closed(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.json"
    with pytest.raises(SystemExit) as exc:
        run(missing, out_dir=None)
    assert exc.value.code == 2


def test_invalid_json_fails_closed(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{ not valid json", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        run(bad, out_dir=None)
    assert exc.value.code == 2
