# Build-time enforcement: how it fires while you build

![Control plane with four gates, data plane content boundary, planned sub-agent lane](../../assets/architecture.svg)

The build-time harness runs inside Claude Code. Every matched tool call passes the control
plane before it executes; every untrusted record passes the data plane before it reaches the
agent's context. Nothing here exists in the deployed application — that surface is
[Deployed runtime](03-deployed-runtime.md).

## Control plane — the permission gate (tool calls)

Every `Bash`/`Write`/`Edit` is piped through `governance/permission.py` by a
`.claude/settings.json` PreToolUse hook. Four gates run in order, **fail-closed** (first
denial wins; malformed input, empty input and an unparseable policy file are all denied,
not allowed):

| # | Gate | Blocks when… | Config |
|---|---|---|---|
| 1a | **Protected paths** | the write target *is* a mechanism or policy file (control S2.4) | built-in floor + `governance/deny-list.json` (additive only) |
| 1b | **Deny-list** | command matches a hard-blocked pattern | `governance/deny-list.json` |
| 2 | **Phase-gate** | tool isn't in the allowlist, or its `gated_until` phase is not listed in `signed_off_phases` | `governance/mcp-allowlist.json` (which phase is *active* still comes from `Harness-Best-Practice/feature_list.json`) |
| 3 | **Egress** | a destination — in a shell command, or in one of 9 structured fields (`url`, `uri`, `endpoint`, `host`, …) at any depth, for **any** tool — is not an **exact** match for an `egress_hosts` entry. A subdomain must be asked for as `*.example.com` | `governance/mcp-allowlist.json` |

