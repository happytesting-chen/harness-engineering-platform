# Build-Time Security

Build-time security protects the coding assistant and development workflow while the application is being created.

## Components

- `prompt_screen.py` — screens coding-assistant input before it reaches the model
- `secret_scan.py` — detects secret leakage during development
- `.claude/settings.json` — Claude Code hook wiring (kept at project root because Claude Code requires it there)

Build-time adapters consume policy and reusable enforcement from `../shared/`. They must not maintain separate copies of shared policy.

Build-time protection ends with the development environment. It must never be presented as protection for the deployed application.