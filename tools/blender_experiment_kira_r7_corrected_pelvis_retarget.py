#!/usr/bin/env python3
"""Run the prior inactive diagnostic with the source's real pelvis landmark."""

from __future__ import annotations

import importlib.util
from pathlib import Path


source = Path(__file__).with_name("blender_inspect_kira_r7_adult_retarget_gate.py")
spec = importlib.util.spec_from_file_location("kira_r7_prior_gate", source)
if spec is None or spec.loader is None:
    raise RuntimeError(f"unable to load {source}")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


_original_world_bone_head = gate.world_bone_head


def corrected_world_bone_head(armature, name):
    # The CC BY rig's `hip_03` is the root at world zero.  The anatomical
    # pelvis is `pelvis_04`; the old scale/correction diagnostic confused them.
    if len(armature.data.bones) == 188 and name == "hip_03":
        name = "pelvis_04"
    return _original_world_bone_head(armature, name)


gate.world_bone_head = corrected_world_bone_head
raise SystemExit(gate.main())
