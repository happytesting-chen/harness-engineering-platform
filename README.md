# Harness Engineering Platform — the model proposes, mechanisms decide

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![Core: Python standard library](https://img.shields.io/badge/core-Python%20standard%20library-brightgreen.svg)

**A runtime safety layer and build-time governance harness for tool-using AI products.**

At runtime, it puts an owned host around the agent loop: user prompts, documents and tool
results pass rule-based and semantic ingress checks; model-proposed actions pass
deterministic policy, origin, schema, session-ceiling and approval checks before a tool can
run; the final output is buffered and screened before release. **The model proposes.
Mechanisms decide** what enters context, which actions execute, and what leaves.

The same repository ships a build-time harness for Claude Code: phase plans, policy files,
verification gates, and hooks that mechanically block disallowed development tool calls.
Every documented control names the test that proves it, and the current release decision is
signed, conditioned and dated.

> **Status.** The deployed runtime profile carries a signed verdict of `DEPLOY_WITH_RULES`, valid to
> 2026-12-01 under five conditions, in
> [`template/evaluation/runtime-security/VERDICT.md`](template/evaluation/runtime-security/VERDICT.md).
> Routing through the host is still the application's responsibility (`SEC-RUNTIME-GAP-001`), which
> is why the decision is not `PRODUCTION_READY`. Pin a revision for anything you depend on.
>
> **On GitLab this repository is a single-commit import.** The development history and the
> commits the verdict names live on GitHub and in an archived bundle; see [PROVENANCE.md](PROVENANCE.md).

![Runtime security flow](assets/runtime-security-flow.svg)

## Why a harness and not a skill

A skill tells the model what to do. A harness decides what the model is allowed to do, in code that
runs whether or not the model agrees. Both surfaces follow one rule: **reasoning proposes,
mechanism enforces.** A non-deterministic component reading attacker-influenceable text cannot be
a control surface, because whatever persuades it disables the control. So enforcement sits
*outside* the model, and the result is measured on side effects, not on what any component says
it did.

The runtime claim is deliberately narrow: one owned host, one agent, a fixed registered tool set,
UTF-8 text ingress. Persistent memory, delegation, streaming output, remote classifiers and binary
ingress are disabled; multi-host operation is out of scope. **Nothing forces an application to use
the host** — complete routing is a deployment architecture-review item, not a property of the
library. Where enforcement sits: [Architecture](docs/reference/01-architecture.md). Where the
guarantee stops: [Boundaries](docs/reference/05-boundaries.md).

## Key features

- **[Every agent turn passes four security checkpoints](docs/reference/02-build-time-enforcement.md)** — checked by code the model cannot change, in a fixed order, and a failed check stops the turn there:
  1. **What you type.** The prompt is screened for injected instructions before the model reads it.
  2. **What the agent wants to do.** Every tool call is checked before it runs: not a protected file, not a forbidden command, allowed in the current phase, and only to permitted destinations.
  3. **What actually runs.** A tool can be reached only through the one chokepoint the checks sit on, and a write that carries a credential is stopped at it.
  4. **What comes back.** The tool's output is screened and, if needed, replaced before the model reads it.
- **[The same protection ships inside your application](docs/reference/03-deployed-runtime.md)** — in the deployed app there is no IDE and no hook, so one host wraps the agent loop and applies the same four checkpoints itself, adding a fifth: a limit on how much any one session may do. Incoming text is screened by rules plus a pinned local classifier, the final answer is held back until secrets are redacted, and every decision lands in a tamper-evident audit log.
- **[Blocked content and actions are released only by a one-time, expiring human approval](docs/reference/03-deployed-runtime.md)** — text held back at a checkpoint comes back only through a receipt bound to its exact digest, usable once, valid for a limited time. An approval can let a paused action proceed; it can never turn a refusal into a yes.
- **[Every security claim is tied to code and a test](docs/reference/04-claims-and-evidence.md)** — each control the documentation describes points at the code that enforces it and the test that proves it. Six automated checks fail the build if a claim has no mechanism, a mechanism has no test, or a test has quietly disappeared, so the documentation cannot drift ahead of what the code does. People, not agents, decide what goes on the register.
- **[Security evidence is measured, signed and expires](template/evaluation/runtime-security/)** — attacks are scored on whether the harmful side effect happened, never on a component's own report; results are immutable files that reproduce byte for byte; the release decision is signed by a named person with conditions and an expiry date, and any change to what it judged lapses it.
- **[A fresh copy fails its own health check until it is secured](docs/guide/01-getting-started.md)** — an unfilled template exits red with an exact set of errors: identity, phases and policy unfilled, and the security controls not yet tailored to the product. CI pins that exact set, so a new error is a visible difference, not one more number.
- **[The injection classifier is rebuilt and verified on your machine, never trusted blind](docs/guide/03-bring-your-own-classifier.md)** — the model is not in the repository. A standard-library bootstrap downloads it with every file checked against a pinned digest, reproduces the published benchmark before anything runs, and writes an unsigned lock that a named human signs.
- **[The security kit depends on nothing but Python](CONTRIBUTING.md)** — no third-party package can be swapped underneath a control, and nothing relies on the model behaving. The classifier subprocess is the one declared exception, and it is pinned by digest.

## New here? Start where you stand

| You are… | Start at | Then |
|---|---|---|
| **Building an agent** and want it governed while you build | [Getting started](docs/guide/01-getting-started.md) | the copied [handbook](template/README.md): eight steps, then attack it |
| **Deploying an application** and need the gates in process | [Integrate the runtime host](docs/guide/02-integrate-the-runtime-host.md) | [Bring your own classifier](docs/guide/03-bring-your-own-classifier.md) |
| **Reviewing or deciding** whether a deployment can be trusted | [`VERDICT.md`](template/evaluation/runtime-security/VERDICT.md) and [Boundaries](docs/reference/05-boundaries.md) | [Produce and sign evidence](docs/guide/05-produce-and-sign-evidence.md) |
| **Changing the platform** itself | [CONTRIBUTING.md](CONTRIBUTING.md) | [Claims and evidence](docs/reference/04-claims-and-evidence.md), then the [directory map](docs/reference/appendix-directory-map.md) |

## Pick your surface

| Surface | What it protects | Start |
|---|---|---|
| **Build-time, Claude Code** | Your development session: hooks block disallowed tool calls, screen prompts and results, guard protected paths | [Getting started](docs/guide/01-getting-started.md), then the [in-project handbook](template/README.md) |
| **Deployed runtime** | The application you ship: the same gates in process, no IDE, plus the semantic tier | [Integrate the runtime host](docs/guide/02-integrate-the-runtime-host.md) |
| **Kiro add-on** | The same build-time controls in Kiro | [`template/kiro/README.md`](template/kiro/README.md) · [Tool compatibility](docs/guide/04-tool-compatibility.md) |

## Quick start

```bash
git clone git@sgts.gitlab-dedicated.com:wog/csa/csacentral/ai-team/security-by-design_harness.git harness-engineering-platform
cp -r harness-engineering-platform/template/ my-agent/
cd my-agent && chmod +x init.sh && ./init.sh     # exits 1 on a fresh copy — by design
```

`init.sh` is a health check, not a scaffolder. On an unfilled copy it reports `FAIL — 5 error(s)`:
**four** unfilled `{{placeholders}}` (identity, phases, policy) and **one** fail-closed coverage gate
that only `/security-tailor` clears, because *which of the 20 OWASP LLM/Agentic risks apply* is a
property of your product, not the template. Prerequisites and the one rule that prevents silent
hook failure: [Getting started](docs/guide/01-getting-started.md). The eight build steps and the
live runtime tests: the copied [`README.md`](template/README.md).

To see the runtime host alone, with synthetic tools and a scripted model:

```bash
cd harness-engineering-platform/template && python3 examples/runtime-security-mvp/run.py
```

Synthetic tools, a scripted model, a classifier stub: it demonstrates the control flow and
deterministic enforcement, not production deployment or classifier quality. The
[example README](template/examples/runtime-security-mvp/README.md) says exactly which.

## Documentation

| Read this | When you are… |
|---|---|
| [`docs/guide/`](docs/README.md) | using the platform: getting started, integrating the host, the classifier, tool compatibility |
| [`template/README.md`](template/README.md) | building an agent from the copied template: eight steps, then attack it |
| [`docs/reference/`](docs/README.md) | changing or auditing the platform: the gates, the runtime tier, the claims plane, the directory map |
| [`template/evaluation/runtime-security/`](template/evaluation/runtime-security/) | deciding whether to deploy: the verdict, its conditions, the measured record |
| [`template/Context/runtime-security-profile.md`](template/Context/runtime-security-profile.md) | holding the runtime to its promises: the binding contract for the deployed profile |

## Repository layout

```
.
├── template/                 # WHAT YOU COPY — the harness, the kit, the runtime, the tests, the evidence
│   ├── governance/           #   policy files and the four-gate permission check   (protected path)
│   ├── Security-kit/         #   claims plane, eval tooling, runtime/ semantic tier (runtime/ protected)
│   ├── Context/              #   product context and the binding runtime profile
│   ├── Harness-Best-Practice/#   identity files and the phase plan
│   ├── tests/                #   38 files, stdlib runners; CI runs them all
│   ├── evaluation/           #   the measured record and the signed verdict
│   ├── docs/superpowers/     #   design record: plans, specs, human-applied patches
│   └── README.md             #   the in-project handbook, travels with every copy
├── docs/                     # HOW TO USE IT AND HOW IT WORKS — guide/, reference/, evaluations/
├── examples/claims-build/    # one complete build on the template, phases signed off
├── assets/                   # the four diagrams
├── .github/workflows/        # CI: baseline shape asserted, full suite fatal
└── CONTRIBUTING.md · SECURITY.md · CHANGELOG.md · LICENSE
```

## Testing

```bash
cd template
python3 -m pytest tests -q               # full suite; every file also runs standalone without pytest
./init.sh                                # exit 1, exactly the documented 5-error baseline
python3 Security-kit/check_coverage.py   # claims invariants I1–I6
python3 Security-kit/runtime/attack_driver.py --output /tmp/traces.jsonl   # 13 cases, side-effect oracles
```

CI asserts the baseline's exact error set, then runs the whole suite as a fatal step. The one test
that needs the operator's local classifier files skips on a runner and says why.

## Troubleshooting

Symptoms and fixes for the copied template are in its own
[Troubleshooting](template/README.md#troubleshooting) section. If a hook does not fire at all, the
usual cause is opening the editor one directory above the copy: hooks load from `.claude/settings.json`
at the project root, and only there.

## Contributing

Merge requests only; protected paths are changed by a human applying a reviewed patch; the claims
register is human-owned; mechanism code stays standard library. Details in
[CONTRIBUTING.md](CONTRIBUTING.md). Vulnerabilities: [SECURITY.md](SECURITY.md).

## Roadmap

Rule-plus-semantic ingress, quarantine and receipted release, guarded dispatch with origin and
schema rules, session ceilings, approval receipts, startup validation, buffered output,
hash-chained evidence and a side-effect replay matrix are shipped and measured. What remains
strengthens assurance without widening the profile:

| Next | Why it remains |
|---|---|
| Independent security review | Verification so far was run by the authors; a written release condition (C-4) |
| Prove complete application routing | The library cannot force every source and sink through its host (`SEC-RUNTIME-GAP-001`) |
| Workflow-impersonation rule | The four remaining classifier misses are one family; a deterministic, origin-aware rule is the recorded follow-up |
| Resident classifier process | About 0.6 s per item today, almost all model load; a prerequisite for the narrower chunk window the corpus expansion recommends |
| Bound and operate the review queue | Fail-closed ingress can exhaust reviewer attention |
| Memory, delegation, binary ingress, streaming | Each is a new source or sink and needs its own threat model before it is enabled |
| `/runtime-harden` | The drafter that would generate per-project wiring; today it is done by hand from `SECURITY.md` S1.6 |

**There are no sub-agents in this repository today** — `template/.claude/` ships slash commands and
no `agents/` directory. The intended direction is phase-scoped sub-agents that each pass the same
gates as their parent, so delegation cannot become privilege escalation. Design only.

## References

| Resource | Role |
|---|---|
| [Learn Harness Engineering](https://walkinglabs.github.io/learn-harness-engineering/en/) | The "why" — harness theory, the feature triple and Fresh Session Test this template implements. |
| [Awesome Harness Engineering](https://github.com/Jiaaqiliu/Awesome-Harness-Engineering) | Primary-source map; the agent-vs-harness framing. |
| [Awesome Claude Code](https://github.com/hesreallyhim/awesome-claude-code) | CLAUDE.md patterns, hooks, slash commands, subagents. |
| "Harness Engineering: Leveraging Codex in an Agent-First World" (OpenAI) | Credited with coining the term. |
| Anthropic — Building Effective Agents | Design principles for tool-use loops and permission boundaries. |
| [Claude Code on AWS Bedrock — Best Practices](https://github.com/timwukp/claude-code-on-aws-bedrock-best-practices) | Fail-closed hooks and managed-settings hierarchy. |


---

Core framing: **agent = model + tools; harness = everything else.**

The design record behind each change — plans, specs and the human-applied patches — is
[`template/docs/superpowers/`](template/docs/superpowers/).

## License

MIT. See [LICENSE](LICENSE).
