"""Attach a video reference to a TemporaryAI candidate.

This creates a reviewable online video-reference package under a candidate
workbench. It is meant for character/style/avatar grounding: source URL,
metadata, thumbnail/reference image, speech-style notes, and visual notes. This
online metadata lane does not download full videos or audio. It is not a global
ban: already-local authorized media uses ``Core.temp_ai_local_media_intake`` for
explicit short ranges and human identity/quality review.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_ROOT = PROJECT_ROOT / "TemporaryAI" / "candidates"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def slug(value: str, limit: int = 70) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")[:limit] or "video_reference"


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def candidate_display(candidate_dir: Path) -> str:
    profile = read_json(candidate_dir / "temporary_ai_profile.json", {})
    return str(profile.get("display_name") or profile.get("role_title") or candidate_dir.name)


def find_candidate(identifier: str) -> Path:
    value = identifier.strip()
    if not value:
        raise ValueError("Candidate id/search text is required.")
    direct = CANDIDATE_ROOT / value
    if direct.exists():
        return direct
    value_lower = value.lower()
    matches = [
        path
        for path in CANDIDATE_ROOT.iterdir()
        if path.is_dir() and value_lower in path.name.lower()
    ]
    if len(matches) == 1:
        return matches[0]
    if matches:
        matches = sorted(matches, key=lambda path: path.stat().st_mtime, reverse=True)
        return matches[0]
    raise FileNotFoundError(f"No TemporaryAI candidate matched: {identifier}")


def recent_candidates(limit: int = 20) -> list[Path]:
    if not CANDIDATE_ROOT.exists():
        return []
    candidates = [path for path in CANDIDATE_ROOT.iterdir() if path.is_dir()]
    return sorted(candidates, key=lambda path: path.stat().st_mtime, reverse=True)[:limit]


def interactive_candidate() -> str:
    print("TemporaryAI Video Reference Intake")
    print()
    candidates = recent_candidates()
    for index, path in enumerate(candidates, 1):
        print(f"{index}. {candidate_display(path)} [{path.name}]")
    print()
    choice = input("Pick number, paste candidate id, or type search text: ").strip()
    if choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(candidates):
            return candidates[idx - 1].name
    return choice


def run_yt_dlp_metadata(url: str) -> tuple[dict[str, Any], str]:
    exe = shutil.which("yt-dlp")
    if not exe:
        command = [sys.executable, "-m", "yt_dlp"]
    else:
        command = [exe]
    try:
        proc = subprocess.run(
            [*command, "--dump-json", "--skip-download", "--no-warnings", url],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=80,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"error": str(exc)}, "metadata_error"
    if proc.returncode != 0:
        return {"stderr": proc.stderr.strip()[:1200]}, "metadata_error"
    try:
        metadata = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return {"error": f"Invalid yt-dlp JSON: {exc}"}, "metadata_error"
    return metadata, "metadata_found"


def yt_dlp_command() -> list[str]:
    exe = shutil.which("yt-dlp")
    if exe:
        return [exe]
    return [sys.executable, "-m", "yt_dlp"]


def run_yt_dlp_captions(url: str, out_dir: Path) -> dict[str, Any]:
    """Download captions/subtitles only, never full video or audio."""
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            [
                *yt_dlp_command(),
                "--skip-download",
                "--write-subs",
                "--write-auto-subs",
                "--sub-langs",
                "en,en.*",
                "--sub-format",
                "vtt",
                "--output",
                str(out_dir / "captions.%(ext)s"),
                "--no-warnings",
                url,
            ],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"status": "caption_download_error", "error": str(exc)[:600], "files": []}
    caption_files = sorted(out_dir.glob("captions*.vtt"))
    return {
        "status": "captions_found" if caption_files else "no_captions_found",
        "returncode": proc.returncode,
        "stderr": proc.stderr.strip()[:900],
        "files": [rel(path) for path in caption_files],
    }


def clean_vtt_lines(path: Path, limit: int = 500) -> list[str]:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    lines: list[str] = []
    last = ""
    for original in raw.splitlines():
        line = original.strip()
        if not line:
            continue
        if line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")):
            continue
        if "-->" in line or re.match(r"^\d+$", line):
            continue
        line = re.sub(r"<[^>]+>", "", line)
        line = re.sub(r"\{[^}]+\}", "", line)
        line = html.unescape(line)
        line = re.sub(r"\s+", " ", line).strip()
        if not line or line == last:
            continue
        lines.append(line)
        last = line
        if len(lines) >= limit:
            break
    return lines


def caption_style_analysis(caption_paths: list[Path]) -> dict[str, Any]:
    all_lines: list[str] = []
    for path in caption_paths:
        all_lines.extend(clean_vtt_lines(path))
    if not all_lines:
        return {"status": "no_caption_text", "line_count": 0}
    word_counts = [len(re.findall(r"\b[\w']+\b", line)) for line in all_lines]
    return {
        "status": "analyzed",
        "line_count": len(all_lines),
        "average_words_per_caption_line": round(sum(word_counts) / max(len(word_counts), 1), 2),
        "question_line_count": sum(1 for line in all_lines if "?" in line),
        "exclamation_line_count": sum(1 for line in all_lines if "!" in line),
        "short_line_count": sum(1 for count in word_counts if count <= 5),
        "long_line_count": sum(1 for count in word_counts if count >= 18),
        "stage_direction_like_line_count": sum(
            1
            for line in all_lines
            if re.search(r"^\[.*\]$|^\(.*\)$|\b(laughs|sighs|gasps|screams|grunts)\b", line, flags=re.I)
        ),
        "copyright_note": "No dialogue is quoted in generated notes; use this only for broad style observation.",
    }


def speech_pattern_notes(analysis: dict[str, Any], caption_result: dict[str, Any]) -> str:
    files = caption_result.get("files", []) or []
    if analysis.get("status") != "analyzed":
        return f"""# Auto Speech Pattern Notes

