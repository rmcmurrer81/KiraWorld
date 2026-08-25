"""Hostile fake-API tests for the inert Blender native-provider contract.

The suite never calls a process API and never launches Blender.  Fake opaque
tokens are ordinary Python objects.
"""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core import avatar_blender_native_provider_contract as contract


PROVIDER_ID = "review_candidate_provider_v2"
RUN_ID = "native_contract_01"
BLENDER_PATH = r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
CLAIM_ROOT = r"C:\claims"
CLAIM_PATH = rf"{CLAIM_ROOT}\{RUN_ID}.claim.json"
DIRECTORY_PATHS = ("C:\\", CLAIM_ROOT)
IMAGE_SHA256 = "a" * 64
CLAIM_SHA256 = "b" * 64


class _FakeCloseApi:
    def __init__(self, *, result: bool = True, raises: bool = False) -> None:
        self.result = result
        self.raises = raises
        self.calls: list[object] = []

    def close_handle(self, native_token: object) -> bool:
        self.calls.append(native_token)
        if self.raises:
            raise RuntimeError("fake close failure")
        return self.result


class _ExplodingCloseProperty:
    @property
    def close_handle(self):
        raise RuntimeError("hostile close property")


def _environment() -> dict[str, str]:
    return {
        "SystemRoot": r"C:\Windows",
        "WINDIR": r"C:\Windows",
        "ComSpec": r"C:\Windows\System32\cmd.exe",
        "PATH": r"C:\Windows\System32",
        "TEMP": r"C:\bounded-temp",
        "TMP": r"C:\bounded-temp",
    }


def _command() -> tuple[str, ...]:
    return (
        BLENDER_PATH,
        "--background",
        "--factory-startup",
        "--disable-autoexec",
        "--python",
        r"C:\project\tools\blender_build_makehuman_adult_female_rigged_carrier_inactive.py",
        "--",
        "--config",
        r"C:\project\Avatar\avatar_builder\tooling\makehuman_adult_female_rigged_carrier_v1.json",
        "--authorization",
        r"C:\claims\ONE_RUN_AUTHORIZATION.json",
    )


def _requirements() -> contract.NativeLaunchRequirements:
    return contract.build_native_launch_requirements(
        provider_id=PROVIDER_ID,
        run_id=RUN_ID,
        command=_command(),
        environment=_environment(),
        working_directory=r"C:\project",
        expected_image_bytes=108687824,
        expected_image_sha256=IMAGE_SHA256,
        claim_path=CLAIM_PATH,
        claim_payload_sha256=CLAIM_SHA256,
        directory_paths=DIRECTORY_PATHS,
        timeout_ms=900_000,
    )


def _handle_bundle(
    *,
    close_api: _FakeCloseApi | None = None,
) -> tuple[contract.RetainedNativeLaunchHandles, _FakeCloseApi]:
    api = close_api or _FakeCloseApi()
    handles = [
        contract.RetainedNativeHandle(
            provider_id=PROVIDER_ID,
            kind=kind,
            native_token=object(),
            close_api=api,
        )
        for kind in (
            "process",
            "primary_thread",
            "job",
            "blender_image_file",
            "claim_file",
            "directory",
            "directory",
        )
    ]
    return (
        contract.RetainedNativeLaunchHandles(
            process=handles[0],
            primary_thread=handles[1],
            job=handles[2],
            blender_image_file=handles[3],
            claim_file=handles[4],
            directories=(handles[5], handles[6]),
        ),
        api,
    )


def _path_identity(
    *,
    source: str,
    file_id: str = "1" * 32,
    final_path: str = BLENDER_PATH,
) -> contract.NativePathIdentityAttestation:
    return contract.NativePathIdentityAttestation(
        schema=contract.NATIVE_PATH_IDENTITY_SCHEMA,
        provider_id=PROVIDER_ID,
        source=source,
        final_path=final_path,
        final_path_sha256=contract.private_windows_path_sha256(final_path),
        canonical_path_sha256=contract.canonical_windows_path_sha256(final_path),
        volume_serial_number=314159,
        file_id=file_id,
        bytes=108687824,
        sha256=IMAGE_SHA256,
        link_count=1,
        regular_file=True,
        reparse_point=False,
        handle_retained=True,
        path_published=False,
    )


def _image_attestation() -> contract.NativeProcessImageAttestation:
    return contract.NativeProcessImageAttestation(
        schema=contract.NATIVE_PROCESS_IMAGE_SCHEMA,
        provider_id=PROVIDER_ID,
        held_blender_image=_path_identity(source="held_blender_file_handle"),
        created_process_image=_path_identity(source="created_process_handle_image"),
        queried_from_retained_process_handle=True,
        pid_lookup_used_as_identity=False,
        identity_equal=True,
        verified_before_resume=True,
    )


