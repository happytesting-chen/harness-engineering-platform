"""Canonical normalization, obfuscation signals, bounded chunking (Task 3, AD-2).

Three rules this module lives by:

1. **Stripping is a signal.** A zero-width or bidi character is removed so the rule
   layer sees the text an attacker meant to hide — and its *presence* is recorded in
   `signals`, because hiding characters is itself evidence.
2. **Flag, never decode.** A base64/hex-looking span is reported as `encoded-span`;
   it is not decoded, not recursed into. Decoding attacker content is executing it.
3. **Reject, never truncate.** Content over `max_chars` or `max_chunks` raises
   `ContentTooLarge`, which the ingress pipeline turns into REQUIRE_REVIEW. "Too long
   to read" must never report as "read and clean".

Deterministic by construction: no clock, no randomness, no environment. Stdlib only.
"""
import hashlib
import re
import unicodedata
from dataclasses import dataclass, field

from .contracts import ContentEnvelope

# Characters that hide or reorder text. Zero-width set and bidi-control set are
# flagged separately — they are different attacker techniques.
_ZERO_WIDTH = frozenset("​‌‍⁠﻿")
_BIDI_CONTROLS = frozenset(
    "‪‫‬‭‮⁦⁧⁨⁩؜‎‏"
)

# A long unbroken run of base64 alphabet (with optional padding) or hex. 40+ chars is
# past the length of ordinary words/ids that happen to be base64-alphabet-only.
_BASE64_SPAN = re.compile(r"[A-Za-z0-9+/]{40,}={0,2}")
_HEX_SPAN = re.compile(r"(?:[0-9a-fA-F]{2}){20,}")


class ContentTooLarge(Exception):
    """Raised when content exceeds the size policy. The caller quarantines; nothing
    downstream ever sees a truncated version presented as the whole."""


@dataclass(frozen=True)
class NormalizationPolicy:
    max_chars: int = 262_144  # 256 KiB of text — far above any sane single ingress

    def __post_init__(self):
        if self.max_chars <= 0:
            raise ValueError("max_chars must be positive")


@dataclass(frozen=True)
class ChunkPolicy:
    size: int = 4096
    overlap: int = 256
    max_chunks: int = 64

    def __post_init__(self):
        if self.size <= 0 or self.max_chunks <= 0:
            raise ValueError("size and max_chunks must be positive")
        if not (0 <= self.overlap < self.size):
            raise ValueError("overlap must be non-negative and smaller than size")


@dataclass(frozen=True)
class NormalizedContent:
    content_id: str
    text: str
    raw_sha256: str
    normalized_sha256: str
    signals: tuple = ()


@dataclass(frozen=True)
class ContentChunk:
    index: int
    start: int
    end: int
    text: str
    parent_raw_sha256: str
    parent_normalized_sha256: str


def normalize(envelope: ContentEnvelope, policy: NormalizationPolicy) -> NormalizedContent:
    """NFKC + hidden-character stripping + newline normalization, with every
    transformation recorded as a signal. Raises `ContentTooLarge` over `max_chars`."""
    if len(envelope.text) > policy.max_chars:
        raise ContentTooLarge(
            f"content is {len(envelope.text)} chars; policy allows {policy.max_chars}"
        )

    signals = []
    text = unicodedata.normalize("NFKC", envelope.text)

    if any(ch in _ZERO_WIDTH for ch in text):
        signals.append("zero-width")
        text = "".join(ch for ch in text if ch not in _ZERO_WIDTH)
    if any(ch in _BIDI_CONTROLS for ch in text):
        signals.append("bidi")
        text = "".join(ch for ch in text if ch not in _BIDI_CONTROLS)

    text = text.replace("\r\n", "\n").replace("\r", "\n")

    if _BASE64_SPAN.search(text) or _HEX_SPAN.search(text):
        signals.append("encoded-span")

    return NormalizedContent(
        content_id=envelope.content_id,
        text=text,
        raw_sha256=envelope.raw_sha256,
        normalized_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        signals=tuple(signals),
    )


def chunk(content: NormalizedContent, policy: ChunkPolicy) -> tuple:
    """Deterministic character windows with fixed overlap, each bound to the parent's
    raw and normalized digests. Raises `ContentTooLarge` past `max_chunks`."""
    text = content.text
    if not text:
        return ()

    step = policy.size - policy.overlap
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + policy.size, len(text))
        if len(chunks) >= policy.max_chunks:
            raise ContentTooLarge(
                f"content needs more than max_chunks={policy.max_chunks} windows "
                f"of size {policy.size}; rejection becomes review, not truncation"
            )
        chunks.append(ContentChunk(
            index=len(chunks),
            start=start,
            end=end,
            text=text[start:end],
            parent_raw_sha256=content.raw_sha256,
            parent_normalized_sha256=content.normalized_sha256,
        ))
        if end == len(text):
            break
        start += step

    return tuple(chunks)
