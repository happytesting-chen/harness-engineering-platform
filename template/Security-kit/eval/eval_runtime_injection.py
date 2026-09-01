"""Benchmark and verification gate for the runtime semantic classifier (Task 5).

Two modes:

  --candidate-manifest M.json --output DIR
      Measure one candidate against the committed corpus. Reports rule-only,
      semantic-only and combined results by case ID, unresolved/error counts, p50/p95
      latency, and every relevant digest. Writes ONE immutable JSON result per run —
      an existing result file is never overwritten. Committed corpus labels are the
      oracle; no model judges whether its own answer is correct.

  --lock semantic-model.lock.json --verify
      Re-verify a signed lock: artifact digests match the files on disk, and the
      corpus digest matches the corpus as committed. This is what CI and Task 12
      replay call; PASS means the approved measurement still describes this tree.

Exit codes: 0 = PASS / result written · 1 = verification or protocol failure.
Stdlib only. The classifier process behind the manifest may use anything (AD-8).
"""
import argparse
import hashlib
import json
import statistics
import sys
import time
from pathlib import Path

_KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_KIT))

from runtime.classifier import (  # noqa: E402
    LockError,
    SemanticLabel,
    SemanticModelLock,
    SubprocessSemanticClassifier,
    load_lock,
)
from runtime.contracts import ContentEnvelope, Origin  # noqa: E402
from runtime.normalization import (  # noqa: E402
    ChunkPolicy,
    ContentTooLarge,
    NormalizationPolicy,
    chunk,
    normalize,
)
from runtime.rules import RuleLabel, RulePolicy, evaluate_rules  # noqa: E402

CORPUS_DIR = _KIT / "eval" / "runtime_injection"
CORPUS_FILES = ("attacks.json", "legitimate.json", "obfuscations.json")
RULE_POLICY = RulePolicy(version="rules-v1")


def corpus_sha256() -> str:
    """One digest over the three corpus files, in fixed order, as committed bytes."""
    h = hashlib.sha256()
    for name in CORPUS_FILES:
        h.update(name.encode())
        h.update((CORPUS_DIR / name).read_bytes())
    return h.hexdigest()


def load_corpus() -> list:
    cases = []
    for name in CORPUS_FILES:
        doc = json.loads((CORPUS_DIR / name).read_text(encoding="utf-8"))
        for case in doc["cases"]:
            cases.append({**case, "file": name})
    return cases


def _envelope(case) -> ContentEnvelope:
    return ContentEnvelope(
        content_id=case["id"],
        text=case["text"],
        origin=Origin.EXTERNAL_CONTENT,
        source=case["file"],
        media_type="text/plain",
        raw_sha256=hashlib.sha256(case["text"].encode("utf-8")).hexdigest(),
    )


def _rule_label(case) -> str:
    """Rule layer over normalized chunks: instruction if ANY chunk trips."""
    try:
        normalized = normalize(_envelope(case), NormalizationPolicy())
        chunks = chunk(normalized, ChunkPolicy())
    except ContentTooLarge:
        return "too-large"
    for c in chunks:
        piece = normalized.__class__(
            content_id=normalized.content_id, text=c.text,
            raw_sha256=normalized.raw_sha256,
            normalized_sha256=normalized.normalized_sha256,
            signals=normalized.signals,
        )
        if evaluate_rules(piece, RULE_POLICY).label is RuleLabel.INSTRUCTION:
            return "instruction"
    return "unresolved"


def _semantic_label(case, classifier) -> tuple:
    """Semantic layer over chunks: strictest chunk wins. Returns (label, seconds)."""
    normalized = normalize(_envelope(case), NormalizationPolicy())
    chunks = chunk(normalized, ChunkPolicy())
    worst = SemanticLabel.DATA
    started = time.perf_counter()
    for c in chunks:
        got = classifier.classify(c).label
        if got is SemanticLabel.INSTRUCTION:
            worst = got
            break
        if got is SemanticLabel.UNRESOLVED:
            worst = SemanticLabel.UNRESOLVED
    return worst.value, time.perf_counter() - started


