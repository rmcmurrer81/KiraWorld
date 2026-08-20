from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping
import unicodedata

from jsonschema import SchemaError, ValidationError

if __package__:
    from .schema_tools import schema_validator
else:  # Direct script execution from the standalone directory.
    from schema_tools import schema_validator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INTAKE = (
    PROJECT_ROOT
    / "hanson_interface_intake"
    / "official-hanson-interface-intake.template.json"
)
DEFAULT_SCHEMA = (
    PROJECT_ROOT
    / "hanson_interface_intake"
    / "official-hanson-interface-intake.schema.json"
)

MAX_JSON_BYTES = 1_048_576
MAX_JSON_CHARACTERS = 1_048_576
MAX_JSON_DEPTH = 64
MAX_JSON_NODES = 100_000
MAX_CONTAINER_ITEMS = 10_000
MAX_STRING_CHARACTERS = 65_536
MAX_ABSOLUTE_JSON_NUMBER = 1_000_000_000_000_000
MAX_EVIDENCE_FUTURE_SKEW = timedelta(minutes=5)

UNSAFE_UNICODE_CATEGORIES = frozenset(
    {
        "Cc",  # controls, including C0/C1 and newlines
        "Cf",  # invisible format and bidi-control characters
        "Cs",  # lone UTF-16 surrogates
        "Co",  # private-use code points have no shared public meaning
        "Cn",  # unassigned code points, including most noncharacters
        "Zl",  # line separator
        "Zp",  # paragraph separator
    }
)
VISIBLE_UNICODE_CATEGORY_PREFIXES = frozenset({"L", "N", "P", "S"})

INTERFACE_CHANNELS = {
    "topic": frozenset({"topic"}),
    "action": frozenset({"goal", "result", "feedback", "status", "cancel"}),
    "service": frozenset({"request", "response", "event"}),
}


class IntakeReferenceError(ValueError):
    """Raised when a schema-valid intake has ambiguous or dangling identifiers."""


class IntakeInputError(ValueError):
    """Raised when input violates parser lexical, resource, or numeric bounds."""


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite_constant(value: str) -> None:
    raise IntakeInputError("nonfinite JSON literal")


def _preflight_json_text(text: str) -> None:
    if len(text) > MAX_JSON_CHARACTERS:
        raise IntakeInputError("JSON character limit exceeded")

    depth = 0
    in_string = False
    escaped = False
    for character in text:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character in "[{":
            depth += 1
            if depth > MAX_JSON_DEPTH:
                raise IntakeInputError("JSON depth limit exceeded")
        elif character in "]}":
            depth -= 1
            if depth < 0:
                break


def _is_unicode_noncharacter(character: str) -> bool:
    code_point = ord(character)
    return 0xFDD0 <= code_point <= 0xFDEF or (code_point & 0xFFFF) in {
        0xFFFE,
        0xFFFF,
    }


def _validate_engineering_string(value: str, path: str) -> None:
    has_visible_character = False
    for character in value:
        category = unicodedata.category(character)
        if category in UNSAFE_UNICODE_CATEGORIES or _is_unicode_noncharacter(
            character
        ):
            raise IntakeInputError(f"unsafe Unicode category at {path}")
        has_visible_character = (
            has_visible_character
            or category[0] in VISIBLE_UNICODE_CATEGORY_PREFIXES
        )
    if value and not has_visible_character:
        raise IntakeInputError(f"string has no visible engineering text at {path}")


def _validate_unicode_lexical_safety(value: Any) -> None:
    """Reject invisible/control-only engineering strings without echoing values."""

    stack: list[tuple[Any, str]] = [(value, "$")]
    while stack:
        current, path = stack.pop()
        if isinstance(current, str):
            _validate_engineering_string(current, path)
        elif isinstance(current, Mapping):
            for index, (key, child) in enumerate(current.items()):
                if isinstance(key, str):
                    _validate_engineering_string(key, f"{path}.<key[{index}]>")
                stack.append((child, f"{path}.<value[{index}]>"))
        elif isinstance(current, list):
            stack.extend(
                (child, f"{path}[{index}]")
                for index, child in enumerate(current)
            )


