# Context Directory

This directory holds domain-specific knowledge documents that the agent reads for context. CLAUDE.md links here — keep documents focused and reference-ready.

## What Goes Here

| Document Type | Purpose | Example |
|--------------|---------|---------|
| Methodology | Step-by-step workflow for the domain | `methodology.md` |
| Scope definition | Boundaries of what's in/out of scope | `target-scope.md` |
| Standards references | Compliance frameworks, coding standards | `standards.md` |
| Threat model | Risks, attack surfaces, mitigations | `threat-model.md` |
| Architecture | System design, component relationships | `architecture.md` |
| Glossary | Domain-specific terminology | `glossary.md` |

## Guidelines

- One topic per file — keep documents under 200 lines
- Use filenames that describe the content (no `doc1.md`)
- CLAUDE.md should link to each file you add here
- The agent reads these files for domain context during sessions
- Do NOT put mechanism code or configuration here — those go in `governance/` and `tools/`

## Getting Started

1. Copy this template directory for your project
2. Add at least one methodology or scope document
3. Update CLAUDE.md's Domain Context section with links to your files
4. Run `./init.sh` to verify the project is properly configured
