# OWASP → Template Mechanism Crosswalk

Maps the two OWASP AI risk lists to the specific harness mechanism that addresses each
risk, and states honestly where the template only *guides* (advisory) or leaves the
work to the **application** you build on top.

Legend for "How the template addresses it":
- **[MECH]** mechanical — an execution path enforces it AND a test proves it.
- **[LIB]** the code exists and is tested, but **nothing calls it** — no execution path, so
  by the `[MECH]` definition above it is not yet a control. Remediation is a *wire-up*, not
  a build.
- **[GUIDE]** advisory — steering/context/docs shape behaviour; not mechanically enforced.
- **[APP]** the template gives the primitive/guidance, but enforcement lives in your agent code.
- **[GAP]** not addressed by the template; call it out in `control-matrix.md` per project.

> ### ⚠ Read this before using the ASI table as evidence of coverage
>
> **The template covers the risks a normal API gateway would catch, at ONE point in the
> loop.** Every enforced control lives at the *tool-call proposal* boundary — the
> PreToolUse hook into `governance/permission.py`. Measured, there are five positions in
> an agent loop and four of them have no preventive control:
>
> ```
>   ① prompt ─────────▶ ✗ nothing wired  UserPromptSubmit exists and CAN block
>                                         (exit 2 erases the prompt) — unused here
>   ② proposal ───────▶ ★ 4 GATES        ← the ONLY enforced boundary
>   ③ tool runs ──────▶ side effect happens
>   ④ result → LLM ───▶ ✗ nothing CAN    PostToolUse cannot block per the docs;
>   │                     block here      audit_hook.py logs, always exit 0
>   └─ ⑤ loop back to ② ▶ ✗ stateless    the gate has no memory across turns
> ```
>
> ① and ④ are different gaps: ① is an **attach point we never used**, ④ has **no blocking
> event at all**, so screening there must live inside the code that reads the content.
>
> The consequence is structural, not a to-do list. Gate ② is a **stateless per-call
> check**, so it is blind by construction to anything that lives in the *sequence*:
> twenty $500 refunds each pass identically; content injected at ④ gets a fresh,
> fully-authorised attempt at ② on every iteration.
>
> So the **agent-specific** half of the ASI list is addressed **by design, not by
> implementation**. The mechanisms for it (origin labelling, session-cumulative state,
> delegation narrowing, memory-write gating) are specified in
> `docs/superpowers/specs/2026-08-04-runtime-tool-mediation-design.md` §4 as A1–A5 and
> **none of them are built**. Do not read a `[MECH]` tag on a G-tier row as coverage of
> the agentic risk it sits next to.
>
> Verified by reading source and driving the live hook on 2026-08-10.

