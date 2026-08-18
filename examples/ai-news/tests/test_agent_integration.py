# ** newly added **
"""Phase 03 tests for Strands integration and no-bypass tool registration."""

import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("strands") is None,
    reason="strands-agents is not installed",
)


def test_agent_registers_only_secured_wrappers(monkeypatch):
    import src.agent as agent_module

    names = {tool.tool_name for tool in agent_module.SECURED_AGENT_TOOLS}
    assert names == {"fetch_news", "get_trending_repos", "save_digest"}


def test_wrapper_routes_fetch_through_runtime(monkeypatch):
    import src.agent as agent_module

    seen = {}

    class FakeRuntime:
        def execute(self, name, args):
            seen["name"] = name
            seen["args"] = args
            return {"ok": True}

    monkeypatch.setattr(agent_module, "_RUNTIME", FakeRuntime())
    result = agent_module.fetch_news("https://thehackernews.com/example")

    assert seen == {
        "name": "fetch_news",
        "args": {"url": "https://thehackernews.com/example"},
    }
    assert result == {"ok": True}


def test_wrapper_routes_github_through_runtime(monkeypatch):
    import src.agent as agent_module

    seen = {}

    class FakeRuntime:
        def execute(self, name, args):
            seen["name"] = name
            seen["args"] = args
            return []

    monkeypatch.setattr(agent_module, "_RUNTIME", FakeRuntime())
    assert agent_module.get_trending_repos(7) == []
    assert seen["name"] == "get_trending_repos"
    assert seen["args"]["endpoint"] == agent_module.GITHUB_SEARCH_ENDPOINT
    assert seen["args"]["days"] == 7


def test_build_agent_disables_directory_tool_loading(monkeypatch):
    import src.agent as agent_module

    captured = {}

    class FakeAgent:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(agent_module, "Agent", FakeAgent)
    marker_model = object()
    agent_module.build_agent(model=marker_model)

    assert captured["model"] is marker_model
    assert captured["tools"] == agent_module.SECURED_AGENT_TOOLS
    assert captured["load_tools_from_directory"] is False


def test_missing_api_key_fails_closed(monkeypatch):
    import src.agent as agent_module

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        agent_module.build_agent()
# ** newly added **
