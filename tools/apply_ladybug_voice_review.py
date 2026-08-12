"""Apply Robert's reviewed Ladybug-only clip list to the local reference pack."""
from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.voice_reference_pipeline import read_json, update_pack_review


PACK_DIR = (
    PROJECT_ROOT
    / "Voice"
    / "reference_packs"
    / "ladybug"
    / "ladybug_miraculous_ladybug_s01e05_mr_pigeon_20260619_184235"
)
APPROVED_IDS = {
    "clip_0005", "clip_0008", "clip_0012", "clip_0017", "clip_0022",
    "clip_0023", "clip_0024", "clip_0025", "clip_0026", "clip_0027",
    "clip_0033", "clip_0037", "clip_0052", "clip_0056", "clip_0091",
    "clip_0105", "clip_0107", "clip_0110", "clip_0114", "clip_0145",
    "clip_0167", "clip_0170", "clip_0194", "clip_0198", "clip_0208",
    "clip_0210", "clip_0212", "clip_0216",
}


def main() -> None:
    manifest = read_json(PACK_DIR / "voice_reference_manifest.json", {})
    clips = manifest.get("audio", {}).get("clips", [])
    found = {str(clip.get("clip_id")) for clip in clips}
    missing = sorted(APPROVED_IDS - found)
    if missing:
        raise SystemExit(f"Missing clips: {', '.join(missing)}")
    for clip in clips:
        if clip.get("clip_id") in APPROVED_IDS:
            clip["review_status"] = "approved_target"
            clip["reviewer_note"] = "Robert confirmed target-only clean Ladybug speech on 2026-06-21."
    result = update_pack_review(PACK_DIR, clips)
    review = result.get("review", {})
    print(f"Approved {review.get('approved_clip_count', 0)} clips ({review.get('approved_seconds', 0)} seconds).")
    print(PACK_DIR / "approved_target_clips")


if __name__ == "__main__":
    main()
