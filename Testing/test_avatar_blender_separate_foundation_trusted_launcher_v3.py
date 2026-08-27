from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unittest

import Core.avatar_blender_separate_foundation_trusted_launcher_v3 as launcher_v3
from Core.avatar_blender_separate_foundation_trusted_launcher_v3 import (
    EXPECTED_RESULT_STATUS,
    LAUNCHER_PATH,
    POLICY_PATH,
    RECORDED_RECEIPT_PATH,
    SeparateFoundationTrustedLauncherV3Rejected,
    _decode_json_object,
    evaluate_separate_foundation_trusted_launcher_v3,
    validate_launcher_source,
)


PROJECT_ROOT = launcher_v3.PROJECT_ROOT
SOURCE_EXPECTED = {
    "Avatar/avatar_builder/candidate_sources/kira_provisional_body_r6/r6_20260718_163658/kira_provisional_body_r6.glb": {
        "bytes": 5_105_808,
        "sha256": "ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77",
        "mtime_ns": 1_784_407_032_475_394_300,
    },
    "Avatar/outputs/user/dual_robert_candidates_20260729/synthetic_robert_twin_body/synthetic_robert_twin_body.glb": {
        "bytes": 8_645_492,
        "sha256": "bfcdf8ec2a1d8444cfef5f7d1382884cb5f6aff685f04c6e4d000b4de0332370",
        "mtime_ns": 1_785_296_385_810_827_200,
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_state() -> dict[str, dict[str, int | str]]:
    result: dict[str, dict[str, int | str]] = {}
    for relative in SOURCE_EXPECTED:
        path = PROJECT_ROOT.joinpath(*relative.split("/"))
        stat_result = path.stat()
        result[relative] = {
            "bytes": stat_result.st_size,
            "sha256": sha256(path),
            "mtime_ns": stat_result.st_mtime_ns,
        }
    return result


class SeparateFoundationTrustedLauncherV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.launcher_source = LAUNCHER_PATH.read_text(encoding="utf-8")
        cls.before_sources = source_state()

    @classmethod
    def tearDownClass(cls) -> None:
        if source_state() != cls.before_sources:
            raise AssertionError("source GLB state changed during static tests")

    def test_01_live_static_evaluation_passes_without_execution_authority(self) -> None:
        result = evaluate_separate_foundation_trusted_launcher_v3(PROJECT_ROOT)
        self.assertEqual(result["status"], EXPECTED_RESULT_STATUS)
        self.assertIs(result["static_launcher_v3_valid"], True)
        self.assertEqual(result["failures"], [])
        self.assertIs(result["independent_audit_passed"], True)
        for key in (
            "positive_authority_present", "authority_consumed", "worker_claim_present",
            "execution_authorized", "blender_started", "body_authoring_performed",
            "source_files_modified", "runtime_activation_allowed", "publication_allowed",
        ):
            self.assertIs(result[key], False, key)

    def test_02_recorded_receipt_replays_live_result(self) -> None:
        live = evaluate_separate_foundation_trusted_launcher_v3(PROJECT_ROOT)
        recorded = json.loads(RECORDED_RECEIPT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(recorded, live)

    def test_03_policy_and_audit_compatibility_mirrors_are_byte_identical(self) -> None:
        self.assertEqual(
            POLICY_PATH.read_bytes(),
            PROJECT_ROOT.joinpath(*launcher_v3.WORKER_POLICY_COMPAT_RELATIVE_PATH.split("/")).read_bytes(),
        )
        self.assertEqual(
            PROJECT_ROOT.joinpath(*launcher_v3.INDEPENDENT_AUDIT_RELATIVE_PATH.split("/")).read_bytes(),
            PROJECT_ROOT.joinpath(*launcher_v3.WORKER_AUDIT_COMPAT_RELATIVE_PATH.split("/")).read_bytes(),
        )

    def test_04_strict_json_rejects_duplicate_and_case_colliding_keys(self) -> None:
        for raw in (b'{"a":1,"a":2}', b'{"Key":1,"key":2}'):
            with self.assertRaises(SeparateFoundationTrustedLauncherV3Rejected):
                _decode_json_object(raw, "attack")

    def test_05_scalar_types_do_not_accept_loose_values(self) -> None:
        for value in (2.0, True, "2", None):
            with self.assertRaises(SeparateFoundationTrustedLauncherV3Rejected):
                launcher_v3._require_exact_type(value, int, "schema")

    def test_06_launcher_source_validator_accepts_frozen_v3(self) -> None:
        evidence = validate_launcher_source(self.launcher_source)
        self.assertTrue(all(evidence.values()))

    def assert_source_mutation_rejected(self, mutated: str) -> None:
        self.assertNotEqual(mutated, self.launcher_source)
        with self.assertRaises(SeparateFoundationTrustedLauncherV3Rejected):
            validate_launcher_source(mutated)

    def test_07_namespace_swap_mutation_is_rejected(self) -> None:
        self.assert_source_mutation_rejected(self.launcher_source.replace(
            "var share = FILE_SHARE_READ | FILE_SHARE_WRITE;",
            "var share = FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE;",
            1,
        ))

    def test_08_ancestor_identity_revalidation_removal_is_rejected(self) -> None:
        self.assert_source_mutation_rejected(self.launcher_source.replace(
            "Assert-DirectoryIdentityClosure $Locked.DirectoryClosure 'runtime namespace immediately before suspended CreateProcess'",
            "# removed ancestor identity revalidation",
            1,
        ))

    def test_09_process_mapped_image_proof_removal_is_rejected(self) -> None:
        self.assert_source_mutation_rejected(self.launcher_source.replace(
            "ProcessMappedImageDevicePath($ProcessInfo.hProcess)",
            "'untrusted path text'",
            1,
        ))

    def test_10_final_executable_identity_comparison_removal_is_rejected(self) -> None:
        self.assert_source_mutation_rejected(self.launcher_source.replace(
            "$ProcessImageIdentity.stable_identity -cne $LockedBlenderIdentity.stable_identity",
            "$false",
            1,
        ))

    def test_11_handle_bound_final_commit_replacement_is_rejected(self) -> None:
        self.assert_source_mutation_rejected(self.launcher_source.replace(
            "RenameDirectoryHandleNoReplace($StageHandle, $Final)",
            "MoveFileExW($Stage, $Final, 0)",
            1,
        ))

    def test_12_cleanup_delete_injection_is_rejected(self) -> None:
        marker = "# Deliberately preserve residue."
        self.assert_source_mutation_rejected(self.launcher_source.replace(
            marker, "Remove-Item -LiteralPath $Absolute -Recurse -Force\n    " + marker, 1,
        ))

    def test_13_cleanup_parent_identity_removal_is_rejected(self) -> None:
        self.assert_source_mutation_rejected(self.launcher_source.replace(
            "Assert-DirectoryIdentityClosure $OriginalNamespaceClosure 'failure residue original parent/ancestor identity closure'",
            "# removed cleanup parent identity proof",
            1,
        ))

    def test_14_cleanup_reparse_or_file_id_mismatch_checks_are_required(self) -> None:
        for marker in (
            "IsReparsePoint($IdentityHandle)",
            "StableVolumeFileIdentity($IdentityHandle) -cne $ExpectedStableIdentity",
            "StableVolumeFileIdentity($AtPath) -cne $ExpectedStableIdentity",
        ):
            self.assert_source_mutation_rejected(self.launcher_source.replace(marker, "removed", 1))

    def test_15_replay_and_no_replace_contract_is_closed(self) -> None:
        config = json.loads(PROJECT_ROOT.joinpath(*launcher_v3.WORKER_CONFIG_RELATIVE_PATH.split("/")).read_text(encoding="utf-8"))
        self.assertEqual(config["worker_claim_contract"]["maximum_authority_ttl_seconds"], 900)
        self.assertIn("Authority was already consumed or claimed", self.launcher_source)
        self.assertIn("Commit-BytesExclusive ($ConsumptionPath", self.launcher_source)
        self.assertIn("Commit-BytesExclusive ($WorkerClaimPath", self.launcher_source)
        self.assertIn("RenameDirectoryHandleNoReplace($StageHandle, $Final)", self.launcher_source)

    def test_16_exact_four_file_closure_and_no_source_mutation(self) -> None:
        result = evaluate_separate_foundation_trusted_launcher_v3(PROJECT_ROOT)
        self.assertEqual(result["exact_final_files"], launcher_v3.EXPECTED_FINAL_FILES)
        self.assertEqual(source_state(), SOURCE_EXPECTED)

    def test_17_no_execute_fails_before_native_and_creates_no_namespace(self) -> None:
        runtime = PROJECT_ROOT.joinpath(*launcher_v3.RUNTIME_NAMESPACE_RELATIVE_PATH.split("/"))
        self.assertFalse(runtime.exists())
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(LAUNCHER_PATH)],
            cwd=PROJECT_ROOT, text=True, capture_output=True, timeout=30, check=False,
        )
        combined = completed.stdout + completed.stderr
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("Execution was not requested", combined)
        self.assertFalse(runtime.exists())

    def test_18_powershell_ast_and_embedded_csharp_compile(self) -> None:
        escaped = str(LAUNCHER_PATH).replace("'", "''")
        command = (
            f"$p='{escaped}';$t=$null;$e=$null;"
            "[System.Management.Automation.Language.Parser]::ParseFile($p,[ref]$t,[ref]$e)|Out-Null;"
            "if($e.Count){$e|% ToString;exit 1};"
            "$s=[IO.File]::ReadAllText($p);"
            "$m=[regex]::Match($s,\"Add-Type -TypeDefinition @'\\r?\\n(?<cs>[\\s\\S]*?)\\r?\\n'@\");"
            "if(-not $m.Success){exit 2};Add-Type -TypeDefinition $m.Groups['cs'].Value -ErrorAction Stop;"
            "'PASS'"
        )
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", command],
            cwd=PROJECT_ROOT, text=True, capture_output=True, timeout=60, check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("PASS", completed.stdout)

    def test_19_python_sources_parse(self) -> None:
        ast.parse(Path(launcher_v3.__file__).read_text(encoding="utf-8"))
        ast.parse(Path(__file__).read_text(encoding="utf-8"))

    def test_20_no_authority_claim_stage_or_output_namespace_exists(self) -> None:
        for relative in (
            launcher_v3.AUTHORITY_RELATIVE_PATH, launcher_v3.CONSUMPTION_RELATIVE_PATH,
            launcher_v3.CLAIM_RELATIVE_PATH, launcher_v3.RUNTIME_NAMESPACE_RELATIVE_PATH,
        ):
            self.assertFalse(PROJECT_ROOT.joinpath(*relative.split("/")).exists(), relative)

    def test_21_source_and_closure_files_have_no_alternate_data_streams(self) -> None:
        paths = [LAUNCHER_PATH, POLICY_PATH]
        paths.extend(PROJECT_ROOT.joinpath(*item.split("/")) for item in SOURCE_EXPECTED)
        for path in paths:
            escaped = str(path).replace("'", "''")
            command = (
                f"$p='{escaped}';$s=@(Get-Item -LiteralPath $p -Stream *);"
                "$extra=@($s|? Stream -ne ':$DATA');"
                "if($extra.Count){$extra|ConvertTo-Json;exit 1}"
            )
            completed = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", command],
                text=True, capture_output=True, timeout=30, check=False,
            )
            self.assertEqual(completed.returncode, 0, f"{path}: {completed.stdout}{completed.stderr}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
