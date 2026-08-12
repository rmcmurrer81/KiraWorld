"""
Create a first avatar build brief for a TemporaryAI candidate.

The brief summarizes approved/downloaded references and policy. It does not
generate a 3D model.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AVATAR_ROOT = PROJECT_ROOT / "Avatar" / "temp_ai"
TEMP_ROOT = PROJECT_ROOT / "TemporaryAI" / "candidates"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def list_refs(folder: Path) -> list[str]:
    if not folder.exists():
        return []
    return [
        rel(path)
        for path in sorted(folder.rglob("*"))
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}
    ]


def reviewable_candidates(queue: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = queue.get("reference_candidates", queue.get("downloaded_items", []))
    if not isinstance(candidates, list):
        return []
    rejected_statuses = {"rejected", "rejected_unrelated", "skip", "skipped"}
    return [
        item
        for item in candidates
        if isinstance(item, dict) and str(item.get("status", "")).lower() not in rejected_statuses
    ]


def create_brief(candidate_id: str) -> dict[str, Any]:
    avatar_base = AVATAR_ROOT / candidate_id
    candidate_base = TEMP_ROOT / candidate_id
    avatar_profile_path = avatar_base / "avatar_profile.json"
    request_path = candidate_base / "creation_request.json"
    if not avatar_profile_path.exists() or not request_path.exists():
        raise FileNotFoundError(f"Missing candidate/avatar files for {candidate_id}")
    avatar_profile = read_json(avatar_profile_path)
    request = read_json(request_path)
    queue_path = avatar_base / "online_reference_queue.json"
    queue = read_json(queue_path) if queue_path.exists() else {}
    approved = list_refs(avatar_base / "references" / "approved")
    downloaded = list_refs(avatar_base / "references" / "downloaded")
    queued_count = len(reviewable_candidates(queue))
    brief = {
        "brief_id": f"{candidate_id}_avatar_build_brief_v1",
        "created_at": now_iso(),
        "candidate_id": candidate_id,
        "display_name": request.get("display_name_or_role", candidate_id),
        "ai_type": request.get("ai_type", ""),
        "build_mode": avatar_profile.get("build_mode", ""),
        "status": "ready_for_visual_concept" if approved else "ready_for_reference_review" if downloaded or queued_count else "needs_references",
        "references": {
            "approved": approved,
            "downloaded_needs_review": downloaded,
            "online_candidates_need_review_count": queued_count,
        },
        "visual_profile": avatar_profile.get("visual_profile", {}),
        "policy": avatar_profile.get("policy", {}),
        "next_steps": [
            "Review downloaded references and move good ones to references/approved.",
            "Write face/hair/body/wardrobe notes in avatar_profile.json.",
            "Use approved references only for the first visual concept.",
            "Do not claim a rendered avatar exists until one is generated and reviewed.",
        ],
    }
    out_json = avatar_base / "outputs" / f"{candidate_id}_avatar_build_brief_v1.json"
    out_md = avatar_base / "outputs" / f"{candidate_id}_avatar_build_brief_v1.md"
    write_json(out_json, brief)
    write_text(
        out_md,
        "\n".join(
            [
                f"# {brief['display_name']} Avatar Build Brief",
                "",
                f"- candidate_id: {candidate_id}",
                f"- ai_type: {brief['ai_type']}",
                f"- build_mode: {brief['build_mode']}",
                f"- status: {brief['status']}",
                "",
                "## References",
                "",
                f"- approved: {len(approved)}",
                f"- downloaded_needs_review: {len(downloaded)}",
                f"- online_candidates_need_review: {queued_count}",
                "",
                "## Next Steps",
                "",
                *[f"- {step}" for step in brief["next_steps"]],
            ]
        ),
    )
    return {"json": rel(out_json), "markdown": rel(out_md), "status": brief["status"]}


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a TemporaryAI avatar build brief.")
    parser.add_argument("candidate_id")
    args = parser.parse_args()
    print(json.dumps(create_brief(args.candidate_id), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
