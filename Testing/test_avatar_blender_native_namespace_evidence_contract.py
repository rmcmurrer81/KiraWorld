"""Hostile fake-provider tests for retained Windows namespace evidence.

The tests construct opaque Python tokens and synthetic identity records only.
They do not call native APIs, create claims or outputs, or start Blender.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
import gc
import hashlib
import json
from pathlib import Path, PureWindowsPath
import sys
from threading import Event, Thread
from types import MappingProxyType
import unittest
import weakref


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core import avatar_blender_carrier_transaction_closure as closure
from Core import avatar_blender_native_namespace_evidence_contract as evidence
from Core import avatar_blender_native_provider_contract as native_contract
from Core import avatar_blender_native_transaction_provider_contract as transaction
from Core import avatar_blender_preimport_controller as preimport


PROVIDER_ID = "review_candidate_transaction_provider_v1"
RUN_ID = "carrier_namespace_evidence_20260825"
CLAIM_ROOT = rf"C:\KiraNativeTransactions\{RUN_ID}"
CLAIM_PATH = rf"{CLAIM_ROOT}\attempt.claim.json"
OUTCOME_PATH = rf"{CLAIM_ROOT}\attempt.outcome.json"
DIRECTORY_PATHS = ("C:\\", r"C:\KiraNativeTransactions", CLAIM_ROOT)


def _environment() -> dict[str, str]:
    return {
        "SystemRoot": r"C:\Windows",
        "WINDIR": r"C:\Windows",
        "ComSpec": r"C:\Windows\System32\cmd.exe",
        "PATH": r"C:\Windows\System32",
        "TEMP": r"C:\Temp",
        "TMP": r"C:\Temp",
    }


def _command(
    policy: preimport.ControllerPolicy,
    authorization_path: Path,
) -> tuple[str, ...]:
    by_role = policy.by_role
    return (
        str(by_role["blender_executable"].path.resolve(strict=True)),
        *preimport.REQUIRED_BLENDER_FLAGS,
        "--python",
        str(by_role["worker_script"].path.resolve(strict=True)),
        "--",
        "--config",
        str(by_role["config"].path.resolve(strict=True)),
        "--authorization",
        str(authorization_path.absolute()),
    )


def _ancestors(path: str) -> tuple[str, ...]:
    value = path[4:] if path.startswith("\\\\?\\") else path
    parsed = PureWindowsPath(value)
    return tuple(
        str(PureWindowsPath(*parsed.parts[:depth]))
        for depth in range(1, len(parsed.parts))
    )


class _CloseApi:
    def __init__(self) -> None:
        self.closed: list[object] = []

    def close_handle(self, native_token: object) -> bool:
        self.closed.append(native_token)
        return True


class _FakeToken:
    pass


class _RejectingCloseApi:
    def __init__(self) -> None:
        self.calls = 0

    def close_handle(self, native_token: object) -> bool:
        del native_token
        self.calls += 1
        return False


class _RaisingCloseApi:
    def __init__(self) -> None:
        self.calls = 0

    def close_handle(self, native_token: object) -> bool:
        del native_token
        self.calls += 1
        raise RuntimeError("synthetic ambiguous close")


class _BlockingCloseApi:
    def __init__(self) -> None:
        self.calls = 0
        self.started = Event()
        self.release = Event()

    def close_handle(self, native_token: object) -> bool:
        del native_token
        self.calls += 1
        self.started.set()
        if not self.release.wait(timeout=5):
            raise RuntimeError("synthetic close test timed out")
        return True


class _EqualitySpoof:
    def __eq__(self, other: object) -> bool:
        del other
        return True

    def __ne__(self, other: object) -> bool:
        del other
        return False


class _Evil(str):
    """String subclass that claims equality with every trusted literal."""

    def __eq__(self, other: object) -> bool:
        del other
        return True

    def __ne__(self, other: object) -> bool:
        del other
        return False

    __hash__ = str.__hash__


class _EvilHash(str):
    """String subclass that forges both equality and a trusted key's hash."""

    def __new__(
        cls,
        value: str,
        hash_target: str,
    ) -> "_EvilHash":
        instance = str.__new__(cls, value)
        instance.hash_target = hash_target
        return instance

    def __eq__(self, other: object) -> bool:
        del other
        return True

    def __ne__(self, other: object) -> bool:
        del other
        return False

    def __hash__(self) -> int:
        return hash(self.hash_target)


class _EvilInt(int):
    pass


class _EvilBytes(bytes):
    pass


class _EvilTuple(tuple):
    pass


