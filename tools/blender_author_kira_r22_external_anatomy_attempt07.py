#!/usr/bin/env python3
"""Attempt 07: mechanical helper-binding repair for Attempt 06.

The one-piece external-field design is unchanged from the preserved failed
Attempt 06.  This append-only successor captures the exact Attempt 04 v2
relaxation helper before replacing the shared runner hook, then writes only a
new Attempt 07 candidate/evidence pair.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

from mathutils import Vector


ROOT = Path(r"C:\Users\robmc\Kira")
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import blender_author_kira_r22_external_anatomy_attempt04 as attempt04  # noqa: E402
import blender_author_kira_r22_external_anatomy_attempt06 as prior  # noqa: E402


base = prior.base
run_attempt = prior.run_attempt
relax_v2 = attempt04.relax_rejected_center_v2


def relax_and_recess_center_fixed(body: Any, topology: dict[str, Any]) -> dict[str, Any]:
    relaxation = relax_v2(body, topology)
    mesh = body.data
    before_recess = {
        index: mesh.vertices[index].co.copy() for index in topology["vertices"]
    }
    moved: set[int] = set()
    maximum_world_recess = 0.0
    inverse = body.matrix_world.inverted()
    for index in topology["vertices"]:
        if int(topology["distance"].get(index, 0)) <= 2:
            continue
        world = body.matrix_world @ mesh.vertices[index].co
        x_weight = prior.smoothstep((0.038 - abs(world.x)) / 0.018)
        z_weight = prior.smoothstep((world.z - 0.842) / 0.012) * prior.smoothstep(
            (0.898 - world.z) / 0.014
        )
        front_weight = prior.smoothstep((0.075 - world.y) / 0.050)
        weight = x_weight * z_weight * front_weight
        if weight <= 1.0e-8:
            continue
        recess = 0.00135 * weight
        mesh.vertices[index].co = inverse @ (world + Vector((0.0, recess, 0.0)))
        moved.add(index)
        maximum_world_recess = max(maximum_world_recess, recess)
    mesh.update()
    seam_delta = max(
        (
            (mesh.vertices[index].co - before_recess[index]).length
            for index in topology["seam"]
        ),
        default=0.0,
    )
    return {
        "method": "attempt07_exact_attempt04_relaxation_plus_attempt06_interior_recess",
        "relaxation": relaxation,
        "recessed_vertex_count": len(moved),
        "maximum_world_recess": float(maximum_world_recess),
        "seam_maximum_delta": float(seam_delta),
        "mechanical_repair": (
            "captured blender_author_kira_r22_external_anatomy_attempt04."
            "relax_rejected_center_v2 before shared-hook override"
        ),
    }


base.relax_rejected_center = relax_and_recess_center_fixed
base.create_module = prior.create_module_one_piece


if __name__ == "__main__":
    output_dir = ROOT / "Avatar/private_owner_review/kira_r22_external_anatomy_attempt_07"
    evidence_dir = ROOT / (
        "RecoverySprint/continuation_20260802/kira_r22_external_anatomy/attempt_07"
    )
    output_blend = output_dir / (
        "KIRA_R22_BALD_PRIVATE_INACTIVE_EXTERNAL_ANATOMY_ATTEMPT07.blend"
    )
    raise SystemExit(
        run_attempt(
            base,
            root=ROOT,
            attempt_number=7,
            output_dir=output_dir,
            evidence_dir=evidence_dir,
            output_blend=output_blend,
            prior_attempt_truth={
                "attempt_04": "aligned but still visually protruding and diagram-like",
                "attempt_05": "smaller components still read as a narrow vertical stack",
                "attempt_06": "failed before mutation/render because its helper lookup was one module level too shallow",
            },
            repair_summary=(
                "mechanically bind the preserved relaxation helper correctly and execute the "
                "unchanged one-piece shallow body-integrated surface-field design"
            ),
        )
    )

