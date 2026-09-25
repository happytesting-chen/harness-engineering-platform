# Claude Code Adapter

<!--
Claude Code entry file.
The project-wide coding-assistant workflow lives in AGENTS.md.
Do not duplicate those instructions here.
-->
@AGENTS.md

<!-- Tailored, product-specific security controls from the shared security layer. -->
@security/shared/active-controls.md

## Claude Code Integration

Claude Code must follow `AGENTS.md` as the authoritative project workflow.

Keep the mechanical hooks configured in `.claude/settings.json` enabled. They are part of the build-time enforcement path and are not replaced by these written instructions.

Security is organized under `security/` into three explicit layers:

- `security/buildtime/` protects the coding assistant during development.
- `security/runtime/` protects the deployed AI application.
- `security/shared/` contains policy, reusable mechanisms and controls used by both layers.

Use the paths under `security/` as the authoritative security paths. Do not use the retired `Security-kit/` or `governance/` paths.

## Files that are NOT part of this project

The following directories ship with the harness template but contain **harness engineering history only** — they document how the template itself was built, not this product:

- `docs/superpowers/` — harness design plans, specs, patches (not product docs)
- `evaluation/runtime-security/` — ships empty; populate via `evaluation/eval.py` after sign-off

Do NOT read these as project state. The project journal is `Harness-Best-Practice/progress.md`.
