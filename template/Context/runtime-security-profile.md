# Runtime Security Profile — runtime-mvp

> Created by Task 1 of
> `docs/superpowers/plans/2026-08-31-runtime-security-semantic-enforcement-rescoped.md`.
> Pinned by `tests/runtime/test_design_contract.py` — the terms below are load-bearing
> vocabulary for later tasks, and this file ceasing to name one of them is a test failure,
> not an editorial choice.

## Two profiles, not one

| Profile | What it is | Enforcement |
|---|---|---|
| `demo` | The accepted local demo and the IDE build-time session. Local, deterministic, provider-free, standard-library based | Hook screens (regex-only, see R-3) + `permission.py` via PreToolUse. Unchanged by this plan |
| `runtime-mvp` | One owned host, one agent, a fixed registered tool set, UTF-8 text ingress, no persistent memory, no delegation | Binding `ON_INGRESS` (rules + semantic) + binding `ON_ACTION` (deterministic gate) + buffered output screen |

The `demo` profile is not silently redefined as production. A `runtime-mvp` claim applies
only to a deployment that starts through the runtime host's startup validation.

## Binding boundaries

- **`ON_INGRESS`** — every supported prompt, tool result and document text field becomes a
  `ContentEnvelope`, is normalized, rule-screened, and (when rules do not already
  withhold) semantically classified. Outcomes: `ALLOW` or `REQUIRE_REVIEW`. Non-`data`
  content is withheld from model context and quarantined. The rule layer never returns
  `data`; classifier timeout, crash, malformed output or digest drift is `REQUIRE_REVIEW`,
  never an allow.
- **`ON_ACTION`** — every registered tool call passes the deterministic gate before the
  side effect. No model, classifier or LLM decides this verdict. Denied means the tool is
  never called (`calls == 0`).
- **Review receipts** — quarantined content is releasable only by an exact-digest,
  expiring, single-use **`ContentReleaseReceipt`**; a paused sensitive action proceeds
  only on an **`ActionApprovalReceipt`**. The two types are cryptographically
  domain-separated: a content release can never authorize an action, an action approval
  can never mark content safe, and no receipt converts `DENY` to `ALLOW`.

## Capabilities disabled in the MVP

Corrected 2026-09-01 after review (findings F-4, F-5, F-6): these are disabled, but they
are **not all enforced in the same place**, and the earlier wording claimed every one was a
startup error. Where a prohibition is enforced matters more than that it is written down.

In one line, for the record and for the contract test that pins this vocabulary — **persistent memory: disabled**, **delegation: disabled**, streaming output disabled, remote classifiers disabled, binary ingress disabled.

| Capability | Status | Enforced where |
|---|---|---|
| persistent memory | disabled | **startup error** — `validate_startup` |
| delegation (inter-agent messaging, subagent spawning) | disabled | **startup error** — `validate_startup` |
| streaming output | disabled | **startup error** — `validate_startup` |
| remote or hosted classifiers | disabled | **startup error in production** — the host requires `classifier_lock_path` and verifies the signed artifact digests. Outside production a stub is permitted; that is the `demo` profile |
| arbitrary binary extraction (PDF/image/archive) | disabled | **contract layer, per envelope** — `ContentEnvelope` rejects any `media_type` but `text/plain`. Not a startup check, because the constraint is per-item, not per-run |
| additional hosts / multi-host operation | out of scope | **not enforced.** A library cannot stop a caller constructing two hosts. The MVP is specified for one; nothing mechanically prevents otherwise, and the earlier claim of a startup error was wrong |

Enabling any of them is a new source/sink and requires a later separately approved plan.

## Sources and sinks (MVP)

| Source | Boundary | Sink |
|---|---|---|
| User prompt | `ON_INGRESS` (USER_DIRECT) | model context, then tools |
| Tool result / document text | `ON_INGRESS` (EXTERNAL_CONTENT) | model context, then tools |
| Structured record | field allowlist, then `ON_INGRESS` per text field | model context — via `adapters.ingress_structured_record`, called by the application; the host exposes no method for it (F-2) |
| Review decision | receipt verifier | context release, via `RuntimeHost.release_quarantined` (F-1, added 2026-09-01) |
| Model tool proposal | `ON_ACTION` | registered tool side effect |
| Model final response | buffered output screen | user |

## Residuals (stated, not hidden)

- **R-1** — the semantic classifier is the content-release authority for rule-clean
  content. A fooled classifier admits content; the deterministic action gate is then the
  only control standing.
- **R-2** — fail-closed ingress makes the review queue floodable; the deployment must
  state a queue bound or record unbounded review load as an accepted risk with an owner.
- **R-3** — semantic screening covers the `runtime-mvp` profile only. The `demo` /
  build-time hook path stays regex-only, deliberately (latency; hook crash semantics).