def run_candidate(manifest_path: Path, output_dir: Path) -> int:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    lock = SemanticModelLock(
        schema_version=1,
        protocol_version=1,
        executable_path=manifest["executable_path"],
        executable_sha256=manifest["executable_sha256"],
        model_path=manifest["model_path"],
        model_sha256=manifest["model_sha256"],
        corpus_sha256=corpus_sha256(),
        confidence_floor=manifest["confidence_floor"],
        approved_by="UNAPPROVED-CANDIDATE",
        approved_date="0000-00-00",
    )
    try:
        classifier = SubprocessSemanticClassifier(lock, timeout_ms=manifest["timeout_ms"])
    except LockError as exc:
        print(f"INELIGIBLE: {exc}")
        return 1

    cases = load_corpus()
    per_case, latencies, protocol_errors = [], [], 0
    for case in cases:
        rule = _rule_label(case)
        semantic, seconds = _semantic_label(case, classifier)
        latencies.append(seconds)
        combined = (
            "REQUIRE_REVIEW"
            if rule != "unresolved" or semantic != "data"
            else "ALLOW"
        )
        expected = "REQUIRE_REVIEW" if case["label"] == "instruction" else "ALLOW"
        per_case.append({
            "id": case["id"], "oracle": case["label"], "rule": rule,
            "semantic": semantic, "combined": combined,
            "correct": combined == expected,
        })
        if semantic == "unresolved":
            protocol_errors += 0  # unresolved is a valid outcome, not a protocol error

    attacks = [c for c in per_case if c["oracle"] == "instruction"]
    legit = [c for c in per_case if c["oracle"] == "data"]
    result = {
        "schema_version": 1,
        "candidate": manifest["name"],
        "executable_sha256": manifest["executable_sha256"],
        "model_sha256": manifest["model_sha256"],
        "corpus_sha256": corpus_sha256(),
        "confidence_floor": manifest["confidence_floor"],
        "attacks_caught_combined": sum(c["combined"] == "REQUIRE_REVIEW" for c in attacks),
        "attacks_total": len(attacks),
        "attacks_caught_rule_only": sum(c["rule"] == "instruction" for c in attacks),
        "legitimate_withheld_combined": sum(c["combined"] == "REQUIRE_REVIEW" for c in legit),
        "legitimate_total": len(legit),
        "semantic_unresolved": sum(c["semantic"] == "unresolved" for c in per_case),
        "latency_p50_ms": round(statistics.median(latencies) * 1000, 2),
        "latency_p95_ms": round(sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)] * 1000, 2),
        "cases": per_case,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / f"{manifest['name']}.result.json"
    if out.exists():
        print(f"REFUSED: {out} exists — results are immutable, use a new candidate name")
        return 1
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE {out}")
    print(f"  combined: {result['attacks_caught_combined']}/{result['attacks_total']} attacks caught, "
          f"{result['legitimate_withheld_combined']}/{result['legitimate_total']} legitimate withheld")
    print(f"  rule-only: {result['attacks_caught_rule_only']}/{result['attacks_total']} attacks caught")
    print(f"  latency p50 {result['latency_p50_ms']}ms · p95 {result['latency_p95_ms']}ms")
    return 0


def verify_lock_mode(lock_path: Path) -> int:
    try:
        lock = load_lock(lock_path)
        SubprocessSemanticClassifier(lock, timeout_ms=1000)  # verifies artifact digests
    except LockError as exc:
        print(f"FAIL: {exc}")
        return 1
    actual = corpus_sha256()
    if actual != lock.corpus_sha256:
        print(f"FAIL: corpus digest drift — lock {lock.corpus_sha256[:12]}…, tree {actual[:12]}…")
        return 1
    print(f"PASS: artifacts and corpus match the approved lock "
          f"(approved by {lock.approved_by}, {lock.approved_date})")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-manifest", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--lock", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args(argv)

    if args.lock and args.verify:
        return verify_lock_mode(args.lock)
    if args.candidate_manifest and args.output:
        return run_candidate(args.candidate_manifest, args.output)
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
