import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_ROOT = PROJECT_ROOT / "Core"
sys.path.insert(0, str(CORE_ROOT))

from daily_life_manager import DailyLifeManager, validate_daily_life_state  # noqa: E402


class DailyLifeManagerTests(unittest.TestCase):
    def test_default_states_validate(self) -> None:
        with TemporaryDirectory() as tmpdir:
            manager = DailyLifeManager(state_dir=Path(tmpdir) / "states", log_dir=Path(tmpdir) / "logs")

            states = manager.list_states()

            self.assertEqual(len(states), 2)
            for state in states:
                self.assertEqual(validate_daily_life_state(state), [])

    def test_set_locked_private_state_changes_phone_availability(self) -> None:
        with TemporaryDirectory() as tmpdir:
            manager = DailyLifeManager(state_dir=Path(tmpdir) / "states", log_dir=Path(tmpdir) / "logs")
            manager.set_state(
                "kira",
                cycle_state="private",
                mood="jealous",
                intensity=0.8,
                activity_type="private_time",
                public_summary="Kira is taking private time.",
                privacy_level="locked_private",
                robert_visibility="status_only",
                interruptibility="low",
            )

            availability = manager.phone_availability("kira")

            self.assertEqual(availability["recommendation"], "delay_or_ignore")
            self.assertEqual(availability["privacy_level"], "locked_private")

    def test_away_step_keeps_kira_and_lisa_separate(self) -> None:
        with TemporaryDirectory() as tmpdir:
            manager = DailyLifeManager(state_dir=Path(tmpdir) / "states", log_dir=Path(tmpdir) / "logs")

            kira = manager.advance_away_step("kira")
            lisa = manager.advance_away_step("lisa")

            self.assertEqual(kira["entity_id"], "kira")
            self.assertEqual(lisa["entity_id"], "lisa")
            self.assertNotEqual(kira["current_activity"]["public_summary"], lisa["current_activity"]["public_summary"])

    def test_write_log_uses_current_state_without_private_dump(self) -> None:
        with TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "logs"
            manager = DailyLifeManager(state_dir=Path(tmpdir) / "states", log_dir=log_dir)
            manager.set_state(
                "lisa",
                cycle_state="private",
                mood="angry",
                intensity=0.7,
                activity_type="private_time",
                public_summary="Lisa is upset and taking private time.",
                private_summary="Sealed private anger details.",
                privacy_level="locked_private",
                robert_visibility="status_only",
                interruptibility="low",
            )

            log = manager.write_log("lisa", notes="test")

            self.assertEqual(log["actor"], "lisa")
            self.assertEqual(log["share_permissions"]["robert"], "status_only")
            self.assertEqual(len(list(log_dir.glob("*.json"))), 1)

    def test_choose_activity_allows_book_abandonment_when_bored(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            session_dir = root / "reading" / "sessions"
            session_dir.mkdir(parents=True)
            session_dir.joinpath("slow_reading_kira_example.json").write_text(
                """{
  "reader": "kira",
  "status": "active",
  "material": {
    "title": "example_book",
    "source_path": "Data/library/novels/example_book.pdf"
  }
}
""",
                encoding="utf-8",
            )
            manager = DailyLifeManager(
                state_dir=root / "states",
                log_dir=root / "logs",
                reading_session_dir=session_dir,
                reading_recommendation_dir=root / "reading",
            )
            manager.set_state(
                "kira",
                cycle_state="quiet",
                mood="bored",
                intensity=0.5,
                activity_type="reading",
                public_summary="Kira is trying a book.",
                source_path="Data/library/novels/example_book.pdf",
            )

            choice = manager.choose_activity("kira")

            self.assertEqual(choice["action"], "may_continue_pause_or_abandon_book")
            self.assertIn("abandon_book", choice["allowed_reader_choices"])
            self.assertTrue(choice["book_may_be_abandoned_if_not_liked"])

    def test_choose_activity_can_use_reading_recommendation(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            recommendation_dir = root / "reading"
            recommendation_dir.mkdir(parents=True)
            recommendation_dir.joinpath("reading_recommendations_lisa.json").write_text(
                """{
  "recommendations": [
    {
      "title": "the_great_gatsby_f_scott_fitzgerald",
      "source_path": "Data/library/novels/the_great_gatsby_f_scott_fitzgerald.pdf"
    }
  ]
}
""",
                encoding="utf-8",
            )
            manager = DailyLifeManager(
                state_dir=root / "states",
                log_dir=root / "logs",
                reading_session_dir=root / "sessions",
                reading_recommendation_dir=recommendation_dir,
            )

            choice = manager.choose_activity("lisa")

            self.assertEqual(choice["activity_type"], "reading")
            self.assertEqual(choice["source_path"], "Data/library/novels/the_great_gatsby_f_scott_fitzgerald.pdf")
            self.assertTrue(choice["advisory_only"])

    def test_choose_and_apply_activity_writes_idle_log(self) -> None:
        with TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "logs"
            manager = DailyLifeManager(state_dir=Path(tmpdir) / "states", log_dir=log_dir)

            result = manager.choose_and_apply_activity("kira")

            self.assertIn("idle_log", result)
            self.assertEqual(len(list(log_dir.glob("*.json"))), 1)
            self.assertIn("not a promoted memory", result["idle_log"]["notes"])

    def test_self_chosen_reading_continues_for_bounded_steps_with_exit_choices(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manager = DailyLifeManager(
                state_dir=root / "states",
                log_dir=root / "logs",
                reading_session_dir=root / "sessions",
                reading_recommendation_dir=root / "reading",
            )
            manager.set_state(
                "kira",
                cycle_state="quiet",
                mood="curious",
                intensity=0.35,
                activity_type="reading",
                source_path="Data/library/example.pdf",
                public_summary="Kira is reading quietly on the couch.",
                continuation_steps_remaining=3,
            )

            first = manager.choose_and_apply_activity("kira")
            second = manager.choose_and_apply_activity("kira")
            third = manager.choose_and_apply_activity("kira")

            self.assertEqual(first["choice"]["action"], "continue_self_chosen_quiet_activity")
            self.assertIn("pause", first["choice"]["allowed_reader_choices"])
            self.assertIn("switch", first["choice"]["allowed_reader_choices"])
            self.assertEqual(first["state"]["current_activity"]["continuation_steps_remaining"], 2)
            self.assertEqual(second["state"]["current_activity"]["continuation_steps_remaining"], 1)
            self.assertEqual(third["state"]["current_activity"]["continuation_steps_remaining"], 0)
            self.assertTrue(third["state"]["current_activity"]["decision_checkpoint_due"])

            after_window = manager.choose_activity("kira")
            self.assertNotEqual(after_window["action"], "continue_self_chosen_quiet_activity")


if __name__ == "__main__":
    unittest.main()
