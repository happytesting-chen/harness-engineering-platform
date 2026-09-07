# Integrate the runtime host into your application

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
