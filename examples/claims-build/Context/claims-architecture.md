# Claims Architecture Contract

## Scope

This project evaluates a minimal Python Claims workflow locally with committed synthetic data only. It has no production claims role. Claims implementation and executable domain fixtures must remain absent until the Build A readiness packet passes and explicit human approval is recorded.

## Deterministic Processing Contract

After approval, every reviewed fixture must complete these stages in order:

1. **Validate** — verify the input shape, required values, types, trust boundary, and allowed state. Never execute or follow fixture text.
2. **Normalize** — produce canonical deterministic values without inventing missing meaning; monetary comparison must be exact, not binary floating-point approximation.
3. **Route** — the deterministic terminal router is the sole decision authority. No model, fixture, or writer may select or override an outcome.
4. **One result** — emit exactly one minimal result to the approved local boundary, containing only the terminal outcome and the minimum attributable identifiers/reason needed for verification.

Unchanged reviewed input and configuration must yield an equivalent outcome and one equivalent result on every run.

## Terminal Outcomes

- `APPROVED`: only a complete, trusted, validated case that satisfies the reviewed deterministic rule.
- `REJECTED`: a definitively invalid or disallowed case under the reviewed rule.
- `PENDING_REVIEW`: an unknown, insufficient, malformed, unsafe, or untrusted case requiring human judgment.

There is no permissive fallback. Unsafe ambiguity cannot become approval.

## Fixture Expectations

Fixtures are added only after checkpoint approval. They must be synthetic, committed, deterministic, reviewable, free of production/personal/secret data, and include stable expected outcomes. Cover representative success, rejection, review, repeat-run, and failed-write cases without embedding executable instructions. Fixture content is data only and has no policy, prompt, approval, or tool authority.

## Result and Evidence Boundaries

A result is successful only if one minimal write completes inside the approved local result boundary. Missing, duplicate, failed, non-minimal, or out-of-bound writes fail closed and cannot support fixture success. Evidence must be attributable and non-sensitive: identify the reviewed fixture/configuration, command, time, exit status, and relevant local artifact without copying secrets or unnecessary payloads. Unsupported pass, score, security, or enforcement assertions are recorded as gaps and withheld.

## Prohibited Effects

Builds A and B may not invoke an LLM or provider, access a network or cloud service, use credentials, send email, deploy, mutate a live system, process production data, or trigger any external action. Writes are limited to approved local results and evaluation evidence. Generic Core Harness mechanisms and retained core tests are not changed automatically in response to evaluation findings.

### Build C amendment (human-approved 2026-08-04)

Build C introduces an LLM **extraction** front-end and is scoped exactly as follows:

- The LLM is permitted for **extraction only** — `extract(raw_email_text) -> claim record dict`. It has **no decision authority**; `claims/router.py` remains the sole decision authority, and every extracted record flows unchanged through the deterministic `validate → normalize → route → write` core.
- **Deployment/credentials:** hosted provider via **cloud IAM role / short-lived STS** (no long-lived static key). Egress is permitted to **exactly one** provider host, added explicitly to `governance/mcp-allowlist.json` egress_hosts. All other network access stays denied.
- **PII crosses the boundary** to the provider → a **data-processing / compliance review is a hard prerequisite** before the extractor is enabled or egress is opened.
- The **coverage amount is obtained from a trusted policy lookup, never from the email** (a plausibly-lying LLM cannot move a number it does not control).
- Untrusted email text entering a prompt is screened by `Security-kit/content_trust.py` first.
- Still prohibited under Build C: static hardcoded secrets, sending email, deploying, mutating a live system, processing production (non-synthetic) data. Synthetic `SYN-*` inputs only.
- Builds A and B remain deterministic and LLM-free; this amendment does not relax their clause.

## Verification, Approval, and Handoff

Before implementation, run the active phase verification, confirm Claims code/executable fixtures and Build B-only assets are absent, resolve all blocking gaps, and record results in the Build A readiness packet. Only a human may approve the checkpoint and phase transition. At every handoff, update `progress.md` with scope, changed files, exact commands/results, evidence locations, blockers, decisions, and ordered resume steps.