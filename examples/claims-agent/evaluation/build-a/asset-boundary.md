# Build A Asset Boundary

**Evidence scope:** task 1.2 boundary record only. **Captured:** 2026-08-03T01:22:43Z. This record does not approve Build A, implement Claims behavior, or claim production/security enforcement.

## Template lineage

- Source repository: `https://github.com/YuanSingapore/harness-engineering-platform.git`
- Source path: `template/`
- Repository HEAD and latest template commit: `82a9db85cc07db2405873be33137f5b77593e338` (`2026-07-31T09:06:47+08:00`, `add security steering file + Security Module section in README`).
- Destination: `examples/claims-agent/`; this is an isolated copy, not a symlink or snapshot.
- Source-worktree caveat: `template/README.md` is modified and `template/.kiro/steering/security-review.md` plus `template/security/` are untracked at capture time. The mechanism/test source paths in the integrity manifest have no source-side Git status entries; hashes below compare the captured source worktree bytes with Build A bytes.

## Included copied core assets

- Root/session foundation: `AGENTS.md`, `CLAUDE.md`, `README.md`, `feature_list.json`, `progress.md`, and `init.sh`.
- Context: `context/README.md` and `context/BEST-PRACTICES.md`.
- Generic workflows: `.claude/settings.json`, both files under `.claude/commands/`, both non-security files under `.kiro/steering/`, and all four JSON files under `.kiro/hooks/`.
- Core mechanisms and documentation: all five files under `demo/`; `governance/{ARCHITECTURE.md,deny-list.json,permission.py}`; `observability/{ARCHITECTURE.md,audit.py}`; and `tools/{ARCHITECTURE.md,mcp-allowlist.json}`.
- Retained core verification: `tests/{ARCHITECTURE.md,fixtures.json,test_e2e.py,test_fixtures.py}`.
- Empty local output boundary: `sandbox/` exists only as an ignored runtime location.
- Filled-copy distinction: `AGENTS.md`, `CLAUDE.md`, `feature_list.json`, `progress.md`, `governance/deny-list.json`, and `tools/mcp-allowlist.json` currently differ from template bytes and belong to project fill/configuration review, not the unchanged-core integrity claim.

## Claims-owned paths

- `claims/`, `claims/fixtures/`, and `claims/tests/` contain only `.gitkeep` placeholders at capture time; there is no Claims implementation or executable fixture.
- `context/claims-architecture.md` is Claims-specific context.
- `evaluation/build-a/` is Build A review/evidence space; this file is its boundary record.
- `.gitignore` is project-owned residue policy.

## Explicit Security Kit exclusions

Build A excludes `security/`, `context/SECURITY.md`, `.kiro/steering/security.md`, and `.kiro/steering/security-review.md`. All four paths were confirmed absent. These are Build B-only review-layer assets; their absence does not remove retained core governance, policy, tests, session workflow, or generic hooks.

## Generated-residue exclusions

The project ignore rules exclude `__pycache__/`, `*.py[cod]`, `.pytest_cache/`, `*.log` (including `observability/audit.log`), `sandbox/` outputs, and `.DS_Store`. They are never copied core assets, baseline evidence, or snapshot inputs. A point-in-time scan found ignored generated directories `.pytest_cache/`, `demo/__pycache__/`, `tests/__pycache__/`, `observability/__pycache__/`, and `governance/__pycache__/`; these are local verification residue, remain excluded by policy, and must not be committed. `git check-ignore -v` confirmed representative cache, log, sandbox-output, and `.DS_Store` paths resolve to this project `.gitignore`.
## Integrity manifest

SHA-256 group digests use sorted members and hash each `path + NUL + bytes + NUL`. Equal source/Build A digests prove byte identity only at capture time.

| Integrity set (members) | Build A SHA-256 | Template SHA-256 | Result |
|---|---|---|---|
| Demo core (`demo/__init__.py`, `demo/demo.py`, `demo/fake_model.py`, `demo/harness.py`) | `0eee24a2d89f541fae5f6ff817c742a883bc33f602651013544e6163b0f74e97` | same | unchanged |
| Core tests (`tests/fixtures.json`, `tests/test_e2e.py`, `tests/test_fixtures.py`) | `4b7a208136502a84b266ec1d6f4a7e0e6819a55555d1aba78afcbccb8d08bc50` | same | unchanged |
| Generic Kiro hooks (all four `.kiro/hooks/*.json`) | `f3121f5d5e050e2441074cccaf85125638d051268885f4d4b992a985e8b3c44e` | same | unchanged |
| Session workflows (two Claude commands and two non-security Kiro steering files) | `3403483ca0643b484380f0caf8cec18c17e93718e1af2ce050050d964855373b` | same | unchanged |
| `init.sh` | `5743d0e86ab16af3c687881aa185fd30eb61b3cad695ece9b4e8fee9a8852db1` | same | unchanged |
| `observability/audit.py` | `939455ffa020540c90858b03559cccd3de19f9322891e9209c8cbc9abdbc6f25` | same | unchanged |
| `.claude/settings.json` | `7950ce2d17f1b189c7149bbafeaef66b51301f62dc8ca2f99bdbec4b4721dd56` | same | unchanged |
| `governance/permission.py` | `c74844926776d3a7f3a75882439f5c30c11d86f10e78f212c56d27191722e555` | `f4d107ffabd23f721b32d1a5deee50c365ab3d86dce03e055ef1d3e836b0159d` | **drift detected** |

`governance/permission.py` adds CLI fail-closed payload handling and Claude tool-name normalization in Build A. This record does not authorize, revert, or characterize that change as an unchanged template mechanism. Until reviewed separately, the full “all reusable mechanisms unchanged” claim must be withheld. The core-test integrity claim remains supported by the independent matching test digest.

## Review use

Later readiness and snapshot reviews should re-compute these hashes, confirm the four Security Kit paths remain absent, treat all ignored residue as out of baseline, and route any generic-mechanism difference to human review rather than silently accepting or overwriting it. Requirements traced: 1.1, 1.2, 2.2, and 5.2.