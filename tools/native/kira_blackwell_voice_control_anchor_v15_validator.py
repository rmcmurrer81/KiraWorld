"""Private validator payload for the Blackwell V15 native anchor.

The exact native controller compiles these locked bytes into a private globals
dictionary.  This file is never an ordinary module and exposes no live route.
"""

from __future__ import annotations


class NativeValidatorError(RuntimeError):
    pass


def _typed(value: object, globals_map: dict[str, object]) -> object:
    if value is None or type(value) in (bool, int, float, str, bytes):
        return (type(value).__name__, value)
    if type(value) is tuple:
        return ("tuple", tuple(_typed(item, globals_map) for item in value))
    if type(value) is list:
        return ("list", tuple(_typed(item, globals_map) for item in value))
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise NativeValidatorError("non-string dictionary key")
        return ("dict", tuple((key, _typed(value[key], globals_map)) for key in sorted(value)))
    if type(value) is set:
        return ("set", tuple(sorted(_typed(item, globals_map) for item in value)))
    if type(value) is frozenset:
        return ("frozenset", tuple(sorted(_typed(item, globals_map) for item in value)))
    if type(value).__name__ == "module":
        return (
            "shared_module", getattr(value, "__name__", None),
            getattr(value, "__file__", None), type(getattr(value, "__loader__", None)).__name__,
        )
    static_path = globals_map.get("_StaticPath")
    if type(static_path) is type and type(value) is static_path:
        if type(value._text) is not str:
            raise NativeValidatorError("static path text is not exact")
        return ("static_path_identity", id(value), value._text)
    static_namespace = globals_map.get("_StaticImportNamespace")
    if type(static_namespace) is type and type(value) is static_namespace:
        return (
            "static_namespace_identity", id(value),
            _typed(value.__name__, globals_map), _typed(value.machinery, globals_map),
            _typed(value.Path, globals_map), _typed(value.Any, globals_map),
        )
    for name, item in globals_map.items():
        if value is item and type(item).__name__ == "function":
            return ("module_function", name)
        if value is item and type(item) is type:
            return ("module_class", name)
    if type(value) is type:
        return ("shared_class", value.__module__, value.__qualname__)
    return ("shared_identity", type(value).__module__, type(value).__qualname__, id(value))


def _typed_cross(value: object, globals_map: dict[str, object]) -> object:
    """Semantic snapshot for two separately executed exact-source graphs."""
    if value is None or type(value) in (bool, int, float, str, bytes):
        return (type(value).__name__, value)
    if type(value) is tuple:
        return ("tuple", tuple(_typed_cross(item, globals_map) for item in value))
    if type(value) is list:
        return ("list", tuple(_typed_cross(item, globals_map) for item in value))
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise NativeValidatorError("non-string dictionary key")
        return (
            "dict",
            tuple((key, _typed_cross(value[key], globals_map)) for key in sorted(value)),
        )
    if type(value) is set:
        return ("set", tuple(sorted(_typed_cross(item, globals_map) for item in value)))
    if type(value) is frozenset:
        return ("frozenset", tuple(sorted(_typed_cross(item, globals_map) for item in value)))
    if type(value).__name__ == "module":
        return (
            "shared_module", getattr(value, "__name__", None),
            getattr(value, "__file__", None), type(getattr(value, "__loader__", None)).__name__,
        )
    static_path = globals_map.get("_StaticPath")
    if type(static_path) is type and type(value) is static_path:
        if type(value._text) is not str:
            raise NativeValidatorError("cross static path text is not exact")
        return ("static_path", value._text)
    static_namespace = globals_map.get("_StaticImportNamespace")
    if type(static_namespace) is type and type(value) is static_namespace:
        return (
            "static_import_namespace",
            _typed_cross(value.__name__, globals_map),
            _typed_cross(value.machinery, globals_map),
            _typed_cross(value.Path, globals_map),
            _typed_cross(value.Any, globals_map),
        )
    for name, item in globals_map.items():
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
    raise NativeValidatorError(
        "cross graph contains unsupported opaque instance: "
        + type(value).__module__ + "." + type(value).__qualname__
    )


def _code(code: object) -> tuple[object, ...]:
    if type(code).__name__ != "code":
        raise NativeValidatorError("non-code object")
    constants = []
    for value in code.co_consts:
        if type(value).__name__ == "code":
            constants.append(("code", _code(value)))
        elif value is None or type(value) in (bool, int, float, str, bytes, tuple):
            constants.append(("constant", repr(value)))
        else:
            constants.append(("typed_constant", type(value).__module__, type(value).__qualname__))
    return (
        code.co_argcount, code.co_posonlyargcount, code.co_kwonlyargcount,
        code.co_nlocals, code.co_stacksize, code.co_flags, code.co_code,
        tuple(constants), code.co_names, code.co_varnames, code.co_filename,
        code.co_name, code.co_qualname, code.co_firstlineno, code.co_linetable,
        code.co_exceptiontable, code.co_freevars, code.co_cellvars,
    )


