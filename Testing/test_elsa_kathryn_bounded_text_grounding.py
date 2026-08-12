from __future__ import annotations

import hashlib
import json
import queue
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Core.temp_ai_source_grounding import (
    activation_block,
    bounded_text_conversation_readiness,
    read_review,
)
from Core.voice_output import VoiceOutputConfig, load_candidate_voice_config
from tools import kira_world_shell_server as shell
from tools.temporary_ai_live_chat import build_system_prompt, load_candidate


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_ROOT = ROOT / "TemporaryAI" / "candidates"
ELSA_ID = "elsa_frozen_frozen_fever_frozen_ii_20260716"
KATHRYN_ID = "kathryn_merteuil_kathryn_merteuil_20260605_213017"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ElsaKathrynBoundedTextGroundingTests(unittest.TestCase):
    def test_reviews_allow_only_bounded_owner_text(self) -> None:
        for candidate_id in (ELSA_ID, KATHRYN_ID):
            with self.subTest(candidate_id=candidate_id):
                review = read_review(CANDIDATE_ROOT, candidate_id)
                self.assertNotIn("_validation_failures", review)
                self.assertEqual(bounded_text_conversation_readiness(review), (True, []))
                self.assertFalse(review["activation"]["runtime_activation_allowed"])
                self.assertFalse(review["voice_scope"]["authorized_by_this_review"])
                text_review = review["text_conversation_review"]
                self.assertTrue(text_review["bounded_owner_text_conversation_allowed"])
                self.assertFalse(text_review["voice_allowed_by_this_review"])
                self.assertFalse(text_review["body_or_world_allowed_by_this_review"])
                self.assertFalse(text_review["life_loop_allowed_by_this_review"])
                self.assertIsNotNone(activation_block(review))

    def test_text_launcher_lists_both_as_normal_private_voice_conversations(self) -> None:
        with (
            patch.object(shell, "TEXT_ONLY_CHAT_MODE", True),
            patch.object(shell, "PRE_RAM_KIRA_ONLY_MODE", True),
        ):
            for candidate_id in (ELSA_ID, KATHRYN_ID):
                with self.subTest(candidate_id=candidate_id):
                    self.assertIsNone(shell.candidate_activation_block(candidate_id))
                    policy = shell.candidate_surface_policy(candidate_id)
                    self.assertFalse(policy["bounded_text_only"])
                    self.assertEqual(policy["conversation_mode"], "normal")
                    self.assertTrue(policy["voice_allowed"])
                    self.assertFalse(policy["world_or_body_allowed"])

    def test_text_launcher_selector_exposes_normal_names_and_voice(self) -> None:
        with (
            patch.object(shell, "TEXT_ONLY_CHAT_MODE", True),
            patch.object(shell, "PRE_RAM_KIRA_ONLY_MODE", False),
        ):
            records = {item["id"]: item for item in shell.list_candidates()}
        self.assertEqual(records[ELSA_ID]["label"], "Elsa (Frozen through Frozen II)")
        self.assertEqual(
            records[KATHRYN_ID]["label"],
            "Kathryn Merteuil",
        )
        for candidate_id in (ELSA_ID, KATHRYN_ID):
            self.assertTrue(records[candidate_id]["activatable"])
            self.assertEqual(records[candidate_id]["conversation_mode"], "normal")
            self.assertTrue(records[candidate_id]["voice_allowed"])
            self.assertFalse(records[candidate_id]["world_or_body_allowed"])

    def test_activation_endpoint_starts_each_normal_private_voice_conversation(self) -> None:
        labels = {
            ELSA_ID: "Elsa (Frozen through Frozen II)",
            KATHRYN_ID: "Kathryn Merteuil",
        }
        for candidate_id, label in labels.items():
            with self.subTest(candidate_id=candidate_id):
                state = dict(shell.DEFAULT_STATE)
                responses: list[tuple[int, dict]] = []
                handler = object.__new__(shell.Handler)
                handler.path = "/api/activate"
                handler._body = lambda candidate_id=candidate_id: {
                    "candidate": candidate_id,
                    "source": "bounded_text_activation_test",
                }
                handler._json = lambda status, payload: responses.append((status, payload))

                with (
                    patch.object(shell, "TEXT_ONLY_CHAT_MODE", True),
                    patch.object(shell, "VOICE_PREWARM_ON_ACTIVATE", False),
                    patch.object(shell, "load_state", return_value=state),
                    patch.object(
                        shell,
                        "candidate_info",
                        return_value={"id": candidate_id, "label": label},
                    ),
                    patch.object(shell, "save_state") as save_state,
                    patch.object(shell, "append_jsonl") as append_jsonl,
                    patch.object(shell, "begin_voice_session") as begin_voice,
                    patch.object(shell, "write_avatar_activity_state") as write_body_state,
                    patch.object(shell, "update_candidate") as update_candidate,
                    patch.object(shell, "saved_avatar_position", return_value=None),
                ):
                    handler.do_POST()

                self.assertEqual(len(responses), 1)
                status, payload = responses[0]
                self.assertEqual(status, 200)
                self.assertTrue(payload["ok"])
                self.assertEqual(payload["label"], label)
                self.assertFalse(payload["voice_prewarm_started"])
                self.assertIsInstance(payload.get("sensory_lease"), str)
                self.assertTrue(payload["sensory_lease"])
                self.assertEqual(state["active_candidate"], candidate_id)
                self.assertEqual(state["active_conversation_mode"], "normal")
                save_state.assert_called_once_with(state)
                append_jsonl.assert_called_once()
                begin_voice.assert_called_once_with(candidate_id, label)
                write_body_state.assert_not_called()
                # The text/voice launcher has no body or world presence.  Its
                # activation must not manufacture mutable embodied state.
                update_candidate.assert_not_called()

    def test_runtime_state_cannot_replace_authored_public_names(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            for candidate_id in (ELSA_ID, KATHRYN_ID):
                (runtime / f"{candidate_id}.json").write_text(
                    json.dumps({"candidate_id": candidate_id, "action": "idle"}),
                    encoding="utf-8",
                )
            with (
                patch.object(shell, "TEMP_AI_DIR", runtime),
                patch.object(shell, "TEXT_ONLY_CHAT_MODE", True),
                patch.object(shell, "PRE_RAM_KIRA_ONLY_MODE", False),
            ):
                records = {item["id"]: item for item in shell.list_candidates()}

        self.assertEqual(records[ELSA_ID]["label"], "Elsa (Frozen through Frozen II)")
        self.assertEqual(records[KATHRYN_ID]["label"], "Kathryn Merteuil")
        self.assertNotIn(ELSA_ID, records[ELSA_ID]["label"])
        self.assertNotIn(KATHRYN_ID, records[KATHRYN_ID]["label"])

    def test_required_voice_bindings_are_distinct_and_fail_closed(self) -> None:
        bindings = {
            candidate_id: shell.required_reference_voice_binding(candidate_id, candidate_id)
            for candidate_id in (ELSA_ID, KATHRYN_ID)
        }
        for candidate_id, binding in bindings.items():
            with self.subTest(candidate_id=candidate_id):
                self.assertTrue(binding["required"])
                self.assertTrue(binding["ready"])
                self.assertEqual(binding["engine"], "chatterbox_tts")
                self.assertTrue(binding["reference_exists"])
                self.assertNotEqual(binding["payload"]["display_name"], candidate_id)
        self.assertNotEqual(
            bindings[ELSA_ID]["reference_audio"],
            bindings[KATHRYN_ID]["reference_audio"],
        )

        blocked_queue: queue.Queue = queue.Queue()
        generic = VoiceOutputConfig(engine="windows_sapi_powershell")
        with (
            patch.object(shell, "load_candidate_voice_config", return_value=generic),
            patch.object(shell, "VOICE_REPLY_QUEUE", blocked_queue),
            patch.object(shell, "_finish_voice_benchmark"),
            patch.object(shell, "append_jsonl"),
        ):
            result = shell.queue_active_reply_voice(
                ELSA_ID,
                "Elsa (Frozen through Frozen II)",
                "Hello, Robert.",
            )
        self.assertFalse(result["spoken"])
        self.assertTrue(result["generic_fallback_blocked"])
        self.assertEqual(
            result["reason"],
            "required_reference_voice_unavailable_no_generic_fallback",
        )
        self.assertEqual(blocked_queue.qsize(), 0)

    def test_text_only_truth_boundary_catches_false_memory_location_and_internal_id(self) -> None:
        answer = (
            "I am sitting in the library area of Kira World and was thinking about "
            "our conversation earlier. " + ELSA_ID
        )
        violations = shell._text_only_reply_truth_violations(
            answer,
            has_prior_contact=False,
            candidate_id=ELSA_ID,
        )
        self.assertIn("text_only_body_or_location_claim", violations)
        self.assertIn("false_prior_contact_claim", violations)
        self.assertIn("internal_candidate_id_exposed", violations)

    def test_first_elsa_reply_is_repaired_before_it_reaches_chat(self) -> None:
        bad = "I'm sitting in the library, thinking about our conversation earlier."
        repaired = "I'm doing well, thank you. What would you like to talk about?"
        with (
            patch.object(shell, "TEXT_ONLY_CHAT_MODE", True),
            patch.object(shell, "load_candidate", return_value={"recent_chat_records": []}),
            patch.object(
                shell,
                "chat_history_for",
                return_value=[{"role": "user", "content": "How are you?"}],
            ),
            patch.object(shell, "_completed_public_chat_pairs", return_value=[]),
            patch.object(shell, "ask_model", side_effect=[bad, repaired]) as ask_model,
            patch.object(shell, "finalize_model_artifacts", None),
            patch.object(shell, "append_jsonl") as append_jsonl,
        ):
            answer = shell.temporary_ai_reply(
                ELSA_ID,
                ELSA_ID,
                "How are you?",
                "home",
                state={},
            )
        self.assertEqual(answer, repaired)
        self.assertEqual(ask_model.call_count, 2)
        first_prompt = ask_model.call_args_list[0].args[2]
        self.assertIn("first completed conversation", first_prompt)
        self.assertIn("no active 3D body", first_prompt)
        append_jsonl.assert_called_once()
        self.assertEqual(
            append_jsonl.call_args.args[1]["event"],
            "text_only_reply_truth_repaired",
        )

    def test_chat_history_is_candidate_scoped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            chat_log = Path(directory) / "chat.jsonl"
            rows = [
                {"speaker": "Robert", "to": KATHRYN_ID, "text": "Kathryn-only question"},
                {"speaker": "Kathryn Merteuil", "speaker_id": KATHRYN_ID, "to": "Robert", "text": "Kathryn-only answer"},
                {"speaker": "Robert", "to": ELSA_ID, "text": "Elsa-only question"},
                {"speaker": "Elsa", "speaker_id": ELSA_ID, "to": "Robert", "text": "Elsa-only answer"},
            ]
            chat_log.write_text(
                "".join(json.dumps(row) + "\n" for row in rows),
                encoding="utf-8",
            )
            with patch.object(shell, "CHAT_LOG", chat_log):
                history = shell.chat_history_for(
                    ELSA_ID,
                    active_label="Elsa (Frozen through Frozen II)",
                )
        content = " ".join(item["content"] for item in history)
        self.assertIn("Elsa-only question", content)
        self.assertIn("Elsa-only answer", content)
        self.assertNotIn("Kathryn-only", content)

    def test_ui_makes_start_and_stop_controls_unambiguous(self) -> None:
        page = shell.html_shell().decode("utf-8")
        self.assertIn('deactivateButton.textContent = state.active_candidate', page)
        self.assertIn('deactivateButton.disabled = !state.active_candidate', page)
        self.assertIn(': "Nothing active"', page)
        self.assertIn('selected?.conversation_mode === "bounded_text_only" ? "Start text conversation" : "Start person"', page)
        self.assertIn('id="activate" type="button"', page)
        self.assertIn('activateButton.addEventListener("pointerup", activateSelectedCandidate)', page)
        self.assertIn('activateButton.addEventListener("click", activateSelectedCandidate)', page)
        self.assertIn("if (activationInFlight) return", page)
        self.assertIn('const boundedConversation = state.text_voice_mode ||', page)
        self.assertIn('deactivateButton.addEventListener("pointerup", deactivateActiveCandidate)', page)
        self.assertIn('deactivateButton.addEventListener("click", deactivateActiveCandidate)', page)
        self.assertIn("if (deactivationInFlight || !state.active_candidate) return", page)
        self.assertIn('closeShellButton.addEventListener("pointerup", closeShellSafely)', page)
        self.assertIn('closeShellButton.addEventListener("click", closeShellSafely)', page)
        self.assertIn("if (closeInProgress) return", page)
        self.assertIn("if (state.text_voice_mode || !state.active_candidate) return true", page)
        self.assertIn("No conversation is active. Select the person", page)
        self.assertNotIn("Private typed conversation with Synthetic Robert", page)

    def test_world_launcher_still_blocks_both(self) -> None:
        with patch.object(shell, "TEXT_ONLY_CHAT_MODE", False):
            for candidate_id in (ELSA_ID, KATHRYN_ID):
                with self.subTest(candidate_id=candidate_id):
                    block = shell.candidate_activation_block(candidate_id)
                    self.assertIsNotNone(block)
                    self.assertEqual(block["reason"], "source_grounding_not_activation_ready")

    def test_each_private_chat_uses_its_own_existing_reference_wav(self) -> None:
        labels = {
            ELSA_ID: "Elsa (Frozen through Frozen II)",
            KATHRYN_ID: "Kathryn Merteuil",
        }
        for candidate_id, label in labels.items():
            with self.subTest(candidate_id=candidate_id):
                config = load_candidate_voice_config({
                    "candidate_id": candidate_id,
                    "display_name": label,
                    "gender_preference": "female",
                })
                self.assertEqual(config.engine, "chatterbox_tts")
                self.assertTrue(config.chatterbox_reference_audio)
                reference = ROOT / config.chatterbox_reference_audio
                self.assertTrue(reference.is_file())
                self.assertGreater(reference.stat().st_size, 1000)

    def test_elsa_copilot_orientation_is_not_promoted_to_canon(self) -> None:
        folder = CANDIDATE_ROOT / ELSA_ID
        ledger = load_json(folder / "scene_behavior_ledger.json")
        unverified = ledger["owner_supplied_orientation_pending_primary_confirmation"]
        self.assertTrue(unverified)
        self.assertTrue(all("unverified" in item["status"] or "not_scene_evidence" in item["status"] for item in unverified))
        canon_blob = json.dumps(
            read_review(CANDIDATE_ROOT, ELSA_ID)["canon_anchors"],
            ensure_ascii=False,
        )
        self.assertNotIn("1821", canon_blob)
        self.assertNotIn("1842", canon_blob)
        self.assertNotIn("what Elsa might say", canon_blob)

    def test_elsa_prompt_uses_selected_endpoint_and_interpretive_labels(self) -> None:
        prompt = build_system_prompt(load_candidate(ELSA_ID), "Hello, Elsa.")
        self.assertIn("end of Frozen II", prompt)
        self.assertIn("FACT: Elsa is Anna's sister", prompt)
        self.assertIn("INTERPRETIVE:", prompt)
        self.assertIn("should not reset to coronation-era panic", prompt)
        self.assertIn("Embodied world/life-loop activation remains blocked", prompt)

    def test_kathryn_preserves_branch_style_but_quarantines_inventions(self) -> None:
        folder = CANDIDATE_ROOT / KATHRYN_ID
        profile = load_json(folder / "temporary_ai_profile.json")
        branch = profile["existing_branch_continuity"]
        chat_path = ROOT / branch["live_chat_path"]
        self.assertEqual(sha256(chat_path), branch["live_chat_sha256"])
        self.assertEqual(
            profile["personality_notes"],
            "Warm, clear, and source-bounded. Natural speech preferred over status-report style. Preserve the established believable chat delivery and in-project interaction continuity; add source grounding without resetting her personality.",
        )
        prompt = build_system_prompt(load_candidate(KATHRYN_ID), "Do you remember me?")
        self.assertIn("Robert and this candidate branch have spoken before", prompt)
        self.assertIn("Reject prior drift: invented mother named Celeste", prompt)
        self.assertIn("stepsister", prompt)
        self.assertIn("do not claim a physical action", prompt)

    def test_kathryn_uses_owner_selected_interstitial_adult_present(self) -> None:
        folder = CANDIDATE_ROOT / KATHRYN_ID
        profile = load_json(folder / "temporary_ai_profile.json")
        selection = profile["continuity_selection"]
        correction_path = ROOT / selection["evidence_path"]
        self.assertEqual(sha256(correction_path), selection["evidence_sha256"])
        self.assertEqual(selection["maturity_lane"], "adult")
        self.assertEqual(
            selection["version_id"],
            "kathryn_post_1999_interstitial_pre_2016_adult_continuation_v2",
        )
        self.assertIn("approximately two years after", selection["present_timepoint"])
        self.assertIn("well before the 2016", selection["present_timepoint"])
        self.assertIn("future evidence only", selection["backstory_order"][-1])

        review = read_review(CANDIDATE_ROOT, KATHRYN_ID)
        self.assertNotIn("_validation_failures", review)
        self.assertEqual(review["identity_binding"]["maturity_lane"], "adult")
        prompt = build_system_prompt(load_candidate(KATHRYN_ID), "Where are you in your story now?")
        self.assertIn("approximately two years after Cruel Intentions (1999)", prompt)
        self.assertIn("pilot supplies later evidence only", prompt)
        self.assertIn(
            "2016-pilot appearance, relationships, status, or knowledge",
            prompt,
        )

    def test_missing_text_review_never_borrows_runtime_permission(self) -> None:
        review = read_review(CANDIDATE_ROOT, ELSA_ID)
        review = dict(review)
        review.pop("text_conversation_review")
        self.assertEqual(
            bounded_text_conversation_readiness(review),
            (False, ["text_conversation_review_missing"]),
        )


if __name__ == "__main__":
    unittest.main()
