# Harness Engineering Platform

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![Runtime dependencies: 0](https://img.shields.io/badge/runtime%20dependencies-0-brightgreen.svg)

**A harness template whose instruction files guide Claude Code to build more consistent
and more secure AI agents.**

You copy `template/` into a new project, describe your product in `Context/`, and the
harness takes over: the coding agent gets a phase plan it must follow one step at a time,
policy files that decide which tools it may call, and hooks that **mechanically block**
disallowed tool calls at the tool boundary — not by asking the model nicely in a prompt.
It cannot mark its own work done, and it cannot see or route around the gate that
evaluates it. Pure Python standard library, zero runtime dependencies.

> **The mental model:** an *agent* is a model plus tools. The **harness** is everything
> else — the instructions, the policy, the verification, the audit trail. Most agent
> quality and nearly all agent safety live in the harness, not the model.

---

## Where this fits in the SDLC

![Where the harness sits in the SDLC](assets/sdlc-position.svg)

This is a **build-time** harness. It takes over after Design & Plan has settled the
product and threat model, and it hands evidence forward to pre-deployment review.

It hands evidence forward to pre-deployment review rather than replacing it: the reviewer
gets an append-only audit log of every tool call and verdict, a measured evaluation
snapshot, and a control matrix mapping each trust boundary to the mechanism covering it.

### Two harnesses, one principle

There are **two** agents in this story, and they need separate enforcement:

| | **Build-time** (shipped here) | **Runtime** (shipped here, opt-in) |
|---|---|---|
| Which agent | the coding agent that *builds* your product | the agent you *deploy* to users |
| Runs | on a developer's laptop, human watching | in production, 3am, nobody watching |
| Enforced by | Claude Code hooks → `governance/permission.py` | `governance/runtime_dispatcher.py` — an in-process chokepoint your app calls |
| Boundary | Claude Code's tool call | your framework's tool dispatch |
| Status | **working, tested** | **working, tested — but nothing forces your app to use it** |

Both follow the same rule: **reasoning proposes, mechanism enforces.** A non-deterministic
component processing attacker-influenceable text cannot be a control surface, because
whatever persuades it disables the control. So enforcement sits *outside* the model in both
harnesses — the model proposes and deterministic code vetoes.

What changes between them is the mechanism's *shape*. A build-time hook is a subscription
to someone else's event loop — Claude Code emits `PreToolUse` and you attach. A deployed
LangChain or Strands app has no hook system, so "add hooks" there means writing the
dispatcher yourself, in-process: a chokepoint that replaces the tool, so bypassing it is
unrepresentable rather than merely forbidden.

Runtime also faces threats that no per-call check can see, because the harm lives in the
*sequence* rather than any single call — twenty $500 refunds each under a $10k ceiling,
a `read_customer` → `send_email` chain where both calls are individually in scope, or
injected text that gets persisted to memory and re-arms every future session. Those need
session-cumulative state, delegation narrowing, and a gated memory write. The build-time
gate is stateless per call and does not attempt them.

> **Status, plainly.** As of 2026-08-22 the runtime layer **exists and is tested**:
> `governance/runtime_dispatcher.py` and `Security-kit/runtime_screen.py` hold all four
> gate positions in process, importing the *same* `permission.py` and the same policy
> JSON as the hooks — so a deployed app and your IDE session return the same verdicts.
> 37 tests cover them and `./init.sh` runs both suites.
>
> **What is still a gap is that using them is opt-in.** Nothing mechanically forces your
> application to route its tool calls through `RuntimeDispatcher`, or to screen its request
> boundary; a tool your app calls directly is ungated exactly as before. That is not
> fixable from inside the kit — the application owns its own call sites, so wiring is a
> human review item at deployment (`SEC-RUNTIME-GAP-001`,
> [`SECURITY.md` S1.6](template/Security-kit/SECURITY.md)). What remains genuinely
> unbuilt is the *sequence-aware* half described two paragraphs above: session-cumulative
> ceilings, delegation narrowing, gated memory writes. All four in-process gates are
> stateless per call, like their hook counterparts.

---

## How it works

![Control plane, data plane, and the planned sub-agent layer](assets/architecture.svg)

This section describes the **build-time** harness. The runtime counterpart is the same
policy and the same gate functions reached through a different door — see
[Wiring the four gates into a deployed application](#wiring-the-four-gates-into-a-deployed-application)
below.

Follow one tool call. The coding agent proposes, say, a `Bash` command. Claude Code's
`PreToolUse` hook fires **before** the command runs and pipes it to
`governance/permission.py`, which applies four gates in a fixed order and stops at the
first denial. If any gate denies, the hook exits **2** and the command never executes —
the agent sees a denial, not a result. If all four pass, the hook exits 0, the tool runs,
and a `PostToolUse` hook appends the call and its verdict to an append-only `audit.log`.

The template wires **7 hooks across 4 events** in `template/.claude/settings.json`: one
`UserPromptSubmit` (the prompt screen — exit 2 there erases the prompt), two `PreToolUse`
(the permission gate and a secret scanner), two `PostToolUse` (the result screen, which
replaces instruction-shaped tool output via `updatedToolOutput`, then audit capture,
matching **every** tool — so the log is wider than the gate), and two `Stop` hooks (a final
audit flush and a stale-`progress.md` warning).

### The four gates

| Gate | What it reads | Scope | On denial |
|---|---|---|---|
| **1a — protected paths** | `BUILTIN_PROTECTED_PATHS` + `protected_paths` in `governance/deny-list.json` | the **write target** of any tool (`file_path`, `notebook_path`, `path`) | exit 2, and **not disableable by policy** |
| **1b — deny-list** | `patterns` in `governance/deny-list.json` | shell **command strings** only | exit 2, unconditional |
| **2 — phase-gate** | `Harness-Best-Practice/feature_list.json` + `governance/mcp-allowlist.json` | all 5 gated tools | exit 2 until the prerequisite phase is signed off |
| **3 — egress** | `egress_hosts` in `governance/mcp-allowlist.json` | a destination in a shell command **or** in one of 9 structured fields (`url`, `uri`, `endpoint`, `host`, …) at any depth, for **any** tool | exit 2 unless the host matches an allowlist entry **exactly** — a subdomain must be asked for as `*.example.com` |

First denial wins. The gate fails closed on empty or malformed input, and on an
unreadable policy file: a corrupt or deleted `deny-list.json` exits 2 rather than
silently matching nothing. (That distinction is load-bearing — Claude Code blocks
*only* on exit 2 and lets the tool run on any other non-zero, so a gate that crashed
would fail open.) Policy lives in JSON, mechanism lives in `permission.py`, and the two
are kept separate so a project tailors policy without ever touching the enforcement
code.

### The feature triple

![The feature triple and the phase state machine](assets/feature-lifecycle.svg)

This is what makes the harness more than a linter. Work is not tracked as prose — every
phase carries a **triple**: an observable *behavior*, an exact *verification command*, and
a machine-readable *state* (`not-started → active → blocked → passing`).

The `active → passing` edge is guarded twice: the verification command must exit 0 **and**
a human sign-off must be recorded in the phase's `evidence` field. **The agent cannot
promote its own phase.** "Mostly done" is not representable.

### Wiring the four gates into a deployed application

Everything above happens because Claude Code emits events. **Your production app emits
none.** Ship the harness as-is and you inherit its *design* and none of its enforcement.
Two imports fix that:

```python
import sys
sys.path.insert(0, "governance"); sys.path.insert(0, "Security-kit")
from runtime_dispatcher import RuntimeDispatcher
from runtime_screen import screen_input, InputRejected

dispatcher = RuntimeDispatcher({"fetch_article": fetch_article})   # gates ② ③ ④

def handle(request_text):
    try:
        prompt = screen_input(request_text, source="http")          # gate ①
    except InputRejected as exc:
        return {"error": str(exc)}, 400      # our words only — never echo the request
    return run_agent(prompt, tools=dispatcher)   # every call goes through execute()
```

| Position | Build-time (hooks) | Deployed runtime (in process) |
|---|---|---|
| ① input, before the model | `prompt_screen.py` · `UserPromptSubmit` | `screen_input()` |
| ② before a tool runs | `permission.py` · `PreToolUse` | `RuntimeDispatcher.execute()` |
| ③ the tool executes | — | — |
| ④ output, before the model | `result_screen.py` · `PostToolUse` | `screen_result()`, on by default |

Four things worth knowing before you rely on it:

- **The verdicts are the same ones.** `runtime_dispatcher.py` imports
  `make_permission_check` from `governance/permission.py` and reads the same policy JSON.
  It holds no second copy of any rule, and a test asserts that.
- **② prevents; ④ does not.** At ② the side effect has not happened, so `execute()` raises
  `PermissionError` and the tool is never called. By ④ it has, so a poisoned result is
  *substituted*, not refused — the call is not undone.
- **① fails closed, unlike its hook counterpart.** Input that cannot be scanned (not a
  `str`) is rejected rather than passed. There is deliberately no warn mode: an operator
  env var that downgrades a request-boundary screen to report-only is a switch an attacker
  would rather have than the bypass itself.
- **You must register your tools.** An unregistered tool denies with
  `<name> not in allowlist` — that is `mcp-allowlist.json` working, not a bug.

Full walkthrough, including the allowlist edit:
[`SECURITY.md` S1.6](template/Security-kit/SECURITY.md).

---

## Security guarantees baked in

- **Tool calls are gated at the boundary, not in the prompt** — `governance/permission.py`,
  invoked by a `PreToolUse` hook. Reasoning-layer rules can be argued around; an exit code
  cannot.
- **Mechanism is separated from policy** — `permission.py` is the engine, the JSON files
  are the policy, and `init.sh` verifies the kit is still wired so it cannot be *silently*
  stripped while the health check still reports PASS.
- **The agent cannot rewrite its own gate** — Gate 1a hard-denies writes whose target
  resolves to the mechanism or policy (`permission.py`, the policy JSON, `settings.json`,
  the hook scripts), and the built-in list stays enforced even if the policy key is emptied
  or deleted, so it cannot be switched off by editing policy. One measured exception is in
  the limits below.
- **Instruction-shaped text is screened at both pre-model positions** —
  `Security-kit/content_trust.py` owns one marker list; `prompt_screen.py` blocks the
  prompt before the model reads it (exit 2 erases it) and `result_screen.py` replaces a
  tool result before the model reads it. Enforcement is exact; **detection is patterns** —
  measured 10 of 12 corpus attacks caught for 2 of 12 legitimate cases withheld. A
  paraphrase outside the markers passes.
- **Secrets are blocked pre-write** — `Security-kit/secret_scan.py` runs as a second
  `PreToolUse` hook.
- **Every call is auditable** — `Harness-Best-Practice/observability/audit.py` appends
  JSON lines; nothing is rewritten.
- **Claims are measured, not asserted** — `evaluation/eval.py` reports accuracy,
  reproducibility and latency against an oracle, and prints cost as
  `N/A (no real provider wired)` rather than inventing a number.
- **The same gates work in the deployed app** — `governance/runtime_dispatcher.py` wraps
  your tool registry and calls the identical `permission.py`; `Security-kit/runtime_screen.py`
  covers the request boundary and tool output. Same policy files, same verdicts, no hooks.
- **A 42-control reference across 8 domains** — `Security-kit/SECURITY.md`, with an OWASP
  crosswalk and a per-project control matrix.

---

## What it does not enforce

Stated plainly, because a security control you misunderstand is worse than none.

- **Only write/exec tools are gated at build time.** The `PreToolUse` matcher covers
  `Bash|Write|Edit|MultiEdit|NotebookEdit`. `Read`, `Grep`, `Glob`, `WebFetch` and `Task`
  are **not** gated — a `Task` spawn therefore reaches no gate at all. (The runtime
  dispatcher has no such hole, because it gates *every* tool in the registry it wraps; the
  hole there is the opposite one — a tool your app never registers with it.)
- **Nothing forces a deployed app through the runtime gate.** `RuntimeDispatcher` and
  `screen_input` are libraries your application chooses to call. Verifying that wiring is a
  human review item at deployment, not something this repo can check.
- **The agent cannot edit its own gate — except through a scripting runtime.** Writes
  targeting `permission.py`, the policy JSON, `settings.json` or the hook scripts are
  hard-denied by Gate 1a, matched on the target's *identity* rather than its spelling —
  `../`, absolute forms, symlinks, hard links and (on macOS/Windows) case variants all
  resolve to the same file — and the built-in list is enforced even if the policy key is emptied
  or `deny-list.json` is deleted. The shell route is covered only by patterns
  (`>`/`>>`, `sed -i`, `tee`, `chmod`, `mv`, …), and one vector is measured as open:
  `python3 -c` opening the file for write — the same hole as Gate 3's `urllib` bypass.
  Closing it needs OS file ownership or Claude Code `permissions.deny`.
- **Gate 3 is policy matching, not network enforcement.** Two of its three original holes
  closed on 2026-08-22. A destination carried in a *structured* field is now examined for
  every tool, not just `Bash` (nesting deeper than 8 levels denies rather than gives up),
  and hosts are matched **exactly** rather than by substring — so
  `curl https://api.github.com.evil.com` is now DENIED with `api.github.com` allowlisted,
  where before it was ALLOWED. What remains open is the **shell verb blocklist**: a command
  string is only inspected if it contains one of five tokens (`curl `, `wget `, `nc `,
  `ssh `, `nmap `), so `python3 -c` with `urllib`, or `perl`, or an aliased `curl`, still
  passes unexamined. Structured fields are matched by *name* against a list of nine
  (`url`, `uri`, `endpoint`, `base_url`, `target_url`, `webhook_url`, `callback_url`,
  `host`, `hostname`), so a tool that calls its destination `address` or `server` is also
  invisible. Read it as "default-deny for destinations the gate can see", not
  "default-deny egress at the network layer" — only OS-level network policy gives you
  that.
- **"Fail-closed" has one deliberate exception.** In steady state — when *every* phase is
  `passing` — the phase gate falls through to the allowlist check rather than denying.
  This is intentional and covered by a test.
- **A malformed deny-list regex degrades to substring matching** rather than failing closed.
- **Automatic, no-code-changes enforcement is Claude Code-specific.** Other hosts get no
  hook interception. They can import `RuntimeDispatcher` (one call site) or invoke
  `permission.py` as a CLI — both work, but both are something you wire, not something that
  happens to you.
- **Zero *runtime* dependencies; `pytest` is needed only for the full test suite.**

---

## Repository layout

| Path | What it is |
|---|---|
| `template/` | The harness itself — copy this. Domain-agnostic, with `{{placeholders}}` to fill. |
| `examples/` | Real filled instances (see below). |
| `assets/` | Diagrams used by this README. |
| `.kiro/specs/harness-engineering-platform/` | The **origin** spec (requirements/design/tasks). Historical — it describes the pre-refactor layout. |
| `LICENSE` | MIT. |

---

## Quick start

```bash
git clone https://github.com/YuanSingapore/harness-engineering-platform.git
cp -r harness-engineering-platform/template my-agent && cd my-agent
./init.sh          # exits non-zero on a fresh copy — by design
```

`init.sh` is a health check, not a scaffolder. On an unfilled copy it reports
`FAIL — 5 error(s)` and prints exactly what is missing. Those five are **two** kinds of
work, and mistaking one for the other is the usual way people get stuck:

- **4 are unfilled `{{placeholders}}`** — identity, phases, policy. Fill them in.
- **1 is `coverage.json missing — run /security-tailor (fail-closed)`**, with a paired
  `security coverage incomplete` line. No amount of filling clears these: the template
  ships no applicability decision because *which of the 20 OWASP LLM/Agentic risks apply*
  is a property of your product, not of the template. `/security-tailor` drafts that
  decision from your `Context/` docs; `check_coverage.py` refuses a bad draft.

So: fill the placeholders → run `/security-tailor` → re-run `./init.sh` until it exits 0.

**→ Full walkthrough: [`template/README.md`](template/README.md)** — a 10-step guide from
empty copy to a first signed-off phase, including where your own code goes (the template
ships no `src/`, on purpose) and what a green `init.sh` does *not* mean. Plus a per-file
directory map, tool-compatibility notes and troubleshooting. That document is the manual;
this page is the front door.

---

## Examples

| Example | Maturity | What it shows |
|---|---|---|
| [`examples/claims-build/`](examples/claims-build/) | **Most complete.** Phases 01–03 signed off, 04 active. `./init.sh` exits 0; 50 tests pass. | An insurance-claims triage agent built end to end *inside* the harness: deterministic decision engine with one decision authority, product code in `claims/` + `extraction/` with their own tests, three proofs (`tests/` correct · `demo/` matters · `evaluation/` good), signed evidence per phase. Built on an **earlier template generation** — no coverage gate, 4 harness suites not 18, no runtime chokepoint — and [its README says exactly which parts](examples/claims-build/README.md#what-this-example-predates). **Start here.** |
| [`examples/claims-agent/`](examples/claims-agent/evaluation/TEMPLATE-EVALUATION-REPORT.md) | Evaluation write-up only. | A live A/B build used to *test the template itself* — whether Claude could follow it, and whether the security kit actually changed the built agent. Useful as a critique of the harness. |
| [`examples/red-team-harness/`](examples/red-team-harness/) | Legacy — **pre-refactor layout**. | The original filled example (authorized penetration testing). Structurally dated (flat `governance/`, `observability/`, `tools/`), still useful for seeing policy tailored to a high-risk domain. |

Each example is self-contained: `cd` in and run `./init.sh`.

---

## Roadmap

### Runtime enforcement — the per-call half landed; the sequence-aware half has not

The chokepoint shipped on 2026-08-22 and is described in
[Wiring the four gates into a deployed application](#wiring-the-four-gates-into-a-deployed-application).
Three pieces of the original design are still **design only**, and they are the ones that
matter for the threats a per-call gate cannot see by construction:

| Still unbuilt | Why the shipped gate cannot cover it |
|---|---|
| **A tiered policy** returning ALLOW / REQUIRE_APPROVAL / DENY, with human-in-the-loop on high-risk actions | `execute()` is binary — it runs the tool or raises. There is no third outcome and no approval channel |
| **Session-cumulative state** — spend ceilings, call-chain rules, a strike counter | Every gate in the repo, hook and runtime alike, is stateless per call. Twenty $500 refunds each pass identically |
| **`/runtime-harden`**, the drafter that would produce a reviewed `policy.json` from your product docs | Today you hand-edit `mcp-allowlist.json`. Tracked as `SEC-HARDEN-GAP-001` |

The seam is unchanged and still the point: a **human signs** the policy file, and the
mechanism only ever reads it. A model may decide things a human reviews before they take
effect; it may not decide at request time when nobody is watching.

**→ Original design:
[`docs/superpowers/specs/2026-08-04-runtime-tool-mediation-design.md`](template/docs/superpowers/specs/2026-08-04-runtime-tool-mediation-design.md)**
— threat model (the eight threats a per-call gateway structurally cannot see) and the
mechanism inventory split into generic and agent-specific tiers. Read it as the design of
record, not as a description of what is built: the per-call chokepoint it specifies now
exists, the rest of it does not.

### The sub-agent layer

**There are no sub-agents in this repo today.** `template/.claude/` ships 4 slash commands
(`init-project`, `security-tailor`, `session-cycle`, `domain-workflow`) and no
`agents/` directory. The dashed lane in the architecture diagram is a design sketch, not
shipped code.

The intended direction: decompose the session loop into phase-scoped sub-agents — a
builder confined to the active phase, a verifier that only runs the declared verification
command, a security reviewer that diffs the control matrix, and an evaluator that writes
the snapshot. The hard requirement is that delegation must not become privilege
escalation: a sub-agent would pass the same four gates as its parent.

---

## Documentation

| Question | Read |
|---|---|
| How do I actually use this? | [`template/README.md`](template/README.md) |
| Why is it built this way? | [`template/Harness-Best-Practice/BEST-PRACTICES.md`](template/Harness-Best-Practice/BEST-PRACTICES.md) |
| What security controls exist? | [`template/Security-kit/SECURITY.md`](template/Security-kit/SECURITY.md) · [`owasp-crosswalk.md`](template/Security-kit/owasp-crosswalk.md) — mostly **build-time** framed; S1.6 is the runtime one |
| How do I secure the *deployed* agent? | [`SECURITY.md` S1.6](template/Security-kit/SECURITY.md) — the wiring, shipped and tested |
| What is *still* missing at runtime? | [`Runtime Security Architecture`](template/docs/superpowers/specs/2026-08-04-runtime-tool-mediation-design.md) — design of record; the per-call chokepoint in it is built, the tiered policy and session state are not |
| How is a claim of "good" measured? | [`template/evaluation/`](template/evaluation/) |
| Where did this come from? | [`.kiro/specs/harness-engineering-platform/`](.kiro/specs/harness-engineering-platform/) — origin spec, not current design |

---

## References & lineage

| Resource | Role |
|---|---|
| [Learn Harness Engineering](https://walkinglabs.github.io/learn-harness-engineering/en/) (13-lecture course) | The "why" — harness theory, lifecycle, the feature-triple and Fresh Session Test this template implements. |
| [Awesome Harness Engineering](https://github.com/Jiaaqiliu/Awesome-Harness-Engineering) | Primary-source map; the agent-vs-harness framing. |
| [Awesome Claude Code](https://github.com/hesreallyhim/awesome-claude-code) | The "how" — CLAUDE.md patterns, hooks, slash commands, subagents. |
| "Harness Engineering: Leveraging Codex in an Agent-First World" (OpenAI) | Credited with coining the term. |
| Anthropic — Building Effective Agents | Design principles for tool-use loops and permission boundaries. |
| [Claude Code on AWS Bedrock — Best Practices](https://github.com/timwukp/claude-code-on-aws-bedrock-best-practices) | Fail-closed hooks and managed-settings hierarchy; our guardrail + audit patterns echo it. |

---

## License

[MIT](LICENSE).
