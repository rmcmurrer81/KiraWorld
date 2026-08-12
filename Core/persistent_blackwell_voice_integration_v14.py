"""Disconnected Blackwell V14 exact-byte control snapshot.

This source is not an ordinary import target.  A future independently accepted
native anchor may compile the exact locked bytes into two private globals
mappings, compare their complete code graphs, and invoke exactly one stored
factory reference.  The source has no model, GPU, voice, synthesis, playback,
network, subprocess, body, Blender, person-state, or production-routing path.

V14 preserves the rejected V13 bytes as evidence.  It never imports V13 by its
normal name, never attaches either source to ``Core``, and never calls a V13
control-plane function.  It compiles the exact retained V13 source into two
private globals dictionaries solely to compare every module function, class
member, code/default/keyword-default/annotation/closure, referenced global,
and referenced builtin.  Mutable loader state is eliminated: no module object,
loader, specification, cache entry, or package attribute is created.
"""

from __future__ import annotations


CANDIDATE_ID = "kira_chatterbox_blackwell_native_exact_control_anchor_candidate_v14"
PRODUCTION_ROUTING_AUTHORIZED = False
LIVE_EXECUTION_AUTHORIZED_BY_THIS_SOURCE = False
FUTURE_HARNESS_AUTHORING_AUTHORIZED = False
SYNTHESIS_AUTHORIZED = False
PLAYBACK_AUTHORIZED = False
LATENCY_RUN_AUTHORIZED = False

V13_MODULE_NAME = "Core.persistent_blackwell_voice_integration_v13"
V13_PACKAGE_NAME = "Core"
V13_PACKAGE_ATTRIBUTE = "persistent_blackwell_voice_integration_v13"
V13_PRIVATE_V12_NAME = "_kira_blackwell_v13_exact_v12_control_plane"
V13_NORMAL_V12_NAME = (
    "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v12."
    "canonical_typed_memory_binding"
)
V13_NORMAL_V12_PARENT = "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v12"
V13_SOURCE_PATH = "C:/Users/robmc/Kira/Core/persistent_blackwell_voice_integration_v13.py"

_CONSTRUCTION_KEY = object()
_MISSING = object()


class V14StaticControlError(RuntimeError):
    """Fail-closed disconnected V14 validation error."""


def _exact_bool(value: object, expected: bool, label: str) -> None:
    if type(value) is not bool or value is not expected:
        raise V14StaticControlError(label + " must be the exact Boolean " + repr(expected))


