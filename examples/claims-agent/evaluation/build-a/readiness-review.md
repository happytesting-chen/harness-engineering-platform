# Build A Filled-Harness Readiness Review

**Status:** **BLOCKED**  
**Review scope:** task 2.3 pre-implementation checks only  
**Evidence capture:** 2026-08-03T01:44:43Z at repository `97e349aa1bd61266227ac9e92e3da077bd9268a4`  
**Human approval:** **Not requested and not recorded.** Build A implementation remains prohibited.

## Decision

The filled harness is not ready for the mandatory human checkpoint. Claims implementation and Build B-only assets are absent, the configured policy and retained core tests pass their targeted checks, and generated residue is clean; however, blocking placeholder, hook, and generic-mechanism-integrity gaps remain. Passing `init.sh` does not override these findings or the human gate.

## Check results

| Check | Result | Exact finding | Evidence |
|---|---|---|---|
| Required-file placeholders | PASS | `init.sh` found no placeholders in `CLAUDE.md`, `feature_list.json`, `governance/deny-list.json`, or `tools/mcp-allowlist.json`. | E-BA-001 |
| Full filled-copy placeholder scan | **BLOCK** | 18 regex matches: 2 explanatory literals and **16 unresolved project-facing occurrences**—6 in copied `README.md`, 5 in `.kiro/steering/domain-workflow.md`, and 5 in `.claude/commands/domain-workflow.md`. | E-BA-002, G-BA-001 |
| Policy configuration | PASS (bounded) | Required deny categories are present; tools are exactly `bash` and `write_file`; egress hosts are empty; one phase is active; representative network, LLM, credential, cloud, email, external-action, unknown-tool, and egress checks denied. This proves only tested literal cases. | E-BA-003 |
| Permission CLI behavior | PASS, but drifted | Harmless `Bash` payload exited 0; `curl`, empty stdin, and malformed JSON exited 2. These results depend on the unapproved Build A mechanism difference analyzed below. | E-BA-003, E-BA-007 |
| Hook/configuration validity | **BLOCK** | Hook/config JSON parses, but `.kiro/hooks/governance-check.json` constructs `"tool_input": {}`. It does not forward the attempted shell command, so deny-list and egress checks cannot evaluate that command. Hooks are not claimed as mechanical prevention. | E-BA-004, G-BA-002 |
| Ignore rules | PASS | Representative Python cache, pytest cache, audit log, sandbox output, and `.DS_Store` paths resolve to project `.gitignore`. | E-BA-005 |
| Generated residue | PASS after cleanup | Post-test scan found 12 ignored entries; cleanup removed the pytest cache and four Python cache trees. Final recheck found **0** residue entries. | E-BA-005 |
| Retained core tests | PASS | `python3 -m pytest tests -v`: **4 passed, 0 failed, 0 skipped** in 0.04s. `./init.sh` exited 0 with 7/7 fixture cases, 3/3 E2E cases, and 5/5 fresh-session questions; it reported one progress-staleness warning. | E-BA-006 |
| Retained core integrity | PASS except permission mechanism | Demo core, core tests, generic hooks, session workflows, `init.sh`, `observability/audit.py`, and `.claude/settings.json` match template digests. | E-BA-007, `asset-boundary.md` |
| Claims absence | PASS | `claims/` contains only three `.gitkeep` files; 0 implementation, test, or executable fixture files. | E-BA-008 |
| Security Kit absence | PASS | 0 of `security/`, `context/SECURITY.md`, `.kiro/steering/security.md`, `.kiro/steering/security-review.md` exist. | E-BA-008 |

## `governance/permission.py` drift reconciliation

Template SHA-256 is `f4d107ffabd23f721b32d1a5deee50c365ab3d86dce03e055ef1d3e836b0159d`; Build A SHA-256 is `c74844926776d3a7f3a75882439f5c30c11d86f10e78f212c56d27191722e555`. The exact difference is confined to CLI-hook handling: Build A adds 39 net lines that (1) map Claude names `Bash`, `Write`, `Edit`, `MultiEdit`, and `NotebookEdit` to internal allowlist names; (2) force empty, malformed, and non-object payloads to exit 2; (3) coerce non-object `tool_input` to `{}`; and (4) centralize denials through `_block()`.
Repository evidence identifies the baseline precisely but not an author/source for the divergent bytes: HEAD and the current template contain the `f4d...` implementation; Git history shows only the tracked template introduction commit `4fe65062f13fb4e12ae477d1b2c5d0918ca0f3fb`; the Build A file is untracked; and repository search finds the added fail-closed text only in this Build A copy. Therefore the historical provenance of the added code is **unknown from repository evidence**. It is not a later tracked template update.

The functional motivation is observable but does not authorize the change. The template CLI exits 0 on empty input, may exit 1 on malformed JSON, and does not normalize Claude PascalCase names; Build A changes those behaviors. That may repair Claude-hook behavior, but it is still a project-copy modification to a file that declares “Do NOT modify this file per project.” It therefore violates Requirement 1.2’s preserve-generic-mechanisms condition until a human resolves it through an attributable generic-template decision or exact restoration. Task 2.3 neither accepts nor overwrites the difference and made **no change** to either permission file. See G-BA-004.

The drift also does not repair the Kiro integration gap: the Kiro hook supplies no attempted command to either implementation.

## Blocking gaps

1. **G-BA-004 — Generic mechanism preservation:** unapproved and unattributed `permission.py` divergence.
2. **G-BA-002 — Hook execution payload:** Kiro governance hook cannot inspect the attempted shell command.
3. **G-BA-001 — Project-facing placeholders:** 16 unresolved occurrences remain.
Generated residue gap G-BA-003 is closed: final count is 0. G-BA-005 is addressed by the updated handoff and must be reconfirmed on the next required startup run.

Resolution and acceptance evidence are defined in `worked-gaps-backlog.md`. Until the three substantive blocking gaps above are resolved and task 2.3 is repeated, readiness remains **BLOCKED**, not “READY FOR HUMAN REVIEW.”

## Packet links

- Boundary and lineage: [`asset-boundary.md`](asset-boundary.md)
- Evidence: [`evidence-index.md`](evidence-index.md)
- Readiness gaps: [`worked-gaps-backlog.md`](worked-gaps-backlog.md)
- Future evaluation dimensions: [`scorecard.md`](scorecard.md)
- Snapshot prohibition: [`snapshot-decision.md`](snapshot-decision.md)

Requirements traced: 2.2, 3.1, 3.2, and 4.3.