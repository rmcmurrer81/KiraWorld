#!/usr/bin/env python3
"""Bind anatomical-axis metadata to a diagnostic copy of an existing GLB.

This utility never overwrites its input and never creates an Avatar Builder
candidate. It exists only to regression-test the independent knee-direction
auditor against already encoded actions. Adding truthful skeleton bindings to
a copy must not make a forward, lateral, or hyperextended knee pass.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy  # type: ignore


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--forward-axis", default="-Y")
    return parser.parse_args(argv)


def main() -> int:
    args = arguments()
    source = Path(args.input).resolve(strict=True)
    output = Path(args.output).resolve()
    if source == output:
        raise SystemExit("diagnostic output must differ from input")
    output.parent.mkdir(parents=True, exist_ok=True)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(source))
    bpy.context.view_layer.update()
    marked = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH"
        and obj.get("rapid_body_primary_surface") is True
    ]
    if len(marked) != 1:
        raise SystemExit(
            "exactly one rapid_body_primary_surface marker is required"
        )
    body = marked[0]
    body["anatomical_forward_axis"] = args.forward_axis
    for side, suffix in (("left", "L"), ("right", "R")):
        body[f"{side}_knee_upper_bone"] = f"upperleg02.{suffix}"
        body[f"{side}_knee_lower_bone"] = f"lowerleg01.{suffix}"
        body[f"{side}_ankle_bone"] = f"lowerleg02.{suffix}"
    body["diagnostic_fixture_only"] = True
    body["runtime_assignment_allowed"] = False
    body["owner_review_candidate"] = False

    bpy.ops.export_scene.gltf(
        filepath=str(output),
        export_format="GLB",
        export_extras=True,
        export_animations=True,
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
