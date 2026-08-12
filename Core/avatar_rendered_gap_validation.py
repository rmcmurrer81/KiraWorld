"""Measure real background tunnels in static-avatar silhouette renders.

Topology counts cannot distinguish a closed but folded surface from a visually
open tunnel.  This module consumes a binary diagnostic render: object coverage
is light and background is dark.  It then measures background runs that are
bounded by rendered surface above and below inside a caller-supplied anatomical
review corridor.

The corridor is intentionally supplied by the body-specific build/audit layer.
This module never guesses likeness or exact anatomy from a generic template.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

from PIL import Image


def _pixel_bounds(
    size: tuple[int, int],
    normalized_roi: Sequence[float],
) -> tuple[int, int, int, int]:
    if len(normalized_roi) != 4:
        raise ValueError("normalized_roi must contain left, top, right, bottom")
    left, top, right, bottom = (float(value) for value in normalized_roi)
    if not (0.0 <= left < right <= 1.0 and 0.0 <= top < bottom <= 1.0):
        raise ValueError("normalized_roi must be ordered and stay inside 0..1")
    width, height = size
    return (
        max(0, min(width - 1, round(left * (width - 1)))),
        max(0, min(height - 1, round(top * (height - 1)))),
        max(1, min(width, round(right * width))),
        max(1, min(height, round(bottom * height))),
    )


def audit_bounded_silhouette_gap(
    image_path: str | Path,
    *,
    normalized_roi: Sequence[float],
    object_threshold: int = 128,
    allowed_run_pixels: int = 2,
) -> Mapping[str, object]:
    """Return encoded-image evidence for a bounded surface/background gap.

    A run counts only when object pixels occur both above and below it in the
    same image column.  Background outside the body silhouette is therefore not
    mislabeled as a hole.  Any run longer than ``allowed_run_pixels`` blocks the
    spatial-coverage gate.
    """

    path = Path(image_path).resolve(strict=True)
    image = Image.open(path).convert("L")
    left, top, right, bottom = _pixel_bounds(image.size, normalized_roi)
    pixels = image.load()
    bounded_runs: list[dict[str, int]] = []
    columns_with_object = 0

    for x in range(left, right):
        object_rows = [
            y for y in range(top, bottom) if pixels[x, y] >= object_threshold
        ]
        if len(object_rows) < 2:
            continue
        columns_with_object += 1
        first = min(object_rows)
        last = max(object_rows)
        run_start: int | None = None
        for y in range(first, last + 1):
            is_background = pixels[x, y] < object_threshold
            if is_background and run_start is None:
                run_start = y
            elif not is_background and run_start is not None:
                bounded_runs.append(
                    {
                        "x": x,
                        "start_y": run_start,
                        "end_y": y - 1,
                        "length_pixels": y - run_start,
                    }
                )
                run_start = None
        if run_start is not None:
            # This cannot be bounded below because ``last`` is an object pixel,
            # but retain the guard in case threshold behavior changes.
            length = last - run_start
            if length > 0:
                bounded_runs.append(
                    {
                        "x": x,
                        "start_y": run_start,
                        "end_y": last - 1,
                        "length_pixels": length,
                    }
                )

    failing_runs = [
        run
        for run in bounded_runs
        if run["length_pixels"] > int(allowed_run_pixels)
    ]
    maximum = max(
        (run["length_pixels"] for run in bounded_runs),
        default=0,
    )
    return {
        "schema": "kira.avatar.rendered_silhouette_gap.v1",
        "image_path": str(path),
        "image_size": list(image.size),
        "normalized_roi": [float(value) for value in normalized_roi],
        "pixel_roi": [left, top, right, bottom],
        "object_threshold": int(object_threshold),
        "allowed_run_pixels": int(allowed_run_pixels),
        "columns_with_object_above_and_below": columns_with_object,
        "bounded_background_run_count": len(bounded_runs),
        "failing_background_run_count": len(failing_runs),
        "maximum_bounded_background_run_pixels": maximum,
        "representative_failing_runs": failing_runs[:20],
        "spatial_gap_detected": bool(failing_runs),
        "status": (
            "FAILED_VISIBLE_SPATIAL_GAP"
            if failing_runs
            else "PASS_NO_BOUNDED_BACKGROUND_GAP_IN_CORRIDOR"
        ),
        "owner_visual_review_still_required": True,
    }

