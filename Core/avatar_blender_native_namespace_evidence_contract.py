"""Static retained-handle namespace evidence for a future Blender transaction.

The two-stage transaction request deliberately stops at a lexical Windows
namespace.  This module defines the next provider boundary: every requested
path must be matched to a normalized final path and an object identity queried
through a retained handle.  Complete ancestor chains make reparse traversal,
8.3 aliases, hard-link aliases, and volume changes reviewable together.

The module calls no native API, opens no path, creates no output, and never
invokes Blender.  A shape-valid response remains untrusted provider data and
does not grant execution, body, anatomy, assignment, activation, or export
authority.
"""

from __future__ import annotations

from gc import get_referents as _imported_gc_get_referents
import weakref
from dataclasses import dataclass, field
from pathlib import PureWindowsPath
from threading import RLock
from types import BuiltinFunctionType, MappingProxyType
from typing import Any, Mapping, Protocol

from Core import avatar_blender_native_provider_contract as launch_contract
from Core import avatar_blender_native_transaction_provider_contract as transaction


NATIVE_NAMESPACE_EVIDENCE_INTERFACE = (
    "kira.blender_native_carrier_transaction_namespace_evidence_provider.v1"
)
NATIVE_NAMESPACE_RESPONSE_SCHEMA = (
    "kira.blender_native_carrier_transaction_namespace_evidence_response.v1"
)
NATIVE_NAMESPACE_TARGET_SCHEMA = (
    "kira.blender_native_carrier_transaction_namespace_target.v1"
)
NATIVE_HANDLE_PATH_EVIDENCE_SCHEMA = (
    "kira.blender_native_retained_handle_path_evidence.v1"
)
NATIVE_NAMESPACE_STATIC_STATUS = (
    "STATIC_RETAINED_NAMESPACE_SHAPE_VALID_ONLY_NO_NATIVE_AUTHORITY"
)

FINAL_PATH_QUERY_SOURCE = (
    "GetFinalPathNameByHandleW(FILE_NAME_NORMALIZED|VOLUME_NAME_DOS)"
)
FILE_ID_QUERY_SOURCE = "GetFileInformationByHandleEx(FileIdInfo)"
STANDARD_INFO_QUERY_SOURCE = "GetFileInformationByHandleEx(FileStandardInfo)"
REPARSE_QUERY_SOURCE = "GetFileInformationByHandleEx(FileAttributeTagInfo)"
VOLUME_QUERY_SOURCE = "GetVolumeInformationByHandleW"
DRIVE_TYPE_QUERY_SOURCE = "GetDriveTypeW(DRIVE_FIXED)"
ZERO_SHA256 = "0" * 64
OBJECT_KINDS = frozenset({"directory", "regular_file"})
MAX_EVIDENCE_TARGETS = 96
PYTHON_OBJECT_GRAPH_THREAT_MODEL = (
    "BOUNDED_RESPONSE_GRAPH_MUTATION_RESISTANCE_NO_ARBITRARY_IN_PROCESS_ISOLATION"
)

if (
    type(_imported_gc_get_referents) is not BuiltinFunctionType
    or _imported_gc_get_referents.__module__ != "gc"
    or _imported_gc_get_referents.__name__ != "get_referents"
):
    raise RuntimeError("canonical gc.get_referents builtin is unavailable")
_TRUSTED_GC_GET_REFERENTS = _imported_gc_get_referents
del _imported_gc_get_referents


class NativeNamespaceEvidenceContractError(ValueError):
    """The untrusted provider evidence differs from the exact static shape."""


def _build_trusted_snapshot_boundary() -> tuple[Any, ...]:
    """Keep construction identity and lifetime outside provider-writable objects.

    The returned functions close over both registries.  The registries are not
    attributes of a retained handle, path evidence, target, or response, so
    ``object.__setattr__`` against that response graph cannot rewrite them.

    This is deliberately a bounded Python object-graph defense.  It does not
    claim isolation from arbitrary code that reflects into closure cells,
    monkeypatches module globals or classes, attaches a debugger, or writes
    interpreter memory.  A future native provider still requires process and
    operating-system isolation appropriate to its review threat model.
    """

    lock = RLock()
    handle_states: dict[
        int,
        tuple[weakref.ReferenceType[object], tuple[Any, ...]],
    ] = {}
    object_snapshots: dict[
        tuple[str, int],
        tuple[weakref.ReferenceType[object], tuple[Any, ...]],
    ] = {}

    def install(
        registry: dict[Any, tuple[weakref.ReferenceType[object], tuple[Any, ...]]],
        key: Any,
        value: object,
        payload: tuple[Any, ...],
        label: str,
    ) -> None:
        with lock:
            prior = registry.get(key)
            if prior is not None and prior[0]() is not None:
                raise NativeNamespaceEvidenceContractError(
                    f"trusted {label} construction snapshot already exists"
                )

            def release(reference: weakref.ReferenceType[object]) -> None:
                with lock:
                    current = registry.get(key)
                    if current is not None and current[0] is reference:
                        del registry[key]

            reference = weakref.ref(value, release)
            registry[key] = (reference, payload)

    def lookup(
        registry: dict[Any, tuple[weakref.ReferenceType[object], tuple[Any, ...]]],
        key: Any,
        value: object,
        label: str,
    ) -> tuple[Any, ...]:
        record = registry.get(key)
        if record is None or record[0]() is not value:
            raise NativeNamespaceEvidenceContractError(
                f"trusted {label} construction snapshot is unavailable"
            )
        return record[1]

    def visible_handle_fields(handle: object) -> tuple[Any, ...]:
        try:
            return (
                object.__getattribute__(handle, "_provider_id"),
                object.__getattribute__(handle, "_kind"),
                object.__getattribute__(handle, "_native_token"),
                object.__getattribute__(handle, "_close_api"),
                object.__getattribute__(handle, "_closed"),
                object.__getattribute__(handle, "_close_epoch"),
            )
        except BaseException as exc:
            raise NativeNamespaceEvidenceContractError(
                "retained namespace handle fields are unavailable"
            ) from exc

    def assert_visible_handle(
        handle: object,
        state: tuple[Any, ...],
        *,
        expected_closed: bool,
        expected_epoch: int,
    ) -> None:
        provider, kind, token, close_api, _close_method, _phase = state
        (
            observed_provider,
            observed_kind,
            observed_token,
            observed_close_api,
            observed_closed,
            observed_epoch,
        ) = visible_handle_fields(handle)
        if (
            type(observed_provider) is not str
            or observed_provider != provider
            or type(observed_kind) is not str
            or observed_kind != kind
            or observed_token is not token
            or observed_close_api is not close_api
        ):
            raise NativeNamespaceEvidenceContractError(
                "retained namespace handle identity changed after construction"
            )
        if (
            type(observed_closed) is not bool
            or observed_closed is not expected_closed
            or type(observed_epoch) is not int
            or observed_epoch != expected_epoch
        ):
            raise NativeNamespaceEvidenceContractError(
                "retained namespace handle lifetime state differs"
            )

    def handle_state(handle: object) -> tuple[Any, ...]:
        return lookup(
            handle_states,
            id(handle),
            handle,
            "retained handle",
        )

    def replace_handle_phase(handle: object, phase: str) -> tuple[Any, ...]:
        key = id(handle)
        record = handle_states.get(key)
        if record is None or record[0]() is not handle:
            raise NativeNamespaceEvidenceContractError(
                "trusted retained handle construction snapshot is unavailable"
            )
        provider, kind, token, close_api, close_method, _prior_phase = record[1]
        updated = (provider, kind, token, close_api, close_method, phase)
        handle_states[key] = (record[0], updated)
        return updated

    def register_handle(
        handle: object,
        provider: str,
        kind: str,
        token: object,
        close_api: object,
        close_method: object,
    ) -> None:
        install(
            handle_states,
            id(handle),
            handle,
            (provider, kind, token, close_api, close_method, "open"),
            "retained handle",
        )

    def assert_handle(
        handle: object,
        provider: str,
        kind: str,
        *,
        require_open: bool,
    ) -> None:
        with lock:
            state = handle_state(handle)
            trusted_provider, trusted_kind, *_rest, phase = state
            if phase == "open":
                assert_visible_handle(
                    handle,
                    state,
                    expected_closed=False,
                    expected_epoch=0,
                )
            elif phase == "closed":
                assert_visible_handle(
                    handle,
                    state,
                    expected_closed=True,
                    expected_epoch=1,
                )
            else:
                raise NativeNamespaceEvidenceContractError(
                    "retained namespace handle lifetime state differs"
                )
            if trusted_provider != provider or trusted_kind != kind:
                raise NativeNamespaceEvidenceContractError(
                    "retained namespace handle evidence binding differs"
                )
            if require_open and phase != "open":
                raise NativeNamespaceEvidenceContractError(
                    "a required retained namespace handle closed early"
                )

    def is_handle_closed(handle: object) -> bool:
        with lock:
            state = handle_state(handle)
            provider, kind, *_rest, phase = state
            assert_handle(
                handle,
                provider,
                kind,
                require_open=False,
            )
            return phase == "closed"

    def handles_share_token(left: object, right: object) -> bool:
        with lock:
            left_state = handle_state(left)
            right_state = handle_state(right)
            assert_handle(
                left,
                left_state[0],
                left_state[1],
                require_open=False,
            )
            assert_handle(
                right,
                right_state[0],
                right_state[1],
                require_open=False,
            )
            return left_state[2] is right_state[2]

    def handles_share_close_api(left: object, right: object) -> bool:
        with lock:
            left_state = handle_state(left)
            right_state = handle_state(right)
            assert_handle(
                left,
                left_state[0],
                left_state[1],
                require_open=False,
            )
            assert_handle(
                right,
                right_state[0],
                right_state[1],
                require_open=False,
            )
            return left_state[3] is right_state[3]

    def close_handle(handle: object) -> None:
        with lock:
            state = handle_state(handle)
            provider, kind, token, _close_api, close_method, phase = state
            if phase == "closed":
                assert_visible_handle(
                    handle,
                    state,
                    expected_closed=True,
                    expected_epoch=1,
                )
                return
            if phase != "open":
                raise NativeNamespaceEvidenceContractError(
                    "retained namespace handle lifetime state differs"
                )
            assert_handle(handle, provider, kind, require_open=True)
            replace_handle_phase(handle, "closing")

        try:
            result = close_method(token)
        except BaseException as exc:
            with lock:
                replace_handle_phase(handle, "failed")
            raise NativeNamespaceEvidenceContractError(
                "native namespace handle close raised"
            ) from exc
        if result is not True:
            with lock:
                replace_handle_phase(handle, "failed")
            raise NativeNamespaceEvidenceContractError(
                "native namespace handle close was not exactly successful"
            )

        with lock:
            state = handle_state(handle)
            if state[5] != "closing":
                replace_handle_phase(handle, "failed")
                raise NativeNamespaceEvidenceContractError(
                    "retained namespace handle lifetime state differs"
                )
            try:
                assert_visible_handle(
                    handle,
                    state,
                    expected_closed=False,
                    expected_epoch=0,
                )
            except BaseException:
                replace_handle_phase(handle, "failed")
                raise
            object.__setattr__(handle, "_closed", True)
            object.__setattr__(handle, "_close_epoch", 1)
            replace_handle_phase(handle, "closed")

    def register_object_snapshot(
        label: str,
        value: object,
        snapshot: tuple[Any, ...],
    ) -> None:
        install(
            object_snapshots,
            (label, id(value)),
            value,
            snapshot,
            label,
        )

    def assert_object_snapshot(
        label: str,
        value: object,
        snapshot: tuple[Any, ...],
    ) -> None:
        def exact_match(observed: Any, trusted: Any) -> bool:
            if type(observed) is not type(trusted):
                return False
            if type(trusted) is tuple:
                return len(observed) == len(trusted) and all(
                    exact_match(left, right)
                    for left, right in zip(observed, trusted)
                )
            if type(trusted) in {str, int, bool, type(None)}:
                return observed == trusted
            return observed is trusted

        with lock:
            trusted = lookup(
                object_snapshots,
                (label, id(value)),
                value,
                label,
            )
            if not exact_match(snapshot, trusted):
                raise NativeNamespaceEvidenceContractError(
                    f"trusted {label} construction snapshot differs"
                )

    return (
        register_handle,
        assert_handle,
        is_handle_closed,
        handles_share_token,
        handles_share_close_api,
        close_handle,
        register_object_snapshot,
        assert_object_snapshot,
    )


