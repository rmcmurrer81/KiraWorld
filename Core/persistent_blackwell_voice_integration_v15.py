"""Disconnected Blackwell V15 immutable origin-bound control result.

This source is not an ordinary import target.  A future independently accepted
native anchor may compile the exact locked bytes into two private globals
mappings, compare their complete code graphs, and invoke exactly one stored
    factory reference.  The result is an exact recursively immutable built-in
    tuple; there is no writable snapshot object.  The source has no model, GPU,
    voice, synthesis, playback,
network, subprocess, body, Blender, person-state, or production-routing path.

V15 preserves the rejected V14 bytes as evidence.  It never imports V14 by its
normal name, never attaches either source to ``Core``, and never calls a V14
control-plane function.  It compiles the exact retained V14 source into two
private globals dictionaries solely to compare every module function, class
member, code/default/keyword-default/annotation/closure, referenced global,
    referenced builtin, and the fields of every retained static namespace/path
    instance. Mutable loader state is eliminated: no module object, loader,
    specification, cache entry, or package attribute is created.
"""

from __future__ import annotations


CANDIDATE_ID = "kira_chatterbox_blackwell_native_exact_control_anchor_candidate_v15"
PRODUCTION_ROUTING_AUTHORIZED = False
LIVE_EXECUTION_AUTHORIZED_BY_THIS_SOURCE = False
FUTURE_HARNESS_AUTHORING_AUTHORIZED = False
SYNTHESIS_AUTHORIZED = False
PLAYBACK_AUTHORIZED = False
LATENCY_RUN_AUTHORIZED = False

V14_MODULE_NAME = "Core.persistent_blackwell_voice_integration_v14"
V14_PACKAGE_NAME = "Core"
V14_PACKAGE_ATTRIBUTE = "persistent_blackwell_voice_integration_v14"
V14_PRIVATE_GRAPH_NAME = "_kira_blackwell_v14_private_v13_graph"
V13_MODULE_NAME = "Core.persistent_blackwell_voice_integration_v13"
V13_PACKAGE_ATTRIBUTE = "persistent_blackwell_voice_integration_v13"
V13_PRIVATE_V12_NAME = "_kira_blackwell_v13_exact_v12_control_plane"
V14_NORMAL_V12_NAME = (
    "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v12."
    "canonical_typed_memory_binding"
)
V14_NORMAL_V12_PARENT = "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v12"
V14_SOURCE_PATH = "C:/Users/robmc/Kira/Core/persistent_blackwell_voice_integration_v14.py"

_MISSING = object()


class V15StaticControlError(RuntimeError):
    """Fail-closed disconnected V15 validation error."""


def _exact_bool(value: object, expected: bool, label: str) -> None:
    if type(value) is not bool or value is not expected:
        raise V15StaticControlError(label + " must be the exact Boolean " + repr(expected))


