# {{PROJECT_NAME}}

{{PROJECT_PURPOSE}}

## Purpose of This File

This file is the authoritative workflow for every coding assistant working on this project.

The developer should be able to open the copied project with a coding assistant, ask it to read `AGENTS.md`, describe the product in the chat, and then follow the guided workflow below.

Do not require the developer to manually decide which project file should contain each requirement. The coding assistant should clarify, organize, and record the confirmed requirements in the appropriate `Context/` files.

## Tech Stack

- **Language:** {{LANGUAGE}} (e.g., Python 3.11+)
- **Dependencies:** Zero external deps for mechanism code (stdlib only)
- **Agent runtimes:** Claude Code, Kiro, Codex, Cursor, Copilot
- **Enforcement:** `security/shared/permission.py` — four-gate permission check (CLI mode)

## Architecture

```text
├── AGENTS.md                         ← Authoritative coding-assistant workflow
├── CLAUDE.md                         ← Claude Code adapter; imports AGENTS.md
├── security/                         ← SECURITY LAYER
│   ├── buildtime/                    ← Coding-assistant hook adapters
│   │   ├── prompt_screen.py
│   │   └── secret_scan.py
│   ├── shared/                       ← Shared policy, guidance, and mechanisms
│   │   ├── SECURITY.md               ← Control reference
│   │   ├── permission.py             ← Permission-gate entry point
│   │   ├── deny-list.json            ← Hard-blocked command patterns
│   │   ├── mcp-allowlist.json        ← Approved tools + egress hosts
│   │   ├── content_trust.py          ← Data-plane content boundary
│   │   └── active-controls.md        ← Project-tailored controls
│   └── runtime/                      ← Deployed-application security
│       ├── runtime_dispatcher.py
│       ├── runtime_screen.py
│       └── core/                     ← Runtime security modules
├── Harness-Best-Practice/            ← Workflow state + reusable guidance
│   ├── progress.md                   ← Session journal + handoff
│   ├── feature_list.json             ← Phase DAG
│   ├── BEST-PRACTICES.md             ← Harness engineering principles
│   └── observability/
│       └── audit.py                   ← Append-only audit log
├── Context/                          ← Product-specific requirements and assumptions
├── tests/                            ← Verification and enforcement tests
├── demo/                             ← Demonstration only, not production path
└── evaluation/                       ← Evaluation and evidence
```

# Coding Assistant Workflow

## 1. Start by Understanding the Project

When the developer asks you to read this file and follow the workflow:

1. Confirm the working directory is the copied project root.
2. Read this file completely.
3. Read the existing files under `Context/`.
4. Read `Harness-Best-Practice/progress.md` and `Harness-Best-Practice/feature_list.json` if they contain existing project state.
5. Determine whether this is a new/unconfigured project or an existing project being continued.

Do not begin substantial implementation until the critical product requirements are sufficiently clear.

## 2. Guide the Product-Definition Conversation

If the product requirements are incomplete, ask the developer focused clarification questions in the coding-assistant chat.

The developer may begin with a short product description. Expand that description only as much as necessary to build the application correctly and securely.

Clarify, where relevant:

- Product purpose and expected user outcome
- Main functions and workflows
- LLM/model and framework
- Required tools and actions
- External websites, APIs, services, databases, or systems
- Credentials, secrets, or sensitive data
- User interface
- Storage or persistence requirements
- Deployment environment
- Human approval requirements
- Important constraints, assumptions, and out-of-scope items

Ask the developer when a decision is important. Do not silently guess critical requirements.

Do not ask unnecessary questions that do not affect product behavior, architecture, security, or deployment.

## 3. Record Confirmed Requirements in Context/

The coding assistant is responsible for recording confirmed requirements in the appropriate `Context/` files.

Use the existing `Context/` structure as the project source of truth. For example:

- Product purpose, users, functions, and UX → product/design context
- LLM, framework, and agent stack → AI-stack context
- Components, tools, data flow, and trust boundaries → architecture context
- Hosting, network, credentials, and environment → deployment context
- Scope, assumptions, and exclusions → relevant scope/context files

When an existing Context file is a template or stub, complete it using confirmed information.

If the correct destination is unclear, choose the closest existing Context file rather than inventing a new structure unnecessarily.

Do not record unconfirmed assumptions as facts. Mark unresolved assumptions explicitly and ask the developer when they block safe implementation.

## 4. Identify the Required Security Controls Before Substantial Coding

After the critical requirements are understood, determine which security controls apply to the product before building the corresponding capability.

Use the existing security material as the implementation source of truth, including:

- `security/shared/SECURITY.md`
- `security/shared/active-controls.md` when present and populated
- `security/shared/deny-list.json`
- `security/shared/mcp-allowlist.json`
- `security/shared/permission.py`
- `security/runtime/` and the project's runtime-security tests

Typical capability-to-control mapping includes:

| Product capability | Security consideration |
|---|---|
| Calls tools or performs actions | Tool authorization / permission control |
| Accesses websites, APIs, or external hosts | Egress restriction / allowlist |
| Uses credentials or secrets | Secret protection |
| Reads Internet or other untrusted content | Content-trust / prompt-injection boundary |
| Performs sensitive or irreversible actions | Human approval where required |
| Returns model output to users or downstream systems | Output handling / release controls where applicable |

