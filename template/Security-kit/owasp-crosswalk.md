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
> **Most enforcement still lives at ONE point in the loop** — the tool-call proposal
> boundary, the PreToolUse hook into `governance/permission.py`. Measured, there are five
> positions in an agent loop; three now carry a preventive control and two do not:
>
> ```
>   ① prompt ─────────▶ ★ 1 GATE         SEC-PROMPT-001, exit 2 erases the prompt.
>                                         Fires once per HUMAN turn — never for a
>                                         subagent, so it adds nothing at runtime
>   ② proposal ───────▶ ★ 4 GATES        ← the only boundary that stops an ACTION
>   ③ tool runs ──────▶ side effect happens
>   ④ result → LLM ───▶ ★ 1 GATE         SEC-RESULT-001, PostToolUse replaces the
>   │                                     output via updatedToolOutput before the
>   │                                     model reads it. Fires per tool call, so
>   │                                     this is the pre-model control that covers
>   │                                     agent RUNTIME. Cannot undo the call
>   └─ ⑤ loop back to ② ▶ ✗ stateless    the gate has no memory across turns
> ```
>
> An earlier version of this file said ④ *cannot* be closed with a hook, on the grounds
> that `PostToolUse` cannot block. That was wrong and it was load-bearing — a gap
> labelled impossible never gets scheduled. `PostToolUse` cannot veto the **call**; it
> can replace the **output**, which the runtime documents as "Replaces the tool output
> before it is sent to the model" (Claude Code 2.1.231, read 2026-08-17).
>
> **State of the ④ control:** the mechanism (`Security-kit/result_screen.py`) and its
> proof (`tests/test_result_screen.py`, 18 tests) are in the tree and green. The wiring
> touches protected and human-owned files, so it ships as `asi01-result-screen.patch`
> and is LIVE only once that patch is applied. Everything below describes the
> post-patch tree.
>
> ① and ④ are different controls, not two copies of one. ① erases a human's prompt and
> fires once per turn; ④ replaces a tool result and fires per call, including inside a
> subagent. They share one marker list on purpose — `content_trust.py` owns it, neither
> screen defines its own — so a detection change moves both at once.
>
> What remains structural, and is not a to-do list: Gate ② is a **stateless per-call
> check**, so it is blind by construction to anything that lives in the *sequence*.
> Twenty $500 refunds each pass identically. And text that ④ does not recognise gets a
> fresh, fully-authorised attempt at ② on every iteration — the screen lowers the odds
> per pass, it does not bound the sequence.
>
> So the **agent-specific** half of the ASI list is addressed **by design, not by
> implementation**. The mechanisms for it (origin labelling, session-cumulative state,
> delegation narrowing, memory-write gating) are specified in
> `docs/superpowers/specs/2026-08-13-security-kit-build-design.md` §4 as A1–A5 and
> **none of them are built**. Do not read a `[MECH]` tag on a G-tier row as coverage of
> the agentic risk it sits next to.
>
> Verified by reading source and driving the live hooks: gate ② on 2026-08-10, the
> ① and ④ screens on 2026-08-17 (including the runtime's `updatedToolOutput`
> handling, read from the Claude Code 2.1.231 bundle rather than the docs).

