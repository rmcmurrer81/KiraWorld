"""Resident-media V14 no-commit validation boundary.

V12 and V13 remain preserved and rejected. V13 hid the rejected V12 ledger
behind a Python wrapper, but ordinary attribute access still reached its commit
method. Moving that state into a Python method closure would only move the same
bypass: closure cells are introspectable. V14 therefore contains no resident
media commit implementation and returns no object that retains an authority,
adapter, compare-and-swap callable, ledger, receipt history, or durable anchor.

The disconnected factory reads caller-supplied bytes in the preserved owner-
selected snapshot schema. Those bytes are not authenticated authority truth.
The returned slot-only validator retains canonical snapshot data only.
It can validate exact scalar types and complete authoritative role coverage
and emit a non-authoritative static plan. The exact sealed record method
refuses. A same-process caller can replace an ordinary Python class member,
which is one reason neither the method nor any returned plan is an authority;
V14 retains no capability such replacement could use to commit.
A future append-only version may commit only through a separately reviewed
protected external/native broker that performs the same checks at its actual
commit boundary and exact post-commit readback.

The execution package binds exact V14/V13/V12/V9/V4 files, module/package
objects, globals, functions, classes, members, code, defaults, keyword
defaults, referenced globals, and closures. Those checks are defence in depth
inside one Python process, not an operating-system trust root. This module
opens, decodes, renders, plays, or presents no media; calls no model or device;
changes no person or memory state; and creates no seeing, hearing, enjoyment,
learning, preference, or memory claim.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
import threading
import types
import weakref
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from Core import resident_media_voluntary_gate_v4 as v4
from Core import resident_media_voluntary_gate_v9 as v9
from Core import resident_media_voluntary_gate_v12 as v12
from Core import resident_media_voluntary_gate_v13 as v13


class ResidentMediaV14Error(v13.ResidentMediaV13Error):
    """Raised when the disconnected V14 static validator fails closed."""


_ROOT = Path(__file__).resolve().parents[1]
_BINDING_PATH = (
    _ROOT
    / "RecoverySprint"
    / "continuation_20260811"
    / "resident_media_voluntary_v14"
    / "attempt_01"
    / "EXECUTION_BINDING_V14.json"
)
_MISSING = object()
_STATE_SEAL = object()
_EXACT_TEXT_FIELDS = frozenset(
    {
        "schema",
        "status",
        "interface_mode",
        "purpose",
        "verifier_boundary",
        "media_kind",
        "source_relative_path",
        "relative_path",
        "derivative_role",
        "role",
        "presented_at_utc",
    }
)
_IDENTIFIER_LIST_FIELDS = frozenset({"used_output_receipt_ids", "required_roles"})
_NULLABLE_SHA_FIELDS = frozenset(
    {"anchor_sha256", "expected_previous_anchor_sha256"}
)
_DECODER_SHA_FIELDS = frozenset(
    {
        "renderer_or_decoder_receipt_sha256",
        "renderer_or_decoder_receipt_sha256s",
        "used_renderer_or_decoder_receipt_sha256s",
    }
)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _typed_snapshot(value: Any) -> Any:
    if value is None or type(value) in (bool, int, float, str, bytes):
        return (type(value).__name__, value)
    if type(value) is tuple:
        return ("tuple", tuple(_typed_snapshot(item) for item in value))
    if type(value) is list:
        return ("list", tuple(_typed_snapshot(item) for item in value))
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise ResidentMediaV14Error("binding metadata keys must be exact strings")
        return (
            "dict",
            tuple((key, _typed_snapshot(value[key])) for key in sorted(value)),
        )
    if type(value) is frozenset:
        return (
            "frozenset",
            tuple(sorted((_typed_snapshot(item) for item in value), key=repr)),
        )
    return ("identity", type(value), id(value))


def _canonical_mapping_copy(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ResidentMediaV14Error(f"{label} must be an object")
    try:
        encoded = v4.canonical_json_bytes(dict(value))
        clean = v4.strict_json_loads(encoded)
    except Exception as exc:
        raise ResidentMediaV14Error(f"{label} is not strict canonical JSON") from exc
    if type(clean) is not dict:
        raise ResidentMediaV14Error(f"{label} must decode to an exact object")
    return clean


def _exact_identifier(value: Any, field: str) -> str:
    if type(value) is not str:
        raise ResidentMediaV14Error(f"{field} must be an exact string identifier")
    try:
        clean = v12._nonzero_identifier(value, field)
    except Exception as exc:
        raise ResidentMediaV14Error(str(exc)) from exc
    if clean != value:
        raise ResidentMediaV14Error(f"{field} must be an exact canonical identifier")
    return value


def _exact_sha256(
    value: Any,
    field: str,
    *,
    nullable: bool = False,
    reject_decimal_only: bool = False,
) -> str | None:
    if value is None and nullable:
        return None
    if type(value) is not str:
        raise ResidentMediaV14Error(f"{field} must be an exact SHA-256 string")
    try:
        clean = v12._nonzero_sha(value, field)
    except Exception as exc:
        raise ResidentMediaV14Error(str(exc)) from exc
    if clean != value or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ResidentMediaV14Error(f"{field} must be exact lowercase SHA-256")
    if reject_decimal_only and value.isdecimal():
        raise ResidentMediaV14Error(f"{field} cannot be a numeric-only decoder digest")
    return value


def _exact_sha_collection(value: Any, field: str, *, decoder: bool) -> None:
    if type(value) is not list:
        raise ResidentMediaV14Error(f"{field} must be an exact SHA-256 list")
    for index, item in enumerate(value):
        item_field = f"{field}[{index}]"
        if type(item) is list:
            _exact_sha_collection(item, item_field, decoder=decoder)
        else:
            _exact_sha256(item, item_field, reject_decimal_only=decoder)


def _require_exact_scalar_types(value: Any, label: str) -> None:
    """Reject identifier/digest coercion and bool/int/string aliases."""

    if isinstance(value, Mapping):
        for key, item in value.items():
            if type(key) is not str:
                raise ResidentMediaV14Error(f"{label} contains a non-string object key")
            field = f"{label}.{key}"
            if key in _IDENTIFIER_LIST_FIELDS or key.endswith("_ids"):
                if type(item) is not list:
                    raise ResidentMediaV14Error(
                        f"{field} must be an exact identifier list"
                    )
                for index, identifier in enumerate(item):
                    _exact_identifier(identifier, f"{field}[{index}]")
            elif key.endswith("_id"):
                _exact_identifier(item, field)
            elif key.endswith("_sha256s"):
                _exact_sha_collection(
                    item,
                    field,
                    decoder=key in _DECODER_SHA_FIELDS,
                )
            elif key == "sha256" or key.endswith("_sha256"):
                _exact_sha256(
                    item,
                    field,
                    nullable=key in _NULLABLE_SHA_FIELDS,
                    reject_decimal_only=key in _DECODER_SHA_FIELDS,
                )
            elif key in _EXACT_TEXT_FIELDS:
                if type(item) is not str:
                    raise ResidentMediaV14Error(f"{field} must be an exact string")
            else:
                _require_exact_scalar_types(item, field)
        return
    if type(value) is list:
        for index, item in enumerate(value):
            _require_exact_scalar_types(item, f"{label}[{index}]")
        return
    if type(value) is tuple:
        raise ResidentMediaV14Error(f"{label} must use canonical JSON arrays")


def _decode_checked_bytes(value: Any, label: str) -> bytes:
    try:
        clean = v12._decode_canonical_object(value, label)
    except Exception as exc:
        raise ResidentMediaV14Error(str(exc)) from exc
    _require_exact_scalar_types(clean, label)
    return value


def _preflight_complete_evidence_v14(
    value: Mapping[str, Any],
    *,
    session_id: str,
    person_id: str,
    expected_manifest: Mapping[str, Any],
    consumed_start_permit_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any], tuple[str, ...]]:
    frozen_value = _canonical_mapping_copy(value, "V14 presentation evidence")
    frozen_manifest = _canonical_mapping_copy(
        expected_manifest, "V14 expected authoritative manifest"
    )
    _require_exact_scalar_types(frozen_value, "V14 presentation evidence")
    _require_exact_scalar_types(
        frozen_manifest, "V14 expected authoritative manifest"
    )
    session = _exact_identifier(session_id, "V14 session id")
    person = _exact_identifier(person_id, "V14 person id")
    permit = _exact_sha256(
        consumed_start_permit_sha256, "V14 consumed start permit"
    )
    assert isinstance(permit, str)
    try:
        clean = v9.validate_presentation_evidence_v9(
            frozen_value,
            session_id=session,
            person_id=person,
            expected_manifest=frozen_manifest,
            consumed_start_permit_sha256=permit,
        )
        required_roles = tuple(v9._required_roles(frozen_manifest))
    except Exception as exc:
        raise ResidentMediaV14Error(str(exc)) from exc
    _require_exact_scalar_types(clean, "V14 validated presentation evidence")
    if clean.get("engineering_output_completed") is not True:
        raise ResidentMediaV14Error(
            "V14 refuses incomplete engineering output in a static plan"
        )
    if clean.get("presentation_complete_for_manifest") is not True:
        raise ResidentMediaV14Error(
            "V14 refuses incomplete manifest presentation in a static plan"
        )
    supplied_roles = clean.get("required_roles")
    if type(supplied_roles) is not list or supplied_roles != list(required_roles):
        raise ResidentMediaV14Error("V14 authoritative required media-role set changed")
    completeness = clean.get("complete_by_required_role")
    if type(completeness) is not dict or set(completeness) != set(required_roles):
        raise ResidentMediaV14Error(
            "V14 authoritative required media-role coverage is incomplete"
        )
    if any(completeness[role] is not True for role in required_roles):
        raise ResidentMediaV14Error(
            "V14 requires every authoritative media role complete in a plan"
        )
    return clean, frozen_manifest, required_roles


def _source_code_map(raw: bytes, filename: str) -> dict[str, tuple[types.CodeType, ...]]:
    top = compile(raw, filename, "exec", dont_inherit=True, optimize=0)
    found: dict[str, list[types.CodeType]] = {}

    def walk(code: types.CodeType) -> None:
        found.setdefault(code.co_qualname, []).append(code)
        for constant in code.co_consts:
            if type(constant) is types.CodeType:
                walk(constant)

    walk(top)
    return {key: tuple(values) for key, values in found.items()}


class _FunctionSealV14:
    __slots__ = (
        "function", "module_dict", "code", "code_bytes_sha256", "defaults",
        "defaults_snapshot", "kwdefaults", "kwdefaults_snapshot",
        "annotations", "annotations_snapshot", "function_dict",
        "function_dict_snapshot", "closure", "closure_cells",
        "closure_contents", "builtins", "referenced_globals",
        "referenced_builtins", "name", "qualname", "module_name",
    )

    def __init__(
        self,
        function: types.FunctionType,
        module_dict: dict[str, Any],
        *,
        source_codes: Mapping[str, tuple[types.CodeType, ...]],
        label: str,
    ) -> None:
        if type(function) is not types.FunctionType or function.__globals__ is not module_dict:
            raise ResidentMediaV14Error(f"{label} is not an exact module function")
        if not any(
            function.__code__ == expected
            for expected in source_codes.get(function.__qualname__, ())
        ):
            raise ResidentMediaV14Error(f"{label} code is not in the exact source")
        self.function = function
        self.module_dict = module_dict
        self.code = function.__code__
        self.code_bytes_sha256 = _sha256(function.__code__.co_code)
        self.defaults = function.__defaults__
        self.defaults_snapshot = _typed_snapshot(function.__defaults__)
        self.kwdefaults = function.__kwdefaults__
        self.kwdefaults_snapshot = _typed_snapshot(function.__kwdefaults__)
        self.annotations = function.__annotations__
        self.annotations_snapshot = _typed_snapshot(function.__annotations__)
        self.function_dict = function.__dict__
        self.function_dict_snapshot = _typed_snapshot(function.__dict__)
        self.closure = function.__closure__
        self.closure_cells = tuple(function.__closure__ or ())
        self.closure_contents = tuple(
            _typed_snapshot(cell.cell_contents) for cell in self.closure_cells
        )
        self.builtins = function.__builtins__
        self.referenced_globals = tuple(
            (name, module_dict[name])
            for name in function.__code__.co_names
            if name in module_dict
        )
        self.referenced_builtins = tuple(
            (name, function.__builtins__[name])
            for name in function.__code__.co_names
            if name not in module_dict and name in function.__builtins__
        )
        self.name = function.__name__
        self.qualname = function.__qualname__
        self.module_name = function.__module__

    def verify(self, label: str) -> None:
        function = self.function
        if type(function) is not types.FunctionType or function.__globals__ is not self.module_dict:
            raise ResidentMediaV14Error(f"{label} function/globals identity changed")
        if function.__code__ is not self.code:
            raise ResidentMediaV14Error(f"{label} code identity changed")
        if _sha256(function.__code__.co_code) != self.code_bytes_sha256:
            raise ResidentMediaV14Error(f"{label} code bytes changed")
        if (
            function.__defaults__ is not self.defaults
            or _typed_snapshot(function.__defaults__) != self.defaults_snapshot
        ):
            raise ResidentMediaV14Error(f"{label} defaults changed")
        if (
            function.__kwdefaults__ is not self.kwdefaults
            or _typed_snapshot(function.__kwdefaults__) != self.kwdefaults_snapshot
        ):
            raise ResidentMediaV14Error(f"{label} keyword defaults changed")
        if (
            function.__annotations__ is not self.annotations
            or _typed_snapshot(function.__annotations__) != self.annotations_snapshot
        ):
            raise ResidentMediaV14Error(f"{label} annotations changed")
        if (
            function.__dict__ is not self.function_dict
            or _typed_snapshot(function.__dict__) != self.function_dict_snapshot
        ):
            raise ResidentMediaV14Error(f"{label} function metadata changed")
        if function.__closure__ is not self.closure:
            raise ResidentMediaV14Error(f"{label} closure tuple changed")
        cells = tuple(function.__closure__ or ())
        if len(cells) != len(self.closure_cells) or any(
            actual is not expected
            for actual, expected in zip(cells, self.closure_cells)
        ):
            raise ResidentMediaV14Error(f"{label} closure cells changed")
        if tuple(_typed_snapshot(cell.cell_contents) for cell in cells) != self.closure_contents:
            raise ResidentMediaV14Error(f"{label} closure contents changed")
        if function.__builtins__ is not self.builtins:
            raise ResidentMediaV14Error(f"{label} builtins identity changed")
        if (
            function.__name__ != self.name
            or function.__qualname__ != self.qualname
            or function.__module__ != self.module_name
        ):
            raise ResidentMediaV14Error(f"{label} name/module changed")
        for name, expected in self.referenced_globals:
            if self.module_dict.get(name, _MISSING) is not expected:
                raise ResidentMediaV14Error(f"{label} referenced global changed: {name}")
        for name, expected in self.referenced_builtins:
            if function.__builtins__.get(name, _MISSING) is not expected:
                raise ResidentMediaV14Error(f"{label} referenced builtin changed: {name}")


def _class_functions(value: type) -> tuple[tuple[str, types.FunctionType], ...]:
    found: list[tuple[str, types.FunctionType]] = []
    for name, member in value.__dict__.items():
        function: Any = member
        if type(member) in (staticmethod, classmethod):
            function = member.__func__
        elif type(member) is property:
            for suffix, candidate in (
                ("fget", member.fget), ("fset", member.fset),
                ("fdel", member.fdel),
            ):
                if type(candidate) is types.FunctionType:
                    found.append((f"{name}.{suffix}", candidate))
            continue
        if type(function) is types.FunctionType:
            found.append((name, function))
    return tuple(found)


class _ClassSealV14:
    __slots__ = ("class_object", "keys", "values", "method_seals", "label")

    def __init__(
        self,
        value: type,
        module_dict: dict[str, Any],
        *,
        source_codes: Mapping[str, tuple[types.CodeType, ...]],
        label: str,
    ) -> None:
        self.class_object = value
        self.keys = frozenset(value.__dict__)
        self.values = tuple(value.__dict__.items())
        self.method_seals = tuple(
            (
                name,
                _FunctionSealV14(
                    function,
                    module_dict,
                    source_codes=source_codes,
                    label=f"{label}.{name}",
                ),
            )
            for name, function in _class_functions(value)
            if (
                function.__globals__ is module_dict
                and any(
                    function.__code__ == expected
                    for expected in source_codes.get(function.__qualname__, ())
                )
            )
        )
        self.label = label

    def verify(self) -> None:
        if frozenset(self.class_object.__dict__) != self.keys:
            raise ResidentMediaV14Error(f"{self.label} class schema changed")
        for name, expected in self.values:
            if self.class_object.__dict__.get(name, _MISSING) is not expected:
                raise ResidentMediaV14Error(
                    f"{self.label} class member changed: {name}"
                )
        for name, seal in self.method_seals:
            seal.verify(f"{self.label}.{name}")


class _ModuleSealV14:
    __slots__ = (
        "label", "module", "module_name", "parent", "package_attribute",
        "path", "expected_bytes", "expected_sha256", "file_identity",
        "file_path", "loader", "spec", "package", "cached", "source_codes",
        "keys", "values", "function_seals", "class_seals", "finalized",
    )

    def __init__(
        self,
        *,
        label: str,
        module: types.ModuleType,
        parent: types.ModuleType,
        binding: Mapping[str, Any],
        finalize: bool,
    ) -> None:
        self.label = label
        self.module = module
        self.module_name = binding["module_name"]
        self.parent = parent
        self.package_attribute = binding["package_attribute"]
        self.path = _ROOT / binding["relative_path"]
        self.expected_bytes = binding["bytes"]
        self.expected_sha256 = binding["sha256"]
        raw, identity, file_path = self._read_exact()
        self.file_identity = identity
        self.file_path = file_path
        self.loader = module.__loader__
        self.spec = module.__spec__
        self.package = module.__package__
        self.cached = module.__cached__
        self.source_codes = _source_code_map(raw, file_path)
        self.keys = frozenset()
        self.values = ()
        self.function_seals = ()
        self.class_seals = ()
        self.finalized = False
        if finalize:
            self.finalize()

    def _read_exact(self) -> tuple[bytes, tuple[int, int, int, int], str]:
        try:
            resolved = self.path.resolve(strict=True)
            before = resolved.stat()
            raw = resolved.read_bytes()
            after = resolved.stat()
        except Exception as exc:
            raise ResidentMediaV14Error(f"{self.label} source is unavailable") from exc
        identity_before = (
            int(before.st_dev), int(before.st_ino), int(before.st_size),
            int(before.st_mtime_ns),
        )
        identity_after = (
            int(after.st_dev), int(after.st_ino), int(after.st_size),
            int(after.st_mtime_ns),
        )
        if identity_before != identity_after:
            raise ResidentMediaV14Error(f"{self.label} source changed while read")
        if len(raw) != self.expected_bytes or _sha256(raw) != self.expected_sha256:
            raise ResidentMediaV14Error(f"{self.label} source exact binding changed")
        return raw, identity_after, str(resolved)

    def finalize(self) -> None:
        if self.finalized:
            raise ResidentMediaV14Error(f"{self.label} seal was already finalized")
        module_dict = self.module.__dict__
        functions = []
        classes = []
        for name, value in module_dict.items():
            if type(value) is types.FunctionType and value.__globals__ is module_dict:
                functions.append(
                    (name, _FunctionSealV14(
                        value, module_dict, source_codes=self.source_codes,
                        label=f"{self.label}.{name}",
                    ))
                )
            elif type(value) is type and value.__module__ == self.module_name:
                classes.append(
                    (name, _ClassSealV14(
                        value, module_dict, source_codes=self.source_codes,
                        label=f"{self.label}.{name}",
                    ))
                )
        self.function_seals = tuple(functions)
        self.class_seals = tuple(classes)
        self.keys = frozenset(module_dict)
        self.values = tuple(module_dict.items())
        self.finalized = True

    def verify(self) -> None:
        if self.finalized is not True:
            raise ResidentMediaV14Error(f"{self.label} seal is not finalized")
        _raw, identity, file_path = self._read_exact()
        if identity != self.file_identity or file_path != self.file_path:
            raise ResidentMediaV14Error(f"{self.label} source identity changed")
        if sys.modules.get(self.module_name) is not self.module:
            raise ResidentMediaV14Error(f"{self.label} sys.modules binding changed")
        if sys.modules.get("Core") is not self.parent:
            raise ResidentMediaV14Error(f"{self.label} Core package identity changed")
        if getattr(self.parent, self.package_attribute, _MISSING) is not self.module:
            raise ResidentMediaV14Error(f"{self.label} package attribute changed")
        if (
            self.module.__name__ != self.module_name
            or self.module.__file__ != self.file_path
            or self.module.__loader__ is not self.loader
            or self.module.__spec__ is not self.spec
            or self.module.__package__ != self.package
            or self.module.__cached__ != self.cached
        ):
            raise ResidentMediaV14Error(f"{self.label} module shell changed")
        module_dict = self.module.__dict__
        if frozenset(module_dict) != self.keys:
            raise ResidentMediaV14Error(f"{self.label} module global schema changed")
        for name, expected in self.values:
            if module_dict.get(name, _MISSING) is not expected:
                raise ResidentMediaV14Error(f"{self.label} module global changed: {name}")
        for name, seal in self.function_seals:
            seal.verify(f"{self.label}.{name}")
        for _name, seal in self.class_seals:
            seal.verify()


def _load_execution_binding() -> tuple[dict[str, Any], bytes, tuple[int, int, int, int]]:
    try:
        resolved = _BINDING_PATH.resolve(strict=True)
        before = resolved.stat()
        raw = resolved.read_bytes()
        after = resolved.stat()
        value = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ResidentMediaV14Error("V14 execution binding is unavailable") from exc
    before_identity = (
        int(before.st_dev), int(before.st_ino), int(before.st_size),
        int(before.st_mtime_ns),
    )
    after_identity = (
        int(after.st_dev), int(after.st_ino), int(after.st_size),
        int(after.st_mtime_ns),
    )
    keys = {
        "schema", "candidate_id", "status", "modules",
        "v12_and_v13_rejected", "disconnected_static_only",
        "authority_protocol_calls_authorized", "durable_commit_authorized",
        "production_routing_authorized", "live_media_authorized",
        "person_state_authorized", "different_fresh_static_audit_required",
    }
    if before_identity != after_identity:
        raise ResidentMediaV14Error("V14 execution binding changed while read")
    if type(value) is not dict or set(value) != keys:
        raise ResidentMediaV14Error("V14 execution binding schema is not exact")
    if (
        value["schema"] != "kira.resident_media.voluntary_v14.execution_binding.v1"
        or value["candidate_id"] != "resident_media_voluntary_v14"
        or value["status"]
        != "SEALED_NO_COMMIT_STATIC_CANDIDATE_PENDING_DIFFERENT_FRESH_AUDIT"
        or value["v12_and_v13_rejected"] is not True
        or value["disconnected_static_only"] is not True
        or value["authority_protocol_calls_authorized"] is not False
        or value["durable_commit_authorized"] is not False
        or value["production_routing_authorized"] is not False
        or value["live_media_authorized"] is not False
        or value["person_state_authorized"] is not False
        or value["different_fresh_static_audit_required"] is not True
    ):
        raise ResidentMediaV14Error("V14 execution binding truth changed")
    modules = value["modules"]
    if type(modules) is not list or len(modules) != 5:
        raise ResidentMediaV14Error("V14 execution module closure is not exact")
    entry_keys = {
        "label", "module_name", "package_attribute", "relative_path",
        "bytes", "sha256",
    }
    for entry, label in zip(modules, ("v14", "v13", "v12", "v9", "v4")):
        if (
            type(entry) is not dict
            or set(entry) != entry_keys
            or entry["label"] != label
            or type(entry["module_name"]) is not str
            or type(entry["package_attribute"]) is not str
            or type(entry["relative_path"]) is not str
            or type(entry["bytes"]) is not int
            or isinstance(entry["bytes"], bool)
            or entry["bytes"] <= 0
            or type(entry["sha256"]) is not str
            or re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]) is None
        ):
            raise ResidentMediaV14Error("V14 execution module entry changed")
    return value, raw, after_identity


class _BootstrapV14:
    __slots__ = (
        "binding", "binding_bytes", "binding_identity", "binding_path",
        "binding_sha256", "parent", "module_seals", "self_seal",
        "finalized", "lock",
    )

    def __init__(self) -> None:
        binding, raw, identity = _load_execution_binding()
        parent = sys.modules.get("Core")
        if type(parent) is not types.ModuleType:
            raise ResidentMediaV14Error("Core package identity is unavailable")
        modules = {
            "v14": sys.modules.get(__name__), "v13": v13, "v12": v12,
            "v9": v9, "v4": v4,
        }
        if any(type(module) is not types.ModuleType for module in modules.values()):
            raise ResidentMediaV14Error("V14 execution module identity is unavailable")
        seals = []
        self_seal = None
        for entry in binding["modules"]:
            label = entry["label"]
            module = modules[label]
            if module.__name__ != entry["module_name"]:
                raise ResidentMediaV14Error(f"{label} module name binding changed")
            seal = _ModuleSealV14(
                label=label,
                module=module,
                parent=parent,
                binding=entry,
                finalize=label != "v14",
            )
            seals.append(seal)
            if label == "v14":
                self_seal = seal
        assert self_seal is not None
        self.binding = binding
        self.binding_bytes = raw
        self.binding_identity = identity
        self.binding_path = str(_BINDING_PATH.resolve(strict=True))
        self.binding_sha256 = _sha256(raw)
        self.parent = parent
        self.module_seals = tuple(seals)
        self.self_seal = self_seal
        self.finalized = False
        self.lock = threading.RLock()

    def finalize_self(self) -> None:
        with self.lock:
            if self.finalized:
                raise ResidentMediaV14Error("V14 bootstrap was already finalized")
            self.self_seal.finalize()
            self.finalized = True

    def verify(self) -> None:
        with self.lock:
            if self.finalized is not True:
                raise ResidentMediaV14Error("V14 bootstrap is not finalized")
            try:
                resolved = _BINDING_PATH.resolve(strict=True)
                before = resolved.stat()
                raw = resolved.read_bytes()
                after = resolved.stat()
            except Exception as exc:
                raise ResidentMediaV14Error("V14 execution binding is unavailable") from exc
            before_identity = (
                int(before.st_dev), int(before.st_ino), int(before.st_size),
                int(before.st_mtime_ns),
            )
            after_identity = (
                int(after.st_dev), int(after.st_ino), int(after.st_size),
                int(after.st_mtime_ns),
            )
            if (
                str(resolved) != self.binding_path
                or before_identity != after_identity
                or after_identity != self.binding_identity
                or raw != self.binding_bytes
                or _sha256(raw) != self.binding_sha256
            ):
                raise ResidentMediaV14Error("V14 execution binding changed")
            for seal in self.module_seals:
                seal.verify()


class _SnapshotStateV14:
    """Canonical data only: no authority, adapter, callable, ledger, or anchor."""

    __slots__ = (
        "seal", "person_id", "snapshot", "snapshot_bytes", "snapshot_sha256",
        "catalog", "catalog_sha256", "lock",
    )

    def __init__(
        self,
        *,
        person_id: str,
        snapshot: dict[str, Any],
        snapshot_bytes: bytes,
        catalog: v4.StimulusCatalog,
    ) -> None:
        self.seal = _STATE_SEAL
        self.person_id = person_id
        self.snapshot = copy.deepcopy(snapshot)
        self.snapshot_bytes = bytes(snapshot_bytes)
        self.snapshot_sha256 = _sha256(snapshot_bytes)
        self.catalog = catalog
        self.catalog_sha256 = catalog.sha256
        self.lock = threading.RLock()

    def verify(self) -> None:
        if self.seal is not _STATE_SEAL:
            raise ResidentMediaV14Error("V14 validator instance seal changed")
        _exact_identifier(self.person_id, "V14 bound person id")
        if v4.canonical_json_bytes(self.snapshot) != self.snapshot_bytes:
            raise ResidentMediaV14Error("V14 bound snapshot state changed")
        if _sha256(self.snapshot_bytes) != self.snapshot_sha256:
            raise ResidentMediaV14Error("V14 bound snapshot digest changed")
        if type(self.catalog) is not v4.StimulusCatalog:
            raise ResidentMediaV14Error("V14 bound catalog type changed")
        if self.catalog.sha256 != self.catalog_sha256:
            raise ResidentMediaV14Error("V14 bound catalog digest changed")
        if self.snapshot.get("catalog_sha256") != self.catalog_sha256:
            raise ResidentMediaV14Error("V14 snapshot/catalog binding changed")


def _validate_snapshot_input_v14(
    owner_selected_snapshot_bytes: Any,
    expected_snapshot_sha256: Any,
) -> tuple[dict[str, Any], bytes, v4.StimulusCatalog]:
    """Validate caller-supplied static bytes without claiming authority."""

    if type(owner_selected_snapshot_bytes) is not bytes or not owner_selected_snapshot_bytes:
        raise ResidentMediaV14Error("V14 snapshot input must be exact nonempty bytes")
    expected = _exact_sha256(
        expected_snapshot_sha256, "V14 expected snapshot SHA-256"
    )
    assert isinstance(expected, str)
    if _sha256(owner_selected_snapshot_bytes) != expected:
        raise ResidentMediaV14Error("V14 snapshot input digest changed")
    _decode_checked_bytes(owner_selected_snapshot_bytes, "V14 snapshot input")
    try:
        snapshot = v12._decode_canonical_object(
            owner_selected_snapshot_bytes, "V14 snapshot input"
        )
        authority_id = _exact_identifier(
            snapshot.get("authority_instance_id"),
            "V14 snapshot authority instance id",
        )
        authority_epoch = _exact_sha256(
            snapshot.get("authority_epoch_sha256"),
            "V14 snapshot authority epoch",
        )
        assert isinstance(authority_epoch, str)
        clean, catalog = v12._validate_owner_snapshot(
            snapshot,
            authority_instance_id=authority_id,
            authority_epoch_sha256=authority_epoch,
        )
    except Exception as exc:
        raise ResidentMediaV14Error("V14 snapshot input is not self-consistent") from exc
    if v4.canonical_json_bytes(clean) != owner_selected_snapshot_bytes:
        raise ResidentMediaV14Error("V14 snapshot input is not exact canonical bytes")
    _require_exact_scalar_types(clean, "V14 snapshot input")
    return clean, bytes(owner_selected_snapshot_bytes), catalog


def _make_public_surface_v14(
    bootstrap: _BootstrapV14,
) -> tuple[type, types.FunctionType]:
    states: weakref.WeakKeyDictionary[Any, _SnapshotStateV14] = weakref.WeakKeyDictionary()
    states_lock = threading.RLock()
    bootstrap_verify = bootstrap.verify
    bootstrap_verify_function = bootstrap_verify.__func__
    bootstrap_verify_code = bootstrap_verify_function.__code__
    state_type = _SnapshotStateV14
    validate_snapshot = _validate_snapshot_input_v14
    preflight = _preflight_complete_evidence_v14
    exact_identifier = _exact_identifier
    exact_sha = _exact_sha256
    exact_types = _require_exact_scalar_types
    canonical_copy = _canonical_mapping_copy
    record_sha = v12._record_sha
    error_type = ResidentMediaV14Error

    def guard() -> None:
        if (
            bootstrap_verify.__self__ is not bootstrap
            or bootstrap_verify.__func__ is not bootstrap_verify_function
            or bootstrap_verify_function.__code__ is not bootstrap_verify_code
        ):
            raise error_type("V14 bootstrap verifier identity changed")
        bootstrap_verify()

    def state_for(instance: Any) -> _SnapshotStateV14:
        with states_lock:
            state = states.get(instance)
        if type(state) is not state_type:
            raise error_type("V14 validator instance is not factory-bound")
        return state

    class DisconnectedStaticValidatorV14:
        __slots__ = ("__weakref__",)

        def __copy__(self) -> Any:
            raise TypeError("V14 validator cannot be copied")

        def __deepcopy__(self, _memo: Any) -> Any:
            raise TypeError("V14 validator cannot be copied")

        def __reduce__(self) -> Any:
            raise TypeError("V14 validator cannot be serialized")

        def validate_static_evidence_plan(
            self,
            value: Mapping[str, Any],
            *,
            session_id: str,
            expected_manifest: Mapping[str, Any],
            consumed_start_permit_sha256: str,
        ) -> dict[str, Any]:
            """Return a non-authoritative plan; never consume or commit."""

            guard()
            state = state_for(self)
            with state.lock:
                guard()
                state.verify()
                session = exact_identifier(session_id, "V14 session id")
                permit = exact_sha(
                    consumed_start_permit_sha256, "V14 consumed start permit"
                )
                assert isinstance(permit, str)
                frozen_value = canonical_copy(value, "V14 presentation evidence")
                if frozen_value.get("session_id") != session:
                    raise error_type("V14 presentation session binding changed")
                ordinal = frozen_value.get("ordinal")
                if isinstance(ordinal, bool) or not isinstance(ordinal, int):
                    raise error_type("V14 presentation ordinal is invalid")
                try:
                    authoritative_manifest = state.catalog.manifest(ordinal)
                except Exception as exc:
                    raise error_type("V14 bound manifest is missing") from exc
                if canonical_copy(
                    expected_manifest, "V14 expected manifest"
                ) != authoritative_manifest:
                    raise error_type(
                        "V14 expected manifest is not the bound static snapshot"
                    )
                clean, manifest, required_roles = preflight(
                    frozen_value,
                    session_id=session,
                    person_id=state.person_id,
                    expected_manifest=authoritative_manifest,
                    consumed_start_permit_sha256=permit,
                )
                guard()
                state.verify()
                clean_again, manifest_again, roles_again = preflight(
                    frozen_value,
                    session_id=session,
                    person_id=state.person_id,
                    expected_manifest=authoritative_manifest,
                    consumed_start_permit_sha256=permit,
                )
                if (
                    clean_again != clean
                    or manifest_again != manifest
                    or roles_again != required_roles
                ):
                    raise error_type("V14 repeated static validation changed")
                plan = {
                    "schema": "kira.resident_media.no_commit_validation_plan.v14",
                    "status": "VALIDATED_STATIC_PLAN_NOT_AUTHORITY_NOT_COMMITTED",
                    "person_id": state.person_id,
                    "session_id": session,
                    "ordinal": clean["ordinal"],
                    "stimulus_id": clean["stimulus_id"],
                    "owner_selection_snapshot_sha256": state.snapshot_sha256,
                    "catalog_sha256": state.catalog_sha256,
                    "source_manifest_sha256": clean["source_manifest_sha256"],
                    "consumed_start_permit_sha256": permit,
                    "presentation_evidence": copy.deepcopy(clean),
                    "presentation_evidence_sha256": record_sha(clean),
                    "required_roles": list(required_roles),
                    "complete_by_required_role": copy.deepcopy(
                        clean["complete_by_required_role"]
                    ),
                    "snapshot_input_authenticated_by_protected_authority": False,
                    "authority_protocol_called": False,
                    "receipt_consumed": False,
                    "anchor_read": False,
                    "commit_attempted": False,
                    "durable_record_created": False,
                    "protected_external_native_commit_broker_required": True,
                    "live_execution_allowed": False,
                    "person_saw_or_heard_claimed": False,
                    "person_enjoyed_learned_preferred_or_remembered_claimed": False,
                }
                exact_types(plan, "V14 no-commit validation plan")
                guard()
                state.verify()
                return copy.deepcopy(plan)

        def validate_and_record_static_evidence(
            self,
            value: Mapping[str, Any],
            *,
            session_id: str,
            expected_manifest: Mapping[str, Any],
            consumed_start_permit_sha256: str,
        ) -> None:
            del value, session_id, expected_manifest, consumed_start_permit_sha256
            guard()
            state = state_for(self)
            with state.lock:
                state.verify()
            raise error_type(
                "V14 has no commit surface; use validate_static_evidence_plan only. "
                "A separately reviewed protected external/native broker is required."
            )

        def snapshot(self) -> dict[str, Any]:
            guard()
            state = state_for(self)
            with state.lock:
                state.verify()
                return {
                    "schema": "kira.resident_media_static_validator_snapshot.v14",
                    "status": "DISCONNECTED_NO_COMMIT_STATIC_VALIDATOR_ONLY",
                    "person_id": state.person_id,
                    "owner_selection_snapshot_sha256": state.snapshot_sha256,
                    "catalog_sha256": state.catalog_sha256,
                    "authority_retained": False,
                    "adapter_retained": False,
                    "ledger_retained": False,
                    "anchor_retained": False,
                    "commit_callable_retained": False,
                    "authority_protocol_called": False,
                    "durable_commit_authorized": False,
                    "python_process_is_trust_root": False,
                    "live_execution_allowed": False,
                }

    DisconnectedStaticValidatorV14.__name__ = "_DisconnectedStaticValidatorV14"
    DisconnectedStaticValidatorV14.__qualname__ = "_DisconnectedStaticValidatorV14"
    DisconnectedStaticValidatorV14.__module__ = __name__

    def open_harness(
        *,
        person_id: str,
        owner_selected_snapshot_bytes: bytes,
        expected_snapshot_sha256: str,
    ) -> Any:
        """Bind caller-supplied static bytes without calling an authority."""

        guard()
        person = exact_identifier(person_id, "V14 person id")
        snapshot, snapshot_bytes, catalog = validate_snapshot(
            owner_selected_snapshot_bytes, expected_snapshot_sha256
        )
        guard()
        instance = DisconnectedStaticValidatorV14()
        state = state_type(
            person_id=person,
            snapshot=snapshot,
            snapshot_bytes=snapshot_bytes,
            catalog=catalog,
        )
        state.verify()
        with states_lock:
            states[instance] = state
        guard()
        return instance

    open_harness.__name__ = "_open_disconnected_static_validation_harness_v14"
    open_harness.__module__ = __name__
    return DisconnectedStaticValidatorV14, open_harness


_BOOTSTRAP_V14 = _BootstrapV14()
(
    _DisconnectedStaticValidatorV14,
    _open_disconnected_static_validation_harness_v14,
) = _make_public_surface_v14(_BOOTSTRAP_V14)


def open_production_resident_media_v14(*args: Any, **kwargs: Any) -> None:
    del args, kwargs
    raise ResidentMediaV14Error(
        "V14 production resident-media opener is disconnected and V14 contains "
        "no authority, anchor, record, or commit surface"
    )


def production_connection_status_v14() -> dict[str, Any]:
    return {
        "schema": "kira.resident_media_production_connection_status.v14",
        "status": "DISCONNECTED_NO_COMMIT_SURFACE",
        "protected_external_authority_implementation_present": False,
        "protected_external_native_commit_broker_present": False,
        "authority_protocol_calls_authorized": False,
        "durable_commit_authorized": False,
        "production_opener_accepts_caller_authority": False,
        "production_opener_accepts_caller_catalog": False,
        "python_process_is_trust_root": False,
        "live_execution_allowed": False,
    }


def static_contract_summary() -> dict[str, Any]:
    return {
        "schema": "kira.resident_media_voluntary_gate_static_summary.v14",
        "status": "SEALED_NO_COMMIT_STATIC_CANDIDATE_PENDING_DIFFERENT_FRESH_AUDIT",
        "v12_rejection_preserved": True,
        "v13_rejection_preserved": True,
        "v12_or_v13_ledger_instance_created_or_returned": False,
        "returned_object_retains_authority_adapter_anchor_or_commit": False,
        "caller_snapshot_is_protected_authority_truth": False,
        "static_plan_is_durable_record": False,
        "authority_protocol_calls_authorized": False,
        "durable_commit_authorized": False,
        "protected_external_native_commit_broker_required": True,
        "v14_v13_v12_v9_v4_module_package_execution_bound": True,
        "sealed_entrypoints_check_function_class_member_code_default_kwdefault_global_closure_binding": True,
        "python_class_methods_claimed_non_substitutable": False,
        "exact_scalar_and_complete_role_static_validation": True,
        "disconnected_static_only": True,
        "different_fresh_static_audit_required": True,
        "production_routing_authorized": False,
        "live_execution_allowed": False,
        "person_saw_or_heard_claimed": False,
        "person_enjoyed_learned_preferred_or_remembered_claimed": False,
    }


_BOOTSTRAP_V14.finalize_self()
