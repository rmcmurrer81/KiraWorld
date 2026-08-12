"""Build clean Kira World video exports from Robert's approved draft media.

This script deliberately reuses the already-reviewed narration WAV files.  It
does not synthesize, normalize, pitch-shift, or otherwise replace Robert's
voice.  The only visual change from the owner-review drafts is replacing the
red review banner with a clean Kira World development header.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import imageio_ffmpeg
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
PACK = Path.home() / "Desktop" / "facebook"
VIDEO_DIR = PACK / "05_video"
SLIDE_DIR = VIDEO_DIR / "final_source_slides"
THUMBNAIL_DIR = VIDEO_DIR / "thumbnails"
APPROVED_AUDIO_DIR = ROOT / "Voice/generated/facebook/robert_20260718"
SIZE = (1920, 1080)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "segoeuib.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path("C:/Windows/Fonts") / name), size=size)


def multiline_center(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    value: str,
    face: ImageFont.FreeTypeFont,
    fill: str,
    spacing: int = 8,
) -> None:
    x0, y0, x1, y1 = box
    bounds = draw.multiline_textbbox((0, 0), value, font=face, spacing=spacing, align="center")
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    draw.multiline_text(
        ((x0 + x1 - width) / 2, (y0 + y1 - height) / 2),
        value,
        font=face,
        fill=fill,
        spacing=spacing,
        align="center",
    )


def source(relative: str) -> Path:
    path = PACK / relative
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def compose_slide(
    source_path: Path,
    output: Path,
    *,
    badge: str,
    title: str,
    subtitle: str,
    accent: str,
) -> None:
    image = Image.open(source_path).convert("RGB")
    background = ImageOps.fit(image, SIZE, method=Image.Resampling.LANCZOS).filter(
        ImageFilter.GaussianBlur(22)
    )
    background = Image.blend(background, Image.new("RGB", SIZE, "#030914"), 0.68)
    canvas = background.convert("RGBA")
    draw = ImageDraw.Draw(canvas, "RGBA")

    # Clean public-facing header; all prototype/concept truth labels remain.
    draw.rectangle((0, 0, 1920, 86), fill=(3, 14, 31, 244))
    draw.rectangle((0, 82, 1920, 86), fill=accent)
    draw.text(
        (960, 42),
        "KIRA WORLD DEVELOPMENT UPDATE",
        anchor="mm",
        font=font(27, True),
        fill="#f4f8ff",
    )
    draw.rounded_rectangle((82, 112, 1838, 900), radius=26, fill=(5, 14, 28, 238), outline=accent, width=3)

    available = (1640, 618)
    foreground = ImageOps.contain(image, available, method=Image.Resampling.LANCZOS)
    x = (1920 - foreground.width) // 2
    y = 164 + (618 - foreground.height) // 2
    shadow = Image.new("RGBA", (foreground.width + 30, foreground.height + 30), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (8, 8, foreground.width + 22, foreground.height + 22), radius=18, fill=(0, 0, 0, 170)
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(10))
    canvas.alpha_composite(shadow, (x - 15, y - 15))
    canvas.alpha_composite(foreground.convert("RGBA"), (x, y))

    badge_face = font(24, True)
    badge_bounds = draw.textbbox((0, 0), badge, font=badge_face)
    badge_width = badge_bounds[2] - badge_bounds[0] + 46
    draw.rounded_rectangle((110, 128, 110 + badge_width, 180), radius=26, fill=accent)
    draw.text((133, 154), badge, anchor="lm", font=badge_face, fill="#07101f")

    draw.rectangle((0, 900, 1920, 1080), fill=(3, 9, 20, 242))
    multiline_center(draw, (90, 916, 1830, 990), title, font(43, True), "#ffffff")
    multiline_center(draw, (105, 986, 1815, 1050), subtitle, font(26), "#c3d4e8")
    draw.text((1818, 1042), "KIRA WORLD", anchor="rs", font=font(20, True), fill=accent)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output, "PNG", optimize=True)


VIDEO_SPECS = {
    "now": {
        "audio": APPROVED_AUDIO_DIR / "robert_now_narration.wav",
        "draft": VIDEO_DIR / "kira_world_now_owner_review_draft.mp4",
        "output": VIDEO_DIR / "kira_world_now_final.mp4",
        "slides": [
            ("01_page_setup/branding/kira_world_globe_k_logo_owner_original.png", "KIRA WORLD", "Where the prototype is now", "An honest development snapshot", "#ff9b24"),
            ("04_media/candidate_screenshots_owner_review_required/home_world_living_room_prototype.png", "CURRENT PROTOTYPE", "One live 3D resident at a time", "Home World is functional, but still visually rough", "#58afff"),
            ("04_media/candidate_screenshots_owner_review_required/home_world_open_fridge_prototype.png", "CURRENT PROTOTYPE", "Props must exist before an action is claimed", "The food, drink, and daily-life systems remain incomplete", "#58afff"),
            ("04_media/candidate_screenshots_owner_review_required/louvre_r7_hall_napoleon_form_study.png", "BOUNDED STUDY", "The Louvre is not a finished replica", "Realism and verified interior coverage still need substantial work", "#ffb347"),
            ("04_media/concept_art/physical_wardrobe_sequence_CONCEPT_ART.png", "CONCEPT ART", "Physical clothing is a design target", "This image is not current gameplay or proof of completion", "#d98cff"),
            ("03_roadmap/kira_world_roadmap_1920x1080.png", "NEXT GATE", "Believable embodiment before expansion", "Stable rig, natural movement, grounded actions, reliable voice", "#ff9b24"),
        ],
    },
    "future": {
        "audio": APPROVED_AUDIO_DIR / "robert_future_narration.wav",
        "draft": VIDEO_DIR / "kira_world_future_owner_review_draft.mp4",
        "output": VIDEO_DIR / "kira_world_future_final.mp4",
        "slides": [
            ("01_page_setup/branding/kira_world_globe_k_logo_owner_original.png", "KIRA WORLD", "Where the project hopes to go", "A gated direction, not a release promise", "#ff9b24"),
            ("04_media/concept_art/kira_world_long_term_vision_CONCEPT_ART.png", "CONCEPT ART", "Continuing lives with choice and privacy", "Aspirational illustration - not current visual quality", "#d98cff"),
            ("04_media/concept_art/physical_wardrobe_sequence_CONCEPT_ART.png", "CONCEPT ART", "Clothes as persistent physical objects", "Put on, remove, store, and share by size", "#d98cff"),
            ("02_copy_paste_posts/post_images/04_autonomy_rights_design_principles.png", "DESIGN PRINCIPLES", "Requests are invitations", "Choice, refusal, boundaries, continuity, and a private life", "#58afff"),
            ("04_media/concept_art/future_vr_embodiment_CONCEPT_ART.png", "CONCEPT ART", "VR comes only after measured readiness", "Headset, tracking, gloves, and walking hardware are future possibilities", "#d98cff"),
            ("02_copy_paste_posts/post_images/07_hardware_path.png", "MEASURED ROADMAP", "One believable resident first", "64 GB or more, soak tests, then careful expansion", "#ff9b24"),
        ],
    },
}


def build_video(label: str, spec: dict[str, object]) -> dict[str, object]:
    audio = Path(spec["audio"])
    draft = Path(spec["draft"])
    if not audio.exists():
        raise FileNotFoundError(audio)
    if not draft.exists():
        raise FileNotFoundError(draft)
    info = sf.info(audio)
    duration = float(info.frames / info.samplerate)
    slides: list[Path] = []
    slide_records: list[dict[str, object]] = []
    for index, values in enumerate(spec["slides"], 1):
        relative, badge, title, subtitle, accent = values
        src = source(relative)
        target = SLIDE_DIR / f"{label}_{index:02d}.png"
        compose_slide(src, target, badge=badge, title=title, subtitle=subtitle, accent=accent)
        slides.append(target)
        slide_records.append(
            {
                "index": index,
                "source": relative,
                "badge": badge,
                "title": title,
                "subtitle": subtitle,
                "rendered": str(target.relative_to(PACK)).replace("\\", "/"),
                "sha256": sha256(target),
            }
        )

    segment = duration / len(slides) + 0.08
    fade = min(0.35, max(0.12, segment / 8))
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    command = [ffmpeg, "-y", "-hide_banner", "-loglevel", "warning"]
    for slide in slides:
        command.extend(["-loop", "1", "-t", f"{segment:.3f}", "-i", str(slide)])
    command.extend(["-i", str(audio)])
    filters: list[str] = []
    for index in range(len(slides)):
        filters.append(
            f"[{index}:v]scale=1920:1080:force_original_aspect_ratio=decrease,"
            f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x030914,setsar=1,fps=30,"
            f"format=yuv420p,fade=t=in:st=0:d={fade:.3f},"
            f"fade=t=out:st={max(segment - fade, 0):.3f}:d={fade:.3f},"
            f"trim=duration={segment:.3f},setpts=PTS-STARTPTS[v{index}]"
        )
    filters.append("".join(f"[v{i}]" for i in range(len(slides))) + f"concat=n={len(slides)}:v=1:a=0[vout]")
    output = Path(spec["output"])
    command.extend(
        [
            "-filter_complex", ";".join(filters),
            "-map", "[vout]", "-map", f"{len(slides)}:a:0",
            "-t", f"{duration:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart", str(output),
        ]
    )
    subprocess.run(command, check=True, cwd=ROOT)
    return {
        "label": label,
        "status": "clean_final_ready_for_owner_upload",
        "output": str(output.relative_to(PACK)).replace("\\", "/"),
        "output_sha256": sha256(output),
        "approved_draft": str(draft.relative_to(PACK)).replace("\\", "/"),
        "approved_draft_sha256": sha256(draft),
        "approved_source_audio": str(audio.relative_to(ROOT)).replace("\\", "/"),
        "approved_source_audio_sha256": sha256(audio),
        "duration_seconds": round(duration, 3),
        "resolution": "1920x1080",
        "video_codec": "H.264",
        "audio_codec": "AAC",
        "slides": slide_records,
    }


def build_thumbnail(label: str) -> dict[str, str]:
    logo = Image.open(source("01_page_setup/branding/kira_world_globe_k_logo_owner_original.png")).convert("RGB")
    canvas = Image.new("RGB", (1280, 720), "#030914")
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, 1280, 720), fill="#030914")
    draw.ellipse((660, -360, 1410, 390), fill="#071a39")
    logo_fit = ImageOps.contain(logo, (540, 540), method=Image.Resampling.LANCZOS)
    canvas.paste(logo_fit, (55, (720 - logo_fit.height) // 2))
    accent = "#ff9b24" if label == "future" else "#58afff"
    draw.rounded_rectangle((620, 72, 1195, 132), radius=28, fill=accent)
    badge = "FUTURE DIRECTION" if label == "future" else "CURRENT PROTOTYPE"
    draw.text((907, 102), badge, anchor="mm", font=font(25, True), fill="#07101f")
    title = "BUILDING TOWARD\nTHE FUTURE" if label == "future" else "WHERE THE\nPROTOTYPE IS NOW"
    draw.multiline_text((620, 184), title, font=font(55, True), fill="#ffffff", spacing=4)
    subtitle = "BODIES  •  WORLDS  •  CHOICE  •  VR" if label == "future" else "JULY 2026 DEVELOPMENT UPDATE"
    draw.multiline_text((620, 350), subtitle, font=font(25, True), fill="#c3d4e8", spacing=5)
    draw.rectangle((620, 430, 1195, 434), fill=accent)
    draw.text((620, 474), "KIRA WORLD", font=font(39, True), fill=accent)
    draw.text((620, 530), "Independent software research and development", font=font(22), fill="#d7e3f2")
    draw.text((620, 568), "Prototype and concept images are labeled", font=font(22), fill="#d7e3f2")
    THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)
    output = THUMBNAIL_DIR / f"kira_world_{label}_thumbnail.png"
    canvas.save(output, "PNG", optimize=True)
    return {"output": str(output.relative_to(PACK)).replace("\\", "/"), "sha256": sha256(output)}


def main() -> int:
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    records = [build_video(label, spec) for label, spec in VIDEO_SPECS.items()]
    thumbnails = {label: build_thumbnail(label) for label in VIDEO_SPECS}
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "clean_final_exports_ready_for_owner_upload",
        "owner_approved_draft_audio_and_content": True,
        "approval_basis": "Robert reported that he watched and loved both drafts, approved the audio level, and asked for finalization.",
        "clean_export_changes": [
            "removed the red OWNER REVIEW DRAFT banner",
            "added a clean KIRA WORLD DEVELOPMENT UPDATE header",
            "preserved every CURRENT PROTOTYPE, BOUNDED STUDY, CONCEPT ART, and roadmap label",
        ],
        "voice_resynthesis_performed": False,
        "facebook_page_url_embedded": False,
        "posting_performed": False,
        "records": records,
        "thumbnails": thumbnails,
    }
    path = VIDEO_DIR / "final_video_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
