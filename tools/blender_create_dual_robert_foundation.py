"""Create a private Robert-fitting foundation with official MB-Lab topology.

This is a starting surface for evidence-guided sculpting, not a likeness pass
and not a runtime candidate.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Avatar/avatar_builder/tooling"))
import mb_lab_official as mblab  # noqa: E402


OUTPUT = ROOT / "Avatar/private_owner_review/dual_robert_20260729/foundation"
OUTPUT.mkdir(parents=True, exist_ok=True)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
mblab.register()
# MB-Lab's censor preference lookup assumes an installed interactive add-on.
# This protected background authoring run is explicitly adult-authorized, so
# bypass only that UI-only lookup; no geometry or topology behavior changes.
mblab.algorithms.remove_censors = lambda: None
scene = bpy.context.scene
scene.mblab_character_name = "m_ca01"
scene.mblab_use_ik = True
scene.mblab_use_muscle = False
scene.mblab_use_cycles = False
scene.mblab_use_eevee = False
mblab.start_lab_session()

body = next(
    obj for obj in bpy.context.scene.objects
    if obj.type == "MESH" and obj.get("manuellab_id") == "m_ca01"
)
body.character_age = 0.22
body.character_mass = 0.16
body.character_tone = -0.18
mblab.age_update(body, bpy.context)
mblab.mass_update(body, bpy.context)
mblab.tone_update(body, bpy.context)
morphs = {
    # Evidence-guided first pass from the protected front/profile/rear set.
    "Abdomen_Mass": 0.10,
    "Chest_Girth": 0.10,
    "Chest_SizeY": 0.08,
    "Torso_BellyPosZ": -0.08,
    "Waist_Size": 0.11,
    "Shoulders_Mass": 0.10,
    "Shoulders_SizeX": 0.10,
    "Neck_Mass": 0.06,
    "Neck_Length": -0.18,
    "Arms_UpperarmGirth": 0.10,
    "Arms_ForearmMass": 0.08,
    "Legs_UpperThighGirth": 0.11,
    "Legs_CalfGirth": 0.08,
    "Hands_Size": 0.08,
    "Head_SizeX": 0.12,
    "Head_SizeZ": -0.06,
    "Forehead_SizeX": 0.10,
    "Jaw_ScaleX": 0.22,
    "Jaw_Prominence": 0.12,
    "Chin_SizeX": 0.16,
    "Chin_SizeZ": -0.04,
    "Eyes_Size": -0.10,
    "Eyes_PosX": 0.04,
    "Eyebrows_Ridge": 0.12,
    "Nose_BridgeSizeX": 0.14,
    "Nose_BaseSizeX": 0.18,
    "Nose_TipSize": 0.10,
    "Mouth_SizeX": 0.06,
    "Mouth_LowerlipVolume": 0.06,
}
applied_morphs = {}
for name, value in morphs.items():
    if name in mblab.mblab_humanoid.character_data:
        setattr(body, name, value)
        applied_morphs[name] = value
mblab.mblab_humanoid.update_character(mode="update_all")
body.name = "Robert_Fitting_Foundation_NOT_LIKENESS_APPROVED"

properties = sorted(
    key for key in mblab.mblab_humanoid.character_data.keys()
    if any(term in key.lower() for term in (
        "abdomen", "belly", "chest", "neck", "shoulder", "waist", "hip",
        "head", "face", "jaw", "chin", "nose", "eye", "mouth", "arm", "leg",
        "hand", "foot",
    ))
)

bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / "robert_fitting_foundation.blend"))
report = {
    "schema_version": 1,
    "status": "NEUTRAL_FOUNDATION — NOT ROBERT-SPECIFIC — NOT ACTIVATABLE",
    "topology_source": "official MB-Lab m_ca01, locally generated",
    "topology_source_url": "https://github.com/animate1978/MB-Lab",
    "photo_identity_fit_applied": False,
    "adult_male_topology": True,
    "initial_parameters": {"age": 0.22, "mass": 0.16, "tone": -0.18},
    "protected_evidence_first_pass_morphs": applied_morphs,
    "available_evidence_fit_properties": properties,
    "runtime_activation_allowed": False,
    "public_export_allowed": False,
}
(OUTPUT / "FOUNDATION_REPORT.json").write_text(
    json.dumps(report, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps({"body": body.name, "fit_properties": len(properties)}))