Sources (verified 2026-08-03):
- OWASP Top 10 for LLM Applications — **v2025** ([genai.owasp.org/llm-top-10](https://genai.owasp.org/llm-top-10/))
- OWASP Top 10 for Agentic Applications — **2026** (ASI01–ASI10, published 2025-12-09;
  [genai.owasp.org](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/))

---

## OWASP Top 10 for LLM Applications (2025)

| ID | Risk | How the template addresses it | Where |
|----|------|-------------------------------|-------|
| LLM01 | Prompt Injection | **[MECH]** screened at BOTH pre-model positions against one shared marker list: ① `prompt_screen.py` exits 2 and the prompt is erased; ④ `result_screen.py` replaces the tool output before the model reads it. **Enforcement is exact, detection is not** — 24 regexes, measured 10 of 12 corpus attacks caught for 2 of 12 legitimate cases withheld; **[LIB]** `content_trust.py::screen_record` (field allowlisting) still has no caller; **[GUIDE]** input-trust rules | `Security-kit/prompt_screen.py`, `Security-kit/result_screen.py`, `Security-kit/eval/corpus/injection/`, `tests/test_injection_corpus.py`, `Security-kit/SECURITY.md` S1.4 |
| LLM02 | Sensitive Information Disclosure | **[MECH]** secret-block hook on writes; **[MECH]** egress default-deny; **[GUIDE]** output-safety rules | `Security-kit/secret_scan.py`, `permission.py` Gate 3, `Security-kit/SECURITY.md` §4 |
| LLM03 | Supply Chain | **[MECH]** allowlist membership — an unregistered tool fails closed (`check_phase_gate` returns `not in allowlist`); **[GUIDE]** the `version` field is *declarative only* — `permission.py` never reads it, so nothing rejects a version drift; **[GUIDE]** pin deps | `governance/mcp-allowlist.json`, `permission.py` `check_phase_gate`, `Security-kit/SECURITY.md` §5 |
| LLM04 | Data and Model Poisoning | **[APP]** treat context files as untrusted / verify consistency; **[GAP]** no training-data controls (out of scope for a local agent harness) | `Security-kit/SECURITY.md` S1.3; declare residual risk in `control-matrix.md` |
| LLM05 | Improper Output Handling | **[MECH]** `result_screen.py` withholds a tool result whose text is instruction-shaped, replacing it via `updatedToolOutput` and preserving the output's shape so the runtime cannot discard the substitution and fall back to the original. It does not undo the call — the side effect at ③ has happened; **[GUIDE]** validate tool output | `Security-kit/result_screen.py`, `tests/test_result_screen.py`, `Harness-Best-Practice/observability/audit_hook.py`, `Security-kit/SECURITY.md` S1.1, S5.4 |
| LLM06 | Excessive Agency | **[MECH]** phase-gate (tools locked until a human records the prerequisite phase in `signed_off_phases`) + WIP=1; deny-list | `permission.py` Gate 2, `governance/mcp-allowlist.json`, `CLAUDE.md` working rules |
| LLM07 | System Prompt Leakage | **[GUIDE]** don't expose gate internals/deny-list/audit; **[APP]** keep secrets out of prompts | `Security-kit/SECURITY.md` S4.3; `kiro/steering/security.md` output-safety |
| LLM08 | Vector & Embedding Weaknesses | **[GAP]** no RAG/vector store in the base template | Declare N/A or add controls in `control-matrix.md` if you add retrieval |
| LLM09 | Misinformation | **[APP]** independent verification pattern + human review on low confidence; **[GUIDE]** don't over-rely on tool output | `Security-kit/SECURITY.md` S5.4; your phase `verification` command |
| LLM10 | Unbounded Consumption | **[APP]** `max_turns` exists only in `demo/harness.py:47` — and `demo/ARCHITECTURE.md:3` states the demo is **NOT the production enforcement path**. Nothing caps turns, tokens or cost on the real path; the loop belongs to Claude Code; **[GUIDE]** budget caps, 3-strike stop | `demo/harness.py:47` (demo only), `Security-kit/SECURITY.md` §7 |

---

## OWASP Top 10 for Agentic Applications (2026, ASI01–ASI10)

| ID | Risk | How the template addresses it | Where |
|----|------|-------------------------------|-------|
| ASI01 | Agent Goal Hijack | **[MECH]** both entry points a hijack uses are now screened before the model: ① the prompt and ④ the tool result. Two limits stay: the gate at ② still sees only the *next single call*, never the goal it serves, and detection is pattern-based, so a paraphrase outside the 24 markers passes (2 recorded misses); **[MECH]** both screens are protected paths as of 2026-08-17 — before that an `Edit` to `result_screen.py` was `ALLOW`, and because a blanked screen exits 0 with empty stdout (read as "no replacement"), hijacked output could have disabled the control that screens it; **[GUIDE]** claim/content is DATA not commands. A1 (origin labelling / turn taint) is still specified, not built — which is what would replace the regexes with provenance | `Security-kit/prompt_screen.py`, `Security-kit/result_screen.py`, spec §4 A1, `Security-kit/SECURITY.md` S1.4 |
| ASI02 | Tool Misuse & Exploitation | **[MECH]** tool allowlist + phase-gate + deny-list on dangerous commands | `governance/mcp-allowlist.json`, `governance/permission.py` Gates 1–2 |
| ASI03 | Identity & Privilege Abuse | **[MECH]** least-privilege via per-phase tool gating; **[GUIDE]** short-lived scoped creds; **[GAP]** no identity broker (deployment concern) | `permission.py` Gate 2, `Security-kit/SECURITY.md` S2.4–S2.5 |
| ASI04 | Agentic Supply Chain Vulnerabilities | **[MECH]** allowlist *membership* fails closed for unregistered tools; **[GAP]** not version-pinned in any enforced sense — the allowlist carries a `version` field but `permission.py` never reads it (grep: no match), and the template ships it unfilled as `{{VERSION}}`. A swapped MCP server at the same name passes; **[GUIDE]** exact dep pins | `governance/mcp-allowlist.json`, `permission.py` `check_phase_gate`, `Security-kit/SECURITY.md` §5 |
| ASI05 | Unexpected Code Execution (RCE) | **[MECH]** deny-list blocks destructive/exec patterns (word/regex modes); egress default-deny | `governance/deny-list.json`, `permission.py` Gates 1 & 3 |
| ASI06 | Memory & Context Poisoning | **[GAP]** the memory files ARE the attack surface and are freely writable: `progress.md` and `feature_list.json` are *not* in `BUILTIN_PROTECTED_PATHS`, and by design cannot be — the agent has to keep its own worklog. No write gate, no consistency check in code; **[GUIDE]** treat them as tamperable (S1.3). A5 (memory-write gate) is specified, not built. **[MECH]** what memory poisoning no longer buys is *privilege*: as of 2026-08-17 `check_phase_gate` reads `signed_off_phases` from the protected allowlist instead of `status` in the worklog, so the three edits that used to take a gated tool from BLOCK to ALLOW (mark it passing, mark everything passing, delete the entry) all DENY — see `SEC-PHASE-GAP-001` and `tests/test_steady_state.py`. Poisoned memory still misleads the model; it does not hand it a tool | `Security-kit/SECURITY.md` S1.3 and S2.2, spec §4 A5, `Security-kit/content_trust.py` (`scan_text` wired at ① and ④; `screen_record` still uncalled) |
| ASI07 | Insecure Inter-Agent Communication | **[GAP]** — and do **not** declare N/A on the grounds that the template is single-agent. It defines no subagents of its own (`.claude/` holds only `commands/` + `settings.json`), but the *host* offers delegation regardless: measured, `permission.py` would deny `Agent`/`Task` (`not in allowlist`, exit 2) yet the `matcher` never routes them, so a spawn reaches no gate. A subagent inherits the goal and returns text straight into position ④. A4 (delegation narrowing) is specified, not built | `.claude/settings.json` `matcher`, spec §4 A4, `SEC-COVER-GAP-001` in `control-matrix.md` |
| ASI08 | Cascading Failures | **[MECH]** the gate itself fails closed (bad input, unreadable policy and unknown tool all DENY — `PolicyError`, `_deny`, `not in allowlist`); **[GAP]** nothing bounds a *run*: `max_turns` is `demo/harness.py:47` only, and the 3-strike stop exists as prose in `CLAUDE.md` with **no code** (grep: no strike counter anywhere). Both are sequence properties, and the gate is stateless per call; **[GUIDE]** human sign-off between phases | `permission.py` (fail-closed), `CLAUDE.md` escalation (**advisory**), spec §4 A2, `Security-kit/SECURITY.md` §7 |
| ASI09 | Human-Agent Trust Exploitation | **[MECH]** policy updates are genuinely human-only — `governance/*`, `.claude/settings.json` and both pre-model screens are protected paths (Gate 1a); **[MECH]** "the agent cannot self-promote phases" became a control on 2026-08-17: the unlock is `signed_off_phases` in the protected allowlist, so the agent's own worklog no longer releases a gated tool (three measured escalation edits now DENY, `tests/test_steady_state.py`); **[OBS]** append-only audit records verdicts but cannot veto; **[GAP]** sign-off is still an *attestation* — adding a phase id re-runs no verification, so a human who signs off without looking is indistinguishable from one who checked (`SEC-PHASE-GAP-001`) | `permission.py` `check_protected_paths` / `check_phase_gate`, `Harness-Best-Practice/observability/audit.py`, `Security-kit/SECURITY.md` §6 |
| ASI10 | Rogue Agents | **[MECH]** append-only audit trail + Gate 1a (`check_protected_paths`) hard-denies writes to the agent's own mechanism/policy — 10 built-in paths, now including both pre-model screens and the two detection modules (file-identity match, covering traversal, symlinks, hard links and case variants; not policy-disableable); **[GAP]** an interpreter (`python3 -c`), plus `cp`/`install`/`ln -sf`/`git checkout`/`dd if=`, can still write those files, and the audit files are open to every shell verb — 68 of 140 cells, see SECURITY.md S2.4; **[GUIDE]** review audit for drift | `Harness-Best-Practice/observability/audit.py`, `permission.py` `check_protected_paths`, `Security-kit/SECURITY.md` S2.4, S6.4–S6.5 |

---

## Where each risk lands in the loop

The tables above answer "what addresses this risk". This one answers the question an
adversary asks: **at which position do I attack, and is anything there?** Positions are
the five from the box at the top of this file.

```
     RISK ENTERS AT            IS A CONTROL THERE?        SO WHAT SURVIVES
  ───────────────────────────────────────────────────────────────────────────────
  ① the prompt                 ★ 1 GATE                   LLM07, ASI09
     LLM01 ASI01                 SEC-PROMPT-001, exit 2      LLM01/ASI01 survive
                                 erases the prompt. Human    only as a paraphrase
                                 turns only, never a         outside the markers
                                 subagent's
  ───────────────────────────────────────────────────────────────────────────────
  ② the tool-call proposal      ★ 4 GATES  ← everything    LLM02 LLM03 LLM06
     LLM02 LLM03 LLM06            mechanical lives here      partially: only for
     ASI02 ASI03 ASI05                                       the 5 matched tools
     ASI10                                                   (SEC-COVER-GAP-001)
  ───────────────────────────────────────────────────────────────────────────────
  ③ the side effect             n/a — already happened     —
  ───────────────────────────────────────────────────────────────────────────────
  ④ the result re-entering      ★ 1 GATE                   ASI06, ASI07
     the model                    SEC-RESULT-001 replaces    LLM05/ASI01 survive
     LLM05 ASI01 ASI06 ASI07      the output before the      only as a paraphrase.
                                  model reads it. Per tool   ASI06 poisoning of a
                                  call, so it covers agent   file the agent WROTE
                                  runtime. The call itself   is not tool output —
                                  is not undone              see the ASI06 row
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
