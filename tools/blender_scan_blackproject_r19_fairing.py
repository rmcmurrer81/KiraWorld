#!/usr/bin/env python3
"""Read-only bounded parameter scan for the R19 central-patch fairing."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bmesh
import bpy


TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import blender_author_kira_r7_adult_surface_trial as helpers  # noqa: E402
from blender_build_kira_temporary_functional_body_blackproject import ordered_boundary_cycles  # noqa: E402
from blender_exact_mesh_intersections import exact_nonadjacent_intersection_report  # noqa: E402
from blender_probe_blackproject_r19_patch_reconstruction import fair_central_patch  # noqa: E402


SOURCE_SHA256 = "26e107ea57c92a0905283d3655cf4e1155e16c2c0c24b0b071a66cccddf567df"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    config = json.loads(Path(args.config).resolve(strict=True).read_text(encoding="utf-8"))
    root = Path(config["project_root"]).resolve(strict=True)
    source = (root / config["source_path"]).resolve(strict=True)
    output = (root / config["output_path"]).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(output)
    if sha256_file(source) != SOURCE_SHA256:
        raise ValueError("source hash mismatch")

    helpers.clear_scene()
    imported = helpers.import_glb(source)
    adult = next(
        obj for obj in imported if obj.type == "MESH" and obj.data.name == "Ariel_Mesh_Genitalia_0"
    )
    cycles = ordered_boundary_cycles(adult)
    if len(cycles) != 1 or len(cycles[0]) != 34:
        raise ValueError("unexpected source boundary")
    boundary = set(cycles[0])
    original_mesh = adult.data.copy()
    records: list[dict[str, object]] = []
    for candidate in config["candidates"]:
        prior = adult.data
        adult.data = original_mesh.copy()
        if prior != original_mesh and prior.users == 0:
            bpy.data.meshes.remove(prior)
        fairing = fair_central_patch(
            adult,
            boundary,
            iterations=int(candidate["iterations"]),
            strength=float(candidate["strength"]),
        )
        bm = bmesh.new()
        bm.from_mesh(adult.data)
        exact = exact_nonadjacent_intersection_report(bm, include_pair_details=False)
        bm.free()
        records.append(
            {
                "label": candidate["label"],
                "iterations": int(candidate["iterations"]),
                "strength": float(candidate["strength"]),
                "selected_vertex_count": fairing["selected_vertex_count"],
                "maximum_total_movement_world_m": fairing["maximum_total_movement_world_m"],
                "exact_genuine_penetration_pair_count": exact["exact_genuine_penetration_pair_count"],
                "bvh_candidate_pair_count": exact["bvh_nonadjacent_candidate_pair_count"],
            }
        )
    result = {
        "schema_version": 1,
        "mode": "READ_ONLY_R19_FAIRING_PARAMETER_SCAN",
        "source_sha256": SOURCE_SHA256,
        "source_unchanged": sha256_file(source) == SOURCE_SHA256,
        "candidate_or_blend_saved": False,
        "records": records,
    }
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
