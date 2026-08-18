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
    return {"schema_version": cc.SCHEMA_VERSION,
            "generated_from": f"Context/ @ {cc.context_hash(context_dir)}",
            "controls": controls}


def _applies_llm01():
    """The canonical well-formed entry, as a factory so no two cases share a dict.

    Named rather than inlined so that the one case which deliberately omits `plane`
    (case_shape_is_wired_into_check) reads as a choice instead of an oversight.
    """
    return {"id": "LLM01", "verdict": "applies", "plane": ["runtime"],
            "reason": "r (Context/a.md:1)", "matrix_row": "SEC-INPUT-001"}


def _run_check(matrix, context_files, coverage=None, active=None, mirror=None,
               crosswalk=None, allowlist=None):
    """Build a temp project, point cc.* constants at it, return (errors, msgs). Restores constants.

    `mirror`, when given, is written to KIRO_MIRROR_PATH (kiro/steering/active-controls.md
    under the temp root) so cases can exercise check()'s mirror-content-consistency branch.
    Left absent (None), KIRO_MIRROR_PATH stays pointed at a path that does not exist —
    isolating these cases from check_kiro_mirror()'s own tests and from the real repo's
    kiro/steering/active-controls.md.

    CROSSWALK_PATH and ALLOWLIST_PATH are redirected into the temp root and left absent
    unless `crosswalk`/`allowlist` are given, so rules 6 and 7 take their documented skip
    branches. Without this every temp-project case would join against the REAL repo
    crosswalk and report all 20 ids missing — a fixture leak, not a finding.
    """
    saved = (cc.COVERAGE_PATH, cc.MATRIX_PATH, cc.ACTIVE_CONTROLS_PATH, cc.CONTEXT_DIR,
             cc.KIRO_MIRROR_PATH, cc.CROSSWALK_PATH, cc.ALLOWLIST_PATH)
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        sec = root / "Security-kit"; sec.mkdir()
        ctx = _write_context(root, context_files)
        (sec / "control-matrix.md").write_text(matrix)
        cc.MATRIX_PATH = sec / "control-matrix.md"
        cc.COVERAGE_PATH = sec / "coverage.json"
        cc.ACTIVE_CONTROLS_PATH = sec / "active-controls.md"
        cc.CONTEXT_DIR = ctx
        cc.KIRO_MIRROR_PATH = root / "kiro" / "steering" / "active-controls.md"
        cc.CROSSWALK_PATH = sec / "owasp-crosswalk.md"
        cc.ALLOWLIST_PATH = root / "governance" / "mcp-allowlist.json"
        if crosswalk is not None:
            cc.CROSSWALK_PATH.write_text(crosswalk)
        if allowlist is not None:
            cc.ALLOWLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
            cc.ALLOWLIST_PATH.write_text(allowlist)
        # coverage may be a dict, the string "MALFORMED", or None (absent)
        if coverage == "MALFORMED":
            cc.COVERAGE_PATH.write_text("{not json")
        elif coverage is not None:
            cc.COVERAGE_PATH.write_text(json.dumps(coverage))
        if active is not None:
            cc.ACTIVE_CONTROLS_PATH.write_text(active)
        if mirror is not None:
            cc.KIRO_MIRROR_PATH.parent.mkdir(parents=True, exist_ok=True)
            cc.KIRO_MIRROR_PATH.write_text(mirror)
        try:
            return cc.check(root)
        finally:
            (cc.COVERAGE_PATH, cc.MATRIX_PATH, cc.ACTIVE_CONTROLS_PATH, cc.CONTEXT_DIR,
             cc.KIRO_MIRROR_PATH, cc.CROSSWALK_PATH, cc.ALLOWLIST_PATH) = saved


def case_fail_when_coverage_missing():
    errs, msgs = _run_check(_MATRIX_OK, {"a.md": "x"})
    assert errs >= 1 and any("missing" in m.lower() for m in msgs), msgs


