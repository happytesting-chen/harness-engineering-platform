# Findings — Security-kit enhancement

## Task
Make Security-kit an *active* part of the template that connects the AI product
(`Context/`) to the security guidance (`SECURITY.md` + `owasp-crosswalk.md`), so it
tailors controls to the specific product rather than sitting passive.

## How Security-kit works TODAY (verified by reading files, 2026-08-04)
- **Passive reference:** `SECURITY.md` (41 controls, source-tagged AWS/CSA/OWASP/HARNESS),
  `owasp-crosswalk.md` (LLM01-10 + ASI01-10 → mechanism, tagged [MECH]/[GUIDE]/[APP]/[GAP]),
  `SECURITY-MANIFEST.md` (security vs non-security inventory, 3 tiers).
- **Manual evidence:** `control-matrix.md` — human fills rows: Control ID | objective |
  impl location | verification | review evidence. Ships 2 example rows + 1 placeholder.
- **Live mechanisms:** `content_trust.py` (data-plane library, agent must call screen_record),
  `secret_scan.py` (PreToolUse hook, exit 2 = block). Both proven by tests.
- **Wiring:** `.claude/settings.json` PreToolUse → permission.py + secret_scan.py;
  PostToolUse → audit. `init.sh` has a "Security-kit integrity" gate (block 5b).
- **Closest existing integration:** `/init-project` command reads Context/, drafts harness
  files, touches control-matrix "one row per trust boundary." But does NOT reason about
  WHICH of the 41 controls apply — that's the gap.

## Gap this addresses
Nothing actively maps "this product" → "these controls apply / these are gaps." The
crosswalk is generic; the matrix is blank. A human must bridge them by hand.

## Decisions locked (from brainstorming Q&A)
- **Core job:** Tailor controls to the product (reasoning task → skill, not a hook).
- **Triggers:** (1) at /init-project + on demand, AND (3) at phase sign-off gate.
- **Output rigor:** Emit a CHECKABLE ARTIFACT — machine-readable coverage file; init.sh
  fails if an applicable control has no mapped verification. Reasoning proposes, test enforces.
- **Selection scope:** Applicability + gaps ONLY. For each control/OWASP id decide
  applies / N-A / gap with a one-line reason grounded in Context/. Do NOT invent new
  controls, do NOT map verifications (engineer fills the matrix verification column;
  skill flags which applicable controls are still unmapped).

## Key design tension resolved
Skill decides *applicability*; engineer supplies *verification*. The coverage artifact
lists applicable controls; init.sh gate requires each applicable control to have a
control-matrix row with non-empty verification. Skill reports unmapped ones as gaps.

## Constraints from the template's own philosophy
- Zero external deps (stdlib python + bash only).
- "A control is real only when an execution path enforces it AND a test proves it."
- Agent cannot self-modify governance; humans own policy + sign-off.
- Claude-first, Kiro opt-in, AGENTS.md for others.
