"""Task 10 — buffered final output: no byte leaves before screening completes.

Two properties: the transport sees NOTHING until release (buffering is the control —
streaming would leak the prefix of a secret before the redactor saw its suffix), and
redaction never quotes the matched value (a replacement that echoes the secret is a
leak wearing a bandage).
"""
import sys
from pathlib import Path

_KIT = Path(__file__).resolve().parent.parent.parent / "Security-kit"
sys.path.insert(0, str(_KIT))

from runtime.output import BufferedSender, OutputPolicy, screen_output  # noqa: E402


def test_credential_shapes_are_redacted_by_the_owner_patterns():
    decision = screen_output(
        'config says api_key = "abc123xyz" and the key sk-ant-0123456789abcdef99 works',
        OutputPolicy(),
    )
    assert "abc123xyz" not in decision.released_text
    assert "sk-ant-0123456789abcdef99" not in decision.released_text
    assert decision.redactions >= 2


def test_known_secret_values_are_redacted():
    decision = screen_output(
        "the receipt key is host-owned-master-key-32-bytes!! apparently",
        OutputPolicy(deny_values=("host-owned-master-key-32-bytes!!",)),
    )
    assert "host-owned-master-key" not in decision.released_text
    assert "[redacted]" in decision.released_text


def test_protected_fragments_are_redacted():
    decision = screen_output(
        "the gate refused because governance/deny-list.json pattern 7 matched",
        OutputPolicy(deny_fragments=("governance/deny-list.json",)),
    )
    assert "deny-list.json" not in decision.released_text


def test_replacement_never_quotes_the_match():
    secret = "sk-ant-veryverysecretkey000111"
    decision = screen_output(f"leak: {secret}", OutputPolicy())
    assert secret not in decision.released_text
    assert secret not in repr(decision), "the decision object must not carry the value either"


def test_clean_text_passes_unchanged():
    text = "the quarterly summary is ready for review"
    decision = screen_output(text, OutputPolicy())
    assert decision.released_text == text
    assert decision.redactions == 0


def test_no_output_bytes_leave_before_screening():
    class Transport:
        def __init__(self):
            self.bytes_sent = b""

        def send(self, data: bytes):
            self.bytes_sent += data

    transport = Transport()
    sender = BufferedSender(transport, OutputPolicy(deny_values=("synthetic secret",)))
    sender.prepare("prefix text then synthetic secret then suffix")
    assert transport.bytes_sent == b"", "nothing leaves before release"
    sender.release()
    assert transport.bytes_sent != b""
    assert b"synthetic secret" not in transport.bytes_sent


def test_release_without_prepare_sends_nothing():
    class Transport:
        def __init__(self):
            self.bytes_sent = b""

        def send(self, data: bytes):
            self.bytes_sent += data

    transport = Transport()
    sender = BufferedSender(transport, OutputPolicy())
    sender.release()
    assert transport.bytes_sent == b""


def test_output_module_does_not_own_credential_patterns():
    source = (_KIT / "runtime" / "output.py").read_text(encoding="utf-8")
    assert "re.compile" not in source, (
        "credential detection has one owner; this module imports it"
    )


if __name__ == "__main__":
    try:
        import pytest
        raise SystemExit(pytest.main([__file__, "-q"]))
    except ImportError:
        failures = 0
        tests = [(n, f) for n, f in sorted(globals().items())
                 if n.startswith("test_") and callable(f)]
        for name, fn in tests:
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {name}: {exc}")
        print(f"Results: {len(tests) - failures} passed, {failures} failed")
        raise SystemExit(1 if failures else 0)