`exit 0` = allow, `exit 2` = **BLOCK**. The gate's *logic* is proven by
`tests/test_hooks.py` (which feeds each hook script a JSON envelope on stdin and asserts
the exit code) and the S2.4 gate by `tests/test_protected_paths.py`. What no test can
prove is that **your host is actually calling those scripts** — that is configuration, not
code, and it is the first thing to check: see [Test the runtime](../../template/README.md#test-the-runtime).

**Why the unlock lives in the allowlist, not the worklog.** Gate 2 answers two questions
from two different files on purpose. *Which phase is active?* comes from
`feature_list.json`, the agent's own worklog, which must stay writable so the agent can
record progress. *Is a gated tool unlocked?* comes from `signed_off_phases` in
`mcp-allowlist.json`, which is a **protected path** and therefore human-only. Before that
split, the unlock was read from the worklog's `status` field, so an agent could grant
itself a gated tool by marking its own phase `passing`. An empty or absent
`signed_off_phases` means no phase is signed off, so every gated tool stays locked — it
fails closed.

Gate 1a runs first because it has a built-in floor and can still answer when the policy
file is unreadable — see [`Security-kit/README.md`](../../template/Security-kit/README.md) for why that
ordering matters, and `governance/ARCHITECTURE.md` for the interface contract.

## Data plane — content trust (untrusted input)

Tool gates can't see a threat that arrives as *data* — e.g. prompt injection inside a
claim body. `Security-kit/content_trust.py` owns one shared list of instruction-shaped
markers, and it is enforced at the **two points where text reaches the model**:

| Position | Hook | Script | Effect |
|---|---|---|---|
| ① the prompt | `UserPromptSubmit` | `Security-kit/prompt_screen.py` | exit 2 **erases the prompt** before the model sees it |
| ④ the tool result | `PostToolUse` | `Security-kit/result_screen.py` | **replaces the tool output** via `updatedToolOutput` before the model reads it |

Both are already wired in `.claude/settings.json`; you do not call them. They share one
marker list on purpose, so a detection change moves both at once. Set
`PROMPT_SCREEN_MODE=warn` or `RESULT_SCREEN_MODE=warn` to downgrade either to
report-only.

**These two are different controls, not two copies of one.** ① fires once per *human*
turn and never for a subagent — so while an agent is looping, ④ is the only pre-model
screen anything passes through. ④'s matcher is `*`, so unlike the permission gate it sees
every tool, including `Agent`/`Task` and MCP results.

**Enforcement is exact; detection is not.** The marker list is a fixed set of patterns.
Measured against the labelled corpus in `Security-kit/eval/corpus/injection/`: **10 of 12
attacks caught, and 2 of 12 legitimate records withheld** — a base64-encoded payload and a
narrative paraphrase get through, and real policy text containing "no further approval"
gets withheld. Those four numbers are pinned by `tests/test_injection_corpus.py` so they
cannot drift silently. Widening the markers moves cases into the false-positive column;
that trade is the reason the pair is pinned rather than tuned.

Separately, `content_trust.py::screen_record()` is a **library you call yourself** where
structured untrusted records enter your code. It **drops injected control fields** (a
claim smuggling `{"decision":"APPROVE"}`) and **flags instruction-shaped text** so the
caller lowers trust and routes to a human. Nothing in the template calls it — that wiring
is yours. It reports; it never obeys. Proven by `tests/test_content_trust.py`.

## The enforcement path: events, hooks, scripts

### The enforcement path (dev-time, live today)

```
  agent decides to act
        │
        ▼
  ┌──────────────┐   PreToolUse fires ONLY for these five tools:
  │  tool call   │   Bash | Write | Edit | MultiEdit | NotebookEdit
  └──────┬───────┘   (the `matcher` in .claude/settings.json)
         │
         │  JSON envelope on stdin: {"tool_name": …, "tool_input": {…}}
         │
         ├───────────────────────────────┬──────────────────────────────┐
         ▼                               ▼                              │
 ╔═════════════════════════════╗  ╔═══════════════════════════╗         │
 ║ governance/permission.py    ║  ║ Security-kit/             ║         │
 ║ four gates, in order,       ║  ║   secret_scan.py          ║         │
 ║ FIRST DENIAL WINS           ║  ║ credential patterns in    ║         │
 ║                             ║  ║ content / command /       ║         │
 ║ ①a protected paths  (S2.4)  ║  ║ new_string                ║         │
 ║ ①b deny-list  command pats  ║  ╚═════════════╤═════════════╝         │
 ║ ②  phase-gate               ║                │                       │
 ║ ③  egress                   ║                │                       │
 ╚══════════════╤══════════════╝                │                       │
                │                               │                       │
                └───────────────┬───────────────┘                       │
                                ▼                                       │
                     ┌────────────────────┐                             │
        exit 2  ◄────┤   what happened?   ├────►  exit 0                │
        BLOCKED      └────────────────────┘       PROCEEDS ─────────────┘
     reason printed            │                                        │
     to the agent              │  anything else (crash, timeout)        ▼
                               └──►  hook ERROR — tool STILL PROCEEDS   │
                                                                        ▼
                                             PostToolUse → audit.log (append-only)
```

**Only exit 2 blocks.** Every other outcome silently allows — that one fact drives the
whole design. It is why the gate must never crash, and why the exit code, not the
reasoning, is the control.

Three consequences worth naming, all in `permission.py`:

- **Bad input denies.** Empty stdin, malformed JSON and a wrong payload shape all exit 2
  (the `_deny(...)` calls in CLI mode) rather than erroring out.
- **Untrusted policy denies.** A policy file that exists but will not parse raises
  `PolicyError`, which CLI mode converts to exit 2. Before that, a `JSONDecodeError`
  escaped as exit 1 — a *non-blocking* hook error — so one corrupt JSON file disabled
  both hard-deny gates, S2.4 included.
- **Unknown tools deny.** `check_phase_gate` ends in `return f"{tool_name} not in
  allowlist"`, so a tool nobody approved is refused rather than waved through.

Gate ①a runs **before** the command patterns on purpose: it has a built-in floor
(`BUILTIN_PROTECTED_PATHS`) and so still returns a verdict when policy is unreadable,
whereas the deny-list has nothing to fall back on.

> Citations here name **functions and constants, not line numbers** — deliberately. The
> previous revision cited `:32/:66/:99`, and every one of those anchors broke the moment
> Gate 1a was inserted above them. Names survive edits; line numbers rot silently.

![The feature triple and the phase state machine](../../assets/feature-lifecycle.svg)
