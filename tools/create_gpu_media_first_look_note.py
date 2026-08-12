"""Create a GPU-era first-look media note for Kira/Lisa.

This bridge is intentionally conservative. It may inspect an image or sample a
few video frames, but it does not claim the viewer watched/listened to the full
source and it does not create memory automatically.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import request


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "Data" / "media" / "gpu_first_look_notes"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".divx"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".wma"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def slug(value: str) -> str:
    out = []
    for ch in value.lower():
        if ch.isalnum():
            out.append(ch)
        elif out and out[-1] != "_":
            out.append("_")
    return "".join(out).strip("_")[:80] or "media"


def resolve_path(raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def media_kind(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    if ext in AUDIO_EXTENSIONS:
        return "audio"
    return "other"


def file_metadata(path: Path) -> dict[str, Any]:
    stat = path.stat()
    meta: dict[str, Any] = {
        "path": rel(path),
        "name": path.name,
        "extension": path.suffix.lower(),
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
    }
    try:
        from PIL import Image

        if path.suffix.lower() in IMAGE_EXTENSIONS:
            with Image.open(path) as img:
                meta["image_width"] = img.width
                meta["image_height"] = img.height
                meta["image_mode"] = img.mode
    except Exception as exc:  # pragma: no cover - optional dependency detail
        meta["image_probe_warning"] = str(exc)
    return meta


def ffmpeg_sample_video(path: Path, output_dir: Path, sample_count: int) -> tuple[list[Path], list[str]]:
    warnings: list[str] = []
    frames: list[Path] = []
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        warnings.append("ffmpeg_not_found; video frames were not sampled")
        return frames, warnings
    output_dir.mkdir(parents=True, exist_ok=True)
    pattern = output_dir / "frame_%02d.jpg"
    # Sample a few frames across the video without needing duration metadata.
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(path),
        "-vf",
        f"thumbnail,select='not(mod(n\\,{max(1, sample_count)}))',scale=640:-1",
        "-frames:v",
        str(sample_count),
        str(pattern),
        "-y",
    ]
    completed = subprocess.run(command, cwd=str(PROJECT_ROOT), capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        warnings.append(f"ffmpeg_sample_failed: {completed.stderr.strip()[:500]}")
    frames = sorted(output_dir.glob("frame_*.jpg"))[:sample_count]
    if not frames and not warnings:
        warnings.append("ffmpeg_created_no_frames")
    return frames, warnings


def image_to_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def ollama_vision_prompt(model: str, image_paths: list[Path], prompt: str, timeout: int) -> dict[str, Any]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "images": [image_to_b64(path) for path in image_paths],
        "options": {"temperature": 0.2, "num_predict": 450},
    }
    data = json.dumps(payload).encode("utf-8")
    req = request.Request("http://localhost:11434/api/generate", data=data, headers={"Content-Type": "application/json"})
    started = datetime.now(timezone.utc)
    try:
        with request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
        parsed = json.loads(raw)
        return {
            "ok": True,
            "model": model,
            "started_at": started.isoformat(),
            "response": (parsed.get("response") or "").strip(),
        }
    except Exception as exc:
        return {"ok": False, "model": model, "started_at": started.isoformat(), "error": str(exc)}


def build_note(args: argparse.Namespace) -> tuple[dict[str, Any], Path, Path]:
    source = resolve_path(args.source)
    if not source.exists():
        raise FileNotFoundError(source)

    kind = media_kind(source)
    note_id = f"gpu_first_look_{args.viewer}_{slug(source.stem)}_{run_id()}"
    output_dir = resolve_path(args.output_dir)
    note_dir = output_dir / note_id
    sample_dir = note_dir / "samples"
    note_dir.mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []
    samples: list[Path] = []
    if kind == "image":
        samples = [source]
    elif kind == "video":
        samples, warnings = ffmpeg_sample_video(source, sample_dir, args.sample_count)
    elif kind == "audio":
        warnings.append("audio_visual_analysis_not_supported_yet; use transcript/metadata listening mode later")
    else:
        warnings.append("unknown_media_type; metadata-only note created")

    vision_model = args.vision_model or os.getenv("KIRA_VISION_MODEL", "")
    vision_result: dict[str, Any] = {"ok": None, "detail": "vision model not configured"}
    if vision_model and samples:
        prompt = (
            "Describe what is visible in these image/video-frame samples for Kira's media understanding notes. "
            "Be concrete but cautious. Do not claim anyone watched the whole movie/video. "
            "Return: visible elements, likely mood/tone, possible questions, and confidence limits."
        )
        vision_result = ollama_vision_prompt(vision_model, samples[: args.sample_count], prompt, args.timeout)

    note = {
        "note_id": note_id,
        "created_at": utc_now(),
        "viewer": args.viewer,
        "source": file_metadata(source),
        "media_kind": kind,
        "samples": [
            {
                "path": rel(path),
                "source_role": "original_image" if path == source else "sampled_video_frame",
                "metadata": file_metadata(path),
            }
            for path in samples
        ],
        "vision_result": vision_result,
        "warnings": warnings,
        "status": "draft_first_look",
        "policy": {
            "does_not_mean_watched_full_media": True,
            "does_not_create_lived_memory": True,
            "does_not_create_temporary_ai": True,
            "safe_use": "May support preview, curiosity, visual reference, or later discussion after review.",
            "if_private_or_adult": "Requires owner/privacy review before Kira/Lisa can browse or discuss.",
        },
        "next_steps": [
            "If this is a video, install/configure frame sampling support or provide selected screenshots.",
            "If a local vision model is installed, rerun with --vision-model MODEL.",
            "Review the note before promoting it into media preferences or project source evidence.",
        ],
    }

    json_path = note_dir / f"{note_id}.json"
    md_path = note_dir / f"{note_id}.monitor.md"
    json_path.write_text(json.dumps(note, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(note), encoding="utf-8")
    return note, json_path, md_path


def render_markdown(note: dict[str, Any]) -> str:
    vision = note.get("vision_result") or {}
    lines = [
        f"# {note['note_id']}",
        "",
        f"- viewer: {note['viewer']}",
        f"- source: {note['source']['path']}",
        f"- media_kind: {note['media_kind']}",
        f"- status: {note['status']}",
        f"- samples: {len(note.get('samples', []))}",
        "",
        "## Policy",
        "",
        "- This first-look note is not a watched/listened memory.",
        "- It may support preview, curiosity, visual reference, or later discussion after review.",
        "",
    ]
    if note.get("warnings"):
        lines.extend(["## Warnings", ""])
        lines.extend(f"- {warning}" for warning in note["warnings"])
        lines.append("")
    lines.extend(["## Vision Result", ""])
    if vision.get("ok") is True:
        lines.append(vision.get("response", ""))
    elif vision.get("ok") is False:
        lines.append(f"Vision call failed: {vision.get('error')}")
    else:
        lines.append(vision.get("detail", "No vision result."))
    lines.append("")
    lines.extend(["## Samples", ""])
    for sample in note.get("samples", []):
        lines.append(f"- {sample['path']} ({sample['source_role']})")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a reviewed GPU-era first-look media note.")
    parser.add_argument("source", help="Image, video, or audio path to inspect. Relative paths are from the project root.")
    parser.add_argument("--viewer", default="kira", choices=["kira", "lisa", "kira_lisa", "robert", "temporary_ai"])
    parser.add_argument("--sample-count", type=int, default=3)
    parser.add_argument("--vision-model", default="", help="Optional Ollama vision model, e.g. llava:7b. Defaults to KIRA_VISION_MODEL.")
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    note, json_path, md_path = build_note(args)
    print(json.dumps({"json": rel(json_path), "monitor": rel(md_path), "samples": len(note["samples"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
