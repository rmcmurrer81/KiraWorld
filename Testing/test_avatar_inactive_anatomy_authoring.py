from __future__ import annotations

import copy
from contextlib import redirect_stderr
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from Core import avatar_anatomy_package as anatomy_preflight
from Core.avatar_inactive_anatomy_authoring import (
    ARTIFACT_NAME,
    AUTHORED_STATUS,
    InactiveAnatomyAuthoringError,
    JOB_NAME,
    MANIFEST_NAME,
    MODULE_COLLECTION_NAME,
    PRIVATE_OUTPUT_PREFIX,
    RECEIPT_NAME,
    WORKER_RESULT_NAME,
    execute_private_inactive_anatomy_authoring,
    plan_private_inactive_anatomy_authoring,
    run_blender_authoring_job,
)
from Testing.test_avatar_anatomy_package import AnatomyFixture, write_json
from tools.author_avatar_inactive_anatomy_package import main as controller_main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REAL_REQUEST = (
    "Avatar/avatar_builder/anatomy_packages/"
    "kira_internal_pelvis_source_preflight_v1_20260820/PREFLIGHT_REQUEST.json"
)
REAL_CARRIER = PROJECT_ROOT / (
    "Avatar/avatar_builder/workspaces/inactive_adult_female_foundations/"
    "generic_makehuman_adult_female_foundation_inactive_v1_20260801/"
    "generic_makehuman_adult_female_foundation_inactive_v1_20260801.blend"
)
WORKER_SOURCE = PROJECT_ROOT / "tools/blender_author_inactive_anatomy_package.py"
CONTROLLER_SOURCE = PROJECT_ROOT / "Core/avatar_inactive_anatomy_authoring.py"


class SyntheticSceneAdapter:
    def __init__(self, *, fail_on_source: int | None = None) -> None:
        self.fail_on_source = fail_on_source
        self.carrier_calls: list[Path] = []
        self.module_calls: list[str] = []
        self.import_calls: list[dict[str, object]] = []
        self.save_calls: list[Path] = []

    def load_carrier_read_only(self, carrier_path: Path) -> None:
        self.carrier_calls.append(carrier_path)

    def create_hidden_module_collection(self, collection_name: str) -> str:
        self.module_calls.append(collection_name)
        return collection_name

    def import_normalized_source(
        self,
        *,
        source_path: Path,
        source_collection_name: str,
        module_collection: object,
        normalization_matrix: list[float],
        object_name_prefix: str,
        source_sha256: str,
    ) -> list[dict[str, object]]:
        call = {
            "source_path": source_path,
            "source_collection_name": source_collection_name,
            "module_collection": module_collection,
            "normalization_matrix": list(normalization_matrix),
            "object_name_prefix": object_name_prefix,
            "source_sha256": source_sha256,
        }
        self.import_calls.append(call)
        if self.fail_on_source == len(self.import_calls):
            raise InactiveAnatomyAuthoringError("synthetic adapter failure")
        document = anatomy_preflight.read_glb2(source_path)
        return [
            {
                "name": f"{object_name_prefix}_{index:03d}_{mesh['name']}",
                "type": "MESH",
            }
            for index, mesh in enumerate(document["meshes"], start=1)
        ]

    def save_private_copy(self, output_path: Path) -> None:
        self.save_calls.append(output_path)
        output_path.write_bytes(b"BLENDER-v1-synthetic-private-inactive-anatomy\x00")


