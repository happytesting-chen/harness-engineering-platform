"""Task 9 — startup isolation: unsupported capability = refuse to start, never degrade.

Every check answers the same question: could this deployment silently be weaker than
the profile claims? Memory, delegation, streaming, unregistered tools, a writable
control root in production, a missing receipt key, a drifted classifier lock — each is
a StartupError that names ALL violations at once (an operator fixes the list, not one
error per restart).
"""
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / "Security-kit"))

from runtime.startup import RuntimeConfig, StartupError, validate_startup  # noqa: E402


def _config(tmp: Path, **overrides):
    control = tmp / "control"
    control.mkdir(exist_ok=True)
    os.chmod(control, 0o555)
    kwargs = dict(
        production=True,
        memory_enabled=False,
        delegation_enabled=False,
        streaming_output=False,
        tools={"fetch": lambda **kw: None},
        policy_tools=("fetch",),
        control_root=control,
        receipt_key=b"host-owned-master-key-32-bytes!!",
        audit_failure_policy="deny",
        audit_max_bytes=1_000_000,
        semantic_enabled=False,
        classifier_lock_path=None,
    )
    kwargs.update(overrides)
    return RuntimeConfig(**kwargs)


def _violations(config):
    try:
        validate_startup(config)
        return ()
    except StartupError as exc:
        return exc.violations


def test_clean_config_starts():
    with tempfile.TemporaryDirectory() as d:
        report = validate_startup(_config(Path(d)))
        assert report.violations == ()


def test_each_disabled_capability_is_a_startup_error():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        for flag in ("memory_enabled", "delegation_enabled", "streaming_output"):
            violations = _violations(_config(tmp, **{flag: True}))
            assert any(flag.split("_")[0] in v for v in violations), (
                f"{flag}=True must refuse startup, got {violations}"
            )


def test_registry_and_policy_tool_sets_must_match_exactly():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        extra = _violations(_config(tmp, tools={"fetch": lambda **kw: None,
                                                "shadow": lambda **kw: None}))
        assert any("shadow" in v for v in extra)
        missing = _violations(_config(tmp, policy_tools=("fetch", "ghost")))
        assert any("ghost" in v for v in missing)


def test_uncallable_tool_is_refused():
    with tempfile.TemporaryDirectory() as d:
        violations = _violations(_config(Path(d), tools={"fetch": "not callable"}))
        assert any("fetch" in v and "callable" in v for v in violations)


def test_missing_or_short_receipt_key_is_refused():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        assert any("receipt key" in v for v in _violations(_config(tmp, receipt_key=None)))
        assert any("receipt key" in v for v in _violations(_config(tmp, receipt_key=b"short")))


def test_bad_audit_policy_is_refused():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        assert any("audit" in v for v in
                   _violations(_config(tmp, audit_failure_policy="ignore")))
        assert any("audit" in v for v in _violations(_config(tmp, audit_max_bytes=0)))


def test_writable_control_root_refuses_production_startup():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        writable = tmp / "writable-control"
        writable.mkdir()
        violations = _violations(_config(tmp, control_root=writable))
        assert any("control root" in v and "writable" in v for v in violations)


def test_non_production_skips_the_control_root_check():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        writable = tmp / "writable-control"
        writable.mkdir()
        report = validate_startup(_config(tmp, control_root=writable, production=False))
        assert report.violations == ()


def test_semantic_enabled_requires_a_valid_lock():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        # no lock at all
        violations = _violations(_config(tmp, semantic_enabled=True, classifier_lock_path=None))
        assert any("classifier" in v for v in violations)
        # lock present but the model artifact has drifted
        exe = tmp / "clf.sh"; exe.write_text("#!/bin/sh\ncat\n"); exe.chmod(0o755)
        model = tmp / "m.onnx"; model.write_bytes(b"original")
        sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
        lock = tmp / "lock.json"
        lock.write_text(json.dumps({
            "schema_version": 1, "protocol_version": 1,
            "executable_path": str(exe), "executable_sha256": sha(exe),
            "model_path": str(model), "model_sha256": sha(model),
            "corpus_sha256": "c" * 64, "confidence_floor": 0.75,
            "approved_by": "r", "approved_date": "2026-08-31",
        }))
        model.write_bytes(b"swapped after signing")
        violations = _violations(_config(tmp, semantic_enabled=True, classifier_lock_path=lock))
        assert any("drift" in v or "classifier" in v for v in violations)


def test_all_violations_are_reported_at_once():
    with tempfile.TemporaryDirectory() as d:
        violations = _violations(_config(
            Path(d), memory_enabled=True, delegation_enabled=True,
            streaming_output=True, receipt_key=None,
        ))
        assert len(violations) >= 4, f"expected the full list, got {violations}"


if __name__ == "__main__":
    try:
        import pytest
        raise SystemExit(pytest.main([__file__, "-q"]))
    except ImportError:
        failures = 0
        tests = [(n, f) for n, f in sorted(globals().items())
                 if n.startswith("test_") and callable(f)]
        for name, fn in tests:
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {name}: {exc}")
        print(f"Results: {len(tests) - failures} passed, {failures} failed")
        raise SystemExit(1 if failures else 0)
