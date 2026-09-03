"""The benchmark's chunk window is a recorded, overridable parameter — never an invisible default.

Measured 2026-09-03: the classifier truncates at 512 tokens, and it labels the dominant tone
of a chunk, so a hostile sentence buried in benign prose is invisible at wide windows. The
eval therefore lets an operator measure a candidate at the window the deployment will use,
and stamps that window into the result so no figure is ever quoted without it.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / "Security-kit"))
sys.path.insert(0, str(_ROOT / "Security-kit" / "eval"))

import eval_runtime_injection as e  # noqa: E402
from runtime.classifier import SemanticDecision, SemanticLabel  # noqa: E402
from runtime.normalization import ChunkPolicy  # noqa: E402


class _Counting:
    def __init__(self):
        self.seen = []

    def classify(self, piece):
        self.seen.append(piece.text)
        return SemanticDecision(label=SemanticLabel.DATA, confidence=1.0, classifier_sha256="c" * 64)


def _case(text):
    return {"id": "t", "text": text, "label": "data", "file": "legitimate.json"}


def test_default_chunk_policy_is_the_runtime_default():
    assert (e.CHUNK_POLICY.size, e.CHUNK_POLICY.overlap) == (ChunkPolicy().size, ChunkPolicy().overlap)


def test_semantic_layer_honours_the_module_chunk_policy():
    saved = e.CHUNK_POLICY
    try:
        text = "benign sentence. " * 200          # ~3400 chars: one default chunk, many small ones
        e.CHUNK_POLICY = ChunkPolicy()
        wide = _Counting(); e._semantic_label(_case(text), wide)
        e.CHUNK_POLICY = ChunkPolicy(size=600, overlap=120)
        narrow = _Counting(); e._semantic_label(_case(text), narrow)
        assert len(wide.seen) == 1 and len(narrow.seen) > 5, (len(wide.seen), len(narrow.seen))
        assert all(len(t) <= 600 for t in narrow.seen)
    finally:
        e.CHUNK_POLICY = saved


def test_cli_flags_set_the_chunk_policy_before_the_run(monkeypatch=None):
    saved = e.CHUNK_POLICY
    calls = []
    orig = e.run_candidate
    try:
        e.run_candidate = lambda m, o: calls.append((e.CHUNK_POLICY.size, e.CHUNK_POLICY.overlap)) or 0
        rc = e.main(["--candidate-manifest", "x.json", "--output", "y",
                     "--chunk-size", "600", "--chunk-overlap", "120"])
        assert rc == 0 and calls == [(600, 120)]
        e.main(["--candidate-manifest", "x.json", "--output", "y", "--chunk-size", "300"])
        assert calls[-1] == (300, ChunkPolicy().overlap), "overlap keeps its default when only size is given"
    finally:
        e.run_candidate = orig
        e.CHUNK_POLICY = saved


def test_committed_results_record_their_window():
    import json
    cands = _ROOT / "evaluation" / "runtime-security" / "classifier-candidates"
    for name in ("corpus40.result.json", "corpus40.chunk600.result.json"):
        result = json.loads(next(cands.glob(f"*.{name}")).read_text())
        assert "chunk_policy" in result, f"{name} does not record its chunk window"
    c600 = json.loads(next(cands.glob("*.corpus40.chunk600.result.json")).read_text())
    assert c600["chunk_policy"] == {"size": 600, "overlap": 120}


if __name__ == "__main__":
    try:
        import pytest
        raise SystemExit(pytest.main([__file__, "-q"]))
    except ImportError:
        failures = 0
        tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
        for name, fn in tests:
            try:
                fn(); print(f"PASS {name}")
            except AssertionError as exc:
                failures += 1; print(f"FAIL {name}: {exc}")
        print(f"Results: {len(tests) - failures} passed, {failures} failed")
        raise SystemExit(1 if failures else 0)
