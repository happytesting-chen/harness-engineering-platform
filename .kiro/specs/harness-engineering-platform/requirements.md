# Requirements Document

## Introduction

The Harness Engineering Platform is a reusable, domain-agnostic framework for building governed AI agent projects. It provides a generic `template/` directory that any team copies to start a new agent project, and `examples/` that demonstrate filled-in instances for specific domains (starting with offensive security). The platform enforces a Customise → Operationalise → Secure lifecycle through mechanical controls that sit outside the model: deny-list enforcement, phase-gated tool access, and default-deny egress. The entire template runs with zero external dependencies (Python standard library only) and ships a scripted fake model for demonstration. The template is designed for use with Claude Code and Kiro.

### File Classification: Must-Fill vs Optional at Initialisation

When a domain expert copies `template/` to start a new project, the following files require domain-specific content before the harness can function:

| File | Status | Reason |
|---|---|---|
| `CLAUDE.md` (placeholders: `{{PROJECT_PURPOSE}}`, `{{VERIFICATION_COMMAND}}`) | **MUST** | Without this, a fresh session cannot answer "what am I" or "how do I verify" |
| `feature_list.json` (phase names, descriptions, verification commands) | **MUST** | Phase-gate denies all tools if no phases are defined |
| `governance/deny-list.json` (patterns array) | **MUST** | At minimum, review the defaults and add domain-specific hard-deny patterns |
| `tools/mcp-allowlist.json` (tool entries + egress hosts) | **MUST** | Phase-gate denies everything if no tools are registered |
| `context/` (at least one methodology/scope doc) | **MUST** | CLAUDE.md links outward to context/ — an empty directory means the agent has no domain knowledge |

The following files ship pre-filled with generic content OR are only needed later:

| File | Status | When needed |
|---|---|---|
| `progress.md` | **Optional at init** | Ships with structure pre-filled. Required to update from session 2 onward |
| `session-handoff.md` | **Optional** | Only written when a session ends mid-task |
| `tools/tool-registry.md` | **Optional** | Add when formalising tool-vetting process for compliance |
| Domain-specific skill files (`.claude/commands/*.md`) | **Optional** | Generic session-cycle skill ships working. Add domain workflows for efficiency |
| Domain-specific hooks | **Optional** | Base hook set fires for all projects. Add domain hooks for additional coverage |
| `context/target-scope.md` | **Domain-dependent** | MUST for pentest/security agents. Not applicable to all project types |

## Glossary

- **Harness**: The complete surrounding structure (agent loop, permission gate, audit log, configuration) that governs an AI model's execution, making the same model reliable or unreliable based on harness quality.
- **Template**: The domain-agnostic skeleton directory (`template/`) containing placeholder-bearing files that a domain expert copies and fills in to create a new governed agent project.
- **Permission_Gate**: The three-gate enforcement mechanism in `governance/permission.py` that evaluates tool calls in sequence: deny-list → phase-gate → egress control, failing closed on any denial.
- **Deny_List**: A JSON file (`governance/deny-list.json`) containing string patterns that cause immediate, unconditional rejection of any tool call whose command matches, regardless of phase or scope.
- **Phase_Gate**: A mechanism that locks specific tools until a named phase in `feature_list.json` reaches "passing" status, enforcing sequential workflow progression.
- **Egress_Control**: A default-deny network access control that blocks outbound commands unless the target host appears in `tools/mcp-allowlist.json`.
- **MCP_Allowlist**: A JSON file (`tools/mcp-allowlist.json`) listing permitted tools with optional phase-gate constraints and approved egress hosts.
- **Feature_List**: A JSON file (`feature_list.json`) defining a phase DAG where each phase has an ID, dependencies, status, and verification command; only one phase may be active at a time.
- **Agent_Loop**: The generic execution cycle in `harness.py` that receives model responses, evaluates each tool call through the Permission_Gate, executes allowed calls, denies blocked calls, and records all decisions to the audit log.
- **Audit_Log**: An append-only JSON-lines file (`observability/audit.log`) where every tool call decision is recorded with timestamp, tool name, arguments, decision, and reason.
- **Phase_DAG**: A directed acyclic graph defined in `feature_list.json` where phases have explicit dependencies and transition from not-started → active → passing, controlling which tools are unlocked.
- **Fake_Model**: A scripted function returning pre-determined Response objects (same shape as a real LLM SDK), enabling the harness to run and demonstrate enforcement with zero API keys or network access.
- **Demo_Script**: A `demo.py` file in each example that exercises the harness with one allowed call, one denied call (phase-gated), and one call that unlocks after a phase transition.
- **E2E_Enforcement_Test**: A test that proves the permission gate actually prevents execution (not just logs denial) by deliberately breaking enforcement and confirming the test catches the break.
- **Red_Team_Harness**: The first filled-in example (`examples/red-team-harness/`) demonstrating the platform applied to authorized penetration testing with ATT&CK references, nmap/Metasploit tooling, and ROE-based scope.

