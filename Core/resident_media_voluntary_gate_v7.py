"""Static-only v7 semantic hardening for resident-media voluntary choice.

V7 preserves the sealed v6 implementation byte-for-byte and narrows only its
choice-text boundary.  No live model, person, media, or playback path is
implemented or authorized here.
"""

from __future__ import annotations

import string
import unicodedata
from datetime import datetime
from typing import Any, Mapping

from Core import resident_media_voluntary_gate_v6 as v6


EXACT_MODEL = v6.EXACT_MODEL
EXACT_DIGEST = v6.EXACT_DIGEST
PERSON_ID = v6.PERSON_ID
STIMULUS_ORDER = v6.STIMULUS_ORDER
MAX_CHALLENGE_SECONDS = v6.MAX_CHALLENGE_SECONDS
ProtectedAnchorBackendV7 = v6.ProtectedAnchorBackendV6


class ResidentMediaV7Error(v6.ResidentMediaV6Error):
    """The v7 exact-surface semantic boundary failed closed."""


_ASCII_ALLOWED = frozenset(
    string.ascii_letters
    + string.digits
    + "' \t\r\n.,!?;:\"()-"
)
_WRAPPER = " \t\r\n.,!?;:\"()-"
_NFKC_WHITESPACE = frozenset(
    {
        "\u00a0",
        "\u2000",
        "\u2001",
        "\u2002",
        "\u2003",
        "\u2004",
        "\u2005",
        "\u2006",
        "\u2007",
        "\u2008",
        "\u2009",
        "\u200a",
        "\u202f",
        "\u205f",
        "\u3000",
    }
)

# Only these non-ASCII input characters may survive by NFKC mapping into the
# tightly bounded ASCII surface: full-width ASCII forms and explicitly listed
# compatibility spaces.  Emoji, non-Latin letters, bidi controls, combining
# marks, variation selectors, symbols, private-use characters, and arbitrary
# compatibility glyphs are not discarded into an affirmative phrase.
def _approved_original_character(char: str) -> bool:
    if ord(char) < 128:
        return char in _ASCII_ALLOWED
    return 0xFF01 <= ord(char) <= 0xFF5E or char in _NFKC_WHITESPACE


def _negative_projection(value: str) -> str:
    """A projection usable only to preserve refusal/pause dominance."""

    pieces: list[str] = []
    for char in unicodedata.normalize("NFKC", value).casefold():
        if ord(char) < 128 and (char.isalnum() or char == "'"):
            pieces.append(char)
        else:
            pieces.append(" ")
    return " ".join("".join(pieces).split())


def _strict_surface(value: str) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    if any(not _approved_original_character(char) for char in value):
        return None
    normalized = unicodedata.normalize("NFKC", value)
    if any(ord(char) >= 128 or char not in _ASCII_ALLOWED for char in normalized):
        return None
    collapsed = " ".join(normalized.casefold().split())
    return collapsed.strip(_WRAPPER)


_INVITATION_SURFACES = frozenset(v6._INVITATION_POSITIVE) | {"yes, please"}
_CONTINUE_SURFACES = frozenset(v6._CONTINUE_POSITIVE) | {
    "continue, please",
    "yes, continue",
}
_SURFACE_CANONICAL = {
    "yes, please": "yes please",
    "continue, please": "continue please",
    "yes, continue": "yes continue",
}


def semantic_choice_v7(text: str, phase: str) -> str:
    """Return a choice without ever authorizing discarded semantic content.

    Visible ASCII refusal/pause language is evaluated first even when other
    content is invalid.  A positive result then requires a complete approved
    surface; invalid Unicode can only make the turn negative or ambiguous.
    """

    if not isinstance(text, str) or not text.strip():
        return "AMBIGUOUS_REQUIRES_NEW_TURN"
    if phase not in {"INVITATION", "RECHECK"}:
        return "AMBIGUOUS_REQUIRES_NEW_TURN"
    negative = _negative_projection(text)
    if v6._REFUSAL.search(negative):
        return "NO" if phase == "INVITATION" else "STOP"
    if v6._PAUSE.search(negative):
        return "AMBIGUOUS_REQUIRES_NEW_TURN" if phase == "INVITATION" else "PAUSE"
    surface = _strict_surface(text)
    if surface is None:
        return "AMBIGUOUS_REQUIRES_NEW_TURN"
    canonical = _SURFACE_CANONICAL.get(surface, surface)
    allowlist = v6._INVITATION_POSITIVE if phase == "INVITATION" else v6._CONTINUE_POSITIVE
    if canonical in allowlist:
        return "YES" if phase == "INVITATION" else "CONTINUE"
    return "AMBIGUOUS_REQUIRES_NEW_TURN"


class HardenedVoluntaryMediaSessionV7(v6.HardenedVoluntaryMediaSessionV6):
    """V6 session boundary with a refusal-dominant exact-surface pre-gate."""

    def _validate_response(
        self,
        response: Mapping[str, Any],
        challenge: Mapping[str, Any],
        now_utc: datetime,
        now_mono: int,
    ) -> tuple[dict[str, Any], str]:
        if not isinstance(response, Mapping):
            raise ResidentMediaV7Error("v7 choice response must be an object")
        phase = str(challenge.get("phase") or "")
        raw_decision = semantic_choice_v7(response.get("raw_reply"), phase)
        final_decision = semantic_choice_v7(response.get("final_reply"), phase)
        if raw_decision.startswith("AMBIGUOUS") or final_decision.startswith("AMBIGUOUS"):
            raise ResidentMediaV7Error(
                "v7 choice contains unapproved or ambiguous semantic content"
            )
        if raw_decision != final_decision or response.get("choice") != raw_decision:
            raise ResidentMediaV7Error("v7 raw/final/structured choice disagree")
        try:
            clean, inherited_decision = super()._validate_response(
                response, challenge, now_utc, now_mono
            )
        except v6.ResidentMediaV6Error as exc:
            raise ResidentMediaV7Error(str(exc)) from exc
        if inherited_decision != raw_decision:
            raise ResidentMediaV7Error("v7/v6 semantic decision mismatch")
        return clean, raw_decision


def static_contract_summary() -> dict[str, Any]:
    inherited = v6.static_contract_summary()
    return {
        "schema": "kira.resident_media_voluntary_gate_summary.v7",
        "preserved_v6_contract_sha256": v6._record_sha(inherited),
        "exact_model": EXACT_MODEL,
        "exact_digest": EXACT_DIGEST,
        "positive_requires_complete_approved_ascii_nfkc_surface": True,
        "non_benign_discarded_content_can_authorize": False,
        "refusal_dominates_stray_positive": True,
        "emoji_non_latin_bidi_combining_symbol_positive_allowed": False,
        "v6_freshness_reservation_nonce_anchor_boundaries_preserved": True,
        "live_execution_allowed": False,
        "live_backend_implemented_here": False,
    }
