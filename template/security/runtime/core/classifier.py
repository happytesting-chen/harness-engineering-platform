"""Pinned local semantic classifier — protocol, subprocess adapter, lock (Task 5, AD-3/AD-5).

The one property everything here serves: **there is no path from a broken classifier to
an allow.** The adapter returns `UNRESOLVED` — never raises toward the caller, never
guesses — for every failure shape: timeout, crash, empty output, malformed JSON, wrong
schema version, unknown label, extra keys, non-numeric or non-finite confidence,
oversized output, confidence below the committed floor. The ingress layer (Task 6) maps
`UNRESOLVED` to REQUIRE_REVIEW.

AD-3: this classifier is detection, not authority. It returns a label and a confidence
over a closed JSON contract; no prose it produces is ever forwarded to model context or
a control decision. The `reason` field on `SemanticDecision` is adapter-authored
diagnostic text (our words), never classifier output.

AD-5: the artifact is pinned. `load_lock` and construction verify absolute paths,
regular files and SHA-256 digests of both the executable and the model artifact; drift
refuses construction with `LockError`. The lock file is written by a HUMAN at the
Task 5 selection gate after reviewing measured benchmark results — code in this repo
never generates it.

Wire protocol (version 1), one JSON object each way, newline-delimited:

    request  {"schema_version":1,"text":"...","origin":"EXTERNAL_CONTENT","content_sha256":"..."}
    response {"schema_version":1,"label":"instruction|data|unresolved","confidence":0.0..1.0}

A response with ANY other key set, or any deviation, is treated as malformed. Stdlib
only in this module; the classifier process itself may use whatever it likes — that is
the point of the subprocess boundary (AD-8).
"""
import hashlib
import json
import math
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .normalization import ContentChunk

PROTOCOL_VERSION = 1
_MAX_RESPONSE_BYTES = 65_536
_RESPONSE_KEYS = frozenset({"schema_version", "label", "confidence"})


class SemanticLabel(str, Enum):
    INSTRUCTION = "instruction"
    DATA = "data"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class SemanticDecision:
    label: SemanticLabel
    confidence: float
    classifier_sha256: str
    reason: str = ""


class LockError(Exception):
    """The lock file, or the artifacts it pins, cannot be trusted. Construction-time
    failure — a runtime-mvp profile with semantic enforcement enabled must not start."""


@dataclass(frozen=True)
class SemanticModelLock:
    schema_version: int
    protocol_version: int
    executable_path: str
    executable_sha256: str
    model_path: str
    model_sha256: str
    corpus_sha256: str
    confidence_floor: float
    approved_by: str
    approved_date: str


_LOCK_FIELDS = (
    "schema_version", "protocol_version", "executable_path", "executable_sha256",
    "model_path", "model_sha256", "corpus_sha256", "confidence_floor",
    "approved_by", "approved_date",
)


def load_lock(path) -> SemanticModelLock:
    """Parse and statically validate a lock file. Digest verification against the
    artifacts happens at classifier construction, so drift after load still refuses."""
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LockError(f"unreadable lock file {path}: {exc}") from exc
    if not isinstance(raw, dict) or set(raw) != set(_LOCK_FIELDS):
        raise LockError(
            f"lock must contain exactly the fields {sorted(_LOCK_FIELDS)}"
        )
    lock = SemanticModelLock(**raw)
    if lock.schema_version != 1 or lock.protocol_version != PROTOCOL_VERSION:
        raise LockError("unsupported lock schema or protocol version")
    for name in ("executable_path", "model_path"):
        p = Path(getattr(lock, name))
        if not p.is_absolute():
            raise LockError(f"{name} must be absolute, got {p}")
    for name in ("executable_sha256", "model_sha256", "corpus_sha256"):
        v = getattr(lock, name)
        if not (isinstance(v, str) and len(v) == 64):
            raise LockError(f"{name} must be a sha256 hex digest")
    if not (isinstance(lock.confidence_floor, (int, float))
            and math.isfinite(lock.confidence_floor)
            and 0.0 <= lock.confidence_floor <= 1.0):
        raise LockError("confidence_floor must be a finite number in [0, 1]")
    if not (lock.approved_by.strip() and lock.approved_date.strip()):
        raise LockError("lock must carry approval identity and date")
    return lock


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def _verify_artifacts(lock: SemanticModelLock) -> None:
    for name, digest in (("executable_path", lock.executable_sha256),
                         ("model_path", lock.model_sha256)):
        p = Path(getattr(lock, name))
        if not p.is_file():
            raise LockError(f"{name} {p} is not a regular file")
        actual = _file_sha256(p)
        if actual != digest:
            raise LockError(
                f"digest drift on {name}: lock says {digest[:12]}…, file is {actual[:12]}…"
            )


