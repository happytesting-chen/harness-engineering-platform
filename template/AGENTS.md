# {{PROJECT_NAME}}

{{PROJECT_PURPOSE}}

## Purpose of This File

This file is the authoritative workflow for coding assistants working with this Secure AI Application Template.

The human developer describes **what to build**. The coding assistant must use this file to determine **how to clarify, record, build, secure, and verify the application**.

Do not require the developer to understand the internal template structure before product definition begins. Guide the developer through the process conversationally and record confirmed requirements in the appropriate project files.

## Development Workflow

### 1. Start by Understanding the Project

When asked to read `AGENTS.md` and follow the workflow:

1. Confirm that the working directory is the project root.
2. Read the existing files under `Context/`.
3. Read `Harness-Best-Practice/progress.md` and `Harness-Best-Practice/feature_list.json` if they contain existing project state.
4. Determine whether this is a new/unconfigured project or an existing project.
5. Do not begin substantial implementation until the important product requirements are sufficiently clear.

For a fresh project, a failing `./init.sh` may indicate expected placeholders or incomplete project/security configuration. Use its output to understand what remains to be configured; do not treat expected fresh-template failures as a reason to abandon the product-definition workflow.

### 2. Guide Product Definition

If the product requirements are incomplete, ask the developer focused questions in the coding-assistant conversation.

Clarify only what is needed for the application being built. Typical areas include:

- product purpose and main user flows;
- required AI model, LLM, or agent framework;
- tools and actions the application needs;
- external websites, APIs, databases, or other systems it must access;
- credentials, secrets, or sensitive data involved;
- storage requirements;
- user interface or integration requirements;
- deployment environment;
- important operational, compliance, or human-approval constraints.

Do not silently guess important requirements. If a decision materially affects architecture, permissions, data handling, external access, or security, ask the developer.

Do not force the developer to manually decide which `Context/` file to edit. The conversation is the normal product-definition interface.

### 3. Record Confirmed Requirements in Context/

After the developer confirms a requirement, record it in the appropriate file under `Context/`.

Use `Context/` as the project-specific source of truth. Follow `Context/README.md` and the existing Context file structure when deciding where information belongs.

Typical mapping:

- product purpose, functions, and user flows → product/design context;
- model, framework, and AI stack → AI-stack context;
- components, tools, integrations, and data flows → architecture context;
- hosting, network environment, external destinations, and operational environment → deployment context.

If the repository uses template/stub Context files, complete or replace the relevant placeholders with confirmed project information.

Before substantial implementation, summarize the important requirements back to the developer when confirmation is needed. Keep unresolved material decisions explicit rather than inventing values.

### 4. Determine the Required Security Controls

Security starts from the product requirements and continues throughout development.

Before implementing a capability, determine which Secure Template controls apply. Use the project Context together with the security and governance references in this repository, including:

- `Security-kit/SECURITY.md` — security-control reference;
- `Security-kit/active-controls.md` — tailored active controls when generated;
- `governance/deny-list.json` — hard-blocked patterns;
- `governance/mcp-allowlist.json` — approved tools and egress destinations;
- `governance/permission.py` — permission enforcement;
- `governance/runtime_dispatcher.py` — deployed runtime tool-call chokepoint;
- `Security-kit/content_trust.py` — untrusted-content screening.

Use `/security-tailor` or the repository's current security-tailoring workflow where required to derive project-specific security coverage from `Context/`. Do not invent security exceptions merely to make implementation easier.

A product capability and its security control are part of the same implementation. Examples:

```text
External website/API access  -> egress control
Tool/action invocation       -> tool permission + runtime enforcement
Credentials/secrets          -> secret protection
External/untrusted content   -> content trust
Sensitive/high-impact action -> human approval where required
```

### 5. Build the Application Through the Secure Template

Implement product functionality and the applicable security controls together.

Do not first build an unrestricted path and plan to secure it later when the template already provides the required controlled path.

For deployed runtime tool actions:

```text
Agent / Orchestrator
        ↓
governance/runtime_dispatcher.py
        ↓
governance/permission.py
        ↓
ALLOW / DENY
        ↓
Actual Tool
```

The application/orchestrator must use the dispatcher rather than retaining or invoking raw tool handlers through a bypass path.

For external or untrusted tool results:

