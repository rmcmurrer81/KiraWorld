#!/usr/bin/env python3
"""Attempt 06 bootstrap: correct the Attempt 05 evidence boolean only."""

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
    "Avatar/private_owner_review/kira_r21_bald_localized_correction_attempt_06"
)
base.EVIDENCE_DIR = ROOT / (
    "RecoverySprint/continuation_20260802/kira_r21_localized_repair/author_attempt_06"
)
base.OUTPUT_BLEND = (
    base.OUTPUT_DIR / "KIRA_R21_BALD_PRIVATE_INACTIVE_PELVIS_ATTEMPT06.blend"
)


if __name__ == "__main__":
    raise SystemExit(base.main())
