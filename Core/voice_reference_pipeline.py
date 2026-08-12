"""Create human-reviewed voice-reference packs from local media."""
from __future__ import annotations

import hashlib, json, math, os, re, shutil, struct, subprocess, wave
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_ROOT = PROJECT_ROOT / "Voice" / "reference_packs"
APPROVED_AUTHORIZATION = {"owned", "licensed", "authorized", "self_recorded"}


def now_iso() -> str: return datetime.now(timezone.utc).isoformat()
def stamp() -> str: return datetime.now().strftime("%Y%m%d_%H%M%S")
def slug(value: str, limit: int = 70) -> str: return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")[:limit] or "voice"

def relative(path: Path) -> str:
    try: return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError: return str(path.resolve())

def read_json(path: Path, default: Any) -> Any:
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError): return default

def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def resolve_ffmpeg() -> str | None:
    configured = os.environ.get("KIRA_FFMPEG", "").strip()
    if configured and Path(configured).exists(): return configured
    if found := shutil.which("ffmpeg"): return found
    try:
        import imageio_ffmpeg  # type: ignore
        return imageio_ffmpeg.get_ffmpeg_exe()
    except (ImportError, OSError): return None

def ffmpeg_readiness() -> dict[str, Any]:
    executable = resolve_ffmpeg()
    return {"ready": bool(executable), "executable": executable or "", "remedy": "Install FFmpeg or imageio-ffmpeg, or set KIRA_FFMPEG." if not executable else ""}

def file_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()

def extract_script_inventory(script_path: Path | None, target_name: str) -> dict[str, Any]:
    if not script_path: return {"status": "not_supplied"}
    result: dict[str, Any] = {"status": "attached", "path": relative(script_path), "sha256": file_fingerprint(script_path)}
    if script_path.suffix.lower() != ".pdf":
        result["note"] = "Non-PDF script attached; no automatic cue inventory was made."
        return result
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(script_path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        pattern = re.compile(rf"\b{re.escape(target_name)}\b", flags=re.I)
        result.update({"status": "inventoried", "page_count": len(reader.pages), "target_name_mentions": len(pattern.findall(text)), "extracted_character_count": len(text), "note": "Cue counts assist review; they do not identify audio speakers automatically."})
    except Exception as exc: result.update({"status": "inventory_error", "error": str(exc)[:500]})
    return result

def extract_audio(source: Path, destination: Path, sample_rate: int = 24000) -> None:
    ffmpeg = resolve_ffmpeg()
    if not ffmpeg: raise RuntimeError("FFmpeg is unavailable. Run tools/check_voice_pipeline.py for setup details.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(source), "-vn", "-ac", "1", "-ar", str(sample_rate), "-c:a", "pcm_s16le", str(destination)], capture_output=True, text=True, timeout=1800, check=False)
    if completed.returncode != 0 or not destination.exists(): raise RuntimeError(f"FFmpeg audio extraction failed: {completed.stderr.strip()[:1000]}")

def _rms_16le(raw: bytes) -> float:
    count = len(raw) // 2
    if count <= 0: return 0.0
    values = struct.unpack(f"<{count}h", raw[:count * 2])
    return math.sqrt(sum(value * value for value in values) / count)

def _percentile(values: list[float], ratio: float) -> float:
    if not values: return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, round((len(ordered) - 1) * ratio)))]

@dataclass
class ClipRecord:
    clip_id: str
    path: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    peak_rms: float
    review_status: str = "unreviewed"
    reviewer_note: str = ""

def segment_wav(source_wav: Path, clips_dir: Path, frame_ms: int = 30) -> list[ClipRecord]:
    """Split mono PCM speech candidates on silence; speaker review still follows."""
    clips_dir.mkdir(parents=True, exist_ok=True)
    with wave.open(str(source_wav), "rb") as reader:
        channels, width, rate, total_frames = reader.getnchannels(), reader.getsampwidth(), reader.getframerate(), reader.getnframes()
        if channels != 1 or width != 2: raise ValueError("Segmentation expects mono 16-bit PCM WAV input.")
        window_frames = max(1, int(rate * frame_ms / 1000)); windows, levels = [], []
        while raw := reader.readframes(window_frames): windows.append(raw); levels.append(_rms_16le(raw))
    threshold = max(180.0, _percentile(levels, .30) * 2.2, _percentile(levels, .75) * .22)
    min_windows, max_windows, hold_windows = round(1000 / frame_ms), round(12000 / frame_ms), round(450 / frame_ms)
    ranges, start, last_active = [], None, None
    for index, level in enumerate(levels):
        if level >= threshold:
            start = max(0, index - 2) if start is None else start; last_active = index
        if start is not None and last_active is not None:
            hit_max, held_silence = index - start + 1 >= max_windows, index - last_active >= hold_windows
            if hit_max or held_silence:
                end = min(len(windows), index + 1 if hit_max else last_active + 3)
                if end - start >= min_windows: ranges.append((start, end))
                start = last_active = None
    if start is not None and len(windows) - start >= min_windows: ranges.append((start, len(windows)))
    clips = []
    for number, (start_window, end_window) in enumerate(ranges, 1):
        clip_path = clips_dir / f"clip_{number:04d}.wav"
        with wave.open(str(clip_path), "wb") as writer:
            writer.setnchannels(1); writer.setsampwidth(2); writer.setframerate(rate); writer.writeframes(b"".join(windows[start_window:end_window]))
        start_seconds, end_seconds = start_window * frame_ms / 1000, min(total_frames / rate, end_window * frame_ms / 1000)
        clips.append(ClipRecord(f"clip_{number:04d}", relative(clip_path), round(start_seconds, 3), round(end_seconds, 3), round(end_seconds - start_seconds, 3), round(max(levels[start_window:end_window], default=0.0), 2)))
    return clips