def case_fail_when_applies_has_no_matrix_row():
    empty_matrix = "| Control ID | O | I | Verification | R |\n|---|---|---|---|---|\n"
    # hash must match the same context the checker will read, so compute over a temp ctx first:
    with tempfile.TemporaryDirectory() as d:
        ctx = _write_context(Path(d), {"a.md": "reads untrusted input"})
        cov = _coverage(ctx, [_applies_llm01()])
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
    cov = _fresh_cov({"a.md": "x"}, [_applies_llm01()])
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
    cov = _fresh_cov({"a.md": "x"}, [_applies_llm01()])
    errs, msgs = _run_check(_MATRIX_OK, {"a.md": "x"}, coverage=cov,
                            active="# Active\n- **[LLM01]** untrusted input\n")
    assert errs == 0, msgs


def case_pass_when_zero_applies():
    cov = _fresh_cov({"a.md": "x"}, [{"id": "LLM08", "verdict": "n_a",
                                      "plane": ["runtime"],
                                      "reason": "no rag (Context/a.md:1)"}])
    errs, msgs = _run_check(_MATRIX_OK, {"a.md": "x"}, coverage=cov, active="# Active\n(none)\n")
    assert errs == 0, msgs


def case_fail_when_mirror_content_mismatches_applies():
    """check()'s layer-D content rule extends to the Kiro mirror: a mirror that exists but
    omits an applies control id is an ERROR, same bar as active-controls.md omitting it.

    Asserts on the message text, not just the count — a bare count can't distinguish this
    failure from any other error the same call might raise.
    """
    cov = _fresh_cov({"a.md": "x"}, [_applies_llm01()])
    errs, msgs = _run_check(_MATRIX_OK, {"a.md": "x"}, coverage=cov,
                            active="# Active\n- **[LLM01]** untrusted input\n",
                            mirror="# Active\n- **[SOMETHING-ELSE]** unrelated\n")
    assert errs >= 1, msgs
    assert any("kiro/steering/active-controls.md does not mention applies control LLM01" in m
               for m in msgs), msgs


def case_pass_when_mirror_content_matches_applies():
    """Same fixture, but the mirror DOES mention the applies control id — no mirror error.

    Asserts the specific mirror-mismatch message is absent (not just that the total is
    zero), so this case stays meaningful even if the fixture later grows unrelated errors.
    """
    cov = _fresh_cov({"a.md": "x"}, [_applies_llm01()])
    errs, msgs = _run_check(_MATRIX_OK, {"a.md": "x"}, coverage=cov,
                            active="# Active\n- **[LLM01]** untrusted input\n",
                            mirror="# Active\n- **[LLM01]** untrusted input\n")
    assert not any("kiro/steering/active-controls.md does not mention applies control" in m
                   for m in msgs), msgs
    assert errs == 0, msgs


def case_kiro_mirror_required_when_steering_exists():
    """With kiro/steering/ present, a missing mirror is an ERROR.

    The Kiro host loads kiro/steering/*.md, not Security-kit/active-controls.md.
    A layer-D file that exists for one host only is steering the agent on one
    host only — and nothing said so.
    """
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "kiro" / "steering").mkdir(parents=True)
        errors, msgs = cc.check_kiro_mirror(root)
        assert errors == 1, f"expected 1 error, got {errors}"
        assert any("kiro/steering/active-controls.md" in m for m in msgs), msgs


def case_kiro_mirror_skipped_when_steering_absent():
    """Without kiro/steering/, the rule SKIPS — and says so.

    A Claude-only copy of the template has no Kiro host to steer. Silence here
    would be indistinguishable from a passing check (spec §1.6).
    """
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        errors, msgs = cc.check_kiro_mirror(root)
        assert errors == 0, f"expected 0 errors, got {errors}"
        assert any("skipped" in m and "no kiro/steering" in m for m in msgs), msgs


# --- rule 5: citations resolve ---

