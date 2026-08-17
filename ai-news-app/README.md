# AI News Runtime Security Demo

Project-specific reference application built using the harness template. The generic files under `template/` remain reusable and are not modified for application-specific choices.

## Scope

- AI + cybersecurity + fast-moving open-source news
- Primary sources: The Hacker News, GitHub, TechCrunch
- Daily 5–8 story digest plus chatbot follow-up
- Streamlit UI
- Strands Agents (Python) with Claude via Anthropic API

## Runtime security

Every real tool execution must pass through the copied runtime harness before the handler runs. External tool output is screened before it returns to model context. Runtime decisions are audited.

## Local secret

Set `ANTHROPIC_API_KEY` in the local runtime environment. Never commit the real key.
