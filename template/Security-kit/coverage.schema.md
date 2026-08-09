# coverage.json — schema (security-tailor contract)

Machine-readable output of `/security-tailor`. Consumed by `check_coverage.py`.
**Generated — do not hand-edit; re-run the skill.**

## Shape

```jsonc
{
  "schema_version": 1,
  "generated_from": "Context/ @ <sha256 of sorted non-.template *.md under Context/>",
  "generated_note": "produced by security-tailor; do not hand-edit — re-run the skill",
  "controls": [
    { "id": "LLM01", "verdict": "applies", "reason": "reads untrusted claim text (Context/product-design.md:12)", "matrix_row": "SEC-INPUT-001" },
    { "id": "LLM08", "verdict": "n_a",     "reason": "no retrieval/vector store (Context/architecture.md)" },
    { "id": "ASI03", "verdict": "gap",     "reason": "cloud deploy, no identity broker (Context/deployment.md:8)" }
  ]
}
```

## Rules
- One entry per OWASP id in `owasp-crosswalk.md` (LLM01–10, ASI01–10). All 20 present.
- `verdict ∈ {applies, n_a, gap}`.
- `applies` REQUIRES `matrix_row` (a Control ID in `control-matrix.md`).
- Every `reason` MUST cite a `Context/` line; no citation ⇒ report as a flagged gap, never guess.
- `generated_from` hash lets `check_coverage.py` detect staleness. The skill writes it as
  `"Context/ @ UNSTAMPED"` then runs `check_coverage.py --stamp` to fill the real hash —
  it is NEVER hand-computed (an LLM cannot produce a correct sha256).