def _function(function: object, globals_map: dict[str, object]) -> tuple[object, ...]:
    if type(function).__name__ != "function" or function.__globals__ is not globals_map:
        raise NativeValidatorError("function/globals identity drift")
    globals_used = []
    builtins_used = []
    for name in function.__code__.co_names:
        if name in globals_map:
            globals_used.append((name, _typed(globals_map[name], globals_map)))
        elif name in function.__builtins__:
            item = function.__builtins__[name]
            builtins_used.append((name, id(item), type(item).__module__, type(item).__qualname__))
    closure = tuple(
        (id(cell), _typed(cell.cell_contents, globals_map))
        for cell in tuple(function.__closure__ or ())
    )
    return (
        function.__name__, function.__qualname__, function.__module__,
        _code(function.__code__), id(function.__code__),
        _typed(function.__defaults__, globals_map), id(function.__defaults__),
        _typed(function.__kwdefaults__, globals_map), id(function.__kwdefaults__),
        _typed(function.__annotations__, globals_map), id(function.__annotations__),
        _typed(function.__dict__, globals_map), id(function.__dict__),
        closure, tuple(globals_used), tuple(builtins_used), id(function.__builtins__),
    )


def _function_cross(function: object, globals_map: dict[str, object]) -> tuple[object, ...]:
    """Cross-compile signature omits identities that must differ by construction."""
    if type(function).__name__ != "function" or function.__globals__ is not globals_map:
        raise NativeValidatorError("cross function/globals identity drift")
    globals_used = []
    builtins_used = []
    for name in function.__code__.co_names:
        if name in globals_map:
            globals_used.append((name, _typed_cross(globals_map[name], globals_map)))
        elif name in function.__builtins__:
            item = function.__builtins__[name]
            builtins_used.append((name, type(item).__module__, type(item).__qualname__))
    closure = tuple(
        _typed_cross(cell.cell_contents, globals_map)
        for cell in tuple(function.__closure__ or ())
    )
    return (
        function.__name__, function.__qualname__, function.__module__, _code(function.__code__),
        _typed_cross(function.__defaults__, globals_map),
        _typed_cross(function.__kwdefaults__, globals_map),
        _typed_cross(function.__annotations__, globals_map),
        _typed_cross(function.__dict__, globals_map),
        closure, tuple(globals_used), tuple(builtins_used), ("exact_builtins_dictionary",),
    )


def _class(value: type, globals_map: dict[str, object], *, cross: bool) -> tuple[object, ...]:
    members = []
    seal = _function_cross if cross else _function
    for name, member in value.__dict__.items():
        if type(member).__name__ == "function" and member.__globals__ is globals_map:
            snapshot = ("function", seal(member, globals_map))
        elif type(member) is staticmethod:
            snapshot = ("staticmethod", seal(member.__func__, globals_map))
        elif type(member) is classmethod:
            snapshot = ("classmethod", seal(member.__func__, globals_map))
        elif type(member) is property:
            pieces = []
            for function in (member.fget, member.fset, member.fdel):
                pieces.append(None if function is None else seal(function, globals_map))
            snapshot = ("property", tuple(pieces), member.__doc__)
        else:
            snapshot = (
                "value",
                _typed_cross(member, globals_map) if cross else _typed(member, globals_map),
            )
        members.append((name, snapshot))
    return (
        value.__name__, value.__qualname__, value.__module__,
        tuple((base.__module__, base.__qualname__) for base in value.__bases__), tuple(members),
    )


def _graph(globals_map: dict[str, object], *, cross: bool) -> tuple[object, ...]:
    if type(globals_map) is not dict:
        raise NativeValidatorError("globals map is not exact dict")
    function_seal = _function_cross if cross else _function
    rows = []
    for name in sorted(globals_map):
        value = globals_map[name]
        if name == "__builtins__":
            if type(value) is not dict:
                raise NativeValidatorError("builtins map is not exact dict")
            rows.append(
                (name, ("exact_builtins_dictionary",) if cross else ("builtins", id(value)))
            )
        elif type(value).__name__ == "function" and value.__globals__ is globals_map:
            rows.append((name, ("function", function_seal(value, globals_map))))
        elif type(value) is type and value.__module__ == globals_map.get("__name__"):
            rows.append((name, ("class", _class(value, globals_map, cross=cross))))
        else:
            rows.append(
                (
                    name,
                    (
                        "value",
                        _typed_cross(value, globals_map) if cross else _typed(value, globals_map),
                    ),
                )
            )
    return tuple(rows)


