# Deployment Target — Claims Agent (Build C)

> Where and how the LLM extraction build runs. Authorized by the Build C amendment in
> `Context/claims-architecture.md` (2026-08-04). Kept consistent with
> `governance/mcp-allowlist.json` and `Security-kit/`.

## The decision that drives all others

**Does claim PII leave our boundary?** — **YES.** Decided credential mode is a hosted
provider (Bedrock via IAM role), so email text + extracted fields cross to AWS.
→ **A data-processing / compliance review is a HARD PREREQUISITE** before the extractor is
enabled or egress opens. Until that review passes, `egress_hosts` stays `[]`.

## Target

- **Environment:** public cloud — AWS (Bedrock for the model).
- **Why:** hosted small/fast model via IAM role, no local GPU infra to run.
- **Runtime:** <container / process — set at implementation>

## Data residency & boundaries

- **Where data lives:** local synthetic `SYN-*` fixtures; extraction calls send text to Bedrock.
- **What may leave:** email text + extracted claim fields → the one Bedrock host only.
- **Sensitive data classes:** PII (claimant), monetary. Synthetic only for now; production data
  remains prohibited even under Build C (Security-kit/SECURITY.md §3).

## Secrets & identity

- **Secret source:** none static. **AWS IAM role / short-lived STS creds** — no hardcoded key
  (`Security-kit/secret_scan.py` hook enforces; also blocks an accidental static key).
- **Agent identity:** the IAM role scoped to the single Bedrock model invoke action, least-privilege.

## Egress

- **Allowed outbound hosts:** `[]` **today**. On compliance sign-off, add **exactly one**:
  `bedrock-runtime.<region>.amazonaws.com` to `governance/mcp-allowlist.json` egress_hosts.
- **Default:** deny (`governance/permission.py:99` `check_egress` blocks unlisted hosts).
- This one-line change is an explicit, human-approved, auditable in-phase task — not done yet.

## Operational

- **Observability sink:** `Harness-Best-Practice/observability/audit.py` (append-only) — extend
  to record each extraction call (model id, latency, token usage) for the eval cost axis.
- **Rollback / kill switch:** revert `egress_hosts` to `[]` → extractor cannot reach Bedrock →
  input fails closed (unparseable → exit 2). The deterministic core keeps working without the LLM.

## New trust boundary introduced

- Untrusted email text → Bedrock prompt input = prompt-injection surface. Screen via
  `Security-kit/content_trust.py` BEFORE the text becomes a prompt. Dormant in A/B; active in C.
