# Integrate the runtime host into your application

Start from the worked example, not from the API:
[`template/examples/runtime-security-mvp/run.py`](../../template/examples/runtime-security-mvp/run.py)
constructs one `RuntimeHost` end to end with synthetic tools, a scripted model and a classifier
stub, and its [README](../../template/examples/runtime-security-mvp/README.md) says exactly what
it does and does not demonstrate. Copy its wiring; replace the stubs with your tools and model.

The condition you will be reviewed on is **C-1** in the signed
[verdict](../../template/evaluation/runtime-security/VERDICT.md): every tool invocation in the
deployed application reaches its callable through `RuntimeHost.invoke_tool`, and no component
keeps a reference to a raw tool callable. The library cannot enforce that for you; the architecture
review does. Design the wiring so the review is a short walkthrough, not an investigation.

The deployed application owns one `RuntimeHost` and routes each supported source and sink
through it:

1. `submit_prompt(...)` — screens user text before it enters model context.
2. `invoke_tool(...)` — applies session, origin, schema, policy and approval controls before
   a registered tool runs. A denial leaves the tool's call count at zero.
3. `deliver_tool_result(...)` — treats every tool result as untrusted external content.
4. `finish(...)` — buffers and screens the complete final response before release.

Quarantined content re-enters context only via `release_quarantined(...)` with a valid
receipt. Structured records use the explicit ingress adapter described in the profile.

Start with the [walkthrough](../../template/examples/runtime-security-mvp/README.md); use the
[profile](../../template/Context/runtime-security-profile.md) as the deployment contract.

---

## What a product team gets

| Product concern | Runtime control |
|---|---|
| Prompt injection in user, document or tool-result text | Rules plus semantic classification; anything not affirmatively cleared is withheld for review |
| Unsafe or out-of-scope tool use | A deterministic action gate checks registration, policy, schema, content origin and session ceilings **before** the side effect |
| Sensitive actions | Optional human approval via an expiring, single-use `ActionApprovalReceipt` — which can un-pause a call but never converts a deny |
| False positives | Quarantined content returns only through an exact-digest, expiring, single-use `ContentReleaseReceipt` |
| Secret leakage in the final answer | The whole response is buffered, redacted and released in one write |
| Incident review and release evidence | Closed-schema, hash-chained audit records bind every decision to the policy and classifier digests in force |

The binding promises and their scope are in
[`template/Context/runtime-security-profile.md`](../../template/Context/runtime-security-profile.md);
the mechanism behind each row is [Deployed runtime](../reference/03-deployed-runtime.md).
