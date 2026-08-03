# Context Directory

This directory holds **project-specific assets** — the architecture, product/design,
and domain knowledge unique to *this* project. The agent reads them for context.
CLAUDE.md links here. Keep documents focused and reference-ready.

> **This is for what you author per project, not generic framework material.**
> Generic references that ship with the template live elsewhere: harness principles in
> root `BEST-PRACTICES.md`, security controls in `security/SECURITY.md`. Don't copy
> those here.

## What Goes Here

| Document Type | Purpose | Example |
|--------------|---------|---------|
| Architecture | System design, components, data flow | `architecture.md` |
| Product / design doc | What the product does and why; requirements | `product-design.md` |
| Methodology | Step-by-step workflow for the domain | `methodology.md` |
| Scope definition | Boundaries of what's in/out of scope | `target-scope.md` |
| Threat model | Project-specific risks, attack surfaces, mitigations | `threat-model.md` |
| Standards references | Compliance frameworks this project must meet | `standards.md` |
| Glossary | Domain-specific terminology | `glossary.md` |

## Guidelines

- Author these per project — they describe *your* system, not the framework.
- One topic per file — keep documents under 200 lines.
- Use filenames that describe the content (no `doc1.md`).
- CLAUDE.md should link to each file you add here.
- Do NOT put mechanism code/config here (→ `governance/`, `tools/`), generic harness
  guidance (→ root `BEST-PRACTICES.md`), or security controls (→ `security/`).

## Getting Started

1. Copy this template directory for your project
2. Add at least one methodology or scope document
3. Update CLAUDE.md's Domain Context section with links to your files
4. Run `./init.sh` to verify the project is properly configured
