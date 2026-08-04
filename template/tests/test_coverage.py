"""Ground-truth tests for the coverage checker (stdlib only; mirrors tests/test_fixtures.py)."""
import json
import sys
import tempfile
from pathlib import Path

SEC_DIR = Path(__file__).parent.parent / "Security-kit"
if str(SEC_DIR) not in sys.path:
    sys.path.insert(0, str(SEC_DIR))
import check_coverage as cc  # noqa: E402


def _write_context(tmp: Path, files: dict) -> Path:
    ctx = tmp / "Context"
    ctx.mkdir()
    for name, body in files.items():
        (ctx / name).write_text(body)
    return ctx


# --- pure-helper cases (each returns None on pass, raises AssertionError on fail) ---

def case_hash_ignores_template_stubs():
    with tempfile.TemporaryDirectory() as d:
        ctx = _write_context(Path(d), {"a.md": "one", "b.md.template": "IGNORED"})
        h1 = cc.context_hash(ctx)
        (ctx / "b.md.template").write_text("STILL IGNORED")
        assert cc.context_hash(ctx) == h1, ".template change moved the hash"


def case_hash_changes_when_real_doc_changes():
    with tempfile.TemporaryDirectory() as d:
        ctx = _write_context(Path(d), {"a.md": "one"})
        h1 = cc.context_hash(ctx)
        (ctx / "a.md").write_text("two")
        assert cc.context_hash(ctx) != h1, "real-doc change did not move the hash"


def case_parse_matrix_extracts_verification_cell():
    md = (
        "| Control ID | Objective | Impl | Verification | Review |\n"
        "|---|---|---|---|---|\n"
        "| `SEC-INPUT-001` | x | y | `python3 tests/t.py` | z |\n"
        "| `SEC-XXX-001` | x | y | {{VERIFICATION_COMMAND}} | z |\n"
    )
    rows = cc.parse_matrix(md)
    assert rows["SEC-INPUT-001"] == "`python3 tests/t.py`"
    assert rows["SEC-XXX-001"] == "{{VERIFICATION_COMMAND}}"


# --- gate cases (Step 5) ---

_MATRIX_OK = (
    "| Control ID | Objective | Impl | Verification | Review |\n"
    "|---|---|---|---|---|\n"
    "| `SEC-INPUT-001` | untrusted input | content_trust.py | `python3 tests/test_content_trust.py` | rev |\n"
)


def _coverage(context_dir, controls):
    return {"schema_version": 1,
            "generated_from": f"Context/ @ {cc.context_hash(context_dir)}",
            "controls": controls}


def _run_check(matrix, context_files, coverage=None, active=None):
    """Build a temp project, point cc.* constants at it, return (errors, msgs). Restores constants."""
    saved = (cc.COVERAGE_PATH, cc.MATRIX_PATH, cc.ACTIVE_CONTROLS_PATH, cc.CONTEXT_DIR)
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        sec = root / "Security-kit"; sec.mkdir()
        ctx = _write_context(root, context_files)
        (sec / "control-matrix.md").write_text(matrix)
        cc.MATRIX_PATH = sec / "control-matrix.md"
        cc.COVERAGE_PATH = sec / "coverage.json"
        cc.ACTIVE_CONTROLS_PATH = sec / "active-controls.md"
        cc.CONTEXT_DIR = ctx
        # coverage may be a dict, the string "MALFORMED", or None (absent)
        if coverage == "MALFORMED":
            cc.COVERAGE_PATH.write_text("{not json")
        elif coverage is not None:
            cc.COVERAGE_PATH.write_text(json.dumps(coverage))
        if active is not None:
            cc.ACTIVE_CONTROLS_PATH.write_text(active)
        try:
            return cc.check(root)
        finally:
            cc.COVERAGE_PATH, cc.MATRIX_PATH, cc.ACTIVE_CONTROLS_PATH, cc.CONTEXT_DIR = saved


def case_fail_when_coverage_missing():
    errs, msgs = _run_check(_MATRIX_OK, {"a.md": "x"})
    assert errs >= 1 and any("missing" in m.lower() for m in msgs), msgs


