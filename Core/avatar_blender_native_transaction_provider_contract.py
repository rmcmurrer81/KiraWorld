"""Inert request contract for one durable native Blender carrier transaction.

The existing ``avatar_blender_native_provider_contract`` describes one
suspended native launch.  A carrier attempt cannot safely be split into two
independent launches: its build and audit must share one durable claim,
retained input/output custody, one ordered phase sequence, and exactly one
terminal outcome.

This module closes only the request-side interface gap.  It does not call a
provider or native API, create a claim or authorization, start Blender, write
an output, or grant authority.  Private command/path/environment values stay
inside the frozen request object; its review record contains digests only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import PureWindowsPath
import re
from types import MappingProxyType
from typing import Any, Mapping, Protocol, Sequence

from Core import avatar_blender_carrier_transaction_closure as closure
from Core import avatar_blender_native_provider_contract as launch_contract


NATIVE_TRANSACTION_PROVIDER_INTERFACE = (
    "kira.blender_native_carrier_transaction_provider.v1"
)
NATIVE_TRANSACTION_REQUEST_SCHEMA = (
    "kira.blender_native_carrier_transaction_request.v1"
)
NATIVE_TRANSACTION_STAGE_SCHEMA = (
    "kira.blender_native_carrier_transaction_stage_request.v1"
)
NATIVE_TRANSACTION_OUTPUT_SCHEMA = (
    "kira.blender_native_carrier_transaction_output_reservation.v1"
)
NATIVE_TRANSACTION_STATIC_STATUS = (
    "STATIC_TWO_STAGE_PROVIDER_REQUEST_VALID_ONLY_NO_NATIVE_AUTHORITY"
)
NATIVE_TRANSACTION_OPERATION = "build_then_audit_one_durable_transaction"
STAGE_ORDER = ("build", "audit")
STAGE_WORKER_ROLES = MappingProxyType(
    {"build": "build_worker", "audit": "audit_worker"}
)
OUTPUT_CUSTODY_PHASES = MappingProxyType(
    {
        "one_run_authorization": "transaction_setup",
        "candidate_blend": "build",
        "build_report": "build",
        "audit_report": "audit",
    }
)
OUTPUT_ORDER = tuple(OUTPUT_CUSTODY_PHASES)
MAX_TRANSACTION_TIMEOUT_MS = 24 * 60 * 60 * 1000
PROVIDER_ID_RE = re.compile(r"^[a-z][a-z0-9_.-]{7,95}$")
RUN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{7,63}$")
DOS_DEVICE_NAMES = frozenset(
    {
        "CON",
        "CONIN$",
        "CONOUT$",
        "CLOCK$",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{index}" for index in range(1, 10)),
        *(f"LPT{index}" for index in range(1, 10)),
        *(f"COM{index}" for index in "¹²³"),
        *(f"LPT{index}" for index in "¹²³"),
    }
)
WIN32_FORBIDDEN_COMPONENT_CHARS = frozenset('<>:"/\\|?*')
ASCII_LOCAL_DRIVE_RE = re.compile(r"^[A-Za-z]:\\")

AUTHORITY_KEYS = (
    "provider_invocation_authorized",
    "native_provider_reviewed",
    "native_provider_implementation_available",
    "operating_system_evidence_verified",
    "blender_execution_authorized",
    "body_build_authorized",
    "body_created",
    "candidate_assignment_authorized",
    "anatomy_authoring_authorized",
    "runtime_activation_authorized",
    "public_export_authorized",
)


class NativeTransactionProviderContractError(ValueError):
    """The inert two-stage provider request differs from the exact contract."""


def _sha256(value: Any, label: str) -> str:
    if type(value) is not str or launch_contract.SHA256_RE.fullmatch(value) is None:
        raise NativeTransactionProviderContractError(
            f"{label} must be lowercase SHA-256"
        )
    return value


def _exact_bool(value: Any, expected: bool, label: str) -> None:
    if type(value) is not bool or value is not expected:
        raise NativeTransactionProviderContractError(
            f"{label} must be exactly {expected}"
        )


def _bounded_int(value: Any, label: str) -> int:
    if (
        type(value) is not int
        or value < 1
        or value > MAX_TRANSACTION_TIMEOUT_MS
    ):
        raise NativeTransactionProviderContractError(f"{label} differs")
    return value


def _provider_id(value: Any) -> str:
    if type(value) is not str or PROVIDER_ID_RE.fullmatch(value) is None:
        raise NativeTransactionProviderContractError("provider_id grammar differs")
    return value


def _run_id(value: Any) -> str:
    if type(value) is not str or RUN_ID_RE.fullmatch(value) is None:
        raise NativeTransactionProviderContractError("run_id grammar differs")
    return value


def _local_path(value: Any, label: str) -> str:
    if type(value) is not str:
        raise NativeTransactionProviderContractError(f"{label} path differs")
    try:
        launch_contract.private_windows_path_sha256(value)
        launch_contract.canonical_windows_path_sha256(value)
    except launch_contract.NativeProviderContractError as exc:
        raise NativeTransactionProviderContractError(
            f"{label} must be a canonical absolute local Windows path"
        ) from exc
    parsed_value = value[4:] if value.startswith("\\\\?\\") else value
    if ASCII_LOCAL_DRIVE_RE.match(parsed_value) is None:
        raise NativeTransactionProviderContractError(
            f"{label} must use an ASCII local drive designator"
        )
    components = PureWindowsPath(parsed_value).parts[1:]
    for component in components:
        device_base = component.split(".", 1)[0].rstrip(" .").upper()
        if (
            component.endswith((".", " "))
            or any(
                character in WIN32_FORBIDDEN_COMPONENT_CHARS
                or ord(character) <= 0x1F
                for character in component
            )
            or device_base in DOS_DEVICE_NAMES
        ):
            raise NativeTransactionProviderContractError(
                f"{label} contains a forbidden Windows path component"
            )
    return value


def _pure_local_path(value: str) -> PureWindowsPath:
    parsed = value[4:] if value.startswith("\\\\?\\") else value
    return PureWindowsPath(parsed)


def _command(value: Any, label: str) -> tuple[str, ...]:
    if type(value) not in {tuple, list} or len(value) != 11:
        raise NativeTransactionProviderContractError(
            f"{label} command must contain exactly eleven entries"
        )
    command = tuple(value)
    if any(type(item) is not str or not item or "\x00" in item for item in command):
        raise NativeTransactionProviderContractError(
            f"{label} command entries differ"
        )
    _local_path(command[0], f"{label} application")
    return command


def _plain_closure_record(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise NativeTransactionProviderContractError("source closure differs")
    record = dict(value)
    try:
        closure.validate_static_transaction_closure_record(record)
    except closure.CarrierTransactionClosureError as exc:
        raise NativeTransactionProviderContractError(
            "source transaction closure is invalid"
        ) from exc
    return record


def _canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise NativeTransactionProviderContractError(
            "source closure is not canonical JSON"
        ) from exc


def _parse_canonical_closure_bytes(value: Any) -> dict[str, Any]:
    if type(value) is not bytes or not value:
        raise NativeTransactionProviderContractError("source closure bytes differ")

    def reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in pairs:
            if type(key) is not str or key in result:
                raise NativeTransactionProviderContractError(
                    "source closure JSON contains a duplicate key"
                )
            result[key] = item
        return result

    def reject_constant(value: str) -> None:
        raise NativeTransactionProviderContractError(
            f"source closure JSON contains non-finite value {value}"
        )

    try:
        parsed = json.loads(
            value.decode("ascii"),
            object_pairs_hook=reject_duplicate_pairs,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise NativeTransactionProviderContractError(
            "source closure bytes are invalid"
        ) from exc
    record = _plain_closure_record(parsed)
    if _canonical_json_bytes(record) != value:
        raise NativeTransactionProviderContractError(
            "source closure bytes are not in canonical form"
        )
    return record


@dataclass(frozen=True)
class NativeTransactionStageRequest:
    """One private launch payload bound to one exact transaction stage."""

    schema: str
    stage_id: str
    ordinal: int
    worker_role: str
    command: tuple[str, ...] = field(repr=False)
    argv_sha256: str
    command_line_sha256: str
    timeout_ms: int
    candidate_custody_required_before_launch: bool
    created_suspended_required: bool
    job_assignment_before_image_check_required: bool
    image_query_from_retained_process_handle_required: bool
    pid_process_identity_forbidden: bool
    exactly_one_resume_required: bool
    completion_required_before_next_phase: bool
    process_execution_authorized: bool

    def __post_init__(self) -> None:
        if self.schema != NATIVE_TRANSACTION_STAGE_SCHEMA:
            raise NativeTransactionProviderContractError("stage schema differs")
        if self.stage_id not in STAGE_ORDER:
            raise NativeTransactionProviderContractError("stage id differs")
        expected_ordinal = STAGE_ORDER.index(self.stage_id)
        if type(self.ordinal) is not int or self.ordinal != expected_ordinal:
            raise NativeTransactionProviderContractError("stage ordinal differs")
        if self.worker_role != STAGE_WORKER_ROLES[self.stage_id]:
            raise NativeTransactionProviderContractError("stage worker role differs")
        command = _command(self.command, self.stage_id)
        if self.argv_sha256 != launch_contract.canonical_sha256(list(command)):
            raise NativeTransactionProviderContractError("stage argv digest differs")
        if (
            self.command_line_sha256
            != launch_contract.windows_command_line_sha256(command)
        ):
            raise NativeTransactionProviderContractError(
                "stage command-line digest differs"
            )
        _bounded_int(self.timeout_ms, "stage timeout")
        _exact_bool(
            self.candidate_custody_required_before_launch,
            self.stage_id == "audit",
            "candidate_custody_required_before_launch",
        )
        for label, value in (
            ("created_suspended_required", self.created_suspended_required),
            (
                "job_assignment_before_image_check_required",
                self.job_assignment_before_image_check_required,
            ),
            (
                "image_query_from_retained_process_handle_required",
                self.image_query_from_retained_process_handle_required,
            ),
            ("pid_process_identity_forbidden", self.pid_process_identity_forbidden),
            ("exactly_one_resume_required", self.exactly_one_resume_required),
            (
                "completion_required_before_next_phase",
                self.completion_required_before_next_phase,
            ),
        ):
            _exact_bool(value, True, label)
        _exact_bool(
            self.process_execution_authorized,
            False,
            "process_execution_authorized",
        )

    def safe_record(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "stage_id": self.stage_id,
            "ordinal": self.ordinal,
            "worker_role": self.worker_role,
            "argv_sha256": self.argv_sha256,
            "command_line_sha256": self.command_line_sha256,
            "timeout_ms": self.timeout_ms,
            "candidate_custody_required_before_launch": (
                self.candidate_custody_required_before_launch
            ),
            "created_suspended_required": True,
            "job_assignment_before_image_check_required": True,
            "image_query_from_retained_process_handle_required": True,
            "pid_process_identity_forbidden": True,
            "exactly_one_resume_required": True,
            "completion_required_before_next_phase": True,
            "process_execution_authorized": False,
        }


@dataclass(frozen=True)
class NativeTransactionOutputReservation:
    """One private create-new output path with transaction-long custody rules."""

    schema: str
    role: str
    custody_phase: str
    path: str = field(repr=False)
    path_sha256: str
    canonical_path_sha256: str
    create_new_required: bool
    initially_absent_required: bool
    handle_retained_from_creation_until_terminal: bool
    validate_from_retained_handle_required: bool
    path_publication_before_terminal: bool

    def __post_init__(self) -> None:
        if self.schema != NATIVE_TRANSACTION_OUTPUT_SCHEMA:
            raise NativeTransactionProviderContractError("output schema differs")
        if self.role not in OUTPUT_CUSTODY_PHASES:
            raise NativeTransactionProviderContractError("output role differs")
        if self.custody_phase != OUTPUT_CUSTODY_PHASES[self.role]:
            raise NativeTransactionProviderContractError("output custody phase differs")
        path = _local_path(self.path, f"{self.role} output")
        if self.path_sha256 != launch_contract.private_windows_path_sha256(path):
            raise NativeTransactionProviderContractError("output path digest differs")
        if (
            self.canonical_path_sha256
            != launch_contract.canonical_windows_path_sha256(path)
        ):
            raise NativeTransactionProviderContractError(
                "output canonical path digest differs"
            )
        for label, value in (
            ("create_new_required", self.create_new_required),
            ("initially_absent_required", self.initially_absent_required),
            (
                "handle_retained_from_creation_until_terminal",
                self.handle_retained_from_creation_until_terminal,
            ),
            (
                "validate_from_retained_handle_required",
                self.validate_from_retained_handle_required,
            ),
        ):
            _exact_bool(value, True, label)
        _exact_bool(
            self.path_publication_before_terminal,
            False,
            "path_publication_before_terminal",
        )

    def safe_record(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "role": self.role,
            "custody_phase": self.custody_phase,
            "path_sha256": self.path_sha256,
            "canonical_path_sha256": self.canonical_path_sha256,
            "create_new_required": True,
            "initially_absent_required": True,
            "handle_retained_from_creation_until_terminal": True,
            "validate_from_retained_handle_required": True,
            "path_publication_before_terminal": False,
        }


@dataclass(frozen=True)
class NativeCarrierTransactionRequest:
    """Frozen request payload for a future reviewed native transaction provider."""

    schema: str
    status: str
    provider_id: str
    interface_version: str
    operation: str
    run_id: str
    candidate_id: str
    source_closure_schema: str
    source_closure_status: str
    source_closure_canonical_json: bytes = field(repr=False)
    source_closure_sha256: str
    input_closure_sha256: str
    output_closure_sha256: str
    source_single_launch_interface: str
    source_single_launch_interface_is_insufficient: bool
    stages: tuple[NativeTransactionStageRequest, ...]
    outputs: tuple[NativeTransactionOutputReservation, ...]
    transaction_phases: tuple[str, ...]
    environment: Mapping[str, str] = field(repr=False)
    environment_block_sha256: str
    working_directory: str = field(repr=False)
    working_directory_sha256: str
    expected_blender_image_bytes: int
    expected_blender_image_sha256: str
    expected_blender_image_path_sha256: str
    expected_blender_image_canonical_path_sha256: str
    directory_paths: tuple[str, ...] = field(repr=False)
    directory_path_sha256: tuple[str, ...]
    directory_canonical_path_sha256: tuple[str, ...]
    directory_chain_sha256: str
    claim_root_path: str = field(repr=False)
    claim_root_path_sha256: str
    claim_root_canonical_path_sha256: str
    claim_path: str = field(repr=False)
    claim_path_sha256: str
    claim_canonical_path_sha256: str
    outcome_path: str = field(repr=False)
    outcome_path_sha256: str
    outcome_canonical_path_sha256: str
    durability_contract_sha256: str
    claim_create_new_required: bool
    claim_payload_and_parent_flush_required: bool
    claim_handle_retained_until_terminal: bool
    outcome_create_new_required: bool
    outcome_payload_and_parent_flush_required: bool
    exactly_one_terminal_outcome_required: bool
    provider_reviewed: bool
    operating_system_evidence_verified: bool
    authority: Mapping[str, bool]

    def __post_init__(self) -> None:
        if type(self.stages) is not tuple or any(
            type(value) is not NativeTransactionStageRequest for value in self.stages
        ):
            raise NativeTransactionProviderContractError("private stage tuple differs")
        if type(self.outputs) is not tuple or any(
            type(value) is not NativeTransactionOutputReservation
            for value in self.outputs
        ):
            raise NativeTransactionProviderContractError("private output tuple differs")
        if type(self.environment) is not MappingProxyType:
            raise NativeTransactionProviderContractError(
                "private environment must be immutable"
            )
        if type(self.directory_paths) is not tuple:
            raise NativeTransactionProviderContractError(
                "private directory tuple differs"
            )
        if type(self.authority) is not MappingProxyType:
            raise NativeTransactionProviderContractError(
                "request authority must be immutable"
            )
        validate_native_transaction_request(self)

    def safe_record(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "status": self.status,
            "provider_id": self.provider_id,
            "interface_version": self.interface_version,
            "operation": self.operation,
            "run_id": self.run_id,
            "candidate_id": self.candidate_id,
            "source_closure_schema": self.source_closure_schema,
            "source_closure_status": self.source_closure_status,
            "source_closure_sha256": self.source_closure_sha256,
            "input_closure_sha256": self.input_closure_sha256,
            "output_closure_sha256": self.output_closure_sha256,
            "source_single_launch_interface": self.source_single_launch_interface,
            "source_single_launch_interface_is_insufficient": (
                self.source_single_launch_interface_is_insufficient
            ),
            "stages": [stage.safe_record() for stage in self.stages],
            "outputs": [output.safe_record() for output in self.outputs],
            "transaction_phases": list(self.transaction_phases),
            "environment_block_sha256": self.environment_block_sha256,
            "working_directory_sha256": self.working_directory_sha256,
            "expected_blender_image_bytes": self.expected_blender_image_bytes,
            "expected_blender_image_sha256": self.expected_blender_image_sha256,
            "expected_blender_image_path_sha256": (
                self.expected_blender_image_path_sha256
            ),
            "expected_blender_image_canonical_path_sha256": (
                self.expected_blender_image_canonical_path_sha256
            ),
            "directory_path_sha256": list(self.directory_path_sha256),
            "directory_canonical_path_sha256": list(
                self.directory_canonical_path_sha256
            ),
            "directory_chain_sha256": self.directory_chain_sha256,
            "claim_root_path_sha256": self.claim_root_path_sha256,
            "claim_root_canonical_path_sha256": (
                self.claim_root_canonical_path_sha256
            ),
            "claim_path_sha256": self.claim_path_sha256,
            "claim_canonical_path_sha256": self.claim_canonical_path_sha256,
            "outcome_path_sha256": self.outcome_path_sha256,
            "outcome_canonical_path_sha256": self.outcome_canonical_path_sha256,
            "durability_contract_sha256": self.durability_contract_sha256,
            "claim_create_new_required": self.claim_create_new_required,
            "claim_payload_and_parent_flush_required": (
                self.claim_payload_and_parent_flush_required
            ),
            "claim_handle_retained_until_terminal": (
                self.claim_handle_retained_until_terminal
            ),
            "outcome_create_new_required": self.outcome_create_new_required,
            "outcome_payload_and_parent_flush_required": (
                self.outcome_payload_and_parent_flush_required
            ),
            "exactly_one_terminal_outcome_required": (
                self.exactly_one_terminal_outcome_required
            ),
            "provider_reviewed": self.provider_reviewed,
            "operating_system_evidence_verified": (
                self.operating_system_evidence_verified
            ),
            "authority": dict(self.authority),
        }


class NativeCarrierTransactionProvider(Protocol):
    """Future provider surface; this module never discovers or invokes one."""

    provider_id: str
    interface_version: str

    def run_build_audit_transaction(
        self,
        request: NativeCarrierTransactionRequest,
    ) -> object:
        """Run one provider-owned transaction and return untrusted evidence."""


def _stage_request(
    *,
    stage_id: str,
    command: Sequence[str],
    timeout_ms: int,
) -> NativeTransactionStageRequest:
    command_tuple = _command(command, stage_id)
    return NativeTransactionStageRequest(
        schema=NATIVE_TRANSACTION_STAGE_SCHEMA,
        stage_id=stage_id,
        ordinal=STAGE_ORDER.index(stage_id),
        worker_role=STAGE_WORKER_ROLES[stage_id],
        command=command_tuple,
        argv_sha256=launch_contract.canonical_sha256(list(command_tuple)),
        command_line_sha256=launch_contract.windows_command_line_sha256(
            command_tuple
        ),
        timeout_ms=_bounded_int(timeout_ms, f"{stage_id} timeout"),
        candidate_custody_required_before_launch=stage_id == "audit",
        created_suspended_required=True,
        job_assignment_before_image_check_required=True,
        image_query_from_retained_process_handle_required=True,
        pid_process_identity_forbidden=True,
        exactly_one_resume_required=True,
        completion_required_before_next_phase=True,
        process_execution_authorized=False,
    )


def build_native_transaction_request(
    *,
    closure_record: Mapping[str, Any],
    provider_id: str,
    run_id: str,
    build_command: Sequence[str],
    audit_command: Sequence[str],
    environment: Mapping[str, str],
    working_directory: str,
    output_paths: Mapping[str, str],
    directory_paths: Sequence[str],
    claim_root_path: str,
    claim_path: str,
    outcome_path: str,
    build_timeout_ms: int,
    audit_timeout_ms: int,
) -> NativeCarrierTransactionRequest:
    """Bind a private payload to a verified closure without executing it."""

    source = _plain_closure_record(closure_record)
    provider = _provider_id(provider_id)
    run = _run_id(run_id)
    build_stage = _stage_request(
        stage_id="build",
        command=build_command,
        timeout_ms=build_timeout_ms,
    )
    audit_stage = _stage_request(
        stage_id="audit",
        command=audit_command,
        timeout_ms=audit_timeout_ms,
    )
    if build_stage.command[0] != audit_stage.command[0]:
        raise NativeTransactionProviderContractError(
            "build and audit application paths differ"
        )
    if (
        build_stage.argv_sha256 != source["build_argv_sha256"]
        or build_stage.command_line_sha256 != source["build_command_line_sha256"]
        or audit_stage.argv_sha256 != source["audit_argv_sha256"]
        or audit_stage.command_line_sha256 != source["audit_command_line_sha256"]
    ):
        raise NativeTransactionProviderContractError(
            "private commands differ from the source closure"
        )
    if build_stage.argv_sha256 == audit_stage.argv_sha256:
        raise NativeTransactionProviderContractError("build and audit commands alias")

    if type(output_paths) not in {dict, MappingProxyType}:
        raise NativeTransactionProviderContractError("output path mapping differs")
    if set(output_paths) != set(OUTPUT_ORDER):
        raise NativeTransactionProviderContractError("output path roles differ")
    closure_outputs = {value["role"]: value for value in source["outputs"]}
    reservations: list[NativeTransactionOutputReservation] = []
    output_canonical_digests: set[str] = set()
    for role in OUTPUT_ORDER:
        path = _local_path(output_paths[role], f"{role} output")
        source_output = closure_outputs[role]
        reservation = NativeTransactionOutputReservation(
            schema=NATIVE_TRANSACTION_OUTPUT_SCHEMA,
            role=role,
            custody_phase=OUTPUT_CUSTODY_PHASES[role],
            path=path,
            path_sha256=launch_contract.private_windows_path_sha256(path),
            canonical_path_sha256=launch_contract.canonical_windows_path_sha256(path),
            create_new_required=True,
            initially_absent_required=True,
            handle_retained_from_creation_until_terminal=True,
            validate_from_retained_handle_required=True,
            path_publication_before_terminal=False,
        )
        if (
            reservation.path_sha256 != source_output["path_sha256"]
            or reservation.canonical_path_sha256
            != source_output["canonical_path_sha256"]
            or source_output["must_be_create_new"] is not True
            or source_output["currently_absent"] is not True
        ):
            raise NativeTransactionProviderContractError(
                f"{role} private path differs from the source closure"
            )
        if reservation.canonical_path_sha256 in output_canonical_digests:
            raise NativeTransactionProviderContractError("output paths alias")
        output_canonical_digests.add(reservation.canonical_path_sha256)
        reservations.append(reservation)

    if type(directory_paths) not in {tuple, list} or not directory_paths:
        raise NativeTransactionProviderContractError("directory path chain is absent")
    if len(directory_paths) > launch_contract.MAX_NATIVE_DIRECTORY_HANDLES:
        raise NativeTransactionProviderContractError(
            "directory path chain exceeds the limit"
        )
    private_directories = tuple(
        _local_path(value, "directory") for value in directory_paths
    )
    directory_digests = tuple(
        launch_contract.private_windows_path_sha256(value)
        for value in private_directories
    )
    directory_canonical_digests = tuple(
        launch_contract.canonical_windows_path_sha256(value)
        for value in private_directories
    )
    if len(set(directory_canonical_digests)) != len(private_directories):
        raise NativeTransactionProviderContractError(
            "directory path chain contains a canonical alias"
        )
    parsed_directories = [_pure_local_path(value) for value in private_directories]
    if (
        not parsed_directories[0].anchor
        or parsed_directories[0] != PureWindowsPath(parsed_directories[0].anchor)
    ):
        raise NativeTransactionProviderContractError(
            "directory path chain does not begin at the local drive root"
        )
    for parent, child in zip(parsed_directories, parsed_directories[1:]):
        if child.parent != parent:
            raise NativeTransactionProviderContractError(
                "directory path chain is not contiguous"
            )

    root = _local_path(claim_root_path, "claim root")
    root_path_sha256 = launch_contract.private_windows_path_sha256(root)
    root_canonical_path_sha256 = launch_contract.canonical_windows_path_sha256(
        root
    )
    claim_path_value = _local_path(claim_path, "claim")
    outcome_path_value = _local_path(outcome_path, "outcome")
    if (
        _pure_local_path(root) != parsed_directories[-1]
        or root_path_sha256 != directory_digests[-1]
        or root_canonical_path_sha256 != directory_canonical_digests[-1]
    ):
        raise NativeTransactionProviderContractError(
            "claim root differs from the retained directory chain"
        )
    if (
        _pure_local_path(claim_path_value).parent != _pure_local_path(root)
        or _pure_local_path(outcome_path_value).parent != _pure_local_path(root)
    ):
        raise NativeTransactionProviderContractError(
            "claim or outcome path is outside the claim root"
        )
    claim_path_sha256 = launch_contract.private_windows_path_sha256(claim_path_value)
    outcome_path_sha256 = launch_contract.private_windows_path_sha256(
        outcome_path_value
    )
    claim_canonical = launch_contract.canonical_windows_path_sha256(claim_path_value)
    outcome_canonical = launch_contract.canonical_windows_path_sha256(
        outcome_path_value
    )
    if claim_canonical == outcome_canonical:
        raise NativeTransactionProviderContractError("claim and outcome paths alias")
    if {claim_canonical, outcome_canonical} & output_canonical_digests:
        raise NativeTransactionProviderContractError(
            "claim or outcome aliases a reserved output"
        )

    if type(environment) not in {dict, MappingProxyType}:
        raise NativeTransactionProviderContractError("environment mapping differs")
    frozen_environment = MappingProxyType(dict(environment))
    try:
        environment_block_sha256 = launch_contract.windows_environment_block_sha256(
            frozen_environment
        )
    except launch_contract.NativeProviderContractError as exc:
        raise NativeTransactionProviderContractError(
            "environment differs from the bounded native grammar"
        ) from exc
    working = _local_path(working_directory, "working directory")

    blender_input = next(
        value for value in source["inputs"] if value["role"] == "blender_executable"
    )
    blender_path = build_stage.command[0]
    # The held image path may use the native ``\\?\`` prefix while the exact
    # CreateProcess application string does not.  Canonical identity must
    # agree; the two lexical path digests are intentionally not conflated.
    if (
        launch_contract.canonical_windows_path_sha256(blender_path)
        != blender_input["canonical_path_sha256"]
    ):
        raise NativeTransactionProviderContractError(
            "private Blender path differs from the source closure"
        )

    directory_records = [
        {
            "depth": index,
            "final_path_sha256": digest,
            "canonical_path_sha256": canonical_digest,
        }
        for index, (digest, canonical_digest) in enumerate(
            zip(directory_digests, directory_canonical_digests)
        )
    ]
    source_closure_bytes = _canonical_json_bytes(source)
    authority = MappingProxyType({key: False for key in AUTHORITY_KEYS})
    request = NativeCarrierTransactionRequest(
        schema=NATIVE_TRANSACTION_REQUEST_SCHEMA,
        status=NATIVE_TRANSACTION_STATIC_STATUS,
        provider_id=provider,
        interface_version=NATIVE_TRANSACTION_PROVIDER_INTERFACE,
        operation=NATIVE_TRANSACTION_OPERATION,
        run_id=run,
        candidate_id=source["candidate_id"],
        source_closure_schema=source["schema"],
        source_closure_status=source["status"],
        source_closure_canonical_json=source_closure_bytes,
        source_closure_sha256=hashlib.sha256(source_closure_bytes).hexdigest(),
        input_closure_sha256=source["input_closure_sha256"],
        output_closure_sha256=source["output_closure_sha256"],
        source_single_launch_interface=source["native_provider_interface"],
        source_single_launch_interface_is_insufficient=True,
        stages=(build_stage, audit_stage),
        outputs=tuple(reservations),
        transaction_phases=tuple(source["transaction_stages"]),
        environment=frozen_environment,
        environment_block_sha256=environment_block_sha256,
        working_directory=working,
        working_directory_sha256=launch_contract.private_windows_path_sha256(
            working
        ),
        expected_blender_image_bytes=blender_input["bytes"],
        expected_blender_image_sha256=blender_input["sha256"],
        expected_blender_image_path_sha256=blender_input["path_sha256"],
        expected_blender_image_canonical_path_sha256=blender_input[
            "canonical_path_sha256"
        ],
        directory_paths=private_directories,
        directory_path_sha256=directory_digests,
        directory_canonical_path_sha256=directory_canonical_digests,
        directory_chain_sha256=launch_contract.canonical_sha256(directory_records),
        claim_root_path=root,
        claim_root_path_sha256=root_path_sha256,
        claim_root_canonical_path_sha256=root_canonical_path_sha256,
        claim_path=claim_path_value,
        claim_path_sha256=claim_path_sha256,
        claim_canonical_path_sha256=claim_canonical,
        outcome_path=outcome_path_value,
        outcome_path_sha256=outcome_path_sha256,
        outcome_canonical_path_sha256=outcome_canonical,
        durability_contract_sha256=(
            launch_contract.directory_claim_durability_contract_sha256()
        ),
        claim_create_new_required=True,
        claim_payload_and_parent_flush_required=True,
        claim_handle_retained_until_terminal=True,
        outcome_create_new_required=True,
        outcome_payload_and_parent_flush_required=True,
        exactly_one_terminal_outcome_required=True,
        provider_reviewed=False,
        operating_system_evidence_verified=False,
        authority=authority,
    )
    validate_native_transaction_request(request)
    return request


def validate_static_native_transaction_request_record(
    record: Mapping[str, Any],
) -> None:
    """Validate a private-path-free request record as untrusted static shape."""

    expected_keys = {
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
        "source_single_launch_interface_is_insufficient",
        "stages",
        "outputs",
        "transaction_phases",
        "environment_block_sha256",
        "working_directory_sha256",
        "expected_blender_image_bytes",
        "expected_blender_image_sha256",
        "expected_blender_image_path_sha256",
        "expected_blender_image_canonical_path_sha256",
        "directory_path_sha256",
        "directory_canonical_path_sha256",
        "directory_chain_sha256",
        "claim_root_path_sha256",
        "claim_root_canonical_path_sha256",
        "claim_path_sha256",
        "claim_canonical_path_sha256",
        "outcome_path_sha256",
        "outcome_canonical_path_sha256",
        "durability_contract_sha256",
        "claim_create_new_required",
        "claim_payload_and_parent_flush_required",
        "claim_handle_retained_until_terminal",
        "outcome_create_new_required",
        "outcome_payload_and_parent_flush_required",
        "exactly_one_terminal_outcome_required",
        "provider_reviewed",
        "operating_system_evidence_verified",
        "authority",
    }
    if type(record) is not dict or set(record) != expected_keys:
        raise NativeTransactionProviderContractError("request record keys differ")
    if (
        record["schema"] != NATIVE_TRANSACTION_REQUEST_SCHEMA
        or record["status"] != NATIVE_TRANSACTION_STATIC_STATUS
        or record["interface_version"] != NATIVE_TRANSACTION_PROVIDER_INTERFACE
        or record["operation"] != NATIVE_TRANSACTION_OPERATION
    ):
        raise NativeTransactionProviderContractError("request record identity differs")
    _provider_id(record["provider_id"])
    _run_id(record["run_id"])
    if type(record["candidate_id"]) is not str or not record["candidate_id"]:
        raise NativeTransactionProviderContractError("candidate id differs")
    if (
        record["source_closure_schema"] != closure.CLOSURE_SCHEMA
        or record["source_closure_status"] != closure.CLOSURE_STATUS
        or record["source_single_launch_interface"]
        != launch_contract.NATIVE_PROVIDER_INTERFACE
    ):
        raise NativeTransactionProviderContractError("source closure binding differs")
    _exact_bool(
        record["source_single_launch_interface_is_insufficient"],
        True,
        "source_single_launch_interface_is_insufficient",
    )
    for key in (
        "source_closure_sha256",
        "input_closure_sha256",
        "output_closure_sha256",
        "environment_block_sha256",
        "working_directory_sha256",
        "expected_blender_image_sha256",
        "expected_blender_image_path_sha256",
        "expected_blender_image_canonical_path_sha256",
        "directory_chain_sha256",
        "claim_root_path_sha256",
        "claim_root_canonical_path_sha256",
        "claim_path_sha256",
        "claim_canonical_path_sha256",
        "outcome_path_sha256",
        "outcome_canonical_path_sha256",
        "durability_contract_sha256",
    ):
        _sha256(record[key], key)
    if (
        type(record["expected_blender_image_bytes"]) is not int
        or record["expected_blender_image_bytes"] <= 0
    ):
        raise NativeTransactionProviderContractError("Blender image byte count differs")
    if (
        record["durability_contract_sha256"]
        != launch_contract.directory_claim_durability_contract_sha256()
    ):
        raise NativeTransactionProviderContractError("durability contract differs")

    stages = record["stages"]
    if type(stages) is not list or len(stages) != 2:
        raise NativeTransactionProviderContractError("exactly two stages are required")
    expected_stage_keys = {
        "schema",
        "stage_id",
        "ordinal",
        "worker_role",
        "argv_sha256",
        "command_line_sha256",
        "timeout_ms",
        "candidate_custody_required_before_launch",
        "created_suspended_required",
        "job_assignment_before_image_check_required",
        "image_query_from_retained_process_handle_required",
        "pid_process_identity_forbidden",
        "exactly_one_resume_required",
        "completion_required_before_next_phase",
        "process_execution_authorized",
    }
    stage_argv: list[str] = []
    for ordinal, (stage_id, stage) in enumerate(zip(STAGE_ORDER, stages)):
        if type(stage) is not dict or set(stage) != expected_stage_keys:
            raise NativeTransactionProviderContractError("stage record shape differs")
        if (
            stage["schema"] != NATIVE_TRANSACTION_STAGE_SCHEMA
            or stage["stage_id"] != stage_id
            or stage["ordinal"] != ordinal
            or stage["worker_role"] != STAGE_WORKER_ROLES[stage_id]
        ):
            raise NativeTransactionProviderContractError("stage order differs")
        _sha256(stage["argv_sha256"], "stage argv digest")
        _sha256(stage["command_line_sha256"], "stage command-line digest")
        _bounded_int(stage["timeout_ms"], "stage timeout")
        _exact_bool(
            stage["candidate_custody_required_before_launch"],
            stage_id == "audit",
            "candidate_custody_required_before_launch",
        )
        for key in (
            "created_suspended_required",
            "job_assignment_before_image_check_required",
            "image_query_from_retained_process_handle_required",
            "pid_process_identity_forbidden",
            "exactly_one_resume_required",
            "completion_required_before_next_phase",
        ):
            _exact_bool(stage[key], True, key)
        _exact_bool(
            stage["process_execution_authorized"],
            False,
            "process_execution_authorized",
        )
        stage_argv.append(stage["argv_sha256"])
    if len(set(stage_argv)) != 2:
        raise NativeTransactionProviderContractError("stage commands alias")

    outputs = record["outputs"]
    expected_output_keys = {
        "schema",
        "role",
        "custody_phase",
        "path_sha256",
        "canonical_path_sha256",
        "create_new_required",
        "initially_absent_required",
        "handle_retained_from_creation_until_terminal",
        "validate_from_retained_handle_required",
        "path_publication_before_terminal",
    }
    if type(outputs) is not list or len(outputs) != len(OUTPUT_ORDER):
        raise NativeTransactionProviderContractError("output reservations differ")
    output_digests: set[str] = set()
    for role, output in zip(OUTPUT_ORDER, outputs):
        if type(output) is not dict or set(output) != expected_output_keys:
            raise NativeTransactionProviderContractError("output record shape differs")
        if (
            output["schema"] != NATIVE_TRANSACTION_OUTPUT_SCHEMA
            or output["role"] != role
            or output["custody_phase"] != OUTPUT_CUSTODY_PHASES[role]
        ):
            raise NativeTransactionProviderContractError("output order differs")
        _sha256(output["path_sha256"], "output path digest")
        canonical = _sha256(
            output["canonical_path_sha256"],
            "output canonical path digest",
        )
        if canonical in output_digests:
            raise NativeTransactionProviderContractError("output paths alias")
        output_digests.add(canonical)
        for key in (
            "create_new_required",
            "initially_absent_required",
            "handle_retained_from_creation_until_terminal",
            "validate_from_retained_handle_required",
        ):
            _exact_bool(output[key], True, key)
        _exact_bool(
            output["path_publication_before_terminal"],
            False,
            "path_publication_before_terminal",
        )

    if record["transaction_phases"] != list(closure.TRANSACTION_STAGES):
        raise NativeTransactionProviderContractError("transaction phase order differs")
    directory_digests = record["directory_path_sha256"]
    if type(directory_digests) is not list or not directory_digests:
        raise NativeTransactionProviderContractError("directory digest chain is absent")
    for digest in directory_digests:
        _sha256(digest, "directory path digest")
    if len(set(directory_digests)) != len(directory_digests):
        raise NativeTransactionProviderContractError("directory digests alias")
    directory_canonical_digests = record["directory_canonical_path_sha256"]
    if (
        type(directory_canonical_digests) is not list
        or len(directory_canonical_digests) != len(directory_digests)
    ):
        raise NativeTransactionProviderContractError(
            "canonical directory digest chain differs"
        )
    for digest in directory_canonical_digests:
        _sha256(digest, "canonical directory path digest")
    if len(set(directory_canonical_digests)) != len(
        directory_canonical_digests
    ):
        raise NativeTransactionProviderContractError(
            "canonical directory digests alias"
        )
    expected_directory_chain = launch_contract.canonical_sha256(
        [
            {
                "depth": index,
                "final_path_sha256": digest,
                "canonical_path_sha256": canonical_digest,
            }
            for index, (digest, canonical_digest) in enumerate(
                zip(directory_digests, directory_canonical_digests)
            )
        ]
    )
    if (
        record["directory_chain_sha256"] != expected_directory_chain
        or record["claim_root_path_sha256"] != directory_digests[-1]
        or record["claim_root_canonical_path_sha256"]
        != directory_canonical_digests[-1]
    ):
        raise NativeTransactionProviderContractError("directory chain binding differs")
    if (
        record["claim_path_sha256"] == record["outcome_path_sha256"]
        or record["claim_canonical_path_sha256"]
        == record["outcome_canonical_path_sha256"]
    ):
        raise NativeTransactionProviderContractError("claim and outcome paths alias")
    if {
        record["claim_canonical_path_sha256"],
        record["outcome_canonical_path_sha256"],
    } & {output["canonical_path_sha256"] for output in outputs}:
        raise NativeTransactionProviderContractError(
            "claim or outcome aliases a reserved output"
        )
    for key in (
        "claim_create_new_required",
        "claim_payload_and_parent_flush_required",
        "claim_handle_retained_until_terminal",
        "outcome_create_new_required",
        "outcome_payload_and_parent_flush_required",
        "exactly_one_terminal_outcome_required",
    ):
        _exact_bool(record[key], True, key)
    _exact_bool(record["provider_reviewed"], False, "provider_reviewed")
    _exact_bool(
        record["operating_system_evidence_verified"],
        False,
        "operating_system_evidence_verified",
    )
    authority = record["authority"]
    if type(authority) is not dict or set(authority) != set(AUTHORITY_KEYS):
        raise NativeTransactionProviderContractError("authority shape differs")
    if any(value is not False for value in authority.values()):
        raise NativeTransactionProviderContractError("authority must remain false")


def validate_native_transaction_request(
    request: NativeCarrierTransactionRequest,
) -> Mapping[str, Any]:
    """Revalidate private payload bindings; never convert them into authority."""

    if type(request) is not NativeCarrierTransactionRequest:
        raise NativeTransactionProviderContractError("request type differs")
    record = request.safe_record()
    validate_static_native_transaction_request_record(record)
    source = _parse_canonical_closure_bytes(
        request.source_closure_canonical_json
    )
    if (
        hashlib.sha256(request.source_closure_canonical_json).hexdigest()
        != request.source_closure_sha256
        or request.source_closure_schema != source["schema"]
        or request.source_closure_status != source["status"]
        or request.candidate_id != source["candidate_id"]
        or request.input_closure_sha256 != source["input_closure_sha256"]
        or request.output_closure_sha256 != source["output_closure_sha256"]
        or request.source_single_launch_interface
        != source["native_provider_interface"]
    ):
        raise NativeTransactionProviderContractError(
            "private source closure binding differs"
        )
    if tuple(stage.stage_id for stage in request.stages) != STAGE_ORDER:
        raise NativeTransactionProviderContractError("private stage order differs")
    for stage, argv_key, command_key in (
        (
            request.stages[0],
            "build_argv_sha256",
            "build_command_line_sha256",
        ),
        (
            request.stages[1],
            "audit_argv_sha256",
            "audit_command_line_sha256",
        ),
    ):
        if stage.argv_sha256 != launch_contract.canonical_sha256(list(stage.command)):
            raise NativeTransactionProviderContractError("private stage argv differs")
        if (
            stage.command_line_sha256
            != launch_contract.windows_command_line_sha256(stage.command)
        ):
            raise NativeTransactionProviderContractError(
                "private stage command line differs"
            )
        if (
            stage.argv_sha256 != source[argv_key]
            or stage.command_line_sha256 != source[command_key]
        ):
            raise NativeTransactionProviderContractError(
                "private stage differs from the source closure"
            )
    if len({output.path.casefold() for output in request.outputs}) != len(
        request.outputs
    ):
        raise NativeTransactionProviderContractError("private output paths alias")
    source_outputs = {value["role"]: value for value in source["outputs"]}
    for output in request.outputs:
        bound = source_outputs[output.role]
        if (
            output.path_sha256 != bound["path_sha256"]
            or output.canonical_path_sha256 != bound["canonical_path_sha256"]
        ):
            raise NativeTransactionProviderContractError(
                "private output differs from the source closure"
            )
    working_directory = _local_path(
        request.working_directory,
        "private working directory",
    )
    if (
        request.environment_block_sha256
        != launch_contract.windows_environment_block_sha256(request.environment)
        or request.working_directory_sha256
        != launch_contract.private_windows_path_sha256(working_directory)
    ):
        raise NativeTransactionProviderContractError(
            "private environment or working-directory binding differs"
        )
    private_directories = tuple(
        _local_path(value, "private directory")
        for value in request.directory_paths
    )
    observed_directory_digests = tuple(
        launch_contract.private_windows_path_sha256(value)
        for value in private_directories
    )
    observed_directory_canonical_digests = tuple(
        launch_contract.canonical_windows_path_sha256(value)
        for value in private_directories
    )
    if (
        observed_directory_digests != request.directory_path_sha256
        or observed_directory_canonical_digests
        != request.directory_canonical_path_sha256
        or len(set(observed_directory_canonical_digests))
        != len(observed_directory_canonical_digests)
    ):
        raise NativeTransactionProviderContractError("private directory binding differs")
    parsed_directories = tuple(
        _pure_local_path(value) for value in private_directories
    )
    if (
        not parsed_directories[0].anchor
        or parsed_directories[0] != PureWindowsPath(parsed_directories[0].anchor)
    ):
        raise NativeTransactionProviderContractError(
            "private directory path chain does not begin at the local drive root"
        )
    for parent, child in zip(parsed_directories, parsed_directories[1:]):
        if child.parent != parent:
            raise NativeTransactionProviderContractError(
                "private directory path chain is not contiguous"
            )
    if (
        request.claim_root_path != private_directories[-1]
        or _pure_local_path(request.claim_root_path) != parsed_directories[-1]
    ):
        raise NativeTransactionProviderContractError(
            "private claim root differs from the final directory"
        )
    claim_root = _pure_local_path(request.claim_root_path)
    if (
        _pure_local_path(request.claim_path).parent != claim_root
        or _pure_local_path(request.outcome_path).parent != claim_root
    ):
        raise NativeTransactionProviderContractError(
            "private claim or outcome path is outside the claim root"
        )
    for raw_path, expected_digest, expected_canonical_digest in (
        (
            request.claim_root_path,
            request.claim_root_path_sha256,
            request.claim_root_canonical_path_sha256,
        ),
        (
            request.claim_path,
            request.claim_path_sha256,
            request.claim_canonical_path_sha256,
        ),
        (
            request.outcome_path,
            request.outcome_path_sha256,
            request.outcome_canonical_path_sha256,
        ),
    ):
        _local_path(raw_path, "private claim transaction path")
        if (
            launch_contract.private_windows_path_sha256(raw_path) != expected_digest
            or launch_contract.canonical_windows_path_sha256(raw_path)
            != expected_canonical_digest
        ):
            raise NativeTransactionProviderContractError("private claim binding differs")
    return MappingProxyType(
        {
            "schema": NATIVE_TRANSACTION_REQUEST_SCHEMA,
            "status": NATIVE_TRANSACTION_STATIC_STATUS,
            "provider_id": request.provider_id,
            "request_sha256": launch_contract.canonical_sha256(record),
            "source_closure_sha256": request.source_closure_sha256,
            "exact_two_stage_shape_valid": True,
            "private_payload_digest_bindings_valid": True,
            "native_provider_reviewed": False,
            "provider_invocation_authorized": False,
            "operating_system_evidence_verified": False,
            "blender_execution_authorized": False,
            "body_created": False,
            "runtime_activation_authorized": False,
            "public_export_authorized": False,
        }
    )


def static_contract_evidence_record() -> Mapping[str, Any]:
    """Public identity of this inert interface, without a provider claim."""

    return MappingProxyType(
        {
            "provider_interface": NATIVE_TRANSACTION_PROVIDER_INTERFACE,
            "request_schema": NATIVE_TRANSACTION_REQUEST_SCHEMA,
            "stage_schema": NATIVE_TRANSACTION_STAGE_SCHEMA,
            "output_schema": NATIVE_TRANSACTION_OUTPUT_SCHEMA,
            "operation": NATIVE_TRANSACTION_OPERATION,
            "stage_order": list(STAGE_ORDER),
            "transaction_phases": list(closure.TRANSACTION_STAGES),
            "source_single_launch_interface": (
                launch_contract.NATIVE_PROVIDER_INTERFACE
            ),
            "source_single_launch_interface_is_insufficient": True,
            "windows_component_grammar": (
                "ASCII_LOCAL_DRIVE_ONLY_NO_WIN32_FORBIDDEN_OR_CONTROL_CHARACTERS_"
                "NO_TRAILING_DOT_OR_SPACE_NO_ADS_NO_DOS_DEVICE_BASENAME"
            ),
            "review_scope": "STATIC_REQUEST_STRUCTURE_AND_HOSTILE_MUTATION_ONLY",
            "short_name_alias_identity_verified": False,
            "reparse_identity_verified": False,
            "hardlink_identity_verified": False,
            "native_provider_reviewed": False,
            "provider_invocation_authorized": False,
            "operating_system_evidence_verified": False,
            "blender_execution_authorized": False,
        }
    )


__all__ = [
    "ASCII_LOCAL_DRIVE_RE",
    "AUTHORITY_KEYS",
    "DOS_DEVICE_NAMES",
    "MAX_TRANSACTION_TIMEOUT_MS",
    "NATIVE_TRANSACTION_OPERATION",
    "NATIVE_TRANSACTION_OUTPUT_SCHEMA",
    "NATIVE_TRANSACTION_PROVIDER_INTERFACE",
    "NATIVE_TRANSACTION_REQUEST_SCHEMA",
    "NATIVE_TRANSACTION_STAGE_SCHEMA",
    "NATIVE_TRANSACTION_STATIC_STATUS",
    "NativeCarrierTransactionProvider",
    "NativeCarrierTransactionRequest",
    "NativeTransactionOutputReservation",
    "NativeTransactionProviderContractError",
    "NativeTransactionStageRequest",
    "OUTPUT_CUSTODY_PHASES",
    "OUTPUT_ORDER",
    "STAGE_ORDER",
    "WIN32_FORBIDDEN_COMPONENT_CHARS",
    "build_native_transaction_request",
    "static_contract_evidence_record",
    "validate_native_transaction_request",
    "validate_static_native_transaction_request_record",
]
