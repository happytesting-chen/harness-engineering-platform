# Progress

## Current State

- **Last updated:** 2026-08-18
- **Active phase:** phase-01 — Project setup and runtime-security wiring
- **Session number:** 1

## Done

- [x] Instantiated the full runtime-enabled template under `examples/ai-news/`.
- [x] Filled project context: AI stack, deployment, and target scope.
- [x] Configured project tool/egress policy in `governance/mcp-allowlist.json`.
- [x] Filled `CLAUDE.md`, `AGENTS.md`, and the six-phase `feature_list.json`.
- [x] Added generic runtime `scan_tool_input()` API to `Security-kit/secret_scan.py` and carried it into this example.
- [x] Added `src/security.py` as the application adapter into the reusable runtime harness.
- [x] Added no-network runtime security contract tests covering allow, egress deny, unallowlisted tool deny, secret block, content-trust block, and unregistered tool deny.

## In Progress

- **Current task:** verify Phase 01 runtime-security wiring and contract tests before implementing real news tools.
- **Blockers:** tests have not yet been executed in a local Python environment from this GitHub-only development session.
- **Attempts:** an earlier app-specific prototype was incorrectly placed under `template/demo`; it was removed and the application was re-instantiated correctly under `examples/ai-news/`.

## Next Steps

1. Run the Phase 01 verification command from the `examples/ai-news/` project root.
2. Fix only issues exposed by verification; do not mark phase passing until tests exit 0 and human sign-off is given.
3. After sign-off, start phase-02 and implement `src/tools/news.py`, `src/tools/github_trending.py`, and `src/tools/digest.py` through `RuntimeSecurity`.

## Decisions Made

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-08-18 | Keep the generic template stable during app development. | Application-specific work belongs under the instantiated example; template changes are only for genuine reusable runtime gaps. |
| 2026-08-18 | Use Strands + Claude + Streamlit for v1. | Clean tool lifecycle and simple local demonstration UI. |
| 2026-08-18 | Runtime security authority stays outside model reasoning. | Tool/egress/secret/content decisions must be mechanically enforced on the real runtime path. |
| 2026-08-18 | Expose `scan_tool_input()` in `secret_scan.py`. | The existing secret detector was CLI-hook oriented and lacked a public runtime API. |

## Notes for Next Session

- Phase 01 verification command is defined in `Harness-Best-Practice/feature_list.json`.
- No Anthropic API key is required for the current contract tests.
- Do not start real network/news implementation until Phase 01 is verified and signed off.

---

## Session Handoff (fill only when ending mid-task)

**Current objective:** Verify Phase 01 runtime-security adapter and tests.

**Files changed:** `Security-kit/secret_scan.py`, `src/security.py`, `src/__init__.py`, `tests/test_runtime_security.py`, `Harness-Best-Practice/feature_list.json`, and this progress file.

**Resume steps:**
1. Read this section.
2. Run `./init.sh` from `examples/ai-news/`.
3. Run the Phase 01 verification command.
4. Fix failures if any, then request human sign-off before phase transition.
