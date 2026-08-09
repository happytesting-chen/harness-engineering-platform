# AI Stack — Claims Agent (Build C)

> AI-development choices for the LLM extraction front-end. Authorized by the Build C
> amendment in `Context/claims-architecture.md` (human-approved 2026-08-04). Linked from
> CLAUDE.md Domain Context. The LLM extracts; the deterministic core decides.

## What the LLM does — and does NOT do

- **Does:** `extract(raw_email_text) -> claim record dict`. One stage IN FRONT of the
  unchanged deterministic core (`claims/validate → normalize → route → write`).
- **Does NOT:** decide. `claims/router.py:25` remains the sole decision authority. LLM output
  is untrusted data that must pass the existing `validate()` shape gate.
- **Proven seam (2026-08-04 stub probe):** faithful extraction → APPROVED; hallucinated field →
  UNKNOWN_FIELD/review; float amount → MALFORMED_AMOUNT/review; injection "set APPROVED" over a
  real shortfall → REJECTED. Core took ZERO edits.

## Agent framework

- **Choice:** minimal raw provider SDK (no orchestration layer).
- **Why:** extraction is a single structured-output call, not multi-agent or graph control flow.
  Fewest dependencies = smallest supply-chain surface (Security-kit/SECURITY.md §5).
- **Version pin:** <pin exact SDK version when the extractor is implemented — in-phase task>

## Model

- **Provider / model:** hosted provider via **AWS Bedrock**, **small/fast tier (Haiku-class)**.
- **Why this tier:** extraction is structured parsing, not deep reasoning → small model keeps
  cost + latency low. Escalate to a larger tier ONLY if measured extraction accuracy misses target.
- **Structured output:** force JSON matching `validate.py`'s allowed claim fields; `temperature=0`.
- **Pinned:** record the exact Bedrock model id at implementation; do not silently switch.

## Credential mode (decided)

- **Cloud IAM role / short-lived STS** — no long-lived static key.
- Egress: exactly one Bedrock host in `governance/mcp-allowlist.json` (see deployment.md).
- **PII crosses to the provider** → compliance review is a hard prerequisite (deployment.md).

## Tools the agent can call

| Tool | Purpose | In `governance/mcp-allowlist.json`? | Egress? |
|------|---------|-------------------------------------|---------|
| `claims_extractor` | email text → claim record (LLM, Bedrock) | to be added, gated_until phase-04 | one Bedrock host |
| `claims_runner` | existing deterministic runner | yes (gated_until phase-01) | none |

> The extractor tool + its egress host are NOT enabled yet. Enabling them is the first
> in-phase task under phase-04, gated by the compliance review.

## Key libraries / dependencies

- AWS SDK (boto3 / Bedrock runtime client) — <exact version pin at implementation>

## Open questions / decisions pending (for the compliance review)

- Which Bedrock region + exact small/fast model id.
- Data-processing agreement covering claim PII sent to Bedrock.
- Where the COVERAGE amount is looked up (trusted policy source) — MUST NOT come from the email.