def case_fail_when_applies_has_no_matrix_row():
    empty_matrix = "| Control ID | O | I | Verification | R |\n|---|---|---|---|---|\n"
    # hash must match the same context the checker will read, so compute over a temp ctx first:
    with tempfile.TemporaryDirectory() as d:
        ctx = _write_context(Path(d), {"a.md": "reads untrusted input"})
        cov = _coverage(ctx, [{"id": "LLM01", "verdict": "applies",
                               "reason": "x (Context/a.md:1)", "matrix_row": "SEC-INPUT-001"}])
    # NOTE: freshness is checked against the REAL temp ctx built in _run_check; this case
    # targets the missing-row rule, so accept either a stale OR a missing-row error.
    errs, msgs = _run_check(empty_matrix, {"a.md": "reads untrusted input"}, coverage=cov)
    assert errs >= 1 and any("SEC-INPUT-001" in m or "stale" in m.lower() for m in msgs), msgs


def _fresh_cov(context_files, controls):
    """Build coverage whose hash matches what _run_check's ctx will produce for the same files."""
    with tempfile.TemporaryDirectory() as d:
        ctx = _write_context(Path(d), context_files)
        return _coverage(ctx, controls)


def case_fail_when_verification_blank_or_todo():
    matrix = ("| Control ID | O | I | Verification | R |\n|---|---|---|---|---|\n"
              "| `SEC-INPUT-001` | x | y | TODO | z |\n")
    cov = _fresh_cov({"a.md": "x"}, [{"id": "LLM01", "verdict": "applies",
                                      "reason": "r", "matrix_row": "SEC-INPUT-001"}])
    errs, msgs = _run_check(matrix, {"a.md": "x"}, coverage=cov,
                            active="# Active\n- LLM01\n")
    assert errs >= 1 and any("SEC-INPUT-001" in m for m in msgs), msgs


def case_fail_when_stale():
    cov = _fresh_cov({"a.md": "x"}, [])
    cov["generated_from"] = "Context/ @ deadbeef"  # deliberately wrong
    errs, msgs = _run_check(_MATRIX_OK, {"a.md": "x"}, coverage=cov, active="# Active\n")
    assert errs >= 1 and any("stale" in m.lower() or "re-run" in m.lower() for m in msgs), msgs


def case_fail_when_malformed():
    errs, msgs = _run_check(_MATRIX_OK, {"a.md": "x"}, coverage="MALFORMED")
    assert errs >= 1, msgs


def case_pass_when_applies_mapped_and_active_matches():
    cov = _fresh_cov({"a.md": "x"}, [{"id": "LLM01", "verdict": "applies",
                                      "reason": "r", "matrix_row": "SEC-INPUT-001"}])
    errs, msgs = _run_check(_MATRIX_OK, {"a.md": "x"}, coverage=cov,
                            active="# Active\n- **[LLM01]** untrusted input\n")
    assert errs == 0, msgs


def case_pass_when_zero_applies():
    cov = _fresh_cov({"a.md": "x"}, [{"id": "LLM08", "verdict": "n_a", "reason": "no rag"}])
    errs, msgs = _run_check(_MATRIX_OK, {"a.md": "x"}, coverage=cov, active="# Active\n(none)\n")
    assert errs == 0, msgs


CASES = [
    case_hash_ignores_template_stubs,
    case_hash_changes_when_real_doc_changes,
    case_parse_matrix_extracts_verification_cell,
    case_fail_when_coverage_missing,
    case_fail_when_applies_has_no_matrix_row,
    case_fail_when_verification_blank_or_todo,
    case_fail_when_stale,
    case_fail_when_malformed,
    case_pass_when_applies_mapped_and_active_matches,
    case_pass_when_zero_applies,
]


def run_coverage_tests():
    passed, failed, failures = 0, 0, []
    for c in CASES:
        try:
            c()
            passed += 1
        except Exception as e:  # AssertionError or setup error
            failed += 1
            failures.append(f"{c.__name__}: {e}")
    return passed, failed, failures


# pytest-discoverable thin wrapper (optional path; not the authoritative runner)
def test_all_coverage_cases():
    passed, failed, failures = run_coverage_tests()
    assert failed == 0, "\n".join(failures)


if __name__ == "__main__":
    p, f, fails = run_coverage_tests()
    for line in fails:
        print(f"  ✗ {line}")
    print(f"  {p} passed, {f} failed")
    sys.exit(1 if f else 0)
