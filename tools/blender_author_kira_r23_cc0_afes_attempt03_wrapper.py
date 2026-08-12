#!/usr/bin/env python3
"""Blender-side wrapper for the bounded R23 Author execution Attempt 03.

The sealed author worker/config/core are unchanged. This wrapper binds the
existing shared edge-face helper and isolates append-only output from the
preserved Attempt02 failure directory, then delegates to the sealed main.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import blender_author_kira_r23_cc0_afes_attempt01 as sealed_worker  # noqa: E402
from tools.kira_r23_cc0_afes_preflight_core import edge_face_map  # noqa: E402


CONFIGURED_OUTPUT = (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author/attempt_01"
)
EFFECTIVE_ATTEMPT03_OUTPUT = (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author/attempt_03"
)


def attempt03_output_paths(config: Mapping[str, Any]) -> dict[str, Path]:
    configured = str(config["output"]["directory"])
    if configured != CONFIGURED_OUTPUT:
        raise sealed_worker.R23AuthorError(
            f"sealed configured output drifted: {configured}"
        )
    effective = deepcopy(config)
    effective["output"]["directory"] = EFFECTIVE_ATTEMPT03_OUTPUT
    return ORIGINAL_OUTPUT_PATHS(effective)


ORIGINAL_OUTPUT_PATHS = sealed_worker.output_paths


def bind_attempt03_runtime() -> None:
    """Patch exactly one missing helper and one append-only output route."""

    sealed_worker.preflight_base.edge_face_map = edge_face_map
    sealed_worker.output_paths = attempt03_output_paths


def main() -> int:
    bind_attempt03_runtime()
    return int(sealed_worker.main())


if __name__ == "__main__":
    raise SystemExit(main())
