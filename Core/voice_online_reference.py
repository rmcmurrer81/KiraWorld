"""Build reviewable online-video voice references without auto-approving speakers."""
from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from Core.voice_reference_pipeline import (
    PROJECT_ROOT,
    REFERENCE_ROOT,
    build_local_reference_pack,
    now_iso,
    read_json,
    relative,
    resolve_ffmpeg,
    slug,
    stamp,
    write_json,
)


def _yt_dlp_command() -> list[str]:
    executable = shutil.which("yt-dlp")
    return [executable] if executable else [sys.executable, "-m", "yt_dlp"]


def find_reference_by_url(url: str) -> Path | None:
    """Find the newest saved TemporaryAI video reference for a URL."""
    root = PROJECT_ROOT / "TemporaryAI" / "candidates"
    matches: list[Path] = []
    if not root.exists():
        return None
    for path in root.glob("*/workbench/inputs/video_references/*/video_reference.json"):
        record = read_json(path, {})
        if str(record.get("url") or record.get("source_url") or "").strip() == url.strip():
            matches.append(path.parent)
    return max(matches, key=lambda item: item.stat().st_mtime) if matches else None


def download_candidate_audio(url: str, destination: Path) -> tuple[Path, dict[str, Any]]:
    """Download best available audio as evidence; no speaker is approved here."""
    destination.mkdir(parents=True, exist_ok=True)
    output_template = destination / "online_source.%(ext)s"
    command = _yt_dlp_command()
    ffmpeg = resolve_ffmpeg()
    if ffmpeg:
        command.extend(["--ffmpeg-location", str(Path(ffmpeg).parent)])
    command.extend([
        "--no-playlist",
        "--no-warnings",
        "--write-info-json",
        "-f",
        "bestaudio/best",
        "-o",
        str(output_template),
        url,
    ])
    completed = subprocess.run(
        command,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=3600,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"yt-dlp audio download failed: {completed.stderr.strip()[:1200]}")
    media = sorted(
        (path for path in destination.glob("online_source.*") if path.suffix.lower() not in {".json", ".part"}),
        key=lambda path: path.stat().st_size,
        reverse=True,
    )
    if not media:
        raise RuntimeError("yt-dlp finished without creating an audio source file.")
    info_files = list(destination.glob("online_source*.info.json"))
    metadata = read_json(info_files[0], {}) if info_files else {}
    return media[0], metadata


def build_online_audio_pack(
    *,
    target_name: str,
    target_id: str,
    url: str,
    form_or_version: str = "",
    script_path: Path | None = None,
    authorization_status: str = "review_required",
    saved_reference_dir: Path | None = None,
) -> dict[str, Any]:
    """Download an online source, segment it, then mark every clip unreviewed."""
    source_dir = PROJECT_ROOT / "Voice" / "reference_sources" / slug(target_id) / str(time.time_ns())
    media_path, metadata = download_candidate_audio(url, source_dir)
    record = build_local_reference_pack(
        target_name=target_name,
        target_id=target_id,
        source_path=media_path,
        script_path=script_path,
        authorization_status=authorization_status,
        form_or_version=form_or_version,
    )
    pack_dir = PROJECT_ROOT / record["pack_dir"]
    manifest_path = pack_dir / "voice_reference_manifest.json"
    manifest = read_json(manifest_path, record)
    reference_dir = saved_reference_dir or find_reference_by_url(url)
    saved_record = read_json(reference_dir / "video_reference.json", {}) if reference_dir else {}
    manifest["source"].update(
        {
            "kind": "online_video_candidate_audio",
            "url": url,
            "title": metadata.get("title") or saved_record.get("title") or "",
            "channel": metadata.get("channel") or saved_record.get("metadata", {}).get("channel") or "",
            "online_audio_is_not_speaker_verified": True,
        }
    )
    manifest["online_reference"] = {
        "saved_reference_dir": relative(reference_dir) if reference_dir else "",
        "metadata_status": saved_record.get("metadata_status", "downloaded_with_audio"),
        "caption_status": saved_record.get("captions", {}).get("status", "unknown"),
        "thumbnail": saved_record.get("thumbnail", {}),
        "speech_pattern_analysis": saved_record.get("speech_pattern_analysis", {}),
    }
    manifest["model_readiness"] = {
        "eligible": False,
        "authorization_permits_model": False,
        "reason": "Online clips may contain narration, music, and other speakers. Human target-speaker review and authorization are required.",
    }
    write_json(manifest_path, manifest)
    return manifest


def link_saved_online_reference(
    *, target_name: str, target_id: str, form_or_version: str, reference_dir: Path
) -> dict[str, Any]:
    """Create a no-audio catalog entry from existing captions/thumbnail/style notes."""
    source = read_json(reference_dir / "video_reference.json", {})
    if not source:
        raise FileNotFoundError(f"No video_reference.json in {reference_dir}")
    pack_id = f"{slug(target_id)}_online_style_{stamp()}"
    pack_dir = REFERENCE_ROOT / slug(target_id) / pack_id
    pack_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for name in (
        "video_reference.json",
        "speech_pattern_auto_notes.md",
        "speaking_style_notes.md",
        "movement_reference_auto_notes.md",
        "visual_reference_notes.md",
        "thumbnail.jpg",
    ):
        source_path = reference_dir / name
        if source_path.exists():
            target_path = pack_dir / "online_reference" / name
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target_path)
            copied.append(relative(target_path))
    record = {
        "schema_version": 1,
        "pack_id": pack_id,
        "created_at": now_iso(),
        "target": {"name": target_name, "id": slug(target_id), "form_or_version": form_or_version},
        "source": {
            "kind": "online_video_style_reference",
            "url": source.get("url") or source.get("source_url") or "",
            "title": source.get("title") or source.get("metadata", {}).get("title") or "",
            "authorization_status": "style_reference_only",
        },
        "online_reference": {
            "original_dir": relative(reference_dir),
            "copied_files": copied,
            "caption_status": source.get("captions", {}).get("status", "unknown"),
            "speech_pattern_analysis": source.get("speech_pattern_analysis", {}),
        },
        "audio": {"candidate_clip_count": 0, "clips": []},
        "review": {"status": "style_reference_saved"},
        "model_readiness": {
            "eligible": False,
            "reason": "This package contains captions, metrics, and imagery but no reviewed target-only audio.",
        },
        "pack_dir": relative(pack_dir),
    }
    write_json(pack_dir / "voice_reference_manifest.json", record)
    return record

