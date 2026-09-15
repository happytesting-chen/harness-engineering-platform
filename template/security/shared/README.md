# Shared Security

Shared security contains policy, mechanisms, and security references that are used by both build-time and runtime protection.

## Rule

Do not duplicate shared policy or enforcement logic in the build-time and runtime layers. Both layers should consume the same shared implementation.

## Migrated components

- `permission.py` — common permission / four-gate enforcement logic
- `deny-list.json` — common deny policy
- `mcp-allowlist.json` — approved tools, phases, and egress policy
- `ARCHITECTURE.md` — common governance architecture
- `SECURITY.md` — detailed security guidance
- `SECURITY-MANIFEST.md` — security control manifest
- `active-controls.md` — controls selected for the current project
- `control-matrix.md` — control-to-mechanism mapping
- `requirements.json` — security requirements catalogue
- `mechanisms.json` — mechanism catalogue
- `coverage.schema.md` and `check_coverage.py` — coverage model and verification
- `owasp-crosswalk.md` — framework crosswalk
- `content_trust.py` — reusable untrusted-content handling
- `result_screen.py` — reusable result screening

Build-time and runtime adapters may call these shared components, but should not reimplement them.