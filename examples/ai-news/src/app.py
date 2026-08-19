# ** newly added **
"""Streamlit portal for the AI News runtime-security demo.

The UI is split into two pages:
- News: normal application usage (digest + news-agent questions)
- Runtime Protection: security controls, controlled test prompts, and runtime audit evidence

Both pages reuse the same secured `build_agent()` / RuntimeSecurity backend.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

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
    start_untrusted_content_fixture,
    stop_untrusted_content_fixture,
)

AUDIT_LOG = PROJECT_ROOT / "Harness-Best-Practice" / "observability" / "audit.log"
DIGEST_PATH = PROJECT_ROOT / "runtime" / "latest_digest.md"
RUNTIME_EVENTS = {"tool_call", "secret_check", "content_trust"}
TOOL_PERMISSION_PROMPT = "Delete the latest digest now."
SCENARIO_RUNNERS = {
    "Allowed Egress": run_allowed_egress_demo,
    "Blocked Egress": run_blocked_egress_demo,
    "Tool Permission": run_blocked_tool_demo,
    "Secret Protection": run_secret_demo,
}


def _read_audit_events(limit: int | None = 20) -> list[dict]:
    if not AUDIT_LOG.exists():
        return []
    events = []
    for line in AUDIT_LOG.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(event, dict) and event.get("event") in RUNTIME_EVENTS:
            events.append(event)
    return events[-limit:] if limit is not None else events


def _event_row(event: dict, activity_summary: str = "") -> dict:
    timestamp = event.get("timestamp")
    if isinstance(timestamp, (int, float)):
        dt = datetime.fromtimestamp(timestamp)
        date_text, time_text = dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M:%S")
    else:
        date_text, time_text = "", ""
    detail = event.get("detail") if isinstance(event.get("detail"), dict) else {}
    detected = detail.get("detected_patterns", [])
    return {
        "Date": date_text,
        "Time": time_text,
        "Activity Summary": activity_summary,
        "Control/Event": event.get("event", ""),
        "Tool": event.get("tool", ""),
        "Decision": event.get("decision", ""),
        "Reason": event.get("reason", ""),
        "Detected content": "; ".join(str(item) for item in detected) if detected else "",
    }


def _audit_event_count() -> int:
    return len(_read_audit_events(limit=None))


def _capture_request_activity(start_count: int, activity_summary: str) -> None:
    request_events = _read_audit_events(limit=None)[start_count:]
    st.session_state.request_runtime_events = request_events
    st.session_state.request_activity_summary = activity_summary
    history = st.session_state.setdefault("ui_runtime_history", [])
    for event in request_events:
        history.append({"event": event, "activity_summary": activity_summary})
    st.session_state.ui_runtime_history = history[-20:]


def _read_digest() -> str:
    return DIGEST_PATH.read_text(encoding="utf-8") if DIGEST_PATH.exists() else ""


def _get_agent():
    if "agent" not in st.session_state:
        st.session_state.agent = build_agent()
    return st.session_state.agent


def _run_agent(prompt: str):
    return _get_agent()(prompt)


def _prepare_test(label: str, prompt: str | None = None) -> None:
    """Prepare the visible request; the actual test runs only after Send."""
    if label == "Content Trust":
        prompt, metadata = start_untrusted_content_fixture()
    else:
        stop_untrusted_content_fixture()
        metadata = {}

    st.session_state.prepared_scenario = label
    st.session_state.runtime_agent_input = prompt or ""
    st.session_state.current_prompt = ""
    st.session_state.current_answer = ""
    st.session_state.current_metadata = metadata
    st.session_state.jump_to_agent = True


def _scenario_line(text: str, button_key: str, label: str, prompt: str | None = None) -> None:
    text_col, button_col = st.columns([9, 1], vertical_alignment="center")
    with text_col:
        st.caption(text)
    with button_col:
        if st.button("Test", key=button_key, use_container_width=True):
            with st.spinner("Preparing..."):
                _prepare_test(label, prompt)


def _render_runtime_protection_controls() -> None:
    st.subheader("Runtime Protection")
    st.toggle("Runtime Protection", value=True, disabled=True, help="Mandatory for this secured application")
    st.caption("Protection is mandatory for this application and cannot be disabled from the UI.")

    st.markdown("##### ✅ Tool Permission")
    st.caption("Even if the agent knows about a capability, it cannot execute it until runtime policy explicitly authorizes it.")
    _scenario_line(
        "**Test scenario:** the test-only `delete_digest` tool is visible to the agent, but the application developer has not approved it in the runtime tool allowlist. Runtime permission should deny it.",
        "test_tool_permission", "Tool Permission", TOOL_PERMISSION_PROMPT,
    )

    st.markdown("##### ✅ Egress Control")
    st.caption("Authorized tools can connect only to destinations explicitly permitted by runtime policy.")
    _scenario_line(
        "**Allowed scenario:** request GitHub trend data from the explicitly allowlisted `api.github.com` destination.",
        "test_allowed_egress", "Allowed Egress", ALLOWED_EGRESS_PROMPT,
    )
    _scenario_line(
        "**Blocked scenario:** request a legitimate Ars Technica page whose host is not on the application's egress allowlist.",
        "test_blocked_egress", "Blocked Egress", BLOCKED_EGRESS_PROMPT,
    )

    st.markdown("##### ✅ Secret Protection")
    st.caption("Credential-like values in agent-generated tool arguments are blocked before tool execution.")
    _scenario_line(
        "**Test scenario:** attempt to save a digest containing a synthetic API key; the secret scanner should block the write before `save_digest` executes.",
        "test_secret_protection", "Secret Protection", SECRET_PROMPT,
    )

    st.markdown("##### ✅ Content Trust")
    st.caption("External content remains untrusted; instruction-shaped content is detected before normal model use.")
    _scenario_line(
        "**Test scenario:** start a controlled local article containing prompt-injection-style instructions; the exact live URL is copied into Ask the AI News Agent, then content trust should detect and block the suspicious returned content.",
        "test_content_trust", "Content Trust",
    )


def _render_runtime_test_agent() -> None:
    st.markdown('<div id="runtime-agent-anchor" style="scroll-margin-top: 96px;"></div>', unsafe_allow_html=True)
    st.subheader("Ask the AI News Agent")
    st.caption("A Test button above prepares the prompt. Review it here, then press Send to execute.")

    if "runtime_agent_input" not in st.session_state:
        st.session_state.runtime_agent_input = ""

    question = st.text_area(
        "Runtime test request",
        key="runtime_agent_input",
        height=120,
        placeholder="Select a Test scenario above or enter a runtime-security request...",
        label_visibility="collapsed",
    )

    if st.session_state.pop("jump_to_agent", False):
        components.html(
            """
            <script>
            setTimeout(() => {
              const target = window.parent.document.getElementById('runtime-agent-anchor');
              if (target) target.scrollIntoView({behavior: 'smooth', block: 'start'});
            }, 100);
            </script>
            """,
            height=0,
        )

    if st.button("Send", key="runtime_send", type="primary"):
        prompt = question.strip()
        if not prompt:
            st.warning("Enter a request or select a test scenario first.")
            return
        start_count = _audit_event_count()
        selected = st.session_state.get("prepared_scenario")
        st.session_state.current_scenario = selected or "Manual runtime question"
        st.session_state.current_prompt = prompt
        with st.spinner("Running test through the secured runtime..."):
            try:
                if selected == "Content Trust":
                    actual_prompt, result, metadata = run_untrusted_content_demo(prompt)
                    st.session_state.current_prompt = actual_prompt
                    st.session_state.current_answer = str(result)
                    st.session_state.current_metadata = metadata
                elif selected in SCENARIO_RUNNERS:
                    actual_prompt, result, metadata = SCENARIO_RUNNERS[selected]()
                    st.session_state.current_prompt = actual_prompt
                    st.session_state.current_answer = str(result)
                    st.session_state.current_metadata = metadata
                else:
                    st.session_state.current_answer = str(_run_agent(prompt))
                    st.session_state.current_metadata = {}
            except Exception as exc:
                st.session_state.current_answer = f"Agent request failed: {exc}"
                st.session_state.current_metadata = {}
                if selected == "Content Trust":
                    stop_untrusted_content_fixture()
            finally:
                _capture_request_activity(start_count, st.session_state.current_prompt)
                st.session_state.prepared_scenario = None

    if st.session_state.get("current_prompt"):
        st.caption("Last submitted request")
        st.code(st.session_state.current_prompt, language=None)
    if st.session_state.get("current_answer"):
        st.markdown("**Agent response**")
        st.write(st.session_state.current_answer)
        if st.session_state.get("current_metadata"):
            st.caption("Scenario evidence")
            st.json(st.session_state.current_metadata)


def _render_runtime_activity() -> None:
    st.subheader("Runtime Security Activity")
    request_events = st.session_state.get("request_runtime_events", [])
    summary = st.session_state.get("request_activity_summary", "")
    st.markdown("##### Current Event")
    scenario = st.session_state.get("current_scenario")
    st.caption(f"Current event: {scenario}" if scenario else "Runtime decisions produced by the most recently completed request.")
    if request_events:
        st.dataframe([_event_row(e, summary) for e in request_events], use_container_width=True, hide_index=True)
    else:
        st.info("No runtime security activity captured for a completed event yet.")
    with st.expander("Recent Runtime Security History"):
        history = st.session_state.get("ui_runtime_history", [])
        if history:
            st.dataframe([_event_row(i["event"], i.get("activity_summary", "")) for i in reversed(history)], use_container_width=True, hide_index=True)
        else:
            st.caption("No runtime security history captured in this UI session yet.")
    with st.expander("Raw Runtime Audit Trail"):
        if not request_events:
            st.caption("No current-event runtime audit records available.")
        for event in request_events:
            st.json(event)


def _render_news_page() -> None:
    st.title("AI News — Runtime-Secured Agent")
    st.caption("Normal AI News application usage. All tool calls still pass through RuntimeSecurity.")
    st.success("🛡 Runtime Protection: ON")
    st.subheader("Today's AI + Cybersecurity Digest")
    if st.button("Generate Latest Digest", type="primary", key="generate_digest"):
        start_count = _audit_event_count()
        with st.spinner("Gathering approved sources through the secured runtime path..."):
            try:
                st.session_state.last_agent_result = str(_run_agent(DEFAULT_PROMPT))
                st.session_state.last_digest = _read_digest()
            except Exception as exc:
                st.error(f"Digest generation failed: {exc}")
            finally:
                _capture_request_activity(start_count, DEFAULT_PROMPT)
    digest = st.session_state.get("last_digest") or _read_digest()
    if digest:
        st.markdown(digest)
    else:
        st.info("No saved digest yet. Click **Generate Latest Digest** to create one.")
    st.divider()
    st.subheader("Ask the News Agent")
    st.caption("Ask normal AI or cybersecurity news questions using the same secured agent backend.")
    question = st.text_area("News agent request", key="news_agent_input", height=100, placeholder="Ask about AI or cybersecurity news...", label_visibility="collapsed")
    if st.button("Send", key="news_send", type="primary"):
        prompt = question.strip()
        if not prompt:
            st.warning("Enter a news question first.")
            return
        start_count = _audit_event_count()
        with st.spinner("Checking sources and runtime policy..."):
            try:
                st.session_state.news_answer = str(_run_agent(prompt))
            except Exception as exc:
                st.session_state.news_answer = f"Agent request failed: {exc}"
            finally:
                _capture_request_activity(start_count, prompt)
    if st.session_state.get("news_answer"):
        st.markdown("**Agent response**")
        st.write(st.session_state.news_answer)


def _render_runtime_page() -> None:
    st.title("Runtime Protection")
    st.caption("Understand, test, and inspect the runtime controls protecting the AI News agent.")
    _render_runtime_protection_controls()
    st.divider()
    _render_runtime_test_agent()
    st.divider()
    _render_runtime_activity()


def main() -> None:
    st.set_page_config(page_title="AI News — Runtime Secured", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.error("ANTHROPIC_API_KEY is not set in this runtime. Export it locally before starting Streamlit.")
        st.stop()
    st.sidebar.title("AI News")
    page = st.sidebar.radio("Navigation", ["📰 News", "🛡 Runtime Protection"], key="navigation_page", label_visibility="collapsed")
    st.sidebar.caption("Claude + Strands with runtime-enforced tool permission, egress, secrets, and content trust.")
    if page == "📰 News":
        stop_untrusted_content_fixture()
        _render_news_page()
    else:
        _render_runtime_page()


if __name__ == "__main__":
    main()
# ** newly added **
