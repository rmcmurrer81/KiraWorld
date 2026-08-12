#!/usr/bin/env python3
"""Deterministic legacy and Blender 5.1 layered-action serializer.

This matches the proven R18/R20 read-only action-digest approach while
retaining slot handles and complete F-curve/keyframe handle data.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable


def _curve_rows(curves: Iterable[Any]) -> list[dict[str, Any]]:
    rows = []
    for curve in sorted(
        curves,
        key=lambda value: (str(value.data_path), int(value.array_index)),
    ):
        rows.append(
            {
                "data_path": str(curve.data_path),
                "array_index": int(curve.array_index),
                "extrapolation": str(getattr(curve, "extrapolation", "")),
                "keyframes": [
                    {
                        "co": [float(point.co.x), float(point.co.y)],
                        "handle_left": [
                            float(point.handle_left.x),
                            float(point.handle_left.y),
                        ],
                        "handle_right": [
                            float(point.handle_right.x),
                            float(point.handle_right.y),
                        ],
                        "handle_left_type": str(
                            getattr(point, "handle_left_type", "")
                        ),
                        "handle_right_type": str(
                            getattr(point, "handle_right_type", "")
                        ),
                        "interpolation": str(point.interpolation),
                        "easing": str(getattr(point, "easing", "")),
                    }
                    for point in curve.keyframe_points
                ],
            }
        )
    return rows


def serialize_actions(actions: Iterable[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for action in sorted(actions, key=lambda value: str(value.name)):
        action_row: dict[str, Any] = {
            "name": str(action.name),
            "frame_range": [float(value) for value in action.frame_range],
            "use_fake_user": bool(getattr(action, "use_fake_user", False)),
        }
        if hasattr(action, "fcurves"):
            action_row["storage"] = "legacy"
            action_row["fcurves"] = _curve_rows(action.fcurves)
        else:
            action_row["storage"] = "layered"
            action_row["slots"] = [
                {
                    "handle": int(slot.handle),
                    "identifier": str(slot.identifier),
                    "target_id_type": str(slot.target_id_type),
                }
                for slot in sorted(
                    getattr(action, "slots", ()),
                    key=lambda value: int(value.handle),
                )
            ]
            action_row["layers"] = []
            for layer in getattr(action, "layers", ()):
                layer_row = {"name": str(layer.name), "strips": []}
                for strip in getattr(layer, "strips", ()):
                    strip_row = {
                        "type": str(getattr(strip, "type", type(strip).__name__)),
                        "channelbags": [],
                    }
                    for channelbag in sorted(
                        getattr(strip, "channelbags", ()),
                        key=lambda value: int(value.slot_handle),
                    ):
                        strip_row["channelbags"].append(
                            {
                                "slot_handle": int(channelbag.slot_handle),
                                "fcurves": _curve_rows(
                                    getattr(channelbag, "fcurves", ())
                                ),
                            }
                        )
                    layer_row["strips"].append(strip_row)
                action_row["layers"].append(layer_row)
        rows.append(action_row)
    return rows


def action_rows_sha256(rows: list[dict[str, Any]]) -> str:
    return hashlib.sha256(
        json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def actions_sha256(actions: Iterable[Any]) -> str:
    return action_rows_sha256(serialize_actions(actions))


def action_inventory(rows: list[dict[str, Any]]) -> dict[str, Any]:
    storage_counts = {"legacy": 0, "layered": 0}
    slot_count = 0
    layer_count = 0
    strip_count = 0
    channelbag_count = 0
    fcurve_count = 0
    keyframe_count = 0
    for action in rows:
        storage = action["storage"]
        storage_counts[storage] += 1
        if storage == "legacy":
            curves = action["fcurves"]
            fcurve_count += len(curves)
            keyframe_count += sum(len(curve["keyframes"]) for curve in curves)
            continue
        slot_count += len(action["slots"])
        layer_count += len(action["layers"])
        for layer in action["layers"]:
            strip_count += len(layer["strips"])
            for strip in layer["strips"]:
                channelbag_count += len(strip["channelbags"])
                for channelbag in strip["channelbags"]:
                    curves = channelbag["fcurves"]
                    fcurve_count += len(curves)
                    keyframe_count += sum(
                        len(curve["keyframes"]) for curve in curves
                    )
    return {
        "action_count": len(rows),
        "action_names": [row["name"] for row in rows],
        "storage_counts": storage_counts,
        "slot_count": slot_count,
        "layer_count": layer_count,
        "strip_count": strip_count,
        "channelbag_count": channelbag_count,
        "fcurve_count": fcurve_count,
        "keyframe_count": keyframe_count,
        "serialized_rows_sha256": action_rows_sha256(rows),
        "actions_omitted": False,
    }

