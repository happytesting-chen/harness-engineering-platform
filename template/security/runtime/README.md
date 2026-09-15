# Runtime Security

Runtime security protects the deployed AI application after development.

## Components

- `runtime_dispatcher.py` — governed runtime tool chokepoint
- `runtime_screen.py` — deployed input screening adapter
- `core/` — runtime host, ingress, classifier, contracts, audit, review, output, session, startup and related runtime modules

Runtime components consume common policy and reusable enforcement from `../shared/`.

## Required integration invariant

Every deployed tool invocation must reach the real callable through the governed runtime path. Application code must not retain a raw callable path that bypasses runtime authorization.

Having these files in a project is not sufficient by itself. The deployed application must mechanically wire its model/tool execution through this runtime layer.