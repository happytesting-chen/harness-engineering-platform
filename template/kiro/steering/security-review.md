---
inclusion: manual
---

# Security Review

Use this workflow for changes to tools, external APIs, retrieval or untrusted content, identity, secrets, policy, deployment, or other security boundaries.

## Review Steps

1. Identify the changed boundary: input, identity, data, tool, network, model, policy, or deployment.
2. Read the affected rows in `security/control-matrix.md`, the baseline in `context/SECURITY.md`, and any module-local constraints.
3. Inspect the change for least privilege, input trust, data exposure, egress, secrets, logging, and human-approval implications.
4. Run the verification mapped to each affected control; add or update a test when a control lacks evidence.
5. Record the result in the control matrix and `progress.md`: evidence reviewed, findings, and unresolved risk.
6. Escalate policy changes, high-risk actions, or unresolved risk for human approval. Do not self-approve them.

## Exit Condition

The relevant controls have verification evidence, findings are resolved or explicitly escalated, and the project state records the review outcome.
