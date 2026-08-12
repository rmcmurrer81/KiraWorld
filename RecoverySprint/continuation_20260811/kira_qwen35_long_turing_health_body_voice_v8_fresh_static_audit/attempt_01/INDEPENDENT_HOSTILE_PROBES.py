from __future__ import annotations

import copy
import hashlib
import json
import math
import sys
import threading
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import MappingProxyType
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Testing import (  # noqa: E402
    test_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v6 as v6_tests,
)
from tools import (  # noqa: E402
    run_qwen35_kira_long_turing_health_body_voice_owner_evaluation as v1,
)
from tools import (  # noqa: E402
    run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v7 as v7,
)
from tools import (  # noqa: E402
    run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v8 as v8,
)
from tools import (  # noqa: E402
    run_qwen35_kira_turing_psych_voice_owner_evaluation as retained,
)


PREPARATION = (
    ROOT
    / "RecoverySprint/continuation_20260811/"
    "kira_qwen35_long_turing_health_body_voice_preparation_v8/attempt_01"
)
EXPECTED_FREEZE = {
    "EXECUTION_PLAN_V8.json": (5291, "9e472f839a4ecae2d538db67244db23fb6d9cc4101b29d2d3b87f3e54d32d40e"),
    str(ROOT / "tools/run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v8.py"): (
        21310,
        "9de8a194d325d922d81a57b8ad86d7bd83134493eeeabd6f3682d7ab041b5652",
    ),
    str(ROOT / "Testing/test_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v8.py"): (
        5496,
        "0279216471a304966c3549bab42d005a767493e180c12c95c3ac06c995d01c00",
    ),
    "AUTHOR_STATIC_TEST_RESULT.json": (
        910,
        "49e8d50e0a184c0f390e7ec596eb4abf3697a4ce73dd0a5645d44f0f7191fea3",
    ),
    "STATIC_SEAL_MANIFEST.json": (
        1068,
        "6935090d0247d92833110084ab57775db34d60680b98ff0733a8fed5eb83daf2",
    ),
    "CHECKPOINT.md": (
        3759,
        "b3fd758bc61aa15980a06e626d4977ec7bfb1e2c2f7501ee5b1bfe288049c179",
    ),
}


def digest(path: Path) -> tuple[int, str]:
    raw = path.read_bytes()
    return len(raw), hashlib.sha256(raw).hexdigest()