Sources (verified 2026-08-03):
- OWASP Top 10 for LLM Applications — **v2025** ([genai.owasp.org/llm-top-10](https://genai.owasp.org/llm-top-10/))
- OWASP Top 10 for Agentic Applications — **2026** (ASI01–ASI10, published 2025-12-09;
  [genai.owasp.org](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/))

---

## OWASP Top 10 for LLM Applications (2025)

| ID | Risk | How the template addresses it | Where |
|----|------|-------------------------------|-------|
| LLM01 | Prompt Injection | **[LIB]** `content_trust.py` would drop injected control fields + flag instruction-shaped text — but no execution path calls it, and there is no prompt-entry hook; **[GUIDE]** input-trust rules. Even wired it is `[OBS]`: a paraphrase defeats a regex | `Security-kit/content_trust.py` (**unwired**), `tests/test_content_trust.py`, `Security-kit/SECURITY.md` S1.4 |
| LLM02 | Sensitive Information Disclosure | **[MECH]** secret-block hook on writes; **[MECH]** egress default-deny; **[GUIDE]** output-safety rules | `Security-kit/secret_scan.py`, `permission.py` Gate 3, `Security-kit/SECURITY.md` §4 |
| LLM03 | Supply Chain | **[MECH]** allowlist membership — an unregistered tool fails closed (`check_phase_gate` returns `not in allowlist`); **[GUIDE]** the `version` field is *declarative only* — `permission.py` never reads it, so nothing rejects a version drift; **[GUIDE]** pin deps | `governance/mcp-allowlist.json`, `permission.py` `check_phase_gate`, `Security-kit/SECURITY.md` §5 |
| LLM04 | Data and Model Poisoning | **[APP]** treat context files as untrusted / verify consistency; **[GAP]** no training-data controls (out of scope for a local agent harness) | `Security-kit/SECURITY.md` S1.3; declare residual risk in `control-matrix.md` |
| LLM05 | Improper Output Handling | **[LIB]** `content_trust.py` can screen tool output — but nothing calls it, and no hook *can* prevent at position ④ — `PostToolUse` is the only event there and cannot veto (it fires after the side effect; `audit_hook.py` logs and always exits 0). Screening has to happen inside the code that reads the content, which is exactly the call nobody makes; **[GUIDE]** validate tool output | `Security-kit/content_trust.py` (**unwired**), `Harness-Best-Practice/observability/audit_hook.py`, `Security-kit/SECURITY.md` S1.1, S5.4 |
| LLM06 | Excessive Agency | **[MECH]** phase-gate (tools locked until prerequisite phase passes) + WIP=1 + human sign-off; deny-list | `permission.py` Gate 2, `feature_list.json`, `CLAUDE.md` working rules |
| LLM07 | System Prompt Leakage | **[GUIDE]** don't expose gate internals/deny-list/audit; **[APP]** keep secrets out of prompts | `Security-kit/SECURITY.md` S4.3; `kiro/steering/security.md` output-safety |
| LLM08 | Vector & Embedding Weaknesses | **[GAP]** no RAG/vector store in the base template | Declare N/A or add controls in `control-matrix.md` if you add retrieval |
| LLM09 | Misinformation | **[APP]** independent verification pattern + human review on low confidence; **[GUIDE]** don't over-rely on tool output | `Security-kit/SECURITY.md` S5.4; your phase `verification` command |
| LLM10 | Unbounded Consumption | **[APP]** `max_turns` exists only in `demo/harness.py:47` — and `demo/ARCHITECTURE.md:3` states the demo is **NOT the production enforcement path**. Nothing caps turns, tokens or cost on the real path; the loop belongs to Claude Code; **[GUIDE]** budget caps, 3-strike stop | `demo/harness.py:47` (demo only), `Security-kit/SECURITY.md` §7 |

---

## OWASP Top 10 for Agentic Applications (2026, ASI01–ASI10)

| ID | Risk | How the template addresses it | Where |
|----|------|-------------------------------|-------|
| ASI01 | Agent Goal Hijack | **[LIB]** `content_trust.py` *can* flag instruction-shaped text — nothing calls it, and the two entry points a hijack uses (① the prompt, ④ the tool result) have no preventive hook at all. The gate at ② sees only the *next single call*, never the goal it serves; **[GUIDE]** claim/content is DATA not commands. A1 (origin labelling / turn taint) is specified, not built | `Security-kit/content_trust.py` (**unwired**), spec §4 A1, `Security-kit/SECURITY.md` S1.4 |
| ASI02 | Tool Misuse & Exploitation | **[MECH]** tool allowlist + phase-gate + deny-list on dangerous commands | `governance/mcp-allowlist.json`, `governance/permission.py` Gates 1–2 |
| ASI03 | Identity & Privilege Abuse | **[MECH]** least-privilege via per-phase tool gating; **[GUIDE]** short-lived scoped creds; **[GAP]** no identity broker (deployment concern) | `permission.py` Gate 2, `Security-kit/SECURITY.md` S2.4–S2.5 |
| ASI04 | Agentic Supply Chain Vulnerabilities | **[MECH]** allowlist *membership* fails closed for unregistered tools; **[GAP]** not version-pinned in any enforced sense — the allowlist carries a `version` field but `permission.py` never reads it (grep: no match), and the template ships it unfilled as `{{VERSION}}`. A swapped MCP server at the same name passes; **[GUIDE]** exact dep pins | `governance/mcp-allowlist.json`, `permission.py` `check_phase_gate`, `Security-kit/SECURITY.md` §5 |
| ASI05 | Unexpected Code Execution (RCE) | **[MECH]** deny-list blocks destructive/exec patterns (word/regex modes); egress default-deny | `governance/deny-list.json`, `permission.py` Gates 1 & 3 |
| ASI06 | Memory & Context Poisoning | **[GAP]** the memory files ARE the attack surface and are freely writable: `progress.md` and `feature_list.json` are *not* in `BUILTIN_PROTECTED_PATHS`, and `feature_list.json` is what `check_phase_gate` reads — so poisoning memory is also privilege escalation (write `"status":"passing"`, unlock a gated tool). No write gate, no consistency check in code; **[GUIDE]** treat them as tamperable (S1.3). A5 (memory-write gate) is specified, not built | `Security-kit/SECURITY.md` S1.3, spec §4 A5, `Security-kit/content_trust.py` (**unwired**) |
| ASI07 | Insecure Inter-Agent Communication | **[GAP]** — and do **not** declare N/A on the grounds that the template is single-agent. It defines no subagents of its own (`.claude/` holds only `commands/` + `settings.json`), but the *host* offers delegation regardless: measured, `permission.py` would deny `Agent`/`Task` (`not in allowlist`, exit 2) yet the `matcher` never routes them, so a spawn reaches no gate. A subagent inherits the goal and returns text straight into position ④. A4 (delegation narrowing) is specified, not built | `.claude/settings.json` `matcher`, spec §4 A4, `SEC-COVER-GAP-001` in `control-matrix.md` |
| ASI08 | Cascading Failures | **[MECH]** the gate itself fails closed (bad input, unreadable policy and unknown tool all DENY — `PolicyError`, `_deny`, `not in allowlist`); **[GAP]** nothing bounds a *run*: `max_turns` is `demo/harness.py:47` only, and the 3-strike stop exists as prose in `CLAUDE.md` with **no code** (grep: no strike counter anywhere). Both are sequence properties, and the gate is stateless per call; **[GUIDE]** human sign-off between phases | `permission.py` (fail-closed), `CLAUDE.md` escalation (**advisory**), spec §4 A2, `Security-kit/SECURITY.md` §7 |
| ASI09 | Human-Agent Trust Exploitation | **[MECH]** policy updates are genuinely human-only — `governance/*` and `.claude/settings.json` are protected paths (Gate 1a); **[OBS]** append-only audit records verdicts but cannot veto; **[GAP]** phase sign-off is **not** mechanical — `check_phase_gate` trusts `status: "passing"` in `feature_list.json`, which is *not* a protected path. Measured: an Edit to it is `ALLOW`, and flipping the field takes the gated tool from `BLOCK` to `ALLOW`. "Agent cannot self-promote phases" is a convention, not a control | `permission.py` `check_protected_paths` / `check_phase_gate`, `Harness-Best-Practice/observability/audit.py`, `Security-kit/SECURITY.md` §6 |
| ASI10 | Rogue Agents | **[MECH]** append-only audit trail + Gate 1a (`check_protected_paths`) hard-denies writes to the agent's own mechanism/policy (file-identity match, covering traversal, symlinks, hard links and case variants; not policy-disableable); **[GAP]** an interpreter (`python3 -c`) can still write those files — see SECURITY.md S2.4; **[GUIDE]** review audit for drift | `Harness-Best-Practice/observability/audit.py`, `permission.py` `check_protected_paths`, `Security-kit/SECURITY.md` S2.4, S6.4–S6.5 |

---

## Where each risk lands in the loop

The tables above answer "what addresses this risk". This one answers the question an
adversary asks: **at which position do I attack, and is anything there?** Positions are
the five from the box at the top of this file.

```
     RISK ENTERS AT            IS A CONTROL THERE?        SO WHAT SURVIVES
  ───────────────────────────────────────────────────────────────────────────────
  ① the prompt                 ✗ nothing WIRED            LLM01, LLM07, ASI09
     LLM01 ASI01                 UserPromptSubmit can        (mitigation is ②
                                 block; we use it not        refusing the *action*
                                                             the hijack asks for)
  ───────────────────────────────────────────────────────────────────────────────
  ② the tool-call proposal      ★ 4 GATES  ← everything    LLM02 LLM03 LLM06
     LLM02 LLM03 LLM06            mechanical lives here      partially: only for
     ASI02 ASI03 ASI05                                       the 5 matched tools
     ASI10                                                   (SEC-COVER-GAP-001)
  ───────────────────────────────────────────────────────────────────────────────
  ③ the side effect             n/a — already happened     —
  ───────────────────────────────────────────────────────────────────────────────
  ④ the result re-entering      ✗ nothing CAN block        LLM05, ASI01, ASI06
     the model                    PostToolUse cannot veto    — the whole data
     LLM05 ASI01 ASI06 ASI07      (docs); it logs, after     plane is [LIB]
                                  the effect
  ───────────────────────────────────────────────────────────────────────────────
  ⑤ the sequence / the run      ✗ stateless                LLM10, ASI06, ASI08
     LLM10 ASI06 ASI08            gate has no memory         ASI09 — every
     ASI09                        across calls               cumulative attack
```

Read the columns, not the rows: **every mechanical control the template has sits at ②**.
That is a real boundary and it holds — `governance/permission.py` is why an Edit to the
gate, a deny-listed command and an unregistered tool are all refused. But it is *one*
boundary out of five, it is per-call, and the deny-list is bypassed by choosing an
unmatched tool rather than by defeating a check.

The honest one-line summary: **the template is a well-built tool-boundary gate, not
agentic-risk coverage.** The G-tier (what a gateway catches: which tool, which command,
which host, which file) is mechanical. The A-tier (what makes an *agent* different:
where content came from, what happened earlier in the session, what the plan was, who
delegated) is designed and unbuilt — spec §4 A1–A5.

---

## How to use this crosswalk

1. For each risk **relevant to your agent**, confirm the cited mechanism exists and its
   test passes (`./init.sh` gates on the enforcement proofs).
2. For every **[APP]** row, implement the control in your agent code and add a row to
   `Security-kit/control-matrix.md` linking it to a verification.
3. For every **[GAP]** / **N/A** row, record the decision (not applicable, or accepted
   residual risk) in `control-matrix.md` — an unstated gap is an unmanaged risk.
4. Re-verify after any change that adds a tool, an external call, retrieval, multi-agent
   messaging, or a new data flow — those change which rows apply.

> A row is only **[MECH]** when an execution path enforces it *and* a test proves that
> path. Everything else is guidance or your responsibility to implement.
