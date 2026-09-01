# Deferred: protect the runtime-mvp modules (acceptance condition 19)

**Status:** not in the claims batch. Split out 2026-09-01 after it broke the shell census.

## Why it was split out

Acceptance condition 19 says every new enforcement module joins
`BUILTIN_PROTECTED_PATHS`. Adding the 15 runtime-mvp modules + the classifier lock does
give them **structured** (Gate 1a, file-identity) write protection — the primary control.
But it also perturbs the **shell-coverage census** that `test_protected_paths.py`,
`control-matrix.md` (SEC-SELF-001), `mechanisms.json` and `SECURITY.md` S2.4 all pin and
document together:

- protected paths 12 → 27, census cells 168 → 378, open cells 78 → **243**
- documented closed ratio 54% → **36%**
- and the shell deny-list never *names* the runtime paths, so they are open for **every**
  shell verb — which breaks `test_the_open_set_has_exactly_two_shapes` (the gap gains a
  third family) and `test_shell_patterns_block_the_common_forms_they_claim`.

That is a real security-design decision, not a mechanical bump, so it does not belong
bundled under the claims register batch.

## The decision to make

**Option A — structured-only (smaller).** Accept that the runtime modules have Gate 1a
structured protection but no shell-deny coverage. Add all 15 + the lock to
`UNCOVERED_PATHS` in `test_protected_paths.py` (they behave exactly like the two audit
paths: open for every verb), update the census to 243/378 and the "two shapes" model to
"5 uncovered verbs + 17 uncovered paths", and update the three docs. Honest, but the
headline closed ratio drops to 36%.

**Option B — full parity (larger, better).** Extend `governance/deny-list.json` (a
protected path) with shell-write patterns naming `Security-kit/runtime/`, so the runtime
modules get the same shell coverage the governance modules have. Keeps the two-family
shape and a healthy ratio. Requires a deny-list patch + re-measuring the census.

Recommendation: **Option B** — the runtime dispatcher and screens are as security-critical
as the governance gate they compose around; giving them weaker shell coverage than
`permission.py` is an inconsistency a reviewer will rightly question. B is more work but
it is the coverage the files deserve.

Either option is a human-applied patch (both `permission.py` and `deny-list.json` are
protected paths). Until then, the runtime modules are protected against the agent's own
Edit/Write tool calls by being un-listed... no — **they are currently NOT in
`BUILTIN_PROTECTED_PATHS` at all**, so an agent's Edit to `Security-kit/runtime/host.py`
is presently ALLOWED. That is the open risk this follow-up closes; `SEC-RUNTIME-GAP-001`
already tracks the routing gap, and this is the self-protection gap beside it.