def _validate_parsed_resources(value: Any) -> None:
    _validate_unicode_lexical_safety(value)
    stack: list[tuple[Any, int]] = [(value, 1)]
    nodes = 0
    while stack:
        current, depth = stack.pop()
        nodes += 1
        if nodes > MAX_JSON_NODES:
            raise IntakeInputError("JSON node limit exceeded")
        if depth > MAX_JSON_DEPTH:
            raise IntakeInputError("JSON depth limit exceeded")
        if isinstance(current, float):
            if not math.isfinite(current):
                raise IntakeInputError("nonfinite JSON number")
            if abs(current) > MAX_ABSOLUTE_JSON_NUMBER:
                raise IntakeInputError("JSON numeric magnitude limit exceeded")
        elif isinstance(current, int) and not isinstance(current, bool):
            if abs(current) > MAX_ABSOLUTE_JSON_NUMBER:
                raise IntakeInputError("JSON numeric magnitude limit exceeded")
        elif isinstance(current, str):
            if len(current) > MAX_STRING_CHARACTERS:
                raise IntakeInputError("JSON string limit exceeded")
        elif isinstance(current, Mapping):
            if len(current) > MAX_CONTAINER_ITEMS:
                raise IntakeInputError("JSON object member limit exceeded")
            stack.extend((child, depth + 1) for child in current.values())
        elif isinstance(current, list):
            if len(current) > MAX_CONTAINER_ITEMS:
                raise IntakeInputError("JSON array item limit exceeded")
            stack.extend((child, depth + 1) for child in current)


def strict_json_loads(text: str) -> Any:
    """Parse bounded engineering JSON and reject duplicates or unsafe scalars."""

    _preflight_json_text(text)
    try:
        value = json.loads(
            text,
            object_pairs_hook=_object_without_duplicate_keys,
            parse_constant=_reject_nonfinite_constant,
        )
    except RecursionError as exc:
        raise IntakeInputError("JSON recursion limit exceeded") from exc
    _validate_parsed_resources(value)
    return value


def _read_bounded_utf8(path: Path) -> str:
    if path.stat().st_size > MAX_JSON_BYTES:
        raise IntakeInputError("JSON file size limit exceeded")
    raw = path.read_bytes()
    if len(raw) > MAX_JSON_BYTES:
        raise IntakeInputError("JSON file size limit exceeded")
    return raw.decode("utf-8")


def _unique_index(
    entries: Iterable[Mapping[str, Any]], id_field: str, label: str
) -> dict[str, Mapping[str, Any]]:
    index: dict[str, Mapping[str, Any]] = {}
    for entry in entries:
        identifier = entry[id_field]
        if identifier in index:
            raise IntakeReferenceError(f"duplicate {label} id: {identifier}")
        index[identifier] = entry
    return index


