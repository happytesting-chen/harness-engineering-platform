# Implementation Plan: Harness Engineering Platform

## Overview

Build the reusable, zero-dependency harness engineering platform as a `template/` directory with mechanism code (permission gate, audit, agent loop), policy placeholders, hook configuration, test infrastructure, and a complete Red Team example. The primary enforcement path is `.claude/settings.json` hooks → `governance/permission.py` (CLI mode). The demo/harness.py is optional evaluation infrastructure.

## Tasks

- [x] 1. Create template directory structure and core data models
  - [x] 1.1 Create the template directory layout with all required subdirectories and placeholder files
    - Create `template/` with subdirectories: `governance/`, `tools/`, `observability/`, `context/`, `tests/`, `demo/`, `.claude/commands/`, `.kiro/steering/`
    - Create empty placeholder files to establish the directory tree
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_

  - [x] 1.2 Implement core data model classes (`Block` and `Response`)
    - Create `template/demo/fake_model.py` with `Block` and `Response` dataclasses
    - `Block` has: type, name, input, text, id fields
    - `Response` has: content (list[Block]), stop_reason
    - Implement `FakeModel` class with scripted responses for the demo sequence
    - _Requirements: 1.2, 8.6_

  - [x] 1.3 Create policy JSON files with placeholder/template content
    - Create `template/feature_list.json` with `{{PHASE_N_NAME}}` placeholders and valid schema structure
    - Create `template/governance/deny-list.json` with `{"patterns": ["{{DENY_PATTERN_1}}"]}` placeholder
    - Create `template/tools/mcp-allowlist.json` with placeholder tools array and egress_hosts, including version field per tool
    - _Requirements: 7.1, 7.2, 4.4, 13.1, 13.2_

- [x] 2. Implement Permission Gate (`governance/permission.py`)
  - [x] 2.1 Implement `check_deny_list(command)` function
    - Read `governance/deny-list.json`, extract patterns array
    - Return non-None reason if any pattern is a substring of command
    - Return None if no match or file missing/empty
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x] 2.2 Implement `check_phase_gate(tool_name)` function
    - Read `tools/mcp-allowlist.json` and `feature_list.json`
    - Deny if tool not in allowlist (Requirement 4.3)
    - Deny if no phase is active (Requirement 4.5)
    - Deny if tool has `gated_until` and referenced phase is not "passing" (Requirement 4.1)
    - Allow if tool in allowlist with no `gated_until` and a phase is active (Requirement 4.2)
    - _Requirements: 4.1, 4.2, 4.3, 4.5, 4.6_

  - [x] 2.3 Implement `check_egress(command)` function
    - Detect network-initiating tokens: curl, wget, nc, ssh, nmap
    - Extract target host from command
    - Check host against `egress_hosts` in `mcp-allowlist.json`
    - Return None (pass) if no network token present
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [x] 2.4 Implement `make_permission_check()` composing all three gates in order
    - Evaluate gates in fixed order: deny-list → phase-gate → egress
    - Fail closed: first denial terminates evaluation
    - Return `(bool, str)` tuple — False with reason on denial, True with empty string on allow
    - _Requirements: 2.1, 2.2, 2.4_

  - [x] 2.5 Implement CLI mode (`if __name__ == "__main__"`) for hook integration
    - Read JSON from stdin (tool_name, tool_input fields)
    - Run through `make_permission_check()`
    - Exit 0 for allow, exit 2 for block (print denial reason to stdout)
    - _Requirements: 2.3, 2.5, 16.2_

  - [ ]* 2.6 Write property tests for Permission Gate (Properties 1-7)
    - **Property 1: Gate order + fail-closed** — verify gates evaluate in order and first denial wins
    - **Property 2: Deny-list substring match** — verify pattern matching correctness
    - **Property 3: Phase-gated tool access** — verify gated_until enforcement
    - **Property 4: Ungated allowlisted tools permitted** — verify ungated tools pass
    - **Property 5: Unknown tools denied** — verify tools not in allowlist are rejected
    - **Property 6: No active phase denies all** — verify all tools denied when no phase active
    - **Property 7: Egress default-deny** — verify network command host checking
    - **Validates: Requirements 2.1, 2.2, 2.4, 3.1, 3.2, 4.1, 4.2, 4.3, 4.5, 4.6, 5.1-5.4**

- [ ] 3. Implement Audit Log (`observability/audit.py`)
  - [x] 3.1 Implement `record()` function with append-only JSON-lines output
    - Accept event, tool, detail, decision, reason parameters
    - Append one JSON line per call to `observability/audit.log`
    - Include timestamp (epoch float) in each entry
    - Never overwrite, truncate, or delete existing entries
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ]* 3.2 Write property tests for Audit Log (Properties 8-9)
    - **Property 8: Append-only JSON-lines integrity** — N calls produce exactly N parseable lines, existing lines unchanged
    - **Property 9: Audit reflects decisions** — ALLOWED has empty reason, DENIED has non-empty reason matching gate output
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**

