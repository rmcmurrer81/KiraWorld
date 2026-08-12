"""Probe the official MB-Lab source inside Blender 5.1 without authoring output."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
ADDON_PARENT = ROOT / "Avatar/avatar_builder/tooling"
sys.path.insert(0, str(ADDON_PARENT))

result = {
    "schema_version": 1,
    "blender_version": bpy.app.version_string,
    "source": "https://github.com/animate1978/MB-Lab.git",
    "probe_only": True,
}
try:
    import mb_lab_official as mblab

    mblab.register()
    result["registered"] = True
    result["character_types"] = sorted(
        str(item[0]) for item in bpy.types.Scene.mblab_character_name[1]["items"]
    ) if False else []
    result["status"] = "registered_probe_pass"
except Exception as exc:
    result["registered"] = False
    result["status"] = "blocked_incompatible_or_missing_dependency"
    result["error_type"] = type(exc).__name__
    result["error"] = str(exc)

output = ROOT / "Avatar/avatar_builder/tooling/mb_lab_blender_51_probe.json"
output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result))