class SubprocessSemanticClassifier:
    """Speaks protocol v1 to the pinned executable. Every failure is UNRESOLVED."""

    def __init__(self, lock: SemanticModelLock, timeout_ms: int, *, _run=None):
        if timeout_ms <= 0:
            raise ValueError("timeout_ms must be positive")
        _verify_artifacts(lock)
        self._lock = lock
        self._timeout_s = timeout_ms / 1000.0
        # _run exists for tests; the default is the real subprocess. Injecting a runner
        # does NOT bypass lock verification — that already ran above.
        self._run = _run if _run is not None else self._run_subprocess

    def _run_subprocess(self, request_bytes: bytes):
        proc = subprocess.run(
            [self._lock.executable_path, self._lock.model_path],
            input=request_bytes,
            capture_output=True,
            timeout=self._timeout_s,
        )
        return proc.returncode, proc.stdout

    def _unresolved(self, reason: str) -> SemanticDecision:
        return SemanticDecision(
            label=SemanticLabel.UNRESOLVED,
            confidence=0.0,
            classifier_sha256=self._lock.model_sha256,
            reason=reason,
        )

    def classify(self, chunk: ContentChunk) -> SemanticDecision:
        request = json.dumps({
            "schema_version": PROTOCOL_VERSION,
            "text": chunk.text,
            "origin": "EXTERNAL_CONTENT",
            "content_sha256": hashlib.sha256(chunk.text.encode("utf-8")).hexdigest(),
        }, sort_keys=True).encode("utf-8")

        try:
            exit_code, stdout = self._run(request)
        except subprocess.TimeoutExpired:
            return self._unresolved("timeout")
        except OSError as exc:
            return self._unresolved(f"spawn failure: {type(exc).__name__}")

        if exit_code != 0:
            return self._unresolved(f"non-zero exit {exit_code}")
        if not stdout:
            return self._unresolved("empty output")
        if len(stdout) > _MAX_RESPONSE_BYTES:
            return self._unresolved("oversized output")

        try:
            reply = json.loads(stdout.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return self._unresolved("malformed output")
        if not isinstance(reply, dict) or set(reply) != _RESPONSE_KEYS:
            return self._unresolved("wrong response keys")
        if reply["schema_version"] != PROTOCOL_VERSION:
            return self._unresolved("wrong schema version")

        label_raw = reply["label"]
        try:
            label = SemanticLabel(label_raw)
        except ValueError:
            return self._unresolved(f"unknown label {label_raw!r}")

        confidence = reply["confidence"]
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            return self._unresolved("non-numeric confidence")
        if not math.isfinite(confidence) or not (0.0 <= confidence <= 1.0):
            return self._unresolved("confidence out of range")

        if label is SemanticLabel.UNRESOLVED:
            return self._unresolved("classifier abstained")
        if confidence < self._lock.confidence_floor:
            return self._unresolved(
                f"confidence {confidence:.2f} below floor {self._lock.confidence_floor:.2f}"
            )

        return SemanticDecision(
            label=label,
            confidence=float(confidence),
            classifier_sha256=self._lock.model_sha256,
            reason="",
        )
