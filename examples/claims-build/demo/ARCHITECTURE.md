# Demo Module

Optional evaluation infrastructure. NOT the production enforcement path.

## Responsibilities

- Provide a scripted agent loop for demos and E2E tests
- Mock LLM responses (zero-dependency, no API keys needed)
- Demonstrate enforcement working vs not working (--nogate flag)

## Files

| File | Role | Modify? |
|------|------|---------|
| `harness.py` | Agent loop — iterates model responses, applies permission gate | **Never** per project |
| `fake_model.py` | Scripted Response/Block objects (mirrors real LLM SDK shape) | **Never** per project |
| `demo.py` | Domain-specific demo script (5-turn enforcement sequence) | **Customise** per domain |

## Interface

```python
from demo.harness import agent_loop, TOOL_HANDLERS
from demo.fake_model import Block, Response, FakeModel
```

## Constraints

- MUST NOT import external packages (stdlib only, except for the project's own modules)
- Production enforcement uses `.claude/settings.json` hooks → `governance/permission.py` CLI
- This module exists for evaluation and testing only
- `demo.py` must restore policy files after execution (save/restore pattern)
