# The deployed runtime tier

## Deployed runtime — the same gates, no hooks

Everything in [the enforcement model](01-enforcement-model.md) happens because Claude Code emits events. **The application you deploy
emits none**, so a shipped copy of this harness inherits its *design* and none of its
enforcement. Two modules close that, in process:

| Position | In your IDE session | In your deployed app |
|---|---|---|
| ① input, before the model | `prompt_screen.py` · `UserPromptSubmit` | `runtime_screen.screen_input()` |
| ② before a tool runs | `permission.py` · `PreToolUse` | `RuntimeDispatcher.execute()` |
| ③ the tool executes | — | — |
| ④ output, before the model | `result_screen.py` · `PostToolUse` | `runtime_screen.screen_result()`, on by default |

```python
import sys
sys.path.insert(0, "governance"); sys.path.insert(0, "Security-kit")
from runtime_dispatcher import RuntimeDispatcher
from runtime_screen import screen_input, InputRejected

dispatcher = RuntimeDispatcher({"fetch_article": fetch_article})   # ② ③ ④

def handle(request_text):
    try:
        prompt = screen_input(request_text, source="http")          # ①
    except InputRejected as exc:
        return {"error": str(exc)}, 400      # our words only — never echo the request
    return run_agent(prompt, tools=dispatcher)   # every call goes through execute()
```

Register each tool in `governance/mcp-allowlist.json` first — an unregistered tool denies
with `<name> not in allowlist`, which is Gate 2 working, not a bug. That file is a
protected path, so registering a tool is a **human** edit (S2.1, S5.2).

Four properties worth knowing:

- **`runtime_dispatcher.py` holds no second copy of any rule.** It imports
  `make_permission_check` from `governance/permission.py` and reads the same policy JSON, so
  the verdicts are the ones you already tested. A test asserts the file compiles no pattern
  and loads no policy of its own.
- **② prevents; ④ does not.** At ② nothing has happened yet, so `execute()` raises
  `PermissionError` and the tool is never called — `tests/test_runtime_dispatcher.py`
  asserts `calls == 0`, because a return-value-only assertion would pass either way. By ④
  the side effect is real, so a poisoned result is *substituted*, shape preserved, and the
  audit line records `WITHHELD` after the `ALLOWED`.
- **① fails closed, unlike its hook counterpart, and has no warn mode.** Input that cannot
  be scanned (anything not a `str`) is rejected rather than passed — `scan_text` returns
  `[]` for a non-`str`, so without the type check "unscannable" would be indistinguishable
  from "clean". There is deliberately no `RUNTIME_SCREEN_MODE=warn`: an env var that
  downgrades a request-boundary screen to report-only is a switch an attacker would prefer
  to the bypass.
- **④ has no off switch; ① and ② are opt-in.** Nothing forces your application to route
  through `RuntimeDispatcher` or to call `screen_input`. That residual is
  `SEC-RUNTIME-GAP-001`, and verifying the wiring is a human review item at deployment.

Full walkthrough: [`Security-kit/SECURITY.md`](../../template/Security-kit/SECURITY.md) S1.6. Proofs:
`tests/test_runtime_dispatcher.py` (20 tests) and `tests/test_runtime_screen.py` (17), both
run by `./init.sh`.

### The semantic tier — `Security-kit/runtime/`

The two modules above are the **regex tier**: the same 24 markers the hooks use, in
process. The `runtime-mvp` profile adds a second tier on top, in `Security-kit/runtime/`
(16 modules, stdlib only apart from the classifier subprocess). A deployed application
constructs one `RuntimeHost` and routes everything through its four methods:

| Method | Position | What it adds over the regex tier |
|---|---|---|
| `submit_prompt()` | ① | normalization (zero-width, bidi, encoded spans) → rules → a **pinned local classifier** on whatever the rules left unresolved. `unresolved + data` is the only ALLOW; every failure withholds |
| `invoke_tool()` | ② ③ ④ | the same four gates via `RuntimeDispatcher`, **composed** with per-tool and total session ceilings (position ⑤ — the first control there), origin rules (a turn tainted by external content cannot reach a user-only tool), argument schema, and an optional `REQUIRE_APPROVAL` tier |
| `deliver_tool_result()` | ④ | tool output through the same ingress; withheld text never enters context |
| `finish()` | output | the whole response buffered and redacted before one release |

Withheld content is quarantined by digest and released only through
`release_quarantined()` with a single-use `ContentReleaseReceipt`; an
`ActionApprovalReceipt` un-pauses a call but never converts a deny. Startup refuses a
misconfiguration — memory, delegation or streaming enabled, an unpinned classifier in
production, a writable control root — rather than degrading. Every decision lands in a
hash-chained audit record.

