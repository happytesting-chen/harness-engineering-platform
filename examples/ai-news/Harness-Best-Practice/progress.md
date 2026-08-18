# Progress

## Current State

- **Last updated:** 2026-08-18
- **Active phase:** phase-03 — Strands Claude agent integration
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
- [x] Added Anthropic model construction using local `ANTHROPIC_API_KEY` and default `claude-sonnet-4-6` model ID.
- [x] Added `tests/test_agent_integration.py` to verify secured registration, wrapper routing, no directory auto-loading, and fail-closed missing API key behavior.
- [x] Pinned Strands/Anthropic and Streamlit runtime dependencies in `requirements.txt`.

## In Progress

- **Current task:** locally verify Phase 03 Strands integration and no-bypass registration.
- **Blockers:** Phase 03 tests require `strands-agents[anthropic]` to be installed locally; no API call is required for the tests themselves.
- **Attempts:** Phase 03 tests initially allowed a skip when Strands was absent; corrected so missing Strands now fails verification rather than producing a misleading pass.

## Next Steps

1. Pull the latest `runtime-permission-minimal` branch.
2. From `examples/ai-news/`, install `requirements.txt` in a virtual environment if needed.
3. Run `python3 -m pytest -q tests/test_runtime_security.py tests/test_news_tools.py tests/test_agent_integration.py`.
4. Fix only issues exposed by verification.
5. After exit 0 and human sign-off, mark phase-03 passing and activate phase-04 Streamlit UI implementation.

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
| 2026-08-18 | Pin `strands-agents[anthropic]==1.48.0`. | Reproducible Phase 03 integration against the current documented Strands API used by this example. |

## Notes for Next Session

- Phase 03 verification command is defined in `Harness-Best-Practice/feature_list.json`.
- No real Anthropic API key is needed for the current integration tests; `ANTHROPIC_API_KEY` is only needed for the later live agent run.
- Strands also supports direct method-style tool invocation; because the toolkit contains only secured wrappers, that path still enters `RuntimeSecurity`.

---

## Session Handoff

**Current objective:** Verify Phase 03 Strands/Claude integration and prove only secured wrappers are agent-callable.

**Files changed:** `src/agent.py`, `tests/test_agent_integration.py`, `requirements.txt`, `Harness-Best-Practice/feature_list.json`, and this progress file.

**Resume steps:**
1. Pull the latest branch.
2. Install requirements if necessary.
3. Run the Phase 03 verification command.
4. Fix failures if any.
5. Request human sign-off before phase transition.
