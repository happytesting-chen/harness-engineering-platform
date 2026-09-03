"""Task 12 — the runtime claims match the runtime code (truthfulness gate).

This does NOT edit the claims register (that is a human batch, plan §5). It checks that
what the docs will claim is backed by code that exists and tests that pass — so a claim
cannot drift ahead of the mechanism. Where a claim is a GAP, it verifies the gap is
still real (the register must not quietly upgrade it).
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
_KIT = _ROOT / "Security-kit"
sys.path.insert(0, str(_KIT))


def test_every_runtime_module_the_profile_names_exists():
    for module in ("contracts", "normalization", "rules", "classifier", "ingress",
                   "review", "review_cli", "adapters", "session", "guarded",
                   "startup", "audit", "output", "host", "attack_driver"):
        assert (_KIT / "runtime" / f"{module}.py").exists(), f"missing runtime/{module}.py"


_LOCK_PATH = _KIT / "runtime" / "semantic-model.lock.json"


def _skip(reason: str) -> None:
    """Skip under pytest; under the stdlib __main__ runner, say so and count as passed.
    Either way the reason is printed — a silent skip is the failure mode this file exists
    to prevent."""
    print(f"SKIP: {reason}")
    try:
        import pytest
        pytest.skip(reason)
    except ImportError:
        return


def test_signed_lock_corpus_digest_matches_the_tree():
    """Runs everywhere, including CI runners with no classifier: the lock's corpus digest
    must equal the committed corpus. This is the half of C-5 that a corpus edit breaks —
    it did on 2026-09-03, and only the operator's machine noticed."""
    sys.path.insert(0, str(_KIT / "eval"))
    import eval_runtime_injection as e
    from runtime.classifier import load_lock
    lock = load_lock(_LOCK_PATH)                       # static validity, incl. approval fields
    assert lock.corpus_sha256 == e.corpus_sha256(), (
        f"corpus digest drift: lock {lock.corpus_sha256[:12]}…, tree {e.corpus_sha256()[:12]}… "
        "— the corpus changed after signing; re-run the evidence and re-sign, do not edit the lock alone"
    )


def test_signed_lock_verifies_against_the_artifacts():
    """Artifact half of C-5: executable and model digests. Needs the operator's local
    classifier files, which are deliberately not in the repo; skipped with a stated reason
    where they are absent, never silently."""
    import json
    lock = json.loads(_LOCK_PATH.read_text(encoding="utf-8"))
    missing = [k for k in ("executable_path", "model_path") if not Path(lock[k]).is_file()]
    if missing:
        return _skip(f"classifier artifacts not on this machine ({', '.join(missing)}); "
                     "run Security-kit/eval/bootstrap_classifier.py to obtain and pin them")
    import subprocess
    result = subprocess.run(
        [sys.executable, "Security-kit/eval/eval_runtime_injection.py",
         "--lock", str(_LOCK_PATH), "--verify"],
        cwd=_ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, f"lock verification failed: {result.stdout}{result.stderr}"


def test_runtime_gap_row_is_still_a_gap():
    """SEC-RUNTIME-GAP-001 stays GAP until the human batch promotes it (plan Task 12
    step 5). If this fails, someone upgraded the claim ahead of the review."""
    matrix = (_KIT / "control-matrix.md").read_text(encoding="utf-8")
    assert "SEC-RUNTIME-GAP-001" in matrix
    # the row must still carry GAP — the code existing is not the same as an app routing through it
    for line in matrix.splitlines():
        if "SEC-RUNTIME-GAP-001" in line:
            assert "GAP" in line, "the runtime routing gap must remain GAP until the human batch"
            break


def test_no_runtime_module_owns_a_duplicated_detector():
    """AD-7 / single-owner, swept across the whole package: no runtime module compiles
    a detection pattern except where the owner lives (content_trust, secret_scan are
    OUTSIDE runtime/)."""
    import re
    offenders = []
    for path in (_KIT / "runtime").glob("*.py"):
        if "re.compile" in path.read_text(encoding="utf-8"):
            offenders.append(path.name)
    # normalization.py legitimately compiles STRUCTURAL signal patterns (not detection
    # markers); everything else must delegate. Assert the set is exactly that.
    assert set(offenders) <= {"normalization.py"}, (
        f"unexpected pattern owners in runtime/: {offenders}"
    )


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
