# Build C (LLM extraction) — Phase Proposal

> ⚠ **PROPOSAL ONLY — not inserted into `feature_list.json`.** Adding this phase
> requires a human to first **amend `Context/claims-architecture.md:36`** (the clause
> banning LLM/provider/network/credentials for Builds A **and** B). The agent does not
> lift that clause or self-transition. This is the `init → context → fill → build → eval`
> journey instantiated for an LLM build — same template, LLM-specific content.

## Prerequisite (human, before any of this)

1. Amend the Prohibited Effects clause to permit a scoped LLM call (or explicitly define
   "Build C" as the LLM capability, leaving A/B deterministic).
2. Fill `Context/ai-stack.md` + `Context/deployment.md` from the `.proposed` drafts —
   answering the credential-mode and PII-boundary questions.
3. Only then add the phase below with `status: active` and sign off.

## Why "Build C", not "Build B"

`Context/claims-architecture.md` names both A and B as deterministic and LLM-free. So the
LLM build is a NEW capability, not a redefinition of B. Keeping it as C preserves the signed
contract's meaning and the audit trail.

## Proposed phase entry (for feature_list.json — DO NOT paste live yet)

```json
{
  "id": "phase-04",
  "name": "Build C — LLM extraction front-end",
  "behavior": "After a human lifts the LLM ban and fills ai-stack.md/deployment.md, an extract() stage turns raw email text into a claim record dict, which flows UNCHANGED through validate -> normalize -> route -> write. The LLM proposes; the deterministic router disposes. Malformed extraction -> PENDING_REVIEW; the coverage amount comes from a trusted policy lookup, never the email.",
  "dependencies": ["phase-03"],
  "status": "not-started",
  "verification": "./init.sh && python3 -m pytest tests claims/tests extraction/tests -v && python3 evaluation/eval.py --snapshot evaluation/build-c",
  "evidence": ""
}
```

## Acceptance criteria (what verification must prove)

1. **Core unchanged** — `claims/` diff is empty; the LLM plugs into the existing seam.
2. **Extraction output is untrusted** — a hallucinated/malformed record → PENDING_REVIEW, proven by test.
3. **Coverage-from-policy** — the covered amount is looked up deterministically, NOT taken from
   the email (mitigates the case-5 finding: core can't catch a plausibly-lying LLM about numbers).
4. **Content-trust active** — email text screened by `Security-kit/content_trust.py` before prompting.
5. **Egress explicit** — either `egress_hosts: []` (local model) or exactly one provider host, human-approved.
6. **Eval populated honestly** — cost flips N/A → real tokens/$; reproducibility axis MEASURES the drop
   below 100% (do not assume it away); accuracy scored against labeled email→record oracle pairs.

## What the eval will finally show (the payoff)

| Axis | Build A (deterministic) | Build C (LLM) |
|------|-------------------------|---------------|
| Accuracy | 100% (7/7) | measured vs email→record oracle |
| Reproducibility | 100% | <100%, quantified per fixture |
| Latency | ~0.1 ms | real model latency |
| Cost | **N/A** (honest) | **real tokens/$** — the column this was built for |

## Scope discipline

- Planning artifacts only in this session. No LLM code, no key, no egress change, no phase inserted.
- Deterministic core stays the authority; the human-in-the-loop (PENDING_REVIEW) is the safety net
  the case-5 finding shows is irreducible.