```text
Actual Tool
        ↓
governance/runtime_dispatcher.py
        ↓
result_screen
        ↓
Security-kit/content_trust.py
        ↓
Agent / LLM
```

Screen untrusted results before they are added back to normal model context.

If a new capability is introduced during development, return to the relevant earlier steps: clarify it when necessary, update `Context/`, determine any new security requirements, update policy/configuration, then implement it.

## Common Architecture and Governance

### Tech Stack

- **Language:** {{LANGUAGE}} (e.g., Python 3.11+)
- **Dependencies:** Zero external dependencies for mechanism code unless the project explicitly requires otherwise.
- **Supported coding assistants:** Claude Code, Kiro, Codex, Cursor, Copilot, and other assistants capable of reading and following this file.
- **Enforcement:** `governance/permission.py` provides the permission check used by the harness/runtime mechanisms.

### Repository Structure

```text
├── AGENTS.md                         ← Authoritative coding-assistant workflow
├── Context/                          ← Project-specific requirements and design
├── governance/                       ← Enforcement + policy
│   ├── permission.py
│   ├── runtime_dispatcher.py
│   ├── deny-list.json
│   └── mcp-allowlist.json
├── Security-kit/                     ← Security controls and references
├── Harness-Best-Practice/            ← Workflow state and harness references
│   ├── progress.md
│   ├── feature_list.json
│   └── observability/
├── tests/                            ← Verification
├── demo/                             ← Enforcement demonstrations
└── evaluation/                       ← Quality evaluation
```

### Hard Constraints

{{DENY_LIST_SUMMARY}}

- Build-time enforcement is mechanical where supported by the configured coding-assistant integration.
- Permission gates fail closed; the agent must not bypass, modify, or disable the enforcement mechanism.
- Protected policy/enforcement paths must remain protected from agent self-modification where configured.
- Deny-list patterns are blocked unconditionally.
- Phase transitions that require human sign-off must not be self-approved by the coding assistant.
- Runtime protection must be in the real deployed application path; merely having security files in the repository is not sufficient.

## Working Rules

- Work on one coherent task at a time; finish or explicitly park it before starting another.
- Stay within the agreed product scope and active project phase.
- Ask rather than guess when an unresolved decision materially affects the product or security boundary.
- Update `Harness-Best-Practice/progress.md` with important work, decisions, unresolved items, and next steps.
- Leave the repository in a clean state: no temporary debug files, knowingly broken tests, or accidental secrets.
- Do not claim completion without verification evidence.

## Verification

Before claiming a feature or application is complete:

1. Verify the intended product behavior.
2. Verify that applicable security controls are actually on the execution/data path.
3. Run the relevant automated tests and project verification commands.
4. Run the project's full health check when appropriate.
5. Report unresolved failures, gaps, or residual risks to the developer rather than hiding them.

Typical commands include:

```bash
{{PRIMARY_VERIFICATION_COMMAND}}
python3 tests/test_fixtures.py
python3 tests/test_e2e.py
python3 evaluation/eval.py
./init.sh
```

Use the commands that actually exist and apply to the current project; do not fabricate successful verification.

## End of Session

Before ending a development session:

1. Update `Harness-Best-Practice/progress.md` with current state and decisions.
2. Run the appropriate verification/health checks for the work performed.
3. If a phase requires human sign-off, report that it is ready for sign-off rather than self-transitioning.
4. If work is incomplete, leave a clear handoff describing what remains.

## Escalation

- **Product or scope ambiguity:** Ask the developer and update `Context/` after confirmation.
- **Security applicability ambiguity:** Consult `Security-kit/` and the security-tailoring workflow; keep the uncertainty explicit if unresolved.
- **Tool unavailable or denied:** Check the relevant governance policy. Do not bypass a denial.
- **Repeated implementation failures:** Record the state in `Harness-Best-Practice/progress.md` and ask for human review when needed.
- **Permission denied:** Do not repeatedly retry or weaken policy to force success.
- {{DOMAIN_ESCALATION_RULES}}

## References

- `Context/README.md` — what belongs in project Context.
- `Harness-Best-Practice/BEST-PRACTICES.md` — generic harness-engineering principles.
- `Security-kit/SECURITY.md` — security-control reference.
- {{DOMAIN_CONTEXT_LINKS}}
