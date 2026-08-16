"""Claims-register invariants — I1 through I5 (spec §4.4.4, §4.5).

Stdlib only. `python3 tests/test_mechanisms.py` is the authoritative runner;
the pytest wrapper at the bottom is an optional path.
"""
import json
import re
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "Security-kit"))

import check_coverage as cc  # noqa: E402


# --- matrix census: the join surface, pinned ------------------------------

def case_matrix_parses_into_rows():
    """parse_matrix_rows sees every row parse_matrix does, with more columns."""
    md = cc.MATRIX_PATH.read_text()
    rows = cc.parse_matrix_rows(md)
    flat = cc.parse_matrix(md)
    assert set(rows) == set(flat), (
        f"parse_matrix_rows and parse_matrix disagree: "
        f"{set(rows) ^ set(flat)}"
    )
    assert len(rows) == 23, f"expected 23 matrix rows, got {len(rows)}"


def case_every_matrix_row_has_a_status_token():
    """An unlabelled row is a claim with no stated strength (spec §4.4.4:1974).

    Three rows lacked one before this series: SEC-TOOL-001 (merged into
    SEC-PHASE-001), SEC-EGRESS-001 (labelled MECHANICAL, objective narrowed)
    and SEC-XXX-001 (labelled GAP — nothing implements a placeholder).
    """
    rows = cc.parse_matrix_rows(cc.MATRIX_PATH.read_text())
    unlabelled = sorted(k for k, r in rows.items() if r.status_token is None)
    assert unlabelled == [], f"unlabelled matrix rows: {unlabelled}"


def case_gap_row_count_is_twelve():
    """8 shipped GAP (Known-Gaps table) + 3 new GAP rows (SEC-PROOF-GAP-001,
    SEC-HARDEN-GAP-001, SEC-KIRO-GAP-001) + 1 per-project placeholder row
    (SEC-XXX-001, labelled GAP because a placeholder claims nothing) = 12.

    An earlier plan draft derived 11 (8 shipped + 3 new) and stopped there,
    omitting SEC-XXX-001. That row is not optional: it must carry SOME status
    token to satisfy case_every_matrix_row_has_a_status_token, and GAP is the
    only honest one for a placeholder — so the count is inescapably 12, not
    11. Do not "fix" this back to 11; that was the arithmetic slip, not this.
    """
    rows = cc.parse_matrix_rows(cc.MATRIX_PATH.read_text())
    gaps = sorted(k for k, r in rows.items() if r.status_token == "GAP")
    assert len(gaps) == 12, f"expected 12 GAP rows, got {len(gaps)}: {gaps}"


def case_every_control_row_has_five_cells():
    """A literal `|` in a prose cell is invisible to row COUNT but not to column
    count. `parse_matrix_rows` rejects `< 5` cells but silently accepts `> 5`: a
    stray pipe in, say, an Objective cell splits it into two cells, shifting every
    later column left by one — Verification silently becomes the old Location
    text, and `check()` rule 3 then validates the wrong string against the wrong
    row. `case_matrix_parses_into_rows`'s row-count assertion cannot see this
    class of defect at all, because a 6-cell row still parses as exactly one row.

    Scoped to the three control tables (Template baseline / Known gaps /
    Per-project rows) between `## Template baseline` and `## Completion Rules` —
    NOT the whole document. The Status legend table above them is legitimately
    2 cells wide (`| Status | Meaning |`), and it is correctly skipped by
    `parse_matrix_rows` too (it has no Control ID column); a naive document-wide
    `!= 5` check would misfire on it.
    """
    md = cc.MATRIX_PATH.read_text()
    control_tables_text = md.split("## Template baseline", 1)[1].split(
        "## Completion Rules", 1
    )[0]
    bad = []
    for line in control_tables_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if set(stripped) <= {"|", "-", " "}:
            continue  # separator row, e.g. |---|---|---|---|---|
        first = cells[0].strip("`").strip()
        if first in ("Control ID", ""):
            continue  # header row
        if len(cells) != 5:
            bad.append(f"{first or stripped[:40]!r}: {len(cells)} cells")
    assert bad == [], f"control rows with != 5 cells (literal '|' in a cell?): {bad}"