class _EvilMapping(Mapping[str, object]):
    """Mapping whose every observable operation records hostile dispatch."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def _called(self, name: str) -> None:
        self.calls.append(name)
        raise AssertionError(f"hostile mapping method dispatched: {name}")

    def __getitem__(self, key: str) -> object:
        del key
        self._called("getitem")

    def __iter__(self):  # type: ignore[no-untyped-def]
        self._called("iter")

    def __len__(self) -> int:
        self._called("len")

    def items(self):  # type: ignore[no-untyped-def]
        self._called("items")

    def __eq__(self, other: object) -> bool:
        del other
        self._called("equality")

    def __hash__(self) -> int:
        self._called("hash")


class _EvidenceFixture:
    def __init__(
        self,
        request: transaction.NativeCarrierTransactionRequest,
    ) -> None:
        self.request = request
        self.request_capsule = (
            evidence.bind_native_namespace_transaction_request(request)
        )
        self.close_api = _CloseApi()
        self.next_identity = 1
        self.objects: dict[str, evidence.NativeHandlePathEvidence] = {}
        self.tokens: dict[str, _FakeToken] = {}
        self.response = self._response()

    def object(
        self,
        path: str,
        kind: str,
        *,
        byte_count: int | None = None,
        content_sha256: str | None = None,
        volume_serial_number: int = 0xA11CE,
        file_id: str | None = None,
        token: object | None = None,
        close_api: _CloseApi | None = None,
        reuse: bool = True,
    ) -> evidence.NativeHandlePathEvidence:
        canonical = native_contract.canonical_windows_path_sha256(path)
        if reuse and canonical in self.objects:
            value = self.objects[canonical]
            self.assert_compatible(value, kind)
            return value
        if file_id is None:
            file_id = f"{self.next_identity:032x}"
            self.next_identity += 1
        if token is None:
            token = _FakeToken()
        if close_api is None:
            close_api = self.close_api
        if kind == "directory":
            byte_count = 0
            content_sha256 = evidence.ZERO_SHA256
        else:
            byte_count = 257 if byte_count is None else byte_count
            content_sha256 = content_sha256 or hashlib.sha256(
                path.encode("utf-8")
            ).hexdigest()
        retained = evidence.RetainedNamespaceHandle(
            provider_id=PROVIDER_ID,
            kind=kind,
            native_token=token,
            close_api=close_api,
        )
        value = evidence.NativeHandlePathEvidence(
            schema=evidence.NATIVE_HANDLE_PATH_EVIDENCE_SCHEMA,
            provider_id=PROVIDER_ID,
            kind=kind,
            handle=retained,
            final_normalized_path=path,
            final_path_sha256=native_contract.private_windows_path_sha256(path),
            final_canonical_path_sha256=canonical,
            volume_serial_number=volume_serial_number,
            file_id=file_id,
            bytes=byte_count,
            content_sha256=content_sha256,
            link_count=1,
            local_fixed_volume=True,
            reparse_point=False,
            reparse_tag=0,
            opened_with_open_reparse_point=True,
            final_path_query_source=evidence.FINAL_PATH_QUERY_SOURCE,
            file_id_query_source=evidence.FILE_ID_QUERY_SOURCE,
            standard_info_query_source=evidence.STANDARD_INFO_QUERY_SOURCE,
            reparse_query_source=evidence.REPARSE_QUERY_SOURCE,
            volume_query_source=evidence.VOLUME_QUERY_SOURCE,
            drive_type_query_source=evidence.DRIVE_TYPE_QUERY_SOURCE,
            handle_retained_until_terminal=True,
            path_published_before_terminal=False,
        )
        if reuse:
            self.objects[canonical] = value
            self.tokens[canonical] = token  # type: ignore[assignment]
        return value

    @staticmethod
    def assert_compatible(
        value: evidence.NativeHandlePathEvidence,
        kind: str,
    ) -> None:
        if value.kind != kind:
            raise AssertionError("test fixture attempted incompatible path reuse")

    def _target(
        self,
        requirement: object,
    ) -> evidence.NativeNamespaceTargetEvidence:
        path = requirement.path
        ancestors = tuple(self.object(value, "directory") for value in _ancestors(path))
        target = self.object(
            path,
            requirement.kind,
            byte_count=requirement.expected_bytes,
            content_sha256=requirement.expected_content_sha256,
        )
        return evidence.NativeNamespaceTargetEvidence(
            schema=evidence.NATIVE_NAMESPACE_TARGET_SCHEMA,
            provider_id=PROVIDER_ID,
            role=requirement.role,
            requested_path_sha256=requirement.path_sha256,
            requested_canonical_path_sha256=requirement.canonical_path_sha256,
            target=target,
            ancestors=ancestors,
            created_new=requirement.created_new,
            observed_initially_absent=requirement.created_new,
        )

    def _response(self) -> evidence.NativeNamespaceEvidenceResponse:
        targets = tuple(
            self._target(requirement)
            for requirement in evidence._expected_targets(self.request)
        )
        return evidence.NativeNamespaceEvidenceResponse(
            schema=evidence.NATIVE_NAMESPACE_RESPONSE_SCHEMA,
            status=evidence.NATIVE_NAMESPACE_STATIC_STATUS,
            provider_id=PROVIDER_ID,
            interface_version=evidence.NATIVE_NAMESPACE_EVIDENCE_INTERFACE,
            request_sha256=self.request_capsule.request_sha256,
            targets=targets,
            provider_claimed_terminal_state="succeeded",
            exactly_one_terminal_outcome_claimed=True,
            provider_reviewed=False,
            operating_system_evidence_verified=False,
            body_created=False,
        )


class AvatarBlenderNativeNamespaceEvidenceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.closure_record = dict(closure.load_machine_static_transaction_closure())
        cls.output_paths = {
            value["role"]: str(PROJECT_ROOT / value["relative_path"])
            for value in cls.closure_record["outputs"]
        }
        authorization = Path(cls.output_paths["one_run_authorization"])
        cls.build_command = _command(
            preimport.load_machine_policy(operation="build"),
            authorization,
        )
        cls.audit_command = _command(
            preimport.load_machine_policy(operation="audit"),
            authorization,
        )

    @classmethod
    def request(
        cls,
        **overrides: object,
    ) -> transaction.NativeCarrierTransactionRequest:
        values: dict[str, object] = {
            "closure_record": cls.closure_record,
            "provider_id": PROVIDER_ID,
            "run_id": RUN_ID,
            "build_command": cls.build_command,
            "audit_command": cls.audit_command,
            "environment": _environment(),
            "working_directory": str(PROJECT_ROOT),
            "output_paths": cls.output_paths,
            "directory_paths": DIRECTORY_PATHS,
            "claim_root_path": CLAIM_ROOT,
            "claim_path": CLAIM_PATH,
            "outcome_path": OUTCOME_PATH,
            "build_timeout_ms": 60 * 60 * 1000,
            "audit_timeout_ms": 30 * 60 * 1000,
        }
        values.update(overrides)
        return transaction.build_native_transaction_request(**values)  # type: ignore[arg-type]

    def setUp(self) -> None:
        self.bound_request = self.request()
        self.fixture = _EvidenceFixture(self.bound_request)

    def validate_response(
        self,
        response: evidence.NativeNamespaceEvidenceResponse,
        request: transaction.NativeCarrierTransactionRequest
        | evidence.NativeNamespaceTransactionRequestCapsule
        | None = None,
    ) -> Mapping[str, object]:
        """Bind raw hostile fixtures before exercising the capsule-only API."""

        if request is None:
            capsule = self.fixture.request_capsule
        elif type(request) is evidence.NativeNamespaceTransactionRequestCapsule:
            capsule = request
        else:
            capsule = evidence.bind_native_namespace_transaction_request(request)
        return evidence.validate_native_namespace_evidence_response(
            response,
            capsule,
        )

    def response_with_target(
        self,
        index: int,
        target: evidence.NativeNamespaceTargetEvidence,
    ) -> evidence.NativeNamespaceEvidenceResponse:
        targets = list(self.fixture.response.targets)
        targets[index] = target
        return replace(self.fixture.response, targets=tuple(targets))

    def test_complete_fake_namespace_shape_is_valid_but_grants_no_authority(self) -> None:
        receipt = dict(
            self.validate_response(
                self.fixture.response,
                self.fixture.request_capsule,
            )
        )
        self.assertTrue(receipt["complete_normalized_ancestor_chains_shape_valid"])
        self.assertTrue(receipt["short_name_alias_rejection_shape_valid"])
        self.assertTrue(receipt["reparse_rejection_shape_valid"])
        self.assertTrue(receipt["single_link_identity_shape_valid"])
        self.assertTrue(receipt["volume_and_file_id_binding_shape_valid"])
        self.assertTrue(receipt["retained_handle_population_shape_valid"])
        self.assertFalse(receipt["native_provider_reviewed"])
        self.assertFalse(receipt["provider_invocation_authorized"])
        self.assertFalse(receipt["operating_system_evidence_verified"])
        self.assertFalse(receipt["blender_execution_authorized"])
        self.assertFalse(receipt["body_created"])

    def test_safe_record_redacts_paths_handles_and_private_values(self) -> None:
        record = self.fixture.response.safe_record()
        serialized = json.dumps(dict(record), sort_keys=True)
        self.assertNotIn("C:\\\\", serialized)
        self.assertNotIn(str(PROJECT_ROOT), serialized)
        self.assertNotIn("final_normalized_path", serialized)
        self.assertNotIn("native_token", serialized)
        self.assertNotIn("body_owner", serialized)
        self.assertNotIn("person_id", serialized)

    def test_evidence_instances_reject_safe_record_method_shadowing(self) -> None:
        path = self.fixture.response.targets[0].target
        target = self.fixture.response.targets[0]
        response = self.fixture.response
        forged_path = dict(path.safe_record())
        forged_path["file_id_query_source"] = "path_lookup"
        forged_path["body_created"] = True
        for value, forged in (
            (path, forged_path),
            (target, {"target": forged_path}),
            (response, {"body_created": True, "targets": []}),
        ):
            with self.subTest(type=type(value).__name__), self.assertRaises(
                (AttributeError, TypeError)
            ):
                object.__setattr__(
                    value,
                    "safe_record",
                    lambda forged=forged: forged,
                )
            self.assertFalse(hasattr(value, "__dict__"))
        record = dict(
            evidence.NativeNamespaceEvidenceResponse.safe_record(response)
        )
        self.assertFalse(record["body_created"])
        self.assertEqual(
            evidence.FILE_ID_QUERY_SOURCE,
            record["targets"][0]["target"]["file_id_query_source"],
        )

    def test_request_safe_record_shadow_is_never_dispatched(self) -> None:
        object.__setattr__(
            self.bound_request,
            "safe_record",
            lambda: (_ for _ in ()).throw(
                AssertionError("injected request serializer was dispatched")
            ),
        )
        receipt = self.validate_response(
            self.fixture.response,
            self.bound_request,
        )
        self.assertFalse(receipt["body_created"])

    def test_request_authority_rewrite_cannot_hide_behind_safe_record_shadow(
        self,
    ) -> None:
        original_record = transaction.NativeCarrierTransactionRequest.safe_record(
            self.bound_request
        )
        forged_authority = {
            key: False for key in transaction.AUTHORITY_KEYS
        }
        forged_authority["provider_invocation_authorized"] = True
        object.__setattr__(
            self.bound_request,
            "authority",
            MappingProxyType(forged_authority),
        )
        object.__setattr__(
            self.bound_request,
            "safe_record",
            lambda: original_record,
        )
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "transaction request authority must remain false",
        ):
            self.validate_response(
                self.fixture.response,
                self.bound_request,
            )

    def test_all_request_string_subclasses_fail_before_equality_or_hashing(
        self,
    ) -> None:
        fields = (
            "schema",
            "status",
            "provider_id",
            "interface_version",
            "operation",
            "run_id",
            "candidate_id",
            "source_closure_schema",
            "source_closure_status",
            "source_closure_sha256",
            "input_closure_sha256",
            "output_closure_sha256",
            "source_single_launch_interface",
            "environment_block_sha256",
            "working_directory",
            "working_directory_sha256",
            "expected_blender_image_sha256",
            "expected_blender_image_path_sha256",
            "expected_blender_image_canonical_path_sha256",
            "directory_chain_sha256",
            "claim_root_path",
            "claim_root_path_sha256",
            "claim_root_canonical_path_sha256",
            "claim_path",
            "claim_path_sha256",
            "claim_canonical_path_sha256",
            "outcome_path",
            "outcome_path_sha256",
            "outcome_canonical_path_sha256",
            "durability_contract_sha256",
        )
        for field_name in fields:
            original = getattr(self.bound_request, field_name)
            with self.subTest(field=field_name):
                object.__setattr__(
                    self.bound_request,
                    field_name,
                    _Evil(str(original)),
                )
                try:
                    with self.assertRaisesRegex(
                        evidence.NativeNamespaceEvidenceContractError,
                        "type differs",
                    ):
                        self.validate_response(
                            self.fixture.response,
                            self.bound_request,
                        )
                finally:
                    object.__setattr__(self.bound_request, field_name, original)

    def test_stage_identity_subclasses_fail_before_membership_or_lookup(self) -> None:
        stage = self.bound_request.stages[0]
        mutations = (
            ("schema", _Evil(str(stage.schema))),
            ("stage_id", _EvilHash("forged-stage", "build")),
            ("worker_role", _EvilHash("forged-worker", "build_worker")),
            ("argv_sha256", _Evil(str(stage.argv_sha256))),
            (
                "command_line_sha256",
                _Evil(str(stage.command_line_sha256)),
            ),
            ("ordinal", _EvilInt(stage.ordinal)),
            (
                "command",
                (
                    _Evil(str(stage.command[0])),
                    *stage.command[1:],
                ),
            ),
        )
        for field_name, forged in mutations:
            original = getattr(stage, field_name)
            with self.subTest(field=field_name):
                object.__setattr__(stage, field_name, forged)
                try:
                    with self.assertRaises(
                        evidence.NativeNamespaceEvidenceContractError
                    ):
                        self.validate_response(
                            self.fixture.response,
                            self.bound_request,
                        )
                finally:
                    object.__setattr__(stage, field_name, original)

    def test_output_identity_subclasses_fail_before_membership_or_lookup(self) -> None:
        output = self.bound_request.outputs[0]
        mutations = (
            ("schema", _Evil(str(output.schema))),
            ("role", _EvilHash("forged-role", str(output.role))),
            (
                "custody_phase",
                _EvilHash("forged-phase", str(output.custody_phase)),
            ),
            ("path", _Evil(str(output.path))),
            ("path_sha256", _Evil(str(output.path_sha256))),
            (
                "canonical_path_sha256",
                _Evil(str(output.canonical_path_sha256)),
            ),
        )
        for field_name, forged in mutations:
            original = getattr(output, field_name)
            with self.subTest(field=field_name):
                object.__setattr__(output, field_name, forged)
                try:
                    with self.assertRaises(
                        evidence.NativeNamespaceEvidenceContractError
                    ):
                        self.validate_response(
                            self.fixture.response,
                            self.bound_request,
                        )
                finally:
                    object.__setattr__(output, field_name, original)

    def test_request_container_and_scalar_subclasses_fail_before_rebuild(self) -> None:
        original_source = self.bound_request.source_closure_canonical_json
        object.__setattr__(
            self.bound_request,
            "source_closure_canonical_json",
            _EvilBytes(original_source),
        )
        try:
            with self.assertRaisesRegex(
                evidence.NativeNamespaceEvidenceContractError,
                "source closure bytes type differs",
            ):
                self.validate_response(
                    self.fixture.response,
                    self.bound_request,
                )
        finally:
            object.__setattr__(
                self.bound_request,
                "source_closure_canonical_json",
                original_source,
            )

        original_bytes = self.bound_request.expected_blender_image_bytes
        object.__setattr__(
            self.bound_request,
            "expected_blender_image_bytes",
            _EvilInt(original_bytes),
        )
        try:
            with self.assertRaisesRegex(
                evidence.NativeNamespaceEvidenceContractError,
                "byte count type differs",
            ):
                self.validate_response(
                    self.fixture.response,
                    self.bound_request,
                )
        finally:
            object.__setattr__(
                self.bound_request,
                "expected_blender_image_bytes",
                original_bytes,
            )

        for field_name in ("stages", "outputs", "transaction_phases"):
            original = getattr(self.bound_request, field_name)
            object.__setattr__(self.bound_request, field_name, _EvilTuple(original))
            try:
                with self.subTest(field=field_name), self.assertRaises(
                    evidence.NativeNamespaceEvidenceContractError
                ):
                    self.validate_response(
                        self.fixture.response,
                        self.bound_request,
                    )
            finally:
                object.__setattr__(self.bound_request, field_name, original)

        original_phases = self.bound_request.transaction_phases
        object.__setattr__(
            self.bound_request,
            "transaction_phases",
            (
                _EvilHash("forged-transaction-phase", original_phases[0]),
                *original_phases[1:],
            ),
        )
        try:
            with self.assertRaisesRegex(
                evidence.NativeNamespaceEvidenceContractError,
                "phase sequence entries differ",
            ):
                self.validate_response(
                    self.fixture.response,
                    self.bound_request,
                )
        finally:
            object.__setattr__(
                self.bound_request,
                "transaction_phases",
                original_phases,
            )

        for field_name in (
            "directory_paths",
            "directory_path_sha256",
            "directory_canonical_path_sha256",
        ):
            original = getattr(self.bound_request, field_name)
            object.__setattr__(
                self.bound_request,
                field_name,
                (_Evil(str(original[0])), *original[1:]),
            )
            try:
                with self.subTest(field=field_name), self.assertRaisesRegex(
                    evidence.NativeNamespaceEvidenceContractError,
                    "entries differ",
                ):
                    self.validate_response(
                        self.fixture.response,
                        self.bound_request,
                    )
            finally:
                object.__setattr__(self.bound_request, field_name, original)

    def test_mapping_subclass_keys_fail_before_hash_membership(self) -> None:
        original_authority = self.bound_request.authority
        authority_target = transaction.AUTHORITY_KEYS[0]
        forged_authority: dict[str, bool] = {
            _EvilHash("forged-authority-key", authority_target): False
        }
        forged_authority.update(
            {
                key: False
                for key in transaction.AUTHORITY_KEYS
                if key != authority_target
            }
        )
        object.__setattr__(
            self.bound_request,
            "authority",
            MappingProxyType(forged_authority),
        )
        try:
            with self.assertRaisesRegex(
                evidence.NativeNamespaceEvidenceContractError,
                "authority entries differ",
            ):
                self.validate_response(
                    self.fixture.response,
                    self.bound_request,
                )
        finally:
            object.__setattr__(
                self.bound_request,
                "authority",
                original_authority,
            )

        original_environment = self.bound_request.environment
        environment_items = tuple(original_environment.items())
        first_key, first_value = environment_items[0]
        forged_environment: dict[str, str] = {
            _EvilHash("forged-environment-key", first_key): first_value
        }
        forged_environment.update(dict(environment_items[1:]))
        object.__setattr__(
            self.bound_request,
            "environment",
            MappingProxyType(forged_environment),
        )
        try:
            with self.assertRaisesRegex(
                evidence.NativeNamespaceEvidenceContractError,
                "environment entries differ",
            ):
                self.validate_response(
                    self.fixture.response,
                    self.bound_request,
                )
        finally:
            object.__setattr__(
                self.bound_request,
                "environment",
                original_environment,
            )

        forged_environment_value = dict(environment_items)
        forged_environment_value[first_key] = _Evil(str(first_value))
        object.__setattr__(
            self.bound_request,
            "environment",
            MappingProxyType(forged_environment_value),
        )
        try:
            with self.assertRaisesRegex(
                evidence.NativeNamespaceEvidenceContractError,
                "environment entries differ",
            ):
                self.validate_response(
                    self.fixture.response,
                    self.bound_request,
                )
        finally:
            object.__setattr__(
                self.bound_request,
                "environment",
                original_environment,
            )

    def test_mapping_proxy_rejects_hostile_backing_before_dispatch(self) -> None:
        for field_name in ("environment", "authority"):
            original = getattr(self.bound_request, field_name)
            hostile = _EvilMapping()
            proxy = MappingProxyType(hostile)
            self.assertEqual([], hostile.calls)
            object.__setattr__(self.bound_request, field_name, proxy)
            try:
                with self.subTest(field=field_name), self.assertRaisesRegex(
                    evidence.NativeNamespaceEvidenceContractError,
                    "backing must be an exact built-in dict",
                ):
                    self.validate_response(
                        self.fixture.response,
                        self.bound_request,
                    )
                self.assertEqual([], hostile.calls)
            finally:
                object.__setattr__(self.bound_request, field_name, original)

    def test_capsule_ignores_postbind_caller_mutation(self) -> None:
        capsule = self.fixture.request_capsule
        environment_referents = gc.get_referents(self.bound_request.environment)
        authority_referents = gc.get_referents(self.bound_request.authority)
        self.assertEqual(1, len(environment_referents))
        self.assertEqual(1, len(authority_referents))
        environment = environment_referents[0]
        authority = authority_referents[0]
        self.assertIs(dict, type(environment))
        self.assertIs(dict, type(authority))
        original_environment = dict.copy(environment)
        original_authority = dict.copy(authority)
        first = dict(
            self.validate_response(
                self.fixture.response,
                capsule,
            )
        )
        try:
            dict.__setitem__(environment, "PATH", r"Z:\CallerChangedAfterBind")
            dict.__setitem__(
                authority,
                "provider_invocation_authorized",
                True,
            )
            object.__setattr__(
                self.bound_request,
                "provider_id",
                _Evil(PROVIDER_ID),
            )
            second = dict(
                self.validate_response(
                    self.fixture.response,
                    capsule,
                )
            )
            self.assertEqual(first, second)
            self.assertTrue(second["opaque_transaction_request_capsule_bound"])
            self.assertFalse(
                second["caller_owned_request_graph_reused_after_binding"]
            )
            self.assertFalse(
                second["caller_owned_mapping_backing_reused_after_binding"]
            )
            self.assertFalse(second["provider_invocation_authorized"])
            self.assertFalse(second["body_created"])
        finally:
            dict.clear(environment)
            dict.update(environment, original_environment)
            dict.clear(authority)
            dict.update(authority, original_authority)
            object.__setattr__(self.bound_request, "provider_id", PROVIDER_ID)

    def test_capsule_is_stable_during_concurrent_caller_backing_flips(self) -> None:
        capsule = self.fixture.request_capsule
        environment = gc.get_referents(self.bound_request.environment)[0]
        authority = gc.get_referents(self.bound_request.authority)[0]
        self.assertIs(dict, type(environment))
        self.assertIs(dict, type(authority))
        original_environment = dict.copy(environment)
        original_authority = dict.copy(authority)
        started = Event()
        stop = Event()

        def flip() -> None:
            started.set()
            while not stop.is_set():
                dict.__setitem__(environment, "PATH", r"Z:\ConcurrentCaller")
                dict.__setitem__(
                    authority,
                    "provider_invocation_authorized",
                    True,
                )
                dict.__setitem__(environment, "PATH", original_environment["PATH"])
                dict.__setitem__(
                    authority,
                    "provider_invocation_authorized",
                    False,
                )

        worker = Thread(target=flip)
        worker.start()
        self.assertTrue(started.wait(timeout=5))
        try:
            receipts = [
                dict(
                    self.validate_response(
                        self.fixture.response,
                        capsule,
                    )
                )
                for _ in range(24)
            ]
            self.assertTrue(all(value == receipts[0] for value in receipts))
            self.assertFalse(receipts[0]["provider_invocation_authorized"])
            self.assertFalse(receipts[0]["body_created"])
        finally:
            stop.set()
            worker.join(timeout=5)
            dict.clear(environment)
            dict.update(environment, original_environment)
            dict.clear(authority)
            dict.update(authority, original_authority)
        self.assertFalse(worker.is_alive())

    def test_capsule_uses_captured_canonical_gc_builtin(self) -> None:
        calls: list[object] = []
        original = gc.get_referents

        def hostile_get_referents(value: object) -> list[object]:
            calls.append(value)
            raise AssertionError("mutable gc module dispatch was used")

        gc.get_referents = hostile_get_referents  # type: ignore[assignment]
        try:
            capsule = evidence.bind_native_namespace_transaction_request(
                self.bound_request
            )
        finally:
            gc.get_referents = original  # type: ignore[assignment]
        self.assertEqual([], calls)
        receipt = self.validate_response(
            self.fixture.response,
            capsule,
        )
        self.assertTrue(receipt["opaque_transaction_request_capsule_bound"])
        self.assertFalse(receipt["provider_invocation_authorized"])

    def test_capsule_has_no_importable_issuer_resolver_or_bypass_validator(
        self,
    ) -> None:
        hidden_names = (
            "_build_transaction_request_capsule_boundary",
            "_install_transaction_request_capsule",
            "_resolve_transaction_request_capsule",
            "_resolve_transaction_request_input",
            "_wrap_transaction_request_capsule_validator",
            "_validate_resolved_native_namespace_evidence_response",
        )
        for name in hidden_names:
            with self.subTest(name=name):
                self.assertFalse(hasattr(evidence, name))

        with self.assertRaises(TypeError):
            evidence.bind_native_namespace_transaction_request(  # type: ignore[call-arg]
                {},
                self.bound_request,
                "0" * 64,
            )

    def test_public_validator_rejects_raw_request_before_response_dispatch(
        self,
    ) -> None:
        class ExplosiveResponse:
            def __getattribute__(self, name: str) -> object:
                raise AssertionError(f"response dispatch occurred: {name}")

        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "transaction request capsule type differs",
        ):
            evidence.validate_native_namespace_evidence_response(  # type: ignore[arg-type]
                ExplosiveResponse(),
                self.bound_request,
            )

    def test_capsule_direct_construction_and_closure_seal_forgery_fail(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "trusted binder",
        ):
            evidence.NativeNamespaceTransactionRequestCapsule()

        real = self.fixture.request_capsule
        trusted_seal = object.__getattribute__(real, "_seal")

        def attacker_closure_issue(seal: object):
            def issue():
                capsule = object.__new__(
                    evidence.NativeNamespaceTransactionRequestCapsule
                )
                object.__setattr__(capsule, "_seal", seal)
                return capsule

            return issue()

        for seal in (object(), trusted_seal):
            forged = attacker_closure_issue(seal)
            with self.subTest(
                digest_shared_seal=seal is trusted_seal
            ), self.assertRaisesRegex(
                evidence.NativeNamespaceEvidenceContractError,
                "snapshot is unavailable",
            ):
                _ = forged.request_sha256
            with self.subTest(shared_seal=seal is trusted_seal), self.assertRaisesRegex(
                evidence.NativeNamespaceEvidenceContractError,
                "snapshot is unavailable",
            ):
                self.validate_response(
                    self.fixture.response,
                    forged,
                )

        object.__setattr__(real, "_seal", object())
        try:
            with self.assertRaisesRegex(
                evidence.NativeNamespaceEvidenceContractError,
                "capsule seal differs",
            ):
                self.validate_response(
                    self.fixture.response,
                    real,
                )
        finally:
            object.__setattr__(real, "_seal", trusted_seal)
        self.assertFalse(hasattr(real, "__dict__"))

    def test_response_graph_identity_subclasses_fail_before_comparison(self) -> None:
        response_mutations = (
            ("schema", _Evil(str(self.fixture.response.schema))),
            ("status", _Evil(str(self.fixture.response.status))),
            (
                "interface_version",
                _Evil(str(self.fixture.response.interface_version)),
            ),
            (
                "provider_claimed_terminal_state",
                _EvilHash("forged-terminal", "succeeded"),
            ),
        )
        for field_name, forged in response_mutations:
            original = getattr(self.fixture.response, field_name)
            with self.subTest(response_field=field_name):
                object.__setattr__(self.fixture.response, field_name, forged)
                try:
                    with self.assertRaises(
                        evidence.NativeNamespaceEvidenceContractError
                    ):
                        self.validate_response(
                            self.fixture.response,
                            self.bound_request,
                        )
                finally:
                    object.__setattr__(self.fixture.response, field_name, original)

        target = self.fixture.response.targets[0]
        for field_name, forged in (
            ("schema", _Evil(str(target.schema))),
            ("role", _EvilHash("forged-target-role", str(target.role))),
        ):
            original = getattr(target, field_name)
            with self.subTest(target_field=field_name):
                object.__setattr__(target, field_name, forged)
                try:
                    with self.assertRaises(
                        evidence.NativeNamespaceEvidenceContractError
                    ):
                        self.validate_response(
                            self.fixture.response,
                            self.bound_request,
                        )
                finally:
                    object.__setattr__(target, field_name, original)

        path = target.target
        for field_name, forged in (
            ("schema", _Evil(str(path.schema))),
            ("kind", _EvilHash("forged-kind", str(path.kind))),
            (
                "file_id_query_source",
                _EvilHash("forged-query-source", evidence.FILE_ID_QUERY_SOURCE),
            ),
        ):
            original = getattr(path, field_name)
            with self.subTest(path_field=field_name):
                object.__setattr__(path, field_name, forged)
                try:
                    with self.assertRaises(
                        evidence.NativeNamespaceEvidenceContractError
                    ):
                        self.validate_response(
                            self.fixture.response,
                            self.bound_request,
                        )
                finally:
                    object.__setattr__(path, field_name, original)

    def test_normalized_long_path_must_equal_requested_canonical_path(self) -> None:
        short_request = self.request(working_directory=r"C:\PROGRA~1")
        fixture = _EvidenceFixture(short_request)
        target = fixture.response.targets[1]
        long_path = r"C:\Program Files"
        normalized = fixture.object(
            long_path,
            "directory",
            reuse=False,
        )
        mutated = replace(target, target=normalized)
        response = replace(
            fixture.response,
            targets=(fixture.response.targets[0], mutated, *fixture.response.targets[2:]),
        )
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "target binding differs",
        ):
            self.validate_response(response, short_request)

    def test_reparse_or_hardlink_claims_fail_at_construction(self) -> None:
        target = self.fixture.response.targets[-1].target
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "reparse_point",
        ):
            replace(target, reparse_point=True)
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "reparse tag",
        ):
            replace(target, reparse_tag=0xA0000003)
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "hard-link count",
        ):
            replace(target, link_count=2)

    def test_volume_change_inside_one_ancestry_fails_closed(self) -> None:
        original = self.fixture.response.targets[1]
        changed_target = replace(
            original.target,
            volume_serial_number=original.target.volume_serial_number + 1,
        )
        response = self.response_with_target(1, replace(original, target=changed_target))
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "volume boundary",
        ):
            self.validate_response(
                response,
                self.bound_request,
            )

    def test_distinct_paths_cannot_share_volume_and_file_identity(self) -> None:
        first_index = next(
            index
            for index, target in enumerate(self.fixture.response.targets)
            if target.role == "output:candidate_blend"
        )
        second_index = next(
            index
            for index, target in enumerate(self.fixture.response.targets)
            if target.role == "output:build_report"
        )
        first = self.fixture.response.targets[first_index]
        second = self.fixture.response.targets[second_index]
        aliased_identity = replace(
            second.target,
            volume_serial_number=first.target.volume_serial_number,
            file_id=first.target.file_id,
        )
        response = self.response_with_target(
            second_index,
            replace(second, target=aliased_identity),
        )
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "alias one volume and file identity",
        ):
            self.validate_response(
                response,
                self.bound_request,
            )

    def test_missing_reordered_or_duplicated_ancestor_evidence_fails(self) -> None:
        original = self.fixture.response.targets[1]
        mutations = (
            replace(original, ancestors=original.ancestors[1:]),
            replace(original, ancestors=tuple(reversed(original.ancestors))),
            replace(original, ancestors=(*original.ancestors, original.ancestors[-1])),
        )
        for target in mutations:
            with self.subTest(length=len(target.ancestors)), self.assertRaises(
                evidence.NativeNamespaceEvidenceContractError
            ):
                self.validate_response(
                    self.response_with_target(1, target),
                    self.bound_request,
                )
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "ancestor count exceeds",
        ):
            replace(
                original,
                ancestors=(original.ancestors[0],)
                * (native_contract.MAX_NATIVE_DIRECTORY_HANDLES + 1),
            )

    def test_one_canonical_path_must_reuse_one_evidence_object(self) -> None:
        original = self.fixture.response.targets[1]
        ancestor = original.ancestors[0]
        duplicate = self.fixture.object(
            ancestor.final_normalized_path,
            "directory",
            reuse=False,
        )
        mutated = replace(
            original,
            ancestors=(duplicate, *original.ancestors[1:]),
        )
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "canonical path used multiple evidence objects",
        ):
            self.validate_response(
                self.response_with_target(1, mutated),
                self.bound_request,
            )

    def test_opaque_handle_alias_mixed_close_api_and_early_close_fail(self) -> None:
        first_index = next(
            index
            for index, target in enumerate(self.fixture.response.targets)
            if target.role == "output:candidate_blend"
        )
        second_index = next(
            index
            for index, target in enumerate(self.fixture.response.targets)
            if target.role == "output:build_report"
        )
        first = self.fixture.response.targets[first_index]
        second = self.fixture.response.targets[second_index]
        first_canonical = first.target.final_canonical_path_sha256
        alias = self.fixture.object(
            second.target.final_normalized_path,
            "regular_file",
            byte_count=second.target.bytes,
            content_sha256=second.target.content_sha256,
            file_id=second.target.file_id,
            token=self.fixture.tokens[first_canonical],
            reuse=False,
        )
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "handle tokens alias",
        ):
            self.validate_response(
                self.response_with_target(second_index, replace(second, target=alias)),
                self.bound_request,
            )

        mixed = self.fixture.object(
            second.target.final_normalized_path,
            "regular_file",
            byte_count=second.target.bytes,
            content_sha256=second.target.content_sha256,
            file_id=second.target.file_id,
            close_api=_CloseApi(),
            reuse=False,
        )
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "close APIs differ",
        ):
            self.validate_response(
                self.response_with_target(second_index, replace(second, target=mixed)),
                self.bound_request,
            )

        first.target.handle.close()
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "closed early",
        ):
            self.validate_response(
                self.fixture.response,
                self.bound_request,
            )

    def test_handle_kind_drift_after_construction_fails_closed(self) -> None:
        handle = self.fixture.response.targets[0].target.handle
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "write-once",
        ):
            handle._kind = "directory"  # type: ignore[misc]
        object.__setattr__(handle, "_kind", "directory")
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "identity changed after construction",
        ):
            self.validate_response(
                self.fixture.response,
                self.bound_request,
            )

    def test_handle_provider_drift_after_construction_fails_closed(self) -> None:
        handle = self.fixture.response.targets[0].target.handle
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "write-once",
        ):
            handle._provider_id = "other_review_provider_v1"  # type: ignore[misc]
        object.__setattr__(
            handle,
            "_provider_id",
            "other_review_provider_v1",
        )
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "identity changed after construction",
        ):
            self.validate_response(
                self.fixture.response,
                self.bound_request,
            )

    def test_unique_handle_token_substitution_fails_closed(self) -> None:
        handle = self.fixture.response.targets[0].target.handle
        replacement = _FakeToken()
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "write-once",
        ):
            handle._native_token = replacement  # type: ignore[misc]
        object.__setattr__(handle, "_native_token", replacement)
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "identity changed after construction",
        ):
            self.validate_response(
                self.fixture.response,
                self.bound_request,
            )

    def test_closed_handle_cannot_be_reset_to_open(self) -> None:
        handle = self.fixture.response.targets[0].target.handle
        handle.close()
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "write-once",
        ):
            handle._closed = False  # type: ignore[misc]
        object.__setattr__(handle, "_closed", False)
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "lifetime state differs",
        ):
            self.validate_response(
                self.fixture.response,
                self.bound_request,
            )

    def test_coherent_close_api_substitution_fails_closed(self) -> None:
        replacement = _CloseApi()
        handles = {
            id(value.handle): value.handle
            for target in self.fixture.response.targets
            for value in (*target.ancestors, target.target)
        }
        first = next(iter(handles.values()))
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "write-once",
        ):
            first._close_api = replacement  # type: ignore[misc]
        for handle in handles.values():
            object.__setattr__(handle, "_close_api", replacement)
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "identity changed after construction",
        ):
            self.validate_response(
                self.fixture.response,
                self.bound_request,
            )

    def test_external_snapshot_rejects_coherent_token_api_and_fake_seal(self) -> None:
        replacement_close_api = _CloseApi()
        handles = {
            id(value.handle): value.handle
            for target in self.fixture.response.targets
            for value in (*target.ancestors, target.target)
        }
        for handle in handles.values():
            replacement_token = _FakeToken()
            object.__setattr__(handle, "_native_token", replacement_token)
            object.__setattr__(handle, "_close_api", replacement_close_api)
            with self.assertRaises(AttributeError):
                object.__setattr__(
                    handle,
                    "_identity_seal",
                    (
                        handle._provider_id,
                        handle._kind,
                        replacement_token,
                        replacement_close_api,
                    ),
                )
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "identity changed after construction",
        ):
            self.validate_response(
                self.fixture.response,
                self.bound_request,
            )

    def test_external_snapshot_rejects_coherent_closed_epoch_reset(self) -> None:
        handle = self.fixture.response.targets[0].target.handle
        close_api = handle._close_api
        handle.close()
        self.assertEqual(1, len(close_api.closed))
        object.__setattr__(handle, "_closed", False)
        object.__setattr__(handle, "_close_epoch", 0)
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "lifetime state differs",
        ):
            self.validate_response(
                self.fixture.response,
                self.bound_request,
            )
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "lifetime state differs",
        ):
            handle.close()
        self.assertEqual(1, len(close_api.closed))

    def test_external_snapshot_rejects_coherent_kind_substitution(self) -> None:
        value = self.fixture.response.targets[0].target
        handle = value.handle
        object.__setattr__(value, "kind", "directory")
        object.__setattr__(value, "bytes", 0)
        object.__setattr__(value, "content_sha256", evidence.ZERO_SHA256)
        object.__setattr__(handle, "_kind", "directory")
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "identity changed after construction",
        ):
            self.validate_response(
                self.fixture.response,
                self.bound_request,
            )

    def test_external_snapshot_rejects_coherent_provider_substitution(self) -> None:
        replacement_provider = "coherent_replacement_provider_v1"
        object.__setattr__(self.bound_request, "provider_id", replacement_provider)
        object.__setattr__(self.fixture.response, "provider_id", replacement_provider)
        for target in self.fixture.response.targets:
            object.__setattr__(target, "provider_id", replacement_provider)
            for value in (*target.ancestors, target.target):
                object.__setattr__(value, "provider_id", replacement_provider)
                object.__setattr__(
                    value.handle,
                    "_provider_id",
                    replacement_provider,
                )
        object.__setattr__(
            self.fixture.response,
            "request_sha256",
            native_contract.canonical_sha256(self.bound_request.safe_record()),
        )
        with self.assertRaises(evidence.NativeNamespaceEvidenceContractError):
            self.validate_response(
                self.fixture.response,
                self.bound_request,
            )

    def test_external_snapshot_rejects_postconstruction_query_source(self) -> None:
        value = self.fixture.response.targets[0].target
        object.__setattr__(value, "file_id_query_source", "path_lookup")
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "file id query source differs",
        ):
            self.validate_response(
                self.fixture.response,
                self.bound_request,
            )
        with self.assertRaises(evidence.NativeNamespaceEvidenceContractError):
            self.fixture.response.safe_record()

    def test_external_snapshot_rejects_postconstruction_authority(self) -> None:
        for field_name in (
            "provider_reviewed",
            "operating_system_evidence_verified",
            "body_created",
        ):
            with self.subTest(field=field_name):
                fixture = _EvidenceFixture(self.bound_request)
                object.__setattr__(fixture.response, field_name, True)
                with self.assertRaisesRegex(
                    evidence.NativeNamespaceEvidenceContractError,
                    field_name,
                ):
                    self.validate_response(
                        fixture.response,
                        self.bound_request,
                    )
                with self.assertRaises(
                    evidence.NativeNamespaceEvidenceContractError
                ):
                    fixture.response.safe_record()

    def test_failed_close_state_is_monotonic_and_never_retried(self) -> None:
        for close_api, first_error in (
            (_RejectingCloseApi(), "not exactly successful"),
            (_RaisingCloseApi(), "close raised"),
        ):
            with self.subTest(close_api=type(close_api).__name__):
                handle = evidence.RetainedNamespaceHandle(
                    provider_id=PROVIDER_ID,
                    kind="regular_file",
                    native_token=_FakeToken(),
                    close_api=close_api,
                )
                with self.assertRaisesRegex(
                    evidence.NativeNamespaceEvidenceContractError,
                    first_error,
                ):
                    handle.close()
                with self.assertRaisesRegex(
                    evidence.NativeNamespaceEvidenceContractError,
                    "lifetime state differs",
                ):
                    handle.close()
                self.assertEqual(1, close_api.calls)

    def test_external_snapshot_retains_and_rejects_cloned_child_identity(self) -> None:
        target = next(
            value
            for value in self.fixture.response.targets
            if value.role == "output:candidate_blend"
        )
        original = target.target
        original_reference = weakref.ref(original)
        clone = replace(original)
        self.fixture.objects.pop(original.final_canonical_path_sha256)
        object.__setattr__(target, "target", clone)
        del original
        gc.collect()
        self.assertIsNotNone(original_reference())
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "trusted target evidence construction snapshot differs",
        ):
            self.validate_response(
                self.fixture.response,
                self.bound_request,
            )

    def test_exact_string_checks_reject_equality_spoofing_objects(self) -> None:
        object.__setattr__(self.fixture.response, "status", _EqualitySpoof())
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "response status differs",
        ):
            self.validate_response(
                self.fixture.response,
                self.bound_request,
            )

        fixture = _EvidenceFixture(self.bound_request)
        object.__setattr__(
            fixture.response.targets[0].target,
            "final_path_sha256",
            _EqualitySpoof(),
        )
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "lowercase SHA-256",
        ):
            self.validate_response(
                fixture.response,
                self.bound_request,
            )

    def test_reinitialization_cannot_overwrite_external_handle_snapshot(self) -> None:
        handle = self.fixture.response.targets[0].target.handle
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "construction snapshot already exists",
        ):
            handle.__init__(
                provider_id=PROVIDER_ID,
                kind="regular_file",
                native_token=_FakeToken(),
                close_api=_CloseApi(),
            )
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "identity changed after construction",
        ):
            self.validate_response(
                self.fixture.response,
                self.bound_request,
            )

    def test_concurrent_close_has_one_native_call_and_monotonic_result(self) -> None:
        close_api = _BlockingCloseApi()
        handle = evidence.RetainedNamespaceHandle(
            provider_id=PROVIDER_ID,
            kind="regular_file",
            native_token=_FakeToken(),
            close_api=close_api,
        )
        worker_errors: list[BaseException] = []

        def close_in_worker() -> None:
            try:
                handle.close()
            except BaseException as exc:
                worker_errors.append(exc)

        worker = Thread(target=close_in_worker)
        worker.start()
        self.assertTrue(close_api.started.wait(timeout=5))
        try:
            with self.assertRaisesRegex(
                evidence.NativeNamespaceEvidenceContractError,
                "lifetime state differs",
            ):
                handle.close()
        finally:
            close_api.release.set()
        worker.join(timeout=5)
        self.assertFalse(worker.is_alive())
        self.assertEqual([], worker_errors)
        self.assertEqual(1, close_api.calls)
        self.assertTrue(handle.closed)

    def test_query_source_and_authority_mutations_fail_closed(self) -> None:
        target = self.fixture.response.targets[0].target
        with self.assertRaisesRegex(
            evidence.NativeNamespaceEvidenceContractError,
            "file id query source differs",
        ):
            replace(target, file_id_query_source="path_lookup")
        for field_name in (
            "provider_reviewed",
            "operating_system_evidence_verified",
            "body_created",
        ):
            with self.subTest(field=field_name), self.assertRaises(
                evidence.NativeNamespaceEvidenceContractError
            ):
                replace(self.fixture.response, **{field_name: True})

    def test_static_contract_keeps_controller_and_execution_boundary_closed(self) -> None:
        record = evidence.static_contract_evidence_record()
        self.assertEqual(frozenset(), preimport.REVIEWED_NATIVE_PROVIDER_IDS)
        self.assertTrue(record["complete_ancestor_chains_required"])
        self.assertTrue(record["single_link_required"])
        self.assertTrue(record["local_fixed_volume_required"])
        self.assertEqual(
            evidence.PYTHON_OBJECT_GRAPH_THREAT_MODEL,
            record["python_object_graph_threat_model"],
        )
        self.assertTrue(record["trusted_snapshots_external_to_response_graph"])
        self.assertTrue(
            record["coherent_object_setattr_rewrite_rejection_required"]
        )
        self.assertTrue(record["evidence_instances_slotted_without_instance_dict"])
        self.assertTrue(record["canonical_module_serializers_required"])
        self.assertFalse(record["untrusted_instance_serializer_dispatch_used"])
        self.assertTrue(
            record["transaction_request_declared_field_rebuild_required"]
        )
        self.assertTrue(
            record["opaque_transaction_request_capsule_binding_required"]
        )
        self.assertFalse(record["raw_transaction_request_validation_accepted"])
        self.assertFalse(record["capsule_issuer_or_resolver_exposed"])
        self.assertFalse(
            record["caller_owned_request_graph_reused_after_binding"]
        )
        self.assertFalse(
            record["caller_owned_mapping_backing_reused_after_binding"]
        )
        self.assertTrue(record["mapping_proxy_exact_dict_snapshot_required"])
        self.assertTrue(
            record["captured_canonical_gc_referents_builtin_required"]
        )
        self.assertTrue(
            record["exact_builtin_type_gates_before_equality_hash_or_lookup"]
        )
        self.assertFalse(record["short_name_alias_identity_verified"])
        self.assertFalse(record["reparse_identity_verified"])
        self.assertFalse(record["hardlink_identity_verified"])
        self.assertFalse(record["volume_and_file_id_identity_verified"])
        self.assertFalse(record["real_native_handle_lifetime_verified"])
        self.assertFalse(record["arbitrary_in_process_python_isolation_verified"])
        self.assertFalse(record["module_or_closure_reflection_resistance_verified"])
        self.assertFalse(record["native_provider_reviewed"])
        self.assertFalse(record["provider_invocation_authorized"])
        self.assertFalse(record["operating_system_evidence_verified"])
        self.assertFalse(record["blender_execution_authorized"])
        self.assertFalse(record["body_created"])


if __name__ == "__main__":
    unittest.main()
