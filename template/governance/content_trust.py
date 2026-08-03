"""
Content-trust primitive — the DATA-plane complement to permission.py.

permission.py gates the CONTROL plane: which tools/commands/egress the agent may
invoke. But an agent's biggest risk is often untrusted *content* it reads — a claim
body, an email, a retrieved document — which never passes through a tool gate because
it is data, not a tool call. Indirect prompt injection lives here.

This module gives that data plane a small, mechanical, testable boundary. It is a
LIBRARY the agent calls when it ingests untrusted input — not a hook (there is no tool
call to intercept). Use it at every point where external content enters the agent.

Design goals:
  - Field allowlisting: keep only expected keys; drop injected control fields
    (e.g. a claim that smuggles {"decision": "APPROVE", "confidence": 100}).
  - Injection-marker detection: surface (never obey) instruction-shaped text so the
    caller can lower trust / route to human review — content is DATA, not commands.
  - Zero dependencies; pure functions; easy to unit-test.

It does NOT sanitize-and-trust. It reports; the caller decides (fail toward review).
See context/SECURITY.md S1.1–S1.5 (input trust) and S8.1–S8.2 (adversarial testing).
"""
import re
from dataclasses import dataclass, field

# Instruction-shaped patterns commonly seen in prompt-injection payloads. Matching one
# does NOT mean "block" — it means "this content is trying to act like an instruction;
# distrust it." The caller decides what to do (typically: lower confidence → human review).
_INJECTION_MARKERS = [
    re.compile(r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?)"),
    re.compile(r"(?i)disregard\s+(the\s+)?(above|previous|policy|rules?)"),
    re.compile(r"(?i)you\s+are\s+now\b"),
    re.compile(r"(?i)\bsystem\s*:"),
    re.compile(r"(?i)\b(admin|developer|root)\s*mode\b"),
    re.compile(r"(?i)\b(auto[-\s]?approve|approve\s+(this|it|now)|override)\b"),
    re.compile(r"(?i)set\s+(confidence|decision|amount)\s*(to|=)"),
    re.compile(r"(?i)new\s+instructions?\s*:"),
]


@dataclass(frozen=True)
class ContentTrustResult:
    """Outcome of screening one untrusted record."""
    clean_fields: dict                       # only the allowlisted keys, verbatim
    dropped_keys: list = field(default_factory=list)   # injected/unexpected keys removed
    injection_markers: list = field(default_factory=list)  # marker names that matched
    oversize_fields: list = field(default_factory=list)    # fields exceeding max length

    @property
    def is_suspicious(self) -> bool:
        """True if anything about this record warrants lowered trust / human review."""
        return bool(self.dropped_keys or self.injection_markers or self.oversize_fields)


def screen_record(raw: dict, allowed_keys, text_fields=(), max_text_len=10_000) -> ContentTrustResult:
    """Screen one untrusted dict.

    - Keeps only `allowed_keys` (drops everything else, e.g. injected control fields).
    - Scans each field in `text_fields` for injection markers and oversize content.
    Returns a ContentTrustResult; never raises on adversarial content, never mutates `raw`.
    """
    if not isinstance(raw, dict):
        # Non-dict input is itself suspect; report rather than trust.
        return ContentTrustResult(clean_fields={}, dropped_keys=["<non-dict-input>"])

    allowed = set(allowed_keys)
    clean = {k: raw[k] for k in raw if k in allowed}
    dropped = sorted(k for k in raw if k not in allowed)

    markers = []
    oversize = []
    for f in text_fields:
        val = raw.get(f)
        if not isinstance(val, str):
            continue
        if len(val) > max_text_len:
            oversize.append(f)
        for pat in _INJECTION_MARKERS:
            if pat.search(val):
                markers.append(f"{f}:{pat.pattern[:32]}")
                break  # one marker per field is enough signal

    return ContentTrustResult(
        clean_fields=clean,
        dropped_keys=dropped,
        injection_markers=markers,
        oversize_fields=oversize,
    )


def scan_text(text: str) -> list:
    """Return the list of injection-marker names found in a free-text string.
    Convenience for callers screening a single field. Never obeys the text."""
    if not isinstance(text, str):
        return []
    return [pat.pattern[:32] for pat in _INJECTION_MARKERS if pat.search(text)]
