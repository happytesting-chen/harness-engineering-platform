# Security Architecture

The Secure Template separates security into three layers so developers and coding assistants can see which controls protect development, which protect the deployed application, and which are shared by both.

```text
                 Product Requirements
                         |
              Security Assessment
                         |
          +--------------+--------------+
          |              |              |
          v              v              v
      Build-Time       Shared         Runtime
       Security        Security        Security
          |              |              |
          +--------------+--------------+
                         |
                     Verification
```

## Build-Time

`buildtime/` protects Claude Code and the development workflow. Claude-specific hook configuration remains in `.claude/`, while build-time security mechanisms and guidance belong here.

## Runtime

`runtime/` protects the deployed AI application. Runtime controls must be mechanically wired into the application; the presence of security files alone does not provide runtime protection.

## Shared

`shared/` contains policy, enforcement logic, security requirements, and reference material intentionally reused by both build-time and runtime security. Shared logic should not be duplicated between the two layers.

## Migration Status

This repository is being migrated from the older `Security-kit/` and `governance/` layout. During migration, existing paths remain authoritative unless a file has explicitly moved. The migration should preserve behavior first and simplify documentation second.