def case_fail_when_applies_cites_nothing():
    """An `applies` with no `Context/` citation is an unsourced claim.

    The procedure requires one and offers `gap` ("cannot determine") as the honest
    alternative, so a missing citation is a real failure, not a formatting nit.
    """
    errs, msgs = cc.check_citations(
        [{"id": "LLM01", "verdict": "applies", "reason": "reads untrusted input"}], Path("/nonexistent"))
    assert errs == 1, msgs
    assert any("cites no Context/ line" in m for m in msgs), msgs


def case_fail_when_citation_names_missing_file():
    with tempfile.TemporaryDirectory() as d:
        ctx = _write_context(Path(d), {"a.md": "line one"})
        errs, msgs = cc.check_citations(
            [{"id": "LLM01", "verdict": "applies", "reason": "x (Context/gone.md:1)"}], ctx)
    assert errs == 1, msgs
    assert any("names no such file" in m for m in msgs), msgs


def case_fail_when_citation_past_end_of_file():
    with tempfile.TemporaryDirectory() as d:
        ctx = _write_context(Path(d), {"a.md": "line one\nline two\n"})
        errs, msgs = cc.check_citations(
            [{"id": "LLM01", "verdict": "applies", "reason": "x (Context/a.md:99)"}], ctx)
    assert errs == 1, msgs
    assert any("past end of file" in m for m in msgs), msgs


def case_fail_when_citation_points_at_blank_line():
    """The off-by-one that this rule exists for.

    A citation to a blank line resolves as a file and a line number and reads as
    evidence, but points at nothing — the exact shape observed in the field.
    """
    blank_cite = dict(_applies_llm01(), reason="x (Context/a.md:2)")
    cov = _fresh_cov({"a.md": "one\n\nthree\n"}, [blank_cite])
    errs, msgs = _run_check(_MATRIX_OK, {"a.md": "one\n\nthree\n"}, coverage=cov,
                            active="# Active\n- **[LLM01]** untrusted input\n")
    assert errs >= 1, msgs
    assert any("blank line" in m for m in msgs), "rule 5 is not wired into check(): " + str(msgs)


def case_gap_needs_no_citation_but_a_bad_one_still_fails():
    with tempfile.TemporaryDirectory() as d:
        ctx = _write_context(Path(d), {"a.md": "line one"})
        ok, _ = cc.check_citations(
            [{"id": "LLM03", "verdict": "gap", "reason": "cannot determine from Context/"}], ctx)
        bad, msgs = cc.check_citations(
            [{"id": "LLM03", "verdict": "gap", "reason": "x (Context/a.md:44)"}], ctx)
    assert ok == 0, "a gap with nothing to cite must pass"
    assert bad == 1 and any("past end of file" in m for m in msgs), msgs


def case_no_mechanism_gap_must_still_cite():
    """The tightened half of rule 5.

    `undetermined` is exempt because there is nothing to cite. `no_mechanism` asserts
    the product HAS the surface — same claim an `applies` makes — so it carries the
    same burden. Exempting all gaps would have made "gap" a way to skip sourcing.
    """
    with tempfile.TemporaryDirectory() as d:
        ctx = _write_context(Path(d), {"a.md": "line one"})
        bad, msgs = cc.check_citations(
            [{"id": "ASI03", "verdict": "gap", "gap_kind": "no_mechanism",
              "reason": "cloud deploy, no identity broker"}], ctx)
        ok, _ = cc.check_citations(
            [{"id": "LLM09", "verdict": "gap", "gap_kind": "undetermined",
              "reason": "Context/ does not say"}], ctx)
    assert bad == 1 and any("cites no Context/ line" in m for m in msgs), msgs
    assert ok == 0, "an undetermined gap has nothing to cite"


