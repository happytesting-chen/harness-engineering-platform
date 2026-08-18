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

## In Progress

- **Current task:** verify the normal terminal application (`src/run_news.py`) generates and saves a daily digest through the secured runtime path.
- **Blockers:** requires local `ANTHROPIC_API_KEY` and working TLS trust configuration for Anthropic/GitHub.

## Next Steps

1. Pull the latest `runtime-permission-minimal` branch.
2. Run the full deterministic regression suite with `python3 -m pytest -q`.
3. Run `python3 src/run_news.py` and verify the normal digest is generated through approved sources/tools.
4. Fix only issues exposed by the normal application run.
5. Add the Streamlit `src/app.py` portal using the same `build_agent()` path; do not create a second security path.
6. After the basic portal works, add live tool-permission, secret, and untrusted-content demonstrations under `tests/live/`.

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

## Notes for Next Session

- Phase 03 is complete and human-approved.
- `tests/live/test_allowed_egress.py` and `tests/live/test_blocked_egress.py` are the live egress demonstrations.
- `src/run_news.py` is normal application behavior and contains no security-test scenario.
- The Streamlit app must reuse `src.agent.build_agent()` rather than registering raw tools independently.

---

## Session Handoff

**Current objective:** Verify `src/run_news.py`, then build the Streamlit portal on the same secured runtime path.

**Resume steps:**
1. Pull the latest branch.
2. Run `python3 -m pytest -q`.
3. Run `python3 src/run_news.py`.
4. Inspect digest output and runtime audit events.
5. Build `src/app.py` only after the terminal path is stable.
