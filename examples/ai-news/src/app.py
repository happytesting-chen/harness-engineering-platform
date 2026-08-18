# ** newly added **
"""Streamlit portal for the AI News runtime-security demo.

This file is presentation/application code only. It deliberately reuses the same
`build_agent()` path as `run_news.py`; it does not register raw tools or implement
security decisions itself.

Run from the project root:
    streamlit run src/app.py
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent import build_agent
from src.run_news import DEFAULT_PROMPT

AUDIT_LOG = PROJECT_ROOT / "Harness-Best-Practice" / "observability" / "audit.log"
DIGEST_PATH = PROJECT_ROOT / "runtime" / "latest_digest.md"
RUNTIME_EVENTS = {"tool_call", "secret_check", "content_trust"}


def _read_audit_events(limit: int = 20) -> list[dict]:
    """Read only AI News runtime-security events; hide build-time hook activity."""
    if not AUDIT_LOG.exists():
        return []

    events: list[dict] = []
    for line in AUDIT_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and event.get("event") in RUNTIME_EVENTS:
            events.append(event)
    return events[-limit:]


def _event_row(event: dict) -> dict:
    """Flatten one runtime audit record into a compact, human-readable UI row."""
    timestamp = event.get("timestamp")
    if isinstance(timestamp, (int, float)):
        time_text = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")
    else:
        time_text = ""

    detail = event.get("detail") if isinstance(event.get("detail"), dict) else {}
    detected = detail.get("detected_patterns", [])
    detected_text = "; ".join(str(item) for item in detected) if detected else ""

    return {
        "Time": time_text,
        "Control/Event": event.get("event", ""),
        "Tool": event.get("tool", ""),
        "Decision": event.get("decision", ""),
        "Reason": event.get("reason", ""),
        "Detected content": detected_text,
    }


def _read_digest() -> str:
    if not DIGEST_PATH.exists():
        return ""
    return DIGEST_PATH.read_text(encoding="utf-8")


def _get_agent():
    """Create one secured agent per Streamlit session."""
    if "agent" not in st.session_state:
        st.session_state.agent = build_agent()
    return st.session_state.agent


def _run_agent(prompt: str):
    """Invoke the normal secured agent path; no UI-specific tool path exists."""
    return _get_agent()(prompt)


def _render_runtime_panel() -> None:
    st.subheader("Runtime Protection")
    st.success("ON — secured tool path enforced")

    st.markdown(
        """
- ✅ **Tool Permission** — default deny unless runtime policy authorizes the tool
- ✅ **Egress Control** — outbound destinations checked against the allowlist
- ✅ **Secret Protection** — credential-like tool input blocked before execution
- ✅ **Content Trust** — suspicious returned instructions blocked before model use
"""
    )

    events = _read_audit_events(20)
    st.markdown("#### Runtime Security Activity")
    if events:
        rows = [_event_row(event) for event in reversed(events)]
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("No runtime security events yet. Generate a digest or ask the agent a question.")

    with st.expander("Raw runtime audit trail"):
        if not events:
            st.caption("No runtime audit records available.")
        for event in reversed(events):
            st.json(event)


def main() -> None:
    st.set_page_config(
        page_title="AI News — Runtime Secured",
        page_icon="🛡️",
        layout="wide",
    )

    st.title("AI News — Runtime-Secured Agent")
    st.caption(
        "Claude + Strands news application with runtime tool permission, egress, "
        "secret protection, content trust, and audit logging."
    )

    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.error(
            "ANTHROPIC_API_KEY is not set in this runtime. Export it locally before starting Streamlit."
        )
        st.stop()

    left, right = st.columns([2, 1], gap="large")

    with left:
        st.subheader("Today's AI + Cybersecurity Digest")

        if st.button("Generate Latest Digest", type="primary"):
            with st.spinner("Gathering approved sources through the secured runtime path..."):
                try:
                    result = _run_agent(DEFAULT_PROMPT)
                    st.session_state.last_agent_result = str(result)
                    st.session_state.last_digest = _read_digest()
                except Exception as exc:
                    st.error(f"Digest generation failed: {exc}")

        digest = st.session_state.get("last_digest") or _read_digest()
        if digest:
            st.markdown(digest)
        else:
            st.info("No saved digest yet. Click **Generate Latest Digest** to create one.")

        st.divider()
        st.subheader("Ask the News Agent")
        st.caption("Questions use the same secured Strands agent and runtime controls.")

        question = st.chat_input("Ask about AI or cybersecurity news...")
        if question:
            st.chat_message("user").write(question)
            with st.chat_message("assistant"):
                with st.spinner("Checking sources and runtime policy..."):
                    try:
                        answer = _run_agent(question)
                        st.write(str(answer))
                    except Exception as exc:
                        st.error(f"Agent request failed: {exc}")

    with right:
        _render_runtime_panel()


if __name__ == "__main__":
    main()
# ** newly added **