def case_error_saying_skipped_is_not_a_skip():
    """The output marker must key on the skip IDIOM, not on the word "skipped".

    Rule 8's schema-version error originally said "field checks skipped until it
    does" and printed itself as a benign `–`. An error that renders as a skip is the
    worst failure mode this file has: the exit code says 1 and the screen says fine.
    """
    for skip in ("layer-D Kiro mirror: skipped — no kiro/steering directory",
                 "crosswalk join: skipped — owasp-crosswalk.md not present",
                 "phase-gate liveness: skipped — no applies control maps to SEC-PHASE-001"):
        assert cc.is_skip(skip), f"real skip misread as an error: {skip}"
    for err in ("coverage.json is schema_version 1, expected 2 — field checks not run",
                "LLM01: some check was skipped by the author and that is a bug",
                "ASI03: gap needs `gap_kind`"):
        assert not cc.is_skip(err), f"error misread as a skip: {err}"


# --- rule 8: plane and gap_kind ---

def _shape(controls, version=cc.SCHEMA_VERSION):
    return cc.check_shape({"schema_version": version, "controls": controls})


def case_old_schema_version_reports_once_not_forty_times():
    """A v1 file is missing both fields on all 20 entries.

    Reporting each one buries the only fact that matters — the file predates the
    contract — under 40 lines. One error, then stop.
    """
    errs, msgs = _shape([{"id": f"LLM{i:02d}", "verdict": "gap"} for i in range(1, 11)],
                        version=1)
    assert errs == 1, msgs
    assert len(msgs) == 1 and "schema_version" in msgs[0], msgs


def case_fail_when_plane_missing_or_empty():
    for planes in (None, [], "runtime"):
        c = {"id": "LLM01", "verdict": "applies"}
        if planes is not None:
            c["plane"] = planes
        errs, msgs = _shape([c])
        assert errs == 1, (planes, msgs)
        assert any("`plane` must be a non-empty list" in m for m in msgs), (planes, msgs)


def case_fail_when_plane_value_illegal_or_repeated():
    errs, msgs = _shape([{"id": "LLM01", "verdict": "applies", "plane": ["prod"]}])
    assert errs == 1 and any("illegal value 'prod'" in m for m in msgs), msgs
    errs, msgs = _shape([{"id": "LLM01", "verdict": "applies",
                          "plane": ["runtime", "runtime"]}])
    assert errs == 1 and any("repeats a value" in m for m in msgs), msgs


def case_fail_when_gap_has_no_kind():
    errs, msgs = _shape([{"id": "LLM09", "verdict": "gap", "plane": ["runtime"]}])
    assert errs == 1, msgs
    assert any("gap needs `gap_kind`" in m for m in msgs), msgs


def case_fail_when_gap_kind_illegal():
    errs, msgs = _shape([{"id": "LLM09", "verdict": "gap", "plane": ["runtime"],
                          "gap_kind": "maybe"}])
    assert errs == 1 and any("got 'maybe'" in m for m in msgs), msgs


def case_fail_when_non_gap_carries_a_gap_kind():
    """A `gap_kind` on an `applies` is a category error, not extra detail.

    Left unchecked it reads as a hedge — "this applies, but also sort of doesn't" —
    which is exactly the ambiguity gap_kind was added to remove.
    """
    errs, msgs = _shape([{"id": "LLM01", "verdict": "applies", "plane": ["build"],
                          "gap_kind": "no_mechanism"}])
    assert errs == 1, msgs
    assert any("only a gap has a kind" in m for m in msgs), msgs


def case_shape_passes_on_a_well_formed_set():
    errs, msgs = _shape([
        {"id": "LLM01", "verdict": "applies", "plane": ["runtime", "build"]},
        {"id": "LLM08", "verdict": "n_a", "plane": ["runtime"]},
        {"id": "ASI03", "verdict": "gap", "plane": ["runtime"], "gap_kind": "no_mechanism"},
        {"id": "LLM09", "verdict": "gap", "plane": ["build"], "gap_kind": "undetermined"},
    ])
    assert errs == 0, msgs
    assert msgs == [], msgs


