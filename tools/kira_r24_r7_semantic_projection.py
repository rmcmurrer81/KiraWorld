from __future__ import annotations

"""Blender-independent canonical child-state helpers for the R24 R7 extractor."""

import math
from collections.abc import Mapping, Sequence
from typing import Any, Callable, Iterable


class ProjectionError(ValueError):
    pass


def value_record(value: Any, *, depth: int = 0) -> Any:
    if depth > 24:
        raise ProjectionError("custom-property nesting exceeds sealed limit")
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ProjectionError("non-finite custom-property value")
        return float(value)
    if hasattr(value, "bl_rna") and hasattr(value, "name"):
        return {
            "id_rna": str(value.bl_rna.identifier),
            "name": str(value.name),
            "library": str(value.library.filepath) if getattr(value, "library", None) else None,
        }
    if isinstance(value, Mapping):
        keyed = sorted(((str(key), key) for key in value.keys()), key=lambda item: item[0])
        return {name: value_record(value[key], depth=depth + 1) for name, key in keyed}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [value_record(item, depth=depth + 1) for item in value]
    try:
        return [value_record(item, depth=depth + 1) for item in value]
    except TypeError as exc:
        raise ProjectionError(f"unsupported custom-property type {type(value).__name__}") from exc


def custom_properties(value: Any) -> dict[str, Any]:
    try:
        names = sorted(str(name) for name in value.keys())
    except (AttributeError, TypeError):
        return {}
    return {name: value_record(value[name]) for name in names}


def color_ramp_record(ramp: Any) -> dict[str, Any]:
    return {
        "color_mode": str(getattr(ramp, "color_mode", "")),
        "hue_interpolation": str(getattr(ramp, "hue_interpolation", "")),
        "interpolation": str(getattr(ramp, "interpolation", "")),
        "elements": [
            {
                "position": float(element.position),
                "color": [float(item) for item in element.color],
                "custom_properties": custom_properties(element),
            }
            for element in ramp.elements
        ],
    }


def curve_mapping_record(mapping: Any) -> dict[str, Any]:
    scalar_names = (
        "black_level",
        "white_level",
        "clip_min_x",
        "clip_min_y",
        "clip_max_x",
        "clip_max_y",
        "extend",
        "tone",
        "use_clip",
    )
    return {
        "scalars": {
            name: value_record(getattr(mapping, name))
            for name in scalar_names
            if hasattr(mapping, name)
        },
        "curves": [
            {
                "points": [
                    {
                        "location": [float(item) for item in point.location],
                        "handle_type": str(getattr(point, "handle_type", "")),
                        "custom_properties": custom_properties(point),
                    }
                    for point in curve.points
                ],
                "custom_properties": custom_properties(curve),
            }
            for curve in mapping.curves
        ],
        "custom_properties": custom_properties(mapping),
    }


def node_nested_collections(node: Any) -> dict[str, Any]:
    result: dict[str, Any] = {}
    ramp = getattr(node, "color_ramp", None)
    if ramp is not None:
        result["color_ramp"] = color_ramp_record(ramp)
    mapping = getattr(node, "mapping", None)
    if mapping is not None and hasattr(mapping, "curves"):
        result["curve_mapping"] = curve_mapping_record(mapping)
    color_mapping = getattr(node, "color_mapping", None)
    if color_mapping is not None:
        nested_ramp = getattr(color_mapping, "color_ramp", None)
        if nested_ramp is not None:
            result["color_mapping_ramp"] = color_ramp_record(nested_ramp)
        result["color_mapping_custom_properties"] = custom_properties(color_mapping)
    return result


def id_target_record(value: Any) -> dict[str, Any]:
    """Return the exact stable identity used for linked Blender ID targets."""
    if value is None or not hasattr(value, "bl_rna") or not hasattr(value, "name"):
        raise ProjectionError("material target is not a Blender ID")
    return {
        "id_rna": str(value.bl_rna.identifier),
        "name": str(value.name),
        "library": (
            str(value.library.filepath)
            if getattr(value, "library", None) is not None
            else None
        ),
    }


def nla_strip_record(
    strip: Any,
    *,
    rna_serializer: Callable[..., dict[str, Any]],
    curve_serializer: Callable[[Any], dict[str, Any]],
    depth: int = 0,
    active_object_ids: frozenset[int] = frozenset(),
    maximum_depth: int = 16,
) -> dict[str, Any]:
    """Serialize an NLA strip and every META child without graph collapse.

    Blender exposes META children through ``NlaStrip.strips``.  R6 omitted
    that collection.  A path-local identity set rejects cycles while still
    allowing one ordinary strip to be referenced in distinct non-recursive
    contexts.  Children beyond the sealed maximum fail closed rather than
    being silently truncated.
    """
    identity = id(strip)
    if identity in active_object_ids:
        raise ProjectionError("cyclic NLA META child graph")
    children = tuple(getattr(strip, "strips", ()))
    if depth >= maximum_depth and children:
        raise ProjectionError("NLA META child graph exceeds sealed depth")
    next_active = active_object_ids | {identity}
    return {
        "name": str(strip.name),
        "type": str(strip.type),
        "rna": rna_serializer(
            strip,
            skip={"name", "type", "fcurves", "modifiers", "strips"},
        ),
        "custom_properties": custom_properties(strip),
        "fcurves": [
            curve_serializer(curve)
            for curve in sorted(
                getattr(strip, "fcurves", ()),
                key=lambda item: (str(item.data_path), int(item.array_index)),
            )
        ],
        "modifiers": [
            {
                "type": str(modifier.type),
                "rna": rna_serializer(modifier, skip={"type"}),
                "custom_properties": custom_properties(modifier),
            }
            for modifier in getattr(strip, "modifiers", ())
        ],
        "children": [
            nla_strip_record(
                child,
                rna_serializer=rna_serializer,
                curve_serializer=curve_serializer,
                depth=depth + 1,
                active_object_ids=next_active,
                maximum_depth=maximum_depth,
            )
            for child in children
        ],
    }


def material_slot_records(slots: Iterable[Any]) -> list[dict[str, Any]]:
    """Bind slots to type/name/library identities and reject ambiguity."""
    rows: list[dict[str, Any]] = []
    identity_owners: dict[tuple[str, str, str | None], int] = {}
    for index, slot in enumerate(slots):
        material = getattr(slot, "material", None)
        target = id_target_record(material) if material is not None else None
        if target is not None:
            key = (target["id_rna"], target["name"], target["library"])
            prior = identity_owners.get(key)
            current = id(material)
            if prior is not None and prior != current:
                raise ProjectionError(
                    "distinct material IDs collapse to one type/name/library identity"
                )
            identity_owners[key] = current
        rows.append(
            {
                "index": index,
                "name": str(slot.name),
                "link": str(slot.link),
                "material_target": target,
                "custom_properties": custom_properties(slot),
            }
        )
    return rows
