#!/usr/bin/env python3
"""Evaluation primitive — quantify a task's quality, not just assert correctness.

The harness already has two proofs:
  - tests/    asserts the claims engine is CORRECT (pass/fail ground truth)
  - demo/     shows enforcement MATTERS (gated vs --nogate)

This module adds the third: it QUANTIFIES a task over four axes and emits a
snapshot report a human can sign off:

  - Accuracy        decisions vs a known oracle           (real)
  - Reproducibility identical output across repeat runs   (real)
  - Latency         wall-clock per case                   (real)
  - Cost            tokens / $                            (only if the task
                    reports usage; otherwise N/A — never fabricated)

`evaluate()` is generic: give it cases, a `decide_fn`, and the oracle key. The
reference wiring at the bottom measures the project's OWN task — the
deterministic claims decision engine (claims.decide) over the committed labeled
fixtures — so it runs with zero deps and no API key. To evaluate a different
task (e.g. the LLM extraction front-end), pass your own `decide_fn` (and a
`usage_fn` if your provider reports token usage) — see README.md.

Stdlib only. No network, no provider, no keys.

Usage:
    python3 evaluation/eval.py                 # evaluate claims.decide, print report
    python3 evaluation/eval.py --snapshot DIR  # also write a filled SNAPSHOT.md
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Callable

EVAL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EVAL_DIR.parent

# A task that does not wire a real model reports no token usage. We render this
# as an explicit "N/A" rather than inventing a number.
COST_NOT_AVAILABLE = "N/A (no real provider wired)"


def evaluate(
    cases: list[dict],
    decide_fn: Callable[[dict], str],
    oracle_key: str,
    *,
    repeats: int = 2,
    usage_fn: Callable[[dict], dict] | None = None,
) -> dict:
    """Run every case through decide_fn and measure the four axes.

    Args:
        cases:      list of case dicts (each carries its own oracle value).
        decide_fn:  case -> normalized decision string (the thing under test).
        oracle_key: key in each case holding the expected decision string.
        repeats:    how many times to re-run each case for reproducibility.
        usage_fn:   optional case -> {"tokens": int, "usd": float}; when None,
                    cost is reported as N/A (not fabricated).

    Returns a metrics dict (see keys assembled at the end). Pure measurement —
    no assertions, no side effects.
    """
    if repeats < 1:
        raise ValueError("repeats must be >= 1")

    total = len(cases)
    correct = 0
    reproducible = 0
    per_case = []
    latencies_ms: list[float] = []
    tokens_total = 0
    usd_total = 0.0
    have_usage = usage_fn is not None

    for idx, case in enumerate(cases):
        expected = case.get(oracle_key)

        # First run is the graded one; time it in isolation.
        t0 = time.perf_counter()
        first = decide_fn(case)
        latency_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(latency_ms)

        # Remaining runs check the output is stable (deterministic).
        stable = True
        for _ in range(repeats - 1):
            if decide_fn(case) != first:
                stable = False

        is_correct = (first == expected)
        if is_correct:
            correct += 1
        if stable:
            reproducible += 1

        if have_usage:
            u = usage_fn(case) or {}
            tokens_total += int(u.get("tokens", 0))
            usd_total += float(u.get("usd", 0.0))

        per_case.append({
            "index": idx,
            "expected": expected,
            "actual": first,
            "correct": is_correct,
            "reproducible": stable,
            "latency_ms": round(latency_ms, 3),
        })

    def _pct(n: int) -> float:
        return round(100.0 * n / total, 1) if total else 0.0

    return {
        "total_cases": total,
        "repeats": repeats,
        "accuracy_pct": _pct(correct),
        "correct": correct,
        "reproducibility_pct": _pct(reproducible),
        "reproducible": reproducible,
        "latency_ms_mean": round(sum(latencies_ms) / total, 3) if total else 0.0,
        "latency_ms_max": round(max(latencies_ms), 3) if latencies_ms else 0.0,
        "cost_tokens": tokens_total if have_usage else COST_NOT_AVAILABLE,
        "cost_usd": round(usd_total, 6) if have_usage else COST_NOT_AVAILABLE,
        "per_case": per_case,
    }


def format_report(metrics: dict, *, target: str) -> str:
    """Render metrics as a compact, human-readable block."""
    lines = [
        f"Evaluation target: {target}",
        f"  cases={metrics['total_cases']}  repeats={metrics['repeats']}",
        f"  accuracy         {metrics['accuracy_pct']}%  "
        f"({metrics['correct']}/{metrics['total_cases']})",
        f"  reproducibility  {metrics['reproducibility_pct']}%  "
        f"({metrics['reproducible']}/{metrics['total_cases']})",
        f"  latency          mean {metrics['latency_ms_mean']} ms  "
        f"max {metrics['latency_ms_max']} ms",
        f"  cost (tokens)    {metrics['cost_tokens']}",
        f"  cost (usd)       {metrics['cost_usd']}",
    ]
    misses = [c for c in metrics["per_case"] if not c["correct"]]
    if misses:
        lines.append(f"  MISSES ({len(misses)}):")
        for c in misses:
            lines.append(
                f"    case #{c['index']}: expected {c['expected']!r} "
                f"got {c['actual']!r}"
            )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Reference wiring: evaluate the project's OWN task — the deterministic claims
# decision engine (claims.decide) over the committed labeled fixtures. This is
# the thing this harness actually produces, so "accuracy" here means claims
# accuracy, not gate accuracy. Swap decide_fn for a different task (e.g. the LLM
# extraction front-end) to measure that instead — see README.md.
# ---------------------------------------------------------------------------

# The oracle string is OUTCOME/REASON_CODE, e.g. "APPROVED/EXACT_COVERAGE". This
# is what claims.decide effectively produces and what each fixture's `expected`
# block records — a single normalized token the evaluator can compare exactly.
def _oracle_string(expected: dict) -> str:
    return f"{expected['outcome']}/{expected['reason_code']}"


def _claims_decide_fn():
    """Return (cases, decide_fn, oracle_key, cleanup) wired to claims.decide.

    Each case is a wrapper {"record": <wire claim>, "oracle": "OUTCOME/REASON"}.
    decide_fn reads only "record" and calls the REAL claims.decide — the oracle
    is never fed into the decision path (validate() would reject an injected
    oracle field anyway; keeping it in a wrapper makes the separation explicit).
    """
    proj = str(PROJECT_ROOT)
    if proj not in sys.path:
        sys.path.insert(0, proj)
    from claims import decide as claims_decide  # noqa: E402

    fixtures_dir = PROJECT_ROOT / "claims" / "tests" / "fixtures"
    cases = []
    for path in sorted(fixtures_dir.glob("*.json")):
        fixture = json.loads(path.read_text())
        expected = fixture.get("expected")
        if not isinstance(expected, dict):
            continue  # a fixture with no oracle can't be graded — skip it
        # The record fed to decide() is the fixture MINUS the oracle block, so
        # the expected answer never reaches the decision logic.
        record = {k: v for k, v in fixture.items() if k != "expected"}
        cases.append({"record": record, "oracle": _oracle_string(expected)})

    def decide_fn(case: dict) -> str:
        outcome = claims_decide(case["record"])
        return f"{outcome.outcome}/{outcome.reason_code}"

    def cleanup():
        pass  # no global state mutated — nothing to restore

    return cases, decide_fn, "oracle", cleanup


def _fill_snapshot(metrics: dict, target: str, out_dir: Path) -> Path:
    """Fill SNAPSHOT.template.md with metrics and write it under out_dir."""
    template = (EVAL_DIR / "SNAPSHOT.template.md").read_text()
    filled = (
        template
        .replace("{{TARGET}}", target)
        .replace("{{TOTAL_CASES}}", str(metrics["total_cases"]))
        .replace("{{REPEATS}}", str(metrics["repeats"]))
        .replace("{{ACCURACY_PCT}}", str(metrics["accuracy_pct"]))
        .replace("{{CORRECT}}", str(metrics["correct"]))
        .replace("{{REPRODUCIBILITY_PCT}}", str(metrics["reproducibility_pct"]))
        .replace("{{REPRODUCIBLE}}", str(metrics["reproducible"]))
        .replace("{{LATENCY_MEAN}}", str(metrics["latency_ms_mean"]))
        .replace("{{LATENCY_MAX}}", str(metrics["latency_ms_max"]))
        .replace("{{COST_TOKENS}}", str(metrics["cost_tokens"]))
        .replace("{{COST_USD}}", str(metrics["cost_usd"]))
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "SNAPSHOT.md"
    out_path.write_text(filled)
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="eval", description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=None,
                        help="directory to write a filled SNAPSHOT.md into")
    args = parser.parse_args(argv)

    cases, decide_fn, oracle_key, cleanup = _claims_decide_fn()
    target = "claims decision engine (claims.decide) over claims/tests/fixtures/*.json"
    try:
        metrics = evaluate(cases, decide_fn, oracle_key, repeats=3)
    finally:
        cleanup()

    print(format_report(metrics, target=target))

    if args.snapshot is not None:
        path = _fill_snapshot(metrics, target, args.snapshot)
        print(f"\nSnapshot written: {path}")

    # Exit non-zero only if the reference target regressed — accuracy and
    # reproducibility of the deterministic engine should both be 100%.
    ok = metrics["accuracy_pct"] == 100.0 and metrics["reproducibility_pct"] == 100.0
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