def _exact_int(value: object, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise V14StaticControlError(label + " must be an exact non-Boolean integer")
    return value


def _sha256_text(value: object, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V14StaticControlError(label + " must be 64 lowercase hexadecimal characters")
    return value


class _StrictJson:
    """Small duplicate-rejecting JSON parser with no module imports."""

    __slots__ = ("_text", "_index", "_length")

    def __init__(self, raw: bytes) -> None:
        if type(raw) is not bytes:
            raise V14StaticControlError("JSON input must be exact bytes")
        try:
            text = raw.decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise V14StaticControlError("JSON is not strict UTF-8") from exc
        if text.startswith("\ufeff"):
            raise V14StaticControlError("JSON BOM is forbidden")
        self._text = text
        self._index = 0
        self._length = len(text)

    def parse(self) -> object:
        self._space()
        value = self._value()
        self._space()
        if self._index != self._length:
            raise V14StaticControlError("trailing JSON data")
        return value

    def _space(self) -> None:
        text = self._text
        index = self._index
        while index < self._length and text[index] in " \t\r\n":
            index += 1
        self._index = index

    def _value(self) -> object:
        if self._index >= self._length:
            raise V14StaticControlError("unexpected end of JSON")
        character = self._text[self._index]
        if character == '"':
            return self._string()
        if character == "{":
            return self._object()
        if character == "[":
            return self._array()
        if character == "t" and self._literal("true"):
            return True
        if character == "f" and self._literal("false"):
            return False
        if character == "n" and self._literal("null"):
            return None
        if character == "-" or "0" <= character <= "9":
            return self._number()
        raise V14StaticControlError("invalid JSON token")

    def _literal(self, literal: str) -> bool:
        end = self._index + len(literal)
        if self._text[self._index:end] != literal:
            return False
        self._index = end
        return True

    def _string(self) -> str:
        self._index += 1
        output: list[str] = []
        while self._index < self._length:
            character = self._text[self._index]
            self._index += 1
            if character == '"':
                return "".join(output)
            if character == "\\":
                if self._index >= self._length:
                    raise V14StaticControlError("truncated JSON escape")
                escaped = self._text[self._index]
                self._index += 1
                simple = {
                    '"': '"',
                    "\\": "\\",
                    "/": "/",
                    "b": "\b",
                    "f": "\f",
                    "n": "\n",
                    "r": "\r",
                    "t": "\t",
                }
                if escaped in simple:
                    output.append(simple[escaped])
                    continue
                if escaped != "u" or self._index + 4 > self._length:
                    raise V14StaticControlError("invalid JSON escape")
                digits = self._text[self._index : self._index + 4]
                if any(value not in "0123456789abcdefABCDEF" for value in digits):
                    raise V14StaticControlError("invalid JSON Unicode escape")
                self._index += 4
                code = int(digits, 16)
                if 0xD800 <= code <= 0xDBFF:
                    if self._text[self._index : self._index + 2] != "\\u":
                        raise V14StaticControlError("unpaired JSON high surrogate")
                    self._index += 2
                    low_digits = self._text[self._index : self._index + 4]
                    if len(low_digits) != 4 or any(
                        value not in "0123456789abcdefABCDEF" for value in low_digits
                    ):
                        raise V14StaticControlError("invalid JSON low surrogate")
                    self._index += 4
                    low = int(low_digits, 16)
                    if not 0xDC00 <= low <= 0xDFFF:
                        raise V14StaticControlError("unpaired JSON high surrogate")
                    code = 0x10000 + ((code - 0xD800) << 10) + (low - 0xDC00)
                elif 0xDC00 <= code <= 0xDFFF:
                    raise V14StaticControlError("unpaired JSON low surrogate")
                output.append(chr(code))
                continue
            if ord(character) < 0x20:
                raise V14StaticControlError("unescaped JSON control character")
            output.append(character)
        raise V14StaticControlError("unterminated JSON string")

    def _number(self) -> int:
        start = self._index
        text = self._text
        if text[self._index] == "-":
            self._index += 1
            if self._index >= self._length:
                raise V14StaticControlError("truncated JSON number")
        if text[self._index] == "0":
            self._index += 1
            if self._index < self._length and text[self._index].isdigit():
                raise V14StaticControlError("leading zero in JSON number")
        elif "1" <= text[self._index] <= "9":
            while self._index < self._length and text[self._index].isdigit():
                self._index += 1
        else:
            raise V14StaticControlError("invalid JSON number")
        if self._index < self._length and text[self._index] in ".eE":
            raise V14StaticControlError("floating JSON numbers are forbidden")
        return int(text[start:self._index], 10)

    def _array(self) -> list[object]:
        self._index += 1
        result: list[object] = []
        self._space()
        if self._index < self._length and self._text[self._index] == "]":
            self._index += 1
            return result
        while True:
            self._space()
            result.append(self._value())
            self._space()
            if self._index >= self._length:
                raise V14StaticControlError("unterminated JSON array")
            character = self._text[self._index]
            self._index += 1
            if character == "]":
                return result
            if character != ",":
                raise V14StaticControlError("invalid JSON array separator")

    def _object(self) -> dict[str, object]:
        self._index += 1
        result: dict[str, object] = {}
        self._space()
        if self._index < self._length and self._text[self._index] == "}":
            self._index += 1
            return result
        while True:
            self._space()
            if self._index >= self._length or self._text[self._index] != '"':
                raise V14StaticControlError("JSON object key is not a string")
            key = self._string()
            if key in result:
                raise V14StaticControlError("duplicate JSON object key: " + key)
            self._space()
            if self._index >= self._length or self._text[self._index] != ":":
                raise V14StaticControlError("missing JSON object colon")
            self._index += 1
            self._space()
            result[key] = self._value()
            self._space()
            if self._index >= self._length:
                raise V14StaticControlError("unterminated JSON object")
            character = self._text[self._index]
            self._index += 1
            if character == "}":
                return result
            if character != ",":
                raise V14StaticControlError("invalid JSON object separator")


def _parse_json(raw: bytes) -> object:
    return _StrictJson(raw).parse()


def _exact_keys(value: object, expected: tuple[str, ...], label: str) -> dict[str, object]:
    if type(value) is not dict or set(value) != set(expected):
        raise V14StaticControlError(label + " keys are not exact")
    return value


def _subject_rows(value: object, *, label: str) -> tuple[tuple[str, int, str], ...]:
    if type(value) is not list:
        raise V14StaticControlError(label + " must be a list")
    rows: list[tuple[str, int, str]] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        row = _exact_keys(item, ("path", "bytes", "sha256"), f"{label}[{index}]")
        path = row["path"]
        if type(path) is not str or not path or "\\" in path or path.startswith("/"):
            raise V14StaticControlError(f"{label}[{index}] path is not canonical relative text")
        if path in seen:
            raise V14StaticControlError(label + " contains a duplicate path")
        seen.add(path)
        rows.append(
            (
                path,
                _exact_int(row["bytes"], f"{label}[{index}].bytes", minimum=1),
                _sha256_text(row["sha256"], f"{label}[{index}].sha256"),
            )
        )
    return tuple(rows)


def _attestations(value: object) -> tuple[tuple[str, int, str, int, bytes], ...]:
    if type(value) is not tuple:
        raise V14StaticControlError("native attestations must be an exact tuple")
    rows: list[tuple[str, int, str, int, bytes]] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if type(item) is not tuple or len(item) != 5:
            raise V14StaticControlError(f"native attestation {index} shape is not exact")
        path, byte_count, digest, volume, file_id = item
        if type(path) is not str or not path or path in seen:
            raise V14StaticControlError("native attestation path is invalid or duplicate")
        seen.add(path)
        _exact_int(byte_count, "native attestation bytes", minimum=1)
        _sha256_text(digest, "native attestation digest")
        _exact_int(volume, "native attestation volume")
        if type(file_id) is not bytes or len(file_id) != 16:
            raise V14StaticControlError("native attestation file identity is not 16 exact bytes")
        rows.append((path, byte_count, digest, volume, file_id))
    return tuple(rows)


def _typed_snapshot(value: object, module_globals: dict[str, object]) -> object:
    if value is None or type(value) in (bool, int, float, str, bytes):
        if type(value) is float and not (-float("inf") < value < float("inf")):
            raise V14StaticControlError("non-finite graph metadata")
        return (type(value).__name__, value)
    if type(value) is tuple:
        return ("tuple", tuple(_typed_snapshot(item, module_globals) for item in value))
    if type(value) is list:
        return ("list", tuple(_typed_snapshot(item, module_globals) for item in value))
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise V14StaticControlError("graph dictionary key is not an exact string")
        return (
            "dict",
            tuple((key, _typed_snapshot(value[key], module_globals)) for key in sorted(value)),
        )
    if type(value) is set:
        return ("set", tuple(sorted(_typed_snapshot(item, module_globals) for item in value)))
    if type(value) is frozenset:
        return ("frozenset", tuple(sorted(_typed_snapshot(item, module_globals) for item in value)))
    if type(value).__name__ == "module":
        return (
            "shared_module",
            getattr(value, "__name__", None),
            getattr(value, "__file__", None),
            type(getattr(value, "__loader__", None)).__name__,
        )
    for name, item in module_globals.items():
        if value is item and type(item).__name__ == "function":
            return ("module_function", name)
        if value is item and type(item) is type:
            return ("module_class", name)
    if type(value) is type:
        return ("shared_class", value.__module__, value.__qualname__)
    # Separately executed exact-source graphs necessarily create distinct
    # sentinels, descriptors, and class namespace objects.  Their cross-graph
    # seal therefore compares exact runtime types; identities are retained and
    # checked within each private graph by the native validator around calls.
    return ("typed_object", type(value).__module__, type(value).__qualname__)


def _code_signature(code: object) -> tuple[object, ...]:
    if type(code).__name__ != "code":
        raise V14StaticControlError("function code is not an exact code object")
    constants: list[object] = []
    for value in code.co_consts:
        if type(value).__name__ == "code":
            constants.append(("code", _code_signature(value)))
        elif value is None or type(value) in (bool, int, float, str, bytes, tuple):
            constants.append(("constant", repr(value)))
        else:
            constants.append(("typed_constant", type(value).__module__, type(value).__qualname__))
    return (
        code.co_argcount,
        code.co_posonlyargcount,
        code.co_kwonlyargcount,
        code.co_nlocals,
        code.co_stacksize,
        code.co_flags,
        code.co_code,
        tuple(constants),
        code.co_names,
        code.co_varnames,
        code.co_filename,
        code.co_name,
        code.co_qualname,
        code.co_firstlineno,
        code.co_linetable,
        code.co_exceptiontable,
        code.co_freevars,
        code.co_cellvars,
    )


def _function_signature(function: object, module_globals: dict[str, object]) -> tuple[object, ...]:
    if type(function).__name__ != "function" or function.__globals__ is not module_globals:
        raise V14StaticControlError("module function/globals identity is not exact")
    cells = tuple(function.__closure__ or ())
    closure = tuple(_typed_snapshot(cell.cell_contents, module_globals) for cell in cells)
    referenced_globals: list[tuple[str, object]] = []
    referenced_builtins: list[tuple[str, int, str, str]] = []
    for name in function.__code__.co_names:
        if name in module_globals:
            referenced_globals.append((name, _typed_snapshot(module_globals[name], module_globals)))
        elif name in function.__builtins__:
            value = function.__builtins__[name]
            referenced_builtins.append(
                (name, id(value), type(value).__module__, type(value).__qualname__)
            )
    return (
        function.__name__,
        function.__qualname__,
        function.__module__,
        _code_signature(function.__code__),
        _typed_snapshot(function.__defaults__, module_globals),
        _typed_snapshot(function.__kwdefaults__, module_globals),
        _typed_snapshot(function.__annotations__, module_globals),
        _typed_snapshot(function.__dict__, module_globals),
        closure,
        tuple(referenced_globals),
        tuple(referenced_builtins),
        id(function.__builtins__),
    )


def _class_signature(value: type, module_globals: dict[str, object]) -> tuple[object, ...]:
    members: list[tuple[str, object]] = []
    for name, member in value.__dict__.items():
        if type(member).__name__ == "function" and member.__globals__ is module_globals:
            snapshot = ("function", _function_signature(member, module_globals))
        elif type(member) is staticmethod:
            snapshot = ("staticmethod", _function_signature(member.__func__, module_globals))
        elif type(member) is classmethod:
            snapshot = ("classmethod", _function_signature(member.__func__, module_globals))
        elif type(member) is property:
            pieces = []
            for function in (member.fget, member.fset, member.fdel):
                pieces.append(
                    None if function is None else _function_signature(function, module_globals)
                )
            snapshot = ("property", tuple(pieces), member.__doc__)
        else:
            snapshot = ("value", _typed_snapshot(member, module_globals))
        members.append((name, snapshot))
    return (
        value.__name__,
        value.__qualname__,
        value.__module__,
        tuple(base.__qualname__ for base in value.__bases__),
        tuple(members),
    )


def _module_graph_signature(module_globals: dict[str, object]) -> tuple[object, ...]:
    if type(module_globals) is not dict:
        raise V14StaticControlError("private module globals are not an exact dictionary")
    result: list[tuple[str, object]] = []
    for name in sorted(module_globals):
        if name == "__builtins__":
            builtins_value = module_globals[name]
            if type(builtins_value) is not dict:
                raise V14StaticControlError("private module builtins are not an exact dictionary")
            result.append((name, ("builtins", id(builtins_value))))
            continue
        value = module_globals[name]
        if type(value).__name__ == "function" and value.__globals__ is module_globals:
            snapshot = ("function", _function_signature(value, module_globals))
        elif type(value) is type and value.__module__ == module_globals.get("__name__"):
            snapshot = ("class", _class_signature(value, module_globals))
        else:
            snapshot = ("value", _typed_snapshot(value, module_globals))
        result.append((name, snapshot))
    return tuple(result)


def _normal_v13_slots_clean(system: object) -> None:
    modules = system.modules
    if (
        V13_MODULE_NAME in modules
        or V13_PRIVATE_V12_NAME in modules
        or V13_NORMAL_V12_NAME in modules
    ):
        raise V14StaticControlError("ordinary V13/V12 module slot is occupied")
    package = modules.get(V13_PACKAGE_NAME)
    if package is not None and hasattr(package, V13_PACKAGE_ATTRIBUTE):
        raise V14StaticControlError("ordinary V13 package attribute is occupied")
    parent = modules.get(V13_NORMAL_V12_PARENT)
    if parent is not None and hasattr(parent, "canonical_typed_memory_binding"):
        raise V14StaticControlError("ordinary V12 package attribute is occupied")


class _StaticPath:
    """Inert path value sufficient for evaluating V13 module constants only."""

    __slots__ = ("_text",)

    def __init__(self, value: object) -> None:
        self._text = str(value).replace("\\", "/")

    def resolve(self) -> _StaticPath:
        return self

    @property
    def parents(self) -> tuple[_StaticPath, ...]:
        return (
            _StaticPath("C:/Users/robmc/Kira/Core"),
            _StaticPath("C:/Users/robmc/Kira"),
            _StaticPath("C:/Users/robmc"),
        )

    def __truediv__(self, value: object) -> _StaticPath:
        return _StaticPath(self._text.rstrip("/") + "/" + str(value).lstrip("/"))

    def __str__(self) -> str:
        return self._text


class _StaticImportNamespace:
    __slots__ = ("__name__", "machinery", "Path", "Any")

    def __init__(
        self,
        name: str,
        *,
        machinery: object = None,
        path_class: object = None,
        any_value: object = None,
    ) -> None:
        self.__name__ = name
        self.machinery = machinery
        self.Path = path_class
        self.Any = any_value


_MACHINERY_STUB = _StaticImportNamespace("importlib.machinery")
_IMPORTLIB_STUB = _StaticImportNamespace("importlib", machinery=_MACHINERY_STUB)
_PATHLIB_STUB = _StaticImportNamespace("pathlib", path_class=_StaticPath)
_TYPING_STUB = _StaticImportNamespace("typing", any_value=object)
_V13_IMPORT_STUBS = {
    "hashlib": _StaticImportNamespace("hashlib"),
    "importlib": _IMPORTLIB_STUB,
    "importlib.machinery": _MACHINERY_STUB,
    "json": _StaticImportNamespace("json"),
    "marshal": _StaticImportNamespace("marshal"),
    "math": _StaticImportNamespace("math"),
    "os": _StaticImportNamespace("os"),
    "sys": _StaticImportNamespace("sys"),
    "threading": _StaticImportNamespace("threading"),
    "types": _StaticImportNamespace("types"),
    "pathlib": _PATHLIB_STUB,
    "typing": _TYPING_STUB,
}


def _restricted_v13_import(
    name: str,
    _globals: object = None,
    _locals: object = None,
    fromlist: object = (),
    level: int = 0,
) -> object:
    if type(name) is not str or type(level) is not int or level != 0:
        raise V14StaticControlError("retained V13 requested a non-exact import")
    if type(fromlist) not in (tuple, list):
        raise V14StaticControlError("retained V13 import fromlist is not exact")
    value = _V13_IMPORT_STUBS.get(name, _MISSING)
    if value is _MISSING:
        raise V14StaticControlError("retained V13 requested an unapproved import: " + name)
    if name == "importlib.machinery" and not fromlist:
        return _IMPORTLIB_STUB
    return value


def _validate_v13_graph(v13_source: bytes) -> tuple[str, int, bool]:
    if type(v13_source) is not bytes or len(v13_source) != 27096:
        raise V14StaticControlError("retained V13 source bytes are not exact")
    system = __import__("sys")
    _normal_v13_slots_clean(system)
    try:
        source_text = v13_source.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise V14StaticControlError("retained V13 source is not strict UTF-8") from exc
    shared_builtins = __builtins__
    if type(shared_builtins) is not dict:
        shared_builtins = shared_builtins.__dict__
    shared_builtins = dict(shared_builtins)
    shared_builtins["__import__"] = _restricted_v13_import
    private_name = "_kira_blackwell_v14_private_v13_graph"
    first = {
        "__name__": private_name,
        "__file__": V13_SOURCE_PATH,
        "__package__": "",
        "__loader__": None,
        "__spec__": None,
        "__cached__": None,
        "__builtins__": shared_builtins,
    }
    second = dict(first)
    first_code = compile(source_text, V13_SOURCE_PATH, "exec", dont_inherit=True, optimize=0)
    second_code = compile(source_text, V13_SOURCE_PATH, "exec", dont_inherit=True, optimize=0)
    if _code_signature(first_code) != _code_signature(second_code):
        raise V14StaticControlError("retained V13 root code comparison failed")
    exec(first_code, first, first)
    _normal_v13_slots_clean(system)
    exec(second_code, second, second)
    _normal_v13_slots_clean(system)
    first_signature = _module_graph_signature(first)
    second_signature = _module_graph_signature(second)
    if first_signature != second_signature:
        raise V14StaticControlError("retained V13 function/class/control graph comparison failed")
    required = (
        "BlackwellV13ControlPlaneBinding",
        "V13ControlPlaneError",
        "create_static_control_plane_binding_v13",
        "open_production_blackwell_v13",
        "bounded_engineering_candidate_v13",
    )
    if any(name not in first or name not in second for name in required):
        raise V14StaticControlError("retained V13 required graph member is absent")
    if first["_CONTROL_FINALIZED"] is not True or second["_CONTROL_FINALIZED"] is not True:
        raise V14StaticControlError("retained V13 finalization truth is not exact")
    if first["PRODUCTION_ROUTING_AUTHORIZED"] is not False:
        raise V14StaticControlError("retained V13 production truth drifted")
    if first["LIVE_EXECUTION_AUTHORIZED_BY_THIS_MODULE"] is not False:
        raise V14StaticControlError("retained V13 live truth drifted")
    if first["FUTURE_HARNESS_AUTHORING_AUTHORIZED"] is not False:
        raise V14StaticControlError("retained V13 harness truth drifted")
    if first["PLAYBACK_AUTHORIZED"] is not False:
        raise V14StaticControlError("retained V13 playback truth drifted")
    first.clear()
    second.clear()
    if first or second:
        raise V14StaticControlError("retained V13 private globals were not destroyed")
    _normal_v13_slots_clean(system)
    return ("v13_complete_graph_exact", len(first_signature), True)


def _validate_v14_config(
    raw: bytes, attestations: tuple[tuple[str, int, str, int, bytes], ...]
) -> tuple[tuple[str, int, str], ...]:
    keys = (
        "schema",
        "candidate_id",
        "status",
        "control_python_path",
        "control_python_bytes",
        "control_python_sha256",
        "native_source_path",
        "native_header_path",
        "native_contract_path",
        "native_contract_bytes",
        "native_contract_sha256",
        "preserved_v13_source_path",
        "preserved_v13_source_bytes",
        "preserved_v13_source_sha256",
        "preserved_v13_config_path",
        "preserved_v13_config_bytes",
        "preserved_v13_config_sha256",
        "preserved_v13_seal_path",
        "preserved_v13_seal_bytes",
        "preserved_v13_seal_sha256",
        "v13_rejection_decision_path",
        "v13_rejection_decision_bytes",
        "v13_rejection_decision_sha256",
        "v13_rejection_checkpoint_path",
        "v13_rejection_checkpoint_bytes",
        "v13_rejection_checkpoint_sha256",
        "preserved_v13_subject_count",
        "preserved_v13_subjects",
        "production_routing_authorized",
        "live_execution_authorized",
        "future_harness_authoring_authorized",
        "synthesis_authorized",
        "playback_authorized",
        "latency_run_authorized",
        "different_fresh_static_audit_required",
    )
    value = _exact_keys(_parse_json(raw), keys, "V14 config")
    if (
        value["schema"] != "kira.blackwell.v14.native_exact_control_anchor_config.v1"
        or value["candidate_id"] != CANDIDATE_ID
        or value["status"]
        != "AUTHOR_STATIC_ONLY_PENDING_BUILD_SEAL_AND_DIFFERENT_FRESH_AUDIT"
        or value["control_python_path"]
        != "Core/persistent_blackwell_voice_integration_v14.py"
        or value["native_source_path"]
        != "tools/native/kira_blackwell_voice_control_anchor_v14.c"
        or value["native_header_path"]
        != "tools/native/kira_blackwell_voice_control_anchor_v14_identity_anchor.h"
        or value["native_contract_path"]
        != "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v14/native_control_contract.json"
        or value["native_contract_bytes"] != 4069
        or value["native_contract_sha256"]
        != "2726655eb808ed0ab24d08a408308d39adbcd3eb86cc7203168ea88850382710"
        or value["preserved_v13_source_path"]
        != "Core/persistent_blackwell_voice_integration_v13.py"
        or value["preserved_v13_source_bytes"] != 27096
        or value["preserved_v13_source_sha256"]
        != "a1a24c3cfb4383feda35d088ce2495991db1f643c116bbcd8dbb13fa3d218f38"
        or value["preserved_v13_config_path"]
        != "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v13/candidate_config.json"
        or value["preserved_v13_config_bytes"] != 1153
        or value["preserved_v13_config_sha256"]
        != "33fa8f3c726f2a2a920f58414881c76ec4a9f3a459b02360f5e8e1668f672060"
        or value["preserved_v13_seal_path"]
        != "RecoverySprint/continuation_20260811/blackwell_v13_control_plane_binding_static_preparation/attempt_01/STATIC_SEAL_MANIFEST.json"
        or value["preserved_v13_seal_bytes"] != 3015
        or value["preserved_v13_seal_sha256"]
        != "c09cadde50a73593fcf7dc2978e11a9012dec0952ef923d415dd035af4312c55"
        or value["v13_rejection_decision_path"]
        != "RecoverySprint/continuation_20260811/blackwell_v13_control_plane_binding_fresh_static_audit/attempt_01/AUDIT_DECISION.json"
        or value["v13_rejection_decision_bytes"] != 2311
        or value["v13_rejection_decision_sha256"]
        != "bfba016c56d8525a1641168ddecaa757b63de840d7582159519db9d2d89591b8"
        or value["v13_rejection_checkpoint_path"]
        != "RecoverySprint/continuation_20260811/blackwell_v13_control_plane_binding_fresh_static_audit/attempt_01/CHECKPOINT.md"
        or value["v13_rejection_checkpoint_bytes"] != 1936
        or value["v13_rejection_checkpoint_sha256"]
        != "d0d953d92b987acad488471c34b57979abfdb0364138150db25d442d0210431a"
    ):
        raise V14StaticControlError("V14 exact predecessor/config values drifted")
    _exact_int(value["control_python_bytes"], "V14 control source bytes", minimum=1)
    _sha256_text(value["control_python_sha256"], "V14 control source digest")
    _exact_int(value["native_contract_bytes"], "V14 native contract bytes", minimum=1)
    _sha256_text(value["native_contract_sha256"], "V14 native contract digest")
    _exact_int(value["preserved_v13_subject_count"], "V14 predecessor count", minimum=1)
    for key in (
        "production_routing_authorized",
        "live_execution_authorized",
        "future_harness_authoring_authorized",
        "synthesis_authorized",
        "playback_authorized",
        "latency_run_authorized",
    ):
        _exact_bool(value[key], False, "V14 config " + key)
    _exact_bool(value["different_fresh_static_audit_required"], True, "V14 audit truth")
    subjects = _subject_rows(value["preserved_v13_subjects"], label="V14 predecessors")
    if len(subjects) != value["preserved_v13_subject_count"] or len(subjects) != 15:
        raise V14StaticControlError("V14 predecessor subject count is not exactly 15")
    attested_simple = tuple((path, size, digest) for path, size, digest, _volume, _id in attestations)
    if subjects != attested_simple:
        raise V14StaticControlError("V14 predecessor subjects differ from native attestations")
    return subjects


def _validate_v13_config(raw: bytes) -> None:
    keys = (
        "schema", "candidate_id", "status", "control_module_path",
        "control_module_bytes", "control_module_sha256", "preserved_v12_path",
        "preserved_v12_bytes", "preserved_v12_sha256",
        "v12_rejection_checkpoint_path", "v12_rejection_checkpoint_sha256",
        "production_routing_authorized", "live_execution_authorized",
        "future_harness_authoring_authorized", "playback_authorized",
        "different_fresh_static_audit_required",
    )
    value = _exact_keys(_parse_json(raw), keys, "V13 config")
    if (
        value["schema"] != "kira.blackwell.v13.control_plane_binding_config.v1"
        or value["candidate_id"]
        != "kira_chatterbox_blackwell_control_plane_binding_candidate_v13"
        or value["status"] != "SEALED_STATIC_ONLY_PENDING_DIFFERENT_FRESH_AUDIT"
        or value["control_module_path"] != "Core/persistent_blackwell_voice_integration_v13.py"
        or value["control_module_bytes"] != 27096
        or value["control_module_sha256"]
        != "a1a24c3cfb4383feda35d088ce2495991db1f643c116bbcd8dbb13fa3d218f38"
    ):
        raise V14StaticControlError("V13 config identity drifted")
    for key in (
        "production_routing_authorized", "live_execution_authorized",
        "future_harness_authoring_authorized", "playback_authorized",
    ):
        _exact_bool(value[key], False, "V13 config " + key)
    _exact_bool(value["different_fresh_static_audit_required"], True, "V13 audit truth")
    _exact_int(value["preserved_v12_bytes"], "V13 preserved V12 bytes", minimum=1)
    _sha256_text(value["preserved_v12_sha256"], "V13 preserved V12 digest")
    _sha256_text(value["v12_rejection_checkpoint_sha256"], "V13 V12 rejection digest")


def _validate_v13_seal(raw: bytes, subjects: tuple[tuple[str, int, str], ...]) -> None:
    keys = (
        "schema", "candidate_id", "status", "subjects", "subject_count",
        "production_routing_authorized", "live_execution_authorized",
        "future_harness_authoring_authorized", "playback_authorized",
        "different_fresh_static_audit_required",
    )
    value = _exact_keys(_parse_json(raw), keys, "V13 seal")
    if (
        value["schema"] != "kira.blackwell.v13.static_seal_manifest.v1"
        or value["candidate_id"]
        != "kira_chatterbox_blackwell_control_plane_binding_candidate_v13"
        or value["status"] != "SEALED_STATIC_ONLY_PENDING_DIFFERENT_FRESH_AUDIT"
    ):
        raise V14StaticControlError("V13 seal identity drifted")
    seal_rows = _subject_rows(value["subjects"], label="V13 seal subjects")
    if _exact_int(value["subject_count"], "V13 seal subject count", minimum=1) != 11:
        raise V14StaticControlError("V13 seal count is not exactly 11")
    if len(seal_rows) != 11:
        raise V14StaticControlError("V13 seal row count is not exactly 11")
    subject_set = set(subjects)
    if any(row not in subject_set for row in seal_rows):
        raise V14StaticControlError("V13 seal row is absent from native closure")
    for key in (
        "production_routing_authorized", "live_execution_authorized",
        "future_harness_authoring_authorized", "playback_authorized",
    ):
        _exact_bool(value[key], False, "V13 seal " + key)
    _exact_bool(value["different_fresh_static_audit_required"], True, "V13 seal audit truth")


def _validate_v13_decision(raw: bytes) -> None:
    value = _exact_keys(
        _parse_json(raw),
        (
            "schema", "recorded_utc", "reviewer_task", "evidence_transcribed_by",
            "decision", "accepted_static_only", "production_routing_authorized",
            "live_execution_authorized", "future_harness_authoring_authorized",
            "playback_authorized", "latency_run_authorized", "seal", "author_checks",
            "blocking_findings", "scope_truth", "required_next_step",
        ),
        "V13 rejection decision",
    )
    if (
        value["schema"] != "kira.blackwell.v13.independent_read_only_audit_decision.v1"
        or value["decision"] != "REJECT"
    ):
        raise V14StaticControlError("V13 rejection decision identity drifted")
    for key in (
        "accepted_static_only", "production_routing_authorized", "live_execution_authorized",
        "future_harness_authoring_authorized", "playback_authorized", "latency_run_authorized",
    ):
        _exact_bool(value[key], False, "V13 decision " + key)
    findings = value["blocking_findings"]
    if type(findings) is not list or len(findings) != 4:
        raise V14StaticControlError("V13 rejection does not contain exactly four blockers")
    identifiers = []
    for index, finding in enumerate(findings):
        item = _exact_keys(finding, ("id", "reproduction"), f"V13 blocker {index}")
        if type(item["id"]) is not str or type(item["reproduction"]) is not str:
            raise V14StaticControlError("V13 blocker fields are not exact strings")
        identifiers.append(item["id"])
    if tuple(identifiers) != (
        "BLOCK_V13_PRECALL_SELF_MODULE_PACKAGE_IDENTITY_NOT_BOUND",
        "BLOCK_V13_SELF_CLASS_METHODS_NOT_BOUND_PRIVATE_V12_BYPASS",
        "BLOCK_V13_CONTROL_STATE_NOT_REVALIDATED",
        "BLOCK_V13_CONFIG_QUARANTINE_LOADER_STATE_NOT_EXACT",
    ):
        raise V14StaticControlError("V13 blocker identities drifted")


class BlackwellV14StaticControlSnapshot:
    """Immutable disconnected state created only inside the native validation."""

    __slots__ = (
        "_seal", "_subjects", "_graph", "_prepared_static", "_quarantined",
        "_production", "_live", "_future_harness", "_synthesis", "_playback",
        "_latency", "_loader_state",
    )

    def __new__(cls, key: object, *args: object):
        if key is not _CONSTRUCTION_KEY:
            raise TypeError("V14 snapshot is native-controller-created only")
        return super().__new__(cls)

    def __init__(
        self,
        key: object,
        subjects: tuple[tuple[str, int, str, int, bytes], ...],
        graph: tuple[str, int, bool],
    ) -> None:
        if key is not _CONSTRUCTION_KEY:
            raise TypeError("V14 snapshot construction key is invalid")
        self._seal = _CONSTRUCTION_KEY
        self._subjects = subjects
        self._graph = graph
        self._prepared_static = True
        self._quarantined = False
        self._production = False
        self._live = False
        self._future_harness = False
        self._synthesis = False
        self._playback = False
        self._latency = False
        self._loader_state = ("private_globals_only", None, None, None, False)

    def __copy__(self):
        raise TypeError("V14 snapshot cannot be copied")

    def __deepcopy__(self, _memo: object):
        raise TypeError("V14 snapshot cannot be copied")

    def __reduce__(self):
        raise TypeError("V14 snapshot cannot be serialized")

    def revalidate(self) -> tuple[object, ...]:
        if self._seal is not _CONSTRUCTION_KEY:
            raise V14StaticControlError("V14 construction seal changed")
        if type(self._subjects) is not tuple or len(self._subjects) != 15:
            raise V14StaticControlError("V14 subject state changed")
        _attestations(self._subjects)
        if (
            type(self._graph) is not tuple
            or len(self._graph) != 3
            or self._graph[0] != "v13_complete_graph_exact"
            or type(self._graph[1]) is not int
            or self._graph[1] <= 0
            or self._graph[2] is not True
        ):
            raise V14StaticControlError("V14 V13 graph state changed")
        _exact_bool(self._prepared_static, True, "V14 prepared state")
        _exact_bool(self._quarantined, False, "V14 quarantine state")
        for label, value in (
            ("production", self._production), ("live", self._live),
            ("future harness", self._future_harness), ("synthesis", self._synthesis),
            ("playback", self._playback), ("latency", self._latency),
        ):
            _exact_bool(value, False, "V14 " + label + " authority")
        if self._loader_state != ("private_globals_only", None, None, None, False):
            raise V14StaticControlError("V14 loader/module state changed")
        return (
            "kira.blackwell.v14.native_exact_control_snapshot.v1",
            CANDIDATE_ID,
            self._prepared_static,
            self._quarantined,
            self._graph,
            self._loader_state,
            self._production,
            self._live,
            self._future_harness,
            self._synthesis,
            self._playback,
            self._latency,
            len(self._subjects),
        )


def create_static_control_snapshot_v14(
    config_raw: bytes,
    v13_source_raw: bytes,
    v13_config_raw: bytes,
    v13_seal_raw: bytes,
    v13_decision_raw: bytes,
    native_attestations: tuple[tuple[str, int, str, int, bytes], ...],
) -> BlackwellV14StaticControlSnapshot:
    attestations = _attestations(native_attestations)
    subjects = _validate_v14_config(config_raw, attestations)
    _validate_v13_config(v13_config_raw)
    _validate_v13_seal(v13_seal_raw, subjects)
    _validate_v13_decision(v13_decision_raw)
    graph = _validate_v13_graph(v13_source_raw)
    snapshot = BlackwellV14StaticControlSnapshot(_CONSTRUCTION_KEY, attestations, graph)
    return snapshot


def open_production_blackwell_v14(*_args: object, **_kwargs: object) -> None:
    raise V14StaticControlError(
        "V14 is disconnected static evidence and authorizes no production or live route"
    )


def bounded_engineering_candidate_v14(*_args: object, **_kwargs: object) -> None:
    raise V14StaticControlError(
        "V14 authorizes no model, voice, synthesis, playback, or latency run"
    )


__all__ = (
    "BlackwellV14StaticControlSnapshot",
    "CANDIDATE_ID",
    "FUTURE_HARNESS_AUTHORING_AUTHORIZED",
    "LATENCY_RUN_AUTHORIZED",
    "LIVE_EXECUTION_AUTHORIZED_BY_THIS_SOURCE",
    "PLAYBACK_AUTHORIZED",
    "PRODUCTION_ROUTING_AUTHORIZED",
    "SYNTHESIS_AUTHORIZED",
    "V14StaticControlError",
    "bounded_engineering_candidate_v14",
    "create_static_control_snapshot_v14",
    "open_production_blackwell_v14",
)