def case_sec_tool_001_is_gone():
    """The merge, not a second token: one function cannot be two mechanisms."""
    md = cc.MATRIX_PATH.read_text()
    assert "SEC-TOOL-001" not in md.split("## Completion Rules")[0] or \
        "Supersedes the former `SEC-TOOL-001`" in md, \
        "SEC-TOOL-001 must be merged into SEC-PHASE-001, which must say so"
    rows = cc.parse_matrix_rows(md)
    assert "SEC-TOOL-001" not in rows, "SEC-TOOL-001 still has its own row"


# --- I2: internal coherence ----------------------------------------------

def case_register_has_ten_rows():
    """The template baseline (spec §4.5.3). A product adds its own rows later."""
    reg = cc._load_register(cc.MECHANISMS_PATH)
    ids = [m["id"] for m in reg["mechanisms"]]
    assert len(ids) == 10, f"expected 10 rows, got {len(ids)}: {ids}"
    assert len(set(ids)) == 10, f"duplicate ids: {ids}"


def case_i2_passes_on_the_shipped_register():
    errors, msgs, skips = cc.check_i2(cc._load_register(cc.MECHANISMS_PATH))
    assert errors == 0, msgs
    assert skips == 0, "I2 is a pure function of one row — it cannot skip"


def case_i2_rejects_a_gate_that_cannot_deny():
    """§4.5.7's mutation, as a permanent test: category is forced by the boundary."""
    reg = {"schema": 1, "mechanisms": [{
        "id": "SEC-FAKE-001", "category": "GATE",
        "decides": "governance/permission.py::check_deny_list",
        "attaches_at": "PreToolUse", "can_deny": False,
        "proof": "python3 tests/test_fixtures.py", "status": "OBSERVE",
        "portable_to_runtime": True}]}
    errors, msgs, _ = cc.check_i2(reg)
    assert errors >= 1, "a GATE that cannot deny must be rejected"
    assert any("can_deny" in m for m in msgs), msgs


def case_i2_rejects_a_flattered_status():
    """Hand-set MECHANICAL while can_deny is false: status is derived, not chosen."""
    reg = {"schema": 1, "mechanisms": [{
        "id": "SEC-FAKE-002", "category": "RECORD",
        "decides": "Harness-Best-Practice/observability/audit.py::record",
        "attaches_at": "PostToolUse", "can_deny": False,
        "proof": "python3 tests/test_hooks.py", "status": "MECHANICAL",
        "portable_to_runtime": True}]}
    errors, msgs, _ = cc.check_i2(reg)
    assert errors >= 1, "a register must not be able to flatter itself"
    assert any("derives to OBSERVE" in m for m in msgs), msgs


CASES = [
    case_matrix_parses_into_rows,
    case_every_matrix_row_has_a_status_token,
    case_gap_row_count_is_twelve,
    case_every_control_row_has_five_cells,
    case_sec_tool_001_is_gone,
    case_register_has_ten_rows,
    case_i2_passes_on_the_shipped_register,
    case_i2_rejects_a_gate_that_cannot_deny,
    case_i2_rejects_a_flattered_status,
]


def run_mechanism_tests():
    """Returns (passed, failed, failures). Mirrors tests/test_coverage.py."""
    passed, failed, failures = 0, 0, []
    for fn in CASES:
        try:
            fn()
            passed += 1
        except AssertionError as e:
            failed += 1
            failures.append(f"{fn.__name__}: {e}")
        except Exception as e:  # a crash is a failure, not an error to swallow
            failed += 1
            failures.append(f"{fn.__name__}: {type(e).__name__}: {e}")
    return passed, failed, failures


def test_all_mechanism_cases():
    """Optional path; `python3 tests/test_mechanisms.py` is the authoritative runner."""
    p, f, failures = run_mechanism_tests()
    assert f == 0, "\n".join(failures)


if __name__ == "__main__":
    p, f, failures = run_mechanism_tests()
    for line in failures:
        print(f"  ✗ {line}")
    print(f"  {p} passed, {f} failed")
    sys.exit(1 if f else 0)