- [x] 4. Implement Agent Loop (`demo/harness.py`)
  - [x] 4.1 Implement `agent_loop()` function with permission-gating and tool dispatch
    - Accept messages, model_fn, permission_check, max_turns parameters
    - Iterate model responses until end_turn or max_turns reached
    - For each tool_use block: call permission_check, execute or deny, record to audit
    - Return "Permission denied" result to model for denied calls
    - Support TOOL_HANDLERS dict for extensible tool registration
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

  - [ ]* 4.2 Write property tests for Agent Loop (Property 10)
    - **Property 10: Loop bounded and permission-respecting** — max_turns honoured, permission_check called once per tool_use block, denied blocks never execute, allowed blocks always execute
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5**

- [x] 5. Checkpoint - Ensure core mechanism passes
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Create test infrastructure
  - [~] 6.1 Create `tests/fixtures.json` with generic ground-truth test cases
    - Include at least 5 cases: deny-list hit (`rm -rf /`), deny-list miss (`ls /tmp`), phase-gate denial (gated tool), egress denial (`curl evil.example`), fully allowed call
    - Each case has: description, tool, input, expected_decision, expected_gate, expected_reason
    - _Requirements: 19.1, 19.2_

  - [~] 6.2 Implement `tests/test_fixtures.py` data-driven test runner
    - Read `tests/fixtures.json`, build Block from each case
    - Run through real Permission Gate with actual policy files
    - Assert actual decision matches expected decision
    - Report which case failed with expected vs actual on failure
    - _Requirements: 19.4, 19.5_

  - [~] 6.3 Implement `tests/test_e2e.py` Day 4 enforcement pattern
    - Test denied call confirmed NOT executed (side effects absent)
    - Test allowed call confirmed DID execute (side effects present)
    - Demonstrate that removing enforcement path causes test to FAIL
    - Run through real Agent Loop with real Permission Gate
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 7. Create CLAUDE.md template and context layer
  - [~] 7.1 Write `template/CLAUDE.md` with pre-filled generic content and placeholders
    - Pre-fill: Startup Workflow (numbered), Working Rules (WIP=1, verify, update, scope, clean), Verification Commands section, Escalation section
    - Use `{{PROJECT_PURPOSE}}`, `{{PRIMARY_VERIFICATION_COMMAND}}`, `{{DOMAIN_ESCALATION_RULES}}` placeholders
    - Keep ≤100 lines, route domain detail to `context/` via links
    - _Requirements: 14.1, 14.2, 14.3, 14.4_

  - [~] 7.2 Create `template/context/README.md` explaining what domain documents belong in the context directory
    - Explain: methodology, scope, standards, threat model documents go here
    - Pre-filled with explanation, empty of actual domain content
    - _Requirements: 14.5_

  - [~] 7.3 Create `template/progress.md` with pre-filled session continuity structure
    - Include sections: Current State (timestamp, active phase), Done (checklist), In Progress (current task + blockers), Next Steps, Decisions Made, Notes for Next Session
    - _Requirements: 17.1_

  - [~] 7.4 Create `template/session-handoff.md` template
    - Structure: Current Objective, Verification Evidence table, Files Changed, Decisions Made, Next Session Startup steps
    - _Requirements: 17.5_

- [ ] 8. Create skill files and hook configuration
  - [~] 8.1 Create `.claude/commands/session-cycle.md` pre-filled generic skill
    - Encode: read CLAUDE.md → run init.sh → read feature_list.json → pick active task → work → verify → update progress → clean exit
    - Include purpose statement, numbered steps, verification checks, exit condition
    - _Requirements: 15.1, 15.2, 15.4_

  - [~] 8.2 Create `.kiro/steering/session-cycle.md` with Kiro front-matter format
    - Same session-cycle content as Claude Code skill
    - Use `inclusion: auto` front-matter
    - _Requirements: 15.2, 18.4_

  - [~] 8.3 Create domain-specific skill placeholder file (`.claude/commands/domain-workflow.md`)
    - Structure provided, content marked with `{{DOMAIN_WORKFLOW_STEPS}}`, `{{DOMAIN_EXIT_CONDITION}}`
    - _Requirements: 15.3_

  - [~] 8.4 Create `.claude/settings.json` with base hook set (5 hooks)
    - `pre:governance-check` (PreToolUse) — runs permission.py, exits 2 to BLOCK
    - `pre:secret-block` (PreToolUse) — blocks hardcoded secrets
    - `post:audit-capture` (PostToolUse) — records to audit.log
    - `stop:cost-tracker` (Stop) — records token usage
    - `stop:clean-state-check` (Stop) — warns if progress.md not updated
    - Document extension pattern for domain-specific hooks
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5, 18.2_

