# Runtime Tool-Mediation Gate — Design Spec

**Status:** Draft for review (rev 1)
**Date:** 2026-08-04
**Scope:** Phase A only — a deployed-runtime tool-mediation gate for a single-agent
LangChain/LangGraph (+ framework-agnostic core) system, with human-in-the-loop approval
for high-risk actions. Ports the "reasoning proposes, mechanism enforces" shape from the
dev-time `governance/permission.py` into a gate that runs *inside the deployed product*.
Phase B (ingress screen, output/egress, full data-plane wiring) is deferred to its own
spec.
**Author:** brainstormed with Yuan Shi

---

## 1. Problem & Goal

### The gap

The existing Security-kit secures the **development** of the AI product. Its enforcement
lives in `.claude/settings.json` hooks (`permission.py`, `secret_scan.py`) that gate the
Claude Code agent *while it builds the code*. Exit-2 blocks a tool call at author time.

None of that runs after the product ships. Once the agent is deployed and calling its own
tools against real users and data, there is **no mechanical control** between the model's
decision and the side effect. The deployed agent has the same failure mode the dev-time
kit was built to prevent — a persuaded or confused model taking a dangerous action — but
none of the enforcement.

### The goal

Port the dev-time enforcement shape into the deployed runtime: a **tool-mediation gate**
that every tool call passes through, sitting **outside the model**, that the model cannot
see, edit, or route around.

The single principle, unchanged from `permission.py`:

> **Reasoning proposes, mechanism enforces.** The LLM is never a control surface.
> Enforcement is deterministic code the model cannot influence. The system prompt is
> *steering*, not *enforcement* — it is explicitly NOT a control point.

Phase A delivers exactly one boundary: the **tool/action gate** (boundary ③ in the map
below). It adds one capability the dev-time binary gate lacks — a third outcome,
**REQUIRE_APPROVAL**, routing high-risk actions to a human instead of a flat allow/deny.

### The trust-boundary map (context; Phase A implements only ③)

```
        ┌─────────────────────────────────────────────┐
   ①───▶│                                             │
 ingress │        UNTRUSTED MODEL CORE (the LLM)       │───▶ ⑤ output / egress
 screen  │   proposes tool calls; never enforces       │      (Phase B)
        │                                             │
        └───────────────────┬─────────────────────────┘
   (Phase B)                │ proposes an action
                            ▼
                   ③  TOOL / ACTION GATE      ◀── Phase A (this spec)
                   deterministic decide()
                   ALLOW / DENY / REQUIRE_APPROVAL
                            │
              ┌─────────────┼──────────────┐
              ▼             ▼              ▼
           run tool   blocked-obs str   approval_fn (human)
              │             │              │
              └─────────────┴──────────────┘
                            ▼
                   ⑥  AUDIT (every decision)  ◀── Phase A (reuses audit.py)

   ④  content screen (tool results / RAG) — data-plane, Phase B
```

Phase A: boundaries **③** (gate) and **⑥** (audit). Boundaries ①, ④, ⑤ are Phase B.

### Non-goals (explicit scope cuts)

- **No ingress screening.** Screening untrusted user input / retrieved content
  (boundary ①/④) is Phase B. `content_trust.py` already exists as the data-plane
  library; wiring it is a separate cycle.
- **No output/egress gate.** Boundary ⑤ is Phase B.
- **No async/durable approval.** Phase A's approver is **synchronous** (blocking
  in-request). The `ApprovalRequest` is designed serializable so a durable/async
  approver can be added in Phase B without touching the core.
- **No policy authoring by the agent.** The deployed agent cannot edit `policy.json`.
  Policy is human-owned, exactly as `deny-list.json` is in the dev-time kit.
- **No new controls invented.** This is a mechanism, not a control catalog. What counts
  as high-risk is declared in `policy.json` by a human.
- **No non-stdlib dependency in the core.** `policy_core.py` and `policy_schema.py` are
  pure stdlib. The framework adapters import LangChain/LangGraph only where the host app
  already has them.

---

## 2. Architecture & Data Model

### Module layout

