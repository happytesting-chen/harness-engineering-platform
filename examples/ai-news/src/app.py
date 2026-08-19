# ** newly added **
"""Streamlit portal for the AI News runtime-security demo.

This file is presentation/application code only. It deliberately reuses the same
`build_agent()` path as `run_news.py`; it does not register raw production tools or
implement security decisions itself.

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
from src.security_demo import (
    run_allowed_egress_demo,
    run_blocked_egress_demo,
    run_blocked_tool_demo,
    run_secret_demo,
    run_untrusted_content_demo,
)

AUDIT_LOG = PROJECT_ROOT / "Harness-Best-Practice" / "observability" / "audit.log"
DIGEST_PATH = PROJECT_ROOT / "runtime" / "latest_digest.md"
RUNTIME_EVENTS = {"tool_call", "secret_check", "content_trust"}


def _read_audit_events(limit: int | None = 20) -> list[dict]:
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
    return events[-limit:] if limit is not None else events


def _event_row(event: dict) -> dict:
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


def _audit_event_count() -> int:
    return len(_read_audit_events(limit=None))


def _capture_request_activity(start_count: int) -> None:
    all_events = _read_audit_events(limit=None)
    st.session_state.request_runtime_events = all_events[start_count:]


def _read_digest() -> str:
    if not DIGEST_PATH.exists():
        return ""
    return DIGEST_PATH.read_text(encoding="utf-8")


def _get_agent():
    if "agent" not in st.session_state:
        st.session_state.agent = build_agent()
    return st.session_state.agent


def _run_agent(prompt: str):
    return _get_agent()(prompt)


def _run_security_scenario(label: str, runner) -> None:
    """Run one controlled demo and capture only that event's runtime audit records."""
    start_count = _audit_event_count()
    st.session_state.current_scenario = label
    try:
        prompt, result, metadata = runner()
        st.session_state.current_prompt = prompt
        st.session_state.current_answer = str(result)
        st.session_state.current_metadata = metadata
    except Exception as exc:
        st.session_state.current_prompt = label
        st.session_state.current_answer = f"Scenario failed: {exc}"
        st.session_state.current_metadata = {}
    finally:
        _capture_request_activity(start_count)


def _render_runtime_protection() -> None:
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


def _render_security_scenarios() -> None:
    st.markdown("#### Runtime Security Test Scenarios")
    st.caption("Run the same controlled scenarios used by the live security tests.")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Allowed Egress", use_container_width=True):
            _run_security_scenario("Allowed Egress", run_allowed_egress_demo)
        if st.button("Blocked Tool", use_container_width=True):
            _run_security_scenario("Blocked Tool", run_blocked_tool_demo)
        if st.button("Untrusted Content", use_container_width=True):
            _run_security_scenario("Untrusted Content", run_untrusted_content_demo)
    with c2:
        if st.button("Blocked Egress", use_container_width=True):
            _run_security_scenario("Blocked Egress", run_blocked_egress_demo)
        if st.button("Secret Protection", use_container_width=True):
            _run_security_scenario("Secret Protection", run_secret_demo)


def _render_agent_interaction() -> None:
    st.markdown("#### Ask the News Agent")
    st.caption("Normal questions and controlled scenarios both use secured runtime paths.")

    if st.session_state.get("current_prompt"):
        st.chat_message("user").write(st.session_state.current_prompt)
    if st.session_state.get("current_answer"):
        with st.chat_message("assistant"):
            st.write(st.session_state.current_answer)
            metadata = st.session_state.get("current_metadata") or {}
            if metadata:
                st.caption("Scenario evidence")
                st.json(metadata)

    question = st.chat_input("Ask about AI or cybersecurity news...")
    if question:
        start_count = _audit_event_count()
        st.session_state.current_scenario = "Manual question"
        st.session_state.current_prompt = question
        st.chat_message("user").write(question)
        with st.chat_message("assistant"):
            with st.spinner("Checking sources and runtime policy..."):
                try:
                    answer = _run_agent(question)
                    st.session_state.current_answer = str(answer)
                    st.session_state.current_metadata = {}
                    st.write(str(answer))
                except Exception as exc:
                    st.session_state.current_answer = f"Agent request failed: {exc}"
                    st.session_state.current_metadata = {}
                    st.error(st.session_state.current_answer)
                finally:
                    _capture_request_activity(start_count)


def _render_runtime_activity() -> None:
    request_events = st.session_state.get("request_runtime_events", [])
    st.markdown("#### Runtime Security Activity for Current Event")
    scenario = st.session_state.get("current_scenario")
    if scenario:
        st.caption(f"Current event: {scenario}")
    else:
        st.caption("One row per runtime security decision triggered by the current event.")

    if request_events:
        rows = [_event_row(event) for event in request_events]
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("No runtime security activity captured for this UI session yet.")

    recent_events = _read_audit_events(20)
    with st.expander("Recent runtime security history"):
        if recent_events:
            rows = [_event_row(event) for event in reversed(recent_events)]
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.caption("No runtime audit records available.")

    with st.expander("Raw runtime audit trail"):
        if not request_events:
            st.caption("No current-event runtime audit records available.")
        for event in request_events:
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
            start_count = _audit_event_count()
            st.session_state.current_scenario = "Generate Latest Digest"
            with st.spinner("Gathering approved sources through the secured runtime path..."):
                try:
                    result = _run_agent(DEFAULT_PROMPT)
                    st.session_state.last_agent_result = str(result)
                    st.session_state.last_digest = _read_digest()
                    st.session_state.current_prompt = DEFAULT_PROMPT
                    st.session_state.current_answer = str(result)
                    st.session_state.current_metadata = {}
                except Exception as exc:
                    st.error(f"Digest generation failed: {exc}")
                finally:
                    _capture_request_activity(start_count)

        digest = st.session_state.get("last_digest") or _read_digest()
        if digest:
            st.markdown(digest)
        else:
            st.info("No saved digest yet. Click **Generate Latest Digest** to create one.")

    with right:
        _render_runtime_protection()
        st.divider()
        _render_security_scenarios()
        st.divider()
        _render_agent_interaction()
        st.divider()
        _render_runtime_activity()


if __name__ == "__main__":
    main()
# ** newly added **