## Requirements

### Requirement 1: Zero-Dependency Template Execution

**User Story:** As a domain expert, I want to run the template harness without installing any external packages, so that I can evaluate the platform without dependency management overhead.

#### Acceptance Criteria

1. THE Template SHALL execute using only Python standard library modules (no pip-installed packages required).
2. THE Template SHALL include a Fake_Model that produces Response objects matching the structure of a real LLM SDK (content blocks with type, name, input, text, and id fields plus a stop_reason field).
3. WHEN the Fake_Model is used, THE Agent_Loop SHALL complete a full init → tool-call → permission-check → audit → exit cycle without network access or API keys.
4. THE Template SHALL include an `init.sh` script that auto-detects the project type and runs verification commands appropriate to the detected stack.

### Requirement 2: Generic Permission Gate Mechanism

**User Story:** As a platform maintainer, I want a single permission gate implementation that is never modified per project, so that governance enforcement is consistent and auditable across all harness instances.

#### Acceptance Criteria

1. THE Permission_Gate SHALL evaluate three gates in fixed order: Deny_List check, Phase_Gate check, Egress_Control check.
2. THE Permission_Gate SHALL fail closed: if any gate returns a denial reason, the tool call SHALL NOT execute.
3. THE Permission_Gate SHALL accept policy content exclusively from external JSON files (deny-list.json, mcp-allowlist.json, feature_list.json) without requiring code changes to `permission.py`.
4. WHEN a tool call is denied, THE Permission_Gate SHALL return a structured reason string identifying which gate triggered and what pattern or rule matched.
5. THE Permission_Gate SHALL remain identical across all project instances — only the JSON policy files (Deny_List, MCP_Allowlist, Feature_List) change per domain.

### Requirement 3: Deny-List Enforcement

**User Story:** As a security engineer, I want unconditional blocking of dangerous command patterns, so that catastrophic operations are prevented regardless of phase, authorization level, or model behavior.

#### Acceptance Criteria

1. WHEN a tool call command contains any string pattern listed in `deny-list.json`, THE Permission_Gate SHALL deny the call immediately without evaluating subsequent gates.
2. THE Deny_List SHALL support plain substring matching against the command string.
3. WHEN the Deny_List file does not exist or is empty, THE Permission_Gate SHALL treat the deny-list gate as passed (no patterns to match).
4. THE Deny_List JSON file SHALL contain a "patterns" array of strings, each representing one blocked substring.

### Requirement 4: Phase-Gated Tool Access

**User Story:** As a domain expert, I want to lock certain tools until prerequisite phases are verified complete, so that the agent follows a structured workflow and cannot use advanced tools prematurely.

#### Acceptance Criteria

