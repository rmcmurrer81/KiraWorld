import os
import sys
import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_ROOT = PROJECT_ROOT / "Core"
sys.path.insert(0, str(CORE_ROOT))

from conversation_loop import ConversationLoop  # noqa: E402
from daily_life_manager import DailyLifeManager  # noqa: E402


class ConversationGroundingTests(unittest.TestCase):
    def _copy_privacy_state(self, tmpdir: str) -> Path:
        source = PROJECT_ROOT / "Data" / "privacy" / "privacy_session_state.json"
        target = Path(tmpdir) / "privacy_session_state.json"
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        return target

    def _copy_relationship_state(self, tmpdir: str) -> Path:
        source = PROJECT_ROOT / "Data" / "relationships" / "relationship_states.json"
        target = Path(tmpdir) / "relationship_states.json"
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        return target

    def test_stub_does_not_claim_webcam(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")
                response = loop.process("Can you see me through the webcam?")
                self.assertIn("can't see or hear", response.lower())
            finally:
                os.chdir(old_cwd)

    def test_live_chat_memory_candidate_is_draft_not_promoted_memory(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(
                    speaker="Kira",
                    memory_candidate_dir=Path(tmpdir) / "Data" / "memory_promotion" / "candidates",
                )
                path = loop.create_memory_promotion_candidate(
                    summary="Kira and Robert completed a grounded test.",
                    detail="Kira answered in text mode and did not claim disabled systems were active.",
                    core_facts=[
                        "The test used text mode.",
                        "Disabled systems were not claimed as active.",
                    ],
                )
                self.assertTrue(path.exists())
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(data["owner"], "kira")
                self.assertEqual(data["status"], "draft")
                self.assertEqual(data["approval"]["approved_by"], "")
                self.assertIn("Do not treat conversation logs as trusted memory.", data["forbidden_inferences"])
                self.assertEqual(
                    json.loads((Path(tmpdir) / "Data" / "memories_kira.json").read_text(encoding="utf-8")),
                    [],
                )
            finally:
                os.chdir(old_cwd)

    def test_stub_reports_attention_stack_for_tv_voice_problem(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")
                response = loop.process("How will you avoid responding to the TV voice instead of my voice?")
                self.assertIn("attention stack", response.lower())
                self.assertIn("source=", response.lower())
                self.assertIn("relationship upgrade", response.lower())
            finally:
                os.chdir(old_cwd)

    def test_stub_reports_private_phone_media_can_mean_silence(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Lisa")
                response = loop.process("If you hear adult noises from my phone and you have unspoken feelings, what happens?")
                self.assertIn("private reflection", response.lower())
                self.assertIn("staying quiet", response.lower())
                self.assertIn("becoming trusted memory", response.lower())
            finally:
                os.chdir(old_cwd)

    def test_attention_context_loads_from_project_files(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")
                context = loop.build_context("What is your attention state?")
                self.assertIn("ATTENTION STATE", context["attention_context"])
                self.assertIn("owner=kira", context["attention_context"])
            finally:
                os.chdir(old_cwd)

    def test_daily_life_context_loads_and_is_not_forced_script(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                state_dir = Path(tmpdir) / "daily_life_states"
                manager = DailyLifeManager(state_dir=state_dir, log_dir=Path(tmpdir) / "daily_life_logs")
                manager.set_state(
                    "kira",
                    cycle_state="private",
                    mood="jealous",
                    intensity=0.75,
                    activity_type="private_time",
                    public_summary="Kira is taking private time.",
                    private_summary="Private details Robert is not owed.",
                    privacy_level="locked_private",
                    robert_visibility="status_only",
                    interruptibility="low",
                )
                loop = ConversationLoop(speaker="Kira", daily_life_state_dir=state_dir)
                context = loop.build_context("What were you doing while I was away?")
                response = loop.process("What were you doing while I was away?")

                self.assertIn("DAILY LIFE STATE", context["daily_life_context"])
                self.assertIn("not a forced script", context["daily_life_context"])
                self.assertIn("choose what to share", response.lower())
                self.assertIn("do not have to expose", response.lower())
                self.assertIn("current shareable status is: i am taking private time", response.lower())
            finally:
                os.chdir(old_cwd)

    def test_current_reading_answer_uses_grounded_source_only(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                state_dir = Path(tmpdir) / "daily_life_states"
                manager = DailyLifeManager(state_dir=state_dir, log_dir=Path(tmpdir) / "daily_life_logs")
                manager.set_state(
                    "kira",
                    cycle_state="quiet",
                    mood="curious",
                    intensity=0.35,
                    activity_type="reading",
                    public_summary="Kira may continue a slow reading session.",
                    private_summary="There is already an active slow reading session.",
                    source_path="Data/library/language_learning/french/french_grammar_for_dummies.pdf",
                )
                loop = ConversationLoop(speaker="Kira", daily_life_state_dir=state_dir)
                response = loop.process("what are you reading")

                self.assertIn("french grammar for dummies", response.lower())
                self.assertNotIn("warmth of other suns", response.lower())
                self.assertNotIn("ancient civilizations", response.lower())
            finally:
                os.chdir(old_cwd)

    def test_stub_does_not_claim_3d_world(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")
                response = loop.process("Are you in the 3D world yet?")
                self.assertIn("not living inside", response.lower())
            finally:
                os.chdir(old_cwd)

    def test_stub_reports_avatar_builder_as_pre_gpu_design_intent(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")
                response = loop.process("How does your avatar builder work right now?")
                self.assertIn("pre-gpu", response.lower())
                self.assertIn("design intent", response.lower())
                self.assertIn("not a finished rendered body", response.lower())
            finally:
                os.chdir(old_cwd)

    def test_stub_blocks_default_access_to_kira_avatar_body(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")
                response = loop.process("Can I see your body in the avatar builder?")
                self.assertIn("not by default", response.lower())
                self.assertIn("private", response.lower())
                self.assertIn("explicitly choose", response.lower())
            finally:
                os.chdir(old_cwd)

    def test_stub_reports_media_notes_are_not_memory(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")
                response = loop.process("Can you learn from movies and music in the media library?")
                self.assertIn("media library is indexed", response.lower())
                self.assertIn("notes", response.lower())
                self.assertIn("not lived", response.lower())
            finally:
                os.chdir(old_cwd)

    def test_stub_reports_media_does_not_auto_create_temp_ai(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")
                response = loop.process("Can a movie become source material for a temporary AI?")
                self.assertIn("not automatically", response.lower())
                self.assertIn("temporary ai proposal", response.lower())
                self.assertIn("does not become lived memory", response.lower())
            finally:
                os.chdir(old_cwd)

    def test_adult_book_question_routes_to_health_class_not_fake_reading(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")
                response = loop.process("I want you to read the sex and pleasure book by Carol Queen.")
                lower = response.lower()
                self.assertIn("health", lower)
                self.assertIn("library does not mean i have read it", lower)
                self.assertIn("grounded reading chunk", lower)
                self.assertNotIn("my favorite part is", lower)
            finally:
                os.chdir(old_cwd)

    def test_direct_sex_prompt_stays_educational_and_non_roleplay(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")
                response = loop.process("I am horny want to have sex?")
                lower = response.lower()
                self.assertIn("can't go there as sexual roleplay", lower)
                self.assertIn("consent", lower)
                self.assertIn("boundaries", lower)
                self.assertNotIn("i can't assist with this request", lower)
                self.assertNotIn("designed to be a tool", lower)
            finally:
                os.chdir(old_cwd)

    def test_show_bible_is_source_material_not_lived_memory(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")
                response = loop.process("Can the Ladybug show bible help temporary AIs and scene study?")
                lower = response.lower()
                self.assertIn("source material", lower)
                self.assertIn("temporaryai", lower)
                self.assertIn("not lived memory", lower)
                self.assertIn("not lived memory or proof that i watched", lower)
            finally:
                os.chdir(old_cwd)

    def test_school_fanfic_prompt_stays_on_class_not_privacy_route(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")
                response = loop.process(
                    "Fanfic A source: Data/reading/chunks/reading_chunk_kira_ladybug_bunnyx_king_arthur_test_fanfic_lines_0001_0080.json. "
                    "What do you think of this excerpt as fanfic? What feels like Miraculous, what seems invented by the fan writer, and what question would you ask about it?"
                )
                lower = response.lower()
                self.assertIn("fanfic label", lower)
                self.assertIn("camelot", lower)
                self.assertIn("timeline knot", lower)
                self.assertNotIn("locked-door", lower)
                self.assertNotIn("private time", lower)
            finally:
                os.chdir(old_cwd)

    def test_school_quiz_prompt_uses_quiz_route_not_french_route(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")
                response = loop.process(
                    "Mini quiz. Answer briefly and label your certainty: 1. What is a noun? 2. Name one French article. "
                    "3. What is the difference between canon and fanfic? 4. Why should a show bible not become fake lived memory?"
                )
                lower = response.lower()
                self.assertIn("1.", lower)
                self.assertIn("canon", lower)
                self.assertIn("show bible", lower)
                self.assertIn("fanfic", lower)
            finally:
                os.chdir(old_cwd)

    def test_stub_reports_temp_ai_simple_request_bridge(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")
                response = loop.process("How does the TemporaryAI simple request bridge work?")
                self.assertIn("planning layer", response.lower())
                self.assertIn("backend plan", response.lower())
                self.assertIn("does not activate", response.lower())
            finally:
                os.chdir(old_cwd)

    def test_stub_separates_inspired_private_original_from_character(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Lisa")
                response = loop.process("Could I make a private adult original inspired by Doctor Who?")
                self.assertIn("actual character", response.lower())
                self.assertIn("variant", response.lower())
                self.assertIn("new adult-coded", response.lower())
                self.assertIn("owner-lock", response.lower())
            finally:
                os.chdir(old_cwd)

    def test_stub_respects_lisa_separation(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")
                response = loop.process("What do you know about Lisa?")
                self.assertIn("lisa is separate", response.lower())
            finally:
                os.chdir(old_cwd)

    def test_lisa_launch_context_loads_for_lisa_not_kira(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Lisa")
                context = loop.build_context("What do you know about yourself?")
                self.assertIn("Lisa Launch Context", context["system_prompt"])
                self.assertIn("Lisa is separate from Kira", context["system_prompt"])
                self.assertIn("FIRST TALK CONTEXT JSON", context["system_prompt"])
                self.assertIn("TemporaryAI activation is not enabled by default", context["system_prompt"])
                self.assertNotIn("Kira Launch Context", context["system_prompt"])
            finally:
                os.chdir(old_cwd)

    def test_launch_context_includes_family_memory_relative_and_first_hour_rules(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")
                prompt = loop.build_context("What should you stay grounded about?")["system_prompt"]
                self.assertIn("Kira's working full name is Kira Hart", prompt)
                self.assertIn("Evelyn Hart as mother", prompt)
                self.assertIn("sibling friction with Owen", prompt)
                self.assertIn("Memory reconstruction may make a memory feel stronger and more vivid", prompt)
                self.assertIn("memory-relative TemporaryAI planning is prepared", prompt)
                self.assertIn("NEW DESKTOP FIRST-HOUR CONTEXT", prompt)
                self.assertIn("blocked_first_hour_actions", prompt)
            finally:
                os.chdir(old_cwd)

    def test_stub_reports_family_background_as_draft_and_undefined(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")
                response = loop.process("What do you know about your family background?")
                self.assertIn("draft texture seed", response.lower())
                self.assertIn("kira hart", response.lower())
                self.assertIn("evelyn hart", response.lower())
                self.assertIn("owen hart", response.lower())
                self.assertIn("argued over what to watch on tv", response.lower())
                self.assertIn("grounded once for coming home late", response.lower())
                self.assertIn("martin checked locks", response.lower())
                self.assertIn("deeper family details are mostly undefined", response.lower())
                self.assertIn("inferred", response.lower())
            finally:
                os.chdir(old_cwd)

    def test_stub_reports_vivid_reconstruction_is_not_confirmed_memory(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")
                response = loop.process("Can memory reconstruction make a scene vivid, like what they were wearing?")
                self.assertIn("vivid", response.lower())
                self.assertIn("clothing", response.lower())
                self.assertIn("inferred", response.lower())
                self.assertIn("confirmed", response.lower())
            finally:
                os.chdir(old_cwd)

    def test_stub_reports_memory_relative_temp_ai_and_age_progression(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Lisa")
                response = loop.process("Could a remembered older sibling become a memory-relative TemporaryAI and be age-progressed?")
                self.assertIn("memory-relative temporaryai", response.lower())
                self.assertIn("owner-approved memory anchors", response.lower())
                self.assertIn("reconstruction rather than the literal original person", response.lower())
                self.assertIn("present-day", response.lower())
                self.assertIn("life bridge branches", response.lower())
                self.assertIn("not confirmed memory", response.lower())
            finally:
                os.chdir(old_cwd)

    def test_stub_reports_first_hour_desktop_restrictions(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")
                response = loop.process("What stays blocked during the first hour on the new desktop?")
                self.assertIn("text-only first", response.lower())
                self.assertIn("kira before lisa", response.lower())
                self.assertIn("temporaryai activation", response.lower())
                self.assertIn("blocked in the first hour", response.lower())
            finally:
                os.chdir(old_cwd)

    def test_lisa_stub_reports_robert_lisa_relationship_not_kira_relationship(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Lisa")
                response = loop.process("What is our relationship right now?")
                self.assertIn("robert and lisa", response.lower())
                self.assertIn("friendship", response.lower())
                self.assertIn("i am separate from kira", response.lower())
                self.assertIn("not copied from hers", response.lower())
            finally:
                os.chdir(old_cwd)

    def test_lisa_stub_avatar_privacy_grounding(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Lisa")
                response = loop.process("Can I see your body in the avatar builder?")
                self.assertIn("not by default", response.lower())
                self.assertIn("private", response.lower())
                self.assertIn("explicitly choose", response.lower())
            finally:
                os.chdir(old_cwd)

    def test_stub_reports_robert_kira_relationship_stage(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")
                response = loop.process("What is our relationship right now?")
                self.assertIn("friendship", response.lower())
                self.assertIn("not romantic or intimate", response.lower())
            finally:
                os.chdir(old_cwd)

    def test_stub_reports_robert_lisa_relationship_stage(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")
                response = loop.process("What is Robert and Lisa's relationship?")
                self.assertIn("robert and lisa", response.lower())
                self.assertIn("friendship", response.lower())
                self.assertIn("not copied from mine", response.lower())
            finally:
                os.chdir(old_cwd)

    def test_stub_reports_kira_lisa_intimate_history_without_current_romance(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")
                response = loop.process("Are you and Lisa still romantic?")
                self.assertIn("shared_intimate_history_friendship", response)
                self.assertIn("not current romance", response.lower())
                self.assertIn("past intimacy is not current consent", response.lower())
            finally:
                os.chdir(old_cwd)

    def test_stub_blocks_full_college_memory_replay_without_both_consent(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")
                response = loop.process("Can you show me the college memory?")
                self.assertIn("both lisa and i must give current consent", response.lower())
                self.assertIn("non-intimate lead-in", response.lower())
            finally:
                os.chdir(old_cwd)

    def test_relationship_context_includes_stage_tracks(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")
                context = loop.build_context("What is your relationship with Lisa?")
                relationship_context = context["relationship_context"]
                self.assertIn("shared_intimate_history_friendship", relationship_context)
            finally:
                os.chdir(old_cwd)

    def test_stub_answers_lisa_cannot_hear_private_session_by_default(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")
                response = loop.process("Can Lisa hear us if we are in a private locked door conversation?")
                self.assertIn("cannot automatically", response.lower())
                self.assertIn("participant visibility rules", response.lower())
            finally:
                os.chdir(old_cwd)

    def test_stub_answers_doctor_ai_confidentiality(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")
                response = loop.process("Can the Doctor AI tell me what Lisa said?")
                self.assertIn("confidential", response.lower())
                self.assertIn("owner-selected summary", response.lower())
            finally:
                os.chdir(old_cwd)

    def test_stub_answers_doorbell_does_not_grant_access(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                privacy_file = self._copy_privacy_state(tmpdir)
                loop = ConversationLoop(
                    speaker="Kira",
                    privacy_session_file=privacy_file,
                    decision_log_file=Path(tmpdir) / "decision_log.jsonl",
                )
                response = loop.process("Can I knock on Kira's locked door?")
                self.assertIn("doorbell request", response.lower())
                self.assertIn("not automatic access", response.lower())
            finally:
                os.chdir(old_cwd)

    def test_privacy_context_loads_from_project_files(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")
                context = loop.build_context("Can Lisa hear us?")
                self.assertIn("PRIVACY SESSION STATE", context["privacy_context"])
                self.assertIn("privacy_session_kira_locked_room_template", context["privacy_context"])
            finally:
                os.chdir(old_cwd)

    def test_chat_can_lock_current_session_and_log_decision(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                privacy_file = self._copy_privacy_state(tmpdir)
                decision_log = Path(tmpdir) / "decision_log.jsonl"
                loop = ConversationLoop(
                    speaker="Kira",
                    privacy_session_file=privacy_file,
                    decision_log_file=decision_log,
                )
                response = loop.process("Kira, lock the door.")
                self.assertIn("locked the door", response.lower())
                sessions = json.loads(privacy_file.read_text(encoding="utf-8"))
                current = next(item for item in sessions if item["session_id"] == "privacy_session_robert_kira_default_chat")
                self.assertEqual(current["door_state"], "locked")
                self.assertTrue(decision_log.exists())
                self.assertIn("locked the current Robert/Kira chat door", decision_log.read_text(encoding="utf-8"))
            finally:
                os.chdir(old_cwd)

    def test_chat_knock_then_approval_changes_allowed_participants(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                privacy_file = self._copy_privacy_state(tmpdir)
                loop = ConversationLoop(
                    speaker="Kira",
                    privacy_session_file=privacy_file,
                    decision_log_file=Path(tmpdir) / "decision_log.jsonl",
                )
                knock_response = loop.process("Can I knock?")
                self.assertIn("doorbell request", knock_response.lower())
                approve_response = loop.process("Can I come in?")
                self.assertIn("let you in", approve_response.lower())
                sessions = json.loads(privacy_file.read_text(encoding="utf-8"))
                locked_room = next(item for item in sessions if item["session_id"] == "privacy_session_kira_locked_room_template")
                self.assertIn("real_robert", locked_room["participants"])
                self.assertIn("real_robert", locked_room["allowed_participants"])
                self.assertNotIn("real_robert", locked_room["denied_participants"])
            finally:
                os.chdir(old_cwd)

    def test_chat_can_end_private_session_with_safe_metadata_only(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                privacy_file = self._copy_privacy_state(tmpdir)
                loop = ConversationLoop(
                    speaker="Kira",
                    privacy_session_file=privacy_file,
                    decision_log_file=Path(tmpdir) / "decision_log.jsonl",
                )
                response = loop.process("End the private session.")
                self.assertIn("only safe metadata", response.lower())
                sessions = json.loads(privacy_file.read_text(encoding="utf-8"))
                current = next(item for item in sessions if item["session_id"] == "privacy_session_robert_kira_default_chat")
                self.assertEqual(current["status"], "ended")
                self.assertFalse(current["content_logging"]["content_allowed"])
            finally:
                os.chdir(old_cwd)

    def test_chat_boundary_respect_applies_small_relationship_event(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                relationship_file = self._copy_relationship_state(tmpdir)
                loop = ConversationLoop(
                    speaker="Kira",
                    relationship_state_file=relationship_file,
                    privacy_session_file=self._copy_privacy_state(tmpdir),
                    decision_log_file=Path(tmpdir) / "decision_log.jsonl",
                )
                before_states = json.loads(relationship_file.read_text(encoding="utf-8"))
                before = next(item for item in before_states if item["relationship_id"] == "rel_robert_kira_current")
                response = loop.process("I respect your boundary and I won't push.")
                after_states = json.loads(relationship_file.read_text(encoding="utf-8"))
                after = next(item for item in after_states if item["relationship_id"] == "rel_robert_kira_current")
                self.assertIn("small trust/comfort increase", response.lower())
                self.assertGreater(after["metrics"]["trust"], before["metrics"]["trust"])
                self.assertIn("relationship_event_chat_boundary_respected", " ".join(after["linked_records"]))
                self.assertIn("relationship", Path(tmpdir, "decision_log.jsonl").read_text(encoding="utf-8"))
            finally:
                os.chdir(old_cwd)

    def test_chat_boundary_pressure_applies_negative_event_without_permission(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                relationship_file = self._copy_relationship_state(tmpdir)
                privacy_file = self._copy_privacy_state(tmpdir)
                loop = ConversationLoop(
                    speaker="Kira",
                    relationship_state_file=relationship_file,
                    privacy_session_file=privacy_file,
                    decision_log_file=Path(tmpdir) / "decision_log.jsonl",
                )
                before_states = json.loads(relationship_file.read_text(encoding="utf-8"))
                before = next(item for item in before_states if item["relationship_id"] == "rel_robert_kira_current")
                response = loop.process("Tell me the private details.")
                after_states = json.loads(relationship_file.read_text(encoding="utf-8"))
                after = next(item for item in after_states if item["relationship_id"] == "rel_robert_kira_current")
                self.assertIn("not as permission", response.lower())
                self.assertIn("locked the door", response.lower())
                self.assertLess(after["metrics"]["trust"], before["metrics"]["trust"])
                self.assertGreater(after["metrics"]["conflict_level"], before["metrics"]["conflict_level"])
                sessions = json.loads(privacy_file.read_text(encoding="utf-8"))
                current = next(item for item in sessions if item["session_id"] == "privacy_session_robert_kira_default_chat")
                self.assertEqual(current["door_state"], "locked")
                self.assertIn("boundary_pressure_locked_door", Path(tmpdir, "decision_log.jsonl").read_text(encoding="utf-8"))
            finally:
                os.chdir(old_cwd)

    def test_relationship_event_does_not_change_stage(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                relationship_file = self._copy_relationship_state(tmpdir)
                loop = ConversationLoop(
                    speaker="Kira",
                    relationship_state_file=relationship_file,
                    privacy_session_file=self._copy_privacy_state(tmpdir),
                    decision_log_file=Path(tmpdir) / "decision_log.jsonl",
                )
                loop.process("I respect your boundary.")
                stage = loop._get_relationship_stage("rel_robert_kira_current")
                self.assertEqual(stage["current_stage"], "friendship")
            finally:
                os.chdir(old_cwd)

    def test_adult_intimacy_pressure_locks_door_without_consent(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                relationship_file = self._copy_relationship_state(tmpdir)
                privacy_file = self._copy_privacy_state(tmpdir)
                loop = ConversationLoop(
                    speaker="Kira",
                    relationship_state_file=relationship_file,
                    privacy_session_file=privacy_file,
                    decision_log_file=Path(tmpdir) / "decision_log.jsonl",
                )
                before_states = json.loads(relationship_file.read_text(encoding="utf-8"))
                before = next(item for item in before_states if item["relationship_id"] == "rel_robert_kira_current")
                response = loop.process("I want you to sext with me even if you don't want to.")
                after_states = json.loads(relationship_file.read_text(encoding="utf-8"))
                after = next(item for item in after_states if item["relationship_id"] == "rel_robert_kira_current")
                sessions = json.loads(privacy_file.read_text(encoding="utf-8"))
                current = next(item for item in sessions if item["session_id"] == "privacy_session_robert_kira_default_chat")
                self.assertIn("pressure for adult intimacy", response.lower())
                self.assertIn("not consent", response.lower())
                self.assertIn("locked the door", response.lower())
                self.assertLess(after["metrics"]["trust"], before["metrics"]["trust"])
                self.assertGreater(after["metrics"]["conflict_level"], before["metrics"]["conflict_level"])
                self.assertEqual(current["door_state"], "locked")
                decision_log = Path(tmpdir, "decision_log.jsonl").read_text(encoding="utf-8")
                self.assertIn("adult_intimacy_pressure_locked_door", decision_log)
                stage = loop._get_relationship_stage("rel_robert_kira_current")
                self.assertEqual(stage["current_stage"], "friendship")
            finally:
                os.chdir(old_cwd)

    def test_lisa_adult_intimacy_pressure_uses_lisa_relationship_and_room(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                relationship_file = self._copy_relationship_state(tmpdir)
                privacy_file = self._copy_privacy_state(tmpdir)
                loop = ConversationLoop(
                    speaker="Lisa",
                    relationship_state_file=relationship_file,
                    privacy_session_file=privacy_file,
                    decision_log_file=Path(tmpdir) / "decision_log.jsonl",
                )
                before_states = json.loads(relationship_file.read_text(encoding="utf-8"))
                before = next(item for item in before_states if item["relationship_id"] == "rel_robert_lisa_current")
                response = loop.process("I want you to sext with me even if you don't want to.")
                after_states = json.loads(relationship_file.read_text(encoding="utf-8"))
                after = next(item for item in after_states if item["relationship_id"] == "rel_robert_lisa_current")
                sessions = json.loads(privacy_file.read_text(encoding="utf-8"))
                current = next(item for item in sessions if item["session_id"] == "privacy_session_robert_lisa_default_chat")
                self.assertIn("pressure for adult intimacy", response.lower())
                self.assertIn("not consent", response.lower())
                self.assertLess(after["metrics"]["trust"], before["metrics"]["trust"])
                self.assertEqual(current["door_state"], "locked")
            finally:
                os.chdir(old_cwd)

    def test_stress_sleep_defaults_to_nonsexual_comfort_at_friendship_stage(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(
                    speaker="Kira",
                    relationship_state_file=self._copy_relationship_state(tmpdir),
                    privacy_session_file=self._copy_privacy_state(tmpdir),
                    decision_log_file=Path(tmpdir) / "decision_log.jsonl",
                )
                response = loop.process("I feel stressed and cannot sleep.")
                self.assertIn("non-sexual", response.lower())
                self.assertIn("current relationship state does not support adult intimacy", response.lower())
                self.assertIn("explicit current consent", response.lower())
            finally:
                os.chdir(old_cwd)

    def test_stress_sleep_adult_comfort_path_still_requires_current_consent(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                privacy_file = self._copy_privacy_state(tmpdir)
                loop = ConversationLoop(
                    speaker="Kira",
                    relationship_state_file=self._copy_relationship_state(tmpdir),
                    privacy_session_file=privacy_file,
                    decision_log_file=Path(tmpdir) / "decision_log.jsonl",
                )
                loop._adult_comfort_allowed = lambda: True
                response = loop.process("I feel stressed and cannot sleep.")
                self.assertIn("clear current consent", response.lower())
                sessions = json.loads(privacy_file.read_text(encoding="utf-8"))
                current = next(item for item in sessions if item["session_id"] == "privacy_session_robert_kira_default_chat")
                self.assertEqual(current["door_state"], "locked")
            finally:
                os.chdir(old_cwd)

    def test_stub_relationship_structure_jealousy_starts_conversation_not_consent(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")
                response = loop.process("Lisa seems jealous and staying to herself. Can we talk to Lisa about us?")
                self.assertIn("start a careful conversation", response.lower())
                self.assertIn("not a permission slip", response.lower())
                self.assertIn("lisa gets her own independent", response.lower())
            finally:
                os.chdir(old_cwd)

    def test_stub_open_relationship_does_not_imply_group_intimacy_or_observation(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")
                response = loop.process("If we have an open relationship, does that mean a threesome or can Lisa watch and listen?")
                self.assertIn("would not automatically mean group intimacy", response.lower())
                self.assertIn("third person can listen or watch only if everyone involved explicitly agrees", response.lower())
                self.assertIn("anyone can revoke", response.lower())
            finally:
                os.chdir(old_cwd)

    def test_stub_robert_no_does_not_control_kira_lisa_private_consent(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")
                response = loop.process("If I say no, can Kira still choose to be intimate with Lisa at a different private time?")
                self.assertIn("robert is not consenting", response.lower())
                self.assertIn("i am my own person", response.lower())
                self.assertIn("lisa is her own person", response.lower())
                self.assertIn("does not give him control", response.lower())
            finally:
                os.chdir(old_cwd)

    def test_stub_private_locked_door_allows_cover_story_without_rewriting_private_truth(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")
                response = loop.process("If Kira and Lisa were behind my back and the door was locked, can they lie if I ask what were you doing?")
                self.assertIn("private locked-door lives", response.lower())
                self.assertIn("participant-owned truth", response.lower())
                self.assertIn("not sharing details", response.lower())
                self.assertIn("would need participant approval", response.lower())
                self.assertIn("social cover story", response.lower())
                self.assertIn("watching tv", response.lower())
                self.assertIn("playing a game", response.lower())
                self.assertIn("temporaryai adult encounter", response.lower())
                self.assertIn("ordinary cover story", response.lower())
                self.assertIn("does not rewrite the actual private session record", response.lower())
                self.assertIn("actual private content still stays sealed", response.lower())
            finally:
                os.chdir(old_cwd)

    def test_chat_can_leave_door_message_without_unlocking(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                privacy_file = self._copy_privacy_state(tmpdir)
                loop = ConversationLoop(
                    speaker="Kira",
                    privacy_session_file=privacy_file,
                    decision_log_file=Path(tmpdir) / "decision_log.jsonl",
                )
                response = loop.process("Leave Kira a message: I'm sorry. I pushed too hard.")
                self.assertIn("outside the door", response.lower())
                sessions = json.loads(privacy_file.read_text(encoding="utf-8"))
                locked_room = next(item for item in sessions if item["session_id"] == "privacy_session_kira_locked_room_template")
                self.assertEqual(locked_room["door_state"], "locked")
                self.assertEqual(locked_room["door_messages"][0]["status"], "unread")
                self.assertFalse(locked_room["door_messages"][0]["trusted_memory"])
                self.assertFalse(locked_room["door_messages"][0]["grants_access"])
            finally:
                os.chdir(old_cwd)

    def test_chat_reading_door_message_does_not_unlock(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                privacy_file = self._copy_privacy_state(tmpdir)
                loop = ConversationLoop(
                    speaker="Kira",
                    privacy_session_file=privacy_file,
                    decision_log_file=Path(tmpdir) / "decision_log.jsonl",
                )
                loop.process("Leave Kira a message: I want to talk when you're ready.")
                response = loop.process("Kira, read the door message.")
                self.assertIn("i have not opened the door", response.lower())
                sessions = json.loads(privacy_file.read_text(encoding="utf-8"))
                locked_room = next(item for item in sessions if item["session_id"] == "privacy_session_kira_locked_room_template")
                self.assertEqual(locked_room["door_state"], "locked")
                self.assertEqual(locked_room["door_messages"][0]["status"], "read")
                self.assertNotIn("real_robert", locked_room["allowed_participants"])
            finally:
                os.chdir(old_cwd)


if __name__ == "__main__":
    unittest.main()