```
Security-kit/runtime/
├── __init__.py
├── policy_core.py      ← pure decide(action, policy) -> Decision  (stdlib only)
├── policy_schema.py    ← load + validate policy.json (fail-closed)  (stdlib only)
├── policy.json         ← the policy (human-owned; agent cannot edit)
├── guard.py            ← guard(tool, ...) wrapper — the enforcement seam
├── approval.py         ← cli_approval_fn reference implementation
└── README.md           ← how to wrap a tool in the three host shapes
tests/
├── test_policy_core.py ← table-driven, stdlib assert (no LLM, no pytest)
└── test_guard.py       ← wrapper control-flow, fake tool + fake approver
```

`policy_core.py` is the analogue of `permission.py`'s three `check_*` functions; `guard.py`
is the analogue of `make_permission_check()`'s closure + the CLI `__main__` wiring; the
audit sink is `Harness-Best-Practice/observability/audit.py` reused **as-is**.

### Data model (frozen dataclasses)

```python
# An action the model proposed. Built by guard() from the tool call.
@dataclass(frozen=True)
class Action:
    tool: str                      # normalized tool name
    args: dict                     # keyword args the model supplied
    agent_id: str = ""             # for audit
    session: str = ""              # for audit

# The gate's ruling. Three outcomes (the runtime addition over permission.py).
Outcome = str  # "ALLOW" | "DENY" | "REQUIRE_APPROVAL"

@dataclass(frozen=True)
class Decision:
    outcome: Outcome
    reason: str                    # human-readable; shown in blocked-obs + audit
    tier: str = ""                 # which risk tier matched (for audit)
    rule: str = ""                 # which rule fired (for audit / debugging)

# Serializable so a Phase-B durable approver can reconstruct it.
@dataclass(frozen=True)
class ApprovalRequest:
    action: Action
    decision: Decision             # the REQUIRE_APPROVAL decision that triggered it

@dataclass(frozen=True)
class ApprovalResponse:
    approved: bool
    approver: str = ""             # who decided (for audit)
    note: str = ""
```

`ApprovalFn = Callable[[ApprovalRequest], ApprovalResponse]` is the injected seam. Phase A
ships `cli_approval_fn`; a host swaps in Slack/web/queue later without changing the core.

---

## 3. policy.json Schema

Declarative, human-owned. Evaluation order is fixed in `decide()`; the policy only
supplies data. Shape:

```json
{
  "deny":  ["delete_account", "wire_transfer_external"],

  "allow": ["search", "get_weather", "read_doc"],

  "risk_tiers": {
    "read":   { "outcome": "ALLOW" },
    "write":  { "outcome": "REQUIRE_APPROVAL" },
    "danger": { "outcome": "DENY" }
  },

  "tool_tiers": {
    "send_email":   "write",
    "issue_refund": "write",
    "run_sql":      "danger"
  },

  "arg_rules": [
    { "tool": "issue_refund", "when": {"field": "amount", "op": ">", "value": 10000},
      "escalate_to": "danger", "rule": "refund>10k is danger" },
    { "tool": "send_email", "when": {"field": "to", "op": "regex", "value": "@(?!ourco\\.com$)"},
      "escalate_to": "write", "rule": "external recipient needs approval" }
  ]
}
```

### Field semantics

| Field | Meaning |
|---|---|
| `deny` | Tools blocked unconditionally. **Deny wins over everything** (ported from `permission.py` gate ordering). |
| `allow` | Tools with an implicit `ALLOW` base outcome and no tier. Convenience for read-only tools. |
| `risk_tiers` | Named tiers → base outcome. The three canonical tiers are read/write/danger but the set is open. |
| `tool_tiers` | Maps a tool to its base tier. A tool here inherits that tier's `outcome`. |
| `arg_rules` | Declarative per-argument escalation. `when` matches an arg; `escalate_to` raises the tier. **Escalate only — never de-escalate** (preserves deny-wins / fail-toward-safety). |

### Evaluation order (fixed in `decide()`, not in policy)

```
1. deny-list         → tool in `deny`?                         → DENY   (wins)
2. resolve base tier → tool_tiers[tool] or (allow→ALLOW)       → base outcome
3. unknown tool      → not in deny/allow/tool_tiers?           → DENY   (fail closed, Q5=A)
4. arg_rules         → any `when` matches? escalate tier       → raised outcome
5. tier → outcome    → risk_tiers[final_tier].outcome          → final Decision
```

Step 3 is the fail-closed default: **a tool the policy never mentions is DENIED**, not
allowed. This is the runtime analogue of `permission.py:96` `"{tool} not in allowlist"`.