Caption status: {caption_result.get("status", "unknown")}
Caption files: {", ".join(files) if files else "none"}

No caption text was available to analyze. Add Robert-approved short transcript excerpts or local authorized samples if needed.

## Manual Notes Still Needed

- Pace:
- Energy:
- How the person interrupts, jokes, hesitates, or softens:
- Relationship-specific ways they address others:
- What to avoid so the TemporaryAI does not sound generic:
"""
    avg = analysis.get("average_words_per_caption_line", 0)
    style_hints: list[str] = []
    if avg <= 7:
        style_hints.append("Caption lines skew short; review for brisk, clipped, or action-scene dialogue.")
    elif avg >= 14:
        style_hints.append("Caption lines skew longer; review for explanatory, reflective, or monologue-like speech.")
    if analysis.get("question_line_count", 0) >= max(3, analysis.get("line_count", 1) // 12):
        style_hints.append("Questions appear often; review whether curiosity, challenge, or uncertainty is part of the voice.")
    if analysis.get("exclamation_line_count", 0) >= max(2, analysis.get("line_count", 1) // 15):
        style_hints.append("Exclamations appear often; review for high-energy or emotionally direct delivery.")
    if analysis.get("stage_direction_like_line_count", 0):
        style_hints.append("Some caption lines look like action/emotion cues; use manually for movement notes, not quoted dialogue.")
    if not style_hints:
        style_hints.append("Use manual review to identify cadence, confidence, warmth, humor, and emotional posture.")
    return f"""# Auto Speech Pattern Notes

Caption status: {caption_result.get("status", "unknown")}
Caption files: {", ".join(files) if files else "none"}

## Non-Quoted Caption Metrics

- Caption line count reviewed: {analysis.get("line_count", 0)}
- Average words per caption line: {analysis.get("average_words_per_caption_line", 0)}
- Question-mark lines: {analysis.get("question_line_count", 0)}
- Exclamation-mark lines: {analysis.get("exclamation_line_count", 0)}
- Short caption lines: {analysis.get("short_line_count", 0)}
- Long caption lines: {analysis.get("long_line_count", 0)}
- Action/emotion cue-like lines: {analysis.get("stage_direction_like_line_count", 0)}

## Style Hints To Manually Confirm

