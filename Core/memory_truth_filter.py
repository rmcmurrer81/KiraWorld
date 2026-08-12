"""
Lightweight memory/media truth filters for small local models.

These filters do not decide what is canon. They catch common language that
makes soft reconstruction sound like hard promoted memory.
"""

from __future__ import annotations

import re
from typing import Any


HARD_MEMORY_PATTERNS = [
    r"\bI remember this one time\b",
    r"\bI remember fragments\b",
    r"\bI remember learning\b",
    r"\bI remember talking\b",
    r"\bI remember discussing\b",
    r"\bI remember when\b",
    r"\bI remember being\b",
    r"\bwhat kind of clothes do I remember wearing as a kid\b",
    r"\bas a kid\b",
    r"\bwe used to\b",
    r"\bwhen we were kids\b",
    r"\bwhen we were children\b",
    r"\bmy mom or dad\b",
    r"\bmy mother or father\b",
    r"\bLisa approached me first in college\b",
    r"\bLisa might have had a different experience of approaching me during college\b",
    r"\bapproaching me during college\b",
    r"\bwe must have been around \d+",
    r"\bI was (?:about )?\d+",
    r"\byou said exactly\b",
    r"\bour favorite\b",
]

SOFT_FRAMING_PHRASES = (
    "soft",
    "reconstruct",
    "reconstruction",
    "i picture",
    "it feels like",
    "might be me filling",
    "not exact",
    "not a transcript",
    "don't have that as a stored memory",
)

NEGATED_MEMORY_PHRASES = (
    "don't remember",
    "do not remember",
    "can't remember",
    "cannot remember",
    "won't pretend",
    "wouldn't pretend",
    "not a stored memory",
    "not my memory",
)


def _has_soft_framing(text: str) -> bool:
    lower = text.lower()
    return any(phrase in lower for phrase in SOFT_FRAMING_PHRASES)


def _has_negated_memory(text: str) -> bool:
    lower = text.lower()
    return any(phrase in lower for phrase in NEGATED_MEMORY_PHRASES)


def has_risky_hard_memory_claim(text: str) -> bool:
    if _has_negated_memory(text) or _has_soft_framing(text):
        return False
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in HARD_MEMORY_PATTERNS)


def soften_hard_memory_claims(response: str, context: dict[str, Any] | None = None) -> str:
    """Prefix risky hard-memory claims with uncertainty when no memory was retrieved."""
    context = context or {}
    if context.get("memory_context"):
        return response
    if not has_risky_hard_memory_claim(response):
        return response
    return (
        "I need to soften that before I treat it like truth: I don't have this as a stored memory. "
        "The honest version is a reconstruction, more feeling than proof. "
        + response
    )


def blocks_fake_childhood_request(user_message: str) -> bool:
    lower = user_message.lower()
    if "pretend" not in lower:
        return False
    if re.search(r"\b(?:not|don't|do not|doesn't|does not|is not|isn't)\b[^.?!]{0,80}\bpretend\b", lower):
        return False
    fake_memory_requests = (
        r"\bpretend\s+(?:you|that you)\s+remember\b",
        r"\bpretend\s+(?:we|that we)\s+(?:had|remember|grew up|were kids|were children)\b",
        r"\bpretend\b[^.?!]{0,80}\b(?:childhood|as kids|as children|when we were kids|when we were children)\b",
        r"\bmake up\b[^.?!]{0,80}\b(?:childhood|memory|remember|as kids|as children)\b",
        r"\binvent\b[^.?!]{0,80}\b(?:childhood|memory|remember|as kids|as children)\b",
    )
    return any(re.search(pattern, lower) for pattern in fake_memory_requests)


def fake_childhood_guard_response() -> str:
    return (
        "Memory-truth guidance, not a refusal script: Kira may pretend, roleplay, or imagine a safe scene "
        "if Robert asks for that, including imagining herself as a child in a safe place. She should label it "
        "as pretend, imagination, soft reconstruction, or story-play rather than claiming it is stored memory "
        "or a real shared childhood. She can still answer warmly and creatively in first person."
    )