def _exact_int(value: object, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise V15StaticControlError(label + " must be an exact non-Boolean integer")
    return value


def _sha256_text(value: object, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V15StaticControlError(label + " must be 64 lowercase hexadecimal characters")
    return value


class _StrictJson:
    """Small duplicate-rejecting JSON parser with no module imports."""

    __slots__ = ("_text", "_index", "_length")

    def __init__(self, raw: bytes) -> None:
        if type(raw) is not bytes:
            raise V15StaticControlError("JSON input must be exact bytes")
        try:
            text = raw.decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise V15StaticControlError("JSON is not strict UTF-8") from exc
        if text.startswith("\ufeff"):
            raise V15StaticControlError("JSON BOM is forbidden")
        self._text = text
        self._index = 0
        self._length = len(text)

    def parse(self) -> object:
        self._space()
        value = self._value()
        self._space()
        if self._index != self._length:
            raise V15StaticControlError("trailing JSON data")
        return value

    def _space(self) -> None:
        text = self._text
        index = self._index
        while index < self._length and text[index] in " \t\r\n":
            index += 1
        self._index = index

    def _value(self) -> object:
        if self._index >= self._length:
            raise V15StaticControlError("unexpected end of JSON")
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
        raise V15StaticControlError("invalid JSON token")

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
                    raise V15StaticControlError("truncated JSON escape")
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
                    raise V15StaticControlError("invalid JSON escape")
                digits = self._text[self._index : self._index + 4]
                if any(value not in "0123456789abcdefABCDEF" for value in digits):
                    raise V15StaticControlError("invalid JSON Unicode escape")
                self._index += 4
                code = int(digits, 16)
                if 0xD800 <= code <= 0xDBFF:
                    if self._text[self._index : self._index + 2] != "\\u":
                        raise V15StaticControlError("unpaired JSON high surrogate")
                    self._index += 2
                    low_digits = self._text[self._index : self._index + 4]
                    if len(low_digits) != 4 or any(
                        value not in "0123456789abcdefABCDEF" for value in low_digits
                    ):
                        raise V15StaticControlError("invalid JSON low surrogate")
                    self._index += 4
                    low = int(low_digits, 16)
                    if not 0xDC00 <= low <= 0xDFFF:
                        raise V15StaticControlError("unpaired JSON high surrogate")
                    code = 0x10000 + ((code - 0xD800) << 10) + (low - 0xDC00)
                elif 0xDC00 <= code <= 0xDFFF:
                    raise V15StaticControlError("unpaired JSON low surrogate")
                output.append(chr(code))
                continue
            if ord(character) < 0x20:
                raise V15StaticControlError("unescaped JSON control character")
            output.append(character)
        raise V15StaticControlError("unterminated JSON string")

    def _number(self) -> int:
        start = self._index
        text = self._text
        if text[self._index] == "-":
            self._index += 1
            if self._index >= self._length:
                raise V15StaticControlError("truncated JSON number")
        if text[self._index] == "0":
            self._index += 1
            if self._index < self._length and text[self._index].isdigit():
                raise V15StaticControlError("leading zero in JSON number")
        elif "1" <= text[self._index] <= "9":
            while self._index < self._length and text[self._index].isdigit():
                self._index += 1
        else:
            raise V15StaticControlError("invalid JSON number")
        if self._index < self._length and text[self._index] in ".eE":
            raise V15StaticControlError("floating JSON numbers are forbidden")
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
                raise V15StaticControlError("unterminated JSON array")
            character = self._text[self._index]
            self._index += 1
            if character == "]":
                return result
            if character != ",":
                raise V15StaticControlError("invalid JSON array separator")

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
                raise V15StaticControlError("JSON object key is not a string")
            key = self._string()
            if key in result:
                raise V15StaticControlError("duplicate JSON object key: " + key)
            self._space()
            if self._index >= self._length or self._text[self._index] != ":":
                raise V15StaticControlError("missing JSON object colon")
            self._index += 1
            self._space()
            result[key] = self._value()
            self._space()
            if self._index >= self._length:
                raise V15StaticControlError("unterminated JSON object")
            character = self._text[self._index]
            self._index += 1
            if character == "}":
                return result
            if character != ",":
                raise V15StaticControlError("invalid JSON object separator")


def _parse_json(raw: bytes) -> object:
    return _StrictJson(raw).parse()


def _canonical_json_string(value: str) -> str:
    if type(value) is not str:
        raise V15StaticControlError("canonical JSON key/value is not an exact string")
    pieces = ['"']
    escapes = {'"': '\\"', "\\": "\\\\", "\b": "\\b", "\f": "\\f",
               "\n": "\\n", "\r": "\\r", "\t": "\\t"}
    for character in value:
        escaped = escapes.get(character)
        if escaped is not None:
            pieces.append(escaped)
        elif ord(character) < 0x20:
            pieces.append("\\u" + format(ord(character), "04x"))
        else:
            pieces.append(character)
    pieces.append('"')
    return "".join(pieces)


def _canonical_json(value: object) -> str:
    if value is None:
        return "null"
    if type(value) is bool:
        return "true" if value else "false"
    if type(value) is int:
        return str(value)
    if type(value) is str:
        return _canonical_json_string(value)
    if type(value) is list:
        return "[" + ",".join(_canonical_json(item) for item in value) + "]"
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise V15StaticControlError("canonical JSON object key is not an exact string")
        return "{" + ",".join(
            _canonical_json_string(key) + ":" + _canonical_json(value[key])
            for key in sorted(value)
        ) + "}"
    raise V15StaticControlError("canonical JSON contains an unsupported exact type")


def _parse_canonical_json(raw: bytes, label: str) -> object:
    value = _parse_json(raw)
    canonical = (_canonical_json(value) + "\n").encode("utf-8", "strict")
    if raw != canonical:
        raise V15StaticControlError(label + " is not exact canonical UTF-8 JSON plus LF")
    return value


def _exact_keys(value: object, expected: tuple[str, ...], label: str) -> dict[str, object]:
    if type(value) is not dict or set(value) != set(expected):
        raise V15StaticControlError(label + " keys are not exact")
    return value


def _subject_rows(value: object, *, label: str) -> tuple[tuple[str, int, str], ...]:
    if type(value) is not list:
        raise V15StaticControlError(label + " must be a list")
    rows: list[tuple[str, int, str]] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        row = _exact_keys(item, ("path", "bytes", "sha256"), f"{label}[{index}]")
        path = row["path"]
        if type(path) is not str or not path or "\\" in path or path.startswith("/"):
            raise V15StaticControlError(f"{label}[{index}] path is not canonical relative text")
        if path in seen:
            raise V15StaticControlError(label + " contains a duplicate path")
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
        raise V15StaticControlError("native attestations must be an exact tuple")
    seen: set[str] = set()
    for index, item in enumerate(value):
        if type(item) is not tuple or len(item) != 5:
            raise V15StaticControlError(f"native attestation {index} shape is not exact")
        path, byte_count, digest, volume, file_id = item
        if type(path) is not str or not path or path in seen:
            raise V15StaticControlError("native attestation path is invalid or duplicate")
        seen.add(path)
        _exact_int(byte_count, "native attestation bytes", minimum=1)
        _sha256_text(digest, "native attestation digest")
        _exact_int(volume, "native attestation volume")
        if type(file_id) is not bytes or len(file_id) != 16:
            raise V15StaticControlError("native attestation file identity is not 16 exact bytes")
    return value


def _exact_immutable_tree(value: object, label: str) -> None:
    if value is None or type(value) in (bool, int, float, str, bytes):
        if type(value) is float and not (-float("inf") < value < float("inf")):
            raise V15StaticControlError(label + " contains a non-finite float")
        return
    if type(value) is tuple:
        for index, item in enumerate(value):
            _exact_immutable_tree(item, label + "[" + str(index) + "]")
        return
    raise V15StaticControlError(label + " contains a mutable or non-built-in value")


def _typed_snapshot(value: object, module_globals: dict[str, object]) -> object:
    if value is None or type(value) in (bool, int, float, str, bytes):
        if type(value) is float and not (-float("inf") < value < float("inf")):
            raise V15StaticControlError("non-finite graph metadata")
        return (type(value).__name__, value)
    if type(value) is tuple:
        return ("tuple", tuple(_typed_snapshot(item, module_globals) for item in value))
    if type(value) is list:
        return ("list", tuple(_typed_snapshot(item, module_globals) for item in value))
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise V15StaticControlError("graph dictionary key is not an exact string")
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
    static_path = module_globals.get("_StaticPath")
    if type(static_path) is type and type(value) is static_path:
        text = value._text
        if type(text) is not str:
            raise V15StaticControlError("static path text is not an exact string")
        return ("static_path", text)
    static_namespace = module_globals.get("_StaticImportNamespace")
    if type(static_namespace) is type and type(value) is static_namespace:
        return (
            "static_import_namespace",
            _typed_snapshot(value.__name__, module_globals),
            _typed_snapshot(value.machinery, module_globals),
            _typed_snapshot(value.Path, module_globals),
            _typed_snapshot(value.Any, module_globals),
        )
    for name, item in module_globals.items():
        if value is item and type(item).__name__ == "function":
            return ("module_function", name)
        if value is item and type(item) is type:
            return ("module_class", name)
    if type(value) is type:
        return ("shared_class", value.__module__, value.__qualname__)
    if type(value) is object:
        return ("exact_builtin_object_sentinel",)
    if type(value).__name__ in (
        "member_descriptor", "getset_descriptor", "wrapper_descriptor",
        "method_descriptor", "classmethod_descriptor",
    ):
        return ("immutable_descriptor", type(value).__module__, type(value).__qualname__)
    raise V15StaticControlError(
        "complete graph contains an unsupported opaque instance: "
        + type(value).__module__ + "." + type(value).__qualname__
    )


def _code_signature(code: object) -> tuple[object, ...]:
    if type(code).__name__ != "code":
        raise V15StaticControlError("function code is not an exact code object")
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
        raise V15StaticControlError("module function/globals identity is not exact")
    cells = tuple(function.__closure__ or ())
    closure = tuple(_typed_snapshot(cell.cell_contents, module_globals) for cell in cells)
    referenced_globals: list[tuple[str, object]] = []
    referenced_builtins: list[tuple[str, str, str]] = []
    for name in function.__code__.co_names:
        if name in module_globals:
            referenced_globals.append((name, _typed_snapshot(module_globals[name], module_globals)))
        elif name in function.__builtins__:
            value = function.__builtins__[name]
            referenced_builtins.append((name, type(value).__module__, type(value).__qualname__))
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
        ("exact_builtins_dictionary",),
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
        tuple((base.__module__, base.__qualname__) for base in value.__bases__),
        tuple(members),
    )


def _module_graph_signature(module_globals: dict[str, object]) -> tuple[object, ...]:
    if type(module_globals) is not dict:
        raise V15StaticControlError("private module globals are not an exact dictionary")
    result: list[tuple[str, object]] = []
    for name in sorted(module_globals):
        if name == "__builtins__":
            builtins_value = module_globals[name]
            if type(builtins_value) is not dict:
                raise V15StaticControlError("private module builtins are not an exact dictionary")
            result.append((name, ("exact_builtins_dictionary",)))
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


def _normal_v14_slots_clean(system: object) -> None:
    modules = system.modules
    names = (
        V14_MODULE_NAME, V14_PRIVATE_GRAPH_NAME, V13_MODULE_NAME,
        V13_PRIVATE_V12_NAME, V14_NORMAL_V12_NAME,
    )
    if any(name in modules for name in names):
        raise V15StaticControlError("ordinary/private V14/V13/V12 module slot is occupied")
    package = modules.get(V14_PACKAGE_NAME)
    if package is not None and (
        hasattr(package, V14_PACKAGE_ATTRIBUTE)
        or hasattr(package, V13_PACKAGE_ATTRIBUTE)
    ):
        raise V15StaticControlError("ordinary V14/V13 Core package attribute is occupied")
    parent = modules.get(V14_NORMAL_V12_PARENT)
    if parent is not None and hasattr(parent, "canonical_typed_memory_binding"):
        raise V15StaticControlError("ordinary V12 package attribute is occupied")


class _StaticPath:
    """Inert path value sufficient for evaluating V14 module constants only."""

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
_V14_IMPORT_STUBS = {
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


def _restricted_v14_import(
    name: str,
    _globals: object = None,
    _locals: object = None,
    fromlist: object = (),
    level: int = 0,
) -> object:
    if type(name) is not str or type(level) is not int or level != 0:
        raise V15StaticControlError("retained V14 requested a non-exact import")
    if type(fromlist) not in (tuple, list):
        raise V15StaticControlError("retained V14 import fromlist is not exact")
    value = _V14_IMPORT_STUBS.get(name, _MISSING)
    if value is _MISSING:
        raise V15StaticControlError("retained V14 requested an unapproved import: " + name)
    if name == "importlib.machinery" and not fromlist:
        return _IMPORTLIB_STUB
    return value


def _validate_v14_graph(v14_source: bytes) -> tuple[object, ...]:
    if type(v14_source) is not bytes or len(v14_source) != 42108:
        raise V15StaticControlError("retained V14 source bytes are not exact")
    system = __import__("sys")
    _normal_v14_slots_clean(system)
    try:
        source_text = v14_source.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise V15StaticControlError("retained V14 source is not strict UTF-8") from exc
    shared_builtins = __builtins__
    if type(shared_builtins) is not dict:
        shared_builtins = shared_builtins.__dict__
    shared_builtins = dict(shared_builtins)
    shared_builtins["__import__"] = _restricted_v14_import
    private_name = "_kira_blackwell_v15_private_v14_graph"
    first = {
        "__name__": private_name,
        "__file__": V14_SOURCE_PATH,
        "__package__": "",
        "__loader__": None,
        "__spec__": None,
        "__cached__": None,
        "__builtins__": shared_builtins,
    }
    second = dict(first)
    first_code = compile(source_text, V14_SOURCE_PATH, "exec", dont_inherit=True, optimize=0)
    second_code = compile(source_text, V14_SOURCE_PATH, "exec", dont_inherit=True, optimize=0)
    if _code_signature(first_code) != _code_signature(second_code):
        raise V15StaticControlError("retained V14 root code comparison failed")
    exec(first_code, first, first)
    _normal_v14_slots_clean(system)
    exec(second_code, second, second)
    _normal_v14_slots_clean(system)
    first_signature = _module_graph_signature(first)
    second_signature = _module_graph_signature(second)
    if first_signature != second_signature:
        raise V15StaticControlError("retained V14 function/class/control graph comparison failed")
    required = (
        "BlackwellV14StaticControlSnapshot",
        "V14StaticControlError",
        "create_static_control_snapshot_v14",
        "open_production_blackwell_v14",
        "bounded_engineering_candidate_v14",
    )
    if any(name not in first or name not in second for name in required):
        raise V15StaticControlError("retained V14 required graph member is absent")
    if first["PRODUCTION_ROUTING_AUTHORIZED"] is not False:
        raise V15StaticControlError("retained V14 production truth drifted")
    if first["LIVE_EXECUTION_AUTHORIZED_BY_THIS_SOURCE"] is not False:
        raise V15StaticControlError("retained V14 live truth drifted")
    if first["FUTURE_HARNESS_AUTHORING_AUTHORIZED"] is not False:
        raise V15StaticControlError("retained V14 harness truth drifted")
    if first["PLAYBACK_AUTHORIZED"] is not False:
        raise V15StaticControlError("retained V14 playback truth drifted")
    if first["SYNTHESIS_AUTHORIZED"] is not False or first["LATENCY_RUN_AUTHORIZED"] is not False:
        raise V15StaticControlError("retained V14 synthesis/latency truth drifted")
    _exact_immutable_tree(first_signature, "retained V14 graph signature")
    result = first_signature
    first.clear()
    second.clear()
    if first or second:
        raise V15StaticControlError("retained V14 private globals were not destroyed")
    _normal_v14_slots_clean(system)
    return result


def _validate_v15_config(
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
        "preserved_v14_source_path",
        "preserved_v14_source_bytes",
        "preserved_v14_source_sha256",
        "preserved_v14_config_path",
        "preserved_v14_config_bytes",
        "preserved_v14_config_sha256",
        "preserved_v14_seal_path",
        "preserved_v14_seal_bytes",
        "preserved_v14_seal_sha256",
        "v14_rejection_decision_path",
        "v14_rejection_decision_bytes",
        "v14_rejection_decision_sha256",
        "v14_rejection_checkpoint_path",
        "v14_rejection_checkpoint_bytes",
        "v14_rejection_checkpoint_sha256",
        "preserved_v14_subject_count",
        "preserved_v14_subjects",
        "production_routing_authorized",
        "live_execution_authorized",
        "future_harness_authoring_authorized",
        "synthesis_authorized",
        "playback_authorized",
        "latency_run_authorized",
        "different_fresh_static_audit_required",
    )
    value = _exact_keys(_parse_canonical_json(raw, "V15 config"), keys, "V15 config")
    if (
        value["schema"] != "kira.blackwell.v15.native_exact_control_anchor_config.v1"
        or value["candidate_id"] != CANDIDATE_ID
        or value["status"]
        != "AUTHOR_STATIC_ONLY_PENDING_BUILD_SEAL_AND_DIFFERENT_FRESH_AUDIT"
        or value["control_python_path"]
        != "Core/persistent_blackwell_voice_integration_v15.py"
        or value["native_source_path"]
        != "tools/native/kira_blackwell_voice_control_anchor_v15.c"
        or value["native_header_path"]
        != "tools/native/kira_blackwell_voice_control_anchor_v15_identity_anchor.h"
        or value["native_contract_path"]
        != "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v15/native_control_contract.json"
        or value["preserved_v14_source_path"]
        != "Core/persistent_blackwell_voice_integration_v14.py"
        or value["preserved_v14_source_bytes"] != 42108
        or value["preserved_v14_source_sha256"]
        != "1faeb894bc9ab9e0bd13c06d6af42497c548ee15310ba97c1cc56df902e26d5f"
        or value["preserved_v14_config_path"]
        != "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v14/candidate_config.json"
        or value["preserved_v14_config_bytes"] != 6184
        or value["preserved_v14_config_sha256"]
        != "c517afc9953ceae527f88afb0361b1022bcc45d19fc9c577d6e6e58f8ad96695"
        or value["preserved_v14_seal_path"]
        != "RecoverySprint/continuation_20260811/blackwell_v14_native_exact_control_anchor_static_preparation/attempt_01/STATIC_SEAL_MANIFEST.json"
        or value["preserved_v14_seal_bytes"] != 6425
        or value["preserved_v14_seal_sha256"]
        != "f995cf68ba1b82de0f56acb11c1b1bf73667602beae0a1e685c8eebde13cc4e8"
        or value["v14_rejection_decision_path"]
        != "RecoverySprint/continuation_20260811/blackwell_v14_native_exact_control_anchor_fresh_static_audit/attempt_01/AUDIT_DECISION.json"
        or value["v14_rejection_decision_bytes"] != 4399
        or value["v14_rejection_decision_sha256"]
        != "b555938d847955c2fb2844bc1894570ce06ec8b53e3011c9ec9bb9f865c78ecb"
        or value["v14_rejection_checkpoint_path"]
        != "RecoverySprint/continuation_20260811/blackwell_v14_native_exact_control_anchor_fresh_static_audit/attempt_01/CHECKPOINT.md"
        or value["v14_rejection_checkpoint_bytes"] != 3806
        or value["v14_rejection_checkpoint_sha256"]
        != "9f15de0358f7563861f034d36fca67fcb14aee0026d90242040807c3b8447fb7"
    ):
        raise V15StaticControlError("V15 exact predecessor/config values drifted")
    _exact_int(value["control_python_bytes"], "V15 control source bytes", minimum=1)
    _sha256_text(value["control_python_sha256"], "V15 control source digest")
    _exact_int(value["native_contract_bytes"], "V15 native contract bytes", minimum=1)
    _sha256_text(value["native_contract_sha256"], "V15 native contract digest")
    for prefix in ("preserved_v14_source", "preserved_v14_config", "preserved_v14_seal",
                   "v14_rejection_decision", "v14_rejection_checkpoint"):
        _exact_int(value[prefix + "_bytes"], prefix + " bytes", minimum=1)
        _sha256_text(value[prefix + "_sha256"], prefix + " digest")
    _exact_int(value["preserved_v14_subject_count"], "V15 predecessor count", minimum=1)
    for key in (
        "production_routing_authorized",
        "live_execution_authorized",
        "future_harness_authoring_authorized",
        "synthesis_authorized",
        "playback_authorized",
        "latency_run_authorized",
    ):
        _exact_bool(value[key], False, "V15 config " + key)
    _exact_bool(value["different_fresh_static_audit_required"], True, "V15 audit truth")
    subjects = _subject_rows(value["preserved_v14_subjects"], label="V15 predecessors")
    if len(subjects) != value["preserved_v14_subject_count"] or len(subjects) != 6:
        raise V15StaticControlError("V15 predecessor subject count is not exactly 6")
    attested_simple = tuple((path, size, digest) for path, size, digest, _volume, _id in attestations)
    if subjects != attested_simple:
        raise V15StaticControlError("V15 predecessor subjects differ from native attestations")
    return subjects


def _validate_v14_config(raw: bytes) -> None:
    value = _parse_json(raw)
    if type(value) is not dict:
        raise V15StaticControlError("V14 config is not an exact object")
    if (
        value.get("schema") != "kira.blackwell.v14.native_exact_control_anchor_config.v1"
        or value["candidate_id"]
        != "kira_chatterbox_blackwell_native_exact_control_anchor_candidate_v14"
        or value["status"] != "AUTHOR_STATIC_ONLY_PENDING_BUILD_SEAL_AND_DIFFERENT_FRESH_AUDIT"
        or value["control_python_path"] != "Core/persistent_blackwell_voice_integration_v14.py"
        or value["control_python_bytes"] != 42108
        or value["control_python_sha256"]
        != "1faeb894bc9ab9e0bd13c06d6af42497c548ee15310ba97c1cc56df902e26d5f"
        or value["preserved_v13_subject_count"] != 15
    ):
        raise V15StaticControlError("V14 config identity drifted")
    for key in (
        "production_routing_authorized", "live_execution_authorized",
        "future_harness_authoring_authorized", "synthesis_authorized",
        "playback_authorized", "latency_run_authorized",
    ):
        _exact_bool(value[key], False, "V14 config " + key)
    _exact_bool(value["different_fresh_static_audit_required"], True, "V14 audit truth")
    rows = _subject_rows(value["preserved_v13_subjects"], label="V14 predecessor rows")
    if len(rows) != 15:
        raise V15StaticControlError("V14 predecessor rows are not exactly 15")


def _validate_v14_seal(raw: bytes, subjects: tuple[tuple[str, int, str], ...]) -> None:
    keys = (
        "schema", "candidate_id", "status", "execution_authority",
        "candidate_executed", "python_candidate_invoked", "model_calls",
        "gpu_voice_calls", "synthesis_calls", "playback_calls",
        "latency_measurements", "sealed_subject_count", "unique_paths", "subjects",
    )
    value = _exact_keys(_parse_json(raw), keys, "V14 seal")
    if (
        value["schema"] != "kira.blackwell.v14.native_exact_control_anchor.static_seal.v1"
        or value["candidate_id"]
        != "kira_chatterbox_blackwell_native_exact_control_anchor_candidate_v14"
        or value["status"] != "SEALED_STATIC_ONLY_PENDING_DIFFERENT_FRESH_AUDIT"
        or value["execution_authority"] != "NONE"
    ):
        raise V15StaticControlError("V14 seal identity drifted")
    seal_rows = _subject_rows(value["subjects"], label="V14 seal subjects")
    if _exact_int(value["sealed_subject_count"], "V14 seal subject count", minimum=1) != 30:
        raise V15StaticControlError("V14 seal count is not exactly 30")
    if len(seal_rows) != 30 or len(set(path for path, _size, _digest in seal_rows)) != 30:
        raise V15StaticControlError("V14 seal rows are not exactly 30 unique paths")
    _exact_bool(value["unique_paths"], True, "V14 unique-path truth")
    _exact_bool(value["candidate_executed"], False, "V14 execution truth")
    _exact_bool(value["python_candidate_invoked"], False, "V14 Python invocation truth")
    for key in ("model_calls", "gpu_voice_calls", "synthesis_calls", "playback_calls", "latency_measurements"):
        if _exact_int(value[key], "V14 seal " + key) != 0:
            raise V15StaticControlError("V14 seal call count is nonzero")
    required = {
        ("Core/persistent_blackwell_voice_integration_v14.py", 42108,
         "1faeb894bc9ab9e0bd13c06d6af42497c548ee15310ba97c1cc56df902e26d5f"),
        ("Voice/sidecars/chatterbox_blackwell_persistent_candidate_v14/candidate_config.json", 6184,
         "c517afc9953ceae527f88afb0361b1022bcc45d19fc9c577d6e6e58f8ad96695"),
    }
    if not required.issubset(set(seal_rows)):
        raise V15StaticControlError("V14 seal omits its exact source/config rows")
    subject_set = set(subjects)
    for required_path in (
        "Core/persistent_blackwell_voice_integration_v14.py",
        "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v14/candidate_config.json",
        "RecoverySprint/continuation_20260811/blackwell_v14_native_exact_control_anchor_static_preparation/attempt_01/STATIC_SEAL_MANIFEST.json",
    ):
        if not any(row[0] == required_path for row in subject_set):
            raise V15StaticControlError("V15 native predecessor closure omits " + required_path)


def _validate_v14_decision(raw: bytes) -> None:
    value = _exact_keys(
        _parse_json(raw),
        (
            "schema", "recorded_utc", "reviewer_task", "decision",
            "accepted_static_only", "one_bounded_disconnected_static_control_validation_authorized",
            "production_routing_authorized", "live_execution_authorized",
            "future_harness_authoring_authorized", "synthesis_authorized",
            "playback_authorized", "latency_run_authorized", "seal",
            "independent_native_build", "pe_static_inspection", "static_tests",
            "blocking_findings", "scope_truth", "required_next_step",
        ),
        "V14 rejection decision",
    )
    if (
        value["schema"] != "kira.blackwell.v14.native_exact_control_anchor.independent_static_audit_decision.v1"
        or value["decision"] != "REJECT"
    ):
        raise V15StaticControlError("V14 rejection decision identity drifted")
    for key in (
        "accepted_static_only", "one_bounded_disconnected_static_control_validation_authorized",
        "production_routing_authorized", "live_execution_authorized",
        "future_harness_authoring_authorized", "synthesis_authorized",
        "playback_authorized", "latency_run_authorized",
    ):
        _exact_bool(value[key], False, "V14 decision " + key)
    findings = value["blocking_findings"]
    if type(findings) is not list or len(findings) != 4:
        raise V15StaticControlError("V14 rejection does not contain exactly four blockers")
    identifiers = []
    for index, finding in enumerate(findings):
        item = _exact_keys(finding, ("id", "evidence"), f"V14 blocker {index}")
        if type(item["id"]) is not str or type(item["evidence"]) is not str:
            raise V15StaticControlError("V14 blocker fields are not exact strings")
        identifiers.append(item["id"])
    if tuple(identifiers) != (
        "BLOCK_V14_SNAPSHOT_STATE_MUTABLE_NOT_ORIGIN_BOUND",
        "BLOCK_V14_LOADER_GRAPH_STATE_NOT_EXACT_TYPED",
        "BLOCK_V14_COMPLETE_GRAPH_OMITS_MUTABLE_INSTANCE_STATE",
        "BLOCK_V14_POSTCALL_V12_PARENT_ATTRIBUTE_NOT_RECHECKED",
    ):
        raise V15StaticControlError("V14 blocker identities drifted")


def create_static_control_result_v15(
    config_raw: bytes,
    v14_source_raw: bytes,
    v14_config_raw: bytes,
    v14_seal_raw: bytes,
    v14_decision_raw: bytes,
    native_attestations: tuple[tuple[str, int, str, int, bytes], ...],
    native_expected_v14_graph: tuple[object, ...],
) -> tuple[object, ...]:
    system = __import__("sys")
    _normal_v14_slots_clean(system)
    attestations = _attestations(native_attestations)
    subjects = _validate_v15_config(config_raw, attestations)
    _validate_v14_config(v14_config_raw)
    _validate_v14_seal(v14_seal_raw, subjects)
    _validate_v14_decision(v14_decision_raw)
    graph = _validate_v14_graph(v14_source_raw)
    if type(native_expected_v14_graph) is not tuple:
        raise V15StaticControlError("native expected V14 graph is not an exact tuple")
    _exact_immutable_tree(native_expected_v14_graph, "native expected V14 graph")
    if graph != native_expected_v14_graph:
        raise V15StaticControlError("V14 graph differs from native creation-time graph")
    if tuple((path, size, digest) for path, size, digest, _volume, _identity in attestations) != subjects:
        raise V15StaticControlError("native attestations differ at result construction")
    loader_state = ("private_globals_only", None, None, None, False)
    result = (
        "kira.blackwell.v15.immutable_origin_bound_control_result.v1",
        CANDIDATE_ID,
        True,
        False,
        attestations,
        native_expected_v14_graph,
        loader_state,
        False, False, False, False, False, False,
    )
    _exact_immutable_tree(result, "V15 immutable control result")
    _normal_v14_slots_clean(system)
    return result


def open_production_blackwell_v15(*_args: object, **_kwargs: object) -> None:
    raise V15StaticControlError(
        "V15 is disconnected static evidence and authorizes no production or live route"
    )


def bounded_engineering_candidate_v15(*_args: object, **_kwargs: object) -> None:
    raise V15StaticControlError(
        "V15 authorizes no model, voice, synthesis, playback, or latency run"
    )


__all__ = (
    "CANDIDATE_ID",
    "FUTURE_HARNESS_AUTHORING_AUTHORIZED",
    "LATENCY_RUN_AUTHORIZED",
    "LIVE_EXECUTION_AUTHORIZED_BY_THIS_SOURCE",
    "PLAYBACK_AUTHORIZED",
    "PRODUCTION_ROUTING_AUTHORIZED",
    "SYNTHESIS_AUTHORIZED",
    "V15StaticControlError",
    "bounded_engineering_candidate_v15",
    "create_static_control_result_v15",
    "open_production_blackwell_v15",
)
