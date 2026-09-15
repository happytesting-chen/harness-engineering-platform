# Build-Time Security

Build-time security protects Claude Code and the development process while the application is being created.

Typical responsibilities include:

- Claude Code hook enforcement
- protection of governance and security mechanism files
- development-time tool restrictions
- development-time egress restrictions
- prompt and tool-result screening for the coding assistant
- secret scanning during development
- phase and workflow gates

Claude-specific hook configuration remains under `.claude/` because it is part of the Claude Code integration surface.

Build-time controls may consume policy and enforcement logic from `../shared/`. Do not create a second copy of shared policy solely for build-time use.
