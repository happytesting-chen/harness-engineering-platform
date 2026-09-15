# Runtime Security

Runtime security protects the deployed AI application after development.

Typical responsibilities include:

- screening application input before it reaches the model
- authorizing tool calls before execution
- enforcing runtime egress policy
- screening tool results before they return to the model
- handling untrusted external content
- ensuring every application tool call passes through the governed runtime path

Runtime security does not come from Claude Code hooks. A deployed application must explicitly integrate the runtime enforcement path.

Runtime controls should consume common policy and enforcement logic from `../shared/` rather than maintaining separate copies.
