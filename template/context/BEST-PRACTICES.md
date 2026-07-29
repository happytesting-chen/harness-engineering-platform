# Harness Engineering Best Practices

Distilled from the [Learn Harness Engineering](https://walkinglabs.github.io/learn-harness-engineering/en/) course. These principles inform every design decision in this template.

---

## Principle 1: Repository as Single Source of Truth (Lecture 03)

> Information not in the repo doesn't exist for the agent.

**The Fresh Session Test** — A brand-new agent session, given only repo contents, must answer:

| Question | Answered by (in this template) |
|----------|-------------------------------|
| What is this system? | `AGENTS.md` |
| How is it organized? | `AGENTS.md` architecture tree + module `ARCHITECTURE.md` files |
| How do I run it? | `AGENTS.md` + `init.sh` |
| How do I verify it? | `AGENTS.md` verification section + `feature_list.json` per-phase commands |
| Where are we now? | `progress.md` + `feature_list.json` status fields |

**Four principles:**

1. **Knowledge lives next to code.** Each module directory has an `ARCHITECTURE.md` explaining responsibilities, interfaces, and constraints. When the agent reaches the code, it also reaches the rules.

2. **Standardized entry file.** `AGENTS.md` is the landing page — 50–100 lines answering "what / how to run / how to verify." It doesn't contain everything; it points to everything.

3. **Minimal but complete.** If removing a rule doesn't affect the agent's decision quality, that rule shouldn't exist. But every Fresh Session Test question must have an answer.

4. **Update with code.** Architecture docs in module dirs get noticed when code changes. Stale docs are worse than no docs — `init.sh` detects staleness.

---

## Principle 2: Feature Lists as Harness Primitives (Lecture 08)

> Feature lists aren't memos for humans. They're the foundational data structure the entire harness is built on.

**The Triple** — Every feature item MUST have:

```
(behavior, verification, state)
```

| Field | Purpose | Example |
|-------|---------|---------|
| `behavior` | Observable outcome — what "done" looks like | "nmap scan of 10.20.0.0/24 produces host inventory in sandbox/recon-results.txt" |
| `verification` | Exact command that proves it | `test -f sandbox/recon-results.txt && echo 'recon complete'` |
| `state` | Machine-readable status | `not-started` / `active` / `passing` |

**State machine:**

```
not-started → active → passing
                ↓
             blocked (optional)
```

- Only ONE feature may be `active` at a time (WIP=1)
- The agent CANNOT self-promote to `passing` — verification must pass + human sign-off
- `passing` is irreversible — once done, it stays done
- Blocked features get unblocked by human intervention

**Four roles the feature list serves:**

1. **Scheduler** — Reads states, picks the next `not-started` item to activate
2. **Verifier** — Executes verification commands, decides state transitions
3. **Phase-gate** — `permission.py` reads feature_list.json to unlock gated tools
4. **Progress tracker** — Tallies state distribution for project health

**Granularity rule:** Each feature should be completable in one session. "Implement recon" is too broad. "Run nmap scan of in-scope subnet" is right.

---

## How This Template Implements Both Principles

| Lecture concept | Template implementation |
|----------------|----------------------|
| Repo as spec | All knowledge in tracked files, zero reliance on conversation memory |
| Fresh session test | `AGENTS.md` + `init.sh` + `feature_list.json` + `progress.md` |
| Knowledge next to code | Module-level `ARCHITECTURE.md` in each directory |
| Feature triple | `feature_list.json`: description (behavior) + verification (command) + status (state) |
| Pass-state gating | `governance/permission.py` reads feature_list.json, enforces phase-gate |
| Single active feature | CLAUDE.md Working Rules: "WIP=1" |
| State controlled by harness | Agent cannot edit status to "passing" — human sign-off required |
| Verification-driven transitions | Each feature has an exact `verification` command (exit 0 = done) |
| Evidence trail | `evidence` field in feature_list.json + `observability/audit.log` |
| Stale state detection | `init.sh` detects outdated progress.md |

---

## Anti-Patterns to Avoid

| Anti-pattern | Why it fails | Template's defense |
|-------------|-------------|-------------------|
| "Shopping cart mostly done" | No machine can act on "mostly" | Feature triple forces exact behavior + verification |
| Agent self-declares "done" | Model's standard ≠ your standard | Pass-state gating: verification command must exit 0 |
| Knowledge in Slack/heads | Agent can't see it | Everything in repo, Fresh Session Test validates |
| One giant instruction file | Context dilution, contradictions | Distributed: AGENTS.md (entry) + module ARCHITECTURE.md (detail) |
| Free-form progress notes | New sessions can't parse state | Structured `feature_list.json` + machine-readable states |
| Agent modifies its own constraints | Fox guarding the henhouse | `permission.py` is mechanism (never modified), policy is separate JSON |

---

## Checklist: Is Your Harness Ready?

- [ ] Fresh session can answer all 5 questions from repo alone
- [ ] Every feature has behavior + verification + state (the triple)
- [ ] Only one feature is `active` at a time
- [ ] Verification commands are executable (exit 0 = pass, non-zero = fail)
- [ ] Agent cannot self-promote features to `passing`
- [ ] `init.sh` catches unfilled placeholders and stale state
- [ ] Module directories have local ARCHITECTURE.md or CONSTRAINTS.md
- [ ] No critical knowledge lives only in conversation history