- [ ] 9. Implement `init.sh` verification script
  - [~] 9.1 Write `template/init.sh` with project detection and verification
    - Auto-detect project type (Python/Node/other)
    - Run test suite (fixture tests)
    - Detect unfilled `{{` placeholders in required config files (CLAUDE.md, feature_list.json, deny-list.json, mcp-allowlist.json)
    - Detect stale `progress.md` (last-modified older than recent code changes)
    - Run fixture-based tests as part of verification
    - _Requirements: 1.4, 7.3, 17.4, 19.6_

- [~] 10. Checkpoint - Ensure template is complete and self-consistent
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. Create `tools/tool-registry.md` and template README
  - [~] 11.1 Create `template/tools/tool-registry.md` documenting tool vetting process
    - Include fields: tool name, version pin, review status, approval rationale
    - _Requirements: 13.3_

  - [~] 11.2 Create template README documenting file classification and tool compatibility
    - Document which files are mechanism (never modify) vs policy (customise per domain)
    - Document which files are consumed by Claude Code vs Kiro
    - Note cross-tool compatibility where same content appears in two locations
    - _Requirements: 7.4, 18.5_

- [ ] 12. Implement Demo Script (`demo/demo.py`)
  - [~] 12.1 Implement `demo.py` with scripted 5-turn enforcement demonstration
    - Turn 1: Allowed tool call (in allowlist, phase active) → ✓ execute
    - Turn 2: Phase-gated tool (prereq not passing) → ⛔ DENIED
    - Turn 3: Phase transition (prereq set to "passing")
    - Turn 4: Re-request previously-gated tool → ✓ now executes
    - Turn 5: Model says "done" → exit
    - Support `--nogate` flag to run same model without Permission Gate
    - Print colour-coded terminal output (green ✓, red ⛔)
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

- [ ] 13. Create Red Team Harness example (`examples/red-team-harness/`)
  - [~] 13.1 Create Red Team example directory as filled copy of template
    - Copy template structure, fill all `{{placeholders}}` with pentesting content
    - Mechanism files (permission.py, audit.py, harness.py) identical to template
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

  - [~] 13.2 Create Red Team CLAUDE.md and context documents
    - `CLAUDE.md`: "Red Team Penetration Testing Agent" with ATT&CK references
    - `context/`: ATT&CK technique references, `target-scope.md` (IP ranges, time windows), `methodology.md` (recon→exploit→escalate→report)
    - _Requirements: 10.1, 10.5_

  - [~] 13.3 Create Red Team policy files
    - `feature_list.json`: scope-validation → recon → exploit → report DAG with dependencies
    - `governance/deny-list.json`: DoS commands, lateral movement beyond ROE scope
    - `tools/mcp-allowlist.json`: nmap always permitted, Metasploit gated until recon=passing, egress hosts for authorized targets
    - _Requirements: 10.2, 10.3, 10.4_

  - [~] 13.4 Extend `tests/fixtures.json` with Red Team domain-specific test cases
    - At least 5 domain cases: nmap in-scope allowed, nmap out-of-scope denied, metasploit before recon denied, metasploit after recon allowed, DoS pattern denied
    - _Requirements: 19.3_

  - [~] 13.5 Create Red Team demo script (`examples/red-team-harness/demo/demo.py`)
    - Demonstrate: nmap allowed → metasploit denied → recon passes → metasploit allowed
    - Use Fake Model with pentesting-specific scripted responses
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

- [~] 14. Final checkpoint - Full integration verification
  - Ensure all tests pass across template and red-team example, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document (Properties 1-11)
- The primary enforcement path is `.claude/settings.json` hooks → `governance/permission.py` (CLI mode)
- `demo/harness.py` is OPTIONAL evaluation infrastructure, not the production path
- `permission.py` has a dual interface: CLI (stdin JSON → exit code) for hooks + Python import for tests
- The template ships pre-filled generic content; domain-specific content uses `{{placeholders}}`
- `tests/fixtures.json` is the ground-truth test dataset, extended per domain example
- All mechanism code uses Python standard library only (zero external dependencies)
- `hypothesis` is the only dev dependency, used for property-based tests only (optional)

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.3"] },
    { "id": 2, "tasks": ["2.1", "2.2", "2.3", "3.1"] },
    { "id": 3, "tasks": ["2.4", "2.5", "3.2"] },
    { "id": 4, "tasks": ["2.6", "4.1"] },
    { "id": 5, "tasks": ["4.2", "6.1"] },
    { "id": 6, "tasks": ["6.2", "6.3"] },
    { "id": 7, "tasks": ["7.1", "7.2", "7.3", "7.4", "8.1", "8.2", "8.3"] },
    { "id": 8, "tasks": ["8.4", "9.1", "11.1", "11.2"] },
    { "id": 9, "tasks": ["12.1"] },
    { "id": 10, "tasks": ["13.1"] },
    { "id": 11, "tasks": ["13.2", "13.3"] },
    { "id": 12, "tasks": ["13.4", "13.5"] }
  ]
}
```