(
    _register_trusted_handle,
    _assert_trusted_handle,
    _is_trusted_handle_closed,
    _trusted_handles_share_token,
    _trusted_handles_share_close_api,
    _close_trusted_handle,
    _register_trusted_object_snapshot,
    _assert_trusted_object_snapshot,
) = _build_trusted_snapshot_boundary()


def _exact_bool(value: Any, expected: bool, label: str) -> None:
    if type(value) is not bool or value is not expected:
        raise NativeNamespaceEvidenceContractError(
            f"{label} must be exactly {expected}"
        )


def _exact_str(value: Any, label: str) -> str:
    """Return only a real built-in string, never a comparison-spoof subclass."""

    if type(value) is not str:
        raise NativeNamespaceEvidenceContractError(f"{label} type differs")
    return value


def _exact_int(value: Any, label: str) -> int:
    """Return only a real built-in integer, excluding ``bool`` and subclasses."""

    if type(value) is not int:
        raise NativeNamespaceEvidenceContractError(f"{label} type differs")
    return value


def _exact_bytes(value: Any, label: str) -> bytes:
    if type(value) is not bytes:
        raise NativeNamespaceEvidenceContractError(f"{label} type differs")
    return value


def _exact_str_tuple(value: Any, label: str) -> tuple[str, ...]:
    """Copy an exact tuple of exact strings after all element type gates."""

    if type(value) is not tuple:
        raise NativeNamespaceEvidenceContractError(f"{label} shape differs")
    if any(type(item) is not str for item in value):
        raise NativeNamespaceEvidenceContractError(f"{label} entries differ")
    return tuple(value)


def _exact_mapping_proxy_dict_snapshot(
    value: Any,
    label: str,
) -> dict[Any, Any]:
    """Copy an exact ``dict`` backing without mapping dispatch.

    ``MappingProxyType`` can wrap an arbitrary ``Mapping`` implementation, so
    checking the proxy's public type is insufficient: calling ``items`` on a
    proxy around a hostile mapping dispatches attacker code.  CPython's GC
    traversal exposes the one directly retained backing object without calling
    that object's mapping, equality, hashing, iteration, length, or indexing
    methods.  Only an exact built-in ``dict`` may cross this boundary, and the
    returned value is a one-time built-in copy rather than the caller-owned
    backing itself.
    """

    if type(value) is not MappingProxyType:
        raise NativeNamespaceEvidenceContractError(f"{label} shape differs")
    try:
        referents = _TRUSTED_GC_GET_REFERENTS(value)
    except BaseException as exc:
        raise NativeNamespaceEvidenceContractError(
            f"{label} backing is unavailable"
        ) from exc
    if (
        type(referents) is not list
        or len(referents) != 1
        or type(referents[0]) is not dict
    ):
        raise NativeNamespaceEvidenceContractError(
            f"{label} backing must be an exact built-in dict"
        )
    return dict.copy(referents[0])


def _exact_mapping_proxy_str_record(
    value: Any,
    label: str,
) -> dict[str, str]:
    """Copy exact string pairs without hashing attacker-controlled subclasses."""

    snapshot = _exact_mapping_proxy_dict_snapshot(value, label)
    try:
        pairs = tuple(dict.items(snapshot))
    except BaseException as exc:
        raise NativeNamespaceEvidenceContractError(
            f"{label} entries are unavailable"
        ) from exc
    if any(type(pair) is not tuple or len(pair) != 2 for pair in pairs):
        raise NativeNamespaceEvidenceContractError(f"{label} entries differ")
    if any(
        type(pair[0]) is not str or type(pair[1]) is not str
        for pair in pairs
    ):
        raise NativeNamespaceEvidenceContractError(f"{label} entries differ")
    keys = tuple(pair[0] for pair in pairs)
    if len(set(keys)) != len(keys):
        raise NativeNamespaceEvidenceContractError(f"{label} keys differ")
    return {pair[0]: pair[1] for pair in pairs}


def _exact_authority_record(value: Any) -> dict[str, bool]:
    """Copy authority only after exact key/value gates precede set/dict use."""

    snapshot = _exact_mapping_proxy_dict_snapshot(
        value,
        "transaction request authority",
    )
    try:
        pairs = tuple(dict.items(snapshot))
    except BaseException as exc:
        raise NativeNamespaceEvidenceContractError(
            "transaction request authority entries are unavailable"
        ) from exc
    if any(type(pair) is not tuple or len(pair) != 2 for pair in pairs):
        raise NativeNamespaceEvidenceContractError(
            "transaction request authority entries differ"
        )
    if any(
        type(pair[0]) is not str or type(pair[1]) is not bool
        for pair in pairs
    ):
        raise NativeNamespaceEvidenceContractError(
            "transaction request authority entries differ"
        )
    keys = tuple(pair[0] for pair in pairs)
    if len(set(keys)) != len(keys) or set(keys) != set(transaction.AUTHORITY_KEYS):
        raise NativeNamespaceEvidenceContractError(
            "transaction request authority keys differ"
        )
    if any(pair[1] is not False for pair in pairs):
        raise NativeNamespaceEvidenceContractError(
            "transaction request authority must remain false"
        )
    return {pair[0]: pair[1] for pair in pairs}


def _provider_id(value: Any) -> str:
    if (
        type(value) is not str
        or launch_contract.PROVIDER_ID_RE.fullmatch(value) is None
    ):
        raise NativeNamespaceEvidenceContractError("provider_id grammar differs")
    return value


def _sha256(value: Any, label: str) -> str:
    if type(value) is not str or launch_contract.SHA256_RE.fullmatch(value) is None:
        raise NativeNamespaceEvidenceContractError(
            f"{label} must be lowercase SHA-256"
        )
    return value


def _file_id(value: Any) -> str:
    if type(value) is not str or launch_contract.FILE_ID_RE.fullmatch(value) is None:
        raise NativeNamespaceEvidenceContractError(
            "file identity must be exact 128-bit lowercase hex"
        )
    return value


