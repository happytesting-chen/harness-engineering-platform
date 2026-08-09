"""Stage 4 — One minimal local result (fail-closed writer).

A result is successful only if exactly ONE minimal write completes inside the
approved local result boundary. Missing, duplicate, failed, non-minimal, or
out-of-bound writes fail closed (raise WriteBoundaryError) and cannot support
fixture success.

The write is local-filesystem only — no network, cloud, credential, or external
action. The payload is minimal: terminal outcome, reason code, and the
attributable claim id. No fixture payload, secrets, or free text are copied.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .outcomes import Outcome, is_terminal


class WriteBoundaryError(Exception):
    """Raised when a write would be missing, duplicate, or out-of-bound."""


def _resolved_within(path: Path, boundary: Path) -> bool:
    """True iff ``path`` resolves strictly inside ``boundary``."""
    try:
        path.resolve().relative_to(boundary.resolve())
        return True
    except ValueError:
        return False


def write_result(outcome: Outcome, boundary: Path) -> Path:
    """Write one minimal result file into ``boundary`` and return its path.

    Fail-closed guarantees:
      - the outcome must be terminal (defensive; router already guarantees it);
      - the target must resolve inside ``boundary`` (no path traversal / escape);
      - the file must not already exist (no duplicate/overwrite — exclusive create).
    """
    if not is_terminal(outcome.outcome):
        raise WriteBoundaryError(f"non-terminal outcome: {outcome.outcome!r}")
    if outcome.claim_id is None:
        # Cannot attribute the result to a claim — refuse rather than write anonymously.
        raise WriteBoundaryError("missing claim_id; cannot attribute result")

    boundary = boundary.resolve()
    boundary.mkdir(parents=True, exist_ok=True)

    target = (boundary / f"{outcome.claim_id}.result.json")
    if not _resolved_within(target, boundary):
        raise WriteBoundaryError(f"target escapes boundary: {target}")
    if target.exists():
        raise WriteBoundaryError(f"duplicate write refused: {target.name}")

    payload = {
        "claim_id": outcome.claim_id,
        "outcome": outcome.outcome,
        "reason_code": outcome.reason_code,
    }
    # Exclusive create ("x") turns any pre-existing file into a hard failure —
    # the write is the single source of the result, never an overwrite.
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    try:
        with open(target, "x", encoding="utf-8") as fh:
            fh.write(body)
            fh.write("\n")
    except FileExistsError as exc:  # race: someone created it between checks
        raise WriteBoundaryError(f"duplicate write refused: {target.name}") from exc

    return target
