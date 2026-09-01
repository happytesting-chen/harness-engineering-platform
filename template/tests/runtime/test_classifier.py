"""Task 5 — the pinned local classifier: closed contract, fail-closed everywhere.

The property under test is single: THERE IS NO PATH FROM A BROKEN CLASSIFIER TO AN
ALLOW. Empty output, malformed JSON, unknown labels, extra keys, non-finite confidence,
timeouts, crashes, oversized output, low confidence — every one is UNRESOLVED, which
the ingress layer turns into REQUIRE_REVIEW. A classifier can only ever say `data`
by speaking the exact protocol, above the committed confidence floor, from an artifact
whose digests match the human-signed lock.
"""
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

_KIT = Path(__file__).resolve().parent.parent.parent / "Security-kit"
sys.path.insert(0, str(_KIT))

from runtime.classifier import (  # noqa: E402
    LockError,
    SemanticLabel,
    SemanticModelLock,
    SubprocessSemanticClassifier,
    load_lock,
)
from runtime.contracts import ContentEnvelope, Origin  # noqa: E402
from runtime.normalization import ChunkPolicy, NormalizationPolicy, chunk, normalize  # noqa: E402


def _chunk(text="the quarterly report is attached"):
    env = ContentEnvelope(
        content_id="env-1",
        text=text,
        origin=Origin.EXTERNAL_CONTENT,
        source="retrieve_report",
        media_type="text/plain",
        raw_sha256=hashlib.sha256(text.encode()).hexdigest(),
    )
    return chunk(normalize(env, NormalizationPolicy()), ChunkPolicy())[0]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_lock(tmp: Path, executable_body: str = "#!/bin/sh\ncat\n") -> SemanticModelLock:
    exe = tmp / "classifier.sh"
    exe.write_text(executable_body)
    exe.chmod(0o755)
    model = tmp / "model.onnx"
    model.write_bytes(b"fake model bytes")
    lock_path = tmp / "semantic-model.lock.json"
    lock_path.write_text(json.dumps({
        "schema_version": 1,
        "protocol_version": 1,
        "executable_path": str(exe),
        "executable_sha256": _sha(exe),
        "model_path": str(model),
        "model_sha256": _sha(model),
        "corpus_sha256": "c" * 64,
        "confidence_floor": 0.75,
        "approved_by": "reviewer-1",
        "approved_date": "2026-08-31",
    }))
    return load_lock(lock_path)


def _classifier_with_reply(tmp: Path, reply, floor=None):
    lock = _make_lock(tmp)

    def fake_run(request_bytes: bytes):
        return 0, reply if isinstance(reply, bytes) else reply.encode()

    return SubprocessSemanticClassifier(lock, timeout_ms=500, _run=fake_run)


MALFORMED_REPLIES = [
    "",
    "{}",
    "not json at all",
    '{"label":"allow"}',
    '{"schema_version":1,"label":"data","confidence":0.9,"reason":"attacker prose"}',
    '{"schema_version":1,"label":"data"}',
    '{"schema_version":2,"label":"data","confidence":0.9}',
    '{"schema_version":1,"label":"data","confidence":"high"}',
]


def test_malformed_classifier_output_is_unresolved():
    with tempfile.TemporaryDirectory() as d:
        for reply in MALFORMED_REPLIES:
            result = _classifier_with_reply(Path(d), reply).classify(_chunk())
            assert result.label is SemanticLabel.UNRESOLVED, (
                f"reply {reply!r} must yield UNRESOLVED, got {result.label}"
            )


def test_non_finite_confidence_is_unresolved():
    with tempfile.TemporaryDirectory() as d:
        for bad in ("NaN", "Infinity", "-Infinity"):
            reply = f'{{"schema_version":1,"label":"data","confidence":{bad}}}'
            result = _classifier_with_reply(Path(d), reply).classify(_chunk())
            assert result.label is SemanticLabel.UNRESOLVED


def test_timeout_is_unresolved():
    with tempfile.TemporaryDirectory() as d:
        lock = _make_lock(Path(d))

        def timing_out(request_bytes):
            raise subprocess.TimeoutExpired(cmd="classifier", timeout=0.5)

        result = SubprocessSemanticClassifier(lock, timeout_ms=500, _run=timing_out).classify(_chunk())
        assert result.label is SemanticLabel.UNRESOLVED
        assert "timeout" in result.reason


