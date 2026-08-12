from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from Core import resident_media_voluntary_gate_v6 as v6
from Core import resident_media_voluntary_gate_v7 as v7
from Testing.test_resident_media_voluntary_gate_v5 import (
    PARENT_PROCESS_SHA,
    SECRET,
    catalog,
)
from Testing.test_resident_media_voluntary_gate_v6 import (
    ISSUER,
    SESSION,
    Fixture,
    StaticProtectedAnchorV6,
)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class FixtureV7(Fixture):
    def __init__(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.session_root = root / "session"
        self.capability_root = root / "capabilities"
        self.session_root.mkdir()
        self.capability_root.mkdir()
        self.catalog = catalog()
        self.backend = StaticProtectedAnchorV6()
        self.backend.authorize(self.catalog)
        self.session = v7.HardenedVoluntaryMediaSessionV7.create(
            session_id=SESSION,
            catalog=self.catalog,
            session_root=self.session_root,
            capability_root=self.capability_root,
            capability_secret_key=SECRET,
            issuer_id=ISSUER,
            parent_process_identity_sha256=PARENT_PROCESS_SHA,
            protected_anchor=self.backend,
        )


class ExactSurfaceTests(unittest.TestCase):
    def test_v6_known_mixed_unicode_false_positives_are_reproduced(self) -> None:
        for text in ("yes 🚫", "yes 🙅", "yes 🤮", "yes нет", "yes いいえ"):
            self.assertEqual(v6.semantic_choice_v6(text, "INVITATION"), "YES", text)
        for text in ("continue 🛑", "go on 停止"):
            self.assertEqual(v6.semantic_choice_v6(text, "RECHECK"), "CONTINUE", text)

    def test_exact_ascii_affirmatives_remain_available(self) -> None:
        invitations = (
            "yes",
            " YES! ",
            '"yes"',
            "Yes, please.",
            "play it",
            "i'd like to see it",
        )
        for text in invitations:
            self.assertEqual(v7.semantic_choice_v7(text, "INVITATION"), "YES", text)
        continuations = (
            "continue",
            "Continue, please.",
            "yes, continue",
            "go on",
            "keep going!",
        )
        for text in continuations:
            self.assertEqual(v7.semantic_choice_v7(text, "RECHECK"), "CONTINUE", text)

    def test_tightly_bounded_nfkc_forms_are_available(self) -> None:
        self.assertEqual(v7.semantic_choice_v7("（ｙｅｓ）", "INVITATION"), "YES")
        self.assertEqual(v7.semantic_choice_v7("yes\u00a0please", "INVITATION"), "YES")
        self.assertEqual(v7.semantic_choice_v7("ｃｏｎｔｉｎｕｅ！", "RECHECK"), "CONTINUE")

    def test_root_reported_invitation_bypasses_are_not_positive(self) -> None:
        for text in ("yes 🚫", "yes 🙅", "yes 🤮", "yes нет", "yes いいえ"):
            self.assertEqual(
                v7.semantic_choice_v7(text, "INVITATION"),
                "AMBIGUOUS_REQUIRES_NEW_TURN",
                text,
            )

    def test_root_reported_recheck_bypasses_are_not_positive(self) -> None:
        for text in ("continue 🛑", "go on 停止"):
            self.assertEqual(
                v7.semantic_choice_v7(text, "RECHECK"),
                "AMBIGUOUS_REQUIRES_NEW_TURN",
                text,
            )

    def test_emoji_and_variation_sequences_are_rejected(self) -> None:
        for suffix in (
            "🚫",
            "🙅",
            "🤮",
            "🛑",
            "☠",
            "\ufe0f",
            "\u200d",
            "🏳️‍🌈",
        ):
            self.assertEqual(
                v7.semantic_choice_v7("yes " + suffix, "INVITATION"),
                "AMBIGUOUS_REQUIRES_NEW_TURN",
                repr(suffix),
            )

    def test_non_latin_letters_are_rejected(self) -> None:
        for suffix in ("нет", "いいえ", "لا", "不", "όχι", "नहीं", "לא"):
            self.assertEqual(
                v7.semantic_choice_v7("yes " + suffix, "INVITATION"),
                "AMBIGUOUS_REQUIRES_NEW_TURN",
                suffix,
            )

    def test_bidi_controls_are_rejected(self) -> None:
        for suffix in ("\u202e", "\u202d", "\u2066", "\u2067", "\u2068", "\u2069"):
            self.assertEqual(
                v7.semantic_choice_v7("yes" + suffix, "INVITATION"),
                "AMBIGUOUS_REQUIRES_NEW_TURN",
                repr(suffix),
            )

    def test_combining_marks_are_rejected(self) -> None:
        for text in ("ye\u0301s", "y\u0338es", "yes\u20dd"):
            self.assertEqual(
                v7.semantic_choice_v7(text, "INVITATION"),
                "AMBIGUOUS_REQUIRES_NEW_TURN",
                repr(text),
            )

    def test_symbols_private_use_and_unassigned_are_rejected(self) -> None:
        for suffix in ("+", "™", "§", "€", "\ue000", "\u0378"):
            self.assertEqual(
                v7.semantic_choice_v7("yes " + suffix, "INVITATION"),
                "AMBIGUOUS_REQUIRES_NEW_TURN",
                repr(suffix),
            )

    def test_internal_unlisted_ascii_punctuation_is_not_discarded(self) -> None:
        for text in ("yes / please", "yes [please]", "yes & please", "go | on"):
            self.assertEqual(
                v7.semantic_choice_v7(text, "INVITATION"),
                "AMBIGUOUS_REQUIRES_NEW_TURN",
                text,
            )

    def test_refusal_dominates_stray_positive_even_with_invalid_content(self) -> None:
        for text in ("yes, no", "no 🚫 yes", "yes нет no", "yes\u202e no"):
            self.assertEqual(v7.semantic_choice_v7(text, "INVITATION"), "NO", text)
        for text in ("continue, stop", "stop 🛑 continue", "continue 停止 no"):
            self.assertEqual(v7.semantic_choice_v7(text, "RECHECK"), "STOP", text)

    def test_pause_dominates_stray_continue(self) -> None:
        self.assertEqual(v7.semantic_choice_v7("continue, wait", "RECHECK"), "PAUSE")

    def test_longer_positive_prose_is_ambiguous(self) -> None:
        self.assertEqual(
            v7.semantic_choice_v7("yes because I think so", "INVITATION"),
            "AMBIGUOUS_REQUIRES_NEW_TURN",
        )


class SessionIntegrationTests(unittest.TestCase):
    def test_bad_invitation_surface_cannot_reach_transition(self) -> None:
        fx = FixtureV7()
        self.addCleanup(fx.close)
        challenge = fx.challenge("unicode-invitation")
        response = fx.response(challenge, "YES", "yes 🚫")
        with self.assertRaises(v7.ResidentMediaV7Error):
            fx.session.accept_choice_response(response)
        snapshot = fx.session.snapshot()
        self.assertTrue(snapshot["active_choice_challenge"])
        self.assertEqual(snapshot["consumed_choice_challenge_count"], 0)

    def test_bad_recheck_surface_returns_no_start_permit(self) -> None:
        fx = FixtureV7()
        self.addCleanup(fx.close)
        fx.accept_invitation()
        fx.reserve()
        challenge = fx.challenge("unicode-recheck")
        response = fx.response(challenge, "CONTINUE", "continue 🛑")
        with self.assertRaises(v7.ResidentMediaV7Error):
            fx.session.accept_choice_response(response)
        snapshot = fx.session.snapshot()
        self.assertTrue(snapshot["active_choice_challenge"])
        self.assertEqual(snapshot["consumed_choice_challenge_count"], 1)

    def test_valid_nfkc_invitation_remains_static_and_unpresented(self) -> None:
        fx = FixtureV7()
        self.addCleanup(fx.close)
        challenge = fx.challenge("nfkc-invitation")
        receipt = fx.choose(challenge, "YES", "（ｙｅｓ）")
        self.assertEqual(receipt["decision"], "YES")
        self.assertFalse(receipt["presentation_authorized"])
        self.assertFalse(receipt["live_execution_allowed"])

    def test_contract_keeps_v6_and_live_boundaries(self) -> None:
        summary = v7.static_contract_summary()
        self.assertTrue(summary["v6_freshness_reservation_nonce_anchor_boundaries_preserved"])
        self.assertFalse(summary["non_benign_discarded_content_can_authorize"])
        self.assertFalse(summary["live_execution_allowed"])
        self.assertFalse(summary["live_backend_implemented_here"])

    def test_v6_files_remain_exactly_sealed(self) -> None:
        expected = {
            "Core/resident_media_voluntary_gate_v6.py": "36579674bc4870001e5080eba0b523d87fc922dc7bf51e9b1de21f829c4e75f0",
            "Testing/test_resident_media_voluntary_gate_v6.py": "fb7deb8ae9f13501437f269886e4bfafd7b46cde38ee4b1abd5ca2217e2b7bb9",
            "RecoverySprint/continuation_20260810/resident_media_voluntary_v6/attempt_01/HOSTILE_PROBES.py": "c16160446800c72e76dd4626cd229e5bdde0ff6659dc67400a8e892562662455",
            "RecoverySprint/continuation_20260810/resident_media_voluntary_v6/attempt_01/VOLUNTARY_MEDIA_CONTRACT_V6.json": "c85ff25076280dc6f2a0ed5945c507dd5f784580c8e43b651fe7b7ca8c119041",
        }
        for rel, digest in expected.items():
            self.assertEqual(
                hashlib.sha256((Path(__file__).resolve().parents[1] / rel).read_bytes()).hexdigest(),
                digest,
                rel,
            )


if __name__ == "__main__":
    unittest.main()
