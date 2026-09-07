# The security kit, from the template's point of view

The security kit is the template's cross-cutting security operating model — it combines
context, guidance, policy, enforcement, verification, and review evidence. It applies an
*approved* design; it doesn't make architecture decisions for you.

| Layer | Purpose | Where |
|---|---|---|
| **Context** | The approved posture, threats, controls | `Security-kit/SECURITY.md` (42 source-tagged controls, S1.1 – S8.6) |
| **Guidance** | Shape everyday coding behaviour | `kiro/steering/security.md` (Kiro auto); `.claude/rules/` (Claude, optional) |
| **Workflow** | Review sensitive changes consistently | `kiro/steering/security-review.md` |
| **Policy** | Permitted tools, egress, approvals | `governance/deny-list.json`, `governance/mcp-allowlist.json`, `Harness-Best-Practice/feature_list.json` |
| **Enforcement** | Prevent prohibited actions | `governance/permission.py` (control) + `Security-kit/content_trust.py` (data) — in your IDE session via hooks, in your deployed app via `governance/runtime_dispatcher.py` + `Security-kit/runtime_screen.py` |
| **Verification** | Prove controls work + resist attack | `tests/test_hooks.py`, `test_e2e.py`, `test_content_trust.py`, `test_runtime_dispatcher.py`, `test_runtime_screen.py`, `fixtures.json` |
| **Evidence** | Record decisions, findings, residual risk | `Security-kit/control-matrix.md`, `progress.md`, git history |

**Fill per project:** `Security-kit/coverage.json` — which of the 20 OWASP LLM/Agentic ids
apply here ([Step 5b](../../template/README.md#step-5b--tailor-the-security-controls-security-tailor) drafts it) —
then the rows of `Security-kit/control-matrix.md` (control → code → verification →
evidence), your threat model, and any domain-specific test cases. The template ships the
matrix's per-project table **empty**: no placeholder row, because a stub row draws wrong
answers that no invariant can catch.

**AI-specific risk coverage.** `Security-kit/owasp-crosswalk.md` maps every item of the
**OWASP Top 10 for LLM Applications (2025)** and the **OWASP Top 10 for Agentic
Applications (2026, ASI01–ASI10)** to the exact template mechanism that addresses it —
marked `[MECH]` (enforced + tested), `[GUIDE]` (advisory), `[APP]` (your code), or
`[GAP]`. Use it to prove coverage and record residual risk.

**Security vs non-security.** `Security-kit/SECURITY-MANIFEST.md` is the authoritative
inventory: which files are pure-security (removable), which are pure-harness, and which
are *wired* (security woven into a shared file). To produce a build with the security
layer removed — for comparison, or a deliberately ungoverned project:

```bash
./install.sh --no-security --dry-run   # preview what's removed/neutralized
./install.sh --no-security             # strip it (run on a copy)
```

The full build's `init.sh` integrity gate prevents the kit from being *silently*
stripped; `--no-security` is the explicit, recorded way to remove it.

> A control is only **mechanical** when an execution path enforces it *and* a test proves
> that path. Steering and docs are *guidance*; hooks and tests are *enforcement*. `init.sh`
> now gates on the enforcement proofs so a disabled kit cannot pass silently.

Sources: AWS Well-Architected Agentic AI Lens, CSA Singapore "Securing Agentic AI"
Addendum, OWASP Agentic AI Top 10 — see `Security-kit/SECURITY.md` for the tagged mapping.

---