def build_local_reference_pack(*, target_name: str, target_id: str, source_path: Path, script_path: Path | None = None, authorization_status: str = "review_required", form_or_version: str = "") -> dict[str, Any]:
    target_slug = slug(target_id or target_name); pack_id = f"{target_slug}_{slug(source_path.stem, 45)}_{stamp()}"; pack_dir = REFERENCE_ROOT / target_slug / pack_id
    extracted_wav = pack_dir / "extracted" / "source_audio_mono_24khz.wav"
    extract_audio(source_path, extracted_wav); clips = segment_wav(extracted_wav, pack_dir / "candidate_clips")
    authorization_status = authorization_status.strip().lower()
    record = {"schema_version": 1, "pack_id": pack_id, "created_at": now_iso(), "target": {"name": target_name, "id": target_slug, "form_or_version": form_or_version}, "source": {"kind": "local_media", "path": relative(source_path), "sha256": file_fingerprint(source_path), "authorization_status": authorization_status}, "script": extract_script_inventory(script_path, target_name), "audio": {"extracted_wav": relative(extracted_wav), "candidate_clip_count": len(clips), "clips": [asdict(c) for c in clips]}, "review": {"status": "pending_human_speaker_review", "approved_clip_count": 0, "rejected_clip_count": 0}, "model_readiness": {"eligible": False, "reason": "Clips must be reviewed as the target speaker before model preparation.", "authorization_permits_model": authorization_status in APPROVED_AUTHORIZATION}, "pack_dir": relative(pack_dir)}
    write_json(pack_dir / "voice_reference_manifest.json", record); write_json(pack_dir / "clip_review.json", {"clips": record["audio"]["clips"]})
    (pack_dir / "README.md").write_text(f"# Voice Reference Pack: {target_name}\n\nSource: `{relative(source_path)}`  \nCandidate clips: {len(clips)}  \nAuthorization: `{authorization_status}`\n\nCandidate clips can contain any speaker. Approve only target-only speech in the review panel. Extraction alone never makes this pack model-ready.\n", encoding="utf-8")
    return record

def update_pack_review(pack_dir: Path, clips: Iterable[dict[str, Any]]) -> dict[str, Any]:
    manifest_path = pack_dir / "voice_reference_manifest.json"; manifest = read_json(manifest_path, {}); clip_list = list(clips)
    approved = [c for c in clip_list if c.get("review_status") == "approved_target"]; rejected = [c for c in clip_list if str(c.get("review_status", "")).startswith("rejected")]
    approved_dir = pack_dir / "approved_target_clips"; approved_dir.mkdir(parents=True, exist_ok=True)
    for stale in approved_dir.glob("*.wav"): stale.unlink()
    for clip in approved:
        source = PROJECT_ROOT / str(clip["path"])
        if source.exists(): shutil.copy2(source, approved_dir / source.name)
    authorization = str(manifest.get("source", {}).get("authorization_status", "review_required")); authorized = authorization in APPROVED_AUTHORIZATION
    total_seconds = round(sum(float(c.get("duration_seconds", 0)) for c in approved), 2); enough_audio = total_seconds >= 20
    manifest["audio"]["clips"] = clip_list; manifest["review"] = {"status": "reviewed" if all(c.get("review_status") != "unreviewed" for c in clip_list) else "in_progress", "approved_clip_count": len(approved), "rejected_clip_count": len(rejected), "approved_seconds": total_seconds}
    manifest["model_readiness"] = {"eligible": bool(authorized and enough_audio), "authorization_permits_model": authorized, "enough_reviewed_audio": enough_audio, "reason": "Ready for a configured local voice-model backend." if authorized and enough_audio else "Requires authorized status and at least 20 seconds of reviewed target-only speech."}
    write_json(pack_dir / "clip_review.json", {"clips": clip_list}); write_json(manifest_path, manifest); return manifest