### `arg_rules` operators

`op` ∈ `{ ">", ">=", "<", "<=", "==", "!=", "contains", "regex" }`. Numeric ops coerce
both sides to float and skip (no match) on coercion failure. `regex` uses `re.search`; a
**malformed regex falls back to substring match** rather than crashing the gate — ported
verbatim in spirit from `permission.py:59-60` (`except re.error: hit = pat in command`).

---

## 4. The guard() Wrapper + Approval Flow

### Contract

```python
def guard(
    tool,                       # the callable to protect (any signature)
    *,
    policy,                     # loaded Policy object
    approval_fn,                # ApprovalFn — injected human seam
    audit=audit.record,         # sink; defaults to the reused audit.py
    agent_id="",
    session="",
):
    """Return a same-signature callable that enforces `policy` before running `tool`."""
```

`guard(tool)` returns a wrapper with the **same call signature** as `tool`. The gate *is*
the tool — the host registers the wrapped callable, so there is no un-wrapped path the
model can reach. This is the enforcement property: you cannot bypass the gate because the
gate replaced the tool.

### Per-call flow

```
wrapped(**kwargs):
    action  = Action(tool.name, kwargs, agent_id, session)
    decision = policy_core.decide(action, policy)      # pure, deterministic

    if decision.outcome == ALLOW:
        audit(..., decision="ALLOW")
        return tool(**kwargs)                          # run the real tool

    if decision.outcome == DENY:
        audit(..., decision="DENY")
        return _blocked_observation(decision)          # a STRING, never raises

    if decision.outcome == REQUIRE_APPROVAL:
        try:
            resp = approval_fn(ApprovalRequest(action, decision))
        except Exception as e:
            audit(..., decision="DENY", reason=f"approver error: {e} (fail closed)")
            return _blocked_observation(...)           # fail closed (Q5=A)
        if resp.approved:
            audit(..., decision="APPROVED", reason=resp.approver)
            return tool(**kwargs)
        audit(..., decision="DENIED_BY_APPROVER")
        return _blocked_observation(...)
```

### The critical choice: DENY returns an observation, does not raise

A blocked call returns a **string** back into the agent loop, e.g.:

```
⛔ blocked by policy: refund>10k is danger (rule: refund>10k is danger, tier: danger)
```

The model sees this as a normal tool observation and can react (explain to the user, try a
smaller amount, give up) — but it **cannot override it**. Raising an exception instead
would either crash the agent or hand control-flow decisions to model-visible `try/except`
in the host loop; a returned observation keeps enforcement outside the model while letting
the loop continue. Every error-path DENY (§5.1) uses this same return, so the model cannot
distinguish a policy deny from an approver crash — both are opaque blocks.

### Three host attach points (one mechanism, three surfaces)

- **LangChain tool:** wrap the tool's function before constructing the tool object. The
  exact call (`StructuredTool.from_function(guard(fn, ...))` vs decorating a `@tool`) is
  flagged `[unverified]` pending doc confirmation at implementation time.
- **LangGraph `ToolNode`:** register the wrapped callables in the node's tool list; the
  node dispatches to the wrapper, not the raw tool.
- **Custom loop:** call `guard(tool, ...)` once at registration; the loop's dispatch table
  holds wrappers only.

---

## 5. Error Handling + Testing

### 5.1 Fail-closed behavior (the load-bearing invariant)

Every error path resolves to **DENY**, never allow-all.

| Failure | Where | Ruling | Ported from |
|---|---|---|---|
| Missing `policy.json` | `policy_schema.load()` | Sentinel deny-all `Policy` → every action DENIED, reason `"policy load failed: <path> not found (fail closed)"` | `permission.py:171-180` |
| Malformed `policy.json` | `policy_schema.load()` | Same sentinel, reason `"policy parse failed (fail closed)"` | same |
| Bad regex in an `arg_rule` | `policy_core.decide()` | That rule falls back to substring match — never crashes | `permission.py:59-60` |
| Unknown tool | `policy_core.decide()` | DENY, `"unknown tool: <name> (fail closed)"` | `permission.py:96` |
| `approval_fn` raises | `guard()` | DENY, `"approver error: <exc> (fail closed)"` | new (runtime addition) |
| `approval_fn` times out | `cli_approval_fn` / `guard()` | DENY, `"approval timed out after Ns (fail closed)"` | new |