1. WHEN a tool has a "gated_until" field in `mcp-allowlist.json`, THE Phase_Gate SHALL deny access to that tool unless the referenced phase has status "passing" in `feature_list.json`.
2. WHEN a tool has no "gated_until" field, THE Phase_Gate SHALL allow access to that tool if it appears in the MCP_Allowlist.
3. WHEN a tool does not appear in the MCP_Allowlist at all, THE Phase_Gate SHALL deny access with a reason indicating the tool is not in the allowlist.
4. THE Feature_List SHALL enforce that only one phase may have status "active" at any time.
5. WHEN no phase has status "active" in the Feature_List, THE Phase_Gate SHALL deny all tool calls with a reason indicating no active phase exists.
6. WHEN a phase transitions from "active" to "passing", THE Phase_Gate SHALL immediately unlock any tools gated on that phase without requiring a restart.

### Requirement 5: Default-Deny Egress Control

**User Story:** As a security engineer, I want outbound network access blocked by default, so that the agent cannot exfiltrate data or reach unauthorized systems even if the model is compromised or injected.

#### Acceptance Criteria

1. WHEN a tool call command contains a network-initiating token (curl, wget, nc, ssh, nmap), THE Egress_Control SHALL check the command against the "egress_hosts" list in `mcp-allowlist.json`.
2. WHEN the target host in a network command does not appear in the "egress_hosts" list, THE Egress_Control SHALL deny the call with a reason indicating default-deny egress.
3. WHEN the target host in a network command appears in the "egress_hosts" list, THE Egress_Control SHALL allow the call.
4. WHEN a tool call command does not contain any network-initiating token, THE Egress_Control SHALL pass (gate does not apply).

### Requirement 6: Append-Only Audit Trail

**User Story:** As a compliance reviewer, I want every tool call decision recorded in an immutable log, so that I can reconstruct the full history of what the agent attempted and what was allowed or denied.

#### Acceptance Criteria

1. THE Audit_Log SHALL record one JSON line per tool call decision, containing: timestamp, event type, tool name, call arguments, decision (ALLOWED or DENIED), and reason.
2. THE Audit_Log SHALL append entries only — the Agent_Loop SHALL NOT overwrite, truncate, or delete existing log entries.
3. WHEN a tool call is denied, THE Audit_Log SHALL record the denial reason returned by the Permission_Gate.
4. WHEN a tool call is allowed, THE Audit_Log SHALL record the decision as ALLOWED with an empty reason string.
5. THE Audit_Log file SHALL use JSON-lines format (one valid JSON object per line, newline-delimited).

### Requirement 7: Template Placeholder System

**User Story:** As a domain expert, I want clearly marked placeholders in all configurable files, so that I know exactly what content to provide without reading the mechanism code.

#### Acceptance Criteria

1. THE Template SHALL use `{{PLACEHOLDER_NAME}}` syntax for all values that must be filled in by the domain expert.
2. THE Template SHALL include placeholders in: AGENTS.md, feature_list.json, tools/mcp-allowlist.json, governance/deny-list.json, and context/ directory files.
3. WHEN `init.sh` detects unfilled `{{` placeholders in required configuration files, THE Template SHALL report the unfilled placeholders and fail verification.
4. THE Template README SHALL document which files are generic (never modify per project) and which are customised (fill in per project), with the responsible role for each.

### Requirement 8: Agent Loop Lifecycle

**User Story:** As a platform engineer, I want the agent loop to follow a strict init → task → verify → exit lifecycle, so that every session is bounded and leaves a clean state for the next session.

#### Acceptance Criteria

1. THE Agent_Loop SHALL process model responses iteratively until either the model signals end_turn or a maximum turn count is reached.
2. WHEN the model response contains tool_use blocks, THE Agent_Loop SHALL evaluate each block through the Permission_Gate before execution.
3. WHEN a tool call is denied, THE Agent_Loop SHALL return a "Permission denied" result to the model without executing the tool handler.
4. WHEN a tool call is allowed, THE Agent_Loop SHALL execute the registered tool handler and return the output to the model.
5. WHEN the maximum turn count is reached, THE Agent_Loop SHALL stop execution and indicate the turn cap was hit.
6. THE Agent_Loop SHALL support registration of arbitrary tool handlers as a name-to-function mapping, extensible per domain without modifying the loop code.

### Requirement 9: E2E Enforcement Verification (Day 4 Pattern)

