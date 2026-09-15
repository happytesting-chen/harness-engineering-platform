# Claude Code Adapter

<!--
Claude Code entry file.
The project-wide coding-assistant workflow lives in AGENTS.md.
Do not duplicate those instructions here.
-->
@AGENTS.md

<!-- Tailored, product-specific security controls shared by build-time and runtime security. -->
@security/shared/active-controls.md

## Claude Code Integration

Claude Code must follow `AGENTS.md` as the authoritative project workflow.

Keep the mechanical hooks configured in `.claude/settings.json` enabled. They are part of the build-time enforcement path and are not replaced by these written instructions.

Security is organized under `security/`:

- `security/buildtime/` protects the coding assistant during development.
- `security/runtime/` protects the deployed AI application.
- `security/shared/` contains policy, reusable mechanisms and controls used by both layers.
