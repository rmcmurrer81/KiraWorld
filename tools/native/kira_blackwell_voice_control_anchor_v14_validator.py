"""Private validator payload for the Blackwell V14 native anchor.

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
    for name, item in globals_map.items():
        if value is item and type(item).__name__ == "function":
            return ("module_function", name)
        if value is item and type(item) is type:
            return ("module_class", name)
    if type(value) is type:
        return ("shared_class", value.__module__, value.__qualname__)
    return ("typed_object", type(value).__module__, type(value).__qualname__)


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
            builtins_used.append((name, id(item), type(item).__module__, type(item).__qualname__))
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
        closure, tuple(globals_used), tuple(builtins_used), id(function.__builtins__),
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
        tuple(base.__qualname__ for base in value.__bases__), tuple(members),
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
            rows.append((name, ("builtins", id(value))))
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
        "Core.persistent_blackwell_voice_integration_v14",
        "Core.persistent_blackwell_voice_integration_v13",
        "_kira_blackwell_v13_exact_v12_control_plane",
        "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v12.canonical_typed_memory_binding",
    )
    if any(name in system.modules for name in names):
        raise NativeValidatorError("ordinary candidate/predecessor slot occupied")
    package = system.modules.get("Core")
    if package is not None and (
        hasattr(package, "persistent_blackwell_voice_integration_v14")
        or hasattr(package, "persistent_blackwell_voice_integration_v13")
    ):
        raise NativeValidatorError("ordinary Core package attribute occupied")


def _same_identity_graph(globals_map: dict[str, object], captured: tuple[object, ...]) -> None:
    keys, values, graph = captured
    if tuple(sorted(globals_map)) != keys:
        raise NativeValidatorError("V14 global schema changed")
    for name, expected in values:
        if globals_map.get(name, object()) is not expected:
            raise NativeValidatorError("V14 global identity changed: " + name)
    if _graph(globals_map, cross=False) != graph:
        raise NativeValidatorError("V14 complete graph changed")


def validate_static_control_graph_v14(
    v14_source: bytes,
    v14_config: bytes,
    v13_source: bytes,
    v13_config: bytes,
    v13_seal: bytes,
    v13_decision: bytes,
    attestations: tuple[tuple[str, int, str, int, bytes], ...],
) -> tuple[object, ...]:
    """Run one private disconnected graph and exact-state validation."""
    for label, value in (
        ("V14 source", v14_source), ("V14 config", v14_config),
        ("V13 source", v13_source), ("V13 config", v13_config),
        ("V13 seal", v13_seal), ("V13 decision", v13_decision),
    ):
        if type(value) is not bytes or not value:
            raise NativeValidatorError(label + " is not exact nonempty bytes")
    if type(attestations) is not tuple or len(attestations) != 15:
        raise NativeValidatorError("native attestation tuple is not exactly 15 rows")
    system = __import__("sys")
    _slots_clean(system)
    try:
        text = v14_source.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise NativeValidatorError("V14 source is not strict UTF-8") from exc
    builtins_map = __builtins__
    if type(builtins_map) is not dict:
        builtins_map = builtins_map.__dict__
    seed = {
        "__name__": "_kira_blackwell_v14_private_control_graph",
        "__file__": "C:/Users/robmc/Kira/Core/persistent_blackwell_voice_integration_v14.py",
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
        raise NativeValidatorError("V14 root code differs across exact compiles")
    exec(first_code, primary, primary)
    _slots_clean(system)
    exec(second_code, reference, reference)
    _slots_clean(system)
    if _graph(primary, cross=True) != _graph(reference, cross=True):
        raise NativeValidatorError("V14 complete source graph differs across exact compiles")
    required = (
        "BlackwellV14StaticControlSnapshot", "V14StaticControlError",
        "create_static_control_snapshot_v14", "open_production_blackwell_v14",
        "bounded_engineering_candidate_v14",
    )
    if any(name not in primary or name not in reference for name in required):
        raise NativeValidatorError("V14 required control graph member absent")
    keys = tuple(sorted(primary))
    values = tuple(primary.items())
    captured = (keys, values, _graph(primary, cross=False))
    factory = primary["create_static_control_snapshot_v14"]
    snapshot_type = primary["BlackwellV14StaticControlSnapshot"]
    revalidate = snapshot_type.__dict__.get("revalidate")
    if type(factory).__name__ != "function" or type(revalidate).__name__ != "function":
        raise NativeValidatorError("stored V14 callable reference is not exact")
    factory_code = factory.__code__
    revalidate_code = revalidate.__code__
    _same_identity_graph(primary, captured)
    _slots_clean(system)
    snapshot = factory(
        v14_config, v13_source, v13_config, v13_seal, v13_decision, attestations
    )
    _same_identity_graph(primary, captured)
    _slots_clean(system)
    if factory.__code__ is not factory_code or revalidate.__code__ is not revalidate_code:
        raise NativeValidatorError("stored V14 callable code changed")
    if type(snapshot) is not snapshot_type:
        raise NativeValidatorError("V14 snapshot type is not exact")
    slots = snapshot_type.__slots__
    if type(slots) is not tuple or set(slots) != {
        "_seal", "_subjects", "_graph", "_prepared_static", "_quarantined",
        "_production", "_live", "_future_harness", "_synthesis", "_playback",
        "_latency", "_loader_state",
    }:
        raise NativeValidatorError("V14 snapshot slot schema changed")
    _same_identity_graph(primary, captured)
    _slots_clean(system)
    if factory.__code__ is not factory_code or revalidate.__code__ is not revalidate_code:
        raise NativeValidatorError("stored V14 callable code changed before revalidation")
    state = revalidate(snapshot)
    _same_identity_graph(primary, captured)
    _slots_clean(system)
    if factory.__code__ is not factory_code or revalidate.__code__ is not revalidate_code:
        raise NativeValidatorError("stored V14 callable code changed after call")
    if (
        type(state) is not tuple
        or len(state) != 13
        or state[0] != "kira.blackwell.v14.native_exact_control_snapshot.v1"
        or state[1] != "kira_chatterbox_blackwell_native_exact_control_anchor_candidate_v14"
        or state[2] is not True
        or state[3] is not False
        or state[5] != ("private_globals_only", None, None, None, False)
        or any(value is not False for value in state[6:12])
        or type(state[12]) is not int
        or state[12] != 15
    ):
        raise NativeValidatorError("V14 public immutable state is not exact")
    graph_count = state[4][1]
    if type(graph_count) is not int or graph_count <= 0:
        raise NativeValidatorError("V13 graph count is not exact")
    _same_identity_graph(primary, captured)
    _slots_clean(system)
    if factory.__code__ is not factory_code or revalidate.__code__ is not revalidate_code:
        raise NativeValidatorError("stored V14 callable code changed before destruction")
    state = None
    snapshot = None
    primary.clear()
    reference.clear()
    if primary or reference:
        raise NativeValidatorError("private V14 globals were not destroyed")
    _slots_clean(system)
    return (
        "kira.blackwell.v14.native_validator_result.v1",
        True,
        15,
        graph_count,
        False,
        False,
        False,
        False,
        False,
        False,
    )


__all__ = ("NativeValidatorError", "validate_static_control_graph_v14")
