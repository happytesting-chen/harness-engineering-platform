# The enforcement model: control plane and data plane

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