**User Story:** As a quality engineer, I want a test that proves enforcement actually works by demonstrating it catches deliberate breakage, so that I have confidence the gate prevents execution rather than merely logging denials.

#### Acceptance Criteria

1. THE E2E_Enforcement_Test SHALL run a complete agent session through the real Agent_Loop with the real Permission_Gate attached.
2. THE E2E_Enforcement_Test SHALL include a test case where a denied tool call is confirmed to NOT have executed (side effects absent, not just logged).
3. THE E2E_Enforcement_Test SHALL include a test case where an allowed tool call is confirmed to HAVE executed (side effects present).
4. THE E2E_Enforcement_Test SHALL demonstrate that removing the enforcement path (e.g., removing the denial branch in the agent loop) causes the test to FAIL — proving the test is sensitive to enforcement wiring, not just rule evaluation.
5. WHEN the E2E_Enforcement_Test passes, THE test output SHALL serve as evidence that the Permission_Gate prevents execution, not just logs denial.

### Requirement 10: Red Team Harness Example

**User Story:** As a security team lead, I want a complete filled-in example demonstrating the harness applied to penetration testing, so that I can see how domain-specific content maps onto the generic template.

#### Acceptance Criteria

1. THE Red_Team_Harness SHALL include a `context/` directory with ATT&CK technique references, authorized target scope (IP ranges and time windows), and a recon→exploit→escalate→report methodology document.
2. THE Red_Team_Harness SHALL include a `tools/mcp-allowlist.json` with nmap permitted from phase start and Metasploit gated until the recon phase reaches "passing" status.
3. THE Red_Team_Harness SHALL include a `governance/deny-list.json` with patterns blocking denial-of-service commands and lateral movement beyond the Rules of Engagement scope.
4. THE Red_Team_Harness SHALL include a `feature_list.json` with a phase DAG of at least: scope-validation → recon → exploit → report, with explicit dependencies between phases.
5. THE Red_Team_Harness SHALL include an `AGENTS.md` with pentesting-specific startup workflow, working rules referencing ROE, and escalation procedures for scope ambiguity.

### Requirement 11: Demo Script Pattern

**User Story:** As a platform evaluator, I want a runnable demo in each example that shows the harness enforcing controls in real time, so that I can verify the three lifecycle stages (Customise → Operationalise → Secure) without reading all source code.

#### Acceptance Criteria

1. THE Demo_Script SHALL demonstrate one tool call that is allowed and executes successfully.
2. THE Demo_Script SHALL demonstrate one tool call that is denied due to phase-gating (tool locked because prerequisite phase is not passing).
3. THE Demo_Script SHALL demonstrate a phase transition (prerequisite phase moves to "passing") followed by the previously-denied tool call now succeeding.
4. THE Demo_Script SHALL use the Fake_Model (no API keys or network required) to produce the scripted tool calls.
5. THE Demo_Script SHALL print colour-coded terminal output distinguishing allowed (green checkmark) from denied (red stop sign) calls.
6. WHEN run with a `--nogate` flag, THE Demo_Script SHALL execute the same model script without the Permission_Gate, showing that the model alone does not enforce controls.

### Requirement 12: Template Directory Structure

**User Story:** As a platform engineer, I want a standardised directory layout in the template, so that every harness instance has predictable file locations and separation between mechanism (generic) and policy (customised).

#### Acceptance Criteria

1. THE Template SHALL contain the following top-level structure: `harness.py`, `init.sh`, `AGENTS.md`, `feature_list.json`, `progress.md`, `governance/` directory, `tools/` directory, `context/` directory, `observability/` directory, and `tests/` directory.
2. THE Template `governance/` directory SHALL contain `permission.py` (mechanism, never modified) and `deny-list.json` (policy, customised per domain).
3. THE Template `tools/` directory SHALL contain `mcp-allowlist.json` (policy, customised per domain).
4. THE Template `observability/` directory SHALL contain `audit.py` (mechanism, never modified).
5. THE Template `context/` directory SHALL serve as the location for domain-specific knowledge documents provided by the domain expert.
6. THE Template `tests/` directory SHALL contain at least one E2E_Enforcement_Test file demonstrating the Day 4 pattern.