def _process_policy(
    requirements: contract.NativeLaunchRequirements,
) -> contract.NativeProcessPolicyAttestation:
    return contract.NativeProcessPolicyAttestation(
        schema=contract.NATIVE_PROCESS_POLICY_SCHEMA,
        provider_id=PROVIDER_ID,
        interface_version=contract.NATIVE_PROVIDER_INTERFACE,
        lp_application_name_sha256=requirements.lp_application_name_sha256,
        lp_application_name_canonical_sha256=(
            requirements.lp_application_name_canonical_sha256
        ),
        argv_sha256=requirements.argv_sha256,
        command_line_sha256=requirements.command_line_sha256,
        environment_block_sha256=requirements.environment_block_sha256,
        working_directory_sha256=requirements.working_directory_sha256,
        environment_entry_count=6,
        creation_api="CreateProcessW",
        creation_flags=contract.EXACT_CREATE_PROCESS_FLAGS,
        application_name_explicit=True,
        shell_used=False,
        parent_environment_inherited=False,
        unicode_environment=True,
        handles_inherited=False,
        created_suspended=True,
        job_kill_on_close=True,
        assigned_to_job_before_image_check=True,
        image_verified_before_resume=True,
        pid_used_as_process_identity=False,
        resume_count=0,
        timeout_ms=requirements.timeout_ms,
        descendant_tree_termination_required=True,
    )


def _directory_chain() -> tuple[contract.NativeDirectoryIdentityAttestation, ...]:
    return tuple(
        contract.NativeDirectoryIdentityAttestation(
            provider_id=PROVIDER_ID,
            depth=index,
            final_path=path,
            final_path_sha256=contract.private_windows_path_sha256(path),
            volume_serial_number=314159,
            file_id=f"{index + 2:032x}",
            local_volume=True,
            reparse_point=False,
            handle_retained=True,
            write_delete_share_denied=True,
            path_published=False,
        )
        for index, path in enumerate(DIRECTORY_PATHS)
    )


def _claim_attestation(
    requirements: contract.NativeLaunchRequirements,
) -> contract.NativeClaimDurabilityAttestation:
    directories = _directory_chain()
    chain_sha256 = contract.canonical_sha256(
        [directory.private_safe_record() for directory in directories]
    )
    return contract.NativeClaimDurabilityAttestation(
        schema=contract.NATIVE_CLAIM_DURABILITY_SCHEMA,
        provider_id=PROVIDER_ID,
        interface_version=contract.NATIVE_PROVIDER_INTERFACE,
        run_id=RUN_ID,
        claim_root_path_sha256=requirements.claim_root_path_sha256,
        claim_path_sha256=requirements.claim_path_sha256,
        claim_payload_sha256=CLAIM_SHA256,
        directory_chain=directories,
        directory_chain_sha256=chain_sha256,
        contract_sha256=contract.directory_claim_durability_contract_sha256(),
        claim_create_disposition=contract.CREATE_NEW,
        claim_share_mode=contract.FILE_SHARE_NONE,
        claim_flags_and_attributes=contract.EXACT_DURABLE_RECORD_FLAGS,
        claim_created_new=True,
        claim_payload_flush_succeeded=True,
        claim_parent_directory_flush_succeeded=True,
        claim_handle_retained_through_terminal=True,
        same_principal_rewrite_denied=True,
        same_principal_delete_denied=True,
        pending_claim_permanently_nonreplayable=True,
        outcome_create_new_required=True,
        outcome_payload_and_parent_flush_required=True,
        exactly_one_terminal_outcome_required=True,
    )


def _pre_resume(
    requirements: contract.NativeLaunchRequirements,
) -> contract.NativePreResumeAttestation:
    handles, _ = _handle_bundle()
    return contract.NativePreResumeAttestation(
        schema=contract.NATIVE_PRE_RESUME_SCHEMA,
        provider_id=PROVIDER_ID,
        interface_version=contract.NATIVE_PROVIDER_INTERFACE,
        requirements_sha256=contract.canonical_sha256(dict(requirements.safe_record())),
        handles=handles,
        process_image=_image_attestation(),
        process_policy=_process_policy(requirements),
        claim_durability=_claim_attestation(requirements),
        process_started_suspended=True,
        resume_authorized=False,
        process_execution_authorized=False,
    )


