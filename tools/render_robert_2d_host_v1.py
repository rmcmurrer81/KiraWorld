"""Render the approved Robert illustration as a layered articulated 2D host."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(r"C:\Users\robmc\Kira\VideoStudioDevelopment\animated_robert_host_v1")
SHEET = ROOT / "ROBERT_2D_HOST_PARTS_CONTACT_SHEET.png"
FRAMES = ROOT / "frames"
FPS = 24
COUNT = 144


def crop(box: tuple[int, int, int, int]) -> Image.Image:
    image = Image.open(SHEET).convert("RGBA").crop(box)
    bounds = image.getbbox()
    return image.crop(bounds) if bounds else image


PARTS = {
    "head_front": crop((35, 15, 145, 160)),
    "head_3q_r": crop((180, 15, 320, 165)),
    "head_side_r": crop((325, 15, 455, 165)),
    "head_side_l": crop((460, 15, 585, 165)),
    "head_smile": crop((320, 165, 455, 310)),
    "head_talk_a": crop((25, 300, 170, 450)),
    "head_talk_e": crop((175, 300, 315, 450)),
    "head_talk_o": crop((320, 300, 455, 450)),
    "head_talk_u": crop((460, 300, 590, 450)),
    "head_blink": crop((295, 165, 430, 310)),
    "torso_front": crop((1295, 45, 1385, 245)),
    "torso_3q": crop((1435, 45, 1505, 245)),
    "torso_side": crop((1555, 45, 1625, 245)),
    "arm_upper_l": crop((800, 460, 890, 625)),
    "arm_upper_r": crop((1050, 460, 1145, 625)),
    "arm_lower_l": crop((805, 620, 890, 780)),
    "arm_lower_r": crop((1050, 620, 1140, 780)),
    "hand_open_l": crop((1195, 475, 1300, 555)),
    "hand_open_r": crop((1380, 475, 1485, 555)),
    "hand_point_l": crop((1190, 565, 1315, 650)),
    "hand_point_r": crop((1370, 565, 1500, 650)),
    "hand_type_l": crop((1180, 635, 1320, 715)),
    "hand_type_r": crop((1360, 635, 1510, 715)),
    "hand_script": crop((1170, 680, 1510, 800)),
    "hand_pen": crop((1230, 780, 1350, 875)),
    "pelvis": crop((20, 690, 175, 780)),
    "leg_l": crop((225, 690, 310, 925)),
    "leg_r": crop((575, 690, 645, 925)),
    "foot_l": crop((805, 785, 925, 925)),
    "foot_r": crop((1045, 785, 1180, 925)),
}


def fit(part: Image.Image, size: tuple[int, int]) -> Image.Image:
    copy = part.copy()
    copy.thumbnail(size, Image.Resampling.LANCZOS)
    return copy


def paste_rotated(canvas: Image.Image, part: Image.Image, center: tuple[float, float],
                  angle: float, size: tuple[int, int]) -> None:
    item = fit(part, size).rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
    canvas.alpha_composite(item, (round(center[0] - item.width / 2), round(center[1] - item.height / 2)))


def head_for(frame: int, view: str) -> Image.Image:
    if view == "side":
        return PARTS["head_side_r"]
    if view == "three_quarter":
        return PARTS["head_3q_r"]
    return PARTS["head_front"]


def render(action: str, frame: int) -> Image.Image:
    t = (frame - 1) / FPS
    cycle = math.sin(t * math.tau)
    canvas = Image.new("RGBA", (900, 900), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas, "RGBA")
    root_x, root_y = 450.0, 515.0
    view = "front"
    seated = action in {"sit", "typing", "writing"}
    if action == "walk":
        view = "side"
        root_x = 250 + 400 * (frame - 1) / (COUNT - 1)
        root_y += 10 * abs(cycle)
    elif action in {"sit", "stand"}:
        view = "three_quarter"
        progress = (frame - 1) / (COUNT - 1)
        if action == "stand":
            progress = 1 - progress
        root_y += 125 * min(1, max(0, progress))
    elif action in {"typing", "writing"}:
        view = "three_quarter"
        root_y += 120

    # Environment-contact props are drawn before the body.
    if action in {"sit", "stand", "typing", "writing"}:
        draw.rounded_rectangle((315, 690, 595, 725), 12, fill=(45, 48, 54, 255))
        draw.rectangle((335, 720, 360, 890), fill=(35, 38, 43, 255))
        draw.rectangle((550, 720, 575, 890), fill=(35, 38, 43, 255))
    if action in {"typing", "writing"}:
        draw.rounded_rectangle((515, 555, 855, 590), 8, fill=(78, 68, 58, 255))
        draw.rectangle((785, 585, 810, 890), fill=(55, 48, 43, 255))
    if action == "typing":
        draw.rounded_rectangle((590, 520, 780, 552), 6, fill=(25, 29, 36, 255))
        draw.rectangle((650, 330, 815, 515), fill=(24, 28, 35, 255))
        draw.rectangle((660, 340, 805, 490), fill=(31, 104 + int(30 * cycle), 145, 255))
    if action == "writing":
        draw.polygon(((575, 520), (770, 510), (785, 565), (590, 575)), fill=(244, 241, 228, 255))
        for y in range(530, 563, 9):
            draw.line((600, y, 750, y - 6), fill=(80, 90, 105, 170), width=2)

    # Joint-bridge underlay keeps the layered cutout visually continuous while
    # the independently animated artwork overlaps at neck, shoulders and hips.
    draw.rounded_rectangle((root_x - 82, root_y - 135, root_x + 82, root_y + 150),
                           32, fill=(25, 29, 33, 255))
    draw.ellipse((root_x - 32, root_y - 190, root_x + 32, root_y - 105),
                 fill=(222, 166, 125, 255))
    draw.rounded_rectangle((root_x - 90, root_y - 75, root_x + 90, root_y + 55),
                           26, fill=(26, 30, 34, 255))
    draw.rounded_rectangle((root_x - 78, root_y + 115, root_x + 78, root_y + 205),
                           24, fill=(24, 27, 31, 255))

    arm_swing = 24 * cycle if action == "walk" else 0
    leg_swing = 28 * cycle if action == "walk" else 0
    if action in {"gesture", "opening_wave", "presenter"}:
        arm_swing = 25 + 20 * math.sin(t * math.pi)
    if action == "acting_script":
        arm_swing = 18 + 8 * cycle

    torso = PARTS["torso_side" if view == "side" else "torso_3q" if view == "three_quarter" else "torso_front"]
    paste_rotated(canvas, PARTS["leg_l"], (root_x - 35, root_y + 230), leg_swing, (115, 275))
    paste_rotated(canvas, PARTS["leg_r"], (root_x + 35, root_y + 230), -leg_swing, (115, 275))
    paste_rotated(canvas, torso, (root_x, root_y), 2 * cycle, (235, 270))

    # Arms and hands are independent layers connected at shoulder/elbow/wrist.
    left_angle = -arm_swing
    right_angle = arm_swing
    if action in {"typing", "writing"}:
        amplitude = 12 if action == "writing" else 5
        left_angle, right_angle = -58 + amplitude * cycle, 58 - amplitude * cycle
    paste_rotated(canvas, PARTS["arm_upper_l"], (root_x - 92, root_y + 20), left_angle, (98, 210))
    paste_rotated(canvas, PARTS["arm_upper_r"], (root_x + 92, root_y + 20), right_angle, (98, 210))
    hand_l = PARTS["hand_open_l"]
    hand_r = PARTS["hand_open_r"]
    if action != "acting_script":
        paste_rotated(canvas, hand_l, (root_x - 125, root_y + 135), left_angle * .35, (75, 60))
        paste_rotated(canvas, hand_r, (root_x + 125, root_y + 135), right_angle * .35, (75, 60))
    if action == "writing":
        pen_draw = ImageDraw.Draw(canvas, "RGBA")
        px = root_x + 150 + 28 * math.sin(t * math.tau * 2)
        py = root_y + 108 + 7 * math.cos(t * math.tau * 2)
        pen_draw.line((px - 18, py + 16, px + 16, py - 18), fill=(45, 50, 62, 255), width=6)
        pen_draw.ellipse((px + 12, py - 22, px + 19, py - 15), fill=(180, 185, 195, 255))
    paste_rotated(canvas, head_for(frame, view), (root_x, root_y - 130 + 4 * cycle), 2 * cycle, (200, 190))
    face_draw = ImageDraw.Draw(canvas, "RGBA")
    mouth_x = root_x + (35 if view == "side" else 15 if view == "three_quarter" else 0)
    mouth_y = root_y - 92
    mouth_phase = (frame // 3) % 5
    if mouth_phase in (1, 3, 4):
        face_draw.ellipse((mouth_x - 9, mouth_y - 3, mouth_x + 9,
                           mouth_y + 4 + 3 * (mouth_phase == 4)),
                          fill=(55, 25, 22, 235))
    else:
        face_draw.line((mouth_x - 10, mouth_y, mouth_x + 10, mouth_y + 1),
                       fill=(55, 25, 22, 235), width=3)
    if frame % 83 in (0, 1, 2):
        face_draw.line((mouth_x - 25, mouth_y - 50, mouth_x - 5, mouth_y - 50),
                       fill=(45, 35, 30, 230), width=3)

    if action == "acting_script":
        prop = fit(PARTS["hand_script"], (280, 150))
        canvas.alpha_composite(prop, (round(root_x - prop.width / 2), round(root_y + 50)))
    return canvas


def main() -> None:
    actions = ["opening_wave", "acting_script", "writing", "walk", "sit",
               "typing", "gesture", "stand", "presenter"]
    for action in actions:
        folder = FRAMES / action
        folder.mkdir(parents=True, exist_ok=True)
        for frame in range(1, COUNT + 1):
            render(action, frame).save(folder / f"frame_{frame:04d}.png")
    spec = {
        "host_id": "animated_robert_host_v1",
        "medium": "layered articulated 2D cutout puppet",
        "design_authority": str(ROOT / "ROBERT_CARTOON_CHARACTER_SHEET_V2_APPROVED.png"),
        "parts_sheet": str(SHEET),
        "hierarchy": ["root", "pelvis", "torso", "neck", "head", "eyes", "mouth",
                      "shoulders", "upper_arms", "lower_arms", "wrists", "hands",
                      "upper_legs", "lower_legs", "ankles", "feet"],
        "views": ["front", "three-quarter-left", "three-quarter-right", "side-left", "side-right"],
        "mouth_shapes": ["closed-rest", "M-B-P", "A", "E", "O", "U-W", "F-V", "L",
                         "smile-talking", "open-emphasis"],
        "actions": actions,
        "avatar_builder_registration_allowed": False,
        "resident_body_registration_allowed": False
    }
    (ROOT / "ROBERT_2D_HOST_RIG_SPEC.json").write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