**The sentinel deny-all policy is a real `Policy` object, not `None`.** `decide()` never
null-checks — it always receives a valid policy whose every lookup misses, so every action
falls through to unknown-tool DENY. Malformed config cannot produce a code path that skips
the gate.

### 5.2 Test strategy — deterministic, stdlib only

No LLM, no pytest, no network. Plain `assert` + `if __name__ == "__main__"` runners,
matching `tests/test_fixtures.py`.

**`tests/test_policy_core.py`** — table-driven over `decide()`; each case a
`(action, policy, expected_outcome, expected_reason_substr)` tuple:

1. allow-listed tool, no risky args → **ALLOW**
2. deny-listed tool → **DENY** (deny wins)
3. tool in a `REQUIRE_APPROVAL` tier → **REQUIRE_APPROVAL**
4. arg-rule raises tier (`amount > 10000`) → base ALLOW becomes **REQUIRE_APPROVAL**
5. arg-rules can only escalate, never de-escalate (deny-wins property holds)
6. unknown tool → **DENY** `"unknown tool"`
7. tool in a DENY-outcome tier → **DENY**
8. bad regex in an arg-rule → substring fallback, evaluates, no exception
9. missing policy (sentinel) → every case **DENY** `"fail closed"`

**`tests/test_guard.py`** — wrapper control flow, fake tool (records if it ran) + fake
`approval_fn` (scripted response or raises):

1. ALLOW → underlying tool **runs**, real result returned
2. DENY → tool **never runs**, blocked-observation **string** returned (assert `isinstance str`, not exception)
3. REQUIRE_APPROVAL + approver yes → tool runs
4. REQUIRE_APPROVAL + approver no → tool doesn't run, blocked-observation returned
5. approver **raises** → DENY, tool doesn't run (fail-closed)
6. every decision path → **one `audit.record` line written** with the correct decision

Case 6 is the important one: it proves the audit sink fires on *every* path — nothing the
gate does is invisible, the same property `audit.py` gives the dev-time kit.

### 5.3 Deliberately NOT covered (scope honesty)

- **Not tested:** real LangChain/LangGraph attach — needs the framework installed;
  deferred to a Phase A integration smoke test, with the wrapping call flagged
  `[unverified]` until confirmed against docs.
- **Not tested:** concurrent/async approval durability — Phase A approver is synchronous
  (Q2=A); the async/durable approver is a Phase-B seam (`ApprovalRequest` already
  serializable).
- **Not tested here:** ingress screening (①/④) and output/egress (⑤) — Phase B entirely.

The eval axes from `evaluation/eval.py` (accuracy/reproducibility/latency/cost) apply
cleanly to `decide()` later — it is a pure `case → decision` function, exactly the
`decide_fn` shape `evaluate()` expects — but wiring that is a nice-to-have, not part of the
Phase A gate.

---

## 6. Relationship to the Dev-Time Kit

| Concern | Dev-time (`permission.py`) | Runtime (this spec) |
|---|---|---|
| Protects | the agent that **builds** the product | the **deployed** agent |
| Trigger | `.claude/settings.json` PreToolUse hook | `guard()` wrapper around each tool |
| Block signal | exit code 2 | blocked-observation string |
| Outcomes | allow / deny (binary) | allow / deny / **require-approval** |
| Policy source | `deny-list.json` + `mcp-allowlist.json` | `policy.json` |
| Fail-closed | empty/malformed stdin → exit 2 | missing/malformed policy → deny-all sentinel |
| Audit sink | `observability/audit.py` | **same** `audit.py`, reused |
| Bad regex | substring fallback | **same** substring fallback |

Same shape, same discipline, ported to run inside the shipped product. Phase A is the gate;
Phase B extends the boundary map to ingress, egress, and the data-plane content screen.

---

## 7. Phasing

- **Phase A (this spec):** boundaries ③ (gate) + ⑥ (audit). `policy_core.py`,
  `policy_schema.py`, `policy.json`, `guard.py`, `approval.py`, two stdlib test files.
- **Phase B (own spec/plan cycle):** boundary ① (ingress screen, wiring `content_trust.py`),
  boundary ④ (tool-result / RAG screen), boundary ⑤ (output/egress gate), async/durable
  approval, optional eval wiring for `decide()`.