{chr(10).join(f"- {hint}" for hint in style_hints)}

## Manual Notes Still Needed

- Pace:
- Energy:
- How the person interrupts, jokes, hesitates, or softens:
- Relationship-specific ways they address others:
- Movement/body-language notes visible in the clip:
- What to avoid so the TemporaryAI does not sound generic:

Copyright note: this file does not quote dialogue. It is a broad style aid only.
"""


def movement_reference_auto_notes(
    analysis: dict[str, Any],
    caption_result: dict[str, Any],
    thumbnail_result: dict[str, str],
) -> str:
    if analysis.get("status") != "analyzed":
        return f"""# Auto Movement And Visual Notes

Caption status: {caption_result.get("status", "unknown")}
Thumbnail status: {thumbnail_result.get("status", "unknown")}

No caption text was available to scan for broad movement cues. Use manual clip review and approved stills.

## Manual Notes Still Needed

- Posture:
- Movement rhythm:
- Gesture habits:
- Fight/action movement:
- Facial expression range:
- Avatar-builder stills/angles still needed:
"""
    cue_count = analysis.get("stage_direction_like_line_count", 0)
    hints = []
    if cue_count:
        hints.append("Caption data contains possible action/emotion cues; manually review those moments for posture and expression.")
    else:
        hints.append("Caption data has few explicit action cues; rely on manual visual review and still images.")
    hints.append("Use the thumbnail only as a weak visual hint. Avatar work needs several reviewed stills or approved reference images.")
    return f"""# Auto Movement And Visual Notes

Caption status: {caption_result.get("status", "unknown")}
Thumbnail status: {thumbnail_result.get("status", "unknown")}
Thumbnail/reference image: {thumbnail_result.get("path", "not downloaded")}

## Non-Quoted Movement Metrics

- Caption lines reviewed: {analysis.get("line_count", 0)}
- Possible action/emotion cue-like lines: {cue_count}

## Movement Hints To Manually Confirm

{chr(10).join(f"- {hint}" for hint in hints)}

## Manual Notes Still Needed

- Posture:
- Movement rhythm:
- Gesture habits:
- Fight/action movement:
- Facial expression range:
- Avatar-builder stills/angles still needed:

Copyright note: this file does not quote dialogue and does not extract video frames.
"""


def ensure_voice_sample_policy(candidate_dir: Path) -> Path:
    folder = candidate_dir / "workbench" / "inputs" / "voice_samples" / "authorized"
    readme = folder / "README.md"
    if not readme.exists():
        write_text(
            readme,
            """# Authorized Voice Samples

Put only Robert-owned, personally recorded, licensed, or clearly authorized voice samples here.

Online videos may be used for broad speaking-style notes, caption metrics, and avatar reference review, but this system does not treat online video audio as consent for exact voice cloning.

Suggested use:

- `raw/` for source clips Robert owns or has permission to use.
- `notes/` for manual cadence, emotion, pronunciation, and delivery observations.
- `exports/` for reviewed features or future voice-model artifacts.
""",
        )
    return folder


def clean_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    keep_keys = [
        "id",
        "title",
        "fulltitle",
        "description",
        "channel",
        "uploader",
        "duration",
        "webpage_url",
        "thumbnail",
        "upload_date",
        "view_count",
        "age_limit",
    ]
    cleaned = {key: metadata.get(key) for key in keep_keys if metadata.get(key) not in (None, "")}
    if "description" in cleaned and isinstance(cleaned["description"], str):
        cleaned["description"] = cleaned["description"][:1200]
    thumbnails = metadata.get("thumbnails") or []
    if isinstance(thumbnails, list):
        cleaned["thumbnails"] = [
            {
                "url": item.get("url"),
                "width": item.get("width"),
                "height": item.get("height"),
            }
            for item in thumbnails[:6]
            if isinstance(item, dict) and item.get("url")
        ]
    return cleaned


def download_thumbnail(url: str, out_dir: Path) -> dict[str, str]:
    if not url.lower().startswith(("http://", "https://")):
        return {"status": "no_thumbnail_url"}
    dest = out_dir / "thumbnail.jpg"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "KiraTemporaryAI/1.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            data = response.read(6_000_000)
        dest.write_bytes(data)
    except (OSError, urllib.error.URLError) as exc:
        return {"status": "thumbnail_download_failed", "error": str(exc)[:500]}
    return {"status": "downloaded", "path": rel(dest)}


def video_reference_markdown(
    *,
    candidate_dir: Path,
    url: str,
    title: str,
    character: str,
    note: str,
    metadata_status: str,
    metadata: dict[str, Any],
    thumbnail_result: dict[str, str],
    caption_result: dict[str, Any],
    speech_analysis: dict[str, Any],
) -> str:
    display = candidate_display(candidate_dir)
    metadata_title = metadata.get("title") or metadata.get("fulltitle") or ""
    thumbnail_path = thumbnail_result.get("path", "")
    source_title = title or metadata_title or "Untitled video reference"
    return f"""# VIDEO_REFERENCE_READ_FIRST