class PrivateInactiveAnatomyAuthoringTests(unittest.TestCase):
    def make_fixture(self) -> AnatomyFixture:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        fixture = AnatomyFixture(root, complete=True, owner_accepted=True)
        (root / "Avatar/avatar_builder/workspaces").mkdir(parents=True)
        write_json(root / "request.json", fixture.request)
        worker = root / "tools/blender_author_inactive_anatomy_package.py"
        worker.parent.mkdir(parents=True)
        worker.write_bytes(WORKER_SOURCE.read_bytes())
        fixture.request_path = root / "request.json"  # type: ignore[attr-defined]
        fixture.fake_blender_path = root / "synthetic_blender.exe"  # type: ignore[attr-defined]
        fixture.fake_blender_path.write_bytes(b"synthetic-blender-executable")  # type: ignore[attr-defined]
        source_patch = mock.patch.dict(
            anatomy_preflight.SUPPORTED_SOURCE_PACKAGES,
            {fixture.authority_id: fixture.authority_record},
            clear=False,
        )
        carrier_patch = mock.patch.dict(
            anatomy_preflight.SUPPORTED_CARRIER_AUTHORITIES,
            {fixture.carrier_authority_id: fixture.carrier_authority_record},
            clear=False,
        )
        source_patch.start()
        carrier_patch.start()
        self.addCleanup(source_patch.stop)
        self.addCleanup(carrier_patch.stop)
        return fixture

    @staticmethod
    def input_hashes(fixture: AnatomyFixture) -> dict[str, str]:
        paths = [fixture.carrier_path, *sorted(fixture.sources.glob("*.glb"))]
        return {
            path.relative_to(fixture.root).as_posix(): anatomy_preflight.sha256_file(path)
            for path in paths
        }

    def write_planned_job(self, fixture: AnatomyFixture, run_id: str):
        plan = plan_private_inactive_anatomy_authoring(
            fixture.root,
            request_path="request.json",
            run_id=run_id,
        )
        plan.output_root.mkdir()
        write_json(plan.output_root / JOB_NAME, plan.job)
        return plan

    def test_ready_synthetic_plan_is_deterministic_and_source_separated(self) -> None:
        fixture = self.make_fixture()
        first = plan_private_inactive_anatomy_authoring(
            fixture.root,
            request_path="request.json",
            run_id="deterministic_plan_v1",
        )
        second = plan_private_inactive_anatomy_authoring(
            fixture.root,
            request_path="request.json",
            run_id="deterministic_plan_v1",
        )

        self.assertEqual(
            anatomy_preflight.canonical_json_bytes(first.job),
            anatomy_preflight.canonical_json_bytes(second.job),
        )
        self.assertEqual(first.job["status"], anatomy_preflight.READY_FOR_PRIVATE_INACTIVE_AUTHORING)
        self.assertEqual(len(first.job["sources"]), 10)
        self.assertEqual(
            len({row["collection_name"] for row in first.job["sources"]}),
            len(first.job["sources"]),
        )
        self.assertTrue(first.job["separation"]["one_hidden_collection_per_source"])
        self.assertTrue(first.job["separation"]["default_hidden"])
        self.assertFalse(first.job["separation"]["objects_joined"])
        self.assertFalse(first.job["separation"]["contains_hair"])
        self.assertFalse(first.job["separation"]["contains_clothing"])
        self.assertEqual(set(first.job["truth"].values()), {False})
        self.assertEqual(
            first.job["job_receipt_sha256"],
            anatomy_preflight.canonical_sha256(
                {key: value for key, value in first.job.items() if key != "job_receipt_sha256"}
            ),
        )
        self.assertFalse(first.output_root.exists())

    def test_worker_imports_each_tiny_glb_into_its_own_hidden_collection(self) -> None:
        fixture = self.make_fixture()
        before = self.input_hashes(fixture)
        plan = self.write_planned_job(fixture, "worker_engine_v1")
        adapter = SyntheticSceneAdapter()

        result = run_blender_authoring_job(
            fixture.root,
            job_path=(plan.output_root / JOB_NAME).relative_to(fixture.root).as_posix(),
            adapter=adapter,
        )

        self.assertEqual(result["status"], AUTHORED_STATUS)
        self.assertEqual(adapter.module_calls, [MODULE_COLLECTION_NAME])
        self.assertEqual(len(adapter.import_calls), len(plan.job["sources"]))
        self.assertEqual(
            [call["source_collection_name"] for call in adapter.import_calls],
            [row["collection_name"] for row in plan.job["sources"]],
        )
        self.assertEqual(
            [call["normalization_matrix"] for call in adapter.import_calls],
            [row["normalization_matrix"] for row in plan.job["sources"]],
        )
        self.assertTrue(all(row["default_hidden"] for row in result["imports"]))
        self.assertTrue(all(row["function_implemented"] is False for row in result["imports"]))
        self.assertEqual(result["module_collection"]["separate_from_carrier_objects"], True)
        self.assertEqual(set(result["truth"].values()), {False})
        self.assertEqual(self.input_hashes(fixture), before)
        self.assertEqual(
            {path.name for path in plan.output_root.iterdir()},
            {JOB_NAME, ARTIFACT_NAME, WORKER_RESULT_NAME},
        )

    def test_controller_uses_safe_blender_flags_and_writes_bound_outputs(self) -> None:
        fixture = self.make_fixture()
        commands: list[list[str]] = []

        def runner(command, **kwargs):
            commands.append(list(command))
            self.assertEqual(kwargs["cwd"].name, f"{PRIVATE_OUTPUT_PREFIX}controller_success_v1")
            project_root = Path(command[command.index("--project-root") + 1])
            job_path = command[command.index("--job") + 1]
            run_blender_authoring_job(
                project_root,
                job_path=job_path,
                adapter=SyntheticSceneAdapter(),
            )
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        result = execute_private_inactive_anatomy_authoring(
            fixture.root,
            request_path="request.json",
            run_id="controller_success_v1",
            blender_path=fixture.fake_blender_path,  # type: ignore[attr-defined]
            runner=runner,
        )

        self.assertEqual(len(commands), 1)
        for flag in ("--background", "--factory-startup", "--disable-autoexec"):
            self.assertIn(flag, commands[0])
        self.assertLess(commands[0].index("--factory-startup"), commands[0].index("--python"))
        self.assertLess(commands[0].index("--disable-autoexec"), commands[0].index("--python"))
        output_root = fixture.root / result["output_root"]
        self.assertEqual(
            {path.name for path in output_root.iterdir()},
            {JOB_NAME, ARTIFACT_NAME, WORKER_RESULT_NAME, MANIFEST_NAME, RECEIPT_NAME},
        )
        manifest = json.loads((output_root / MANIFEST_NAME).read_text(encoding="utf-8"))
        receipt = json.loads((output_root / RECEIPT_NAME).read_text(encoding="utf-8"))
        self.assertEqual(anatomy_preflight.sha256_file(output_root / MANIFEST_NAME), result["manifest_sha256"])
        self.assertEqual(
            receipt["receipt_sha256"],
            anatomy_preflight.canonical_sha256(
                {key: value for key, value in receipt.items() if key != "receipt_sha256"}
            ),
        )
        self.assertEqual(manifest["worker"]["required_flags"], [
            "--background",
            "--factory-startup",
            "--disable-autoexec",
        ])
        self.assertFalse(manifest["truth"]["medical_completeness_claimed"])
        self.assertFalse(result["function_implemented"])
        self.assertFalse(result["runtime_activation_allowed"])
        self.assertFalse(result["public_export_allowed"])

    def test_manifest_and_receipt_are_deterministic_for_identical_inputs(self) -> None:
        fixture_one = self.make_fixture()
        fixture_two = self.make_fixture()

        def run_fixture(fixture: AnatomyFixture) -> dict[str, object]:
            def runner(command, **_kwargs):
                root = Path(command[command.index("--project-root") + 1])
                job = command[command.index("--job") + 1]
                run_blender_authoring_job(root, job_path=job, adapter=SyntheticSceneAdapter())
                return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

            return execute_private_inactive_anatomy_authoring(
                fixture.root,
                request_path="request.json",
                run_id="repeatable_v1",
                blender_path=fixture.fake_blender_path,  # type: ignore[attr-defined]
                runner=runner,
            )

        first = run_fixture(fixture_one)
        second = run_fixture(fixture_two)
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
        self.assertEqual(first["receipt_sha256"], second["receipt_sha256"])
        self.assertEqual(first["artifact_sha256"], second["artifact_sha256"])

    def test_controller_rolls_back_fresh_root_after_worker_failure(self) -> None:
        fixture = self.make_fixture()
        before = self.input_hashes(fixture)
        output_root = fixture.root / (
            "Avatar/avatar_builder/workspaces/"
            f"{PRIVATE_OUTPUT_PREFIX}rollback_v1"
        )

        def failed_runner(command, **_kwargs):
            return subprocess.CompletedProcess(command, 9, stdout="", stderr="synthetic failure")

        with self.assertRaisesRegex(InactiveAnatomyAuthoringError, "failed with exit code 9"):
            execute_private_inactive_anatomy_authoring(
                fixture.root,
                request_path="request.json",
                run_id="rollback_v1",
                blender_path=fixture.fake_blender_path,  # type: ignore[attr-defined]
                runner=failed_runner,
            )
        self.assertFalse(output_root.exists())
        quarantines = list(output_root.parent.glob(f".rollback_{output_root.name}_*"))
        self.assertEqual(len(quarantines), 1)
        self.assertTrue((quarantines[0] / JOB_NAME).is_file())
        self.assertEqual(self.input_hashes(fixture), before)

    def test_rollback_refuses_directory_substitution_and_preserves_victim(self) -> None:
        fixture = self.make_fixture()
        workspace = fixture.root / "Avatar/avatar_builder/workspaces"
        output_root = workspace / f"{PRIVATE_OUTPUT_PREFIX}substitution_v1"
        parked_original = workspace / "parked_original_fresh_root"
        victim = workspace / "victim_directory"
        victim.mkdir()
        sentinel = victim / "must_survive.txt"
        sentinel.write_text("victim content must survive", encoding="utf-8")

        def substituting_runner(command, **kwargs):
            current_output = Path(kwargs["cwd"])
            current_output.rename(parked_original)
            victim.rename(current_output)
            return subprocess.CompletedProcess(command, 9, stdout="", stderr="substituted")

        with self.assertRaisesRegex(
            InactiveAnatomyAuthoringError,
            "cleanup refused: output directory identity changed",
        ):
            execute_private_inactive_anatomy_authoring(
                fixture.root,
                request_path="request.json",
                run_id="substitution_v1",
                blender_path=fixture.fake_blender_path,  # type: ignore[attr-defined]
                runner=substituting_runner,
            )
        self.assertEqual((output_root / sentinel.name).read_text(encoding="utf-8"), "victim content must survive")
        self.assertTrue((parked_original / JOB_NAME).is_file())

    def test_multiply_linked_blender_executable_is_rejected_before_output(self) -> None:
        fixture = self.make_fixture()
        linked_blender = fixture.root / "multiply_linked_blender.exe"
        try:
            os.link(fixture.fake_blender_path, linked_blender)  # type: ignore[attr-defined]
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"hardlink creation unavailable: {exc}")
        output_root = fixture.root / (
            "Avatar/avatar_builder/workspaces/"
            f"{PRIVATE_OUTPUT_PREFIX}hardlinked_blender_v1"
        )
        runner = mock.Mock()

        with self.assertRaisesRegex(InactiveAnatomyAuthoringError, "multiply linked"):
            execute_private_inactive_anatomy_authoring(
                fixture.root,
                request_path="request.json",
                run_id="hardlinked_blender_v1",
                blender_path=linked_blender,
                runner=runner,
            )
        runner.assert_not_called()
        self.assertFalse(output_root.exists())

    def test_worker_refuses_nonready_status_before_adapter_or_artifact(self) -> None:
        fixture = self.make_fixture()
        plan = plan_private_inactive_anatomy_authoring(
            fixture.root,
            request_path="request.json",
            run_id="nonready_worker_v1",
        )
        job = copy.deepcopy(plan.job)
        job["status"] = anatomy_preflight.PREFLIGHT_BLOCKED_MISSING_STRUCTURES
        unsigned = {key: value for key, value in job.items() if key != "job_receipt_sha256"}
        job["job_receipt_sha256"] = anatomy_preflight.canonical_sha256(unsigned)
        plan.output_root.mkdir()
        write_json(plan.output_root / JOB_NAME, job)
        adapter = SyntheticSceneAdapter()

        with self.assertRaisesRegex(InactiveAnatomyAuthoringError, "not READY"):
            run_blender_authoring_job(
                fixture.root,
                job_path=(plan.output_root / JOB_NAME).relative_to(fixture.root).as_posix(),
                adapter=adapter,
            )
        self.assertEqual(adapter.carrier_calls, [])
        self.assertEqual(adapter.import_calls, [])
        self.assertFalse((plan.output_root / ARTIFACT_NAME).exists())

    def test_checked_in_kira_blocked_request_refuses_without_blender_or_output(self) -> None:
        before = anatomy_preflight.sha256_file(REAL_CARRIER)
        runner = mock.Mock()
        run_id = "checked_in_kira_blocked_refusal_v1"
        output_root = PROJECT_ROOT / (
            "Avatar/avatar_builder/workspaces/" f"{PRIVATE_OUTPUT_PREFIX}{run_id}"
        )
        self.assertFalse(output_root.exists())

        with self.assertRaisesRegex(
            InactiveAnatomyAuthoringError,
            anatomy_preflight.PREFLIGHT_BLOCKED_MISSING_STRUCTURES,
        ):
            execute_private_inactive_anatomy_authoring(
                PROJECT_ROOT,
                request_path=REAL_REQUEST,
                run_id=run_id,
                blender_path=PROJECT_ROOT / "does_not_need_to_exist_for_blocked_preflight.exe",
                runner=runner,
            )
        runner.assert_not_called()
        self.assertFalse(output_root.exists())
        self.assertEqual(anatomy_preflight.sha256_file(REAL_CARRIER), before)

    def test_cli_failure_reports_truthful_quarantine_policy(self) -> None:
        run_id = "checked_in_kira_cli_refusal_v1"
        output_root = PROJECT_ROOT / (
            "Avatar/avatar_builder/workspaces/" f"{PRIVATE_OUTPUT_PREFIX}{run_id}"
        )
        self.assertFalse(output_root.exists())
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            exit_code = controller_main(
                [
                    "--project-root",
                    str(PROJECT_ROOT),
                    "--request",
                    REAL_REQUEST,
                    "--run-id",
                    run_id,
                    "--blender",
                    str(PROJECT_ROOT / "not_needed_for_blocked_preflight.exe"),
                ]
            )
        self.assertEqual(exit_code, 9)
        result = json.loads(stderr.getvalue())
        self.assertIsNone(result["output_retained"])
        self.assertEqual(
            result["failed_output_quarantine_policy"],
            "retained_if_fresh_output_was_created",
        )
        self.assertIs(result["automatic_recursive_cleanup_performed"], False)
        self.assertFalse(output_root.exists())

    def test_failure_quarantine_contains_no_recursive_delete_primitive(self) -> None:
        source = CONTROLLER_SOURCE.read_text(encoding="utf-8")
        for forbidden in ("shutil.rmtree", "os.remove(", "os.unlink(", "Path.unlink("):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
