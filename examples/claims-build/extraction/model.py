"""The extractor interface and its implementations.

An ``Extractor`` maps raw email text to a *proposed* claim record dict. Two
implementations:

- ``FakeExtractor`` — scripted, deterministic, zero-dependency. Mirrors the
  demo/fake_model.py honesty pattern: no tokens, no network, no credentials.
  Used to prove the seam and to run the evaluation without a provider.
- ``BedrockExtractor`` — the real small/fast Bedrock client. Declared for shape,
  but intentionally NOT wired: constructing/calling it fails closed with a clear
  message, because enabling it requires the compliance review + an egress host
  (governance/mcp-allowlist.json) that are deliberately not in place yet.

The extractor's output is UNTRUSTED data. Nothing here decides an outcome.
"""
from __future__ import annotations

from typing import Protocol


class Extractor(Protocol):
    """Maps raw email text to a proposed claim record dict (untrusted)."""

    def extract(self, email_text: str) -> dict:
        ...


class FakeExtractor:
    """A scripted extractor: returns pre-set proposed records in call order.

    The email text is accepted but ignored — the point is to exercise the
    downstream seam (validate -> normalize -> route) against known extractor
    outputs, including hallucinated, malformed, and adversarial ones, with no
    model, network, or key. A real LLM would infer these dicts from the text.
    """

    def __init__(self, scripted_records: list[dict]) -> None:
        self._records = list(scripted_records)
        self._index = 0

    def extract(self, email_text: str) -> dict:
        if self._index < len(self._records):
            record = self._records[self._index]
            self._index += 1
            return record
        raise RuntimeError("FakeExtractor: script exhausted")

    def reset(self) -> None:
        self._index = 0


class BedrockExtractor:
    """Real Bedrock small/fast extractor — NOT wired in the stub build.

    Present so the seam has its production shape, but fail-closed: it cannot run
    until (a) the compliance/data-processing review passes (PII crosses to the
    provider) and (b) an egress host is added to governance/mcp-allowlist.json.
    Both are deliberately absent. Instantiating raises rather than silently
    reaching for credentials.
    """

    def __init__(self, *_args, **_kwargs) -> None:
        raise NotImplementedError(
            "BedrockExtractor is not enabled: requires the compliance review and "
            "an egress host in governance/mcp-allowlist.json (egress_hosts is []). "
            "Use FakeExtractor for the stub build."
        )

    def extract(self, email_text: str) -> dict:  # pragma: no cover - unreachable
        raise NotImplementedError
