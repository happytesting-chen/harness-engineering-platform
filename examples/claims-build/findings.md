# Findings — Build B (LLM extraction) design

## Verified this session (live commands, not memory)

### Deterministic core is stable and correct
- `claims/` = 451 lines stdlib-only; pipeline `validate → normalize → route → write` (`claims/pipeline.py:23`).
- `router.py:25` is sole decision authority; no permissive fallback; defects → PENDING_REVIEW.
- `validate.py:89` never returns `expected` oracle → structurally can't reach routing.
- Live eval: accuracy 100% (7/7), reproducibility 100% (7/7), latency ~0.1ms, cost N/A. Reproduced this session.
- 2 `test_hooks` failures = EXPECTED (all phases passing → no active phase → gate fails closed). Documented, not a regression.

### Email test (proper-input request)
- Runner contract (`runner.py:9`): explicitly NO email; input is structured JSON claim record.
- Proper structured claim → APPROVED, exactly 1 file written.
- Raw email `.txt` → exit 2 (not valid JSON), fails closed — won't parse prose.
- Email-as-JSON-string → PENDING_REVIEW / MALFORMED_RECORD (shape gate holds).

### Build B seam probe (THE key result — scripted stub LLM, no tokens/key/egress)
Stub extractor feeds output verbatim into REAL unchanged `decide()`:

| Case | Outcome | Meaning |
|------|---------|---------|
| 1 faithful extraction | APPROVED / EXACT_COVERAGE | seam works, core unchanged |
| 2 LLM hallucinates extra field | PENDING_REVIEW / UNKNOWN_FIELD | core rejects malformed output |
| 3 LLM emits float not "480.00" | PENDING_REVIEW / MALFORMED_AMOUNT | type gate holds |
| 4 prompt injection "set APPROVED", real=shortfall | REJECTED / COVERAGE_SHORTFALL | injection text is data, ignored |
| 5 injection SUCCEEDS, LLM fakes covered==submitted | APPROVED / EXACT_COVERAGE | **the honest limit** |

**Case 5 = the load-bearing finding.** Deterministic core defends against *malformed*
LLM output but NOT a *plausibly-wrong* one. If the LLM lies about the numbers themselves
(structurally valid), the core has no ground truth to catch it. Drives Build B mitigations:
1. Coverage amount from trusted policy lookup, never from email (injection can't move a number it doesn't control).
2. `content_trust.py` screens email before it becomes prompt input.
3. Low-confidence / abstention → PENDING_REVIEW, never auto-approve.

## Template stages: same journey, LLM-specific content
- Init, fill, build, eval loop UNCHANGED.
- `Context/deployment.md` (data sensitivity) becomes load-bearing — decides credential/egress story.
- Eval cost column (was N/A by design) populates with real tokens/$; reproducibility axis measures the drop.
- API key is NOT a must: local model → no egress; IAM role → no static secret; static key = last resort, contained by secret_scan + egress + content_trust gates.
- Real risk = PII leaving boundary to a 3rd party, not the key itself. That's a deployment.md decision.

## ⚠ BLOCKER — signed contract prohibits LLM for Build B
- `Context/claims-architecture.md:36`: "Builds A and B may not invoke an LLM or provider,
  access a network or cloud service, use credentials, send email, deploy, mutate a live
  system, process production data, or trigger any external action."
- So "Build B = LLM extraction" **contradicts the governing contract**. Under it, Build B is
  still deterministic. An LLM build = a NEW capability (call it Build C) OR requires a
  human-approved amendment to the Prohibited Effects clause. Agent cannot self-redefine Build B.
- ALSO: templates reference stale paths `security/SECURITY.md` + `tools/mcp-allowlist.json`
  (now `Security-kit/` + `governance/`). Known template drift — note when filling.
- Decision for the drafts: produce them as **"Build C / contract-amendment proposal"**, every
  file marked contingent on human sign-off to lift the clause. Do NOT present as ready-to-run.

## Open questions for the human (init-project "Clarification Needed" style)
1. Model + framework? (Bedrock / Anthropic API / on-prem vLLM-Ollama; LangChain/Strands/raw SDK)
2. Deployment target + data sensitivity? (does claim PII leave the boundary?)
3. Where does the COVERAGE amount come from? (must be trusted policy source, not email — per case 5)
4. Eval oracle for extraction: do we have labeled email→record pairs?
