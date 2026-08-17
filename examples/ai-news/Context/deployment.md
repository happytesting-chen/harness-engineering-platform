# Deployment Target — AI News Runtime Security Demo

> Project-specific copy of `deployment.md.template`.

## Target

- **Environment:** local development and runtime verification first.
- **Runtime:** local Python process running Streamlit.
- **Region / residency:** local test environment; production target not selected yet.
- **Network model:** outbound internet access is default-deny at the application permission layer and limited to approved hosts.

## Identity & access

- **Service identity:** local developer process for v1.
- **Human access:** local user running the Streamlit application.
- **Authentication:** no multi-user authentication in v1; do not expose the local demo publicly.

## Secrets

- **Secret source:** local environment variable `ANTHROPIC_API_KEY`.
- Never hardcode, print, log, or commit the real API key.
- Runtime outbound/write-capable tool inputs must pass the runtime secret check before execution.

## Data

- **External data:** public news pages and public GitHub repository metadata.
- External content is untrusted data and must pass `Security-kit/content_trust.py` before being added back to model context.
- **Persistence:** generated digest may be stored locally; runtime audit events are stored in the project audit log.

## Egress

Default deny.

Approved application destinations for v1:

- `thehackernews.com`
- `github.com`
- `api.github.com`
- `techcrunch.com`
- `localhost` / `127.0.0.1` for local testing where required

Additional hosts require an explicit project policy change.

## Observability

- Runtime tool permission, egress, content-trust, and secret-protection decisions must be auditable.
- Evaluation must verify that denied handlers do not execute, rather than checking only the returned decision string.

## Deployment decisions pending

- Production hosting platform.
- Production identity/authentication model.
- Production secret manager.
- Production audit/log retention.
