# Secure Template Bootstrap

This `CLAUDE.md` is only for creating a new application project from this repository's `template/` directory.

Do not use this file as the application development workflow. After the new project is created, the new project's own `CLAUDE.md` and `AGENTS.md` become authoritative.

## Create a New Project

When the developer asks you to create a new project using the Secure Template:

1. Determine the requested project name. Ask only if the name is missing or ambiguous.
2. Create a new project directory from the complete contents of `template/`.
3. Do not modify the source `template/` while creating the project.
4. After the copy is complete, continue all subsequent work from the new project directory. Do not develop the application in this template repository.
5. Read and follow the new project's `CLAUDE.md`. It imports `AGENTS.md` and the active security controls that govern application development.
6. Continue with the product clarification, secure development, and verification workflow defined by the new project.

## Bootstrap Boundary

```text
This repository
    |
    |  create project from template/
    v
New project directory
    |
    |  hand over
    v
New project's CLAUDE.md
    |
    v
AGENTS.md + active security controls
    |
    v
Clarify -> Build + Secure -> Verify
```

A shell `cd` by itself may not permanently change Claude Code's session root. The important requirement is that after project creation, all application files, commands, edits, and verification must target the new project directory and follow the instructions located there.
