# Init Project

> Purpose: Turn a freshly-copied template into a configured project by reading the
> product definition in `Context/` and filling the harness files — flagging anything
> that cannot be confidently derived for human clarification.

Run this once, right after copying the template and adding your product docs.

## Preconditions

1. The template has been copied into a new project folder and you are in its root.
2. The user has placed product-definition docs in `Context/` — at minimum a
   product/design doc; ideally also `architecture.md`, `ai-stack.md`, `deployment.md`.
   If `Context/` has only its `README.md` and the `.template` stubs, **stop** and ask
   the user to add at least one product doc first.

## Step 1 — Read the product definition

Read every non-template file in `Context/`. Build an understanding of:
- **What** the agent does (product/design) and its success criteria.
- **AI stack** — framework + model (from `ai-stack.md` if present).
- **Deployment** — on-prem/cloud, egress needs, data sensitivity (`deployment.md`).
- **Architecture** — components, tools the agent calls, external integrations, phases/milestones.

## Step 2 — Draft, do not finalize

From that understanding, prepare drafts for:

| File | Fill from Context/ |
|------|--------------------|
| `CLAUDE.md` | `{{PROJECT_NAME}}`, `{{PROJECT_PURPOSE}}`, `{{PRIMARY_VERIFICATION_COMMAND}}`, `{{DENY_LIST_SUMMARY}}`, `{{DOMAIN_ESCALATION_RULES}}`, `{{DOMAIN_CONTEXT_LINKS}}` |
| `Harness-Best-Practice/AGENTS.md` | name, purpose, `{{LANGUAGE}}`, verification command |
| `Harness-Best-Practice/feature_list.json` | phases derived from architecture milestones — each with behavior + a real verification command + status (`phase-01` active, rest not-started) |
| `Harness-Best-Practice/progress.md` | session-1 state: what Context/ defined, what was auto-filled, open questions |
| `Security-kit/governance/mcp-allowlist.json` | the tools the architecture says the agent uses (+ `gated_until` for risky ones); `egress_hosts` from deployment |
| `Security-kit/governance/deny-list.json` | add domain patterns implied by the design (keep catastrophic defaults) |
| `Security-kit/control-matrix.md` | one row per trust boundary the design introduces (tool, egress, untrusted input) |

## Step 3 — FLAG every uncertainty (do not guess)

For each value you cannot derive **with confidence** from `Context/`, do NOT invent one.
Collect them into a single **Clarification Needed** list and present it to the user, e.g.:

```
Clarification needed before I finish init:
1. Verification command — Context/ doesn't specify how to prove phase-01 works. What command should exit 0?
2. Egress — architecture mentions "notify the user" but not the host/endpoint. Which host goes in egress_hosts?
3. Phase breakdown — I inferred 3 phases from architecture.md; is that the intended sequence?
```

Ask, wait for answers, then incorporate them. This honors the harness rule: the repo is
the single source of truth, so gaps must be resolved explicitly, not filled by assumption.

## Step 4 — Write and verify

1. Write the confirmed values into the files above.
2. Run `./init.sh` — must exit 0 (all placeholders filled, tests green, Security-kit
   integrity ✓).
3. If `init.sh` still reports unfilled placeholders, surface them and resolve with the user.

## Step 5 — Hand off

Report: what was auto-filled, what the user clarified, and confirm phase-01 is `active`
and ready for the normal `/session-cycle` loop. Do **not** start implementing features —
init only configures the harness.

## Rule

Never fabricate a project detail to make `init.sh` pass. An unfilled value that needs a
human decision must be flagged (Step 3), not guessed.
