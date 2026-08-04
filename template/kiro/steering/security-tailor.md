---
inclusion: manual
---

# Security Tailor (Kiro)

Invoke on demand or at phase sign-off. Same procedure as `.claude/commands/security-tailor.md`:
read `Context/*.md`, classify all 20 OWASP ids from `Security-kit/owasp-crosswalk.md` into
applies/n_a/gap (each reason citing a `Context/` line), then write `Security-kit/coverage.json`
(per `coverage.schema.md`), update `control-matrix.md` rows for `applies` (Verification left for
the engineer), and regenerate `Security-kit/active-controls.md` with only the applicable controls.
Do not invent controls or edit policy. Print the n_a + gap report.
