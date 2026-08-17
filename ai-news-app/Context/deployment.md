# Deployment Target — AI News Runtime Security Demo

## Target

- **Environment:** local development/testing first.
- **Runtime:** local Python process running Streamlit.
- **Next target:** deployment choice remains open until local runtime controls pass evaluation.

## Data residency & boundaries

- News content is public external data.
- Outbound access is limited by the project `governance/mcp-allowlist.json`.
- No real credentials may be placed in prompts, tool arguments, logs, or repository files.

## Secrets & identity

- **Secret source:** local environment variable `ANTHROPIC_API_KEY`.
- Never hardcode or commit the key.

## Egress

- Allowed: `thehackernews.com`, `github.com`, `api.github.com`, `techcrunch.com` plus localhost for local testing.
- Default: deny.

## Operational

- Audit events are written to the project's runtime audit log during local testing.
- Stop the Streamlit process to stop the local agent.
