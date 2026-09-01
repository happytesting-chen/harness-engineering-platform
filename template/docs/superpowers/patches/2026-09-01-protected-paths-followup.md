# Protect the runtime-mvp modules (acceptance condition 19) — RESOLVED, Option B

**Status:** authored and verified as
`2026-09-01-protect-runtime-modules.patch`. Human-apply (both `permission.py` and
`deny-list.json` are protected paths). Split out of the claims batch 2026-09-01 after the
bundled first attempt broke the shell census.

## The risk this closes

Before this patch the 15 runtime-mvp enforcement modules and the human-signed classifier
lock were **not** in `BUILTIN_PROTECTED_PATHS`. An agent `Edit` to
`Security-kit/runtime/host.py` — or to `ingress.py`, or to the signed lock — was
**ALLOWED**. Every control the runtime profile claims was editable by the agent it
constrains, which is the exact failure `SEC-SELF-001` exists to prevent and the reason
the runtime pair joined the list on 2026-08-22 in the same commit as the mechanism.

## Why Option B (full parity), not Option A (structured-only)

Option A would have added the paths to `BUILTIN_PROTECTED_PATHS` and to `UNCOVERED_PATHS`,
accepting that the shell deny-list never names them. Measured, that produced **243 of 378
cells open (36% closed, down from 54%)** and broke
`test_the_open_set_has_exactly_two_shapes` — the runtime paths formed a **third** gap
family, so the residual could no longer be stated in one sentence.

Option B instead gives the runtime modules the same shell coverage every other mechanism
file has, by adding a `Security-kit/runtime/` prefix to the two deny-list families that
enumerate filenames (redirect `>`/`>>`, and `chmod|chown|rm|mv`). The other two families
(`sed|perl|awk -i`, `tee|truncate|dd of=`) already use a bare `Security-kit/` prefix and
covered the new paths with no change.

**Measured result: 158 of 392 cells open — 60% closed, IMPROVED from 54%.** Adding paths
that carry full coverage dilutes the two uncovered audit paths, so the ratio rises rather
than falls, and the gap keeps its two-family shape.

## What the patch contains

| File | Change |
|---|---|
| `governance/permission.py` | `BUILTIN_PROTECTED_PATHS` 12 → 28: the 15 runtime modules + `semantic-model.lock.json` |
| `governance/deny-list.json` | `Security-kit/runtime/` prefix added to the redirect and `chmod\|chown\|rm\|mv` families; the same paths mirrored into the advisory `protected_paths` list |
| `tests/test_protected_paths.py` | census pins 78 → 158 open, 168 → 392 total, with the reasoning comment rewritten |
| `control-matrix.md`, `mechanisms.json`, `SECURITY.md` | the SEC-SELF-001 / S2.4 census citations, all three moved together |

**Deliberately NOT protected:** `runtime/attack_driver.py` (evaluation tooling) and
`runtime/semantic-model.schema.json` (inert documentation of the lock format) — matching
how `Security-kit/eval/` is left unprotected. Both still gain shell coverage from the
directory prefix; they are simply not claimed as protected paths in the census.

## Verification (done in a scratch copy of the template, not the working tree)

- `pytest tests -q` → **309 passed**, including `test_protected_paths.py` in full
- `test_shell_patterns_block_the_common_forms_they_claim` → passes (redirect now covers runtime)
- `test_the_open_set_has_exactly_two_shapes` → passes (no third family)
- `./init.sh` → the unchanged **5-error baseline**
- **Composes with the claims batch:** both applied together → 309 passed, all six
  invariants green, `init.sh` at baseline

## Apply

```bash
cd template
git apply docs/superpowers/patches/2026-09-01-runtime-claims-batch.patch
git apply docs/superpowers/patches/2026-09-01-protect-runtime-modules.patch
./init.sh && python3 -m pytest tests -q
```
