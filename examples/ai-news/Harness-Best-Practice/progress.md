# Progress

## Current State

- **Last updated:** 2026-08-18
- **Active phase:** phase-02 — News retrieval tools
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

## In Progress

- **Current task:** verify Phase 02 real tool handlers through the runtime security boundary.
- **Blockers:** Phase 02 tests have not yet been run locally after the new tool implementation.
- **Attempts:** a hard-coded GitHub API endpoint was initially placed inside the raw handler; corrected before verification because the runtime egress gate could not inspect a destination absent from tool input.

## Next Steps

1. Run `python3 -m pytest -q tests/test_runtime_security.py tests/test_news_tools.py` from the `examples/ai-news/` project root.
2. Fix only issues exposed by verification.
3. After exit 0 and human sign-off, mark phase-02 passing and activate phase-03.
4. Phase 03 will add Strands/Claude agent-facing tool wrappers that call only `RuntimeSecurity.execute()`; raw handlers must not be registered directly with the agent.

## Decisions Made

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-08-18 | Keep the generic template stable during app development. | Application-specific work belongs under the instantiated example; template changes are only for genuine reusable runtime gaps. |
| 2026-08-18 | Use Strands + Claude + Streamlit for v1. | Clean tool lifecycle and simple local demonstration UI. |
| 2026-08-18 | Runtime security authority stays outside model reasoning. | Tool/egress/secret/content decisions must be mechanically enforced on the real runtime path. |
| 2026-08-18 | Use a dedicated runtime secret scanner under `src/`. | Keeps deployed runtime behavior separate from Claude Code build-time hook mechanics. |
| 2026-08-18 | Do not automatically follow HTTP redirects in the raw news fetcher. | Prevents redirect-based egress bypass; any redirected URL must re-enter the secured runtime path. |
| 2026-08-18 | Expose fixed network destinations as tool inputs where permission.py must enforce them. | Egress enforcement can only mechanically validate destinations visible before the handler executes. |

## Notes for Next Session

- Phase 02 verification command is defined in `Harness-Best-Practice/feature_list.json`.
- No Anthropic API key is required for Phase 02 tests because network behavior is mocked.
- `get_trending_repos` is a proxy for fast-rising interest: recently created repositories sorted by stars, not an exact historical star-velocity measurement.

---

## Session Handoff

**Current objective:** Verify Phase 02 real news/GitHub/digest handlers behind RuntimeSecurity.

**Files changed:** `src/tools/__init__.py`, `src/tools/news.py`, `src/tools/github_trending.py`, `src/tools/digest.py`, `tests/test_news_tools.py`, `.gitignore`, `Harness-Best-Practice/feature_list.json`, and this progress file.

**Resume steps:**
1. Read this section.
2. Run the Phase 02 verification command.
3. Fix failures if any.
4. Request human sign-off before phase transition.
