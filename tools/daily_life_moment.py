"""
Create one lightweight daily-life moment for Kira/Lisa.

This gives continuity without background model runtime: choose an activity,
write a daily-life log, and create a small public moment record.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Core"))

from daily_life_manager import DailyLifeManager  # noqa: E402


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "Data" / "daily_life" / "moments"
VALID_ENTITIES = {"kira", "lisa"}


def _relative(path: Path, base: Path = PROJECT_ROOT) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def create_moment(
    entity_id: str,
    reason: str = "sixteen_gb_daily_life_step",
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    manager: DailyLifeManager | None = None,
) -> dict[str, Any]:
    manager = manager or DailyLifeManager()
    applied = manager.choose_and_apply_activity(entity_id)
    log = manager.write_log(entity_id, notes=f"daily_life_moment reason={reason}")
    now = datetime.now(timezone.utc)
    moment = {
        "moment_id": f"daily_moment_{entity_id}_{now.strftime('%Y%m%d_%H%M%S')}",
        "entity_id": entity_id,
        "created_at": now.isoformat(),
        "reason": reason,
        "public_summary": applied["state"]["current_activity"]["public_summary"],
        "activity_type": applied["state"]["current_activity"]["activity_type"],
        "mood": applied["state"]["mood_state"]["primary_mood"],
        "privacy_level": applied["state"]["privacy_state"]["level"],
        "source_path": applied["state"]["current_activity"].get("source_path", ""),
        "choice": applied["choice"],
        "daily_life_log_id": log["log_id"],
        "memory_policy": {
            "does_not_promote_memory_automatically": True,
            "may_become_memory_candidate_if_meaningful": True,
            "private_details_not_exposed": True,
        },
        "resource_use": {
            "pre_gpu_safe": True,
            "used_heavy_model": False,
            "used_video_understanding": False,
            "used_microphone": False,
            "used_webcam": False,
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{moment['moment_id']}.json"
    path.write_text(json.dumps(moment, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    moment["path"] = _relative(path)
    return moment


def main() -> None:
    parser = argparse.ArgumentParser(description="Create lightweight daily-life moments.")
    parser.add_argument("--entity", choices=["kira", "lisa", "both"], default="both")
    parser.add_argument("--reason", default="sixteen_gb_daily_life_step")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    entities = sorted(VALID_ENTITIES) if args.entity == "both" else [args.entity]
    moments = [create_moment(entity, args.reason, output_dir) for entity in entities]
    print(json.dumps(moments, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