Candidate: {display}
Character/version focus: {character or display}
Source title: {source_title}
Source URL: {url}
Metadata status: {metadata_status}
Created: {now_iso()}

## Robert Note

{note or "No extra note provided."}

## Use Policy

- This is a video-reference aid for character voice, movement, expression, costume, and avatar design.
- Do not treat this as a watched memory or personal experience.
- This online-reference package alone does not extract, train, assign, or authorize a voice.
- Authorized files already in `Data/library` may use the separate bounded private-local intake lane after target speaker/performer review.
- Do not quote copyrighted dialogue from the video unless Robert pasted a short excerpt separately.
- If the video conflicts with more specific local transcript/canon notes, ask Robert or prefer the selected canon point.

## Metadata Snapshot

- Video title: {metadata_title or "not available"}
- Channel/uploader: {metadata.get("channel") or metadata.get("uploader") or "not available"}
- Duration seconds: {metadata.get("duration") or "not available"}
- Upload date: {metadata.get("upload_date") or "not available"}
- Local thumbnail/reference image: {thumbnail_path or "not downloaded"}
- Caption/subtitle status: {caption_result.get("status", "unknown")}
- Caption style analysis: {speech_analysis.get("status", "unknown")}

## Speaking Style Notes To Fill In

- Pace:
- Energy:
- Common emotional posture:
- How she addresses others:
- What to avoid so she does not sound generic:

## Visual Reference Notes To Fill In

- Face/hair:
- Outfit/form:
- Body language:
- Movement/action notes:
- Useful avatar-builder angles still needed:

## Next Extraction Tasks