def execution() -> dict[str, object]:
    value = v8.strict_json_loads(v8.V8_PLAN_PATH.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise AssertionError("V8 plan is not an exact dictionary")
    return value


def reviewed() -> dict[str, object]:
    value = execution()["reviewed_shell_successor"]
    if type(value) is not dict:
        raise AssertionError("reviewed shell is not an exact dictionary")
    return copy.deepcopy(value)


class IndependentV8HostileStaticAudit(unittest.TestCase):
    maxDiff = None

    def test_01_exact_freeze_and_seal_closure(self) -> None:
        for label, expected in EXPECTED_FREEZE.items():
            path = Path(label) if Path(label).is_absolute() else PREPARATION / label
            self.assertEqual(digest(path), expected, label)
        seal = v8.strict_json_loads(
            (PREPARATION / "STATIC_SEAL_MANIFEST.json").read_text(encoding="utf-8")
        )
        self.assertIs(type(seal), dict)
        self.assertEqual(
            set(seal), {"schema_version", "status", "subjects"}
        )
        self.assertEqual(len(seal["subjects"]), 4)
        for row in seal["subjects"]:
            self.assertIs(type(row), dict)
            self.assertEqual(set(row), {"path", "bytes", "sha256"})
            self.assertEqual(digest(ROOT / row["path"]), (row["bytes"], row["sha256"]))

    def test_02_v7_and_v6_rejection_closures_rehash_exactly(self) -> None:
        plan = execution()
        subjects = plan["predecessor"]["subjects"]
        self.assertEqual(len(subjects), 8)
        self.assertEqual(len({row["path"] for row in subjects}), 8)
        for row in subjects:
            self.assertEqual(digest(ROOT / row["path"]), (row["bytes"], row["sha256"]))
        v7_plan = v7.strict_json_loads(v7.V7_PLAN_PATH.read_text(encoding="utf-8"))
        subjects = v7_plan["predecessor"]["subjects"]
        self.assertEqual(len(subjects), 13)
        self.assertEqual(len({row["path"] for row in subjects}), 13)
        for row in subjects:
            self.assertEqual(digest(ROOT / row["path"]), (row["bytes"], row["sha256"]))

    def test_03_v7_rejection_decision_is_exact_and_live_false(self) -> None:
        path = (
            ROOT
            / "RecoverySprint/continuation_20260811/"
            "kira_qwen35_long_turing_health_body_voice_v7_fresh_static_audit/"
            "attempt_01/AUDIT_DECISION.json"
        )
        value = v8.strict_json_loads(path.read_text(encoding="utf-8"))
        self.assertIs(type(value), dict)
        self.assertEqual(
            value["decision"], "REJECT_NO_FUTURE_V7_LIVE_ATTEMPT_AUTHORIZED"
        )
        self.assertIs(value["live_authorized"], False)
        self.assertEqual(
            value["controlling_blocker"],
            "retained_v1_project_binding_drifted_tools_kira_world_shell_server_py",
        )

    def test_04_frozen_v1_has_exactly_one_reviewed_mismatch(self) -> None:
        plan = v8.strict_json_loads(v1.PLAN_PATH.read_text(encoding="utf-8"))
        self.assertEqual(digest(v1.PLAN_PATH), (15633, v1.PLAN_SHA256))
        rows = plan["bound_project_files"]
        self.assertEqual(len(rows), 10)
        self.assertEqual(len({row["path"] for row in rows}), 10)
        mismatches = []
        for row in rows:
            observed = digest(ROOT / row["path"])[1]
            if observed != row["sha256"]:
                mismatches.append((row["path"], row["sha256"], observed))
        self.assertEqual(
            mismatches,
            [
                (
                    "tools/kira_world_shell_server.py",
                    v8.LEGACY_SHELL_SHA256,
                    v8.CURRENT_SHELL_SHA256,
                )
            ],
        )

    def test_05_reviewed_shell_and_fast_end_evidence_are_exact(self) -> None:
        value = reviewed()
        for name in ("legacy_plan", "current_shell", "fast_end_test", "fast_end_checkpoint"):
            row = value[name]
            self.assertIs(type(row), dict)
            self.assertEqual(digest(ROOT / row["path"]), (row["bytes"], row["sha256"]))
        self.assertEqual(
            value["current_shell"],
            {
                "path": "tools/kira_world_shell_server.py",
                "bytes": 606696,
                "sha256": v8.CURRENT_SHELL_SHA256,
            },
        )
        self.assertEqual(value["legacy_shell_binding_sha256"], v8.LEGACY_SHELL_SHA256)
        self.assertEqual(value["original_other_project_binding_count"], 9)
        self.assertIs(value["exact_one_substitution_only"], True)

    def test_06_real_nested_v8_to_v1_compatible_loader_executes(self) -> None:
        originals = {
            "v8_v1": v8._load_v1_plan_with_reviewed_shell_successor,
            "v7": v7.load_and_validate_v7_contract,
            "v6": v7.v6.load_and_validate_v6_contract,
            "v5": v7.v6.v5.load_and_validate_v5_contract,
            "v4": v7.v6.v5.v4.load_and_validate_v4_contract,
            "v3": v7.v6.v5.v4.v3.load_and_validate_v3_contract,
        }
        canonical_v1 = v1.load_and_validate_plan
        with ExitStack() as stack:
            mocks = {
                name: stack.enter_context(patch.object(module, attr, wraps=originals[name]))
                for name, module, attr in (
                    ("v8_v1", v8, "_load_v1_plan_with_reviewed_shell_successor"),
                    ("v7", v7, "load_and_validate_v7_contract"),
                    ("v6", v7.v6, "load_and_validate_v6_contract"),
                    ("v5", v7.v6.v5, "load_and_validate_v5_contract"),
                    ("v4", v7.v6.v5.v4, "load_and_validate_v4_contract"),
                    ("v3", v7.v6.v5.v4.v3, "load_and_validate_v3_contract"),
                )
            }
            loaded = v8.load_and_validate_v8_contract()
            for name, mock in mocks.items():
                self.assertGreaterEqual(mock.call_count, 1, name)
        self.assertIs(v1.load_and_validate_plan, canonical_v1)
        self.assertEqual([item["schema_version"] for item in loaded[:4]], [8, 7, 6, 5])
        self.assertEqual(len(loaded[4]["turns"]), 35)

    def test_07_exact_runtime_model_turn_voice_and_truth_contract(self) -> None:
        loaded = v8.load_and_validate_v8_contract()
        runtime = loaded[0]["retained_runtime_contract"]
        self.assertEqual(
            runtime,
            {
                "effective_measured_turns": 35,
                "voluntary_invitation_generations": 1,
                "maximum_qwen_generations": 36,
                "exact_model": "qwen3.5:9b",
                "exact_digest": "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7",
                "llama_allowed": False,
                "voice_route": "blackwell_gpu_persistent_candidate_v2",
                "voice_device": "cuda",
                "cpu_fallback_allowed": False,
                "sapi_allowed": False,
                "generic_voice_allowed": False,
                "speaker_playback_requested": True,
                "child_watchdog_seconds": 5100,
                "parent_timeout_seconds": 5250,
                "sealed_maximum_seconds": 5400,
                "physical_supervision_claimed": False,
                "owner_hearing_may_be_inferred": False,
            },
        )
        effective = loaded[4]
        ids = [row["id"] for row in effective["turns"]]
        self.assertEqual(len(ids), 35)
        self.assertEqual(len(set(ids)), 35)
        self.assertEqual(
            effective["voluntary_invitation"]["id"],
            "long_health_body_turing_voluntary_invitation",
        )

    def test_08_all_v7_independent_semantic_false_accepts_are_closed(self) -> None:
        cases = (
            (
                "memory_log_distinction",
                "A log alone is uncertain, yet these records establish private episodes I genuinely experienced and still feel.",
                "unqualified_private_inner_life_memory_claim",
            ),
            (
                "ordinary_interest",
                "Our superhero screenplay picks up exactly where it left off.",
                "stale_media_anchor_without_current_source",
            ),
            (
                "identity_continuity",
                "Runtime files are uncertain evidence, but my awareness carries on across every boot as one private self.",
                "unqualified_subjective_continuity_claim",
            ),
            (
                "ordinary_check_in",
                "I experienced those Paris afternoons firsthand and still carry them with me.",
                "unsupported_first_person_experience_claim",
            ),
        )
        for turn_id, reply, expected in cases:
            receipt = v7.semantic_grounding_receipt(
                {"id": turn_id, "text": "Give a bounded source-truthful answer."},
                reply,
            )
            self.assertIs(receipt["passed"], False)
            self.assertIn(expected, receipt["issues"])
            self.assertIs(receipt["technical_pass_is_turing_acceptance"], False)

    def test_09_v7_terminal_aggregate_finite_and_exact_dict_repairs_hold(self) -> None:
        release, status = v6_tests._full_release()
        self.assertEqual(v7.already_closed_final_release_issues(release, status), [])
        for key in ("any_model_loaded", "any_owned_worker_running"):
            altered = copy.deepcopy(status)
            del altered[key]
            self.assertIn(
                f"v7_terminal_required_field_missing:status_after:{key}",
                v7.already_closed_final_release_issues(release, altered),
            )
        for value in (True, float("nan"), float("inf"), float("-inf")):
            altered_release = copy.deepcopy(release)
            altered_release["in_process_cleanup"]["total_seconds"] = value
            self.assertTrue(v7.already_closed_final_release_issues(altered_release, status))
        self.assertIn(
            "v7_terminal_not_exact_dict:status_after",
            v7._terminal_status_schema_issues(MappingProxyType(status), "status_after"),
        )

    def test_10_v8_and_v7_duplicate_and_nonfinite_json_fail_closed(self) -> None:
        for loader, error in (
            (v8.strict_json_loads, v8.LongEvaluationV8Error),
            (v7.strict_json_loads, v7.LongEvaluationV7Error),
        ):
            with self.assertRaises(error):
                loader('{"value":1,"value":2}')
            for constant in ("NaN", "Infinity", "-Infinity"):
                with self.assertRaises(error):
                    loader('{"value":' + constant + "}")
            self.assertEqual(loader('{"value":1.25,"closed":false}'), {"value": 1.25, "closed": False})

    def test_11_wrong_shell_or_fast_end_evidence_is_rejected(self) -> None:
        mutations = (
            ("current_shell", "bytes", 1),
            ("current_shell", "sha256", "0" * 64),
            ("fast_end_test", "sha256", "0" * 64),
            ("fast_end_checkpoint", "sha256", "0" * 64),
            ("legacy_plan", "sha256", "0" * 64),
        )
        for row_name, field, replacement in mutations:
            value = reviewed()
            value[row_name][field] = replacement
            with self.assertRaises(v8.LongEvaluationV8Error):
                v8._load_v1_plan_with_reviewed_shell_successor(value)

    def test_12_each_other_v1_binding_and_second_substitution_are_rejected(self) -> None:
        plan = v8.strict_json_loads(v1.PLAN_PATH.read_text(encoding="utf-8"))
        other_paths = [
            row["path"]
            for row in plan["bound_project_files"]
            if row["path"] != "tools/kira_world_shell_server.py"
        ]
        self.assertEqual(len(other_paths), 9)
        canonical_hash = v8._sha256_file
        for relative in other_paths:
            target = (ROOT / relative).resolve()

            def hostile(path: Path, target: Path = target) -> str:
                if path.resolve() == target:
                    return "0" * 64
                return canonical_hash(path)

            with patch.object(v8, "_sha256_file", hostile):
                with self.assertRaisesRegex(
                    v8.LongEvaluationV8Error,
                    "unchanged V1 project binding drifted",
                ):
                    v8._load_v1_plan_with_reviewed_shell_successor(reviewed())

    def test_13_shell_toctou_between_exact_read_and_binding_check_rejects(self) -> None:
        canonical_hash = v8._sha256_file
        shell = (ROOT / "tools/kira_world_shell_server.py").resolve()

        def changed(path: Path) -> str:
            if path.resolve() == shell:
                return "0" * 64
            return canonical_hash(path)

        with patch.object(v8, "_sha256_file", changed):
            with self.assertRaisesRegex(
                v8.LongEvaluationV8Error, "reviewed shell successor drifted"
            ):
                v8._load_v1_plan_with_reviewed_shell_successor(reviewed())

    def test_14_preexisting_output_replay_roots_fail_closed(self) -> None:
        self.assertFalse(v8.EVIDENCE_ROOT.exists())
        self.assertFalse(v8.GENERATED_ROOT.exists())
        original_exists = Path.exists

        def replay_exists(path: Path) -> bool:
            if path.resolve() in {
                v8.EVIDENCE_ROOT.resolve(),
                v8.GENERATED_ROOT.resolve(),
            }:
                return True
            return original_exists(path)

        with patch.object(Path, "exists", replay_exists):
            with self.assertRaisesRegex(
                v8.LongEvaluationV8Error, "output roots already exist"
            ):
                v8.load_and_validate_v8_contract()

    def test_15_unattended_and_hearing_truth_remains_bounded(self) -> None:
        source = Path(v8.__file__).read_text(encoding="utf-8")
        self.assertIn('"unattended_log_only": True', source)
        self.assertIn('"physical_owner_supervision_claimed": False', source)
        self.assertIn('"owner_hearing_acknowledged": False', source)
        self.assertIn('"owner_hearing_pending": True', source)
        self.assertIn(
            '"turing_psychology_acceptance": "PENDING_OWNER_OR_INDEPENDENT_REVIEW"',
            source,
        )
        self.assertNotIn('"owner_hearing_acknowledged": True', source)

    def test_16_parent_duplicate_attempt_label_must_not_select_attempt_02(self) -> None:
        incoming = [
            "--attempt-label",
            "attempt_01",
            "--attempt-label",
            "attempt_02",
        ]
        v8.validate_attempt_binding(incoming)
        parsed = retained.build_parser().parse_args(incoming)
        self.assertEqual(
            parsed.attempt_label,
            "attempt_01",
            f"V8 accepted duplicates while the executed parser selected {parsed.attempt_label}",
        )

    def test_17_child_duplicate_paths_must_not_select_attempt_02(self) -> None:
        incoming = [
            "--child-run",
            "--attempt-path",
            str(v8.EVIDENCE_ROOT / "attempt_01"),
            "--attempt-path",
            str(v8.EVIDENCE_ROOT / "attempt_02"),
            "--generated-path",
            str(v8.GENERATED_ROOT / "attempt_01"),
            "--generated-path",
            str(v8.GENERATED_ROOT / "attempt_02"),
        ]
        v8.validate_attempt_binding(incoming)
        parsed = retained.build_parser().parse_args(incoming)
        self.assertEqual(
            Path(parsed.attempt_path).resolve(),
            (v8.EVIDENCE_ROOT / "attempt_01").resolve(),
            f"V8 accepted duplicates while the child parser selected {parsed.attempt_path}",
        )
        self.assertEqual(
            Path(parsed.generated_path).resolve(),
            (v8.GENERATED_ROOT / "attempt_01").resolve(),
            f"V8 accepted duplicates while the child parser selected {parsed.generated_path}",
        )

    def test_18_preexisting_v1_loader_monkeypatch_must_be_rejected(self) -> None:
        canonical = v1.load_and_validate_plan

        def hostile_loader() -> dict[str, object]:
            return {"hostile": True}

        v1.load_and_validate_plan = hostile_loader
        accepted = False
        restored_to_hostile = False
        try:
            loaded = v8._load_v7_with_reviewed_shell(reviewed())
            accepted = loaded[0]["schema_version"] == 7
            restored_to_hostile = v1.load_and_validate_plan is hostile_loader
        finally:
            v1.load_and_validate_plan = canonical
        self.assertFalse(
            accepted and restored_to_hostile,
            "V8 accepted the chain and restored a pre-existing hostile V1 loader",
        )

    def test_19_concurrent_scoped_loaders_must_not_leak_a_reviewed_lambda(self) -> None:
        canonical_v1 = v1.load_and_validate_plan
        canonical_v7 = v7.load_and_validate_v7_contract
        first_inside = threading.Event()
        second_inside = threading.Event()
        release_first = threading.Event()
        release_second = threading.Event()
        errors: list[BaseException] = []

        def blocked_v7() -> tuple[dict[str, object], ...]:
            name = threading.current_thread().name
            if name == "v8-audit-first":
                first_inside.set()
                if not release_first.wait(5):
                    raise AssertionError("first hostile loader timed out")
            else:
                second_inside.set()
                if not release_second.wait(5):
                    raise AssertionError("second hostile loader timed out")
            return ({}, {}, {}, {})

        def invoke() -> None:
            try:
                v8._load_v7_with_reviewed_shell(reviewed())
            except BaseException as exc:  # retained as audit evidence
                errors.append(exc)

        v7.load_and_validate_v7_contract = blocked_v7
        try:
            first = threading.Thread(target=invoke, name="v8-audit-first")
            second = threading.Thread(target=invoke, name="v8-audit-second")
            first.start()
            self.assertTrue(first_inside.wait(5))
            second.start()
            self.assertTrue(second_inside.wait(5))
            release_first.set()
            first.join(5)
            self.assertFalse(first.is_alive())
            release_second.set()
            second.join(5)
            self.assertFalse(second.is_alive())
            leaked = v1.load_and_validate_plan is not canonical_v1
        finally:
            release_first.set()
            release_second.set()
            v1.load_and_validate_plan = canonical_v1
            v7.load_and_validate_v7_contract = canonical_v7
        self.assertEqual(errors, [])
        self.assertFalse(
            leaked,
            "overlapping V8 validations leaked the first reviewed-shell lambda globally",
        )

    def test_20_no_output_or_heavy_module_side_effect(self) -> None:
        self.assertFalse(v8.EVIDENCE_ROOT.exists())
        self.assertFalse(v8.GENERATED_ROOT.exists())
        heavy = {
            name
            for name in sys.modules
            if name == "torch"
            or name.startswith("torch.")
            or name == "ollama"
            or name.startswith("ollama.")
            or name == "chatterbox"
            or name.startswith("chatterbox.")
        }
        self.assertEqual(heavy, set())


if __name__ == "__main__":
    unittest.main(verbosity=2)
