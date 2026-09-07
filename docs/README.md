# Documentation

Two kinds of page, kept apart on purpose.

**Guide** — how to use the platform. Read in order the first time.

| Page | What it covers |
|---|---|
| [01 Getting started](guide/01-getting-started.md) | Clone, copy the template, run the health check, read its failure |
| [02 Integrate the runtime host](guide/02-integrate-the-runtime-host.md) | The four calls a deployed application routes through, and the routing condition |
| [03 Bring your own classifier](guide/03-bring-your-own-classifier.md) | Why the model is not in the repo, and how another machine rebuilds and pins it |
| [04 Tool compatibility](guide/04-tool-compatibility.md) | Claude Code, Kiro and the other agent runtimes |
| [05 The security kit](guide/05-the-security-kit.md) | The kit from the template's point of view: context, guidance, policy, enforcement, verification |

The in-project handbook — the eight build steps and the live runtime tests — is
[`template/README.md`](../template/README.md), because it travels with every copied template.

**Reference** — how it works. Read when you need the mechanism.

| Page | What it covers |
|---|---|
| [01 The enforcement model](reference/01-enforcement-model.md) | Control plane (tool calls) and data plane (untrusted content) |
| [02 The deployed runtime tier](reference/02-deployed-runtime-tier.md) | The same gates with no hooks; the semantic tier; the receipts |
| [03 The claims plane](reference/03-claims-plane.md) | The tailoring path, what is mechanical, the six invariants |
| [04 Security kit internals](reference/04-security-kit-internals.md) | From the agent loop you know to the dev-time enforcement path |
| [05 Directory map](reference/05-directory-map.md) | Every directory and file, what edits it, what tests it |
| [06 Observability and human checkpoints](reference/06-observability-and-human-checkpoints.md) | The audit record and the two places a human decides |
| [07 What is not enforced](reference/07-what-is-not-enforced.md) | Stated boundaries, each linked to its full statement |
| [08 References and lineage](reference/08-references-and-lineage.md) | Where the ideas came from |

**Evidence** — measured, signed, dated.

| Location | What it is |
|---|---|
| [`template/evaluation/runtime-security/`](../template/evaluation/runtime-security/) | The runtime verdict, its conditions and expiry, the attack traces, the classifier selection record |
| [`evaluations/2026-08-template-ab/`](evaluations/2026-08-template-ab/) | The A/B evaluation that tested the template against a build without it |

**Design record** — [`template/docs/superpowers/`](../template/docs/superpowers/): the plans, specs and
human-applied patches behind each change. It ships with the template because the patches apply to it.
