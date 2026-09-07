# Security policy

## Reporting a vulnerability

Report suspected vulnerabilities in the harness, the runtime tier or the shipped policy files to
the repository owner privately, through the platform's confidential issue mechanism. Do not open a
public issue for a suspected bypass of a gate.

Include: the gate or module concerned, a minimal reproduction, and whether the bypass produced an
observable side effect (a tool call executed, bytes left the transport) or only a misclassification.
The distinction matters: the runtime's evidence is scored on side effects, and a bypass with a side
effect voids the current verdict immediately.

## What is and is not in scope

In scope: `template/governance/`, `template/Security-kit/`, the hooks under `template/.claude/`,
and the CI workflow. Out of scope: model behaviour itself, the operating environment, and any
application code a product team writes around the kit. The boundaries the runtime does not claim
are listed in `docs/reference/05-boundaries.md`.

## Signed evidence

The current release decision, its conditions and its expiry are in
`template/evaluation/runtime-security/VERDICT.md`. A report that contradicts a claim there is a
finding against the verdict, not only against the code.
