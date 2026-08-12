"""Assemble the protected V20 engineering contact sheet."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
review = ROOT / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v20_local_pelvis_rebuild/private_review"
items = [
    ("FRONT — FULL BODY", "front.png"),
    ("REAR — FULL BODY", "rear.png"),
    ("LEFT PROFILE — FULL BODY", "left_profile.png"),
    ("RIGHT PROFILE — FULL BODY", "right_profile.png"),
    ("LEFT THREE-QUARTER", "left_three_quarter.png"),
    ("RIGHT THREE-QUARTER", "right_three_quarter.png"),
    ("CLOSE FACE", "close_face.png"),
    ("CLOSE PELVIS — FRONT", "close_pelvis_front.png"),
    ("CLOSE PELVIS — LEFT 3/4", "close_pelvis_left_three_quarter.png"),
    ("CLOSE PELVIS — RIGHT 3/4", "close_pelvis_right_three_quarter.png"),
    ("CLOSE PELVIS — SIDE", "close_pelvis_side.png"),
]
font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 25)
small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 18)
canvas = Image.new("RGB", (2000, 3260), (20, 22, 28))
draw = ImageDraw.Draw(canvas)
draw.text((55, 28), "BIOLOGICAL ROBERT — V20 LOCAL PELVIS REBUILD", fill=(245, 245, 248), font=font)
draw.text((55, 68), "PRIVATE ENGINEERING EVIDENCE • FAILED VISUAL/TOPOLOGY GATE • NOT OWNER-READY", fill=(255, 120, 90), font=small)
cell_w, cell_h = 480, 960
for index, (label, filename) in enumerate(items):
    row, col = divmod(index, 4)
    x, y = 35 + col * 490, 115 + row * 1010
    draw.text((x, y), label, fill=(235, 238, 244), font=small)
    image = Image.open(review / filename).convert("RGB")
    image.thumbnail((cell_w, cell_h - 45), Image.Resampling.LANCZOS)
    canvas.paste(image, (x + (cell_w - image.width) // 2, y + 40))
draw.text((55, 3215), "BLOCKED — LOCAL TRANSITION NOT SEAMLESS • no movement, runtime attachment, or activation", fill=(255, 120, 90), font=small)
canvas.save(review / "BIOLOGICAL_ROBERT_STATIC_CONTACT_SHEET_V20_FAILED_ENGINEERING.jpg", quality=94, subsampling=0)