Contract, evidence and verdict: [`Context/runtime-security-profile.md`](../../template/Context/runtime-security-profile.md)
· [`evaluation/runtime-security/`](../../template/evaluation/runtime-security/). Measured: 13/13 attack
cases resisted on side-effect oracles; detection 14/16 with two named misses on the corpus
the verdict was signed against. Re-measured 2026-09-03 on a 40-case corpus that adds long,
structured and buried cases: 18/24 at the default chunk window, 20/24 at 600 chars, the
four remaining misses all workflow impersonation, 7–8 of 16 legitimate documents withheld
(logs, tables, security discussion). Details and the chunk-window recommendation in
`evaluation/runtime-security/classifier-selection.md`. **Routing is still opt-in**
(`SEC-RUNTIME-GAP-001`).

## The enforcement path (deployed runtime, no hooks)

The hook diagram in [Security kit internals](04-security-kit-internals.md) is an *event subscription*. A deployed application emits no hook events,
so none of it fires. The same four positions are available as in-process calls:

| Position | Build-time (hooks) | Deployed runtime (in-process) |
|---|---|---|
| ① input before the model | `prompt_screen.py` · UserPromptSubmit | `runtime_screen.screen_input()` |
| ② before a tool runs | `permission.py` · PreToolUse | `RuntimeDispatcher.execute()` |
| ③ the tool executes | — | — |
| ④ output before the model | `result_screen.py` · PostToolUse | `screen_result()`, on by default |

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

Four properties, and the reason for each:

- **No second copy of any rule.** `RuntimeDispatcher` imports `permission.py` and reads the
  same `deny-list.json` / `mcp-allowlist.json`. A policy edit moves both planes at once;
  there is no runtime deny-list to drift out of step.
- **② prevents, ④ does not.** `execute()` raises `PermissionError` *before* calling the
  tool, so the side effect never happens; `screen_result()` runs after it. The tests assert
  `calls == 0` after a ② denial and `calls == 1` after a ④ withholding — a return-value-only
  test would pass in both cases and prove nothing (S8.4).
- **① fails closed, with no warn mode.** `scan_text` returns `[]` for a non-`str`, so
  `screen_input` type-checks explicitly — otherwise "unscannable" would be
  indistinguishable from "clean". A rejected input raises; it is never passed through
  annotated.
- **④ has no off switch; ① and ② are opt-in.** Once a call goes through `execute()` its
  result is screened. The `result_screen=` argument exists to let an application *extend*
  the screen — passing `None` raises `ValueError` rather than skipping it, because a
  default argument is far too quiet a place to keep an off switch on a data-plane control.
  Whether any call goes through `execute()` at all is your application's decision, and
  nothing here verifies it (`SEC-RUNTIME-GAP-001`).

Registering a tool means adding it to `governance/mcp-allowlist.json`. An unregistered
tool denies with `<name> not in allowlist` — that is Gate ② working, not a bug. That file
is a protected path, so registering a tool is a **human** edit (S2.1, S5.2).

### Above the regex tier: `Security-kit/runtime/` (the runtime-mvp profile)

`runtime_dispatcher.py` and `runtime_screen.py` are the regex tier — the hooks' markers, in
process. The `runtime/` package (16 modules) adds what a per-call regex gate cannot have,
without touching the owners it composes around:

- **Semantic ingress** — `ingress.py`: normalization → rules → a pinned local classifier on
  rule-unresolved text. The rule layer never returns `data`; every classifier failure lands on
  `REQUIRE_REVIEW`. Withheld content is quarantined by digest.
- **Position ⑤** — `session.py` + `guarded.py`: per-tool and total ceilings, correct under
  concurrency, plus origin rules and argument schema, all wrapping `RuntimeDispatcher.execute()`.
  No gate predicate is re-implemented (source-scan tests pin this).
- **Separated review authority** — `review.py`: `ContentReleaseReceipt` and
  `ActionApprovalReceipt` differ by type *and* by derived key; neither converts a deny.
- **Refuse-to-start** — `startup.py`; **buffered output** — `output.py`; **hash-chained
  evidence** — `audit.py`; the owned loop — `host.py`.

All 16 modules and the signed `semantic-model.lock.json` are in `BUILTIN_PROTECTED_PATHS`.
Proof: 18 suites in `tests/runtime/`; evidence and the signed `DEPLOY_WITH_RULES` verdict in
[`evaluation/runtime-security/`](../../template/../evaluation/runtime-security/). Residuals R-1..R-3 and
`SEC-RUNTIME-GAP-001` (routing is opt-in) are stated in
[`Context/runtime-security-profile.md`](../../template/Context/runtime-security-profile.md).
