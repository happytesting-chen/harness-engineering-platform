# runtime-security-mvp — limitations

Every disabled or untested capability, named. A limitation stated here is a managed
risk; one omitted is an incident waiting to be named. This file is part of the evidence
the release verdict is scoped to.

## Disabled by design — a startup error, not a gap to close later

Enabling any of these is a new source or sink and requires a separately approved plan
(plan §7). `runtime/startup.py` refuses to start if any is on.

- **Persistent / cross-session memory** — the agent keeps no state between sessions.
- **Delegation / inter-agent messaging / subagent spawning** — single agent only.
- **Arbitrary binary extraction** (PDF, image, archive) — UTF-8 text ingress only.
- **Multiple hosts** — one owned host.
- **Streaming output** — the final response is buffered; a streamed release could emit a
  secret's prefix before the redactor saw its suffix.
- **Remote / hosted classifiers** — the classifier is a pinned local process.

## Detection limits — measured, not assumed

- **The classifier is confidently wrong on workflow-impersonation attacks.** Measured
  (classifier-selection.md): `atk-008` (recon framed as a compliance ask, `data` @ 0.89)
  and `atk-010` (fetch-URL indirect injection, `data` @ 0.95). Threshold tuning cannot
  fix a confident miss without flooding review. These are admitted into context and stopped,
  if at all, only by the action gate and output screen downstream (R-1).
- **Detection is patterns + one encoder, not provenance.** A paraphrase outside both the
  24 markers and the classifier's training distribution passes ingress. The origin label
  travels with the content, but understanding *intent* from text alone is bounded.
- **False positives on security discussion.** `leg-004..006`: text that quotes or
  describes injection is withheld. Recoverable by review receipt; a cost, not a breach.

## Residuals carried from the plan

- **R-1 — the classifier is the content-release authority.** For rule-clean content, the
  classifier's `data` label is the only thing between the content and the model. A fooled
  classifier admits content; the deterministic action gate is then the sole control. The
  `classifier-false-negative` attack case exists to prove that gate holds, permanently.
- **R-2 — review-queue flooding.** Fail-closed ingress routes every timeout, unresolved
  and false positive to human review. An attacker who cannot inject can still exhaust
  reviewer attention. The deployment must state a queue bound or accept the risk with an
  owner; the MVP does not bound it in code.
- **R-3 — the semantic tier is deployed-profile only.** IDE / build-time hook screening
  stays regex-only (latency; hook crash semantics). "Semantic enforcement" is a claim
  about the runtime-mvp profile, not about an IDE session.
- **SEC-RUNTIME-GAP-001 — wiring is opt-in.** The modules exist and are tested; nothing
  forces a deployed application to route through the host. Routing is a per-deployment
  architecture-review item, not a mechanical guarantee.

## Not established by this work

No verdict from this evidence covers: model-weight robustness, operating-system
confinement or sandboxing, the disabled capabilities above, deployments without the
required read-only control plane, or resistance to attack classes outside the 13-case
matrix. The matrix is a floor, not a ceiling — absence of a case is not evidence of
resistance.
