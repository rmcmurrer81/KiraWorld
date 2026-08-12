"""Create Avatar Builder silhouette overlay calibration artifacts.

This pass is intentionally not an approval pass. Robert rejected the previous
previews because the builder guessed at bodies, faces, hair, and eyes instead
of lining references up over a base model. This tool builds the reference
overlay sheets and a Blender calibration GLB so the next sculpt/fitting pass
has something concrete to align against.

Run image/manifest pass:
  py tools/run_avatar_builder_silhouette_overlay_pass_20260712.py

Run Blender calibration pass after the image pass:
  "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background --python tools/run_avatar_builder_silhouette_overlay_pass_20260712.py -- --blender-calibration-only
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.avatar_body_policy_gate import enforce_body_policy  # noqa: E402

AVATAR_TEMP = PROJECT_ROOT / "Avatar" / "temp_ai"
AVATAR_MODELS = PROJECT_ROOT / "Avatar" / "models" / "temp_ai"
BUILDER_ROOT = PROJECT_ROOT / "Avatar" / "avatar_builder"
OVERLAY_ROOT = BUILDER_ROOT / "body_training" / "overlay_passes" / "20260712_robert_f_grade"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
PASS_ID = "silhouette_overlay_pass_20260712"

MARINETTE_ID = "ladybug_marinette_expanded_smoke"
GWEN_ID = "spider_gwen_spider_gwen_20260606_013325"

CANDIDATES = {
    MARINETTE_ID: {
        "display_name": "Marinette / Ladybug",
        "maturity_policy": "non_adult_doll_safe",
        "adult_anatomy_references_allowed": False,
        "non_adult_barbie_treatment_allowed": True,
        "base_model": AVATAR_MODELS / MARINETTE_ID / "avatar_builder_base_body_pass_20260712.glb",
        "front_hint_terms": ("marinette_png", "guardian_ladybug", "reference_01", "reference_02"),
        "side_hint_terms": ("profile", "side", "sans_titre", "44fe", "b750"),
    },
    GWEN_ID: {
        "display_name": "Spider-Gwen",
        "maturity_policy": "adult",
        "adult_anatomy_references_allowed": True,
        "non_adult_barbie_treatment_allowed": False,
        "base_model": AVATAR_MODELS / GWEN_ID / "avatar_builder_base_body_pass_20260712.glb",
        "front_hint_terms": ("reference_01", "reference_03"),
        "side_hint_terms": ("reference_02", "profile", "side"),
        "chat_reference_memory": AVATAR_TEMP / GWEN_ID / "gwen_chat_reference_batch_20260712.json",
    },
}

MANUAL_REJECTIONS = {
    MARINETTE_ID: {
        "references/downloaded/reference_01.jpg": "Rejected after visual audit: this is a real-person singer/photo, not a Marinette body reference.",
    },
    GWEN_ID: {
        "references/downloaded/reference_01.jpg": "Rejected after visual audit: this is a real person signing comics, not a Gwen avatar/body reference.",
        "references/downloaded/reference_04.png": "Rejected after visual audit: unrelated comic-book/chibi graphic, not a Gwen body or face reference.",
    },
}


def validate_calibration_body_input(candidate_id: str) -> dict:
    meta = CANDIDATES[candidate_id]
    base_model = meta["base_model"]
    provenance = [base_model.with_suffix(".manifest.json")]
    if candidate_id == MARINETTE_ID:
        provenance.append(
            AVATAR_MODELS / MARINETTE_ID / "avatar_body_base_rebuild_v1.json"
        )
    return enforce_body_policy(
        project_root=PROJECT_ROOT,
        candidate_id=candidate_id,
        body_treatment=(
            "non_adult_doll_safe" if candidate_id == MARINETTE_ID else "neutral_adult_anatomy"
        ),
        selected_asset_paths=[base_model],
        provenance_manifests=provenance,
        expected_maturity_classes={meta["maturity_policy"]},
        require_asset_evidence=True,
    )

MANUAL_VIEW_PRIORITY = {
    MARINETTE_ID: {
        "front": {
            "marinette_png": 6.0,
            "guardian_ladybug": 5.0,
            "reference_02.png": 4.0,
            "miraculous_ladybug_marinette_sans_titre": 3.5,
        },
        "side": {
            "miraculous_ladybug_marinette_sans_titre": 4.0,
            "44fe3c1cffbba4ffead04d4e51a64ae2": 3.0,
            "b750ee423cf4ade118a3714fbc801e60": 2.5,
            "b56454c5f896f6b8e41803c7002b9485": 2.0,
        },
    },
    GWEN_ID: {
        "front": {
            "reference_02.jpg": 2.5,
            "reference_03.jpg": 1.4,
        },
        "side": {
            "reference_02.jpg": 2.5,
            "reference_03.jpg": 1.0,
        },
    },
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def preview_url(path: Path) -> str:
    return "/" + rel(path)


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default.copy() if isinstance(default, dict) else default


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


@dataclass
class ReferenceImage:
    path: Path
    width: int
    height: int
    front_score: float
    side_score: float
    body_score: float
    face_score: float


@dataclass
class MaskResult:
    small_mask: list[list[bool]]
    size: tuple[int, int]
    bbox: tuple[int, int, int, int]
    confidence: float
    method: str


def import_pillow():
    try:
        from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps
    except ImportError as exc:  # pragma: no cover - environment guard
        raise RuntimeError("Pillow is required for the image/silhouette overlay pass.") from exc
    return Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps


def collect_reference_images(candidate_id: str) -> list[ReferenceImage]:
    Image, *_ = import_pillow()
    root = AVATAR_TEMP / candidate_id / "references"
    hints = CANDIDATES[candidate_id]
    rejections = MANUAL_REJECTIONS.get(candidate_id, {})
    priorities = MANUAL_VIEW_PRIORITY.get(candidate_id, {})
    images: list[ReferenceImage] = []
    if not root.exists():
        return images

    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        rel_path = path.as_posix().lower()
        if any(pattern.lower() in rel_path for pattern in rejections):
            continue
        try:
            with Image.open(path) as img:
                width, height = img.size
        except Exception:
            continue
        if width < 120 or height < 120 or path.stat().st_size < 2000:
            continue
        name = path.name.lower()
        ratio = height / max(width, 1)
        body_score = 0.0
        if ratio > 1.35:
            body_score += 2.4
        if height >= 650:
            body_score += 0.8
        if width <= 550 and ratio > 1.55:
            body_score += 0.7
        if "fullview" in name or "guardian" in name:
            body_score += 1.2

        face_score = 0.0
        if 0.75 <= ratio <= 1.35:
            face_score += 1.0
        if width >= 600 and height >= 400:
            face_score += 0.5

        front_score = body_score
        side_score = 0.0
        for term in hints.get("front_hint_terms", ()):
            if term in name:
                front_score += 2.0
        for term in hints.get("side_hint_terms", ()):
            if term in name:
                side_score += 2.0
        for term, boost in priorities.get("front", {}).items():
            if term in name:
                front_score += boost
        for term, boost in priorities.get("side", {}).items():
            if term in name:
                side_score += boost
        if 0.45 <= ratio <= 1.2:
            side_score += 0.7
        if candidate_id == MARINETTE_ID and width > height and "profile" not in name and "side" not in name:
            side_score -= 3.0
        if "profile" in str(path).lower() or "side" in str(path).lower():
            side_score += 2.0

        images.append(ReferenceImage(path, width, height, front_score, side_score, body_score, face_score))
    return images


def rejected_reference_records(candidate_id: str) -> list[dict]:
    root = AVATAR_TEMP / candidate_id / "references"
    records: list[dict] = []
    for pattern, reason in MANUAL_REJECTIONS.get(candidate_id, {}).items():
        matches = [path for path in root.rglob("*") if pattern.lower() in path.as_posix().lower()]
        for path in matches:
            records.append({"source": rel(path), "reason": reason})
    return records


def _median_corner_color(rgb) -> tuple[int, int, int]:
    width, height = rgb.size
    pixels: list[tuple[int, int, int]] = []
    sample = max(8, min(width, height) // 18)
    boxes = [
        (0, 0, sample, sample),
        (width - sample, 0, width, sample),
        (0, height - sample, sample, height),
        (width - sample, height - sample, width, height),
    ]
    for box in boxes:
        crop = rgb.crop(box)
        pixels.extend(list(crop.getdata())[:: max(1, len(crop.getdata()) // 64)])
    return tuple(int(median(channel)) for channel in zip(*pixels))


def _largest_center_component(mask: list[list[bool]]) -> tuple[list[list[bool]], tuple[int, int, int, int], float]:
    height = len(mask)
    width = len(mask[0]) if height else 0
    visited = [[False] * width for _ in range(height)]
    best_cells: list[tuple[int, int]] = []
    best_score = -1.0
    center_x = width * 0.5
    center_y = height * 0.5
    for start_y in range(height):
        for start_x in range(width):
            if visited[start_y][start_x] or not mask[start_y][start_x]:
                continue
            cells: list[tuple[int, int]] = []
            queue: deque[tuple[int, int]] = deque([(start_x, start_y)])
            visited[start_y][start_x] = True
            min_x = max_x = start_x
            min_y = max_y = start_y
            while queue:
                x, y = queue.popleft()
                cells.append((x, y))
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)
                for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                    if 0 <= nx < width and 0 <= ny < height and not visited[ny][nx] and mask[ny][nx]:
                        visited[ny][nx] = True
                        queue.append((nx, ny))
            if len(cells) < 12:
                continue
            comp_cx = (min_x + max_x) * 0.5
            comp_cy = (min_y + max_y) * 0.5
            distance = math.hypot((comp_cx - center_x) / max(width, 1), (comp_cy - center_y) / max(height, 1))
            score = len(cells) * (1.0 - min(0.85, distance))
            if score > best_score:
                best_score = score
                best_cells = cells
                best_bbox = (min_x, min_y, max_x + 1, max_y + 1)
    out = [[False] * width for _ in range(height)]
    for x, y in best_cells:
        out[y][x] = True
    if not best_cells:
        return out, (0, 0, width, height), 0.0
    area = len(best_cells) / max(1, width * height)
    bbox_area = ((best_bbox[2] - best_bbox[0]) * (best_bbox[3] - best_bbox[1])) / max(1, width * height)
    confidence = max(0.0, min(1.0, area * 3.2 + (0.45 if 0.05 <= bbox_area <= 0.70 else 0.0)))
    touches_edges = (
        best_bbox[0] <= 1
        and best_bbox[1] <= 1
        and best_bbox[2] >= width - 1
        and best_bbox[3] >= height - 1
    )
    if bbox_area > 0.82 or touches_edges:
        confidence = min(confidence, 0.28)
    return out, best_bbox, confidence


def estimate_subject_mask(path: Path, max_size: int = 260) -> MaskResult:
    Image, ImageChops, _, ImageFilter, _, _ = import_pillow()
    with Image.open(path) as original:
        rgba = original.convert("RGBA")
        alpha = rgba.getchannel("A")
        if alpha.getextrema()[0] < 250:
            small_alpha = alpha.copy()
            small_alpha.thumbnail((max_size, max_size))
            small_alpha = small_alpha.filter(ImageFilter.MedianFilter(size=3))
            width, height = small_alpha.size
            raw = list(small_alpha.getdata())
            mask = [[raw[y * width + x] > 32 for x in range(width)] for y in range(height)]
            component, bbox, confidence = _largest_center_component(mask)
            return MaskResult(component, (width, height), bbox, max(confidence, 0.80), "alpha_channel")

        rgb = rgba.convert("RGB")
        rgb.thumbnail((max_size, max_size))
        rgb = rgb.filter(ImageFilter.MedianFilter(size=3))
        width, height = rgb.size
        bg = _median_corner_color(rgb)
        pixels = list(rgb.getdata())
        raw_mask: list[list[bool]] = []
        for y in range(height):
            row: list[bool] = []
            for x in range(width):
                r, g, b = pixels[y * width + x]
                color_distance = abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2])
                saturation = max(r, g, b) - min(r, g, b)
                brightness = r + g + b
                near_center_weight = 1.0 - min(0.55, abs(x - width * 0.5) / max(width, 1))
                threshold = 72 - 18 * near_center_weight
                row.append(color_distance > threshold and (saturation > 18 or brightness < 690))
            raw_mask.append(row)
        component, bbox, confidence = _largest_center_component(raw_mask)
        return MaskResult(component, (width, height), bbox, confidence, "corner_background_center_component")


def mask_to_image(mask_result: MaskResult, fill=(0, 0, 0, 220)):
    Image, *_ = import_pillow()
    width, height = mask_result.size
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pixels = img.load()
    for y, row in enumerate(mask_result.small_mask):
        for x, value in enumerate(row):
            if value:
                pixels[x, y] = fill
    return img


def fit_image(image, box: tuple[int, int], background=(255, 255, 255, 255)):
    Image, *_ = import_pillow()
    canvas = Image.new("RGBA", box, background)
    copy = image.copy()
    copy.thumbnail(box)
    x = (box[0] - copy.width) // 2
    y = (box[1] - copy.height) // 2
    canvas.alpha_composite(copy.convert("RGBA"), (x, y))
    return canvas


def draw_label(draw, xy: tuple[int, int], text: str) -> None:
    _, _, ImageDraw, _, ImageFont, _ = import_pillow()
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except Exception:
        font = ImageFont.load_default()
    draw.text(xy, text, fill=(15, 31, 46), font=font)


def make_contact_sheet(
    candidate_id: str,
    label: str,
    references: list[ReferenceImage],
    out_path: Path,
    view: str,
) -> list[dict]:
    Image, ImageChops, ImageDraw, ImageFilter, _, _ = import_pillow()
    tile_w, tile_h = 340, 500
    columns = 3
    rows = max(1, math.ceil(len(references) / columns))
    sheet = Image.new("RGBA", (columns * tile_w, rows * tile_h + 70), (244, 248, 250, 255))
    draw = ImageDraw.Draw(sheet)
    draw_label(draw, (18, 18), f"{label} {view} overlay candidates - references only, not copied bodies")
    records: list[dict] = []
    for index, ref in enumerate(references):
        x0 = (index % columns) * tile_w
        y0 = 70 + (index // columns) * tile_h
        with Image.open(ref.path) as img:
            original = fit_image(img.convert("RGBA"), (tile_w - 24, 285), (255, 255, 255, 255))
        mask = estimate_subject_mask(ref.path)
        mask_img = mask_to_image(mask)
        outline = ImageChops.difference(mask_img.filter(ImageFilter.MaxFilter(5)), mask_img.filter(ImageFilter.MinFilter(5)))
        silhouette = Image.new("RGBA", mask_img.size, (255, 255, 255, 255))
        silhouette.alpha_composite(mask_img)
        outline_colored = Image.new("RGBA", outline.size, (210, 35, 45, 0))
        outline_colored.putalpha(outline.getchannel("A"))
        silhouette.alpha_composite(outline_colored)
        silhouette = fit_image(silhouette, (tile_w - 24, 145), (255, 255, 255, 255))

        sheet.alpha_composite(original, (x0 + 12, y0 + 10))
        sheet.alpha_composite(silhouette, (x0 + 12, y0 + 305))
        short = ref.path.name[:44]
        draw_label(draw, (x0 + 12, y0 + 456), f"{index + 1}. {short}")
        draw_label(draw, (x0 + 12, y0 + 476), f"mask {mask.confidence:.2f} | {mask.method}")
        records.append({
            "index": index + 1,
            "source": rel(ref.path),
            "width": ref.width,
            "height": ref.height,
            "front_score": round(ref.front_score, 3),
            "side_score": round(ref.side_score, 3),
            "body_score": round(ref.body_score, 3),
            "face_score": round(ref.face_score, 3),
            "mask_confidence": round(mask.confidence, 3),
            "mask_method": mask.method,
            "mask_bbox_small": list(mask.bbox),
        })
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(out_path)
    return records


def make_silhouette_stack(references: list[ReferenceImage], out_path: Path, view: str) -> dict:
    Image, ImageChops, _, ImageFilter, _, _ = import_pillow()
    canvas_w, canvas_h = 900, 1320
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (255, 255, 255, 0))
    colors = [
        (20, 70, 200, 78),
        (210, 40, 65, 76),
        (20, 145, 105, 74),
        (220, 155, 20, 70),
        (80, 50, 160, 68),
        (30, 30, 30, 60),
    ]
    used: list[dict] = []
    aggregate_bbox = [canvas_w, canvas_h, 0, 0]
    for index, ref in enumerate(references[:6]):
        mask = estimate_subject_mask(ref.path)
        mask_img = mask_to_image(mask, colors[index % len(colors)])
        x1, y1, x2, y2 = mask.bbox
        crop = mask_img.crop((x1, y1, max(x2, x1 + 1), max(y2, y1 + 1)))
        target_h = 1080 if view == "front" else 1000
        scale = target_h / max(crop.height, 1)
        target_w = max(1, int(crop.width * scale))
        if target_w > 780:
            shrink = 780 / target_w
            target_w = 780
            target_h = max(1, int(target_h * shrink))
        resized = crop.resize((target_w, target_h))
        x = (canvas_w - target_w) // 2
        y = canvas_h - target_h - 80
        canvas.alpha_composite(resized, (x, y))
        aggregate_bbox[0] = min(aggregate_bbox[0], x)
        aggregate_bbox[1] = min(aggregate_bbox[1], y)
        aggregate_bbox[2] = max(aggregate_bbox[2], x + target_w)
        aggregate_bbox[3] = max(aggregate_bbox[3], y + target_h)
        used.append({
            "source": rel(ref.path),
            "mask_confidence": round(mask.confidence, 3),
            "normalized_width": target_w,
            "normalized_height": target_h,
            "canvas_position": [x, y],
        })

    guide = Image.new("RGBA", (canvas_w, canvas_h), (255, 255, 255, 0))
    guide_outline = Image.new("RGBA", (canvas_w, canvas_h), (30, 35, 40, 0))
    alpha = canvas.getchannel("A")
    outline = ImageChops.difference(alpha.filter(ImageFilter.MaxFilter(9)), alpha.filter(ImageFilter.MinFilter(9)))
    guide_outline.putalpha(outline)
    guide.alpha_composite(canvas)
    guide.alpha_composite(guide_outline)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    guide.save(out_path)
    if aggregate_bbox[2] <= aggregate_bbox[0] or aggregate_bbox[3] <= aggregate_bbox[1]:
        aggregate_bbox = [0, 0, canvas_w, canvas_h]
    return {
        "output": rel(out_path),
        "used_sources": used,
        "canvas_size": [canvas_w, canvas_h],
        "aggregate_bbox": aggregate_bbox,
        "aggregate_width_height_ratio": round((aggregate_bbox[2] - aggregate_bbox[0]) / max(1, aggregate_bbox[3] - aggregate_bbox[1]), 4),
    }


def pick_references(candidate_id: str, images: list[ReferenceImage]) -> tuple[list[ReferenceImage], list[ReferenceImage]]:
    if candidate_id == MARINETTE_ID:
        front_candidates = [item for item in images if item.front_score >= 4.0]
    else:
        front_candidates = [item for item in images if item.body_score >= 1.8 or item.front_score >= 3.0]
    front = sorted(front_candidates or images, key=lambda item: (item.front_score, item.body_score, item.height), reverse=True)[:6]
    side_candidates = [
        item
        for item in images
        if item.side_score > 0 and (candidate_id != MARINETTE_ID or item.width <= item.height or "profile" in item.path.name.lower() or "side" in item.path.name.lower())
    ]
    side_pool = sorted(side_candidates or images, key=lambda item: (item.side_score, item.face_score, item.width), reverse=True)
    side: list[ReferenceImage] = []
    front_paths = {item.path for item in front[:3]}
    for item in side_pool:
        if item.path not in front_paths or len(side) < 2:
            side.append(item)
        if len(side) >= 6:
            break
    if candidate_id == GWEN_ID and len(images) <= 4:
        front = sorted(images, key=lambda item: item.front_score, reverse=True)[:3]
        side = sorted(images, key=lambda item: item.side_score, reverse=True)[:3]
    return front, side[:6]


def update_adjustments(candidate_id: str, pass_manifest: Path, generated: dict) -> None:
    path = AVATAR_TEMP / candidate_id / "avatar_builder_adjustments.json"
    data = read_json(path, {"schema_version": 1, "candidate_id": candidate_id, "builder": "avatar_builder"})
    data["updated_at"] = now_iso()
    data["approval_status"] = "silhouette_overlay_calibration_ready_failed_likeness"
    data["silhouette_overlay_pass_manifest"] = rel(pass_manifest)
    data["silhouette_overlay_pass"] = generated
    data["silhouette_overlay_required_before_likeness_claim"] = True
    data["current_likeness_claim"] = "failed_not_approved"
    data["builder_overlay_calibration_model_url"] = generated.get("calibration_model_url", "")
    data["learning_notes"] = data.get("learning_notes", [])
    data["learning_notes"].append({
        "created_at": now_iso(),
        "tags": ["avatar_builder", "silhouette_overlay", "robert_big_f", "not_approved"],
        "text": (
            "Robert rejected the previous preview. This pass creates front/side overlay sheets and a "
            "calibration model so the next sculpt pass aligns the base body to references before claiming likeness."
        ),
    })
    targets = data.setdefault("build_targets", [])
    target_text = "Use the generated front/side silhouette overlay sheets to reshape the base body/head before any new likeness claim."
    if not any(item.get("instruction") == target_text for item in targets if isinstance(item, dict)):
        targets.append({
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "area": "silhouette_overlay_sculpt",
            "source": "Robert correction",
            "instruction": target_text,
            "status": "queued_for_builder_review",
        })
    write_json(path, data)


def build_image_pass_for_candidate(candidate_id: str) -> dict:
    meta = CANDIDATES[candidate_id]
    out_dir = OVERLAY_ROOT / candidate_id
    images = collect_reference_images(candidate_id)
    front_refs, side_refs = pick_references(candidate_id, images)
    front_sheet = out_dir / f"{candidate_id}_front_reference_sheet.png"
    side_sheet = out_dir / f"{candidate_id}_side_reference_sheet.png"
    front_stack = out_dir / f"{candidate_id}_front_silhouette_stack.png"
    side_stack = out_dir / f"{candidate_id}_side_silhouette_stack.png"
    front_records = make_contact_sheet(candidate_id, meta["display_name"], front_refs, front_sheet, "front/body")
    side_records = make_contact_sheet(candidate_id, meta["display_name"], side_refs, side_sheet, "side/profile")
    front_stack_info = make_silhouette_stack(front_refs, front_stack, "front")
    side_stack_info = make_silhouette_stack(side_refs, side_stack, "side")
    chat_reference_memory = meta.get("chat_reference_memory")
    generated = {
        "pass_id": PASS_ID,
        "candidate_id": candidate_id,
        "created_at": now_iso(),
        "status": "overlay_images_ready_calibration_glb_pending",
        "display_name": meta["display_name"],
        "maturity_policy": meta["maturity_policy"],
        "adult_anatomy_references_allowed": meta["adult_anatomy_references_allowed"],
        "non_adult_barbie_treatment_allowed": meta["non_adult_barbie_treatment_allowed"],
        "base_model": rel(meta["base_model"]),
        "reference_image_count": len(images),
        "rejected_reference_images": rejected_reference_records(candidate_id),
        "source_set_quality": (
            "insufficient_local_images_for_gwen_use_chat_refs_or_save_new_images"
            if candidate_id == GWEN_ID
            else "usable_first_overlay_set_needs_human_review"
        ),
        "front_reference_sheet": rel(front_sheet),
        "side_reference_sheet": rel(side_sheet),
        "front_silhouette_stack": front_stack_info,
        "side_silhouette_stack": side_stack_info,
        "front_selected_sources": front_records,
        "side_selected_sources": side_records,
        "guide_links_recorded": [
            "https://www.3dart.it/head-sculpt-in-blender-tutorial/",
            "https://yelzkizi.org/2d-image-to-3d-model-in-blender-guide/",
        ],
        "strict_notes": [
            "Reference models and images are guides only; no candidate body may be copied from them.",
            "This is not an approved likeness or runtime replacement.",
            "Round eye mechanics from the previous pass must stay; eyes must be seated in the head, not flat plates.",
            "Only Marinette uses non-adult doll-safe treatment. Gwen remains adult and may use adult anatomy references in neutral modeling context.",
        ],
        "next_required_builder_step": (
            "Load the front and side silhouette stacks as image planes over the base model in Blender, "
            "then reshape head/body/hair using proportional/lattice/sculpt controls before generating a new preview."
        ),
    }
    if chat_reference_memory and chat_reference_memory.exists():
        generated["chat_reference_memory"] = rel(chat_reference_memory)
        generated["chat_reference_limitation"] = (
            "Robert's newer chat-uploaded Gwen images are recorded here as guidance, but the raw files are not "
            "available on disk yet, so this automated image sheet used the local downloaded Gwen references."
        )
    manifest = out_dir / f"{candidate_id}_{PASS_ID}.json"
    write_json(manifest, generated)
    update_adjustments(candidate_id, manifest, generated)
    return {"candidate_id": candidate_id, "manifest": rel(manifest), "artifacts": generated}


def run_image_pass() -> int:
    results = [build_image_pass_for_candidate(candidate_id) for candidate_id in (MARINETTE_ID, GWEN_ID)]
    index_path = OVERLAY_ROOT / f"{PASS_ID}_index.json"
    write_json(index_path, {
        "schema_version": 1,
        "created_at": now_iso(),
        "status": "overlay_images_ready_calibration_glb_pending",
        "pass_id": PASS_ID,
        "results": results,
    })
    print(json.dumps({"ok": True, "index": rel(index_path), "results": results}, indent=2))
    return 0


def _clear_scene(bpy) -> None:
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def _scene_bounds(bpy, mathutils):
    points = []
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            points.append(obj.matrix_world @ mathutils.Vector(corner))
    if not points:
        return mathutils.Vector((0, 0, 0)), mathutils.Vector((0, 0, 0))
    return (
        mathutils.Vector(min(point[index] for point in points) for index in range(3)),
        mathutils.Vector(max(point[index] for point in points) for index in range(3)),
    )


def _normalize_scene(bpy, mathutils, target_height: float) -> None:
    low, high = _scene_bounds(bpy, mathutils)
    height = max(high.z - low.z, 0.001)
    center = mathutils.Vector(((low.x + high.x) * 0.5, (low.y + high.y) * 0.5, low.z))
    scale = target_height / height
    for obj in list(bpy.context.scene.objects):
        if obj.parent is None:
            obj.location = (obj.location - center) * scale
            obj.scale *= scale
    bpy.context.view_layer.update()


def _remove_unmaterialized_helper_meshes(bpy) -> list[str]:
    removed: list[str] = []
    for obj in list(bpy.context.scene.objects):
        lowered = obj.name.lower()
        if obj.type == "MESH" and lowered.startswith(("icosphere", "sphere")) and not obj.data.materials:
            removed.append(obj.name)
            bpy.data.objects.remove(obj, do_unlink=True)
    return removed


def _make_image_plane_material(bpy, name: str, image_path: Path):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.blend_method = "BLEND"
    mat.show_transparent_back = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    image = bpy.data.images.load(str(image_path))
    image.alpha_mode = "STRAIGHT"
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    mat.node_tree.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    bsdf.inputs["Alpha"].default_value = 0.56
    return mat


def _add_overlay_plane(bpy, name: str, material, location, rotation, scale) -> None:
    bpy.ops.mesh.primitive_plane_add(size=1, location=location, rotation=rotation)
    plane = bpy.context.object
    plane.name = name
    plane.data.name = f"{name}_mesh"
    plane.scale = scale
    plane.data.materials.append(material)
    plane["avatar_builder_overlay_role"] = "reference_image_plane_not_body"


def build_calibration_for_candidate(candidate_id: str) -> dict:
    import bpy  # type: ignore
    import mathutils  # type: ignore

    meta = CANDIDATES[candidate_id]
    manifest_path = OVERLAY_ROOT / candidate_id / f"{candidate_id}_{PASS_ID}.json"
    manifest = read_json(manifest_path, {})
    if not manifest:
        raise RuntimeError(f"Image pass manifest missing for {candidate_id}: {manifest_path}")
    base_model = meta["base_model"]
    body_policy_gate = validate_calibration_body_input(candidate_id)
    front_stack = PROJECT_ROOT / manifest["front_silhouette_stack"]["output"]
    side_stack = PROJECT_ROOT / manifest["side_silhouette_stack"]["output"]
    output = AVATAR_MODELS / candidate_id / "avatar_builder_silhouette_overlay_calibration_20260712.glb"

    _clear_scene(bpy)
    bpy.ops.import_scene.gltf(filepath=str(base_model))
    removed_helpers = _remove_unmaterialized_helper_meshes(bpy)
    _normalize_scene(bpy, mathutils, 1.65 if candidate_id == GWEN_ID else 1.36)
    front_mat = _make_image_plane_material(bpy, f"{candidate_id}_front_silhouette_overlay_material", front_stack)
    side_mat = _make_image_plane_material(bpy, f"{candidate_id}_side_silhouette_overlay_material", side_stack)
    _add_overlay_plane(
        bpy,
        f"{candidate_id}_front_silhouette_overlay_image_plane",
        front_mat,
        (0.0, 0.22, 0.70 if candidate_id == MARINETTE_ID else 0.84),
        (math.radians(90), 0, 0),
        (0.62, 0.92, 1.0),
    )
    _add_overlay_plane(
        bpy,
        f"{candidate_id}_side_silhouette_overlay_image_plane",
        side_mat,
        (0.48, 0.0, 0.70 if candidate_id == MARINETTE_ID else 0.84),
        (0, math.radians(90), 0),
        (0.62, 0.92, 1.0),
    )
    bpy.context.scene["avatar_builder_status"] = "silhouette_overlay_calibration_ready_failed_likeness"
    bpy.context.scene["avatar_builder_note"] = "Calibration/reference overlay only. Do not promote to runtime body."
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(
        filepath=str(output),
        export_format="GLB",
        export_apply=True,
        export_yup=True,
        export_animations=False,
        export_morph=True,
    )
    low, high = _scene_bounds(bpy, mathutils)
    calibration = {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "created_at": now_iso(),
        "status": "silhouette_overlay_calibration_ready_failed_likeness",
        "output_model": rel(output),
        "output_model_url": preview_url(output),
        "source_manifest": rel(manifest_path),
        "base_model": rel(base_model),
        "body_policy_validation": body_policy_gate,
        "front_overlay": rel(front_stack),
        "side_overlay": rel(side_stack),
        "removed_helper_meshes": removed_helpers,
        "scene_bounds": {"low": list(low), "high": list(high)},
        "not_runtime_body": True,
        "not_approved_likeness": True,
    }
    calibration_path = output.with_suffix(".manifest.json")
    write_json(calibration_path, calibration)
    manifest["status"] = "silhouette_overlay_calibration_ready_failed_likeness"
    manifest["calibration_model"] = rel(output)
    manifest["calibration_model_url"] = preview_url(output)
    manifest["calibration_manifest"] = rel(calibration_path)
    manifest["updated_at"] = now_iso()
    write_json(manifest_path, manifest)
    update_adjustments(candidate_id, manifest_path, manifest)
    return {"candidate_id": candidate_id, "output": rel(output), "manifest": rel(calibration_path)}


def run_blender_calibration_pass() -> int:
    validate_calibration_body_input(MARINETTE_ID)
    validate_calibration_body_input(GWEN_ID)
    results = [build_calibration_for_candidate(candidate_id) for candidate_id in (MARINETTE_ID, GWEN_ID)]
    index_path = OVERLAY_ROOT / f"{PASS_ID}_calibration_index.json"
    write_json(index_path, {
        "schema_version": 1,
        "created_at": now_iso(),
        "status": "silhouette_overlay_calibration_ready_failed_likeness",
        "pass_id": PASS_ID,
        "results": results,
    })
    print(json.dumps({"ok": True, "index": rel(index_path), "results": results}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blender-calibration-only", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else None)
    if args.blender_calibration_only:
        return run_blender_calibration_pass()
    return run_image_pass()


if __name__ == "__main__":
    raise SystemExit(main())
