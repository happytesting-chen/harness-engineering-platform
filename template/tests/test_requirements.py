"""Requirement-spine invariant — I6, both directions (spec §8.1).

Stdlib only. `python3 tests/test_requirements.py` is the authoritative runner.
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "Security-kit"))

import check_coverage as cc  # noqa: E402


def _matrix():
    return cc.parse_matrix_rows(cc.MATRIX_PATH.read_text())


def _spine_path() -> Path:
    """The installed spine if a human has installed it, else the drafted proposal.

    Not in the plan, and load-bearing. `requirements.json` is human-owned at merge
    time (spec §8.1 rule 4), so the model that wrote this increment drafted
    `requirements.proposed.json` instead. If these tests read only the real path
    they would ImportError-or-skip until someone moves the file, and a test that
    silently checks nothing is the §1.6 failure this whole file exists to prevent.

    So: real path if present, proposed path otherwise, and a raised error if
    neither exists. Never a silent skip. Once a human installs the spine, this
    function returns the real path and nothing else here changes.
    """
    if cc.REQUIREMENTS_PATH.is_file():
        return cc.REQUIREMENTS_PATH
    proposed = cc.REQUIREMENTS_PATH.with_name("requirements.proposed.json")
    if proposed.is_file():
        return proposed
    raise FileNotFoundError(
        f"no spine to check: neither {cc.REQUIREMENTS_PATH.name} nor "
        f"{proposed.name} exists under Security-kit/"
    )


def case_spine_covers_every_non_gap_row():
    reqs = cc._load_requirements(_spine_path())
    errors, msgs, skips = cc.check_i6(reqs, _matrix())
    assert errors == 0, msgs
    assert skips == 0, f"no matrix row should be skipped: {msgs}"


def case_severity_is_one_of_four():
    """Operational, not adjectival: critical/high block promotion, medium/low are
    recorded. A severity that changes no decision is decoration."""
    reqs = cc._load_requirements(_spine_path())
    bad = [r["id"] for r in reqs["requirements"] if r["severity"] not in cc.SEVERITIES]
    assert bad == [], f"rows with an unknown severity: {bad}"


def case_requirement_text_is_about_the_world_not_a_file():
    """§8.1 rule 1, machine-checkable half. 'Gate 1a is enabled' cannot be wrong
    while the guarantee is broken; 'the agent cannot edit the files that decide
    what it may do' can be tested by trying."""
    reqs = cc._load_requirements(_spine_path())
    for r in reqs["requirements"]:
        text = r["requirement"]
        assert ".py" not in text and ".json" not in text, \
            f"{r['id']}: a requirement names a guarantee, not a file: {text!r}"


def case_load_requirements_fails_closed_on_a_malformed_spine():
    """Not in the plan. `_load_requirements` is the only reader of the obligation
    plane, and its docstring claims it fails closed — so the claim gets a test.
    A reader that returned `{}` on a truncated file would turn every obligation
    into an absence of obligations, and I6 would pass over nothing."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        no_list = Path(d) / "no-list.json"
        no_list.write_text(json.dumps({"generated_note": "no requirements key"}))
        try:
            cc._load_requirements(no_list)
        except ValueError:
            pass
        else:
            raise AssertionError("a spine with no 'requirements' list must raise")

        truncated = Path(d) / "truncated.json"
        truncated.write_text('{"requirements": [')
        try:
            cc._load_requirements(truncated)
        except json.JSONDecodeError:
            pass
        else:
            raise AssertionError("a truncated spine must raise, not return empty")


def case_i6_catches_an_uncovered_matrix_row():
    """Direction 2 — a control no requirement asked for is unexplained machinery
    the next person cannot safely delete."""
    reqs = {"requirements": [{"id": "SEC-REQ-001", "risk": "r",
                              "requirement": "Something is true.",
                              "severity": "high",
                              "satisfied_by": ["SEC-SELF-001"], "residual": None}]}
    errors, msgs, _ = cc.check_i6(reqs, _matrix())
    assert errors >= 1
    assert any("named by no requirement" in m for m in msgs), msgs


def case_i6_catches_a_requirement_naming_nothing():
    """Direction 1 — a requirement nothing serves is a lie."""
    reqs = {"requirements": [{"id": "SEC-REQ-999", "risk": "r",
                              "requirement": "Something is true.",
                              "severity": "high",
                              "satisfied_by": ["SEC-NOPE-001"], "residual": None}]}
    errors, msgs, _ = cc.check_i6(reqs, _matrix())
    assert any("does not exist" in m and "SEC-NOPE-001" in m for m in msgs), msgs


def case_i6_requires_a_residual_for_a_gap():
    """§8.1 rule 3 — the field that stops the spine becoming a comfort object."""
    reqs = {"requirements": [{"id": "SEC-REQ-998", "risk": "r",
                              "requirement": "Something is true.",
                              "severity": "high",
                              "satisfied_by": ["SEC-EGRESS-GAP-001"],
                              "residual": None}]}
    errors, msgs, _ = cc.check_i6(reqs, _matrix())
    assert any("no residual" in m for m in msgs), msgs


def case_i6_rejects_an_unknown_severity():
    """Not in the plan. `case_severity_is_one_of_four` reads the shipped spine
    directly and would still pass if `check_i6` never looked at the field — which
    would leave the build unable to catch a bad severity on a FUTURE row. This
    pins the check inside the invariant, where the gate reads it."""
    reqs = {"requirements": [{"id": "SEC-REQ-997", "risk": "r",
                              "requirement": "Something is true.",
                              "severity": "showstopper",
                              "satisfied_by": ["SEC-SELF-001"], "residual": None}]}
    errors, msgs, _ = cc.check_i6(reqs, _matrix())
    assert any("severity" in m and "SEC-REQ-997" in m for m in msgs), msgs


def case_i6_over_an_empty_spine_fails_loudly():
    """An empty spine must FAIL, naming every uncovered row. The precedent is
    f16525a: a sampling test reported 100% while 57% of the matrix was unmeasured."""
    errors, msgs, _ = cc.check_i6({"requirements": []}, _matrix())
    assert errors == 11, f"expected 11 uncovered non-GAP rows, got {errors}"
    assert all("named by no requirement" in m for m in msgs), msgs


CASES = [
    case_spine_covers_every_non_gap_row,
    case_severity_is_one_of_four,
    case_requirement_text_is_about_the_world_not_a_file,
    case_load_requirements_fails_closed_on_a_malformed_spine,
    case_i6_catches_an_uncovered_matrix_row,
    case_i6_catches_a_requirement_naming_nothing,
    case_i6_requires_a_residual_for_a_gap,
    case_i6_rejects_an_unknown_severity,
    case_i6_over_an_empty_spine_fails_loudly,
]


def run_requirement_tests():
    """Returns (passed, failed, failures)."""
    passed, failed, failures = 0, 0, []
    for fn in CASES:
        try:
            fn()
            passed += 1
        except AssertionError as e:
            failed += 1
            failures.append(f"{fn.__name__}: {e}")
        except Exception as e:
            failed += 1
            failures.append(f"{fn.__name__}: {type(e).__name__}: {e}")
    return passed, failed, failures


def test_all_requirement_cases():
    """Optional path; `python3 tests/test_requirements.py` is the authoritative runner."""
    p, f, failures = run_requirement_tests()
    assert f == 0, "\n".join(failures)


if __name__ == "__main__":
    p, f, failures = run_requirement_tests()
    for line in failures:
        print(f"  ✗ {line}")
    print(f"  {p} passed, {f} failed")
    sys.exit(1 if f else 0)