Security is not a separate final phase. Apply the required control while implementing each relevant product capability.

## 5. Build the Application and Security Together

For each capability:

```text
Product requirement
        ↓
Determine applicable control
        ↓
Configure the relevant policy
        ↓
Implement the capability through the approved mechanism
        ↓
Add or update verification
```

Examples:

```text
Fetch news from TechCrunch
        ↓
External network access required
        ↓
Configure approved egress destination
        ↓
Implement fetch through the governed runtime path
        ↓
Verify approved host is allowed and unapproved host is denied
```

```text
Save a digest
        ↓
Tool/action required
        ↓
Confirm the tool is approved
        ↓
Route the action through the permission mechanism
        ↓
Verify approved action succeeds and unapproved action is blocked
```

Do not create a direct execution path that bypasses the template's security mechanism and plan to secure it later.

## 6. Reassess Security When Requirements Change

If the developer introduces a new capability during development, update the relevant `Context/` files first and determine whether the change introduces:

- A new tool or action
- A new external destination
- A new credential or secret
- A new source of untrusted content
- A new sensitive data flow
- A new approval requirement
- A new runtime trust boundary

Then update the relevant policy, implementation, and verification before completing the feature.

## 7. Verify Before Claiming Completion

Product behavior and security enforcement must both be verified.

Use the project's existing verification commands and tests. At minimum, verify that:

- Required product functions work
- Approved actions are allowed
- Unapproved actions are denied
- Egress restrictions are enforced where applicable
- Untrusted content is handled through the intended trust boundary
- Secrets are not passed through unsafe paths
- Runtime tool calls use the governed execution path
- The project health check passes when configuration is complete

Do not claim completion merely because the application appears to work.

## 8. Developer Review and Sign-Off

When the required verification passes:

1. Summarize what was implemented.
2. Summarize the important security controls applied.
3. Identify unresolved assumptions, gaps, or residual risks.
4. Update `Harness-Best-Practice/progress.md` with the current state and decisions.
5. Request developer review/sign-off where required.

The coding assistant must not self-promote phases that require human approval.

# Working Rules

- **WIP=1** — One task at a time. Finish or park before starting another.
- **Verify before claiming done** — Run the required verification command. Exit 0 = done only when the command is intended as the completion gate.
- **Update progress.md** — Record what was done, decisions, and next steps before session end.
- **Stay in scope** — Work only within the agreed requirements and active phase.
- **Do not guess critical requirements** — Ask the developer.
- **Leave clean state** — No temporary files, broken tests, or uncommitted debug code.
- **Do not bypass security controls** — Product code must use the intended governed path.

# Hard Constraints

{{DENY_LIST_SUMMARY}}

- Enforcement is mechanical — `security/shared/permission.py` evaluates governed tool calls.
- Four gates in order: protected-paths → deny-list → phase-gate → egress (fail-closed, first denial wins).
- The agent CANNOT bypass, modify, or disable the permission gate.
- Phase transitions require human sign-off; the agent cannot self-promote phases.
- Patterns in `security/shared/deny-list.json` are blocked unconditionally.
- Security files existing in the repository do not by themselves protect the deployed application; the application must route the relevant runtime actions and data through the security mechanisms defined by the template.

# How to Run

```bash
./init.sh
python3 demo/demo.py
python3 demo/demo.py --nogate
```

# How to Verify

```bash
{{PRIMARY_VERIFICATION_COMMAND}}
python3 tests/test_fixtures.py
python3 tests/test_e2e.py
python3 evaluation/eval.py
./init.sh
```

Use the verification commands that apply to the current project state. Do not remove or weaken failing security tests merely to obtain a passing result.

# Escalation

- **Scope ambiguity:** Re-read `Harness-Best-Practice/feature_list.json` and `Context/`; ask the developer if the ambiguity remains.
- **Tool not available:** Check `security/shared/mcp-allowlist.json`; do not bypass the permission mechanism.
- **Repeated failures (3+):** Update `Harness-Best-Practice/progress.md` and flag the issue for human review.
- **Permission denied:** Do not retry or bypass the denial. Record it in `Harness-Best-Practice/progress.md` and surface it to the developer.
- {{DOMAIN_ESCALATION_RULES}}

# Current State

See:

- `Harness-Best-Practice/progress.md` for the session journal and handoff
- `Harness-Best-Practice/feature_list.json` for phase status
- `Context/` for project-specific requirements and assumptions

# Reference

- [BEST-PRACTICES.md](Harness-Best-Practice/BEST-PRACTICES.md) — Harness engineering principles
- `security/shared/SECURITY.md` — Security-control reference
- `security/shared/permission.py` — Permission enforcement
- `security/shared/mcp-allowlist.json` — Approved tools and egress destinations
- `security/runtime/` — Deployed-application security mechanisms

# Domain Context

See `Context/` for project-specific AI-development assets: product/design, AI stack, deployment target, architecture, methodology, scope, assumptions, and other confirmed requirements.

Threat model and shared security controls live in `security/shared/`; deployed runtime controls live in `security/runtime/`.

- {{DOMAIN_CONTEXT_LINKS}}
