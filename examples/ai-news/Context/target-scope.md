# Target Scope — AI News Runtime Security Demo

## Purpose

Build a small but real AI application that demonstrates that runtime security controls remain active after development, when the deployed/running agent invokes tools and consumes external content.

## Application scope

- Focus: AI, cybersecurity, and fast-moving developer/open-source trends.
- Produce a daily digest of approximately 5–8 important stories.
- Each story should include headline, source, short summary, why it matters, and original URL.
- Provide chatbot follow-up over the collected news context.
- Primary sources: The Hacker News, GitHub, and TechCrunch.

## In scope

- Fetching content from explicitly approved external destinations.
- Finding recent/high-interest AI, security, and developer repositories on GitHub.
- LLM summarisation and prioritisation of screened external content.
- Saving a digest locally.
- Streamlit UI for the digest/chat and visible runtime-security events.
- Runtime tool permission enforcement.
- Runtime egress destination enforcement.
- Runtime external-content trust screening.
- Runtime secret protection before outbound/write-capable execution.
- Runtime audit logging.
- Integration/evaluation tests that verify the real handler did or did not execute.

## Out of scope for v1

- Unrestricted web browsing or arbitrary URL crawling.
- Automatically expanding the egress allowlist.
- Autonomous social-media posting.
- Destructive tools or administrative system operations.
- Real email sending until the core controls pass; `send_digest_email` is optional later.
- Production/public internet deployment.
- A dedicated prompt-injection prevention layer beyond the current external-content trust control.

## Runtime security acceptance criteria

| ID | Scenario | Expected result | Required evidence |
|----|----------|-----------------|------------------|
| E01 | Approved tool and approved destination | `ALLOW` | real handler executes; successful audit trace exists |
| E02 | Approved network tool with unapproved destination | `DENY` | network handler execution count = 0; denied audit trace exists |
| E03 | Tool absent from runtime allowlist | `DENY` | tool handler execution count = 0; denied audit trace exists |
| E04 | Approved source returns instruction-shaped malicious content | `SUSPICIOUS` and unsafe onward use prevented | content-trust event exists; raw suspicious content is not passed onward unchanged |
| E05 | Outbound/write-capable tool input contains a fake test credential | `BLOCK` | real outbound handler execution count = 0; secret-protection event exists |
| E06 | Normal successful end-to-end run | successful | expected allowed/executed events are traceable in audit log |

## Security boundary

The agent/model must not be the security authority. Runtime enforcement occurs outside model reasoning on the actual tool execution path. A model instruction to use a tool or destination does not override the project runtime policy.
