"""Append-only, hash-chained audit evidence (Task 10).

Each record carries the hash of the previous record, so the JSONL file is a chain:
edit or delete any line and `verify_chain` fails at exactly that point. The schema is
CLOSED — an event with an unknown field is refused with `ValueError`, which is how
"never record raw quarantined content, receipt keys or model-authored rationale" is
enforced mechanically rather than by convention: there is no field to put them in.

Failure policy is explicit and two-valued (AD-6 / plan Task 10):
- `deny` — an action that cannot be audited does not happen; `record()` raises.
- `degrade-and-count` — the action proceeds, and the loss is emitted to a SEPARATE
  monitoring sink so silent evidence loss is impossible.

Stdlib only. The recorder holds a lock; sequence numbers are monotonic per recorder.
"""
import hashlib
import json
import threading
from dataclasses import dataclass
from pathlib import Path

_EVENT_FIELDS = frozenset({
    "event_type", "content_sha256", "action_sha256", "rule_version",
    "classifier_sha256", "policy_sha256", "decision", "receipt_ref",
})
_GENESIS = "0" * 64


class AuditWriteError(Exception):
    """The sink failed and policy is `deny`: the action must not proceed unaudited."""


@dataclass(frozen=True)
class AuditPolicy:
    failure_policy: str
    max_bytes: int

    def __post_init__(self):
        if self.failure_policy not in ("deny", "degrade-and-count"):
            raise ValueError("failure_policy must be 'deny' or 'degrade-and-count'")
        if self.max_bytes <= 0:
            raise ValueError("max_bytes must be positive")


@dataclass(frozen=True)
class AuditRecord:
    schema_version: int
    run_id: str
    session_id: str
    sequence: int
    event_type: str
    content_sha256: str | None
    action_sha256: str | None
    rule_version: str | None
    classifier_sha256: str | None
    policy_sha256: str | None
    decision: str
    receipt_ref: str | None
    previous_hash: str
    record_hash: str


class FileAuditSink:
    """Appends JSONL lines, rotating to `<name>.<n>` when max_bytes is exceeded —
    a bounded evidence file, never unbounded growth (plan Task 10 step 5)."""

    def __init__(self, path, max_bytes: int):
        self._path = Path(path)
        self._max_bytes = max_bytes
        self._rotations = 0

    def append(self, line: str) -> None:
        if self._path.exists() and self._path.stat().st_size + len(line) > self._max_bytes:
            self._rotations += 1
            self._path.rename(self._path.with_name(
                f"{self._path.name}.{self._rotations}"
            ))
        with open(self._path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")


def _record_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class AuditRecorder:
    def __init__(self, *, sink, policy: AuditPolicy, run_id: str, session_id: str,
                 lost_record_sink=None):
        self._sink = sink
        self._policy = policy
        self._run_id = run_id
        self._session_id = session_id
        self._lost = lost_record_sink or (lambda info: None)
        self._lock = threading.Lock()
        self._sequence = 0
        self._previous_hash = _GENESIS

    def record(self, event: dict) -> AuditRecord:
        unknown = set(event) - _EVENT_FIELDS
        if unknown:
            raise ValueError(
                f"audit event carries unknown fields {sorted(unknown)} — the schema is "
                "closed so content, keys and rationale have nowhere to hide"
            )
        missing = _EVENT_FIELDS - set(event)
        if missing:
            raise ValueError(f"audit event missing fields {sorted(missing)}")

        with self._lock:
            self._sequence += 1
            payload = {
                "schema_version": 1,
                "run_id": self._run_id,
                "session_id": self._session_id,
                "sequence": self._sequence,
                "previous_hash": self._previous_hash,
                **{k: event[k] for k in sorted(_EVENT_FIELDS)},
            }
            record_hash = _record_hash(payload)
            record = AuditRecord(**payload, record_hash=record_hash)
            line = json.dumps({**payload, "record_hash": record_hash}, sort_keys=True)
            try:
                self._sink.append(line)
            except Exception as exc:
                if self._policy.failure_policy == "deny":
                    # roll the chain state back: the record was never written
                    self._sequence -= 1
                    raise AuditWriteError(f"audit sink failed: {exc}") from exc
                self._lost({"sequence": self._sequence, "error": str(exc)})
            self._previous_hash = record_hash
            return record


def verify_chain(path) -> tuple:
    """Re-walk a JSONL evidence file. Returns (ok, records_verified) — on tampering,
    verification fails AT the doctored record, and the count says where."""
    previous = _GENESIS
    verified = 0
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        raw = json.loads(line)
        claimed = raw.pop("record_hash")
        if raw.get("previous_hash") != previous or _record_hash(raw) != claimed:
            return False, verified
        previous = claimed
        verified += 1
    return True, verified
