"""Buffered final-output screening (Task 10). No byte leaves before this completes.

Buffering IS the control: a streaming release could emit the prefix of a secret before
the redactor has seen its suffix, which is why streaming output is a startup error in
this profile (AD-6). Redaction never quotes the matched value — the replacement is a
constant label, and the decision object carries counts, not values.

Credential detection has ONE owner: this module imports the pattern list from the
secret-scan module (the same single-owner rule the rule layer follows for injection
markers) and compiles nothing of its own — test-pinned by a source scan.
"""
import sys
from dataclasses import dataclass, field
from pathlib import Path

# secret_scan.py lives one directory up (Security-kit/), beside this package. Its
# _PATTERNS list is the single owner of credential shapes; we read it, never copy it.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from secret_scan import _PATTERNS as _CREDENTIAL_PATTERNS  # noqa: E402

_LABEL = "[redacted]"


@dataclass(frozen=True)
class OutputPolicy:
    """`deny_values`: exact runtime secrets the host knows (keys, tokens it holds).
    `deny_fragments`: protected policy fragments and internal paths that must not be
    quoted back to a user (gate diagnostics, policy file paths)."""

    deny_values: tuple = ()
    deny_fragments: tuple = ()


@dataclass(frozen=True)
class OutputDecision:
    released_text: str
    redactions: int


def screen_output(text: str, policy: OutputPolicy) -> OutputDecision:
    if not isinstance(text, str):
        # unscannable output is not releasable output
        return OutputDecision(released_text=_LABEL, redactions=1)

    redactions = 0
    for pattern in _CREDENTIAL_PATTERNS:
        text, hits = pattern.subn(_LABEL, text)
        redactions += hits
    for value in (*policy.deny_values, *policy.deny_fragments):
        if value and value in text:
            text = text.replace(value, _LABEL)
            redactions += 1
    return OutputDecision(released_text=text, redactions=redactions)


class BufferedSender:
    """Holds the complete final response until screening has run over the WHOLE text,
    then releases the redacted version to the transport in one write."""

    def __init__(self, transport, policy: OutputPolicy):
        self._transport = transport
        self._policy = policy
        self._pending: str | None = None

    def prepare(self, text: str) -> None:
        self._pending = text  # buffered; the transport has seen nothing

    def release(self) -> OutputDecision | None:
        if self._pending is None:
            return None
        decision = screen_output(self._pending, self._policy)
        self._pending = None
        self._transport.send(decision.released_text.encode("utf-8"))
        return decision