1. Watch or review the clip manually and add short non-quoted notes to this file.
2. Add any Robert-pasted short transcript excerpt under `workbench/inputs/reference_material/transcripts/`.
3. Review `speech_pattern_auto_notes.md` and convert broad metrics into human speaking-style notes.
4. Add approved still images or thumbnails to the avatar reference review folder when needed.
5. For exact private-local voice/movement evidence, use `tools/create_temp_ai_local_media_intake.py` with explicit short scene ranges, then complete its human review file.
6. Voice model preparation and activation are later, separate actions; private intake does not authorize public release or an official voice claim.
7. In chat, use these notes as backstage grounding and speak as the selected version, not as a source analyst.
"""


def update_index(candidate_dir: Path, record: dict[str, Any]) -> None:
    index_path = candidate_dir / "workbench" / "inputs" / "video_references" / "video_reference_index.json"
    index = read_json(index_path, {"candidate_id": candidate_dir.name, "updated_at": "", "references": []})
    references = index.setdefault("references", [])
    references = [item for item in references if item.get("reference_id") != record.get("reference_id")]
    references.append(record)
    index["references"] = references
    index["updated_at"] = now_iso()
    write_json(index_path, index)


def attach_video_reference(args: argparse.Namespace) -> dict[str, Any]:
    candidate_id = args.candidate or interactive_candidate()
    url = args.url or input("Video URL: ").strip()
    if not url:
        raise ValueError("Video URL is required.")
    candidate_dir = find_candidate(candidate_id)
    title = args.title or input("Optional source title: ").strip()
    character = args.character or input("Character/version focus: ").strip()
    note = args.note or input("Robert note / intended use: ").strip()

    metadata, metadata_status = run_yt_dlp_metadata(url)
    cleaned = clean_metadata(metadata) if metadata_status == "metadata_found" else metadata
    reference_id = f"{stamp()}_{slug(title or cleaned.get('title', '') or character or candidate_dir.name)}"
    out_dir = candidate_dir / "workbench" / "inputs" / "video_references" / reference_id
    out_dir.mkdir(parents=True, exist_ok=True)

    thumb_url = str(cleaned.get("thumbnail") or "")
    thumbnail_result = download_thumbnail(thumb_url, out_dir) if thumb_url else {"status": "no_thumbnail_url"}
    caption_result = run_yt_dlp_captions(url, out_dir)
    caption_paths = [PROJECT_ROOT / path for path in caption_result.get("files", []) or []]
    speech_analysis = caption_style_analysis(caption_paths)
    authorized_voice_folder = ensure_voice_sample_policy(candidate_dir)

    record = {
        "reference_id": reference_id,
        "created_at": now_iso(),
        "candidate_id": candidate_dir.name,
        "candidate_display": candidate_display(candidate_dir),
        "url": url,
        "source_url": url,
        "title": title or cleaned.get("title", ""),
        "character_or_version_focus": character,
        "robert_note": note,
        "metadata_status": metadata_status,
        "metadata": cleaned,
        "thumbnail": thumbnail_result,
        "captions": caption_result,
        "speech_pattern_analysis": speech_analysis,
        "local_folder": rel(out_dir),
        "read_first": rel(out_dir / "VIDEO_REFERENCE_READ_FIRST.md"),
        "authorized_voice_samples_folder": rel(authorized_voice_folder),
        "policy": {
            "full_video_downloaded": False,
            "audio_downloaded": False,
            "voice_samples_from_online_video_downloaded": False,
            "voice_clone_allowed": False,
            "use_for_speaking_style_notes": True,
            "use_for_avatar_reference_review": True,
            "sources_are_evidence_not_memory": True,
        },
    }

    write_json(out_dir / "video_reference.json", record)
    write_text(
        out_dir / "VIDEO_REFERENCE_READ_FIRST.md",
        video_reference_markdown(
            candidate_dir=candidate_dir,
            url=url,
            title=title,
            character=character,
            note=note,
            metadata_status=metadata_status,
            metadata=cleaned,
            thumbnail_result=thumbnail_result,
            caption_result=caption_result,
            speech_analysis=speech_analysis,
        ),
    )
    write_text(
        out_dir / "speaking_style_notes.md",
        "# Speaking Style Notes\n\nUse short observations here. Do not paste long copyrighted dialogue.\n",
    )
    write_text(out_dir / "speech_pattern_auto_notes.md", speech_pattern_notes(speech_analysis, caption_result))
    write_text(
        out_dir / "movement_reference_auto_notes.md",
        movement_reference_auto_notes(speech_analysis, caption_result, thumbnail_result),
    )
    write_text(
        out_dir / "visual_reference_notes.md",
        "# Visual Reference Notes\n\nUse this for avatar-builder observations and approved still/reference notes.\n\nThumbnail-only capture is not enough for movement. Add manual notes from reviewed clips or approved stills here.\n",
    )
    update_index(candidate_dir, record)
    return record


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Attach a video reference to a TemporaryAI candidate.")
    parser.add_argument("--candidate", default="", help="Candidate id or search text. If omitted, asks interactively.")
    parser.add_argument("--url", default="", help="Video URL.")
    parser.add_argument("--title", default="", help="Optional source title.")
    parser.add_argument("--character", default="", help="Character/version focus.")
    parser.add_argument("--note", default="", help="Robert note / intended use.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        record = attach_video_reference(args)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    print(json.dumps(record, indent=2, ensure_ascii=True))
    print()
    print(f"Video reference saved: {record['local_folder']}")
    if record["metadata_status"] == "yt_dlp_not_installed":
        print("Note: yt-dlp is not installed, so only the manual reference package was created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
