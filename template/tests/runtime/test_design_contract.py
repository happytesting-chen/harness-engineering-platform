"""Task 1 documentation contract — the runtime profile names its binding boundaries.

This is a contract test over PROSE, deliberately: later tasks import these names as
load-bearing vocabulary (`ON_INGRESS`, the two receipt types, the two hard exclusions),
and a profile that stops naming one of them is a profile that stopped meaning what the
implementation assumes. The test pins the vocabulary, not the wording around it.

Plan: docs/superpowers/plans/2026-08-31-runtime-security-semantic-enforcement-rescoped.md
Task 1. Runs standalone (`python3 tests/runtime/test_design_contract.py`) or under pytest;
pytest is never required for it to pass.
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROFILE = PROJECT_ROOT / "Context" / "runtime-security-profile.md"

REQUIRED_TERMS = (
    "ON_INGRESS",
    "ON_ACTION",
    "ContentReleaseReceipt",
    "ActionApprovalReceipt",
    "persistent memory: disabled",
    "delegation: disabled",
)

# The profile must separate the two profiles by name, and say that unsupported
# capabilities are STARTUP errors — not warnings, not degraded modes.
REQUIRED_DISTINCTIONS = (
    "runtime-mvp",
    "demo",
    "startup error",
)


def test_runtime_profile_exists():
    assert PROFILE.exists(), (
        f"{PROFILE} does not exist — Task 1 Step 4 creates it"
    )


def test_runtime_profile_names_binding_boundaries():
    text = PROFILE.read_text(encoding="utf-8")
    missing = [term for term in REQUIRED_TERMS if term not in text]
    assert not missing, f"profile is missing required terms: {missing}"


def test_runtime_profile_distinguishes_profiles_and_fails_startup():
    text = PROFILE.read_text(encoding="utf-8")
    missing = [term for term in REQUIRED_DISTINCTIONS if term not in text]
    assert not missing, f"profile is missing required distinctions: {missing}"


def test_specs_record_the_measured_baseline():
    """The 2026-08-17 spec must carry the corrected baseline, labelled as such."""
    spec = PROJECT_ROOT / "docs" / "superpowers" / "specs" / (
        "2026-08-17-pre-llm-injection-screening-design.md"
    )
    text = spec.read_text(encoding="utf-8")
    assert "10 of 12" in text and "2 of 12" in text, (
        "spec must record the measured 10-of-12 / 2-of-12 corpus baseline"
    )
    assert "ON_INGRESS" in text, (
        "spec must reference the binding ingress boundary that supersedes its open decisions"
    )


if __name__ == "__main__":
    try:
        import pytest
        raise SystemExit(pytest.main([__file__, "-q"]))
    except ImportError:
        failures = 0
        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                try:
                    fn()
                    print(f"PASS {name}")
                except AssertionError as exc:
                    failures += 1
                    print(f"FAIL {name}: {exc}")
        total = len([n for n in globals() if n.startswith("test_")])
        print(f"Results: {total - failures} passed, {failures} failed")
        raise SystemExit(1 if failures else 0)