### Requirement 13: Supply-Chain Vetting for Tool Registration

**User Story:** As a security architect, I want all external tool integrations explicitly vetted and version-pinned in a registry, so that the harness does not silently adopt unreviewed dependencies.

#### Acceptance Criteria

1. THE MCP_Allowlist SHALL include a "version" field for each registered tool, pinning it to a specific reviewed version.
2. WHEN a tool is registered in the MCP_Allowlist, THE registration SHALL include: name, description, and version at minimum.
3. THE Template SHALL include a `tools/tool-registry.md` document where each tool's review status, version pin, and approval rationale are recorded.
4. WHEN a tool not present in the MCP_Allowlist is invoked, THE Permission_Gate SHALL deny the call, enforcing that only vetted tools execute.

### Requirement 14: Context Layer Best Practice (CLAUDE.md / AGENTS.md)

**User Story:** As a domain expert, I want the template to ship a pre-filled instruction file with generic best practices already written, so that I only need to add my domain-specific content — not reinvent the structure from scratch.

#### Acceptance Criteria

1. THE Template SHALL ship a `CLAUDE.md` (or `AGENTS.md`) file with the following sections pre-filled with working generic content: Startup Workflow (numbered steps), Working Rules (WIP=1, verification required, update artifacts, stay in scope, leave clean state), Required Artifacts list, Definition of Done checklist, End of Session steps, Verification Commands section, and Escalation section.
2. THE pre-filled generic content SHALL be usable as-is without domain knowledge — a fresh Claude Code session reading only this file SHALL be able to answer: what is the startup sequence, how to verify, and what to do when stuck.
3. THE Template SHALL mark domain-specific sections with `{{PLACEHOLDER}}` syntax: `{{PROJECT_PURPOSE}}`, `{{PRIMARY_VERIFICATION_COMMAND}}`, and `{{DOMAIN_ESCALATION_RULES}}`.
4. THE Template `CLAUDE.md` SHALL be ≤100 lines total and SHALL route detailed domain knowledge to topic docs in `context/` via explicit links, never inline the full content.
5. THE Template SHALL include a `context/` directory with a `README.md` explaining what domain documents belong here (methodology, scope, standards, threat model) — pre-filled with the explanation, empty of actual domain content.

### Requirement 15: Lifecycle Skill Definitions

**User Story:** As a domain expert, I want the template to include a pre-filled skill/workflow definition file that encodes the generic session cycle, so that my agent has a reusable "how to work" pattern — and I only add domain-specific phase content.

#### Acceptance Criteria

1. THE Template SHALL include at least one pre-filled skill file (`.md` workflow definition) encoding the generic session cycle: read CLAUDE.md → run init.sh → read feature_list.json → pick one active task → work → verify → update progress → clean exit.
2. THE pre-filled skill SHALL be functional in Claude Code as a slash command (placed in `.claude/commands/` or equivalent) or in Kiro as a steering file (placed in `.kiro/steering/`).
3. THE Template SHALL include a second, placeholder skill file for domain-specific workflows (e.g., `engage.md` for a pentest workflow, `review.md` for a code review workflow) — structure provided, content marked with `{{DOMAIN_WORKFLOW_STEPS}}`.
4. EACH skill file SHALL include: a one-line purpose statement, numbered steps, verification checks between steps, and an exit condition.

### Requirement 16: Hook-Based Observability (Claude Code / Kiro Hooks)

**User Story:** As a platform engineer, I want the template to ship pre-configured hooks for governance and observability, so that enforcement and audit logging fire automatically without requiring the domain expert to wire them manually.

#### Acceptance Criteria

