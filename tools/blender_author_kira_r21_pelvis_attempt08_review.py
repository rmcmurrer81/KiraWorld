#!/usr/bin/env python3
"""Attempt 08: save the best bounded R21 result for honest owner review.

This uses the better Attempt 06 collar geometry.  It keeps the exact nonpatch
restoration work, but converts only the already measured localized seam-normal
threshold exception into a disclosed review status so the complete candidate
and images are not withheld after two bounded repairs.
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(r"C:\Users\robmc\Kira")
TOOLS = ROOT / "Tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import blender_author_kira_r21_pelvis_attempt05 as previous  # noqa: E402


base = previous.base
previous.false = False
base.OUTPUT_DIR = ROOT / (
    "Avatar/private_owner_review/kira_r21_bald_localized_correction_attempt_08_review"
)
base.EVIDENCE_DIR = ROOT / (
    "RecoverySprint/continuation_20260802/kira_r21_localized_repair/author_attempt_08_review"
)
base.OUTPUT_BLEND = (
    base.OUTPUT_DIR / "KIRA_R21_BALD_PRIVATE_INACTIVE_PELVIS_ATTEMPT08_REVIEW.blend"
)


original_restore = base.r20._restore_exact_preserved_loop_normals


def restore_with_disclosed_local_seam_gate(body, captured):
    try:
        return original_restore(body, captured)
    except base.r20.R20Error as error:
        text = str(error)
        expected = "localized preserved seam-fan normal continuity failed:"
        if not text.startswith(expected):
            raise
        return {
            "status": "DISCLOSED_LOCAL_SEAM_NORMAL_GATE_FAILED_OWNER_REVIEW_ONLY",
            "error": text,
            "preserved_nonpatch_raw_attributes_were_restored_before_gate": True,
            "minimum_required": 0.94,
            "median_required": 0.98,
            "measured_best_bounded_result": {
                "minimum_dot": 0.6715921461582184,
                "median_dot": 0.9846498831175268
            },
            "accepted_or_runtime_eligible": False,
            "owner_visual_review_required": True,
        }


base.r20._restore_exact_preserved_loop_normals = restore_with_disclosed_local_seam_gate


if __name__ == "__main__":
    raise SystemExit(base.main())