def _private_path(value: Any, label: str) -> str:
    try:
        # The transaction contract has the strict component grammar used by
        # the request, including ADS, device-name, and trailing-dot rejection.
        return transaction._local_path(value, label)
    except transaction.NativeTransactionProviderContractError as exc:
        raise NativeNamespaceEvidenceContractError(
            f"{label} is not a canonical local Windows path"
        ) from exc


def _without_native_prefix(value: str) -> str:
    return value[4:] if value.startswith("\\\\?\\") else value


def _ancestor_paths(value: str) -> tuple[str, ...]:
    """Return the lexical root-to-parent chain without native-prefix aliases."""

    path = PureWindowsPath(_without_native_prefix(value))
    return tuple(
        str(PureWindowsPath(*path.parts[:depth]))
        for depth in range(1, len(path.parts))
    )


def _path_evidence_snapshot(value: Any) -> tuple[Any, ...]:
    return (
        value.schema,
        value.provider_id,
        value.kind,
        value.handle,
        value.final_normalized_path,
        value.final_path_sha256,
        value.final_canonical_path_sha256,
        value.volume_serial_number,
        value.file_id,
        value.bytes,
        value.content_sha256,
        value.link_count,
        value.local_fixed_volume,
        value.reparse_point,
        value.reparse_tag,
        value.opened_with_open_reparse_point,
        value.final_path_query_source,
        value.file_id_query_source,
        value.standard_info_query_source,
        value.reparse_query_source,
        value.volume_query_source,
        value.drive_type_query_source,
        value.handle_retained_until_terminal,
        value.path_published_before_terminal,
    )


def _target_evidence_snapshot(value: Any) -> tuple[Any, ...]:
    return (
        value.schema,
        value.provider_id,
        value.role,
        value.requested_path_sha256,
        value.requested_canonical_path_sha256,
        value.target,
        tuple(value.ancestors),
        value.created_new,
        value.observed_initially_absent,
    )


def _response_evidence_snapshot(value: Any) -> tuple[Any, ...]:
    return (
        value.schema,
        value.status,
        value.provider_id,
        value.interface_version,
        value.request_sha256,
        tuple(value.targets),
        value.provider_claimed_terminal_state,
        value.exactly_one_terminal_outcome_claimed,
        value.provider_reviewed,
        value.operating_system_evidence_verified,
        value.body_created,
    )


class NativeNamespaceHandleCloseApi(Protocol):
    """Minimal close surface held strongly by every opaque handle lease."""

    def close_handle(self, native_token: object) -> bool:
        """Return exactly ``True`` only for an exact successful close."""


class RetainedNamespaceHandle:
    """Strongly retain one opaque provider token until explicit close.

    Object retention is testable here.  Whether the token is a genuine native
    handle remains a native-provider review question.
    """

    __slots__ = (
        "_provider_id",
        "_kind",
        "_native_token",
        "_close_api",
        "_closed",
        "_close_epoch",
        "__weakref__",
    )

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise NativeNamespaceEvidenceContractError(
            "retained namespace handle fields are write-once"
        )

    def __init__(
        self,
        *,
        provider_id: str,
        kind: str,
        native_token: object,
        close_api: NativeNamespaceHandleCloseApi,
    ) -> None:
        validated_provider = _provider_id(provider_id)
        if type(kind) is not str or kind not in OBJECT_KINDS:
            raise NativeNamespaceEvidenceContractError("handle kind differs")
        if native_token is None or isinstance(
            native_token,
            (bool, int, float, complex, str, bytes, bytearray, memoryview),
        ):
            raise NativeNamespaceEvidenceContractError(
                "native handle token must be an opaque provider object"
            )
        try:
            close_method = getattr(close_api, "close_handle")
        except BaseException as exc:
            raise NativeNamespaceEvidenceContractError(
                "native close API is unavailable"
            ) from exc
        if not callable(close_method):
            raise NativeNamespaceEvidenceContractError(
                "native close API is not callable"
            )
        object.__setattr__(self, "_provider_id", validated_provider)
        object.__setattr__(self, "_kind", kind)
        object.__setattr__(self, "_native_token", native_token)
        object.__setattr__(self, "_close_api", close_api)
        object.__setattr__(self, "_closed", False)
        object.__setattr__(self, "_close_epoch", 0)
        _register_trusted_handle(
            self,
            validated_provider,
            kind,
            native_token,
            close_api,
            close_method,
        )

    @property
    def provider_id(self) -> str:
        self.assert_sealed_identity(
            provider_id=self._provider_id,
            kind=self._kind,
        )
        return self._provider_id

    @property
    def kind(self) -> str:
        self.assert_sealed_identity(
            provider_id=self._provider_id,
            kind=self._kind,
        )
        return self._kind

    @property
    def closed(self) -> bool:
        return _is_trusted_handle_closed(self)

    def assert_sealed_identity(self, *, provider_id: str, kind: str) -> None:
        expected_provider = _provider_id(provider_id)
        if type(kind) is not str or kind not in OBJECT_KINDS:
            raise NativeNamespaceEvidenceContractError(
                "retained namespace handle expected kind differs"
            )
        _assert_trusted_handle(
            self,
            expected_provider,
            kind,
            require_open=False,
        )

    def shares_native_token_with(self, other: "RetainedNamespaceHandle") -> bool:
        return (
            type(other) is RetainedNamespaceHandle
            and _trusted_handles_share_token(self, other)
        )

    def shares_close_api_with(self, other: "RetainedNamespaceHandle") -> bool:
        return (
            type(other) is RetainedNamespaceHandle
            and _trusted_handles_share_close_api(self, other)
        )

    def assert_open(self) -> None:
        _assert_trusted_handle(
            self,
            self._provider_id,
            self._kind,
            require_open=True,
        )

    def close(self) -> None:
        _close_trusted_handle(self)


@dataclass(frozen=True, slots=True, weakref_slot=True)
class NativeHandlePathEvidence:
    """One normalized path and identity queried from one retained handle."""

    schema: str
    provider_id: str
    kind: str
    handle: RetainedNamespaceHandle = field(repr=False)
    final_normalized_path: str = field(repr=False)
    final_path_sha256: str
    final_canonical_path_sha256: str
    volume_serial_number: int
    file_id: str
    bytes: int
    content_sha256: str
    link_count: int
    local_fixed_volume: bool
    reparse_point: bool
    reparse_tag: int
    opened_with_open_reparse_point: bool
    final_path_query_source: str
    file_id_query_source: str
    standard_info_query_source: str
    reparse_query_source: str
    volume_query_source: str
    drive_type_query_source: str
    handle_retained_until_terminal: bool
    path_published_before_terminal: bool

    def __post_init__(self) -> None:
        _validate_path_evidence_current_state(self)
        _register_trusted_object_snapshot(
            "path evidence",
            self,
            _path_evidence_snapshot(self),
        )

    def _validate_current_state(self) -> None:
        _validate_path_evidence_current_state(self)

    def assert_trusted_current_state(self) -> None:
        _assert_trusted_path_evidence(self)

    def safe_record(self) -> Mapping[str, Any]:
        return _canonical_path_evidence_record(self)


@dataclass(frozen=True, slots=True, weakref_slot=True)
class NativeNamespaceTargetEvidence:
    """One requested target plus its complete retained root-to-parent chain."""

    schema: str
    provider_id: str
    role: str
    requested_path_sha256: str
    requested_canonical_path_sha256: str
    target: NativeHandlePathEvidence
    ancestors: tuple[NativeHandlePathEvidence, ...]
    created_new: bool
    observed_initially_absent: bool

    def __post_init__(self) -> None:
        _validate_target_evidence_current_state(self)
        _register_trusted_object_snapshot(
            "target evidence",
            self,
            _target_evidence_snapshot(self),
        )

    def _validate_current_state(self) -> None:
        _validate_target_evidence_current_state(self)

    def assert_trusted_current_state(self) -> None:
        _assert_trusted_target_evidence(self)

    def safe_record(self) -> Mapping[str, Any]:
        return _canonical_target_evidence_record(self)


@dataclass(frozen=True, slots=True, weakref_slot=True)
class NativeNamespaceEvidenceResponse:
    """Untrusted provider response shape for terminal successful-path review."""

    schema: str
    status: str
    provider_id: str
    interface_version: str
    request_sha256: str
    targets: tuple[NativeNamespaceTargetEvidence, ...]
    provider_claimed_terminal_state: str
    exactly_one_terminal_outcome_claimed: bool
    provider_reviewed: bool
    operating_system_evidence_verified: bool
    body_created: bool

    def __post_init__(self) -> None:
        _validate_response_evidence_current_state(self)
        _register_trusted_object_snapshot(
            "response evidence",
            self,
            _response_evidence_snapshot(self),
        )

    def _validate_current_state(self) -> None:
        _validate_response_evidence_current_state(self)

    def assert_trusted_current_state(self) -> None:
        _assert_trusted_response_evidence(self)

    def safe_record(self) -> Mapping[str, Any]:
        return _canonical_response_evidence_record(self)


