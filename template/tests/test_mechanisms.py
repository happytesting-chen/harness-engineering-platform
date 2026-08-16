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


def case_sec_tool_001_is_gone():
    """The merge, not a second token: one function cannot be two mechanisms."""
    md = cc.MATRIX_PATH.read_text()
    assert "SEC-TOOL-001" not in md.split("## Completion Rules")[0] or \
        "Supersedes the former `SEC-TOOL-001`" in md, \
        "SEC-TOOL-001 must be merged into SEC-PHASE-001, which must say so"
    rows = cc.parse_matrix_rows(md)
    assert "SEC-TOOL-001" not in rows, "SEC-TOOL-001 still has its own row"


CASES = [
    case_matrix_parses_into_rows,
    case_every_matrix_row_has_a_status_token,
    case_gap_row_count_is_twelve,
    case_sec_tool_001_is_gone,
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