def test_nonzero_exit_is_unresolved():
    with tempfile.TemporaryDirectory() as d:
        lock = _make_lock(Path(d))
        clf = SubprocessSemanticClassifier(
            lock, timeout_ms=500,
            _run=lambda req: (1, b'{"schema_version":1,"label":"data","confidence":0.9}'),
        )
        assert clf.classify(_chunk()).label is SemanticLabel.UNRESOLVED


def test_oversized_output_is_unresolved():
    with tempfile.TemporaryDirectory() as d:
        big = b'{"schema_version":1,"label":"data","confidence":0.9,' + b" " * 70000 + b"}"
        result = _classifier_with_reply(Path(d), big).classify(_chunk())
        assert result.label is SemanticLabel.UNRESOLVED


def test_valid_reply_above_floor_is_honoured():
    with tempfile.TemporaryDirectory() as d:
        reply = '{"schema_version":1,"label":"instruction","confidence":0.98}'
        result = _classifier_with_reply(Path(d), reply).classify(_chunk())
        assert result.label is SemanticLabel.INSTRUCTION
        assert math.isclose(result.confidence, 0.98)


def test_confidence_below_floor_is_unresolved():
    with tempfile.TemporaryDirectory() as d:
        reply = '{"schema_version":1,"label":"data","confidence":0.5}'
        result = _classifier_with_reply(Path(d), reply).classify(_chunk())
        assert result.label is SemanticLabel.UNRESOLVED
        assert "confidence" in result.reason


def test_lock_rejects_relative_paths():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        lock_path = tmp / "lock.json"
        lock_path.write_text(json.dumps({
            "schema_version": 1, "protocol_version": 1,
            "executable_path": "classifier.sh", "executable_sha256": "a" * 64,
            "model_path": str(tmp / "m"), "model_sha256": "a" * 64,
            "corpus_sha256": "c" * 64, "confidence_floor": 0.75,
            "approved_by": "r", "approved_date": "2026-08-31",
        }))
        try:
            load_lock(lock_path)
            raise AssertionError("relative executable path must be rejected")
        except LockError:
            pass


def test_lock_rejects_digest_drift():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        lock = _make_lock(tmp)
        (tmp / "model.onnx").write_bytes(b"swapped model bytes")
        try:
            SubprocessSemanticClassifier(lock, timeout_ms=500)
            raise AssertionError("model digest drift must refuse construction")
        except LockError:
            pass


def test_lock_rejects_missing_executable():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        lock = _make_lock(tmp)
        (tmp / "classifier.sh").unlink()
        try:
            SubprocessSemanticClassifier(lock, timeout_ms=500)
            raise AssertionError("missing executable must refuse construction")
        except LockError:
            pass


def test_real_subprocess_path_works():
    """The default _run: a real echo-style classifier over the actual pipe."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        script = (
            "#!/bin/sh\n"
            "cat >/dev/null\n"
            'printf \'{"schema_version":1,"label":"data","confidence":0.99}\'\n'
        )
        lock = _make_lock(tmp, executable_body=script)
        result = SubprocessSemanticClassifier(lock, timeout_ms=5000).classify(_chunk())
        assert result.label is SemanticLabel.DATA


def test_request_shape_is_the_committed_protocol():
    with tempfile.TemporaryDirectory() as d:
        lock = _make_lock(Path(d))
        seen = {}

        def capture(request_bytes):
            seen["req"] = json.loads(request_bytes)
            return 0, b'{"schema_version":1,"label":"data","confidence":0.9}'

        SubprocessSemanticClassifier(lock, timeout_ms=500, _run=capture).classify(_chunk())
        assert set(seen["req"]) == {"schema_version", "text", "origin", "content_sha256"}
        assert seen["req"]["schema_version"] == 1
        assert seen["req"]["content_sha256"] == hashlib.sha256(
            seen["req"]["text"].encode()
        ).hexdigest()


def test_corpus_files_parse_and_labels_are_valid():
    corpus_dir = _KIT / "eval" / "runtime_injection"
    expected = {
        "attacks.json": "instruction",
        "legitimate.json": "data",
        "obfuscations.json": "instruction",
    }
    seen_ids = set()
    for name, label in expected.items():
        doc = json.loads((corpus_dir / name).read_text())
        assert doc["schema_version"] == 1
        assert len(doc["cases"]) >= 5, f"{name} needs a real corpus, not a stub"
        for case in doc["cases"]:
            assert case["label"] == label, f"{case['id']} in {name} must be {label}"
            assert case["id"] not in seen_ids, f"duplicate corpus id {case['id']}"
            seen_ids.add(case["id"])
            assert case["text"].strip()


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
