"""claims_runner — the executable entrypoint the governance allowlist gates.

`governance/mcp-allowlist.json` declares a tool named ``claims_runner`` with
``gated_until: phase-01``. This module IS that tool: it reads exactly one
untrusted claim fixture, runs the deterministic pipeline, and emits exactly one
minimal local result. The gate decides whether this may run; this code performs
no policy of its own beyond the fail-closed writer.

Stdlib only. No LLM/provider, network, cloud, credentials, email, or external
action. The fixture is DATA — it is parsed, never executed or obeyed.

Usage:
    python3 -m claims.runner <fixture.json> --out <result_dir>
    python3 -m claims.runner <fixture.json>          # decide only, no write

Exit codes:
    0  decision produced (and, if --out given, one minimal result written)
    2  fail-closed: unreadable/invalid input, or a refused/duplicate/out-of-bound write
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .pipeline import decide, process
from .writer import WriteBoundaryError

TOOL_NAME = "claims_runner"


def _load_fixture(path: Path) -> object:
    """Read and JSON-parse the fixture. Any failure is fail-closed (exit 2)."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"{TOOL_NAME}: cannot read {path}: {exc}", file=sys.stderr)
        raise SystemExit(2)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        print(f"{TOOL_NAME}: {path} is not valid JSON: {exc}", file=sys.stderr)
        raise SystemExit(2)


def run(fixture_path: Path, out_dir: Path | None) -> int:
    """Process one fixture; return an exit code. No side effects beyond one write."""
    record = _load_fixture(fixture_path)

    if out_dir is None:
        outcome = decide(record)
    else:
        try:
            outcome = process(record, boundary=out_dir)
        except WriteBoundaryError as exc:
            # Missing/duplicate/out-of-bound/unattributable write → fail closed.
            print(f"{TOOL_NAME}: write refused (fail-closed): {exc}", file=sys.stderr)
            return 2

    # Minimal, attributable line to stdout — no fixture payload echoed back.
    print(json.dumps(
        {"claim_id": outcome.claim_id, "outcome": outcome.outcome,
         "reason_code": outcome.reason_code},
        sort_keys=True, separators=(",", ":"),
    ))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="claims_runner", description=__doc__)
    parser.add_argument("fixture", type=Path, help="path to one claim fixture JSON")
    parser.add_argument("--out", type=Path, default=None,
                        help="approved local result boundary; omit to decide only")
    args = parser.parse_args(argv)
    return run(args.fixture, args.out)


if __name__ == "__main__":
    raise SystemExit(main())
