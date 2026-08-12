#!/usr/bin/env python3
"""Reproduce the inactive Kira R7 existing-mouth topology limit proof."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = (
    PROJECT_ROOT
    / "Avatar/avatar_builder/candidate_sources/kira_adult_body_r7/workspace_v1"
    / "kira_r7_authoring_workspace.blend"
)
SOURCE_R6 = (
    PROJECT_ROOT
    / "Avatar/avatar_builder/candidate_sources/kira_provisional_body_r6"
    / "r6_20260718_163658/kira_provisional_body_r6.glb"
)
WORKER = PROJECT_ROOT / "tools/blender_probe_kira_r7_mouth_topology.py"
DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT
    / "Data/avatar_builder_workspace_tests"
    / "kira_r7_existing_mouth_authoring_limit_20260721"
)
EXPECTED = {
    "workspace": "9d0f9dad39b2e0650419ccef48a7d524d5cd67e4429f1d23ee3398db396c0394",
    "source_r6": "ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_blender(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).resolve(strict=True)
    candidates = sorted(
        Path("C:/Program Files/Blender Foundation").glob("Blender */blender.exe"),
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError("Blender executable was not found")
    return candidates[0].resolve(strict=True)


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    name = "segoeuib.ttf" if bold else "segoeui.ttf"
    path = Path("C:/Windows/Fonts") / name
    if path.exists():
        return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def draw_topology_panel(
    draw: ImageDraw.ImageDraw,
    evidence: dict[str, object],
    box: tuple[int, int, int, int],
    *,
    vertical_scale: float,
    title: str,
) -> None:
    left, top, right, bottom = box
    draw.rounded_rectangle(box, radius=24, fill="#111c2b", outline="#32506e", width=3)
    draw.text((left + 28, top + 22), title, font=font(28, bold=True), fill="#f4f7fb")
    projection = evidence["diagnostic_projection"]
    vertices = {
        int(index): (float(point[0]), float(point[1]) * vertical_scale)
        for index, point in projection["vertices"].items()
    }
    xs = [point[0] for point in vertices.values()]
    zs = [point[1] for point in vertices.values()]
    pad_x, pad_top, pad_bottom = 45, 85, 45
    width = right - left - 2 * pad_x
    height = bottom - top - pad_top - pad_bottom
    scale = min(
        width / max(max(xs) - min(xs), 1e-8),
        height / max(max(zs) - min(zs), 1e-8),
    )
    center_x = (min(xs) + max(xs)) * 0.5
    center_z = (min(zs) + max(zs)) * 0.5
    screen_center = ((left + right) * 0.5, top + pad_top + height * 0.5)

    def point(index: int) -> tuple[float, float]:
        x, z = vertices[index]
        return (
            screen_center[0] + (x - center_x) * scale,
            screen_center[1] - (z - center_z) * scale,
        )

    boundary = {tuple(sorted(edge)) for edge in projection["boundary_edges"]}
    for raw_edge in projection["edges"]:
        edge = tuple(sorted((int(raw_edge[0]), int(raw_edge[1]))))
        draw.line(
            (point(edge[0]), point(edge[1])),
            fill="#ff6b6b" if edge in boundary else "#7ba7ce",
            width=4 if edge in boundary else 2,
        )
    for index in vertices:
        x, y = point(index)
        radius = 3 if any(index in edge for edge in boundary) else 2
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill="#e8eef5")


def render_diagram(evidence: dict[str, object], output: Path) -> None:
    image = Image.new("RGB", (1800, 1220), "#08111e")
    draw = ImageDraw.Draw(image)
    draw.text((70, 46), "Kira R7 existing single-mouth topology", font=font(48, bold=True), fill="#ffffff")
    draw.text(
        (70, 112),
        "Exact 207-vertex island  |  red = boundary  |  blue = internal topology",
        font=font(25),
        fill="#a9bfd3",
    )
    draw_topology_panel(draw, evidence, (65, 175, 875, 735), vertical_scale=1.0, title="True X/Z proportions")
    draw_topology_panel(draw, evidence, (925, 175, 1735, 735), vertical_scale=4.0, title="Vertical x4 diagnostic view")
    result = evidence["existing_mouth"]
    facts = [
        f"Vertices: {result['vertex_count']}    Polygons: {result['polygon_count']}",
        (
            f"Boundary loops: {result['boundary_loop_count']}    "
            f"Boundary degree: {result['boundary_vertex_degree_histogram']}"
        ),
        "Oral fissure / commissure / attachment edge roles: UNLABELED",
        "Result: a symmetry or shortest-path seam would be a guess, so authoring stopped.",
    ]
    y = 785
    for ordinal, line in enumerate(facts):
        color = "#ffbf69" if ordinal >= 2 else "#dbe7f2"
        draw.text((85, y), line, font=font(29, bold=ordinal >= 2), fill=color)
        y += 50
    note = (
        "Next reviewed Blender operation: mark Kira's upper and lower fissure edges, both "
        "commissures, the attachment rim, and every open symmetry segment on the isolated "
        "R7 copy. Only after that reviewed selection may the same existing mouth receive an "
        "internal cavity and viseme controls. No exterior replacement or overlay."
    )
    draw.rounded_rectangle((65, 985, 1735, 1170), radius=20, fill="#1d2a39", outline="#ffbf69", width=2)
    draw.multiline_text(
        (90, 1004),
        "\n".join(textwrap.wrap(note, width=105)),
        font=font(24),
        fill="#f4f7fb",
        spacing=8,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blender")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    blender = find_blender(args.blender)
    output_dir = Path(args.output_dir).resolve()
    evidence_path = output_dir / "topology_probe.json"
    diagram_path = output_dir / "existing_single_mouth_topology_limit.png"
    manifest_path = output_dir / "manifest.json"
    pinned = {"workspace": WORKSPACE, "source_r6": SOURCE_R6}
    before = {name: sha256_file(path) for name, path in pinned.items()}
    if before != EXPECTED:
        raise ValueError(f"pinned inputs changed: expected={EXPECTED} actual={before}")
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        str(blender),
        "--background",
        str(WORKSPACE),
        "--python",
        str(WORKER),
        "--",
        "--output",
        str(evidence_path),
    ]
    completed = subprocess.run(command, cwd=PROJECT_ROOT, text=True, capture_output=True)
    if completed.returncode:
        raise RuntimeError(
            f"Blender probe failed ({completed.returncode})\n"
            f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )
    after = {name: sha256_file(path) for name, path in pinned.items()}
    if after != before:
        raise RuntimeError(f"probe changed a pinned input: before={before} after={after}")
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence["host_verification"] = {
        "blender_path": str(blender),
        "blender_sha256": sha256_file(blender),
        "pinned_hashes_before": before,
        "pinned_hashes_after": after,
        "all_pinned_inputs_byte_unchanged": before == after,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    render_diagram(evidence, diagram_path)
    manifest = {
        "schema_version": 1,
        "proof_id": "kira_r7_existing_mouth_authoring_limit_20260721",
        "status": "inactive_manual_semantic_selection_required",
        "artifacts": {
            "evidence": str(evidence_path),
            "diagram": str(diagram_path),
            "diagram_sha256": sha256_file(diagram_path),
        },
        "result": {
            "existing_single_mouth_preserved": True,
            "second_mouth_or_overlay_created": False,
            "mouth_interior_created": False,
            "viseme_or_jaw_controls_created": False,
            "deterministic_shortest_path_rejected": True,
            "reason": evidence["existing_mouth"]["exact_blocker"],
            "required_manual_selection": [
                "upper oral-fissure edge path",
                "lower oral-fissure edge path",
                "left and right commissure vertices",
                "outer attachment-rim edges",
                "open center/symmetry-seam edges and any duplicate center vertices",
            ],
        },
        "gates": {
            "candidate_export_allowed": False,
            "runtime_binding_allowed": False,
            "activation_allowed": False,
            "owner_approved": False,
        },
        "pinned_inputs_byte_unchanged": True,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "manifest": str(manifest_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