def case_shape_is_wired_into_check():
    """Rule 8 must fire through check(), not just when called directly."""
    no_plane = {"id": "LLM01", "verdict": "applies",  # `plane` omitted ON PURPOSE
                "reason": "r (Context/a.md:1)", "matrix_row": "SEC-INPUT-001"}
    cov = _fresh_cov({"a.md": "x"}, [no_plane])
    errs, msgs = _run_check(_MATRIX_OK, {"a.md": "x"}, coverage=cov,
                            active="# Active\n- **[LLM01]** untrusted input\n")
    assert errs >= 1, msgs
    assert any("`plane` must be a non-empty list" in m for m in msgs), \
        "rule 8 is not wired into check(): " + str(msgs)


# --- rule 6: the crosswalk join ---

_CROSSWALK_OK = (
    "| OWASP id | Name | Mechanism | Notes |\n"
    "|---|---|---|---|\n"
    "| `LLM01` | Prompt Injection | [MECH] prompt_screen.py | n |\n"
    "| `LLM03` | Supply Chain | [GUIDE] review deps by hand | n |\n"
)


def case_fail_when_applies_lacks_mech_in_crosswalk():
    """coverage.json says `applies`; the crosswalk says only `[GUIDE]`.

    Before this rule the two files shared ids and nothing else — the divergence was
    invisible. An `applies` asserts a mechanism, so advice-only backing is a gap.
    """
    with tempfile.TemporaryDirectory() as d:
        cw = Path(d) / "owasp-crosswalk.md"
        cw.write_text(_CROSSWALK_OK)
        errs, msgs = cc.check_crosswalk_join(
            [{"id": "LLM01", "verdict": "applies"}, {"id": "LLM03", "verdict": "applies"}], cw)
    assert errs == 1, msgs
    assert any("LLM03" in m and "no [MECH]" in m for m in msgs), msgs


def case_fail_when_crosswalk_id_absent_from_coverage():
    with tempfile.TemporaryDirectory() as d:
        cw = Path(d) / "owasp-crosswalk.md"
        cw.write_text(_CROSSWALK_OK)
        errs, msgs = cc.check_crosswalk_join([{"id": "LLM01", "verdict": "applies"}], cw)
    assert errs == 1, msgs
    assert any("LLM03" in m and "absent from coverage.json" in m for m in msgs), msgs


def case_fail_when_coverage_invents_an_id():
    with tempfile.TemporaryDirectory() as d:
        cw = Path(d) / "owasp-crosswalk.md"
        cw.write_text(_CROSSWALK_OK)
        errs, msgs = cc.check_crosswalk_join(
            [{"id": "LLM01", "verdict": "applies"}, {"id": "LLM03", "verdict": "gap"},
             {"id": "LLM99", "verdict": "gap"}], cw)
    assert errs == 1, msgs
    assert any("LLM99" in m and "not an id" in m for m in msgs), msgs


def case_crosswalk_parsing_zero_ids_fails_closed():
    """A crosswalk this parser cannot read must not pass vacuously.

    If the table format ever changes, parse_crosswalk_rows returns {} — and a rule
    that iterates an empty dict finds no violations. That is silence, not a pass.
    """
    with tempfile.TemporaryDirectory() as d:
        cw = Path(d) / "owasp-crosswalk.md"
        cw.write_text("# no table here\n")
        errs, msgs = cc.check_crosswalk_join([{"id": "LLM01", "verdict": "applies"}], cw)
    assert errs == 1, msgs
    assert any("parsed 0 ids" in m for m in msgs), msgs


def case_crosswalk_join_passes_when_files_agree():
    with tempfile.TemporaryDirectory() as d:
        cw = Path(d) / "owasp-crosswalk.md"
        cw.write_text(_CROSSWALK_OK)
        errs, msgs = cc.check_crosswalk_join(
            [{"id": "LLM01", "verdict": "applies"}, {"id": "LLM03", "verdict": "gap"}], cw)
    assert errs == 0, msgs


def case_crosswalk_join_skips_when_file_absent():
    errs, msgs = cc.check_crosswalk_join([{"id": "LLM01", "verdict": "applies"}],
                                         Path("/nonexistent/owasp-crosswalk.md"))
    assert errs == 0, msgs
    assert any("skipped" in m for m in msgs), msgs


