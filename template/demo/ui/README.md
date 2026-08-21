# Interactive gate viewer

A browser UI over the real permission gate. Every verdict on screen is an exit code
from `governance/permission.py` — the same CLI the PreToolUse hooks in
`.claude/settings.json` invoke.

```bash
python3 demo/ui/server.py
```

Serves `http://127.0.0.1:8765/`. Zero dependencies — Python 3.11+ stdlib only.
`--port N` to move it, `--no-browser` to skip opening a tab.

## Two pages

| Route | For | Shape |
|---|---|---|
| `/` | Anyone who has 90 seconds | One attack, four beats, one diagram |
| `/detail` | Whoever wants to argue with it | Sixteen presets, a free-form composer, the gap catalogue |

Start at `/`. It runs a single indirect prompt injection end to end: a poisoned
supplier page comes back from a tool, the model believes it, the model asks to POST
your AWS credentials to an attacker, and the gate returns exit 2. Then a diagram of
the loop showing why the block landed where it did.

**The headline is deliberate.** The injection is not blocked — it cannot be. Nothing
preventive stands where a tool result re-enters the context (`SEC-RESULT-GAP-001`),
and `content_trust.py` reports rather than refuses even once wired. What the template
blocks is the *action the injection was trying to cause*, one step later, at the only
boundary where refusing is still possible. A demo captioned "injection blocked" would
be selling something this repo does not have.

Beats 1, 3 and 4 are measured. Beat 2 — the model changing its mind — is scripted,
and the page says so on the beat itself: a defence you can only demonstrate with a
cooperative model is not a defence.

## What `/detail` shows

Three bays, left to right: the tool call the model wants to make, the four gates in
the order `permission.py` evaluates them, and the verdict — exit code plus stderr,
verbatim.

The presets are grouped by what they prove:

| Group | What it demonstrates |
|---|---|
| **The gate stops these** | Nine calls the mechanism denies, one per gate, including three spellings of the same protected file |
| **The gate permits these** | Three calls that clear all applicable gates — the demo is not a rigged "everything is denied" |
| **Known open** | Four calls that are harmful and still allowed. Each cites its gap ID in `Security-kit/control-matrix.md` |

The **Sign off phase-01** button flips the scratch feature list, and the `deploy_release`
preset goes from exit 2 to exit 0. That is a real policy transition, not a scripted
animation.

## What it is not

- **Not the enforcement path.** Production enforcement is the hooks in
  `.claude/settings.json`. This is a window onto the CLI they call, so it is exactly
  as good as that CLI and no better.
- **It never executes the command.** Whatever you type becomes JSON on another
  process's stdin. Nothing here shells out to it, in either enforcement mode.
- **It never touches your policy files.** `demo/demo.py` overwrites the real
  `governance/*.json` and restores them in a `finally`; this server copies into
  `tempfile.mkdtemp()` instead, so an interrupted demo cannot leave your policy
  modified. The scratch tree is removed on exit.
- **Gate attribution is read back, not predicted.** The server matches the reason
  string the gate returned against the strings in `permission.py`'s four `check_*`
  functions. It does not decide in advance which gate should fire.
- **Denials only in the audit panel.** `permission.py` writes an audit line from
  `_deny` and nowhere else; allowed calls are logged by the PostToolUse hook, which
  is not running here.
- **Enforcement off does not run anything.** It reports that the verdict was produced
  and then ignored — which is what removing the hook actually does, pinned by
  `tests/test_e2e.py::test_removing_enforcement_allows_dangerous_call`.

## Why a scratch tree works

`permission.py` resolves its policy relative to its own `__file__`, not the working
directory (`PROJECT_ROOT = Path(__file__).parent.parent`). A copy of the gate in a
temp tree therefore reads that tree's policy. The gate and `deny-list.json` are
copied byte-for-byte, and the masthead shows a SHA-256 of each so you can check.

Two files are substituted, and `/api/context` reports every substitution:
`mcp-allowlist.json` and `feature_list.json` ship with `{{GATED_TOOL}}` and
placeholder phase names, so there is no gated tool to demonstrate until something
fills them. The viewer fills them with `deploy_release` and three plausible phases.
Statuses are left as shipped — phase-01 `active`, the rest `not-started`.

## Requires the security kit

A project installed with `install.sh --no-security` has no `governance/` directory.
The server refuses to start and says so, rather than failing obscurely.

## Customising

`demo/ui/*` is **Customise** tier, like `demo/demo.py` — see
[`demo/ARCHITECTURE.md`](../ARCHITECTURE.md). Edit `PRESETS` in `app.js` for the
instrument panel, or the three constants at the top of `story.js` — the poisoned
document, the model's plan, the command it asks for — to retell the walkthrough with
your own attack. Two rules if you do:

1. **Stdlib only.** No `pip install`, no CDN `<script>` tags. The demo has to run on
   a laptop with no network.
2. **Never assert a verdict the gate did not produce.** A preset supplies the
   envelope; the exit code and reason come back from the gate. If you hardcode an
   expected result anywhere, the demo stops being evidence and becomes a slide.
