# Progress

## Current State

- **Last updated:** 2026-08-18
- **Active phase:** phase-04 — Application runners and Streamlit portal
- **Session number:** 1

## Done

- [x] Instantiated the full runtime-enabled template under `examples/ai-news/`.
- [x] Filled project context: AI stack, deployment, and target scope.
- [x] Configured project tool/egress policy in `governance/mcp-allowlist.json`.
- [x] Filled `CLAUDE.md`, `AGENTS.md`, and the six-phase `feature_list.json`.
- [x] Added `src/security.py` as the application adapter into the reusable runtime harness.
- [x] Separated runtime secret scanning into `src/runtime_secret_scan.py`; restored `Security-kit/secret_scan.py` to its build-time hook role.
- [x] Added no-network runtime security contract tests covering allow, egress deny, unallowlisted tool deny, secret block, content-trust block, and unregistered tool deny.
- [x] Phase 01 locally verified and human-approved: `12 passed in 0.44s`.
- [x] Added raw application handlers under `src/tools/`: `fetch_news`, `get_trending_repos`, and `save_digest`.
- [x] Disabled automatic HTTP redirects in `fetch_news` so an approved URL cannot silently redirect to an unchecked destination.
- [x] Made the GitHub API endpoint an explicit `get_trending_repos` tool argument so `permission.py` can check egress before execution.
- [x] Added Phase 02 mocked-network tests in `tests/test_news_tools.py`.
- [x] Phase 02 locally verified and human-approved: `11 passed in 0.57s`.
- [x] Added Strands-facing secured wrappers in `src/agent.py`; raw handlers are not registered with Strands.
- [x] Disabled Strands directory auto-loading with `load_tools_from_directory=False`.
- [x] Added Anthropic model construction using local `ANTHROPIC_API_KEY` and configurable `CLAUDE_MODEL`.
- [x] Added `tests/test_agent_integration.py` to verify secured registration, wrapper routing, no directory auto-loading, and fail-closed missing API key behavior.
- [x] Phase 03 deterministic integration verification passed locally: `16 passed in 27.87s`.
- [x] Live allowed egress verification passed: Claude/Strands called `get_trending_repos`, `api.github.com` was ALLOWED, and the audit event was recorded.
- [x] Live blocked egress verification passed: Claude/Strands called `fetch_news` for legitimate `arstechnica.com`; runtime default-deny egress produced a DENIED audit event before network execution.
- [x] Reorganized all live security tests under `tests/live/`; normal application code remains under `src/`.
- [x] Added positive ALLOWED audit reasons in the runtime dispatcher.
- [x] Added `src/run_news.py` as the normal terminal AI News application runner.
- [x] Normal terminal application verified: Claude used `get_trending_repos`, two `fetch_news` calls, and `save_digest`, producing and saving an 8-story digest.
- [x] Added and locally exercised live scenarios for blocked tool permission, blocked fake secret, and untrusted instruction-shaped content under `tests/live/`.
- [x] Improved model-facing blocked-tool results so Claude receives the authoritative runtime `security_control` and `reason` rather than inferring the cause.
- [x] Added human-readable content-trust `detected_patterns` for audit/demo display.
- [x] Full deterministic regression verification passed locally after runtime changes: `82 passed in 82.89s`.
- [x] Re-ran `src/run_news.py` after regression verification and confirmed normal digest generation/save still succeeds.
- [x] Added `src/app.py` Streamlit portal using the same `build_agent()` secured runtime path as the terminal application.

## In Progress

- **Current task:** locally verify the first Streamlit portal and refine presentation only if needed.
- **Blockers:** Streamlit runtime requires local `ANTHROPIC_API_KEY` and the existing TLS/CA environment used by the terminal application.

## Next Steps

1. Pull the latest `runtime-permission-minimal` branch.
2. Start the portal with `streamlit run src/app.py`.
3. Verify the saved digest renders, **Generate Latest Digest** uses the real secured agent path, and chat questions use the same agent.
4. Verify the Runtime Protection panel shows recent ALLOWED/DENIED/BLOCKED/SUSPICIOUS audit events, reasons, and detected content patterns where present.
5. Fix only issues exposed by the local portal run.
6. After portal verification and human sign-off, complete phase-04 and move to formal E01-E06 runtime-enforcement/evaluation work.

## Decisions Made

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-08-18 | Keep the generic template stable during app development. | Application-specific work belongs under the instantiated example; template changes are only for genuine reusable runtime gaps. |
| 2026-08-18 | Use Strands + Claude + Streamlit for v1. | Clean tool lifecycle and simple local demonstration UI. |
| 2026-08-18 | Runtime security authority stays outside model reasoning. | Tool/egress/secret/content decisions must be mechanically enforced on the real runtime path. |
| 2026-08-18 | Use a dedicated runtime secret scanner under `src/`. | Keeps deployed runtime behavior separate from Claude Code build-time hook mechanics. |
| 2026-08-18 | Do not automatically follow HTTP redirects in the raw news fetcher. | Prevents redirect-based egress bypass; any redirected URL must re-enter the secured runtime path. |
| 2026-08-18 | Expose fixed network destinations as tool inputs where permission.py must enforce them. | Egress enforcement can only mechanically validate destinations visible before the handler executes. |
| 2026-08-18 | Register only secured wrapper tools with Strands and disable directory auto-loading. | Prevents the agent from gaining a direct raw-handler path that bypasses `RuntimeSecurity`. |
| 2026-08-18 | Keep normal app code in `src/` and all security tests in `tests/`. | Keeps application behavior and validation/demo scenarios clearly separated. |
| 2026-08-18 | Use a legitimate non-allowlisted news source for blocked-egress testing. | Demonstrates authorization policy rather than malicious-site classification. |
| 2026-08-18 | Use synthetic credentials and a local malicious-content fixture for live tests. | Provides safe, reproducible evidence without exposing real secrets or relying on attacker-controlled external infrastructure. |
| 2026-08-18 | Streamlit is a presentation layer, not a new runtime-security implementation. | Terminal and browser applications must share the same `build_agent()` and `RuntimeSecurity` enforcement path. |

## Notes for Next Session

- Phase 03 is complete and human-approved.
- All current live runtime-control scenarios have been exercised locally.
- Full regression result after recent changes: `82 passed in 82.89s`.
- `src/run_news.py` is the verified normal terminal application.
- `src/app.py` is the first Streamlit portal and must be locally verified next.

---

## Session Handoff

**Current objective:** Verify `src/app.py` locally and make only presentation/usability fixes required by the real portal run.

**Resume steps:**
1. Pull the latest branch.
2. Run `streamlit run src/app.py`.
3. Generate a digest and ask one normal news question.
4. Inspect the Runtime Protection panel and raw audit trail.
5. Report any UI/runtime issue before phase transition.
