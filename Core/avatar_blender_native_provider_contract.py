"""Static contract for a future reviewed Windows Blender launch provider.

This module deliberately does not call a native API, create a process, resume a
thread, write a claim, or grant execution authority.  It provides only:

* opaque handle leases that keep provider-owned objects strongly referenced;
* exact, bounded in-memory image/path and process-policy attestation types;
* an exact directory/claim durability requirements record; and
* a pure validator for hostile fake-provider tests.

A shape-valid fake attestation is not operating-system evidence.  The current
controller therefore never calls this interface and every returned validation
receipt keeps resume and execution authority false.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import PureWindowsPath
import re
import subprocess
from types import MappingProxyType
from typing import Any, Mapping, Protocol, Sequence


NATIVE_PROVIDER_INTERFACE = "kira.blender_native_launch_provider.v2"
NATIVE_REQUIREMENTS_SCHEMA = "kira.blender_native_launch_requirements.v1"
NATIVE_PATH_IDENTITY_SCHEMA = "kira.blender_native_path_identity_attestation.v1"
NATIVE_PROCESS_IMAGE_SCHEMA = "kira.blender_native_process_image_attestation.v1"
NATIVE_PROCESS_POLICY_SCHEMA = "kira.blender_native_process_policy_attestation.v1"
NATIVE_CLAIM_DURABILITY_SCHEMA = "kira.blender_native_claim_durability_attestation.v1"
NATIVE_PRE_RESUME_SCHEMA = "kira.blender_native_pre_resume_attestation.v1"
NATIVE_DIRECTORY_CLAIM_CONTRACT_SCHEMA = (
    "kira.blender_native_directory_claim_durability_contract.v1"
)
NATIVE_STATIC_VALIDATION_STATUS = "STATIC_SHAPE_VALID_ONLY_NO_NATIVE_AUTHORITY"

CREATE_SUSPENDED = 0x00000004
CREATE_UNICODE_ENVIRONMENT = 0x00000400
EXACT_CREATE_PROCESS_FLAGS = CREATE_SUSPENDED | CREATE_UNICODE_ENVIRONMENT
FILE_SHARE_NONE = 0
FILE_SHARE_READ = 0x00000001
CREATE_NEW = 1
FILE_ATTRIBUTE_NORMAL = 0x00000080
FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
FILE_FLAG_WRITE_THROUGH = 0x80000000
EXACT_DIRECTORY_OPEN_FLAGS = FILE_FLAG_OPEN_REPARSE_POINT | FILE_FLAG_BACKUP_SEMANTICS
EXACT_DURABLE_RECORD_FLAGS = (
    FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT | FILE_FLAG_WRITE_THROUGH
)
MAX_NATIVE_RUNTIME_MS = 24 * 60 * 60 * 1000
MAX_NATIVE_DIRECTORY_HANDLES = 64

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
FILE_ID_RE = re.compile(r"^[0-9a-f]{32}$")
PROVIDER_ID_RE = re.compile(r"^[a-z][a-z0-9_.-]{7,95}$")
RUN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{7,63}$")
SAFE_ENVIRONMENT_KEYS = frozenset(
    {"SystemRoot", "WINDIR", "ComSpec", "PATH", "TEMP", "TMP"}
)
HANDLE_KINDS = frozenset(
    {
        "process",
        "primary_thread",
        "job",
        "blender_image_file",
        "claim_file",
        "directory",
    }
)
PATH_IDENTITY_SOURCES = frozenset(
    {
        "held_blender_file_handle",
        "created_process_handle_image",
    }
)


class NativeProviderContractError(ValueError):
    """Stable failure for the non-executing native-provider contract."""


def _exact_bool(value: Any, expected: bool, label: str) -> None:
    if type(value) is not bool or value is not expected:
        raise NativeProviderContractError(f"{label} must be exactly {expected}")


def _exact_int(
    value: Any,
    label: str,
    *,
    minimum: int = 0,
    maximum: int = (1 << 63) - 1,
) -> int:
    if (
        type(value) is not int
        or value < minimum
        or value > maximum
    ):
        raise NativeProviderContractError(f"{label} is outside the exact integer range")
    return value


def _sha256(value: Any, label: str) -> str:
    if type(value) is not str or SHA256_RE.fullmatch(value) is None:
        raise NativeProviderContractError(f"{label} must be lowercase SHA-256")
    return value


def _provider_id(value: Any) -> str:
    if type(value) is not str or PROVIDER_ID_RE.fullmatch(value) is None:
        raise NativeProviderContractError("provider_id grammar is invalid")
    return value


def _run_id(value: Any) -> str:
    if type(value) is not str or RUN_ID_RE.fullmatch(value) is None:
        raise NativeProviderContractError("run_id grammar is invalid")
    return value


def _canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise NativeProviderContractError("contract value is not canonical JSON") from exc


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _windows_absolute_local_path(value: Any, label: str) -> str:
    if type(value) is not str or not value or len(value) > 32767:
        raise NativeProviderContractError(f"{label} must be bounded path text")
    if "/" in value or "\x00" in value:
        raise NativeProviderContractError(f"{label} must use exact Windows path text")
    parsed_value = value
    prefix = ""
    if value.startswith("\\\\?\\"):
        parsed_value = value[4:]
        prefix = "\\\\?\\"
        if parsed_value.casefold().startswith("unc\\"):
            raise NativeProviderContractError(f"{label} must not be UNC")
    elif value.startswith("\\\\") or value.startswith("//"):
        raise NativeProviderContractError(f"{label} must not be UNC")
    path = PureWindowsPath(parsed_value)
    if not path.is_absolute() or not path.drive or path.root != "\\":
        raise NativeProviderContractError(f"{label} must be an absolute local path")
    if any(part in {".", ".."} for part in path.parts):
        raise NativeProviderContractError(f"{label} must not contain traversal")
    if f"{prefix}{path}" != value:
        raise NativeProviderContractError(f"{label} must be lexically canonical")
    return value


def private_windows_path_sha256(value: str) -> str:
    path = _windows_absolute_local_path(value, "private path")
    return hashlib.sha256(path.encode("utf-16le")).hexdigest()


def canonical_windows_path_sha256(value: str) -> str:
    path = _windows_absolute_local_path(value, "private path")
    if path.startswith("\\\\?\\"):
        path = path[4:]
    canonical = str(PureWindowsPath(path)).casefold()
    return hashlib.sha256(canonical.encode("utf-16le")).hexdigest()


def windows_command_line_sha256(command: Sequence[str]) -> str:
    if type(command) not in {tuple, list} or not command:
        raise NativeProviderContractError("command must be a nonempty exact sequence")
    if any(type(item) is not str or not item or "\x00" in item for item in command):
        raise NativeProviderContractError("command entries must be bounded text")
    line = subprocess.list2cmdline(list(command))
    return hashlib.sha256(line.encode("utf-16le")).hexdigest()


def windows_environment_block_sha256(environment: Mapping[str, str]) -> str:
    if type(environment) not in {dict, MappingProxyType}:
        raise NativeProviderContractError("environment must be an exact mapping")
    if set(environment) != SAFE_ENVIRONMENT_KEYS or len(environment) != 6:
        raise NativeProviderContractError("environment keys differ from the safe grammar")
    entries: list[str] = []
    folded: set[str] = set()
    for key in sorted(environment, key=lambda item: item.casefold()):
        value = environment[key]
        if type(key) is not str or type(value) is not str or not value:
            raise NativeProviderContractError("environment entries must be nonempty text")
        if "=" in key or "\x00" in key or "\x00" in value:
            raise NativeProviderContractError("environment entry grammar differs")
        casefolded = key.casefold()
        if casefolded in folded:
            raise NativeProviderContractError("environment contains a case-folded duplicate")
        folded.add(casefolded)
        entries.append(f"{key}={value}")
    block = "\x00".join(entries) + "\x00\x00"
    return hashlib.sha256(block.encode("utf-16le")).hexdigest()


class NativeHandleCloseApi(Protocol):
    """Minimal close API retained by an opaque handle lease."""

    def close_handle(self, native_token: object) -> bool:
        """Return exactly ``True`` only after the exact native handle closed."""


class RetainedNativeHandle:
    """Strongly retain one provider-owned token until an explicit close.

    This class proves Python object lifetime and exact close-result handling. It
    cannot prove that the opaque token names a real or still-open Windows
    handle; only a reviewed native provider and real hostile tests can do that.
    """

    __slots__ = (
        "_provider_id",
        "_kind",
        "_native_token",
        "_close_api",
        "_closed",
    )

    def __init__(
        self,
        *,
        provider_id: str,
        kind: str,
        native_token: object,
        close_api: NativeHandleCloseApi,
    ) -> None:
        self._provider_id = _provider_id(provider_id)
        if type(kind) is not str or kind not in HANDLE_KINDS:
            raise NativeProviderContractError("native handle kind differs")
        if native_token is None or isinstance(
            native_token,
            (bool, int, float, complex, str, bytes, bytearray, memoryview),
        ):
            raise NativeProviderContractError(
                "native handle token must be an opaque provider object"
            )
        try:
            close_method = getattr(close_api, "close_handle")
        except BaseException as exc:
            raise NativeProviderContractError("native close API is unavailable") from exc
        if not callable(close_method):
            raise NativeProviderContractError("native close API is not callable")
        self._kind = kind
        self._native_token = native_token
        self._close_api = close_api
        self._closed = False

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def kind(self) -> str:
        return self._kind

    @property
    def closed(self) -> bool:
        return self._closed

    def shares_native_token_with(self, other: "RetainedNativeHandle") -> bool:
        if type(other) is not RetainedNativeHandle:
            return False
        return self._native_token is other._native_token

    def shares_close_api_with(self, other: "RetainedNativeHandle") -> bool:
        if type(other) is not RetainedNativeHandle:
            return False
        return self._close_api is other._close_api

    def close(self) -> None:
        if self._closed:
            return
        try:
            result = self._close_api.close_handle(self._native_token)
        except BaseException as exc:
            raise NativeProviderContractError("native handle close raised") from exc
        if result is not True:
            raise NativeProviderContractError("native handle close was not exactly successful")
        self._closed = True


@dataclass(frozen=True)
class RetainedNativeLaunchHandles:
    """Retain all pre-resume handles needed by the static contract."""

    process: RetainedNativeHandle
    primary_thread: RetainedNativeHandle
    job: RetainedNativeHandle
    blender_image_file: RetainedNativeHandle
    claim_file: RetainedNativeHandle
    directories: tuple[RetainedNativeHandle, ...]

    def __post_init__(self) -> None:
        exact = (
            ("process", self.process),
            ("primary_thread", self.primary_thread),
            ("job", self.job),
            ("blender_image_file", self.blender_image_file),
            ("claim_file", self.claim_file),
        )
        if type(self.directories) is not tuple or not self.directories:
            raise NativeProviderContractError("at least one retained directory is required")
        if len(self.directories) > MAX_NATIVE_DIRECTORY_HANDLES:
            raise NativeProviderContractError("retained directory count exceeds the limit")
        handles: list[RetainedNativeHandle] = []
        for kind, handle in exact:
            if type(handle) is not RetainedNativeHandle or handle.kind != kind:
                raise NativeProviderContractError(f"retained {kind} handle differs")
            handles.append(handle)
        for handle in self.directories:
            if type(handle) is not RetainedNativeHandle or handle.kind != "directory":
                raise NativeProviderContractError("retained directory handle differs")
            handles.append(handle)
        provider_ids = {handle.provider_id for handle in handles}
        if len(provider_ids) != 1:
            raise NativeProviderContractError("retained handle providers differ")
        first = handles[0]
        for index, handle in enumerate(handles):
            if handle.closed:
                raise NativeProviderContractError("a retained native handle is already closed")
            if not first.shares_close_api_with(handle):
                raise NativeProviderContractError("retained handle close APIs differ")
            for previous in handles[:index]:
                if handle.shares_native_token_with(previous):
                    raise NativeProviderContractError("retained native handle tokens alias")

    @property
    def provider_id(self) -> str:
        return self.process.provider_id

    def assert_all_open(self) -> None:
        handles = (
            self.process,
            self.primary_thread,
            self.job,
            self.blender_image_file,
            self.claim_file,
            *self.directories,
        )
        if any(handle.closed for handle in handles):
            raise NativeProviderContractError("a required retained handle closed early")


@dataclass(frozen=True)
class NativePathIdentityAttestation:
    """Exact in-memory handle-derived file identity; raw paths stay private."""

    schema: str
    provider_id: str
    source: str
    final_path: str = field(repr=False)
    final_path_sha256: str
    canonical_path_sha256: str
    volume_serial_number: int
    file_id: str
    bytes: int
    sha256: str
    link_count: int
    regular_file: bool
    reparse_point: bool
    handle_retained: bool
    path_published: bool

    def __post_init__(self) -> None:
        if self.schema != NATIVE_PATH_IDENTITY_SCHEMA:
            raise NativeProviderContractError("path identity schema differs")
        _provider_id(self.provider_id)
        if type(self.source) is not str or self.source not in PATH_IDENTITY_SOURCES:
            raise NativeProviderContractError("path identity source differs")
        path = _windows_absolute_local_path(self.final_path, "final handle path")
        if self.final_path_sha256 != private_windows_path_sha256(path):
            raise NativeProviderContractError("final handle path digest differs")
        if self.canonical_path_sha256 != canonical_windows_path_sha256(path):
            raise NativeProviderContractError("canonical handle path digest differs")
        _exact_int(
            self.volume_serial_number,
            "volume serial number",
            maximum=(1 << 64) - 1,
        )
        if type(self.file_id) is not str or FILE_ID_RE.fullmatch(self.file_id) is None:
            raise NativeProviderContractError("file identity must be exact 128-bit lowercase hex")
        _exact_int(self.bytes, "file byte count", minimum=1)
        _sha256(self.sha256, "file sha256")
        if type(self.link_count) is not int or self.link_count != 1:
            raise NativeProviderContractError("file link count must be exactly one")
        _exact_bool(self.regular_file, True, "regular_file")
        _exact_bool(self.reparse_point, False, "reparse_point")
        _exact_bool(self.handle_retained, True, "handle_retained")
        _exact_bool(self.path_published, False, "path_published")

    def private_safe_record(self) -> Mapping[str, Any]:
        return MappingProxyType(
            {
                "schema": self.schema,
                "provider_id": self.provider_id,
                "source": self.source,
                "final_path_sha256": self.final_path_sha256,
                "canonical_path_sha256": self.canonical_path_sha256,
                "volume_serial_number": self.volume_serial_number,
                "file_id": self.file_id,
                "bytes": self.bytes,
                "sha256": self.sha256,
                "link_count": self.link_count,
                "regular_file": True,
                "reparse_point": False,
                "handle_retained": True,
                "path_published": False,
            }
        )


@dataclass(frozen=True)
class NativeProcessImageAttestation:
    schema: str
    provider_id: str
    held_blender_image: NativePathIdentityAttestation
    created_process_image: NativePathIdentityAttestation
    queried_from_retained_process_handle: bool
    pid_lookup_used_as_identity: bool
    identity_equal: bool
    verified_before_resume: bool

    def __post_init__(self) -> None:
        if self.schema != NATIVE_PROCESS_IMAGE_SCHEMA:
            raise NativeProviderContractError("process image schema differs")
        provider_id = _provider_id(self.provider_id)
        if (
            type(self.held_blender_image) is not NativePathIdentityAttestation
            or type(self.created_process_image) is not NativePathIdentityAttestation
        ):
            raise NativeProviderContractError("process image identity structures differ")
        expected = self.held_blender_image
        observed = self.created_process_image
        if expected.provider_id != provider_id or observed.provider_id != provider_id:
            raise NativeProviderContractError("process image provider binding differs")
        if expected.source != "held_blender_file_handle":
            raise NativeProviderContractError("held Blender image source differs")
        if observed.source != "created_process_handle_image":
            raise NativeProviderContractError("created process image source differs")
        compared = (
            expected.canonical_path_sha256 == observed.canonical_path_sha256
            and expected.volume_serial_number == observed.volume_serial_number
            and expected.file_id == observed.file_id
            and expected.bytes == observed.bytes
            and expected.sha256 == observed.sha256
            and expected.link_count == observed.link_count == 1
        )
        if not compared:
            raise NativeProviderContractError("created process image identity differs")
        _exact_bool(
            self.queried_from_retained_process_handle,
            True,
            "queried_from_retained_process_handle",
        )
        _exact_bool(self.pid_lookup_used_as_identity, False, "pid_lookup_used_as_identity")
        _exact_bool(self.identity_equal, True, "identity_equal")
        _exact_bool(self.verified_before_resume, True, "verified_before_resume")


@dataclass(frozen=True)
class NativeProcessPolicyAttestation:
    schema: str
    provider_id: str
    interface_version: str
    lp_application_name_sha256: str
    lp_application_name_canonical_sha256: str
    argv_sha256: str
    command_line_sha256: str
    environment_block_sha256: str
    working_directory_sha256: str
    environment_entry_count: int
    creation_api: str
    creation_flags: int
    application_name_explicit: bool
    shell_used: bool
    parent_environment_inherited: bool
    unicode_environment: bool
    handles_inherited: bool
    created_suspended: bool
    job_kill_on_close: bool
    assigned_to_job_before_image_check: bool
    image_verified_before_resume: bool
    pid_used_as_process_identity: bool
    resume_count: int
    timeout_ms: int
    descendant_tree_termination_required: bool

    def __post_init__(self) -> None:
        if self.schema != NATIVE_PROCESS_POLICY_SCHEMA:
            raise NativeProviderContractError("process policy schema differs")
        _provider_id(self.provider_id)
        if self.interface_version != NATIVE_PROVIDER_INTERFACE:
            raise NativeProviderContractError("process policy interface differs")
        for label, value in (
            ("lp_application_name_sha256", self.lp_application_name_sha256),
            (
                "lp_application_name_canonical_sha256",
                self.lp_application_name_canonical_sha256,
            ),
            ("argv_sha256", self.argv_sha256),
            ("command_line_sha256", self.command_line_sha256),
            ("environment_block_sha256", self.environment_block_sha256),
            ("working_directory_sha256", self.working_directory_sha256),
        ):
            _sha256(value, label)
        if type(self.environment_entry_count) is not int or self.environment_entry_count != 6:
            raise NativeProviderContractError("environment entry count differs")
        if self.creation_api != "CreateProcessW":
            raise NativeProviderContractError("process creation API differs")
        if type(self.creation_flags) is not int or self.creation_flags != EXACT_CREATE_PROCESS_FLAGS:
            raise NativeProviderContractError("CreateProcessW flags differ")
        exact_bools = (
            ("application_name_explicit", self.application_name_explicit, True),
            ("shell_used", self.shell_used, False),
            ("parent_environment_inherited", self.parent_environment_inherited, False),
            ("unicode_environment", self.unicode_environment, True),
            ("handles_inherited", self.handles_inherited, False),
            ("created_suspended", self.created_suspended, True),
            ("job_kill_on_close", self.job_kill_on_close, True),
            (
                "assigned_to_job_before_image_check",
                self.assigned_to_job_before_image_check,
                True,
            ),
            ("image_verified_before_resume", self.image_verified_before_resume, True),
            ("pid_used_as_process_identity", self.pid_used_as_process_identity, False),
            (
                "descendant_tree_termination_required",
                self.descendant_tree_termination_required,
                True,
            ),
        )
        for label, value, expected in exact_bools:
            _exact_bool(value, expected, label)
        if type(self.resume_count) is not int or self.resume_count != 0:
            raise NativeProviderContractError("pre-resume count must be exactly zero")
        _exact_int(
            self.timeout_ms,
            "timeout_ms",
            minimum=1,
            maximum=MAX_NATIVE_RUNTIME_MS,
        )


def directory_claim_durability_contract() -> Mapping[str, Any]:
    """Return the exact future-native durability requirements.

    The current Python claim store does not satisfy this contract: it does not
    retain all directory handles, flush the parent entry, or protect records
    against same-principal rewrite/deletion after an abnormal death.
    """

    return MappingProxyType(
        {
            "schema": NATIVE_DIRECTORY_CLAIM_CONTRACT_SCHEMA,
            "platform": "Windows",
            "provider_interface": NATIVE_PROVIDER_INTERFACE,
            "directory_open_api": "CreateFileW",
            "directory_open_flags": EXACT_DIRECTORY_OPEN_FLAGS,
            "directory_share_mode": FILE_SHARE_READ,
            "unc_allowed": False,
            "reparse_traversal_allowed": False,
            "all_existing_ancestor_handles_retained": True,
            "claim_create_disposition": CREATE_NEW,
            "claim_share_mode": FILE_SHARE_NONE,
            "claim_flags_and_attributes": EXACT_DURABLE_RECORD_FLAGS,
            "claim_payload_flush_required": True,
            "claim_parent_directory_flush_required": True,
            "claim_handle_retained_through_terminal": True,
            "same_principal_rewrite_denied": True,
            "same_principal_delete_denied": True,
            "pending_claim_permanently_nonreplayable": True,
            "outcome_create_disposition": CREATE_NEW,
            "outcome_share_mode": FILE_SHARE_NONE,
            "outcome_flags_and_attributes": EXACT_DURABLE_RECORD_FLAGS,
            "outcome_payload_flush_required": True,
            "outcome_parent_directory_flush_required": True,
            "exactly_one_terminal_outcome_required": True,
            "authority_granted": False,
        }
    )


def directory_claim_durability_contract_sha256() -> str:
    return canonical_sha256(dict(directory_claim_durability_contract()))


@dataclass(frozen=True)
class NativeDirectoryIdentityAttestation:
    provider_id: str
    depth: int
    final_path: str = field(repr=False)
    final_path_sha256: str
    volume_serial_number: int
    file_id: str
    local_volume: bool
    reparse_point: bool
    handle_retained: bool
    write_delete_share_denied: bool
    path_published: bool

    def __post_init__(self) -> None:
        _provider_id(self.provider_id)
        _exact_int(self.depth, "directory depth", maximum=MAX_NATIVE_DIRECTORY_HANDLES - 1)
        path = _windows_absolute_local_path(self.final_path, "directory final path")
        if self.final_path_sha256 != private_windows_path_sha256(path):
            raise NativeProviderContractError("directory final path digest differs")
        _exact_int(
            self.volume_serial_number,
            "directory volume serial number",
            maximum=(1 << 64) - 1,
        )
        if type(self.file_id) is not str or FILE_ID_RE.fullmatch(self.file_id) is None:
            raise NativeProviderContractError("directory file identity differs")
        _exact_bool(self.local_volume, True, "directory local_volume")
        _exact_bool(self.reparse_point, False, "directory reparse_point")
        _exact_bool(self.handle_retained, True, "directory handle_retained")
        _exact_bool(
            self.write_delete_share_denied,
            True,
            "directory write_delete_share_denied",
        )
        _exact_bool(self.path_published, False, "directory path_published")

    def private_safe_record(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "depth": self.depth,
            "final_path_sha256": self.final_path_sha256,
            "volume_serial_number": self.volume_serial_number,
            "file_id": self.file_id,
            "local_volume": True,
            "reparse_point": False,
            "handle_retained": True,
            "write_delete_share_denied": True,
            "path_published": False,
        }


@dataclass(frozen=True)
class NativeClaimDurabilityAttestation:
    schema: str
    provider_id: str
    interface_version: str
    run_id: str
    claim_root_path_sha256: str
    claim_path_sha256: str
    claim_payload_sha256: str
    directory_chain: tuple[NativeDirectoryIdentityAttestation, ...]
    directory_chain_sha256: str
    contract_sha256: str
    claim_create_disposition: int
    claim_share_mode: int
    claim_flags_and_attributes: int
    claim_created_new: bool
    claim_payload_flush_succeeded: bool
    claim_parent_directory_flush_succeeded: bool
    claim_handle_retained_through_terminal: bool
    same_principal_rewrite_denied: bool
    same_principal_delete_denied: bool
    pending_claim_permanently_nonreplayable: bool
    outcome_create_new_required: bool
    outcome_payload_and_parent_flush_required: bool
    exactly_one_terminal_outcome_required: bool

    def __post_init__(self) -> None:
        if self.schema != NATIVE_CLAIM_DURABILITY_SCHEMA:
            raise NativeProviderContractError("claim durability schema differs")
        provider_id = _provider_id(self.provider_id)
        if self.interface_version != NATIVE_PROVIDER_INTERFACE:
            raise NativeProviderContractError("claim durability interface differs")
        _run_id(self.run_id)
        for label, value in (
            ("claim_root_path_sha256", self.claim_root_path_sha256),
            ("claim_path_sha256", self.claim_path_sha256),
            ("claim_payload_sha256", self.claim_payload_sha256),
            ("directory_chain_sha256", self.directory_chain_sha256),
            ("contract_sha256", self.contract_sha256),
        ):
            _sha256(value, label)
        if type(self.directory_chain) is not tuple or not self.directory_chain:
            raise NativeProviderContractError("directory identity chain is absent")
        if len(self.directory_chain) > MAX_NATIVE_DIRECTORY_HANDLES:
            raise NativeProviderContractError("directory identity chain exceeds the limit")
        records: list[dict[str, Any]] = []
        paths: list[PureWindowsPath] = []
        for index, directory in enumerate(self.directory_chain):
            if type(directory) is not NativeDirectoryIdentityAttestation:
                raise NativeProviderContractError("directory identity shape differs")
            if directory.provider_id != provider_id or directory.depth != index:
                raise NativeProviderContractError("directory identity order differs")
            current = PureWindowsPath(directory.final_path)
            if paths and current.parent != paths[-1]:
                raise NativeProviderContractError("directory identity chain is not contiguous")
            paths.append(current)
            records.append(directory.private_safe_record())
        if canonical_sha256(records) != self.directory_chain_sha256:
            raise NativeProviderContractError("directory identity chain digest differs")
        if self.claim_root_path_sha256 != self.directory_chain[-1].final_path_sha256:
            raise NativeProviderContractError("claim root identity differs from directory chain")
        if self.contract_sha256 != directory_claim_durability_contract_sha256():
            raise NativeProviderContractError("claim durability contract digest differs")
        if type(self.claim_create_disposition) is not int or self.claim_create_disposition != CREATE_NEW:
            raise NativeProviderContractError("claim create disposition differs")
        if type(self.claim_share_mode) is not int or self.claim_share_mode != FILE_SHARE_NONE:
            raise NativeProviderContractError("claim share mode differs")
        if (
            type(self.claim_flags_and_attributes) is not int
            or self.claim_flags_and_attributes != EXACT_DURABLE_RECORD_FLAGS
        ):
            raise NativeProviderContractError("claim durability flags differ")
        required_true = (
            ("claim_created_new", self.claim_created_new),
            ("claim_payload_flush_succeeded", self.claim_payload_flush_succeeded),
            (
                "claim_parent_directory_flush_succeeded",
                self.claim_parent_directory_flush_succeeded,
            ),
            (
                "claim_handle_retained_through_terminal",
                self.claim_handle_retained_through_terminal,
            ),
            ("same_principal_rewrite_denied", self.same_principal_rewrite_denied),
            ("same_principal_delete_denied", self.same_principal_delete_denied),
            (
                "pending_claim_permanently_nonreplayable",
                self.pending_claim_permanently_nonreplayable,
            ),
            ("outcome_create_new_required", self.outcome_create_new_required),
            (
                "outcome_payload_and_parent_flush_required",
                self.outcome_payload_and_parent_flush_required,
            ),
            (
                "exactly_one_terminal_outcome_required",
                self.exactly_one_terminal_outcome_required,
            ),
        )
        for label, value in required_true:
            _exact_bool(value, True, label)


@dataclass(frozen=True)
class NativeLaunchRequirements:
    schema: str
    provider_id: str
    interface_version: str
    run_id: str
    lp_application_name_sha256: str
    lp_application_name_canonical_sha256: str
    argv_sha256: str
    command_line_sha256: str
    environment_block_sha256: str
    working_directory_sha256: str
    expected_image_bytes: int
    expected_image_sha256: str
    claim_root_path_sha256: str
    claim_path_sha256: str
    claim_payload_sha256: str
    directory_path_sha256: tuple[str, ...]
    directory_chain_sha256: str
    durability_contract_sha256: str
    creation_flags: int
    timeout_ms: int
    resume_authorized: bool
    process_execution_authorized: bool

    def __post_init__(self) -> None:
        if self.schema != NATIVE_REQUIREMENTS_SCHEMA:
            raise NativeProviderContractError("native requirements schema differs")
        _provider_id(self.provider_id)
        if self.interface_version != NATIVE_PROVIDER_INTERFACE:
            raise NativeProviderContractError("native requirements interface differs")
        _run_id(self.run_id)
        for label, value in (
            ("lp_application_name_sha256", self.lp_application_name_sha256),
            (
                "lp_application_name_canonical_sha256",
                self.lp_application_name_canonical_sha256,
            ),
            ("argv_sha256", self.argv_sha256),
            ("command_line_sha256", self.command_line_sha256),
            ("environment_block_sha256", self.environment_block_sha256),
            ("working_directory_sha256", self.working_directory_sha256),
            ("expected_image_sha256", self.expected_image_sha256),
            ("claim_root_path_sha256", self.claim_root_path_sha256),
            ("claim_path_sha256", self.claim_path_sha256),
            ("claim_payload_sha256", self.claim_payload_sha256),
            ("directory_chain_sha256", self.directory_chain_sha256),
            ("durability_contract_sha256", self.durability_contract_sha256),
        ):
            _sha256(value, label)
        _exact_int(self.expected_image_bytes, "expected image bytes", minimum=1)
        if type(self.directory_path_sha256) is not tuple or not self.directory_path_sha256:
            raise NativeProviderContractError("directory path digest chain is absent")
        if len(self.directory_path_sha256) > MAX_NATIVE_DIRECTORY_HANDLES:
            raise NativeProviderContractError("directory path digest chain exceeds the limit")
        for digest in self.directory_path_sha256:
            _sha256(digest, "directory path sha256")
        expected_directory_chain_sha256 = canonical_sha256(
            [
                {"depth": index, "final_path_sha256": digest}
                for index, digest in enumerate(self.directory_path_sha256)
            ]
        )
        if self.directory_chain_sha256 != expected_directory_chain_sha256:
            raise NativeProviderContractError("directory path chain digest differs")
        if self.directory_path_sha256[-1] != self.claim_root_path_sha256:
            raise NativeProviderContractError("claim root path digest differs")
        if self.durability_contract_sha256 != directory_claim_durability_contract_sha256():
            raise NativeProviderContractError("durability contract binding differs")
        if self.creation_flags != EXACT_CREATE_PROCESS_FLAGS:
            raise NativeProviderContractError("native requirements creation flags differ")
        _exact_int(self.timeout_ms, "timeout_ms", minimum=1, maximum=MAX_NATIVE_RUNTIME_MS)
        _exact_bool(self.resume_authorized, False, "requirements resume_authorized")
        _exact_bool(
            self.process_execution_authorized,
            False,
            "requirements process_execution_authorized",
        )

    def safe_record(self) -> Mapping[str, Any]:
        return MappingProxyType(
            {
                "schema": self.schema,
                "provider_id": self.provider_id,
                "interface_version": self.interface_version,
                "run_id": self.run_id,
                "lp_application_name_sha256": self.lp_application_name_sha256,
                "lp_application_name_canonical_sha256": (
                    self.lp_application_name_canonical_sha256
                ),
                "argv_sha256": self.argv_sha256,
                "command_line_sha256": self.command_line_sha256,
                "environment_block_sha256": self.environment_block_sha256,
                "working_directory_sha256": self.working_directory_sha256,
                "expected_image_bytes": self.expected_image_bytes,
                "expected_image_sha256": self.expected_image_sha256,
                "claim_root_path_sha256": self.claim_root_path_sha256,
                "claim_path_sha256": self.claim_path_sha256,
                "claim_payload_sha256": self.claim_payload_sha256,
                "directory_path_sha256": list(self.directory_path_sha256),
                "directory_chain_sha256": self.directory_chain_sha256,
                "durability_contract_sha256": self.durability_contract_sha256,
                "creation_flags": self.creation_flags,
                "timeout_ms": self.timeout_ms,
                "resume_authorized": False,
                "process_execution_authorized": False,
            }
        )


def build_native_launch_requirements(
    *,
    provider_id: str,
    run_id: str,
    command: Sequence[str],
    environment: Mapping[str, str],
    working_directory: str,
    expected_image_bytes: int,
    expected_image_sha256: str,
    claim_path: str,
    claim_payload_sha256: str,
    directory_paths: Sequence[str],
    timeout_ms: int,
) -> NativeLaunchRequirements:
    provider = _provider_id(provider_id)
    run = _run_id(run_id)
    if type(command) not in {tuple, list} or not command:
        raise NativeProviderContractError("command is absent")
    command_values = tuple(command)
    if any(type(value) is not str or not value for value in command_values):
        raise NativeProviderContractError("command entry differs")
    application_path = _windows_absolute_local_path(
        command_values[0],
        "lpApplicationName",
    )
    working = _windows_absolute_local_path(working_directory, "working directory")
    claim = _windows_absolute_local_path(claim_path, "claim path")
    if type(directory_paths) not in {tuple, list} or not directory_paths:
        raise NativeProviderContractError("directory path chain is absent")
    if len(directory_paths) > MAX_NATIVE_DIRECTORY_HANDLES:
        raise NativeProviderContractError("directory path chain exceeds the limit")
    directories = tuple(
        _windows_absolute_local_path(value, "directory path") for value in directory_paths
    )
    if len(set(value.casefold() for value in directories)) != len(directories):
        raise NativeProviderContractError("directory path chain contains a duplicate")
    parsed = [PureWindowsPath(value) for value in directories]
    for parent, child in zip(parsed, parsed[1:]):
        if child.parent != parent:
            raise NativeProviderContractError("directory path chain is not contiguous")
    if PureWindowsPath(claim).parent != parsed[-1]:
        raise NativeProviderContractError("claim path is outside the bound claim root")
    directory_digests = tuple(private_windows_path_sha256(value) for value in directories)
    directory_records = [
        {"depth": index, "final_path_sha256": digest}
        for index, digest in enumerate(directory_digests)
    ]
    return NativeLaunchRequirements(
        schema=NATIVE_REQUIREMENTS_SCHEMA,
        provider_id=provider,
        interface_version=NATIVE_PROVIDER_INTERFACE,
        run_id=run,
        lp_application_name_sha256=private_windows_path_sha256(application_path),
        lp_application_name_canonical_sha256=canonical_windows_path_sha256(
            application_path
        ),
        argv_sha256=canonical_sha256(list(command_values)),
        command_line_sha256=windows_command_line_sha256(command_values),
        environment_block_sha256=windows_environment_block_sha256(environment),
        working_directory_sha256=private_windows_path_sha256(working),
        expected_image_bytes=_exact_int(
            expected_image_bytes,
            "expected image bytes",
            minimum=1,
        ),
        expected_image_sha256=_sha256(expected_image_sha256, "expected image sha256"),
        claim_root_path_sha256=directory_digests[-1],
        claim_path_sha256=private_windows_path_sha256(claim),
        claim_payload_sha256=_sha256(claim_payload_sha256, "claim payload sha256"),
        directory_path_sha256=directory_digests,
        directory_chain_sha256=canonical_sha256(directory_records),
        durability_contract_sha256=directory_claim_durability_contract_sha256(),
        creation_flags=EXACT_CREATE_PROCESS_FLAGS,
        timeout_ms=_exact_int(
            timeout_ms,
            "timeout_ms",
            minimum=1,
            maximum=MAX_NATIVE_RUNTIME_MS,
        ),
        resume_authorized=False,
        process_execution_authorized=False,
    )


@dataclass(frozen=True)
class NativePreResumeAttestation:
    schema: str
    provider_id: str
    interface_version: str
    requirements_sha256: str
    handles: RetainedNativeLaunchHandles
    process_image: NativeProcessImageAttestation
    process_policy: NativeProcessPolicyAttestation
    claim_durability: NativeClaimDurabilityAttestation
    process_started_suspended: bool
    resume_authorized: bool
    process_execution_authorized: bool

    def __post_init__(self) -> None:
        if self.schema != NATIVE_PRE_RESUME_SCHEMA:
            raise NativeProviderContractError("pre-resume attestation schema differs")
        provider_id = _provider_id(self.provider_id)
        if self.interface_version != NATIVE_PROVIDER_INTERFACE:
            raise NativeProviderContractError("pre-resume interface differs")
        _sha256(self.requirements_sha256, "requirements_sha256")
        if type(self.handles) is not RetainedNativeLaunchHandles:
            raise NativeProviderContractError("retained handle bundle differs")
        if type(self.process_image) is not NativeProcessImageAttestation:
            raise NativeProviderContractError("process image attestation differs")
        if type(self.process_policy) is not NativeProcessPolicyAttestation:
            raise NativeProviderContractError("process policy attestation differs")
        if type(self.claim_durability) is not NativeClaimDurabilityAttestation:
            raise NativeProviderContractError("claim durability attestation differs")
        if {
            self.handles.provider_id,
            self.process_image.provider_id,
            self.process_policy.provider_id,
            self.claim_durability.provider_id,
        } != {provider_id}:
            raise NativeProviderContractError("pre-resume provider bindings differ")
        _exact_bool(self.process_started_suspended, True, "process_started_suspended")
        _exact_bool(self.resume_authorized, False, "pre-resume resume_authorized")
        _exact_bool(
            self.process_execution_authorized,
            False,
            "pre-resume process_execution_authorized",
        )


def validate_native_pre_resume_attestation(
    attestation: NativePreResumeAttestation,
    requirements: NativeLaunchRequirements,
) -> Mapping[str, Any]:
    """Validate a pre-resume structure without trusting it as native proof."""

    if type(requirements) is not NativeLaunchRequirements:
        raise NativeProviderContractError("native requirements shape differs")
    if type(attestation) is not NativePreResumeAttestation:
        raise NativeProviderContractError("native pre-resume attestation shape differs")
    requirements_sha256 = canonical_sha256(dict(requirements.safe_record()))
    if attestation.requirements_sha256 != requirements_sha256:
        raise NativeProviderContractError("pre-resume requirements binding differs")
    if (
        attestation.provider_id != requirements.provider_id
        or attestation.interface_version != requirements.interface_version
    ):
        raise NativeProviderContractError("pre-resume provider requirement differs")
    attestation.handles.assert_all_open()
    if len(attestation.handles.directories) != len(requirements.directory_path_sha256):
        raise NativeProviderContractError("retained directory handle count differs")

    expected_image = attestation.process_image.held_blender_image
    observed_image = attestation.process_image.created_process_image
    if (
        expected_image.canonical_path_sha256
        != requirements.lp_application_name_canonical_sha256
        or expected_image.bytes != requirements.expected_image_bytes
        or expected_image.sha256 != requirements.expected_image_sha256
        or observed_image.bytes != requirements.expected_image_bytes
        or observed_image.sha256 != requirements.expected_image_sha256
    ):
        raise NativeProviderContractError("process image differs from launch requirements")

    policy = attestation.process_policy
    policy_expected = {
        "lp_application_name_sha256": requirements.lp_application_name_sha256,
        "lp_application_name_canonical_sha256": (
            requirements.lp_application_name_canonical_sha256
        ),
        "argv_sha256": requirements.argv_sha256,
        "command_line_sha256": requirements.command_line_sha256,
        "environment_block_sha256": requirements.environment_block_sha256,
        "working_directory_sha256": requirements.working_directory_sha256,
        "creation_flags": requirements.creation_flags,
        "timeout_ms": requirements.timeout_ms,
    }
    for key, expected in policy_expected.items():
        if getattr(policy, key) != expected:
            raise NativeProviderContractError(f"process policy {key} differs")

    claim = attestation.claim_durability
    observed_directory_digests = tuple(
        directory.final_path_sha256 for directory in claim.directory_chain
    )
    if (
        claim.run_id != requirements.run_id
        or claim.claim_root_path_sha256 != requirements.claim_root_path_sha256
        or claim.claim_path_sha256 != requirements.claim_path_sha256
        or claim.claim_payload_sha256 != requirements.claim_payload_sha256
        or observed_directory_digests != requirements.directory_path_sha256
        or claim.contract_sha256 != requirements.durability_contract_sha256
    ):
        raise NativeProviderContractError("claim durability differs from launch requirements")

    return MappingProxyType(
        {
            "schema": NATIVE_PRE_RESUME_SCHEMA,
            "status": NATIVE_STATIC_VALIDATION_STATUS,
            "provider_id": requirements.provider_id,
            "requirements_sha256": requirements_sha256,
            "retained_handle_shape_valid": True,
            "image_path_shape_valid": True,
            "process_policy_shape_valid": True,
            "directory_claim_shape_valid": True,
            "native_provider_reviewed": False,
            "operating_system_evidence_verified": False,
            "resume_authorized": False,
            "process_execution_authorized": False,
            "body_created": False,
            "runtime_activation_authorized": False,
            "public_export_authorized": False,
        }
    )


def static_contract_evidence_record() -> Mapping[str, Any]:
    """Machine-safe identity for the contract itself, with no private paths."""

    return MappingProxyType(
        {
            "provider_interface": NATIVE_PROVIDER_INTERFACE,
            "requirements_schema": NATIVE_REQUIREMENTS_SCHEMA,
            "path_identity_schema": NATIVE_PATH_IDENTITY_SCHEMA,
            "process_image_schema": NATIVE_PROCESS_IMAGE_SCHEMA,
            "process_policy_schema": NATIVE_PROCESS_POLICY_SCHEMA,
            "claim_durability_schema": NATIVE_CLAIM_DURABILITY_SCHEMA,
            "pre_resume_schema": NATIVE_PRE_RESUME_SCHEMA,
            "directory_claim_contract_schema": NATIVE_DIRECTORY_CLAIM_CONTRACT_SCHEMA,
            "directory_claim_contract_sha256": directory_claim_durability_contract_sha256(),
            "exact_create_process_flags": EXACT_CREATE_PROCESS_FLAGS,
            "exact_directory_open_flags": EXACT_DIRECTORY_OPEN_FLAGS,
            "exact_durable_record_flags": EXACT_DURABLE_RECORD_FLAGS,
            "review_scope": "STATIC_STRUCTURE_AND_FAKE_API_ONLY",
            "native_provider_reviewed": False,
            "operating_system_evidence_verified": False,
            "resume_authorized": False,
            "process_execution_authorized": False,
        }
    )


__all__ = [
    "CREATE_NEW",
    "CREATE_SUSPENDED",
    "CREATE_UNICODE_ENVIRONMENT",
    "EXACT_CREATE_PROCESS_FLAGS",
    "EXACT_DIRECTORY_OPEN_FLAGS",
    "EXACT_DURABLE_RECORD_FLAGS",
    "FILE_SHARE_NONE",
    "FILE_SHARE_READ",
    "MAX_NATIVE_RUNTIME_MS",
    "NATIVE_CLAIM_DURABILITY_SCHEMA",
    "NATIVE_DIRECTORY_CLAIM_CONTRACT_SCHEMA",
    "NATIVE_PATH_IDENTITY_SCHEMA",
    "NATIVE_PRE_RESUME_SCHEMA",
    "NATIVE_PROCESS_IMAGE_SCHEMA",
    "NATIVE_PROCESS_POLICY_SCHEMA",
    "NATIVE_PROVIDER_INTERFACE",
    "NATIVE_REQUIREMENTS_SCHEMA",
    "NATIVE_STATIC_VALIDATION_STATUS",
    "NativeClaimDurabilityAttestation",
    "NativeDirectoryIdentityAttestation",
    "NativeHandleCloseApi",
    "NativeLaunchRequirements",
    "NativePathIdentityAttestation",
    "NativePreResumeAttestation",
    "NativeProcessImageAttestation",
    "NativeProcessPolicyAttestation",
    "NativeProviderContractError",
    "RetainedNativeHandle",
    "RetainedNativeLaunchHandles",
    "build_native_launch_requirements",
    "canonical_windows_path_sha256",
    "canonical_sha256",
    "directory_claim_durability_contract",
    "directory_claim_durability_contract_sha256",
    "private_windows_path_sha256",
    "static_contract_evidence_record",
    "validate_native_pre_resume_attestation",
    "windows_command_line_sha256",
    "windows_environment_block_sha256",
]
