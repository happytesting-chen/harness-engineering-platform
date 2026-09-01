# runtime-security-mvp example

One scripted run of the owned host: a clean prompt enters, a tool returns a **poisoned
document**, the document is withheld before the model, the email sink stays untouched,
the final answer is buffered and redacted, and the whole run is hash-chain audited.

```bash
python3 examples/runtime-security-mvp/run.py
```

## What this demonstrates — and what it does not

**Demonstrates:** the runtime mechanics. The fixed loop order (startup validation →
ingress ① → guarded action ② ③ → result ingress ④ → buffered output), the
nothing-unapproved-enters-context rule, origin taint reaching the action gate, and the
audit chain. The tools are synthetic, the "model" is this script, and the classifier is
a stub that always answers `data` — deliberately, so what you watch is the
*deterministic* layers working alone.

**Does not demonstrate:** detection quality (that is measured, not scripted —
`Security-kit/eval/eval_runtime_injection.py` against the committed corpus, results in
`evaluation/runtime-security/`), production deployment, operating-system confinement,
or unseen-attack resistance. Production readiness is a human-signed verdict scoped to
one exact policy, classifier lock and revision (plan Task 12) — no example can stand in
for it.

## The boundaries in force

Per `Context/runtime-security-profile.md`: persistent memory disabled, delegation
disabled, streaming output disabled, UTF-8 text ingress only — each a **startup
error**, not a warning. The real classifier is pinned by
`Security-kit/runtime/semantic-model.lock.json` (human-signed; artifact digests
verified at construction); swap the stub for `SubprocessSemanticClassifier` with that
lock to run the semantic tier.

## Where the pieces live

| Piece | Module |
|---|---|
| Host loop | `Security-kit/runtime/host.py` |
| Ingress pipeline (the decision table) | `Security-kit/runtime/ingress.py` |
| Action plane (composed, never re-implemented) | `Security-kit/runtime/guarded.py` over `governance/runtime_dispatcher.py` |
| Receipts (content ≠ action, by type and by key) | `Security-kit/runtime/review.py` |
| Audit chain / buffered output | `Security-kit/runtime/audit.py`, `output.py` |
| Proof | `tests/runtime/` — run `python3 -m pytest tests/runtime -q` |
