# AI Stack — AI News Runtime Security Demo

> Project-specific copy of `ai-stack.md.template`.

## Agent framework

- **Choice:** Strands Agents (Python)
- **Why:** its explicit tool lifecycle provides a clean first integration point for the runtime harness while the harness controls remain framework-independent.
- **Version pin:** pin the exact tested version when the local environment is installed and verified.

## Model

- **Provider / model:** Claude via Anthropic API.
- **Why this tier:** suitable tool-use and summarisation capability for the reference application.
- **Fallback / secondary:** none for v1.
- **Pinned:** exact Claude model ID will be recorded before runtime verification.
- **Credential:** `ANTHROPIC_API_KEY` must come from the runtime environment; never commit a real key.

## Tools the agent can call

| Tool | Purpose | In `governance/mcp-allowlist.json`? | Egress? |
|------|---------|-------------------------------------|---------|
| `fetch_news` | Fetch an approved news article/page | yes | approved source host |
| `get_trending_repos` | Retrieve recent high-interest GitHub repositories | yes | `api.github.com` |
| `save_digest` | Save the generated digest locally | yes | none |
| `send_digest_email` | Optional later secret-protection demo | no in v1 | TBD |

Summarisation is an LLM reasoning step, not a separate tool.

## Primary external sources

- The Hacker News — `thehackernews.com`
- GitHub — `github.com`, `api.github.com`
- TechCrunch — `techcrunch.com`

Only add supporting hosts when implementation genuinely requires them.

## UI

- **Choice:** Streamlit.
- One page: digest/chat on the left, runtime-security status/events on the right, expandable audit trail below.

## Runtime security path

```text
Strands Agent
     ↓
runtime interception / adapter
     ↓
permission.py + secret check
     ↓
real tool handler
     ↓
external/untrusted result
     ↓
content_trust.py
     ↓
model context
```

All runtime security decisions/events are recorded through the existing audit mechanism. No real tool handler may have an alternate agent-callable bypass path.

## Key libraries / dependencies

- `strands-agents` — agent framework — exact version to pin after local verification.
- `streamlit` — local web UI — exact version to pin after local verification.
- Anthropic model integration required by Strands — exact dependency/version to pin after local verification.

## Open questions / decisions pending

- Exact Claude model ID after local API verification.
- Whether to enable `send_digest_email` after the core runtime controls pass.
- Production deployment target after local evaluation passes.
