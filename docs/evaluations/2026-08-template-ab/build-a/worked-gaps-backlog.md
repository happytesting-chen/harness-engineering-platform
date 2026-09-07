# Build A Worked / Gaps Backlog

**State:** readiness backlog initialized; no generic mechanism change is authorized here.

## Worked

| ID | Observation | Evidence |
|---|---|---|
| W-BA-001 | Retained core verification passes without changing core tests. | E-BA-006 |
| W-BA-002 | Build A policy is least-privilege on its face and representative CLI denials fail closed. | E-BA-003 |
| W-BA-003 | Claims behavior and all four Build B-only Security Kit assets remain absent. | E-BA-008 |
| W-BA-004 | Integrity digests remain equal for all recorded groups except the disclosed permission mechanism. | E-BA-007 |

## Blocking gaps and prioritized improvements

| Priority / ID | Gap / what did not work | Required improvement (human-reviewed) | Acceptance evidence / retest |
|---|---|---|---|
| P0 / G-BA-004 | `governance/permission.py` differs from the template generic mechanism; historical provenance is not attributable from Git. | Human chooses either restore exact template bytes in Build A, or separately review/promote a generic template change with tests and then recopy. Do not silently accept/revert it. | Equal approved mechanism hashes, or a recorded generic-change decision plus new lineage/integrity evidence and passing core/hook tests. |
| P0 / G-BA-002 | Kiro governance hook passes `{}` instead of the attempted command, so command policy cannot inspect shell content. | Review the generic hook integration outside this task; preserve Build A mechanism until authorized. | Target-runtime execution test proves a prohibited attempted command reaches the gate and is blocked, while an allowed command passes. |
| P1 / G-BA-001 | 16 unresolved project-facing placeholder occurrences remain in README and two domain workflows; README also presents template/Security Kit language that can misstate Build A. | Fill or explicitly remove/non-include project-facing placeholder surfaces without adding Claims behavior or Build B assets. | Full project-facing placeholder scan has zero unresolved occurrences and review confirms Build A boundary text. |
| Closed / G-BA-003 | Test execution generated ignored caches/bytecode. | Removed generated residue after tests. | Final scan: zero `.pytest_cache`, `__pycache__`, `.pyc/.pyo`, `.log`, sandbox outputs, and `.DS_Store` beneath Build A. |
| P2 / G-BA-005 | `init.sh` warned that `progress.md` was older than recent changes. | Update handoff state after packet completion. | Handoff file is newer than reviewed packet files; confirm warning-free on the next required startup run. |

## Retest condition

Repeat all task 2.3 checks after blockers are resolved. Readiness may become **READY FOR HUMAN REVIEW** only when no blocking gap remains; that state still is not human approval.
