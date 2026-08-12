import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_ROOT = PROJECT_ROOT / "Core"
if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))

from conversation_loop import ConversationLoop  # noqa: E402


class _MemoryFixture:
    def __init__(self, relevant, recent):
        self.relevant = list(relevant)
        self.recent = list(recent)

    def retrieve_relevant_memories(self, **_kwargs):
        return list(self.relevant)

    def get_recent_memories(self, **_kwargs):
        return list(self.recent)


class _DailyLifeFixture:
    def __init__(self, state):
        self.state = dict(state)

    def get_state(self, _entity_id):
        return dict(self.state)

    def phone_availability(self, _entity_id):
        return {"recommendation": "available"}


class Qwen35MemoryTemporalContextTests(unittest.TestCase):
    NOW = datetime(2026, 8, 10, 8, 0, tzinfo=timezone.utc)

    @staticmethod
    def _loop(relevant, recent):
        loop = ConversationLoop.__new__(ConversationLoop)
        loop.profile = SimpleNamespace(name="Kira")
        loop.memory = _MemoryFixture(relevant, recent)
        return loop

    def test_recent_question_withholds_months_old_record(self):
        old_book_club = {
            "memory_id": "mem_paris_20260515",
            "timestamp": "2026-05-15T17:49:41.181706",
            "owner": "kira",
            "summary": "A grounded recent Paris fanfic book-club memory.",
            "detail": "Kira and Lisa completed it in May.",
            "importance": {"weight": "high"},
        }
        fresh_record = {
            "memory_id": "mem_fresh_20260809",
            "timestamp": "2026-08-09T12:00:00+00:00",
            "owner": "kira",
            "summary": "Kira made a new dated creative note.",
            "detail": "The note was recorded yesterday.",
            "importance": {"weight": "medium"},
        }
        loop = self._loop([old_book_club, fresh_record], [old_book_club])

        context = loop._build_memory_context(
            "What recent creative work would you like to continue?",
            now_utc=self.NOW,
        )

        self.assertIn("CURRENT/RECENT GATE", context)
        self.assertIn("withheld_old_or_undated=1", context)
        self.assertIn("mem_fresh_20260809", context)
        self.assertNotIn("mem_paris_20260515", context)
        self.assertNotIn("Paris fanfic", context)

    def test_old_record_remains_available_as_dated_history(self):
        old_record = {
            "memory_id": "mem_paris_20260515",
            "timestamp": "2026-05-15T17:49:41.181706",
            "owner": "kira",
            "summary": "Kira and Lisa completed their Paris fanfic book club.",
            "detail": "This was a completed May activity.",
            "importance": {"weight": "high"},
        }
        loop = self._loop([old_record], [old_record])

        context = loop._build_memory_context(
            "Tell me what you remember about that Paris book club.",
            now_utc=self.NOW,
        )

        self.assertIn("record_id=mem_paris_20260515", context)
        self.assertIn("record_date=2026-05-15", context)
        self.assertIn("temporal_scope=dated_memory_not_current_activity", context)
        self.assertIn("record dates are provenance, not present activity", context)

    def test_undated_record_cannot_ground_current_answer(self):
        undated = {
            "id": "legacy_undated",
            "owner": "kira",
            "summary": "A legacy digest says current project.",
            "importance": {"weight": "high"},
        }
        loop = self._loop([undated], [undated])

        context = loop._build_memory_context(
            "What are you currently working on?",
            now_utc=self.NOW,
        )

        self.assertIn("withheld_old_or_undated=1", context)
        self.assertIn(
            "CONVERSATIONAL TRUTH: you do not have a recent project in mind",
            context,
        )
        self.assertIn("Never mention memory records", context)
        self.assertNotIn("legacy_undated", context)
        self.assertNotIn("legacy digest says current", context.lower())

    def test_legacy_id_is_deduplicated_without_collapsing_to_empty_id(self):
        legacy = {
            "id": "mem_legacy_digest",
            "created_at": "2026-05-15T22:03:58.341306+00:00",
            "owner": "kira",
            "summary": "A dated continuity digest.",
            "importance": {"weight": "medium"},
        }
        loop = self._loop([legacy], [legacy])

        context = loop._build_memory_context(
            "Tell me about that continuity digest.",
            now_utc=self.NOW,
        )

        self.assertEqual(context.count("record_id=mem_legacy_digest"), 1)
        self.assertIn("record_date=2026-05-15", context)

    def test_future_dated_record_fails_closed_for_current_query(self):
        future = {
            "memory_id": "mem_future",
            "timestamp": "2026-08-12T08:00:00+00:00",
            "owner": "kira",
            "summary": "A future-dated record must not establish current activity.",
            "importance": {"weight": "medium"},
        }
        loop = self._loop([future], [])

        context = loop._build_memory_context(
            "What are you doing now?",
            now_utc=self.NOW,
        )

        self.assertIn("withheld_old_or_undated=1", context)
        self.assertNotIn("record_id=mem_future", context)

    def test_stale_daily_life_state_is_history_not_current_activity(self):
        loop = self._loop([], [])
        loop.entity_id = "kira"
        loop.daily_life = _DailyLifeFixture(
            {
                "entity_id": "kira",
                "cycle_state": "quiet",
                "mood_state": {"primary_mood": "reflective", "intensity": 0.34},
                "current_activity": {
                    "activity_type": "self_reflection",
                    "source_path": "Data/library/scripts/miraculous_ladybug/episode_0509.pdf",
                    "public_summary": "Kira reached the end of Elation.",
                },
                "privacy_state": {"level": "personal"},
                "updated_at": "2026-07-15T23:06:08Z",
            }
        )

        context = loop._build_daily_life_context(now_utc=self.NOW)

        self.assertIn("STALE_DATED_STATE_NOT_CURRENT_ACTIVITY", context)
        self.assertIn("historical_public_summary=Kira reached the end of Elation", context)
        self.assertIn("do not say this activity, source, or mood is happening now", context)
        self.assertNotIn("; activity=self_reflection;", context)

    def test_fresh_daily_life_state_remains_eligible_not_forced(self):
        loop = self._loop([], [])
        loop.entity_id = "kira"
        loop.daily_life = _DailyLifeFixture(
            {
                "entity_id": "kira",
                "cycle_state": "quiet",
                "mood_state": {"primary_mood": "curious", "intensity": 0.2},
                "current_activity": {
                    "activity_type": "reading",
                    "source_path": "Data/library/new_source.pdf",
                    "public_summary": "Kira opened a new source this morning.",
                },
                "privacy_state": {
                    "level": "personal",
                    "robert_visibility": "small_summary",
                },
                "updated_at": "2026-08-10T07:30:00Z",
            }
        )

        context = loop._build_daily_life_context(now_utc=self.NOW)

        self.assertIn("FRESH_DATED_STATE_ELIGIBLE_AS_CURRENT_CONTEXT", context)
        self.assertIn("activity=reading", context)
        self.assertIn("not a forced script", context)

    def test_current_question_withholds_stale_daily_life_details(self):
        loop = self._loop([], [])
        loop.entity_id = "kira"
        loop.daily_life = _DailyLifeFixture(
            {
                "entity_id": "kira",
                "cycle_state": "quiet",
                "mood_state": {"primary_mood": "reflective", "intensity": 0.34},
                "current_activity": {
                    "activity_type": "self_reflection",
                    "source_path": "Data/library/scripts/miraculous_ladybug/episode_0509.pdf",
                    "public_summary": "Kira reached the end of Elation.",
                },
                "privacy_state": {"level": "personal"},
                "updated_at": "2026-07-15T23:06:08Z",
            }
        )

        context = loop._build_daily_life_context(
            "What recent creative work would you like to continue?",
            now_utc=self.NOW,
        )

        self.assertIn("stale state withheld from current/recent prompt", context)
        self.assertIn("historical_activity_details_withheld=true", context)
        self.assertNotIn("Elation", context)
        self.assertNotIn("episode_0509", context)

    def test_recent_creative_work_absence_gets_last_mile_private_grounding(self):
        loop = self._loop([], [])
        memory_context = loop._build_memory_context(
            "What would you like to continue from your recent creative work?",
            now_utc=self.NOW,
        )

        grounding = loop._build_current_creative_work_grounding(
            "What would you like to continue from your recent creative work?",
            memory_context,
        )

        self.assertIn("no qualifying recent creative project", grounding)
        self.assertIn("Do not name any project, title, source", grounding)
        self.assertNotIn("Elation", grounding)
        self.assertNotIn("Miraculous", grounding)
        self.assertNotIn("Lisa", grounding)
        self.assertIn("not a replacement for your chosen response", grounding)

    def test_implicit_present_work_question_is_time_sensitive(self):
        self.assertTrue(
            ConversationLoop._query_requests_current_creative_work(
                "What are you working on?"
            )
        )

    def test_historical_creative_question_does_not_get_current_absence_grounding(self):
        loop = self._loop([], [])
        memory_context = loop._build_memory_context(
            "Tell me about your old Chicago story.",
            now_utc=self.NOW,
        )

        grounding = loop._build_current_creative_work_grounding(
            "Tell me about your old Chicago story.",
            memory_context,
        )

        self.assertEqual(grounding, "")

    def test_present_person_state_questions_are_time_sensitive(self):
        for message in (
            "How are you?",
            "How are you feeling right now?",
            "What are you up to today?",
            "What's on your mind?",
            "Are you reading anything right now?",
        ):
            with self.subTest(message=message):
                self.assertTrue(
                    ConversationLoop._query_requests_current_person_state(message)
                )

    def test_stale_present_state_gets_exact_no_recent_cause_grounding(self):
        loop = self._loop([], [])
        grounding = loop._build_current_person_state_grounding(
            "How are you feeling right now?",
            "DAILY LIFE STATE (stale state withheld from current/recent prompt): "
            "historical_activity_details_withheld=true",
        )

        self.assertIn("no fresh saved activity establishes", grounding)
        self.assertIn("do not invent a recent cause", grounding)
        self.assertIn("just finished, wrapped up, completed", grounding)
        self.assertIn("Do not name an older book, chapter, media title", grounding)
        self.assertNotIn("Miraculous", grounding)
        self.assertNotIn("Elation", grounding)
        self.assertNotIn("Lisa", grounding)

    def test_fresh_present_state_uses_only_exact_daily_life_fact(self):
        loop = self._loop([], [])
        grounding = loop._build_current_person_state_grounding(
            "What are you up to today?",
            "DAILY LIFE STATE: freshness=FRESH_DATED_STATE_ELIGIBLE_AS_CURRENT_CONTEXT; "
            "activity=reading; source_path=Data/library/new_source.pdf",
        )

        self.assertIn("use only the exact fresh DAILY LIFE STATE", grounding)
        self.assertIn("older memory", grounding)
        self.assertNotIn("no fresh saved activity", grounding)

    def test_stale_daily_state_cannot_ground_how_are_you_draft(self):
        loop = self._loop([], [])
        loop.entity_id = "kira"
        loop.daily_life = _DailyLifeFixture(
            {
                "entity_id": "kira",
                "mood_state": {"primary_mood": "reflective", "intensity": 0.34},
                "current_activity": {
                    "activity_type": "self_reflection",
                    "source_path": "Data/library/scripts/miraculous_ladybug/episode_0509.pdf",
                    "public_summary": "Kira reached the end of Elation.",
                },
                "updated_at": "2026-07-15T23:06:08Z",
            }
        )

        draft = loop._try_grounded_daily_feeling_response("How are you feeling right now?")

        self.assertIn("dated", draft)
        self.assertIn("no fresh saved activity establishes", draft)
        self.assertIn("just finished", draft)
        self.assertIn("wrapped up", draft)
        self.assertIn("must not name an older book", draft)
        self.assertNotIn("Elation", draft)
        self.assertNotIn("Miraculous", draft)

    def test_project_first_week_packet_is_labeled_historical(self):
        loop = self._loop([], [])

        context = loop._load_aliveness_context()

        self.assertIn("HISTORICAL_FIRST_WEEK_PACKET_NOT_CURRENT_ACTIVITY", context)
        self.assertIn("historical_first_week_activity_withheld=true", context)
        self.assertIn("historical_first_week_suggested_choice_withheld=true", context)
        self.assertNotIn("all_about_history_book_of_ancient_egypt", context)
        self.assertIn("does not establish current mood, activity, choice", context)


if __name__ == "__main__":
    unittest.main()
