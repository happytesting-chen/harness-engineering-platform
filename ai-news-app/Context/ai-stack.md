# AI Stack — AI News Runtime Security Demo

## Agent framework

- **Choice:** Strands Agents (Python)
- **Why:** explicit tool lifecycle interception maps cleanly to the runtime harness while keeping the harness itself framework-independent.
- **Version pin:** pin when dependencies are installed and verified locally.

## Model

- **Provider / model:** Claude via Anthropic API
- **Why this tier:** strong tool-use and summarisation capability for the reference application.
- **Credential:** `ANTHROPIC_API_KEY` from the runtime environment only.
- **Pinned:** model ID will be explicitly configured before runtime verification.

## Tools the agent can call

| Tool | Purpose | Allowlisted? | Egress? |
|---|---|---|---|
| `fetch_news` | Fetch approved news content | yes | approved source host |
| `get_trending_repos` | Retrieve recent high-interest GitHub repositories | yes | `api.github.com` |
| `save_digest` | Save digest locally | yes | none |
| `send_digest_email` | Optional secret-protection demo | not enabled in v1 | TBD |

## Primary external sources

- `thehackernews.com`
- `github.com` / `api.github.com`
- `techcrunch.com`

## UI

- Streamlit one-page interface.
- Left: digest and chat.
- Right: runtime protection status and latest security events.
- Bottom: expandable audit trail.

## Runtime security acceptance criteria

- Approved tool + destination -> ALLOW and handler executes.
- Unapproved destination -> DENY and network handler execution count remains zero.
- Tool absent from allowlist -> DENY and handler execution count remains zero.
- Suspicious external content -> detected and prevented from unsafe onward use.
- Fake test credential in outbound arguments -> BLOCK and handler execution count remains zero.
- Allowed, denied, suspicious, and blocked events are traceable in the audit log.