# --- rule 7: the phase gate has something to gate ---

_GATED = json.dumps({"tools": [{"name": "bash"},
                               {"name": "deploy", "gated_until": "phase-01"}]})
_UNGATED = json.dumps({"tools": [{"name": "bash"}, {"name": "write_file"}]})


def case_fail_when_phase_gate_is_inert():
    """SEC-PHASE-001 mapped, but no tool is gated — the gate passes on every call.

    An always-passing gate is indistinguishable from an enforcing one in the logs,
    which is precisely why a green coverage row here would be a false claim.
    """
    with tempfile.TemporaryDirectory() as d:
        al = Path(d) / "mcp-allowlist.json"
        al.write_text(_UNGATED)
        errs, msgs = cc.check_phase_gate_liveness(
            [{"id": "LLM06", "verdict": "applies", "matrix_row": "SEC-PHASE-001"}], al)
    assert errs == 1, msgs
    assert any("LLM06" in m and "gated_until" in m for m in msgs), msgs


def case_pass_when_a_tool_is_actually_gated():
    with tempfile.TemporaryDirectory() as d:
        al = Path(d) / "mcp-allowlist.json"
        al.write_text(_GATED)
        errs, msgs = cc.check_phase_gate_liveness(
            [{"id": "LLM06", "verdict": "applies", "matrix_row": "SEC-PHASE-001"}], al)
    assert errs == 0, msgs
    assert msgs == [], msgs


def case_phase_gate_missing_allowlist_fails_closed():
    errs, msgs = cc.check_phase_gate_liveness(
        [{"id": "LLM06", "verdict": "applies", "matrix_row": "SEC-PHASE-001"}],
        Path("/nonexistent/mcp-allowlist.json"))
    assert errs == 1, msgs
    assert any("no policy" in m for m in msgs), msgs


def case_phase_gate_skips_when_nothing_maps_to_it():
    errs, msgs = cc.check_phase_gate_liveness(
        [{"id": "LLM01", "verdict": "applies", "matrix_row": "SEC-INPUT-001"}],
        Path("/nonexistent/mcp-allowlist.json"))
    assert errs == 0, msgs
    assert any("skipped" in m for m in msgs), msgs


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
    case_fail_when_mirror_content_mismatches_applies,
    case_pass_when_mirror_content_matches_applies,
    case_kiro_mirror_required_when_steering_exists,
    case_kiro_mirror_skipped_when_steering_absent,
    case_fail_when_applies_cites_nothing,
    case_fail_when_citation_names_missing_file,
    case_fail_when_citation_past_end_of_file,
    case_fail_when_citation_points_at_blank_line,
    case_gap_needs_no_citation_but_a_bad_one_still_fails,
    case_fail_when_applies_lacks_mech_in_crosswalk,
    case_fail_when_crosswalk_id_absent_from_coverage,
    case_fail_when_coverage_invents_an_id,
    case_crosswalk_parsing_zero_ids_fails_closed,
    case_crosswalk_join_passes_when_files_agree,
    case_crosswalk_join_skips_when_file_absent,
    case_fail_when_phase_gate_is_inert,
    case_pass_when_a_tool_is_actually_gated,
    case_phase_gate_missing_allowlist_fails_closed,
    case_phase_gate_skips_when_nothing_maps_to_it,
    case_no_mechanism_gap_must_still_cite,
    case_error_saying_skipped_is_not_a_skip,
    case_old_schema_version_reports_once_not_forty_times,
    case_fail_when_plane_missing_or_empty,
    case_fail_when_plane_value_illegal_or_repeated,
    case_fail_when_gap_has_no_kind,
    case_fail_when_gap_kind_illegal,
    case_fail_when_non_gap_carries_a_gap_kind,
    case_shape_passes_on_a_well_formed_set,
    case_shape_is_wired_into_check,
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
