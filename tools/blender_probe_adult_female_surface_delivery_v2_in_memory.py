"""Second/final bounded in-memory probe for delivery adult surface v2."""

from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import tools.blender_probe_adult_female_surface_delivery_v1_in_memory as base_probe
from tools.blender_author_adult_female_external_surface_delivery_v2 import (
    refine_existing_continuous_adult_female_surface_delivery_v2,
)


base_probe.CONFIG_PATH = Path(
    "Avatar/avatar_builder/tooling/adult_female_surface_delivery_v2_inactive_refinement.json"
)
base_probe.refine_existing_continuous_adult_female_surface_delivery_v1 = (
    refine_existing_continuous_adult_female_surface_delivery_v2
)
_original_write_report = base_probe._write_report


def _write_attempt_02_report(path: Path, payload: dict) -> None:
    row = dict(payload)
    row["probe_id"] = "adult_female_surface_delivery_v2_in_memory_probe"
    row["bounded_repair_attempt"] = 2
    row["final_bounded_attempt"] = True
    _original_write_report(path, row)


base_probe._write_report = _write_attempt_02_report


if __name__ == "__main__":
    base_probe.main()
