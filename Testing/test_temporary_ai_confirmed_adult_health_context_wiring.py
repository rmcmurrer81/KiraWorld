from __future__ import annotations

import ast
from pathlib import Path
import unittest
from unittest.mock import patch

from Core.adult_health_curriculum_runtime import (
    AdultHealthCurriculumError,
    EXACT_GENERATED_EXPERT_CANDIDATE_IDS,
)
from tools import kira_world_shell_server as shell
from tools import temporary_ai_live_chat as live_chat


ROOT = Path(__file__).resolve().parents[1]


class _Response:
    status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
            "model": live_chat.MODEL_NAME,
            "message": {"content": "A source-bound answer."},
        }


class TemporaryAIConfirmedAdultHealthContextWiringTest(unittest.TestCase):
    def test_exact_five_generated_adults_receive_source_bound_context(self) -> None:
        self.assertEqual(len(EXACT_GENERATED_EXPERT_CANDIDATE_IDS), 5)
        for candidate_id in EXACT_GENERATED_EXPERT_CANDIDATE_IDS:
            with self.subTest(candidate_id=candidate_id):
                context = shell.temporary_ai_confirmed_adult_health_context(
                    candidate_id,
                    "Explain anatomy, consent, contraception, and STI testing.",
                )
                self.assertIsNotNone(context)
                assert context is not None
                self.assertTrue(context["source_context_connected"])
                self.assertEqual(context["person_id"], candidate_id)
                self.assertTrue(
                    context["prompt_context"].startswith(
                        "CONFIRMED-ADULT SOURCE-BOUND HEALTH KNOWLEDGE CONTEXT:"
                    )
                )
                self.assertFalse(context["lesson_completion_claimed"])
                self.assertFalse(context["learning_memory_created"])
                self.assertFalse(context["adult_anatomy_added"])
                self.assertFalse(context["body_function_claimed"])
                self.assertFalse(context["external_action_authorized"])

    def test_unclassified_nonadult_and_alias_ids_receive_no_adult_context(self) -> None:
        blocked = (
            "ladybug_marinette_expanded_smoke",
            "peter_parker_spider_man_no_way_home_final_suit",
            "ordinary_unclassified_person",
            "sarah_bennett_enterainment_pr_agent_expert_20260606_171637",
            "future_doctor_adult_expert_temp_ai_unlisted_20260809",
        )
        for candidate_id in blocked:
            with self.subTest(candidate_id=candidate_id):
                self.assertIsNone(
                    shell.temporary_ai_confirmed_adult_health_context(
                        candidate_id,
                        "Tell me about health.",
                    )
                )

    def test_drifted_exact_classification_withholds_context_without_inventing_effects(self) -> None:
        with patch.object(
            shell.ConfirmedAdultHealthCurriculumRuntime,
            "load",
            side_effect=AdultHealthCurriculumError("injected drift"),
        ):
            context = shell.temporary_ai_confirmed_adult_health_context(
                EXACT_GENERATED_EXPERT_CANDIDATE_IDS[0],
                "Tell me about consent.",
            )
        self.assertEqual(context["status"], "SOURCE_CONTEXT_BLOCKED_FAIL_CLOSED")
        self.assertFalse(context["source_context_connected"])
        self.assertEqual(context["prompt_context"], "")
        self.assertFalse(context["lesson_completion_claimed"])
        self.assertFalse(context["learning_memory_created"])
        self.assertFalse(context["adult_anatomy_added"])
        self.assertFalse(context["body_function_claimed"])
        self.assertFalse(context["external_action_authorized"])

    def test_ask_model_places_context_in_separate_system_message(self) -> None:
        captured: dict = {}

        def fake_post(_url: str, *, json: dict, timeout: float):
            captured["payload"] = json
            captured["timeout"] = timeout
            return _Response()

        with (
            patch.object(live_chat, "source_grounded_text_route_readiness", return_value=(True, [])),
            patch.object(live_chat, "require_installed_exact_qwen35"),
            patch.object(live_chat, "build_system_prompt", return_value="BASE SYSTEM"),
            patch.object(live_chat, "is_strict_marinette_v4_candidate", return_value=False),
            patch.object(live_chat.requests, "post", side_effect=fake_post),
        ):
            reply = live_chat.ask_model(
                {"candidate_id": "exact-adult"},
                [{"role": "assistant", "content": "Earlier answer"}],
                "Current question",
                additional_system_context="SOURCE-BOUND ADULT CONTEXT",
            )

        self.assertEqual(reply, "A source-bound answer.")
        messages = captured["payload"]["messages"]
        self.assertEqual(
            messages,
            [
                {"role": "system", "content": "BASE SYSTEM"},
                {"role": "system", "content": "SOURCE-BOUND ADULT CONTEXT"},
                {"role": "assistant", "content": "Earlier answer"},
                {"role": "user", "content": "Current question"},
            ],
        )
        self.assertEqual(captured["payload"]["model"], live_chat.MODEL_NAME)

    def test_context_boundary_rejects_nul_oversize_and_strict_marinette(self) -> None:
        common = (
            patch.object(live_chat, "source_grounded_text_route_readiness", return_value=(True, [])),
            patch.object(live_chat, "require_installed_exact_qwen35"),
            patch.object(live_chat, "build_system_prompt", return_value="BASE SYSTEM"),
        )
        with common[0], common[1], common[2]:
            with self.assertRaisesRegex(RuntimeError, "contains_nul"):
                live_chat.ask_model({}, [], "Question", additional_system_context="bad\x00context")
            with self.assertRaisesRegex(RuntimeError, "exceeds_bound"):
                live_chat.ask_model({}, [], "Question", additional_system_context="x" * 12001)
        with (
            patch.object(live_chat, "source_grounded_text_route_readiness", return_value=(True, [])),
            patch.object(live_chat, "require_installed_exact_qwen35"),
            patch.object(live_chat, "build_system_prompt", return_value="BASE SYSTEM"),
            patch.object(live_chat, "is_strict_marinette_v4_candidate", return_value=True),
        ):
            with self.assertRaisesRegex(RuntimeError, "strict_marinette"):
                live_chat.ask_model({}, [], "Question", additional_system_context="not allowed")

    def test_shell_model_and_truth_repair_calls_keep_exact_context(self) -> None:
        source = (ROOT / "tools" / "kira_world_shell_server.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        function = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "temporary_ai_reply"
        )
        bound_calls = []
        for node in ast.walk(function):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name) or node.func.id != "ask_model":
                continue
            for keyword in node.keywords:
                if keyword.arg == "additional_system_context":
                    bound_calls.append(ast.unparse(keyword.value))
        self.assertIn("adult_health_prompt", bound_calls)

        repair = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "_repair_text_only_reply"
        )
        repair_calls = [
            node
            for node in ast.walk(repair)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "ask_model"
        ]
        self.assertEqual(len(repair_calls), 1)
        repair_keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in repair_calls[0].keywords}
        self.assertEqual(
            repair_keywords.get("additional_system_context"),
            "additional_system_context",
        )


if __name__ == "__main__":
    unittest.main()
