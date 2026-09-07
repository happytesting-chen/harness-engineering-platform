# Documentation

Two kinds of page, kept apart on purpose: the **guide** is cut by task, the **reference** by question.

## Guide — how to use it

| Page | Task |
|---|---|
| [01 Getting started](guide/01-getting-started.md) | Get the code, copy the template, read the red health check |
| [02 Integrate the runtime host](guide/02-integrate-the-runtime-host.md) | Route a deployed application through the host; what a product team gets |
| [03 Bring your own classifier](guide/03-bring-your-own-classifier.md) | Rebuild, benchmark, pin and sign the classifier on another machine |
| [04 Tool compatibility](guide/04-tool-compatibility.md) | Which runtime wires what, and the hook-wiring caveat |
| [05 Produce and sign evidence](guide/05-produce-and-sign-evidence.md) | The operator's release sequence: gate, attack matrix, benchmark, checklist, verdict |

Building an agent inside a copied template — the eight steps and the live runtime tests — is
[`template/README.md`](../template/README.md), because that handbook travels with every copy.

## Reference — how it works

| Page | Question it answers |
|---|---|
| [01 Architecture](reference/01-architecture.md) | Where does enforcement sit? The two surfaces, the gate positions, one tool call end to end |
| [02 Build-time enforcement](reference/02-build-time-enforcement.md) | How does it fire while I build? Events, hooks, the four gates, content trust |
| [03 Deployed runtime](reference/03-deployed-runtime.md) | How does it fire in the application I ship? The host, the semantic tier, receipts, audit |
| [04 Claims and evidence](reference/04-claims-and-evidence.md) | How do I know any of this is true? The claims plane, then how evidence is produced and signed |
| [05 Boundaries](reference/05-boundaries.md) | Where does the guarantee stop? |
| [Appendix: directory map](reference/appendix-directory-map.md) | Where is everything? Every file, what edits it, what tests it |

## Evidence — measured, signed, dated

| Location | What it is |
|---|---|
| [`template/evaluation/runtime-security/`](../template/evaluation/runtime-security/) | The runtime verdict, its conditions and expiry, the attack traces, the classifier selection record |
| [`evaluations/2026-08-template-ab/`](evaluations/2026-08-template-ab/) | The A/B evaluation that tested the template against a build without it |

## Design record

[`template/docs/superpowers/`](../template/docs/superpowers/): the plans, specs and human-applied
patches behind each change. It ships with the template because the patches apply to it.