def _slots_clean(system: object) -> None:
    names = (
        "Core.persistent_blackwell_voice_integration_v15",
        "Core.persistent_blackwell_voice_integration_v14",
        "Core.persistent_blackwell_voice_integration_v13",
        "_kira_blackwell_v14_private_v13_graph",
        "_kira_blackwell_v13_exact_v12_control_plane",
        "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v12.canonical_typed_memory_binding",
    )
    if any(name in system.modules for name in names):
        raise NativeValidatorError("ordinary candidate/predecessor slot occupied")
    package = system.modules.get("Core")
    if package is not None and (
        hasattr(package, "persistent_blackwell_voice_integration_v15")
        or hasattr(package, "persistent_blackwell_voice_integration_v14")
        or hasattr(package, "persistent_blackwell_voice_integration_v13")
    ):
        raise NativeValidatorError("ordinary Core package attribute occupied")
    v12_parent = system.modules.get(
        "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v12"
    )
    if v12_parent is not None and hasattr(v12_parent, "canonical_typed_memory_binding"):
        raise NativeValidatorError("ordinary V12 parent package attribute occupied")


def _immutable(value: object, label: str) -> None:
    if value is None or type(value) in (bool, int, float, str, bytes):
        if type(value) is float and not (-float("inf") < value < float("inf")):
            raise NativeValidatorError(label + " contains non-finite float")
        return
    if type(value) is tuple:
        for index, item in enumerate(value):
            _immutable(item, label + "[" + str(index) + "]")
        return
    raise NativeValidatorError(label + " contains mutable/non-built-in state")


def _attestations_exact(value: object) -> None:
    if type(value) is not tuple or len(value) != 6:
        raise NativeValidatorError("native attestations are not exactly six rows")
    seen = set()
    for row in value:
        if type(row) is not tuple or len(row) != 5:
            raise NativeValidatorError("native attestation row shape is not exact")
        path, size, digest, volume, file_id = row
        if (
            type(path) is not str or not path or path in seen
            or type(size) is not int or size <= 0
            or type(digest) is not str or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
            or type(volume) is not int or volume < 0
            or type(file_id) is not bytes or len(file_id) != 16
        ):
            raise NativeValidatorError("native attestation row values are not exact")
        seen.add(path)


def _same_identity_graph(globals_map: dict[str, object], captured: tuple[object, ...]) -> None:
    keys, values, graph = captured
    if tuple(sorted(globals_map)) != keys:
        raise NativeValidatorError("V15 global schema changed")
    for name, expected in values:
        if globals_map.get(name, object()) is not expected:
            raise NativeValidatorError("V15 global identity changed: " + name)
    if _graph(globals_map, cross=False) != graph:
        raise NativeValidatorError("V15 complete graph changed")


