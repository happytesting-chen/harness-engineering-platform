# Build A Evidence Index

**Scope:** attributable, non-sensitive task 2.3 readiness evidence. No Build A functional evidence or human approval is recorded.

| ID | Evidence / command | Result | Supports |
|---|---|---|---|
| E-BA-001 | `./init.sh` required-file placeholder stage | PASS: 4/4 required files had no placeholders. | Required configuration fill. |
| E-BA-002 | Full-tree `{{...}}` Python regex scan excluding generated caches | FAIL: 18 hits; 16 unresolved project-facing occurrences and 2 explanatory literals. | Placeholder blocker G-BA-001. |
| E-BA-003 | Policy JSON assertions plus direct permission/CLI cases | Static checks 12/12 pass; CLI cases 4/4 pass. | Bounded policy and CLI observations. |
| E-BA-004 | JSON inspection and Kiro governance-hook payload check | FAIL: hook sends empty `tool_input`; attempted command absent. | Hook blocker G-BA-002. |
| E-BA-005 | Residue scan, cleanup, final scan, and `git check-ignore -v` representatives | 12 ignored entries observed after tests; cleanup completed; final residue count **0**. | Residue exclusion and clean handoff. |
| E-BA-006 | `python3 -m pytest tests -v`; `./init.sh` | 4 passed in 0.04s; init exited 0 with 7/7 fixtures, 3/3 E2E, 5/5 fresh-session, 1 warning. | Retained-core verification. |
| E-BA-007 | Sorted-member SHA-256 comparison and exact permission diff | All recorded groups match except `governance/permission.py`; hashes match `asset-boundary.md`. | Boundary integrity and blocker G-BA-004. |
| E-BA-008 | Claims/Security Kit path scan | 0 Claims non-placeholder files; 0/4 excluded Security Kit paths present. | Pre-implementation and Build A boundary. |
| E-BA-009 | `git status`, path history, repository exact-string search | Build permission file is untracked; only template path has history; added fail-closed string exists only in Build A. | Drift provenance limit. |

## Evidence limits

- Capture window: 2026-08-03T01:44:43Z; repository HEAD `97e349aa1bd61266227ac9e92e3da077bd9268a4`.
- Policy checks cover named literal examples; they do not prove all syntactic network/LLM/external-action variants are mechanically prevented.
- Kiro hook execution-path enforcement is specifically withheld because the attempted command is not forwarded.
- Generated output, environment dumps, secrets, and fixture payloads are not retained here.