1. THE Template SHALL include a `.claude/settings.json` file (or equivalent Kiro hook configuration) with at least two pre-configured hooks: one PreToolUse hook for governance checking and one PostToolUse hook for audit logging.
2. THE PreToolUse hook SHALL invoke the governance check (deny-list + phase-gate) and exit with code 2 (BLOCK) when a violation is detected, printing the denial reason to stdout.
3. THE PostToolUse hook SHALL record every tool execution result to the Audit_Log.
4. THE hook configuration SHALL be pre-filled and functional out of the box — no domain-specific content required to activate basic enforcement and logging.
5. THE Template SHALL document (in `.claude/settings.json` comments or a companion README) how to add domain-specific hooks (e.g., a hook that checks file edits against a scope boundary).

### Requirement 17: Session Continuity and Clean State

**User Story:** As a domain expert running multi-session engagements, I want the template to enforce that every session leaves a clean, resumable state, so that the next session picks up from recorded artifacts — not by re-deriving context from code exploration.

#### Acceptance Criteria

1. THE Template SHALL ship a pre-filled `progress.md` with the following generic sections: Current State (timestamp, active phase), Done (checklist), In Progress (current task + blockers), Next Steps, Decisions Made, and Notes for Next Session.
2. THE Template `CLAUDE.md` Startup Workflow SHALL include "Read progress.md" as a required step before any work begins.
3. THE Template `CLAUDE.md` End of Session section SHALL include: update progress.md, update feature_list.json with phase transition if applicable, remove any temporary/debug artifacts, and confirm init.sh passes before ending.
4. WHEN a session ends without updating `progress.md`, THE Template `init.sh` SHALL detect a stale progress file (last-modified timestamp older than most recent code changes) and issue a warning.
5. THE Template SHALL include a `session-handoff.md` template file (structure only, to be filled when a session ends mid-task) with: Current Objective, Verification Evidence table, Files Changed, Decisions Made, and Next Session Startup steps.

### Requirement 18: Claude Code and Kiro Compatibility

**User Story:** As a platform engineer, I want the template to produce files in the exact locations Claude Code and Kiro expect, so that the harness integrates natively without manual wiring after copying.

#### Acceptance Criteria

1. THE Template SHALL place the primary instruction file at project root as `CLAUDE.md` (Claude Code's auto-loaded project instruction file).
2. THE Template SHALL include a `.claude/settings.json` with hooks configuration in the schema Claude Code expects (PreToolUse, PostToolUse, Stop event types with matcher patterns and command arrays).
3. THE Template SHALL place skill/command files in `.claude/commands/` for Claude Code compatibility (each as a `.md` file loadable as a slash command).
4. THE Template SHALL include a `.kiro/steering/` directory with at least one steering file for Kiro compatibility, containing the same session-cycle instructions as the Claude Code skill but in Kiro's front-matter format (`inclusion: auto`).
5. THE Template README SHALL document which files are consumed by Claude Code vs. Kiro, noting where the same content appears in two locations and why (cross-tool compatibility).

### Requirement 19: Verification Test Fixture Dataset

**User Story:** As a quality engineer, I want a structured test dataset with known-correct expected outcomes per case, so that verification is reproducible, extensible per domain, and has explicit ground truth rather than relying on ad-hoc assertions.

#### Acceptance Criteria

1. THE Template SHALL include a `tests/fixtures.json` file containing an array of test cases, each with: tool name, input arguments, expected decision (ALLOWED or DENIED), expected gate (deny-list, phase-gate, egress, or null), and expected reason string.
2. THE Template SHALL ship with at least 5 generic test cases covering: one deny-list hit, one deny-list miss (allowed), one phase-gate denial, one egress denial, and one fully-allowed call.
3. EACH example project SHALL extend `tests/fixtures.json` with at least 5 additional domain-specific test cases reflecting that project's deny-list patterns, tool allowlist, and phase structure.
4. THE test runner SHALL read `tests/fixtures.json`, execute each case through the real Permission_Gate, and assert that the actual decision matches the expected decision for every case.
5. WHEN any fixture case fails (actual ≠ expected), THE test output SHALL report which case failed, what was expected, and what was returned — serving as ground truth evidence for the harness state.
6. THE `init.sh` verification step SHALL include running the fixture-based test — all cases must pass for the project to be considered in a verified state.
