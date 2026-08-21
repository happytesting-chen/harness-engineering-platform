# coverage.json — schema (security-tailor contract)

Machine-readable output of `/security-tailor`. Consumed by `check_coverage.py`.
**Generated — do not hand-edit; re-run the skill.**

## Shape

```jsonc
{
  "schema_version": 2,
  "generated_from": "Context/ @ <sha256 of sorted non-.template *.md under Context/>",
  "generated_note": "produced by security-tailor; do not hand-edit — re-run the skill",
  "controls": [
    { "id": "LLM01", "verdict": "applies", "plane": ["runtime", "build"], "reason": "reads untrusted claim text (Context/product-design.md:12)", "matrix_row": "SEC-INPUT-001" },
    { "id": "LLM08", "verdict": "n_a",     "plane": ["runtime"], "reason": "no retrieval/vector store (Context/architecture.md:4)" },
    { "id": "ASI03", "verdict": "gap",     "plane": ["runtime"], "gap_kind": "no_mechanism",  "reason": "cloud deploy, no identity broker (Context/deployment.md:8)" },
    { "id": "LLM09", "verdict": "gap",     "plane": ["runtime"], "gap_kind": "undetermined",  "reason": "Context/ does not say whether output reaches a user unreviewed" }
  ]
}
```

## Rules
- One entry per OWASP id in `owasp-crosswalk.md` (LLM01–10, ASI01–10). All 20 present.
- `verdict ∈ {applies, n_a, gap}`.
- `applies` REQUIRES `matrix_row` (a Control ID in `control-matrix.md`).
- `plane` REQUIRED on every entry — a non-empty list drawn from `{runtime, build}`, no
  repeats. These documents describe two subjects: the product at runtime, and the agent
  that builds it. A verdict that does not say which one it judged cannot be checked —
  "no retrieval" is true of the product and false of a build agent that reads every file
  in `Context/`. List both when the id genuinely applies to both.
- `gap_kind` REQUIRED on `gap`, and FORBIDDEN on any other verdict. Two values:
  - `no_mechanism` — the product has this surface; the template offers nothing for it.
    **Needs a control owner.** Carries the same citation burden as an `applies`, because
    it asserts the surface exists.
  - `undetermined` — `Context/` does not answer it. **Needs an answer from a human**, and
    is the only verdict exempt from citing a `Context/` line.
- Every other `reason` MUST cite a `Context/` line that resolves — real file, in range,
  not blank. No citation ⇒ record `gap` / `undetermined`, never guess.
- `generated_from` hash lets `check_coverage.py` detect staleness. The skill writes it as
  `"Context/ @ UNSTAMPED"` then runs `check_coverage.py --stamp` to fill the real hash —
  it is NEVER hand-computed (an LLM cannot produce a correct sha256).
