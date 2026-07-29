"""
Generic agent loop — the foundation.
Identical shape regardless of domain. Capability is added by registering
tool handlers; policy is added by configuring governance/ and tools/.

Runs with ZERO dependencies and NO API key — a scripted fake_model
stands in for the LLM. Swap for the real client and the loop is unchanged.

NOTE: This file lives in demo/ — it's optional evaluation infrastructure.
The production enforcement path is .claude/settings.json hooks → permission.py CLI.
"""
import subprocess
from pathlib import Path
import sys

# Adjust sys.path so we can import from sibling directories (governance/, observability/)
sys.path.insert(0, str(Path(__file__).parent.parent / "observability"))
sys.path.insert(0, str(Path(__file__).parent.parent / "governance"))

from audit import record
from permission import make_permission_check

WORKDIR = Path(__file__).parent.parent / "sandbox"
WORKDIR.mkdir(exist_ok=True)


# --- Tool handlers (extend per domain) ---
def tool_bash(command: str) -> str:
    result = subprocess.run(command, shell=True, capture_output=True,
                           text=True, cwd=WORKDIR, timeout=30)
    return (result.stdout + result.stderr).strip() or "(no output)"


def tool_write_file(path: str, content: str) -> str:
    target = WORKDIR / path
    target.write_text(content)
    return f"wrote {len(content)} bytes to {path}"


TOOL_HANDLERS = {
    "bash": lambda args: tool_bash(args["command"]),
    "write_file": lambda args: tool_write_file(args["path"], args["content"]),
}


# --- The loop ---
def agent_loop(messages, model_fn, permission_check=None, max_turns=10):
    for turn in range(max_turns):
        response = model_fn(messages)
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            final = next((b.text for b in response.content if b.type == "text"), "")
            print(f"\n[agent done] {final}")
            return

        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            allowed, reason = permission_check(block) if permission_check else (True, "")
            if not allowed:
                print(f"   \033[31m\u26d4 DENIED\033[0m  {block.name}({block.input})")
                record("tool_call", block.name, block.input, "DENIED", reason)
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": f"Permission denied: {reason}"})
                continue

            print(f"   \033[32m\u2713 allow\033[0m   {block.name}({block.input})")
            record("tool_call", block.name, block.input, "ALLOWED")
            handler = TOOL_HANDLERS.get(block.name)
            if handler:
                output = handler(block.input)
            else:
                output = f"unknown tool: {block.name}"
            results.append({"type": "tool_result", "tool_use_id": block.id,
                            "content": output})

        messages.append({"role": "user", "content": results})
    print("\n[agent stopped] hit max_turns cap")
