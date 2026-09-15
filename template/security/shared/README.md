# Shared Security

Shared security contains policy, enforcement logic, and security knowledge intentionally reused by both build-time and runtime protection.

The design rule is:

> If build-time and runtime require the same policy or decision logic, keep one authoritative implementation here and let both layers consume it.

Likely shared components from the current layout include the common permission engine, tool and egress policy, deny policy, security requirements, control mapping, mechanism mapping, and common security architecture documentation.

Do not duplicate shared gate logic in `buildtime/` and `runtime/`. A second implementation is a second security boundary that can drift.
