# Security Architecture

The Secure Template separates security into three explicit layers so developers and coding assistants can tell what protects development, what protects the deployed application, and what is reused by both.

```text
                 Product Requirements
                         |
                  Security Assessment
                         |
          +--------------+--------------+
          |              |              |
          v              v              v
     BUILD-TIME        SHARED         RUNTIME
      SECURITY        SECURITY        SECURITY
          |              |              |
          +--------------+--------------+
                         |
                    Verification
```

## Build-Time

`buildtime/` protects Claude Code and the development workflow. It contains coding-assistant-specific adapters such as prompt screening and secret scanning. Claude Code hook configuration remains in `.claude/settings.json` because Claude requires that location.

## Runtime

`runtime/` protects the deployed AI application. It contains the runtime dispatcher, runtime input screening, runtime host and the supporting runtime enforcement modules. Runtime protection only exists when the application is actually wired through these mechanisms.

## Shared

`shared/` contains security policy, reusable mechanisms, control definitions and security references consumed by both layers. Shared logic must not be copied independently into Build-Time and Runtime.

## Design rule

A product requirement may create both build-time and runtime controls. Separate the enforcement layers, but keep the security reasoning and common policy shared.

Example:

```text
Application needs external API access
            |
      Security assessment
            |
     +------+------+
     |             |
Build-time      Runtime
restriction     restriction
     |             |
     +------+------+
            |
       Shared policy
```

During migration, legacy `Security-kit/` and `governance/` paths may temporarily coexist with this structure. They should be removed only after imports, hooks, tests, protected paths and documentation have been switched to the new paths.