# Harness Engineering Platform — the model proposes, mechanisms decide

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![Core: Python standard library](https://img.shields.io/badge/core-Python%20standard%20library-brightgreen.svg)

A security harness for tool-using AI agents, in two surfaces from one set of gates: hooks that
**block** disallowed development tool calls while you build, and an in-process runtime host that
**decides** what enters the model's context, which actions execute, and what leaves, in the
application you deploy. Every documented control names the test that proves it, and the current
release decision is signed, conditioned and dated.

> **Status.** The deployed runtime profile carries a signed verdict of `DEPLOY_WITH_RULES`, valid to
> 2026-12-01 under five conditions, in
> [`template/evaluation/runtime-security/VERDICT.md`](template/evaluation/runtime-security/VERDICT.md).
> Routing through the host is still the application's responsibility (`SEC-RUNTIME-GAP-001`), which
> is why the decision is not `PRODUCTION_READY`. Pin a revision for anything you depend on.

![Runtime security flow](assets/runtime-security-flow.svg)

## Why a harness and not a skill

A skill tells the model what to do. A harness decides what the model is allowed to do, in code that
runs whether or not the model agrees. Prompted rules lose to a determined input often enough that
the loss must be assumed; this repository puts every security decision outside the model, keeps the
model's judgement where judgement belongs, and measures the result on side effects, not on what any
component says it did. The distinction is the whole design: see
[What is not enforced](docs/reference/07-what-is-not-enforced.md) for where the guarantee stops.

## Key features

- **[Four deterministic gates](docs/reference/01-enforcement-model.md)** — input, before a tool runs, execution, output before the model — on the control plane (tool calls) and the data plane (untrusted content).
- **[A deployed runtime tier](docs/reference/02-deployed-runtime-tier.md)** — one owned `RuntimeHost`; rule-based and pinned-classifier ingress; an action gate with policy, origin, schema, session ceilings and optional approval; buffered, redacted output; hash-chained audit.
- **[Receipts, not overrides](docs/reference/02-deployed-runtime-tier.md)** — quarantined content returns only by exact-digest, single-use, expiring receipt; an approval can un-pause a call but never converts a deny.
- **[A claims plane](docs/reference/03-claims-plane.md)** — every documented control names its proof; six invariants fail closed; the register is human-owned.
- **[Signed, expiring evidence](template/evaluation/runtime-security/)** — immutable benchmark results, a labelled corpus, deterministic replay, attack traces scored on side effects, a verdict with conditions and an expiry.
- **[Red by design](docs/guide/01-getting-started.md)** — the health check fails on a correct fresh copy with an exact error set, and CI pins that set so a new error is a diff, not an increment.
- **[Bring your own classifier](docs/guide/03-bring-your-own-classifier.md)** — the model is not in the repo; a stdlib bootstrap rebuilds, benchmarks and pins it on any machine, and a human signs the lock.
- **[Standard library only](CONTRIBUTING.md)** — nothing in the kit depends on a package or on the model behaving. The classifier subprocess is the one declared exception.

## Pick your surface

| Surface | What it protects | Start |
|---|---|---|
| **Build-time, Claude Code** | Your development session: hooks block disallowed tool calls, screen prompts and results, guard protected paths | [Getting started](docs/guide/01-getting-started.md), then the [in-project handbook](template/README.md) |
| **Deployed runtime** | The application you ship: the same gates in process, no IDE, plus the semantic tier | [Integrate the runtime host](docs/guide/02-integrate-the-runtime-host.md) |
| **Kiro add-on** | The same build-time controls in Kiro | [`template/kiro/README.md`](template/kiro/README.md) · [Tool compatibility](docs/guide/04-tool-compatibility.md) |

## Quick start

```bash
git clone <repository-url> harness-engineering-platform
cp -r harness-engineering-platform/template/ my-agent/
cd my-agent && chmod +x init.sh && ./init.sh
```

The health check exits 1 and lists the five things a fresh copy still needs. That is the contract.
The eight build steps and the live runtime tests are in the copied
[`README.md`](template/README.md). To see the runtime host alone, with synthetic tools and a
scripted model:

```bash
cd harness-engineering-platform/template && python3 examples/runtime-security-mvp/run.py
```

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

## References

Lineage and the sources this work draws on: [References and lineage](docs/reference/08-references-and-lineage.md).
The design record behind each change: [`template/docs/superpowers/`](template/docs/superpowers/).

## License

MIT. See [LICENSE](LICENSE).