class BlenderNativeProviderContractTests(unittest.TestCase):
    def test_exact_static_contract_has_no_authority_or_private_paths(self) -> None:
        record = dict(contract.static_contract_evidence_record())
        self.assertEqual(contract.NATIVE_PROVIDER_INTERFACE, record["provider_interface"])
        self.assertEqual(
            contract.directory_claim_durability_contract_sha256(),
            record["directory_claim_contract_sha256"],
        )
        self.assertEqual("STATIC_STRUCTURE_AND_FAKE_API_ONLY", record["review_scope"])
        for key in (
            "native_provider_reviewed",
            "operating_system_evidence_verified",
            "resume_authorized",
            "process_execution_authorized",
        ):
            self.assertIs(record[key], False)
        serialized = json.dumps(record, sort_keys=True)
        self.assertNotIn("C:\\", serialized)
        self.assertNotIn("Blender Foundation", serialized)

    def test_fake_pre_resume_shape_validates_without_resume_authority(self) -> None:
        requirements = _requirements()
        receipt = contract.validate_native_pre_resume_attestation(
            _pre_resume(requirements),
            requirements,
        )
        self.assertEqual(contract.NATIVE_STATIC_VALIDATION_STATUS, receipt["status"])
        self.assertTrue(receipt["retained_handle_shape_valid"])
        self.assertTrue(receipt["image_path_shape_valid"])
        self.assertTrue(receipt["process_policy_shape_valid"])
        self.assertTrue(receipt["directory_claim_shape_valid"])
        for key in (
            "native_provider_reviewed",
            "operating_system_evidence_verified",
            "resume_authorized",
            "process_execution_authorized",
            "body_created",
            "runtime_activation_authorized",
            "public_export_authorized",
        ):
            self.assertIs(receipt[key], False)

    def test_requirements_bind_exact_argv_environment_paths_and_timeout(self) -> None:
        requirements = _requirements()
        self.assertEqual(
            contract.canonical_sha256(list(_command())),
            requirements.argv_sha256,
        )
        self.assertEqual(
            contract.windows_command_line_sha256(_command()),
            requirements.command_line_sha256,
        )
        self.assertEqual(
            contract.windows_environment_block_sha256(_environment()),
            requirements.environment_block_sha256,
        )
        self.assertEqual(
            contract.private_windows_path_sha256(BLENDER_PATH),
            requirements.lp_application_name_sha256,
        )
        self.assertEqual(
            contract.canonical_windows_path_sha256(BLENDER_PATH),
            requirements.lp_application_name_canonical_sha256,
        )
        self.assertEqual(contract.EXACT_CREATE_PROCESS_FLAGS, requirements.creation_flags)
        self.assertEqual(900_000, requirements.timeout_ms)
        self.assertIs(requirements.resume_authorized, False)

        poisoned = _environment()
        poisoned["PYTHONPATH"] = r"C:\poison"
        with self.assertRaisesRegex(
            contract.NativeProviderContractError,
            "environment keys",
        ):
            contract.build_native_launch_requirements(
                provider_id=PROVIDER_ID,
                run_id=RUN_ID,
                command=_command(),
                environment=poisoned,
                working_directory=r"C:\project",
                expected_image_bytes=1,
                expected_image_sha256=IMAGE_SHA256,
                claim_path=CLAIM_PATH,
                claim_payload_sha256=CLAIM_SHA256,
                directory_paths=DIRECTORY_PATHS,
                timeout_ms=1,
            )

    def test_handle_bundle_rejects_alias_closed_and_mixed_api_tokens(self) -> None:
        api = _FakeCloseApi()
        token = object()
        process = contract.RetainedNativeHandle(
            provider_id=PROVIDER_ID,
            kind="process",
            native_token=token,
            close_api=api,
        )
        thread = contract.RetainedNativeHandle(
            provider_id=PROVIDER_ID,
            kind="primary_thread",
            native_token=token,
            close_api=api,
        )
        good, _ = _handle_bundle(close_api=api)
        with self.assertRaisesRegex(contract.NativeProviderContractError, "tokens alias"):
            contract.RetainedNativeLaunchHandles(
                process=process,
                primary_thread=thread,
                job=good.job,
                blender_image_file=good.blender_image_file,
                claim_file=good.claim_file,
                directories=good.directories,
            )

        good.process.close()
        with self.assertRaisesRegex(contract.NativeProviderContractError, "closed early"):
            good.assert_all_open()

        second_api = _FakeCloseApi()
        mixed_job = contract.RetainedNativeHandle(
            provider_id=PROVIDER_ID,
            kind="job",
            native_token=object(),
            close_api=second_api,
        )
        fresh, _ = _handle_bundle(close_api=api)
        with self.assertRaisesRegex(contract.NativeProviderContractError, "close APIs differ"):
            contract.RetainedNativeLaunchHandles(
                process=fresh.process,
                primary_thread=fresh.primary_thread,
                job=mixed_job,
                blender_image_file=fresh.blender_image_file,
                claim_file=fresh.claim_file,
                directories=fresh.directories,
            )

    def test_handle_close_is_idempotent_and_failure_is_not_hidden(self) -> None:
        token = object()
        api = _FakeCloseApi()
        handle = contract.RetainedNativeHandle(
            provider_id=PROVIDER_ID,
            kind="job",
            native_token=token,
            close_api=api,
        )
        handle.close()
        handle.close()
        self.assertTrue(handle.closed)
        self.assertEqual([token], api.calls)

        failing = contract.RetainedNativeHandle(
            provider_id=PROVIDER_ID,
            kind="job",
            native_token=object(),
            close_api=_FakeCloseApi(result=False),
        )
        with self.assertRaisesRegex(contract.NativeProviderContractError, "not exactly successful"):
            failing.close()
        self.assertFalse(failing.closed)

        raising = contract.RetainedNativeHandle(
            provider_id=PROVIDER_ID,
            kind="job",
            native_token=object(),
            close_api=_FakeCloseApi(raises=True),
        )
        with self.assertRaisesRegex(contract.NativeProviderContractError, "close raised"):
            raising.close()
        self.assertFalse(raising.closed)

        with self.assertRaisesRegex(contract.NativeProviderContractError, "unavailable"):
            contract.RetainedNativeHandle(
                provider_id=PROVIDER_ID,
                kind="job",
                native_token=object(),
                close_api=_ExplodingCloseProperty(),
            )
        with self.assertRaisesRegex(contract.NativeProviderContractError, "opaque"):
            contract.RetainedNativeHandle(
                provider_id=PROVIDER_ID,
                kind="process",
                native_token=4242,
                close_api=api,
            )

    def test_image_path_mismatch_pid_identity_and_published_path_fail_closed(self) -> None:
        expected = _path_identity(source="held_blender_file_handle")
        extended = _path_identity(
            source="created_process_handle_image",
            final_path=rf"\\?\{BLENDER_PATH}",
        )
        normalized = contract.NativeProcessImageAttestation(
            schema=contract.NATIVE_PROCESS_IMAGE_SCHEMA,
            provider_id=PROVIDER_ID,
            held_blender_image=expected,
            created_process_image=extended,
            queried_from_retained_process_handle=True,
            pid_lookup_used_as_identity=False,
            identity_equal=True,
            verified_before_resume=True,
        )
        self.assertNotEqual(
            normalized.held_blender_image.final_path_sha256,
            normalized.created_process_image.final_path_sha256,
        )
        self.assertEqual(
            normalized.held_blender_image.canonical_path_sha256,
            normalized.created_process_image.canonical_path_sha256,
        )
        wrong_id = _path_identity(
            source="created_process_handle_image",
            file_id="2" * 32,
        )
        with self.assertRaisesRegex(contract.NativeProviderContractError, "identity differs"):
            contract.NativeProcessImageAttestation(
                schema=contract.NATIVE_PROCESS_IMAGE_SCHEMA,
                provider_id=PROVIDER_ID,
                held_blender_image=expected,
                created_process_image=wrong_id,
                queried_from_retained_process_handle=True,
                pid_lookup_used_as_identity=False,
                identity_equal=True,
                verified_before_resume=True,
            )
        with self.assertRaisesRegex(contract.NativeProviderContractError, "pid_lookup"):
            replace(_image_attestation(), pid_lookup_used_as_identity=True)
        with self.assertRaisesRegex(contract.NativeProviderContractError, "path_published"):
            replace(expected, path_published=True)
        with self.assertRaisesRegex(contract.NativeProviderContractError, "path digest differs"):
            replace(expected, final_path_sha256="f" * 64)

    def test_hostile_process_policy_mutations_fail_before_any_resume(self) -> None:
        policy = _process_policy(_requirements())
        mutations = (
            ("flags", {"creation_flags": contract.CREATE_UNICODE_ENVIRONMENT}),
            ("shell", {"shell_used": True}),
            ("parent_env", {"parent_environment_inherited": True}),
            ("inherit_handles", {"handles_inherited": True}),
            ("foreground", {"created_suspended": False}),
            ("job", {"job_kill_on_close": False}),
            ("order", {"assigned_to_job_before_image_check": False}),
            ("image_order", {"image_verified_before_resume": False}),
            ("pid_identity", {"pid_used_as_process_identity": True}),
            ("already_resumed", {"resume_count": 1}),
            ("bool_as_timeout", {"timeout_ms": True}),
        )
        for name, changes in mutations:
            with self.subTest(name=name), self.assertRaises(
                contract.NativeProviderContractError
            ):
                replace(policy, **changes)

    def test_hostile_claim_durability_mutations_fail_closed(self) -> None:
        claim = _claim_attestation(_requirements())
        mutations = (
            ("bool_create_disposition", {"claim_create_disposition": True}),
            ("bool_share", {"claim_share_mode": False}),
            ("share", {"claim_share_mode": contract.FILE_SHARE_READ}),
            ("flags", {"claim_flags_and_attributes": 0}),
            ("create", {"claim_created_new": False}),
            ("file_flush", {"claim_payload_flush_succeeded": False}),
            ("directory_flush", {"claim_parent_directory_flush_succeeded": False}),
            ("retention", {"claim_handle_retained_through_terminal": False}),
            ("rewrite", {"same_principal_rewrite_denied": False}),
            ("delete", {"same_principal_delete_denied": False}),
            ("pending_replay", {"pending_claim_permanently_nonreplayable": False}),
            ("outcome", {"exactly_one_terminal_outcome_required": False}),
            ("contract", {"contract_sha256": "0" * 64}),
        )
        for name, changes in mutations:
            with self.subTest(name=name), self.assertRaises(
                contract.NativeProviderContractError
            ):
                replace(claim, **changes)

    def test_validator_rejects_requirement_binding_and_cross_structure_drift(self) -> None:
        requirements = _requirements()
        valid = _pre_resume(requirements)
        with self.assertRaisesRegex(contract.NativeProviderContractError, "requirements binding"):
            contract.validate_native_pre_resume_attestation(
                replace(valid, requirements_sha256="0" * 64),
                requirements,
            )

        changed_requirements = replace(requirements, timeout_ms=requirements.timeout_ms + 1)
        with self.assertRaisesRegex(contract.NativeProviderContractError, "requirements binding"):
            contract.validate_native_pre_resume_attestation(valid, changed_requirements)

        changed_policy = replace(valid.process_policy, timeout_ms=valid.process_policy.timeout_ms + 1)
        changed = replace(
            valid,
            process_policy=changed_policy,
            requirements_sha256=contract.canonical_sha256(dict(requirements.safe_record())),
        )
        with self.assertRaisesRegex(contract.NativeProviderContractError, "timeout_ms differs"):
            contract.validate_native_pre_resume_attestation(changed, requirements)

        valid.handles.claim_file.close()
        with self.assertRaisesRegex(contract.NativeProviderContractError, "closed early"):
            contract.validate_native_pre_resume_attestation(valid, requirements)

    def test_directory_chain_rejects_gap_reparse_unc_and_duplicate(self) -> None:
        requirements = _requirements()
        claim = _claim_attestation(requirements)
        gap = replace(
            claim.directory_chain[1],
            final_path=r"C:\unrelated\claims",
            final_path_sha256=contract.private_windows_path_sha256(r"C:\unrelated\claims"),
        )
        with self.assertRaisesRegex(contract.NativeProviderContractError, "not contiguous"):
            replace(
                claim,
                directory_chain=(claim.directory_chain[0], gap),
                directory_chain_sha256=contract.canonical_sha256(
                    [claim.directory_chain[0].private_safe_record(), gap.private_safe_record()]
                ),
            )
        with self.assertRaisesRegex(contract.NativeProviderContractError, "reparse_point"):
            replace(claim.directory_chain[1], reparse_point=True)
        with self.assertRaisesRegex(contract.NativeProviderContractError, "must not be UNC"):
            replace(
                claim.directory_chain[1],
                final_path=r"\\server\claims",
                final_path_sha256="0" * 64,
            )
        with self.assertRaisesRegex(contract.NativeProviderContractError, "duplicate"):
            contract.build_native_launch_requirements(
                provider_id=PROVIDER_ID,
                run_id=RUN_ID,
                command=_command(),
                environment=_environment(),
                working_directory=r"C:\project",
                expected_image_bytes=1,
                expected_image_sha256=IMAGE_SHA256,
                claim_path=CLAIM_PATH,
                claim_payload_sha256=CLAIM_SHA256,
                directory_paths=(CLAIM_ROOT, CLAIM_ROOT),
                timeout_ms=1,
            )


if __name__ == "__main__":
    unittest.main()
