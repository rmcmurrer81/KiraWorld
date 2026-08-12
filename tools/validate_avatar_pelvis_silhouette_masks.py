"""Audit encoded V23 pelvis silhouette masks for bounded background tunnels.

Usage:
    py tools/validate_avatar_pelvis_silhouette_masks.py DIAGNOSTIC_DIRECTORY

The front corridor is tied to the standardized V23 diagnostic camera and is a
fail-closed automatic gate.  Side and three-quarter masks are retained as
descriptive evidence, but the near thigh/hand can occlude the attachment in a
binary silhouette; those two views therefore require a geometry-ray or visual
decision and are not allowed to manufacture either a pass or a failure.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.avatar_rendered_gap_validation import audit_bounded_silhouette_gap


CORRIDORS = {
    "front": (0.465, 0.245, 0.535, 0.445),
    "side": (0.255, 0.260, 0.525, 0.625),
    "three_quarter": (0.315, 0.245, 0.585, 0.585),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    directory = Path(sys.argv[1]).resolve(strict=True)
    reports = {}
    for view, corridor in CORRIDORS.items():
        path = directory / f"silhouette_mask_pelvis_{view}.png"
        report = dict(
            audit_bounded_silhouette_gap(
                path,
                normalized_roi=corridor,
                object_threshold=128,
                allowed_run_pixels=2,
            )
        )
        report["sha256"] = sha256(path)
        reports[view] = report
    reports["front"]["automatic_gate"] = True
    for view in ("side", "three_quarter"):
        reports[view]["automatic_gate"] = False
        reports[view]["assessment_status"] = (
            "DESCRIPTIVE_ONLY__DEPTH_OCCLUSION_REQUIRES_GEOMETRY_RAY_OR_VISUAL_REVIEW"
        )
    failures = ["front"] if reports["front"]["spatial_gap_detected"] else []
    payload = {
        "schema": "kira.avatar.v23.pelvis_silhouette_audit.v1",
        "diagnostic_directory": str(directory),
        "status": (
            "FAIL_FRONT_ENCODED_SPATIAL_GAP"
            if failures
            else "PASS_FRONT_MASK__SIDE_AND_THREE_QUARTER_REVIEW_REQUIRED"
        ),
        "failed_views": failures,
        "automatic_gate_views": ["front"],
        "descriptive_only_views": ["side", "three_quarter"],
        "technical_gap_gate_complete": False,
        "views": reports,
        "rule": (
            "A bounded front-view background tunnel in an encoded silhouette "
            "mask blocks the candidate even when mesh counts pass. Side and "
            "three-quarter masks cannot decide attachment where another body "
            "surface occludes depth; geometry-ray or visual evidence remains "
            "mandatory."
        ),
        "owner_visual_review_still_required": True,
        "runtime_activation_allowed": False,
    }
    output = directory / "PELVIS_SILHOUETTE_GAP_AUDIT.json"
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(output)
    print(json.dumps(payload, indent=2))
    # Even a clean front mask is not the complete multi-view gate.  Exit 2
    # keeps callers fail-closed until side/three-quarter geometry-ray or visual
    # evidence is combined by the owning audit.
    return 1 if failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
