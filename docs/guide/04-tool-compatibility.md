# Tool compatibility

| Feature | Claude Code (active root) | Kiro (opt-in: `cp -r kiro/ .kiro/`) | Codex / Cursor / Copilot / Gemini |
|---|---|---|---|
| Instruction file | `CLAUDE.md` (auto; imports `@AGENTS.md`) | `CLAUDE.md` (manual ref) | `AGENTS.md` (auto) |
| Enforcement hooks | `.claude/settings.json` → `permission.py` | `.kiro/hooks/*.json` → same `permission.py` | call `permission.py` CLI |
| Always-on rules | `.claude/rules/*.md` | `.kiro/steering/*.md` (`inclusion: auto`) | — |
| Session workflow | `.claude/commands/session-cycle.md` | `.kiro/steering/session-cycle.md` | — |

**Claude-first, Kiro opt-in.** Everything in the active root is read by Claude Code —
nothing sits inert. Kiro's integration lives under `kiro/`; a Kiro user copies it to
`.kiro/` (see `kiro/README.md`). Both runtimes invoke the **same** tool-agnostic
`governance/permission.py` — only the activation layer differs.

**Why `AGENTS.md`?** It's the open standard read by other agents. Claude Code reads
`CLAUDE.md`, not `AGENTS.md`, so `CLAUDE.md` imports it via `@AGENTS.md` — one source of
truth that loads in every runtime.

> **Enforcement caveat — read this one.** The gate is real, but the hook *wiring*
> activates it, and wiring is configuration on **your** machine. `tests/test_hooks.py`
> proves each hook script honours its contract (JSON envelope on stdin, exit 2 to block);
> it cannot prove your host is invoking those scripts, and a host that isn't gives you
> silence, not an error. **Verify it yourself in 30 seconds** —
> [Test the runtime, Step R2](../../template/README.md#step-r2--the-30-second-wiring-check-do-this-before-anything-else).
> The Kiro hook payload must additionally be confirmed in a real Kiro runtime — see the
> note in `kiro/hooks/governance-check.json`.

---