def validate_static_control_graph_v15(
    v15_source: bytes,
    v15_config: bytes,
    v14_source: bytes,
    v14_config: bytes,
    v14_seal: bytes,
    v14_decision: bytes,
    attestations: tuple[tuple[str, int, str, int, bytes], ...],
) -> tuple[object, ...]:
    """Run one private disconnected graph and exact-state validation."""
    for label, value in (
        ("V15 source", v15_source), ("V15 config", v15_config),
        ("V14 source", v14_source), ("V14 config", v14_config),
        ("V14 seal", v14_seal), ("V14 decision", v14_decision),
    ):
        if type(value) is not bytes or not value:
            raise NativeValidatorError(label + " is not exact nonempty bytes")
    _attestations_exact(attestations)
    system = __import__("sys")
    _slots_clean(system)
    try:
        text = v15_source.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise NativeValidatorError("V15 source is not strict UTF-8") from exc
    builtins_map = __builtins__
    if type(builtins_map) is not dict:
        builtins_map = builtins_map.__dict__
    seed = {
        "__name__": "_kira_blackwell_v15_private_control_graph",
        "__file__": "C:/Users/robmc/Kira/Core/persistent_blackwell_voice_integration_v15.py",
        "__package__": "",
        "__loader__": None,
        "__spec__": None,
        "__cached__": None,
        "__builtins__": builtins_map,
    }
    primary = dict(seed)
    reference = dict(seed)
    first_code = compile(text, seed["__file__"], "exec", dont_inherit=True, optimize=0)
    second_code = compile(text, seed["__file__"], "exec", dont_inherit=True, optimize=0)
    if _code(first_code) != _code(second_code):
        raise NativeValidatorError("V15 root code differs across exact compiles")
    exec(first_code, primary, primary)
    _slots_clean(system)
    exec(second_code, reference, reference)
    _slots_clean(system)
    if _graph(primary, cross=True) != _graph(reference, cross=True):
        raise NativeValidatorError("V15 complete source graph differs across exact compiles")
    required = (
        "V15StaticControlError", "create_static_control_result_v15",
        "open_production_blackwell_v15",
        "bounded_engineering_candidate_v15",
    )
    if any(name not in primary or name not in reference for name in required):
        raise NativeValidatorError("V15 required control graph member absent")
    keys = tuple(sorted(primary))
    values = tuple(primary.items())
    captured = (keys, values, _graph(primary, cross=False))
    if "BlackwellV15StaticControlSnapshot" in primary:
        raise NativeValidatorError("writable V15 snapshot class unexpectedly exists")
    factory = primary["create_static_control_result_v15"]
    if type(factory).__name__ != "function":
        raise NativeValidatorError("stored V15 factory reference is not exact")
    factory_code = factory.__code__
    _same_identity_graph(primary, captured)
    _slots_clean(system)

    try:
        v14_text = v14_source.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise NativeValidatorError("V14 source is not strict UTF-8") from exc
    v14_builtins = dict(builtins_map)
    v14_builtins["__import__"] = primary["_restricted_v14_import"]
    v14_seed = {
        "__name__": "_kira_blackwell_v15_private_v14_graph",
        "__file__": "C:/Users/robmc/Kira/Core/persistent_blackwell_voice_integration_v14.py",
        "__package__": "", "__loader__": None, "__spec__": None,
        "__cached__": None, "__builtins__": v14_builtins,
    }
    v14_primary = dict(v14_seed)
    v14_reference = dict(v14_seed)
    v14_first_code = compile(v14_text, v14_seed["__file__"], "exec", dont_inherit=True, optimize=0)
    v14_second_code = compile(v14_text, v14_seed["__file__"], "exec", dont_inherit=True, optimize=0)
    if _code(v14_first_code) != _code(v14_second_code):
        raise NativeValidatorError("V14 root code differs across native creation-time compiles")
    exec(v14_first_code, v14_primary, v14_primary)
    _slots_clean(system)
    exec(v14_second_code, v14_reference, v14_reference)
    _slots_clean(system)
    expected_v14_graph = _graph(v14_primary, cross=True)
    if expected_v14_graph != _graph(v14_reference, cross=True):
        raise NativeValidatorError("V14 creation-time complete graphs differ")
    _immutable(expected_v14_graph, "native V14 creation-time graph")
    v14_keys = tuple(sorted(v14_primary))
    v14_values = tuple(v14_primary.items())

    state = factory(
        v15_config, v14_source, v14_config, v14_seal, v14_decision,
        attestations, expected_v14_graph,
    )
    _same_identity_graph(primary, captured)
    _slots_clean(system)
    if factory.__code__ is not factory_code:
        raise NativeValidatorError("stored V15 callable code changed")
    if tuple(sorted(v14_primary)) != v14_keys:
        raise NativeValidatorError("V14 creation-time graph schema changed")
    for name, expected in v14_values:
        if v14_primary.get(name, object()) is not expected:
            raise NativeValidatorError("V14 creation-time global identity changed: " + name)
    if _graph(v14_primary, cross=True) != expected_v14_graph:
        raise NativeValidatorError("V14 creation-time graph changed across V15 call")
    if (
        type(state) is not tuple
        or len(state) != 13
        or state[0] != "kira.blackwell.v15.immutable_origin_bound_control_result.v1"
        or type(state[0]) is not str
        or state[1] != "kira_chatterbox_blackwell_native_exact_control_anchor_candidate_v15"
        or type(state[1]) is not str
        or state[2] is not True
        or state[3] is not False
        or state[4] is not attestations
        or state[4] != attestations
        or state[5] is not expected_v14_graph
        or state[5] != expected_v14_graph
        or type(state[6]) is not tuple
        or len(state[6]) != 5
        or type(state[6][0]) is not str
        or state[6] != ("private_globals_only", None, None, None, False)
        or any(type(value) is not bool or value is not False for value in state[7:13])
    ):
        raise NativeValidatorError("V15 immutable origin-bound result is not exact")
    _immutable(state, "V15 result")
    graph_count = len(expected_v14_graph)
    if type(graph_count) is not int or graph_count <= 0:
        raise NativeValidatorError("V14 exact graph row count is invalid")
    _same_identity_graph(primary, captured)
    _slots_clean(system)
    if factory.__code__ is not factory_code:
        raise NativeValidatorError("stored V15 callable code changed before destruction")
    state = None
    expected_v14_graph = None
    v14_primary.clear()
    v14_reference.clear()
    if v14_primary or v14_reference:
        raise NativeValidatorError("private V14 creation-time globals were not destroyed")
    primary.clear()
    reference.clear()
    if primary or reference:
        raise NativeValidatorError("private V15 globals were not destroyed")
    _slots_clean(system)
    return (
        "kira.blackwell.v15.native_validator_result.v1",
        True,
        6,
        graph_count,
        False,
        False,
        False,
        False,
        False,
        False,
    )


__all__ = ("NativeValidatorError", "validate_static_control_graph_v15")