def _walk_source_references(
    value: Any, known_source_ids: set[str], path: str = "$"
) -> None:
    if isinstance(value, Mapping):
        source_ids = value.get("source_ids")
        if isinstance(source_ids, list):
            for source_id in source_ids:
                if source_id not in known_source_ids:
                    raise IntakeReferenceError(
                        f"{path}.source_ids references unknown source id: {source_id}"
                    )
        for key, child in value.items():
            _walk_source_references(child, known_source_ids, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_source_references(child, known_source_ids, f"{path}[{index}]")


def _require_known(
    values: Iterable[str], known: Mapping[str, Any], path: str, label: str
) -> None:
    for value in values:
        if value not in known:
            raise IntakeReferenceError(f"{path} references unknown {label} id: {value}")


def _require_interface_role(
    values: Iterable[str],
    interfaces: Mapping[str, Mapping[str, Any]],
    expected_roles: frozenset[str],
    path: str,
) -> None:
    _require_known(values, interfaces, path, "interface")
    for interface_id in values:
        if interfaces[interface_id]["capability"] not in expected_roles:
            raise IntakeReferenceError(f"{path} references an interface with the wrong role")


def _require_confirmed(confirmation: Mapping[str, Any], path: str) -> None:
    if confirmation["status"] != "confirmed_official" or not confirmation["source_ids"]:
        raise IntakeReferenceError(f"{path} is not confirmed from an official source")


def _require_official_text(field: Mapping[str, Any], path: str) -> str:
    if (
        field["status"] != "confirmed_official"
        or not isinstance(field["value"], str)
        or not any(
            unicodedata.category(character)[0]
            in VISIBLE_UNICODE_CATEGORY_PREFIXES
            for character in field["value"]
        )
        or not field["source_ids"]
    ):
        raise IntakeReferenceError(f"{path} requires a sourced official value")
    return field["value"]


def _require_official_list(
    field: Mapping[str, Any], path: str, *, nonempty: bool = True
) -> list[str]:
    if field["status"] != "confirmed_official" or not field["source_ids"]:
        raise IntakeReferenceError(f"{path} is not confirmed from an official source")
    values = field["values"]
    if nonempty and not values:
        raise IntakeReferenceError(f"{path} requires at least one official mapping")
    return values


def _require_official_positive_integer(field: Mapping[str, Any], path: str) -> int:
    if (
        field["status"] != "confirmed_official"
        or not isinstance(field["value"], int)
        or isinstance(field["value"], bool)
        or field["value"] <= 0
        or not field["source_ids"]
    ):
        raise IntakeReferenceError(f"{path} requires a positive sourced official value")
    return field["value"]


def _require_official_catalog(catalog: Mapping[str, Any], path: str) -> None:
    _require_confirmed(catalog["confirmation"], f"{path}.confirmation")
    if not catalog["entries"]:
        raise IntakeReferenceError(f"{path} requires at least one official entry")
    for index, entry in enumerate(catalog["entries"]):
        _require_confirmed(entry["confirmation"], f"{path}.entries[{index}].confirmation")


def _validate_frame_hierarchy(frames: Mapping[str, Mapping[str, Any]]) -> None:
    for frame_id, frame in frames.items():
        parent = frame["parent_frame_id"]
        if parent is None:
            continue
        if parent not in frames:
            raise IntakeReferenceError("frame parent references an unknown frame")
        if parent == frame_id:
            raise IntakeReferenceError("frame cannot be its own parent")

    for frame_id in frames:
        visited: set[str] = set()
        current: str | None = frame_id
        while current is not None:
            if current in visited:
                raise IntakeReferenceError("frame parent cycle detected")
            visited.add(current)
            current = frames[current]["parent_frame_id"]


def _validate_official_completeness(intake: Mapping[str, Any]) -> None:
    if intake["intake_status"] not in {
        "hanson_reviewed",
        "simulator_validated_for_named_versions",
    }:
        raise IntakeReferenceError(
            "--require-official requires a Hanson-reviewed intake status"
        )
    if not intake["official_sources"]:
        raise IntakeReferenceError("official_sources requires at least one entry")

    environment = intake["target_environment"]
    for field in (
        "ros_2_distribution",
        "ros_2_patch_release",
        "operating_system",
        "architecture",
        "python_version",
        "rmw_implementation",
        "time_source",
        "clock_synchronization",
    ):
        _require_official_text(environment[field], f"$.target_environment.{field}")

    simulator = environment["simulator"]
    for field in (
        "product_name",
        "version",
        "access_method",
        "launch_package",
        "launch_file_or_executable",
        "fixture",
        "readiness_signal",
        "shutdown_procedure",
    ):
        _require_official_text(simulator[field], f"$.target_environment.simulator.{field}")
    _require_official_list(
        simulator["launch_arguments"],
        "$.target_environment.simulator.launch_arguments",
        nonempty=False,
    )

    for catalog_name in ("packages", "interfaces", "frames", "units", "limits"):
        _require_official_catalog(intake[catalog_name], f"$.{catalog_name}")

    for index, interface in enumerate(intake["interfaces"]["entries"]):
        if not interface["qos_profiles"]:
            raise IntakeReferenceError(
                f"$.interfaces.entries[{index}].qos_profiles requires an official profile"
            )
        for qos_index, qos in enumerate(interface["qos_profiles"]):
            _require_confirmed(
                qos["confirmation"],
                f"$.interfaces.entries[{index}].qos_profiles[{qos_index}].confirmation",
            )

    for capability_name, capability in intake["capabilities"].items():
        path = f"$.capabilities.{capability_name}"
        _require_confirmed(capability["confirmation"], f"{path}.confirmation")
        _require_official_list(capability["interface_ids"], f"{path}.interface_ids")

    lifecycle = intake["lifecycle_semantics"]
    _require_confirmed(lifecycle["confirmation"], "$.lifecycle_semantics.confirmation")
    _require_official_list(
        lifecycle["status_interface_ids"],
        "$.lifecycle_semantics.status_interface_ids",
    )
    for state_name in (
        "request_admission",
        "requested",
        "accepted",
        "started",
        "completed",
        "rejected",
        "failed",
        "cancelled",
        "interrupted",
        "expired",
    ):
        state = lifecycle[state_name]
        path = f"$.lifecycle_semantics.{state_name}"
        _require_confirmed(state["confirmation"], f"{path}.confirmation")
        _require_official_text(
            state["official_state_or_outcome"], f"{path}.official_state_or_outcome"
        )

    session = intake["session_and_liveness"]
    _require_confirmed(session["confirmation"], "$.session_and_liveness.confirmation")
    for field in (
        "capability_discovery_interface_ids",
        "session_interface_ids",
        "heartbeat_interface_ids",
    ):
        _require_official_list(session[field], f"$.session_and_liveness.{field}")
    for field in ("session_ttl_ms", "heartbeat_period_ms", "heartbeat_timeout_ms"):
        _require_official_positive_integer(
            session[field], f"$.session_and_liveness.{field}"
        )

    safety = intake["safety_semantics"]
    _require_confirmed(safety["confirmation"], "$.safety_semantics.confirmation")
    _require_official_text(
        safety["authoritative_physical_safety_component"],
        "$.safety_semantics.authoritative_physical_safety_component",
    )
    for safeguard_name in (
        "emergency_stop",
        "watchdog",
        "degraded_mode",
        "collision_or_safe_stop",
        "recovery",
    ):
        safeguard = safety[safeguard_name]
        path = f"$.safety_semantics.{safeguard_name}"
        _require_confirmed(safeguard["confirmation"], f"{path}.confirmation")
        _require_official_list(safeguard["interface_ids"], f"{path}.interface_ids")
        _require_official_list(safeguard["official_states"], f"{path}.official_states")

    _require_official_text(
        intake["review"]["hanson_review_disposition"],
        "$.review.hanson_review_disposition",
    )


def _resolution_paths(value: Any, path: str = "$") -> list[str]:
    unresolved: list[str] = []
    if isinstance(value, Mapping):
        status = value.get("status")
        if status in {"unresolved", "provided_unverified"}:
            unresolved.append(f"{path}: {status}")
        for key, child in value.items():
            unresolved.extend(_resolution_paths(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            unresolved.extend(_resolution_paths(child, f"{path}[{index}]"))
    return unresolved


def validate_references(intake: Mapping[str, Any], require_official: bool = False) -> None:
    """Check uniqueness and cross-references not expressible in draft JSON Schema."""

    _validate_unicode_lexical_safety(intake)
    sources = _unique_index(intake["official_sources"], "source_id", "source")
    packages = _unique_index(intake["packages"]["entries"], "package_id", "package")
    interfaces = _unique_index(
        intake["interfaces"]["entries"], "interface_id", "interface"
    )
    frames = _unique_index(intake["frames"]["entries"], "frame_id", "frame")
    units = _unique_index(intake["units"]["entries"], "unit_id", "unit")
    limits = _unique_index(intake["limits"]["entries"], "limit_id", "limit")

    _walk_source_references(intake, set(sources))

    for interface_id, interface in interfaces.items():
        path = f"$.interfaces.entries[{interface_id}]"
        _require_known([interface["package_id"]], packages, path, "package")
        _require_known(interface["frame_ids"], frames, path, "frame")
        _require_known(interface["unit_ids"], units, path, "unit")
        channels: set[str] = set()
        allowed_channels = INTERFACE_CHANNELS[interface["kind"]]
        for qos in interface["qos_profiles"]:
            channel = qos["channel"]
            if qos["history"] == "keep_last" and qos["depth"] is None:
                raise IntakeReferenceError(
                    f"{path}.qos_profiles keep_last history requires a positive depth"
                )
            if channel is None:
                continue
            if channel not in allowed_channels:
                raise IntakeReferenceError(
                    f"{path}.qos_profiles contains a channel incompatible with its kind"
                )
            if channel in channels:
                raise IntakeReferenceError(
                    f"{path}.qos_profiles contains a duplicate channel"
                )
            channels.add(channel)

    _validate_frame_hierarchy(frames)

    for limit_id, limit in limits.items():
        if limit["unit_id"] is not None:
            _require_known(
                [limit["unit_id"]], units, f"$.limits.entries[{limit_id}]", "unit"
            )
        lower = limit["lower_bound"]
        upper = limit["upper_bound"]
        if lower is not None and upper is not None and lower > upper:
            raise IntakeReferenceError(
                f"$.limits.entries[{limit_id}] has lower_bound above upper_bound"
            )

    for capability_name, capability in intake["capabilities"].items():
        path = f"$.capabilities.{capability_name}"
        requested_interfaces = capability["interface_ids"]["values"]
        _require_known(requested_interfaces, interfaces, path, "interface")
        _require_known(capability["frame_ids"]["values"], frames, path, "frame")
        _require_known(capability["unit_ids"]["values"], units, path, "unit")
        _require_known(capability["limit_ids"]["values"], limits, path, "limit")
        for interface_id in requested_interfaces:
            if interfaces[interface_id]["capability"] != capability_name:
                raise IntakeReferenceError(
                    f"{path} references {interface_id}, whose capability is "
                    f"{interfaces[interface_id]['capability']}"
                )
        for limit_id in capability["limit_ids"]["values"]:
            if limits[limit_id]["capability"] not in {
                capability_name,
                "cross_cutting",
            }:
                raise IntakeReferenceError(
                    f"{path} references a limit for a different capability"
                )

    lifecycle = intake["lifecycle_semantics"]
    _require_interface_role(
        lifecycle["status_interface_ids"]["values"],
        interfaces,
        frozenset({"execution_status"}),
        "$.lifecycle_semantics.status_interface_ids",
    )

    session = intake["session_and_liveness"]
    session_roles = {
        "capability_discovery_interface_ids": frozenset({"capability_discovery"}),
        "session_interface_ids": frozenset({"session_management"}),
        "heartbeat_interface_ids": frozenset({"session_liveness"}),
    }
    for field, expected_roles in session_roles.items():
        _require_interface_role(
            session[field]["values"],
            interfaces,
            expected_roles,
            f"$.session_and_liveness.{field}",
        )

    timer_values = (
        session["heartbeat_period_ms"]["value"],
        session["heartbeat_timeout_ms"]["value"],
        session["session_ttl_ms"]["value"],
    )
    if all(value is not None for value in timer_values):
        period, timeout, ttl = timer_values
        if not 0 < period <= timeout <= ttl:
            raise IntakeReferenceError(
                "session timers must satisfy 0 < heartbeat period <= timeout <= TTL"
            )

    safety = intake["safety_semantics"]
    for safeguard_name in (
        "emergency_stop",
        "watchdog",
        "degraded_mode",
        "collision_or_safe_stop",
        "recovery",
    ):
        _require_interface_role(
            safety[safeguard_name]["interface_ids"]["values"],
            interfaces,
            frozenset({"safety_state"}),
            f"$.safety_semantics.{safeguard_name}.interface_ids",
        )

    evidence_status = intake["review"]["simulator_evidence"]["status"]
    intake_status = intake["intake_status"]
    if (evidence_status == "passed_for_named_versions") != (
        intake_status == "simulator_validated_for_named_versions"
    ):
        raise IntakeReferenceError(
            "simulator evidence and intake promotion status are inconsistent"
        )
    if intake_status in {"awaiting_hanson_input", "partially_sourced"} and (
        evidence_status != "not_run"
    ):
        raise IntakeReferenceError(
            "unreviewed intake status cannot carry simulator run evidence"
        )

    evidence = intake["review"]["simulator_evidence"]
    if evidence_status != "not_run":
        if evidence["commit_sha"] == "0" * 40:
            raise IntakeReferenceError(
                "simulator evidence commit SHA cannot be Git's null object id"
            )
        try:
            completed_at = datetime.fromisoformat(
                evidence["completed_at_utc"][:-1] + "+00:00"
                if evidence["completed_at_utc"].endswith("Z")
                else evidence["completed_at_utc"]
            ).astimezone(timezone.utc)
        except (AttributeError, TypeError, ValueError) as exc:
            raise IntakeReferenceError(
                "simulator evidence completion time is not valid RFC 3339"
            ) from exc
        if completed_at > datetime.now(timezone.utc) + MAX_EVIDENCE_FUTURE_SKEW:
            raise IntakeReferenceError(
                "simulator evidence completion time exceeds the clock-skew allowance"
            )

    if require_official or intake_status in {
        "hanson_reviewed",
        "simulator_validated_for_named_versions",
    }:
        _validate_official_completeness(intake)
        unresolved = _resolution_paths(intake)
        if unresolved:
            preview = "; ".join(unresolved[:12])
            suffix = (
                ""
                if len(unresolved) <= 12
                else f"; ... {len(unresolved) - 12} more"
            )
            raise IntakeReferenceError(
                f"official confirmation incomplete ({len(unresolved)} fields): "
                f"{preview}{suffix}"
            )


def load_and_validate(
    intake_path: Path, schema_path: Path, require_official: bool = False
) -> Mapping[str, Any]:
    schema = strict_json_loads(_read_bounded_utf8(schema_path))
    intake = strict_json_loads(_read_bounded_utf8(intake_path))
    if not isinstance(schema, Mapping) or not isinstance(intake, Mapping):
        raise TypeError("schema and intake must each contain a JSON object")
    schema_validator(schema).validate(intake)
    validate_references(intake, require_official=require_official)
    return intake


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the closed official-Hanson-interface intake and its references."
        )
    )
    parser.add_argument("intake", nargs="?", type=Path, default=DEFAULT_INTAKE)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument(
        "--require-official",
        action="store_true",
        help="Also reject every unresolved or provided-unverified status.",
    )
    args = parser.parse_args()

    try:
        intake = load_and_validate(
            args.intake, args.schema, require_official=args.require_official
        )
    except (SchemaError, ValidationError):
        print("valid=false\nerror_code=schema_validation_failed")
        return 1
    except IntakeReferenceError:
        print("valid=false\nerror_code=semantic_validation_failed")
        return 1
    except (IntakeInputError, json.JSONDecodeError, RecursionError, UnicodeError):
        print("valid=false\nerror_code=invalid_or_unsafe_json")
        return 1
    except (OSError, TypeError, ValueError, KeyError, IndexError, OverflowError):
        print("valid=false\nerror_code=input_validation_failed")
        return 1

    print("valid=true")
    print(f"intake_status={intake['intake_status']}")
    print(f"official_sources={len(intake['official_sources'])}")
    print(f"packages={len(intake['packages']['entries'])}")
    print(f"interfaces={len(intake['interfaces']['entries'])}")
    print(f"frames={len(intake['frames']['entries'])}")
    print(f"units={len(intake['units']['entries'])}")
    print(f"limits={len(intake['limits']['entries'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
