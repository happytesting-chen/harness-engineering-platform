# OWASP → Template Mechanism Crosswalk

Maps the two OWASP AI risk lists to the specific harness mechanism that addresses each
risk, and states honestly where the template only *guides* (advisory) or leaves the
work to the **application** you build on top.

Legend for "How the template addresses it":
- **[MECH]** mechanical — an execution path enforces it AND a test proves it.
- **[GUIDE]** advisory — steering/context/docs shape behaviour; not mechanically enforced.
- **[APP]** the template gives the primitive/guidance, but enforcement lives in your agent code.
- **[GAP]** not addressed by the template; call it out in `control-matrix.md` per project.

Sources (verified 2026-08-03):
- OWASP Top 10 for LLM Applications — **v2025** ([genai.owasp.org/llm-top-10](https://genai.owasp.org/llm-top-10/))
- OWASP Top 10 for Agentic Applications — **2026** (ASI01–ASI10, published 2025-12-09;
  [genai.owasp.org](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/))

---

## OWASP Top 10 for LLM Applications (2025)

| ID | Risk | How the template addresses it | Where |
|----|------|-------------------------------|-------|
| LLM01 | Prompt Injection | **[MECH]** data-plane screening drops injected control fields + flags instruction-shaped text; **[GUIDE]** input-trust rules | `governance/content_trust.py`, `tests/test_content_trust.py`, `context/SECURITY.md` S1.4 |
| LLM02 | Sensitive Information Disclosure | **[MECH]** secret-block hook on writes; **[MECH]** egress default-deny; **[GUIDE]** output-safety rules | `governance/secret_scan.py`, `permission.py` Gate 3, `context/SECURITY.md` §4 |
| LLM03 | Supply Chain | **[MECH]** tool allowlist with pinned versions + phase-gate on unregistered tools; **[GUIDE]** pin deps | `tools/mcp-allowlist.json`, `permission.py` Gate 2, `context/SECURITY.md` §5 |
| LLM04 | Data and Model Poisoning | **[APP]** treat context files as untrusted / verify consistency; **[GAP]** no training-data controls (out of scope for a local agent harness) | `context/SECURITY.md` S1.3; declare residual risk in `control-matrix.md` |
| LLM05 | Improper Output Handling | **[MECH]** content_trust screens tool/return content before use; **[GUIDE]** validate tool output | `governance/content_trust.py`, `context/SECURITY.md` S1.1, S5.4 |
| LLM06 | Excessive Agency | **[MECH]** phase-gate (tools locked until prerequisite phase passes) + WIP=1 + human sign-off; deny-list | `permission.py` Gate 2, `feature_list.json`, `CLAUDE.md` working rules |
| LLM07 | System Prompt Leakage | **[GUIDE]** don't expose gate internals/deny-list/audit; **[APP]** keep secrets out of prompts | `context/SECURITY.md` S4.3; `kiro/steering/security.md` output-safety |
| LLM08 | Vector & Embedding Weaknesses | **[GAP]** no RAG/vector store in the base template | Declare N/A or add controls in `control-matrix.md` if you add retrieval |
| LLM09 | Misinformation | **[APP]** independent verification pattern + human review on low confidence; **[GUIDE]** don't over-rely on tool output | `context/SECURITY.md` S5.4; your phase `verification` command |
| LLM10 | Unbounded Consumption | **[MECH/APP]** `max_turns` cap in the agent loop; **[GUIDE]** budget caps, 3-strike stop | `demo/harness.py` max_turns, `context/SECURITY.md` §7 |

---

## OWASP Top 10 for Agentic Applications (2026, ASI01–ASI10)

| ID | Risk | How the template addresses it | Where |
|----|------|-------------------------------|-------|
| ASI01 | Agent Goal Hijack | **[MECH]** content_trust flags instruction-shaped text in untrusted input → route to human; **[GUIDE]** claim/content is DATA not commands | `governance/content_trust.py`, `context/SECURITY.md` S1.4 |
| ASI02 | Tool Misuse & Exploitation | **[MECH]** tool allowlist + phase-gate + deny-list on dangerous commands | `tools/mcp-allowlist.json`, `governance/permission.py` Gates 1–2 |
| ASI03 | Identity & Privilege Abuse | **[MECH]** least-privilege via per-phase tool gating; **[GUIDE]** short-lived scoped creds; **[GAP]** no identity broker (deployment concern) | `permission.py` Gate 2, `context/SECURITY.md` S2.4–S2.5 |
| ASI04 | Agentic Supply Chain Vulnerabilities | **[MECH]** version-pinned allowlist, human approval for new tools; **[GUIDE]** exact dep pins | `tools/mcp-allowlist.json`, `context/SECURITY.md` §5 |
| ASI05 | Unexpected Code Execution (RCE) | **[MECH]** deny-list blocks destructive/exec patterns (word/regex modes); egress default-deny | `governance/deny-list.json`, `permission.py` Gates 1 & 3 |
| ASI06 | Memory & Context Poisoning | **[MECH/APP]** treat `progress.md`/`feature_list.json` as tamperable — verify consistency; content_trust on stored content | `context/SECURITY.md` S1.3, `governance/content_trust.py` |
| ASI07 | Insecure Inter-Agent Communication | **[GAP]** base template is single-agent | Declare N/A; add controls in `control-matrix.md` if you add multi-agent |
| ASI08 | Cascading Failures | **[MECH/APP]** fail-closed gates + 3-strike stop + `max_turns`; human sign-off between phases | `permission.py` (fail-closed), `CLAUDE.md` escalation, `context/SECURITY.md` §7 |
| ASI09 | Human-Agent Trust Exploitation | **[MECH]** three human-in-the-loop checkpoints (phase sign-off, escalation, policy update); append-only audit | `feature_list.json` sign-off, `observability/audit.py`, `context/SECURITY.md` §6 |
| ASI10 | Rogue Agents | **[MECH]** append-only audit trail + agent cannot modify its own governance files; **[GUIDE]** review audit for drift | `observability/audit.py`, `governance/` (immutable per policy), `context/SECURITY.md` S6.4–S6.5 |

---

## How to use this crosswalk

1. For each risk **relevant to your agent**, confirm the cited mechanism exists and its
   test passes (`./init.sh` gates on the enforcement proofs).
2. For every **[APP]** row, implement the control in your agent code and add a row to
   `security/control-matrix.md` linking it to a verification.
3. For every **[GAP]** / **N/A** row, record the decision (not applicable, or accepted
   residual risk) in `control-matrix.md` — an unstated gap is an unmanaged risk.
4. Re-verify after any change that adds a tool, an external call, retrieval, multi-agent
   messaging, or a new data flow — those change which rows apply.

> A row is only **[MECH]** when an execution path enforces it *and* a test proves that
> path. Everything else is guidance or your responsibility to implement.
