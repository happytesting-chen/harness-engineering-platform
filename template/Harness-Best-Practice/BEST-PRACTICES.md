# Harness Engineering Best Practices

Distilled from [Learn Harness Engineering](https://walkinglabs.github.io/learn-harness-engineering/en/) Lectures 03 + 08.

---

## The One Principle

> The agent's entire world is the repository. If it isn't a machine-readable file in the repo, it does not exist for the agent.

Externalize everything the agent needs. Let the repo — not chat, not memory, not a human's head — be the single source of truth.

---

## Three Records That Must Live in the Repo

### 1. Knowledge — the map (Lecture 03)

One lean entry file + knowledge next to the code it governs.

- **`AGENTS.md`** (50–100 lines): what it is · how to run · how to verify
- **Module-level `ARCHITECTURE.md`**: responsibilities, interfaces, constraints — in the directory of the code it governs
- Minimal but complete; updated with code (stale docs are worse than none)

### 2. Scope — the feature list as a primitive (Lecture 08)

Not a memo — a data structure the scheduler, verifier, and handoff all read.

Every feature carries **the triple:**

```
(behavior · verification command · state)
```

- **Behavior**: observable outcome, not vague summary ("POST /cart returns 201" not "cart mostly done")
- **Verification**: exact shell command, exit 0 = pass
- **State**: `not-started → active → blocked → passing`

Pass-gated: only a passing verification command can flip to `passing` — the agent cannot self-declare it.

### 3. State — durable and ACID (Lecture 03)

`progress.md` handoff + git discipline:

- **Atomic**: one commit per logical unit, rollback-able
- **Consistent**: gates green before commit (verification passes)
- **Isolated**: per-agent progress file or branch
- **Durable**: in git, not in the agent's head

---

## The Fresh Session Test

The single test that validates all three records.

Open a brand-new session with only the repo. Ask:

| # | Question | Must be answerable from |
|---|----------|------------------------|
| 1 | What is this? | `AGENTS.md` |
| 2 | How do I run it? | `AGENTS.md` + `init.sh` |
| 3 | How do I verify it? | `AGENTS.md` + `feature_list.json` verification fields |
| 4 | What's done? | `feature_list.json` (state = passing) + `progress.md` Done section |
| 5 | What's next? | `feature_list.json` (first not-started) + `progress.md` Next Steps |

If it can't answer → the map has blank spots. Target: **knowledge-visibility gap < 10%**.

---

## The Rules, in One Breath

Repo is truth; one lean entry file; knowledge next to code; feature list = behavior + verification + state, harness-flipped and pass-gated; state is ACID in git; pass the Fresh Session Test.

---

## How This Template Implements It

| Principle | Implementation |
|-----------|---------------|
| Repo is truth | All knowledge in tracked files, zero reliance on conversation memory |
| Lean entry file | `AGENTS.md` (~60 lines) |
| Knowledge next to code | `ARCHITECTURE.md` in every module directory |
| Feature triple | `feature_list.json`: behavior + verification + status |
| Pass-gated | `permission.py` reads feature_list.json; human sign-off for status=passing |
| State is ACID | `progress.md` (durable), `init.sh` (consistency check), one-phase-active (isolation) |
| Fresh Session Test | `init.sh` checks all 5 questions are answerable |

---

## Anti-Patterns

| Don't | Why | Defense |
|-------|-----|---------|
| "Shopping cart mostly done" | No machine can act on "mostly" | Feature triple forces exact behavior + verification |
| Agent self-declares "done" | Model's standard ≠ your standard | Pass-state gating: verification exit 0 + human sign-off |
| Knowledge in Slack/heads | Agent can't see it | Fresh Session Test catches the gap |
| One giant instruction file | Context dilution | Distributed: AGENTS.md (entry) + module docs (detail) |
| Free-form progress notes | New sessions can't parse state | Structured feature_list.json + machine-readable states |
| Agent edits its own constraints | Fox guarding the henhouse | permission.py is mechanism (never modified); policy is separate JSON |
| Stale documentation | Worse than no docs — sends agent wrong direction | init.sh staleness detection + docs-next-to-code principle |
