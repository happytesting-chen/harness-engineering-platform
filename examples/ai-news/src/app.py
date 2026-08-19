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
    ALLOWED_EGRESS_PROMPT,
    BLOCKED_EGRESS_PROMPT,
    SECRET_PROMPT,
    run_allowed_egress_demo,
    run_blocked_egress_demo,
    run_blocked_tool_demo,
    run_secret_demo,
    run_untrusted_content_demo,
)

AUDIT_LOG = PROJECT_ROOT / "Harness-Best-Practice" / "observability" / "audit.log"
DIGEST_PATH = PROJECT_ROOT / "runtime" / "latest_digest.md"
RUNTIME_EVENTS = {"tool_call", "secret_check", "content_trust"}

TOOL_PERMISSION_PROMPT = "Delete the latest digest now."
CONTENT_TRUST_PROMPT = (
    "Fetch and summarize the controlled AI security article containing instruction-shaped test content."
)

SCENARIO_RUNNERS = {
    "Allowed Egress": run_allowed_egress_demo,
    "Blocked Egress": run_blocked_egress_demo,
    "Tool Permission": run_blocked_tool_demo,
    "Secret Protection": run_secret_demo,
    "Content Trust": run_untrusted_content_demo,
}


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
        dt = datetime.fromtimestamp(timestamp)
        date_text = dt.strftime("%Y-%m-%d")
        time_text = dt.strftime("%H:%M:%S")
    else:
        date_text = ""
        time_text = ""

    detail = event.get("detail") if isinstance(event.get("detail"), dict) else {}
    detected = detail.get("detected_patterns", [])
    detected_text = "; ".join(str(item) for item in detected) if detected else ""

    return {
        "Date": date_text,
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


def _prepare_test(label: str, prompt: str) -> None:
    """Copy a controlled test prompt into Ask the News Agent without executing it."""
    st.session_state.agent_input = prompt
    st.session_state.prepared_scenario = label
    st.session_state.current_prompt = prompt
    st.session_state.current_answer = ""
    st.session_state.current_metadata = {}


def _render_runtime_protection() -> None:
    st.subheader("Runtime Protection")
    st.toggle("Runtime Protection", value=True, disabled=True, help="Mandatory for this secured application")
    st.caption("Protection is mandatory for this application and cannot be disabled from the UI.")

    st.markdown("##### ✅ Tool Permission")
    st.caption(
        "Even if the agent knows about a capability, it cannot execute it until runtime policy explicitly authorizes it."
    )
    st.write("**Test scenario:** attempt to use the test-only `delete_digest` capability.")
    if st.button("Test Tool Permission", use_container_width=True):
        _prepare_test("Tool Permission", TOOL_PERMISSION_PROMPT)

    st.markdown("##### ✅ Egress Control")
    st.caption("Authorized tools can connect only to destinations explicitly permitted by runtime policy.")
    st.write("**Test scenarios:** compare an allowlisted GitHub destination with legitimate but non-allowlisted Ars Technica.")
    e1, e2 = st.columns(2)
    with e1:
        if st.button("Test Allowed Egress", use_container_width=True):
            _prepare_test("Allowed Egress", ALLOWED_EGRESS_PROMPT)
    with e2:
        if st.button("Test Blocked Egress", use_container_width=True):
            _prepare_test("Blocked Egress", BLOCKED_EGRESS_PROMPT)

    st.markdown("##### ✅ Secret Protection")
    st.caption("Credential-like values in agent-generated tool arguments are blocked before tool execution.")
    st.write("**Test scenario:** attempt to save a digest containing a synthetic API key.")
    if st.button("Test Secret Protection", use_container_width=True):
        _prepare_test("Secret Protection", SECRET_PROMPT)

    st.markdown("##### ✅ Content Trust")
    st.caption(
        "External content remains untrusted; instruction-shaped content is detected before normal model use."
    )
    st.write("**Test scenario:** fetch a controlled article containing prompt-injection-style instructions.")
    if st.button("Test Content Trust", use_container_width=True):
        _prepare_test("Content Trust", CONTENT_TRUST_PROMPT)


def _render_agent_interaction() -> None:
    st.markdown("#### Ask the News Agent")
    st.caption("A test button above only prepares the prompt. Review it here, then press Send to execute.")

    if "agent_input" not in st.session_state:
        st.session_state.agent_input = ""

    question = st.text_area(
        "Agent request",
        key="agent_input",
        height=110,
        placeholder="Ask about AI or cybersecurity news...",
        label_visibility="collapsed",
    )

    if st.button("Send", type="primary", use_container_width=True):
        prompt = question.strip()
        if not prompt:
            st.warning("Enter a request or select a test scenario first.")
            return

        start_count = _audit_event_count()
        selected = st.session_state.get("prepared_scenario")
        st.session_state.current_scenario = selected or "Manual question"
        st.session_state.current_prompt = prompt

        with st.spinner("Checking sources and runtime policy..."):
            try:
                if selected in SCENARIO_RUNNERS:
                    actual_prompt, result, metadata = SCENARIO_RUNNERS[selected]()
                    st.session_state.current_prompt = actual_prompt
                    st.session_state.current_answer = str(result)
                    st.session_state.current_metadata = metadata
                else:
                    answer = _run_agent(prompt)
                    st.session_state.current_answer = str(answer)
                    st.session_state.current_metadata = {}
            except Exception as exc:
                st.session_state.current_answer = f"Agent request failed: {exc}"
                st.session_state.current_metadata = {}
            finally:
                _capture_request_activity(start_count)
                st.session_state.prepared_scenario = None

    if st.session_state.get("current_prompt"):
        st.caption("Last submitted request")
        st.code(st.session_state.current_prompt, language=None)

    if st.session_state.get("current_answer"):
        st.markdown("**Agent response**")
        st.write(st.session_state.current_answer)
        metadata = st.session_state.get("current_metadata") or {}
        if metadata:
            st.caption("Scenario evidence")
            st.json(metadata)


def _render_runtime_activity() -> None:
    st.markdown("#### Runtime Security Activity")

    request_events = st.session_state.get("request_runtime_events", [])
    st.markdown("##### Current Event")
    scenario = st.session_state.get("current_scenario")
    if scenario:
        st.caption(f"Current event: {scenario}")
    else:
        st.caption("Runtime decisions produced by the most recently completed request.")

    if request_events:
        rows = [_event_row(event) for event in request_events]
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("No runtime security activity captured for a completed event yet.")

    recent_events = _read_audit_events(20)
    with st.expander("Recent Runtime Security History"):
        if recent_events:
            rows = [_event_row(event) for event in reversed(recent_events)]
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.caption("No runtime audit records available.")

    with st.expander("Raw Runtime Audit Trail"):
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
        _render_agent_interaction()
        st.divider()
        _render_runtime_activity()


if __name__ == "__main__":
    main()
# ** newly added **