class NativeNamespaceTransactionRequestCapsule:
    """Opaque identity for one closure-owned clean transaction snapshot."""

    __slots__ = ("_seal", "__weakref__")

    def __new__(cls, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        del cls, args, kwargs
        raise NativeNamespaceEvidenceContractError(
            "transaction request capsules require the trusted binder"
        )

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise NativeNamespaceEvidenceContractError(
            "transaction request capsule identity is sealed"
        )

    def __getattribute__(self, name: str) -> object:
        if name == "_seal":
            raise NativeNamespaceEvidenceContractError(
                "transaction request capsule seal is opaque"
            )
        return object.__getattribute__(self, name)

    @property
    def request_sha256(self) -> str:
        return native_namespace_transaction_request_sha256(self)

    def __repr__(self) -> str:
        return "<NativeNamespaceTransactionRequestCapsule opaque>"


def _build_transaction_request_capsule_boundary():
    """Build the only binder and consumers for clean request snapshots.

    Capsule installation and resolution never become module globals.  The
    public binder exact-gates and reconstructs the complete caller request
    before it can install a capsule.  The validator wrapper receives resolved
    state only from the same private registry.  Reflection into Python closure
    cells remains outside this module's explicitly bounded threat model.
    """

    lock = RLock()
    snapshots: dict[
        int,
        tuple[
            weakref.ReferenceType[object],
            object,
            dict[str, Any],
            transaction.NativeCarrierTransactionRequest,
            str,
        ],
    ] = {}

    validator_wrapper_issued = False

    def bind(
        request: transaction.NativeCarrierTransactionRequest,
    ) -> NativeNamespaceTransactionRequestCapsule:
        record, clean_request = _capture_clean_transaction_request(request)
        request_sha256 = launch_contract.canonical_sha256(record)
        capsule = object.__new__(NativeNamespaceTransactionRequestCapsule)
        seal = object()
        object.__setattr__(capsule, "_seal", seal)
        key = id(capsule)

        def release(reference: weakref.ReferenceType[object]) -> None:
            with lock:
                current = snapshots.get(key)
                if current is not None and current[0] is reference:
                    del snapshots[key]

        reference = weakref.ref(capsule, release)
        with lock:
            if key in snapshots:
                raise NativeNamespaceEvidenceContractError(
                    "transaction request capsule identity already exists"
                )
            snapshots[key] = (
                reference,
                seal,
                record,
                clean_request,
                request_sha256,
            )
        return capsule

    def resolve_private(
        capsule: object,
    ) -> tuple[
        dict[str, Any],
        transaction.NativeCarrierTransactionRequest,
        str,
    ]:
        if type(capsule) is not NativeNamespaceTransactionRequestCapsule:
            raise NativeNamespaceEvidenceContractError(
                "transaction request capsule type differs"
            )
        with lock:
            current = snapshots.get(id(capsule))
            if current is None or current[0]() is not capsule:
                raise NativeNamespaceEvidenceContractError(
                    "transaction request capsule snapshot is unavailable"
                )
            try:
                visible_seal = object.__getattribute__(capsule, "_seal")
            except BaseException as exc:
                raise NativeNamespaceEvidenceContractError(
                    "transaction request capsule seal is unavailable"
                ) from exc
            if visible_seal is not current[1]:
                raise NativeNamespaceEvidenceContractError(
                    "transaction request capsule seal differs"
                )
            return current[2], current[3], current[4]

    def request_sha256(
        capsule: NativeNamespaceTransactionRequestCapsule,
    ) -> str:
        _record, _clean_request, digest = resolve_private(capsule)
        return digest

    def wrap_validator(callback: object):
        nonlocal validator_wrapper_issued
        if validator_wrapper_issued:
            raise RuntimeError("transaction request validator wrapper already issued")
        validator_wrapper_issued = True

        def validate(
            response: NativeNamespaceEvidenceResponse,
            capsule: NativeNamespaceTransactionRequestCapsule,
        ) -> Mapping[str, Any]:
            request_record, clean_request, digest = resolve_private(capsule)
            return callback(  # type: ignore[operator]
                response,
                request_record,
                clean_request,
                digest,
            )

        validate.__name__ = "validate_native_namespace_evidence_response"
        validate.__qualname__ = "validate_native_namespace_evidence_response"
        validate.__doc__ = (
            "Validate a response against a previously bound opaque request capsule."
        )
        return validate

    return bind, request_sha256, wrap_validator


(
    bind_native_namespace_transaction_request,
    native_namespace_transaction_request_sha256,
    _wrap_transaction_request_capsule_validator,
) = _build_transaction_request_capsule_boundary()
del _build_transaction_request_capsule_boundary


def _validate_path_evidence_current_state(
    value: NativeHandlePathEvidence,
) -> None:
    """Validate live path evidence without invoking an instance method.

    Provider-controlled objects are data at this boundary.  All recursive
    validation and serialization therefore enters through module-level
    functions and exact types, never a potentially shadowed instance method.
    """

    if type(value) is not NativeHandlePathEvidence:
        raise NativeNamespaceEvidenceContractError("path evidence type differs")
    if (
        type(value.schema) is not str
        or value.schema != NATIVE_HANDLE_PATH_EVIDENCE_SCHEMA
    ):
        raise NativeNamespaceEvidenceContractError("path evidence schema differs")
    provider = _provider_id(value.provider_id)
    if type(value.kind) is not str or value.kind not in OBJECT_KINDS:
        raise NativeNamespaceEvidenceContractError("path evidence kind differs")
    if type(value.handle) is not RetainedNamespaceHandle:
        raise NativeNamespaceEvidenceContractError(
            "path evidence retained handle differs"
        )
    _assert_trusted_handle(
        value.handle,
        provider,
        value.kind,
        require_open=True,
    )
    path = _private_path(value.final_normalized_path, "final normalized path")
    _sha256(value.final_path_sha256, "final_path_sha256")
    if value.final_path_sha256 != launch_contract.private_windows_path_sha256(path):
        raise NativeNamespaceEvidenceContractError(
            "final normalized path digest differs"
        )
    _sha256(
        value.final_canonical_path_sha256,
        "final_canonical_path_sha256",
    )
    if (
        value.final_canonical_path_sha256
        != launch_contract.canonical_windows_path_sha256(path)
    ):
        raise NativeNamespaceEvidenceContractError(
            "final canonical path digest differs"
        )
    if (
        type(value.volume_serial_number) is not int
        or value.volume_serial_number < 0
        or value.volume_serial_number > (1 << 64) - 1
    ):
        raise NativeNamespaceEvidenceContractError("volume identity differs")
    _file_id(value.file_id)
    _sha256(value.content_sha256, "content_sha256")
    if type(value.link_count) is not int or value.link_count != 1:
        raise NativeNamespaceEvidenceContractError(
            "hard-link count must be exactly one"
        )
    if value.kind == "directory":
        if type(value.bytes) is not int or value.bytes != 0:
            raise NativeNamespaceEvidenceContractError(
                "directory byte count must be zero"
            )
        if value.content_sha256 != ZERO_SHA256:
            raise NativeNamespaceEvidenceContractError(
                "directory content digest sentinel differs"
            )
    else:
        if type(value.bytes) is not int or value.bytes < 1:
            raise NativeNamespaceEvidenceContractError(
                "regular file byte count must be positive"
            )
        if value.content_sha256 == ZERO_SHA256:
            raise NativeNamespaceEvidenceContractError(
                "regular file content digest is absent"
            )
    _exact_bool(value.local_fixed_volume, True, "local_fixed_volume")
    _exact_bool(value.reparse_point, False, "reparse_point")
    if type(value.reparse_tag) is not int or value.reparse_tag != 0:
        raise NativeNamespaceEvidenceContractError(
            "reparse tag must be exactly zero"
        )
    _exact_bool(
        value.opened_with_open_reparse_point,
        True,
        "opened_with_open_reparse_point",
    )
    expected_sources = (
        (value.final_path_query_source, FINAL_PATH_QUERY_SOURCE, "final path"),
        (value.file_id_query_source, FILE_ID_QUERY_SOURCE, "file id"),
        (
            value.standard_info_query_source,
            STANDARD_INFO_QUERY_SOURCE,
            "standard info",
        ),
        (value.reparse_query_source, REPARSE_QUERY_SOURCE, "reparse"),
        (value.volume_query_source, VOLUME_QUERY_SOURCE, "volume"),
        (value.drive_type_query_source, DRIVE_TYPE_QUERY_SOURCE, "drive type"),
    )
    for observed, expected, label in expected_sources:
        if type(observed) is not str or observed != expected:
            raise NativeNamespaceEvidenceContractError(
                f"{label} query source differs"
            )
    _exact_bool(
        value.handle_retained_until_terminal,
        True,
        "handle_retained_until_terminal",
    )
    _exact_bool(
        value.path_published_before_terminal,
        False,
        "path_published_before_terminal",
    )


def _assert_trusted_path_evidence(value: NativeHandlePathEvidence) -> None:
    _validate_path_evidence_current_state(value)
    _assert_trusted_object_snapshot(
        "path evidence",
        value,
        _path_evidence_snapshot(value),
    )


def _canonical_path_evidence_record(
    value: NativeHandlePathEvidence,
) -> Mapping[str, Any]:
    _assert_trusted_path_evidence(value)
    return MappingProxyType(
        {
            "schema": value.schema,
            "provider_id": value.provider_id,
            "kind": value.kind,
            "final_path_sha256": value.final_path_sha256,
            "final_canonical_path_sha256": value.final_canonical_path_sha256,
            "volume_serial_number": value.volume_serial_number,
            "file_id": value.file_id,
            "bytes": value.bytes,
            "content_sha256": value.content_sha256,
            "link_count": value.link_count,
            "local_fixed_volume": value.local_fixed_volume,
            "reparse_point": value.reparse_point,
            "reparse_tag": value.reparse_tag,
            "opened_with_open_reparse_point": (
                value.opened_with_open_reparse_point
            ),
            "final_path_query_source": value.final_path_query_source,
            "file_id_query_source": value.file_id_query_source,
            "standard_info_query_source": value.standard_info_query_source,
            "reparse_query_source": value.reparse_query_source,
            "volume_query_source": value.volume_query_source,
            "drive_type_query_source": value.drive_type_query_source,
            "handle_retained_until_terminal": (
                value.handle_retained_until_terminal
            ),
            "path_published_before_terminal": (
                value.path_published_before_terminal
            ),
        }
    )


def _validate_target_evidence_current_state(
    value: NativeNamespaceTargetEvidence,
) -> None:
    if type(value) is not NativeNamespaceTargetEvidence:
        raise NativeNamespaceEvidenceContractError("target evidence type differs")
    if (
        type(value.schema) is not str
        or value.schema != NATIVE_NAMESPACE_TARGET_SCHEMA
    ):
        raise NativeNamespaceEvidenceContractError("target schema differs")
    provider = _provider_id(value.provider_id)
    if type(value.role) is not str or not value.role or len(value.role) > 96:
        raise NativeNamespaceEvidenceContractError("target role differs")
    _sha256(value.requested_path_sha256, "requested_path_sha256")
    _sha256(
        value.requested_canonical_path_sha256,
        "requested_canonical_path_sha256",
    )
    if type(value.target) is not NativeHandlePathEvidence:
        raise NativeNamespaceEvidenceContractError("target object differs")
    _assert_trusted_path_evidence(value.target)
    if value.target.provider_id != provider:
        raise NativeNamespaceEvidenceContractError("target object differs")
    if type(value.ancestors) is not tuple or any(
        type(child) is not NativeHandlePathEvidence for child in value.ancestors
    ):
        raise NativeNamespaceEvidenceContractError("target ancestors differ")
    if len(value.ancestors) > launch_contract.MAX_NATIVE_DIRECTORY_HANDLES:
        raise NativeNamespaceEvidenceContractError(
            "target ancestor count exceeds the retained-handle limit"
        )
    if type(value.created_new) is not bool:
        raise NativeNamespaceEvidenceContractError("created_new type differs")
    _exact_bool(
        value.observed_initially_absent,
        value.created_new,
        "observed_initially_absent",
    )
    for child in value.ancestors:
        _assert_trusted_path_evidence(child)
        if child.provider_id != provider or child.kind != "directory":
            raise NativeNamespaceEvidenceContractError("target ancestors differ")


def _assert_trusted_target_evidence(
    value: NativeNamespaceTargetEvidence,
) -> None:
    _validate_target_evidence_current_state(value)
    _assert_trusted_object_snapshot(
        "target evidence",
        value,
        _target_evidence_snapshot(value),
    )


def _canonical_target_evidence_record(
    value: NativeNamespaceTargetEvidence,
) -> Mapping[str, Any]:
    _assert_trusted_target_evidence(value)
    return MappingProxyType(
        {
            "schema": value.schema,
            "provider_id": value.provider_id,
            "role": value.role,
            "requested_path_sha256": value.requested_path_sha256,
            "requested_canonical_path_sha256": (
                value.requested_canonical_path_sha256
            ),
            "target": dict(_canonical_path_evidence_record(value.target)),
            "ancestors": [
                dict(_canonical_path_evidence_record(child))
                for child in value.ancestors
            ],
            "created_new": value.created_new,
            "observed_initially_absent": value.observed_initially_absent,
        }
    )


def _validate_response_evidence_current_state(
    value: NativeNamespaceEvidenceResponse,
) -> None:
    if type(value) is not NativeNamespaceEvidenceResponse:
        raise NativeNamespaceEvidenceContractError("response evidence type differs")
    if (
        type(value.schema) is not str
        or value.schema != NATIVE_NAMESPACE_RESPONSE_SCHEMA
    ):
        raise NativeNamespaceEvidenceContractError("response schema differs")
    if (
        type(value.status) is not str
        or value.status != NATIVE_NAMESPACE_STATIC_STATUS
    ):
        raise NativeNamespaceEvidenceContractError("response status differs")
    provider = _provider_id(value.provider_id)
    if (
        type(value.interface_version) is not str
        or value.interface_version != NATIVE_NAMESPACE_EVIDENCE_INTERFACE
    ):
        raise NativeNamespaceEvidenceContractError("response interface differs")
    _sha256(value.request_sha256, "request_sha256")
    if type(value.targets) is not tuple or not value.targets:
        raise NativeNamespaceEvidenceContractError("response targets differ")
    if len(value.targets) > MAX_EVIDENCE_TARGETS or any(
        type(child) is not NativeNamespaceTargetEvidence
        for child in value.targets
    ):
        raise NativeNamespaceEvidenceContractError("response targets differ")
    if (
        type(value.provider_claimed_terminal_state) is not str
        or value.provider_claimed_terminal_state != "succeeded"
    ):
        raise NativeNamespaceEvidenceContractError(
            "provider terminal-state claim differs"
        )
    _exact_bool(
        value.exactly_one_terminal_outcome_claimed,
        True,
        "exactly_one_terminal_outcome_claimed",
    )
    _exact_bool(value.provider_reviewed, False, "provider_reviewed")
    _exact_bool(
        value.operating_system_evidence_verified,
        False,
        "operating_system_evidence_verified",
    )
    _exact_bool(value.body_created, False, "body_created")
    for child in value.targets:
        _assert_trusted_target_evidence(child)
        if child.provider_id != provider:
            raise NativeNamespaceEvidenceContractError("response targets differ")


def _assert_trusted_response_evidence(
    value: NativeNamespaceEvidenceResponse,
) -> None:
    _validate_response_evidence_current_state(value)
    _assert_trusted_object_snapshot(
        "response evidence",
        value,
        _response_evidence_snapshot(value),
    )


def _canonical_response_evidence_record(
    value: NativeNamespaceEvidenceResponse,
) -> Mapping[str, Any]:
    _assert_trusted_response_evidence(value)
    return MappingProxyType(
        {
            "schema": value.schema,
            "status": value.status,
            "provider_id": value.provider_id,
            "interface_version": value.interface_version,
            "request_sha256": value.request_sha256,
            "targets": [
                dict(_canonical_target_evidence_record(child))
                for child in value.targets
            ],
            "provider_claimed_terminal_state": (
                value.provider_claimed_terminal_state
            ),
            "exactly_one_terminal_outcome_claimed": (
                value.exactly_one_terminal_outcome_claimed
            ),
            "provider_reviewed": value.provider_reviewed,
            "operating_system_evidence_verified": (
                value.operating_system_evidence_verified
            ),
            "body_created": value.body_created,
        }
    )


class NativeNamespaceEvidenceProvider(Protocol):
    """Future native surface; this module never discovers or invokes it."""

    provider_id: str
    interface_version: str

    def collect_terminal_namespace_evidence(
        self,
        request: transaction.NativeCarrierTransactionRequest,
    ) -> object:
        """Return untrusted retained-handle evidence for static validation."""


@dataclass(frozen=True)
class _ExpectedTarget:
    role: str
    path: str
    path_sha256: str
    canonical_path_sha256: str
    kind: str
    created_new: bool
    expected_bytes: int | None = None
    expected_content_sha256: str | None = None


def _expected_targets(
    request: transaction.NativeCarrierTransactionRequest,
) -> tuple[_ExpectedTarget, ...]:
    image_path = request.stages[0].command[0]
    values: list[_ExpectedTarget] = [
        _ExpectedTarget(
            role="blender_image",
            path=image_path,
            path_sha256=launch_contract.private_windows_path_sha256(image_path),
            canonical_path_sha256=request.expected_blender_image_canonical_path_sha256,
            kind="regular_file",
            created_new=False,
            expected_bytes=request.expected_blender_image_bytes,
            expected_content_sha256=request.expected_blender_image_sha256,
        ),
        _ExpectedTarget(
            role="working_directory",
            path=request.working_directory,
            path_sha256=request.working_directory_sha256,
            canonical_path_sha256=launch_contract.canonical_windows_path_sha256(
                request.working_directory
            ),
            kind="directory",
            created_new=False,
        ),
    ]
    values.extend(
        _ExpectedTarget(
            role=f"directory:{index}",
            path=path,
            path_sha256=request.directory_path_sha256[index],
            canonical_path_sha256=request.directory_canonical_path_sha256[index],
            kind="directory",
            created_new=False,
        )
        for index, path in enumerate(request.directory_paths)
    )
    values.extend(
        _ExpectedTarget(
            role=f"output:{reservation.role}",
            path=reservation.path,
            path_sha256=reservation.path_sha256,
            canonical_path_sha256=reservation.canonical_path_sha256,
            kind="regular_file",
            created_new=True,
        )
        for reservation in request.outputs
    )
    values.extend(
        (
            _ExpectedTarget(
                role="claim",
                path=request.claim_path,
                path_sha256=request.claim_path_sha256,
                canonical_path_sha256=request.claim_canonical_path_sha256,
                kind="regular_file",
                created_new=True,
            ),
            _ExpectedTarget(
                role="outcome",
                path=request.outcome_path,
                path_sha256=request.outcome_path_sha256,
                canonical_path_sha256=request.outcome_canonical_path_sha256,
                kind="regular_file",
                created_new=True,
            ),
        )
    )
    return tuple(values)


def _validate_handle_population(
    objects: tuple[NativeHandlePathEvidence, ...],
) -> None:
    unique: list[NativeHandlePathEvidence] = []
    by_canonical_path: dict[str, NativeHandlePathEvidence] = {}
    by_file_identity: dict[tuple[int, str], NativeHandlePathEvidence] = {}
    for value in objects:
        _assert_trusted_handle(
            value.handle,
            value.provider_id,
            value.kind,
            require_open=True,
        )
        prior_path = by_canonical_path.get(value.final_canonical_path_sha256)
        if prior_path is not None:
            if prior_path is not value:
                raise NativeNamespaceEvidenceContractError(
                    "one canonical path used multiple evidence objects"
                )
            continue
        identity = (value.volume_serial_number, value.file_id)
        prior_identity = by_file_identity.get(identity)
        if prior_identity is not None:
            raise NativeNamespaceEvidenceContractError(
                "distinct normalized paths alias one volume and file identity"
            )
        if unique:
            first = unique[0].handle
            if not _trusted_handles_share_close_api(first, value.handle):
                raise NativeNamespaceEvidenceContractError(
                    "retained namespace handle close APIs differ"
                )
            for prior in unique:
                if _trusted_handles_share_token(prior.handle, value.handle):
                    raise NativeNamespaceEvidenceContractError(
                        "retained namespace handle tokens alias"
                    )
        by_canonical_path[value.final_canonical_path_sha256] = value
        by_file_identity[identity] = value
        unique.append(value)


def _canonical_transaction_stage_record(value: Any) -> dict[str, Any]:
    if type(value) is not transaction.NativeTransactionStageRequest:
        raise NativeNamespaceEvidenceContractError(
            "transaction request stage shape differs"
        )
    schema = _exact_str(value.schema, "transaction stage schema")
    stage_id = _exact_str(value.stage_id, "transaction stage id")
    ordinal = _exact_int(value.ordinal, "transaction stage ordinal")
    worker_role = _exact_str(value.worker_role, "transaction stage worker role")
    _exact_str_tuple(value.command, "transaction stage command")
    argv_sha256 = _exact_str(value.argv_sha256, "transaction stage argv digest")
    command_line_sha256 = _exact_str(
        value.command_line_sha256,
        "transaction stage command-line digest",
    )
    timeout_ms = _exact_int(value.timeout_ms, "transaction stage timeout")
    bool_fields = {
        "candidate_custody_required_before_launch": (
            value.candidate_custody_required_before_launch
        ),
        "created_suspended_required": value.created_suspended_required,
        "job_assignment_before_image_check_required": (
            value.job_assignment_before_image_check_required
        ),
        "image_query_from_retained_process_handle_required": (
            value.image_query_from_retained_process_handle_required
        ),
        "pid_process_identity_forbidden": value.pid_process_identity_forbidden,
        "exactly_one_resume_required": value.exactly_one_resume_required,
        "completion_required_before_next_phase": (
            value.completion_required_before_next_phase
        ),
        "process_execution_authorized": value.process_execution_authorized,
    }
    if any(type(item) is not bool for item in bool_fields.values()):
        raise NativeNamespaceEvidenceContractError(
            "transaction stage boolean field type differs"
        )
    return {
        "schema": schema,
        "stage_id": stage_id,
        "ordinal": ordinal,
        "worker_role": worker_role,
        "argv_sha256": argv_sha256,
        "command_line_sha256": command_line_sha256,
        "timeout_ms": timeout_ms,
        "candidate_custody_required_before_launch": (
            bool_fields["candidate_custody_required_before_launch"]
        ),
        "created_suspended_required": bool_fields["created_suspended_required"],
        "job_assignment_before_image_check_required": (
            bool_fields["job_assignment_before_image_check_required"]
        ),
        "image_query_from_retained_process_handle_required": (
            bool_fields["image_query_from_retained_process_handle_required"]
        ),
        "pid_process_identity_forbidden": bool_fields[
            "pid_process_identity_forbidden"
        ],
        "exactly_one_resume_required": bool_fields["exactly_one_resume_required"],
        "completion_required_before_next_phase": (
            bool_fields["completion_required_before_next_phase"]
        ),
        "process_execution_authorized": bool_fields[
            "process_execution_authorized"
        ],
    }


def _canonical_transaction_output_record(value: Any) -> dict[str, Any]:
    if type(value) is not transaction.NativeTransactionOutputReservation:
        raise NativeNamespaceEvidenceContractError(
            "transaction request output shape differs"
        )
    schema = _exact_str(value.schema, "transaction output schema")
    role = _exact_str(value.role, "transaction output role")
    custody_phase = _exact_str(
        value.custody_phase,
        "transaction output custody phase",
    )
    _exact_str(value.path, "transaction output path")
    path_sha256 = _exact_str(value.path_sha256, "transaction output path digest")
    canonical_path_sha256 = _exact_str(
        value.canonical_path_sha256,
        "transaction output canonical path digest",
    )
    bool_fields = {
        "create_new_required": value.create_new_required,
        "initially_absent_required": value.initially_absent_required,
        "handle_retained_from_creation_until_terminal": (
            value.handle_retained_from_creation_until_terminal
        ),
        "validate_from_retained_handle_required": (
            value.validate_from_retained_handle_required
        ),
        "path_publication_before_terminal": (
            value.path_publication_before_terminal
        ),
    }
    if any(type(item) is not bool for item in bool_fields.values()):
        raise NativeNamespaceEvidenceContractError(
            "transaction output boolean field type differs"
        )
    return {
        "schema": schema,
        "role": role,
        "custody_phase": custody_phase,
        "path_sha256": path_sha256,
        "canonical_path_sha256": canonical_path_sha256,
        "create_new_required": bool_fields["create_new_required"],
        "initially_absent_required": bool_fields["initially_absent_required"],
        "handle_retained_from_creation_until_terminal": (
            bool_fields["handle_retained_from_creation_until_terminal"]
        ),
        "validate_from_retained_handle_required": (
            bool_fields["validate_from_retained_handle_required"]
        ),
        "path_publication_before_terminal": (
            bool_fields["path_publication_before_terminal"]
        ),
    }


def _capture_clean_transaction_stage(
    value: Any,
) -> tuple[dict[str, Any], transaction.NativeTransactionStageRequest]:
    """Capture exact stage scalars, then construct a method-shadow-free stage."""

    record = _canonical_transaction_stage_record(value)
    command = _exact_str_tuple(value.command, "transaction stage command")
    clean = transaction.NativeTransactionStageRequest(
        schema=record["schema"],
        stage_id=record["stage_id"],
        ordinal=record["ordinal"],
        worker_role=record["worker_role"],
        command=command,
        argv_sha256=record["argv_sha256"],
        command_line_sha256=record["command_line_sha256"],
        timeout_ms=record["timeout_ms"],
        candidate_custody_required_before_launch=record[
            "candidate_custody_required_before_launch"
        ],
        created_suspended_required=record["created_suspended_required"],
        job_assignment_before_image_check_required=record[
            "job_assignment_before_image_check_required"
        ],
        image_query_from_retained_process_handle_required=record[
            "image_query_from_retained_process_handle_required"
        ],
        pid_process_identity_forbidden=record["pid_process_identity_forbidden"],
        exactly_one_resume_required=record["exactly_one_resume_required"],
        completion_required_before_next_phase=record[
            "completion_required_before_next_phase"
        ],
        process_execution_authorized=record["process_execution_authorized"],
    )
    return record, clean


def _capture_clean_transaction_output(
    value: Any,
) -> tuple[dict[str, Any], transaction.NativeTransactionOutputReservation]:
    """Capture exact output scalars, then construct a clean reservation."""

    record = _canonical_transaction_output_record(value)
    path = _exact_str(value.path, "transaction output path")
    clean = transaction.NativeTransactionOutputReservation(
        schema=record["schema"],
        role=record["role"],
        custody_phase=record["custody_phase"],
        path=path,
        path_sha256=record["path_sha256"],
        canonical_path_sha256=record["canonical_path_sha256"],
        create_new_required=record["create_new_required"],
        initially_absent_required=record["initially_absent_required"],
        handle_retained_from_creation_until_terminal=record[
            "handle_retained_from_creation_until_terminal"
        ],
        validate_from_retained_handle_required=record[
            "validate_from_retained_handle_required"
        ],
        path_publication_before_terminal=record[
            "path_publication_before_terminal"
        ],
    )
    return record, clean


def _capture_clean_transaction_request(
    request: transaction.NativeCarrierTransactionRequest,
) -> tuple[dict[str, Any], transaction.NativeCarrierTransactionRequest]:
    """Type-gate the entire live request before comparison, hashing or rebuild.

    The upstream request classes are frozen but intentionally not slotted.
    Therefore, this boundary treats every declared value as hostile after
    construction.  Exact built-in scalar/container checks happen before a
    value can reach equality, membership, mapping lookup, canonical hashing,
    serialization, or an upstream constructor.
    """

    if type(request) is not transaction.NativeCarrierTransactionRequest:
        raise NativeNamespaceEvidenceContractError(
            "transaction request shape differs"
        )

    exact_string_fields = (
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
    strings = {
        name: _exact_str(getattr(request, name), f"transaction request {name}")
        for name in exact_string_fields
    }
    source_closure_bytes = _exact_bytes(
        request.source_closure_canonical_json,
        "transaction request source closure bytes",
    )
    expected_blender_image_bytes = _exact_int(
        request.expected_blender_image_bytes,
        "transaction request Blender image byte count",
    )

    bool_field_names = (
        "source_single_launch_interface_is_insufficient",
        "claim_create_new_required",
        "claim_payload_and_parent_flush_required",
        "claim_handle_retained_until_terminal",
        "outcome_create_new_required",
        "outcome_payload_and_parent_flush_required",
        "exactly_one_terminal_outcome_required",
        "provider_reviewed",
        "operating_system_evidence_verified",
    )
    bools = {name: getattr(request, name) for name in bool_field_names}
    if any(type(item) is not bool for item in bools.values()):
        raise NativeNamespaceEvidenceContractError(
            "transaction request boolean field type differs"
        )

    stages = request.stages
    if type(stages) is not tuple or any(
        type(item) is not transaction.NativeTransactionStageRequest
        for item in stages
    ):
        raise NativeNamespaceEvidenceContractError(
            "transaction request stages differ"
        )
    outputs = request.outputs
    if type(outputs) is not tuple or any(
        type(item) is not transaction.NativeTransactionOutputReservation
        for item in outputs
    ):
        raise NativeNamespaceEvidenceContractError(
            "transaction request outputs differ"
        )
    captured_stages = tuple(
        _capture_clean_transaction_stage(item) for item in stages
    )
    captured_outputs = tuple(
        _capture_clean_transaction_output(item) for item in outputs
    )
    stage_records = [item[0] for item in captured_stages]
    clean_stages = tuple(item[1] for item in captured_stages)
    output_records = [item[0] for item in captured_outputs]
    clean_outputs = tuple(item[1] for item in captured_outputs)

    transaction_phases = _exact_str_tuple(
        request.transaction_phases,
        "transaction request phase sequence",
    )
    directory_paths = _exact_str_tuple(
        request.directory_paths,
        "transaction request directory paths",
    )
    directory_path_sha256 = _exact_str_tuple(
        request.directory_path_sha256,
        "transaction request directory path digests",
    )
    directory_canonical_path_sha256 = _exact_str_tuple(
        request.directory_canonical_path_sha256,
        "transaction request canonical directory path digests",
    )
    environment = _exact_mapping_proxy_str_record(
        request.environment,
        "transaction request environment",
    )
    authority = _exact_authority_record(request.authority)

    record = {
        "schema": strings["schema"],
        "status": strings["status"],
        "provider_id": strings["provider_id"],
        "interface_version": strings["interface_version"],
        "operation": strings["operation"],
        "run_id": strings["run_id"],
        "candidate_id": strings["candidate_id"],
        "source_closure_schema": strings["source_closure_schema"],
        "source_closure_status": strings["source_closure_status"],
        "source_closure_sha256": strings["source_closure_sha256"],
        "input_closure_sha256": strings["input_closure_sha256"],
        "output_closure_sha256": strings["output_closure_sha256"],
        "source_single_launch_interface": strings[
            "source_single_launch_interface"
        ],
        "source_single_launch_interface_is_insufficient": bools[
            "source_single_launch_interface_is_insufficient"
        ],
        "stages": stage_records,
        "outputs": output_records,
        "transaction_phases": list(transaction_phases),
        "environment_block_sha256": strings["environment_block_sha256"],
        "working_directory_sha256": strings["working_directory_sha256"],
        "expected_blender_image_bytes": expected_blender_image_bytes,
        "expected_blender_image_sha256": strings[
            "expected_blender_image_sha256"
        ],
        "expected_blender_image_path_sha256": strings[
            "expected_blender_image_path_sha256"
        ],
        "expected_blender_image_canonical_path_sha256": strings[
            "expected_blender_image_canonical_path_sha256"
        ],
        "directory_path_sha256": list(directory_path_sha256),
        "directory_canonical_path_sha256": list(
            directory_canonical_path_sha256
        ),
        "directory_chain_sha256": strings["directory_chain_sha256"],
        "claim_root_path_sha256": strings["claim_root_path_sha256"],
        "claim_root_canonical_path_sha256": strings[
            "claim_root_canonical_path_sha256"
        ],
        "claim_path_sha256": strings["claim_path_sha256"],
        "claim_canonical_path_sha256": strings[
            "claim_canonical_path_sha256"
        ],
        "outcome_path_sha256": strings["outcome_path_sha256"],
        "outcome_canonical_path_sha256": strings[
            "outcome_canonical_path_sha256"
        ],
        "durability_contract_sha256": strings["durability_contract_sha256"],
        "claim_create_new_required": bools["claim_create_new_required"],
        "claim_payload_and_parent_flush_required": bools[
            "claim_payload_and_parent_flush_required"
        ],
        "claim_handle_retained_until_terminal": bools[
            "claim_handle_retained_until_terminal"
        ],
        "outcome_create_new_required": bools["outcome_create_new_required"],
        "outcome_payload_and_parent_flush_required": bools[
            "outcome_payload_and_parent_flush_required"
        ],
        "exactly_one_terminal_outcome_required": bools[
            "exactly_one_terminal_outcome_required"
        ],
        "provider_reviewed": bools["provider_reviewed"],
        "operating_system_evidence_verified": bools[
            "operating_system_evidence_verified"
        ],
        "authority": authority,
    }
    try:
        transaction.validate_static_native_transaction_request_record(record)
    except transaction.NativeTransactionProviderContractError as exc:
        raise NativeNamespaceEvidenceContractError(
            "transaction request safe record is invalid"
        ) from exc

    try:
        clean_request = transaction.NativeCarrierTransactionRequest(
            schema=strings["schema"],
            status=strings["status"],
            provider_id=strings["provider_id"],
            interface_version=strings["interface_version"],
            operation=strings["operation"],
            run_id=strings["run_id"],
            candidate_id=strings["candidate_id"],
            source_closure_schema=strings["source_closure_schema"],
            source_closure_status=strings["source_closure_status"],
            source_closure_canonical_json=source_closure_bytes,
            source_closure_sha256=strings["source_closure_sha256"],
            input_closure_sha256=strings["input_closure_sha256"],
            output_closure_sha256=strings["output_closure_sha256"],
            source_single_launch_interface=strings[
                "source_single_launch_interface"
            ],
            source_single_launch_interface_is_insufficient=bools[
                "source_single_launch_interface_is_insufficient"
            ],
            stages=clean_stages,
            outputs=clean_outputs,
            transaction_phases=transaction_phases,
            environment=MappingProxyType(environment),
            environment_block_sha256=strings["environment_block_sha256"],
            working_directory=strings["working_directory"],
            working_directory_sha256=strings["working_directory_sha256"],
            expected_blender_image_bytes=expected_blender_image_bytes,
            expected_blender_image_sha256=strings[
                "expected_blender_image_sha256"
            ],
            expected_blender_image_path_sha256=strings[
                "expected_blender_image_path_sha256"
            ],
            expected_blender_image_canonical_path_sha256=strings[
                "expected_blender_image_canonical_path_sha256"
            ],
            directory_paths=directory_paths,
            directory_path_sha256=directory_path_sha256,
            directory_canonical_path_sha256=directory_canonical_path_sha256,
            directory_chain_sha256=strings["directory_chain_sha256"],
            claim_root_path=strings["claim_root_path"],
            claim_root_path_sha256=strings["claim_root_path_sha256"],
            claim_root_canonical_path_sha256=strings[
                "claim_root_canonical_path_sha256"
            ],
            claim_path=strings["claim_path"],
            claim_path_sha256=strings["claim_path_sha256"],
            claim_canonical_path_sha256=strings[
                "claim_canonical_path_sha256"
            ],
            outcome_path=strings["outcome_path"],
            outcome_path_sha256=strings["outcome_path_sha256"],
            outcome_canonical_path_sha256=strings[
                "outcome_canonical_path_sha256"
            ],
            durability_contract_sha256=strings["durability_contract_sha256"],
            claim_create_new_required=bools["claim_create_new_required"],
            claim_payload_and_parent_flush_required=bools[
                "claim_payload_and_parent_flush_required"
            ],
            claim_handle_retained_until_terminal=bools[
                "claim_handle_retained_until_terminal"
            ],
            outcome_create_new_required=bools["outcome_create_new_required"],
            outcome_payload_and_parent_flush_required=bools[
                "outcome_payload_and_parent_flush_required"
            ],
            exactly_one_terminal_outcome_required=bools[
                "exactly_one_terminal_outcome_required"
            ],
            provider_reviewed=bools["provider_reviewed"],
            operating_system_evidence_verified=bools[
                "operating_system_evidence_verified"
            ],
            authority=MappingProxyType(authority),
        )
    except (transaction.NativeTransactionProviderContractError, TypeError) as exc:
        raise NativeNamespaceEvidenceContractError(
            "transaction request is invalid"
        ) from exc
    return record, clean_request


def _validate_resolved_native_namespace_evidence_response(
    response: NativeNamespaceEvidenceResponse,
    request_record: dict[str, Any],
    clean_request: transaction.NativeCarrierTransactionRequest,
    request_sha256: str,
) -> Mapping[str, Any]:
    """Validate resolved capsule state with every execution authority false."""

    if type(response) is not NativeNamespaceEvidenceResponse:
        raise NativeNamespaceEvidenceContractError("namespace response shape differs")
    _assert_trusted_response_evidence(response)
    if (
        response.provider_id != clean_request.provider_id
        or response.request_sha256 != request_sha256
    ):
        raise NativeNamespaceEvidenceContractError(
            "namespace response request binding differs"
        )

    expected = _expected_targets(clean_request)
    if tuple(value.role for value in response.targets) != tuple(
        value.role for value in expected
    ):
        raise NativeNamespaceEvidenceContractError(
            "namespace target roles or order differ"
        )

    observed_objects: list[NativeHandlePathEvidence] = []
    for target, requirement in zip(response.targets, expected):
        _assert_trusted_target_evidence(target)
        for value in (*target.ancestors, target.target):
            _assert_trusted_path_evidence(value)
        if (
            target.requested_path_sha256 != requirement.path_sha256
            or target.requested_canonical_path_sha256
            != requirement.canonical_path_sha256
            or target.target.final_canonical_path_sha256
            != requirement.canonical_path_sha256
            or target.target.kind != requirement.kind
            or target.created_new is not requirement.created_new
            or target.observed_initially_absent is not requirement.created_new
        ):
            raise NativeNamespaceEvidenceContractError(
                f"{requirement.role} target binding differs"
            )
        if requirement.expected_bytes is not None and (
            target.target.bytes != requirement.expected_bytes
            or target.target.content_sha256 != requirement.expected_content_sha256
        ):
            raise NativeNamespaceEvidenceContractError(
                "Blender image content identity differs"
            )

        ancestor_paths = _ancestor_paths(requirement.path)
        if len(target.ancestors) != len(ancestor_paths):
            raise NativeNamespaceEvidenceContractError(
                f"{requirement.role} ancestor count differs"
            )
        expected_ancestor_digests = tuple(
            launch_contract.canonical_windows_path_sha256(path)
            for path in ancestor_paths
        )
        observed_ancestor_digests = tuple(
            value.final_canonical_path_sha256 for value in target.ancestors
        )
        if observed_ancestor_digests != expected_ancestor_digests:
            raise NativeNamespaceEvidenceContractError(
                f"{requirement.role} normalized ancestor chain differs"
            )
        chain = (*target.ancestors, target.target)
        if len({value.volume_serial_number for value in chain}) != 1:
            raise NativeNamespaceEvidenceContractError(
                f"{requirement.role} crosses a retained volume boundary"
            )
        if len(
            {(value.volume_serial_number, value.file_id) for value in chain}
        ) != len(chain):
            raise NativeNamespaceEvidenceContractError(
                f"{requirement.role} ancestor file identities alias"
            )
        observed_objects.extend(chain)

    _validate_handle_population(tuple(observed_objects))
    _assert_trusted_response_evidence(response)
    return MappingProxyType(
        {
            "schema": NATIVE_NAMESPACE_RESPONSE_SCHEMA,
            "status": NATIVE_NAMESPACE_STATIC_STATUS,
            "provider_id": response.provider_id,
            "request_sha256": request_sha256,
            "target_count": len(response.targets),
            "complete_normalized_ancestor_chains_shape_valid": True,
            "short_name_alias_rejection_shape_valid": True,
            "reparse_rejection_shape_valid": True,
            "single_link_identity_shape_valid": True,
            "volume_and_file_id_binding_shape_valid": True,
            "retained_handle_population_shape_valid": True,
            "opaque_transaction_request_capsule_bound": True,
            "caller_owned_request_graph_reused_after_binding": False,
            "caller_owned_mapping_backing_reused_after_binding": False,
            "native_provider_reviewed": False,
            "provider_invocation_authorized": False,
            "operating_system_evidence_verified": False,
            "blender_execution_authorized": False,
            "body_created": False,
            "runtime_activation_authorized": False,
            "public_export_authorized": False,
        }
    )


validate_native_namespace_evidence_response = (
    _wrap_transaction_request_capsule_validator(
        _validate_resolved_native_namespace_evidence_response
    )
)
del _wrap_transaction_request_capsule_validator
del _validate_resolved_native_namespace_evidence_response


def static_contract_evidence_record() -> Mapping[str, Any]:
    """Public identity of this static boundary without an evidence claim."""

    return MappingProxyType(
        {
            "provider_interface": NATIVE_NAMESPACE_EVIDENCE_INTERFACE,
            "response_schema": NATIVE_NAMESPACE_RESPONSE_SCHEMA,
            "target_schema": NATIVE_NAMESPACE_TARGET_SCHEMA,
            "path_evidence_schema": NATIVE_HANDLE_PATH_EVIDENCE_SCHEMA,
            "source_transaction_interface": (
                transaction.NATIVE_TRANSACTION_PROVIDER_INTERFACE
            ),
            "required_query_sources": [
                FINAL_PATH_QUERY_SOURCE,
                FILE_ID_QUERY_SOURCE,
                STANDARD_INFO_QUERY_SOURCE,
                REPARSE_QUERY_SOURCE,
                VOLUME_QUERY_SOURCE,
                DRIVE_TYPE_QUERY_SOURCE,
            ],
            "review_scope": "STATIC_RETAINED_HANDLE_NAMESPACE_SHAPE_ONLY",
            "python_object_graph_threat_model": PYTHON_OBJECT_GRAPH_THREAT_MODEL,
            "trusted_snapshots_external_to_response_graph": True,
            "coherent_object_setattr_rewrite_rejection_required": True,
            "evidence_instances_slotted_without_instance_dict": True,
            "canonical_module_serializers_required": True,
            "untrusted_instance_serializer_dispatch_used": False,
            "transaction_request_declared_field_rebuild_required": True,
            "opaque_transaction_request_capsule_binding_required": True,
            "raw_transaction_request_validation_accepted": False,
            "capsule_issuer_or_resolver_exposed": False,
            "caller_owned_request_graph_reused_after_binding": False,
            "caller_owned_mapping_backing_reused_after_binding": False,
            "mapping_proxy_exact_dict_snapshot_required": True,
            "captured_canonical_gc_referents_builtin_required": True,
            "exact_builtin_type_gates_before_equality_hash_or_lookup": True,
            "complete_ancestor_chains_required": True,
            "single_link_required": True,
            "local_fixed_volume_required": True,
            "short_name_alias_identity_verified": False,
            "reparse_identity_verified": False,
            "hardlink_identity_verified": False,
            "volume_and_file_id_identity_verified": False,
            "real_native_handle_lifetime_verified": False,
            "arbitrary_in_process_python_isolation_verified": False,
            "module_or_closure_reflection_resistance_verified": False,
            "native_provider_reviewed": False,
            "provider_invocation_authorized": False,
            "operating_system_evidence_verified": False,
            "blender_execution_authorized": False,
            "body_created": False,
        }
    )


__all__ = [
    "DRIVE_TYPE_QUERY_SOURCE",
    "FILE_ID_QUERY_SOURCE",
    "FINAL_PATH_QUERY_SOURCE",
    "MAX_EVIDENCE_TARGETS",
    "NATIVE_HANDLE_PATH_EVIDENCE_SCHEMA",
    "NATIVE_NAMESPACE_EVIDENCE_INTERFACE",
    "NATIVE_NAMESPACE_RESPONSE_SCHEMA",
    "NATIVE_NAMESPACE_STATIC_STATUS",
    "NATIVE_NAMESPACE_TARGET_SCHEMA",
    "PYTHON_OBJECT_GRAPH_THREAT_MODEL",
    "NativeHandlePathEvidence",
    "NativeNamespaceEvidenceContractError",
    "NativeNamespaceEvidenceProvider",
    "NativeNamespaceEvidenceResponse",
    "NativeNamespaceHandleCloseApi",
    "NativeNamespaceTargetEvidence",
    "NativeNamespaceTransactionRequestCapsule",
    "REPARSE_QUERY_SOURCE",
    "RetainedNamespaceHandle",
    "STANDARD_INFO_QUERY_SOURCE",
    "VOLUME_QUERY_SOURCE",
    "ZERO_SHA256",
    "bind_native_namespace_transaction_request",
    "static_contract_evidence_record",
    "validate_native_namespace_evidence_response",
]
