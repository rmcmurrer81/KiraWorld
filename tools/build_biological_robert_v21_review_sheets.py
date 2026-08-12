"""Build V21 protected contact and V15 comparison sheets."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v21_bounded_local_repair"
REVIEW = BASE / "private_review"
DIAG = BASE / "diagnostics"
font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 24)
small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 17)

def sheet(path, title, entries, columns=3, cell=(620, 820)):
    rows = (len(entries) + columns - 1) // columns
    canvas = Image.new("RGB", (columns * cell[0], 90 + rows * cell[1]), (22, 24, 30))
    draw = ImageDraw.Draw(canvas)
    draw.text((30, 24), title, fill=(245, 245, 248), font=font)
    for i, (label, source) in enumerate(entries):
        row, col = divmod(i, columns)
        x, y = col * cell[0], 90 + row * cell[1]
        draw.text((x + 20, y + 8), label, fill=(240, 195, 95), font=small)
        image = Image.open(source).convert("RGB")
        image.thumbnail((cell[0] - 30, cell[1] - 55), Image.Resampling.LANCZOS)
        canvas.paste(image, (x + (cell[0] - image.width) // 2, y + 45))
    canvas.save(path, quality=94, subsampling=0)

standard = [
    ("FRONT", REVIEW / "front.png"), ("REAR", REVIEW / "rear.png"),
    ("LEFT PROFILE", REVIEW / "left_profile.png"), ("RIGHT PROFILE", REVIEW / "right_profile.png"),
    ("LEFT 3/4", REVIEW / "left_three_quarter.png"), ("RIGHT 3/4", REVIEW / "right_three_quarter.png"),
    ("FACE", REVIEW / "close_face.png"), ("LOCAL FRONT", REVIEW / "close_pelvis_front.png"),
    ("LOCAL LEFT 3/4", REVIEW / "close_pelvis_left_three_quarter.png"),
    ("LOCAL RIGHT 3/4", REVIEW / "close_pelvis_right_three_quarter.png"),
    ("LOCAL SIDE", REVIEW / "close_pelvis_side.png"),
]
sheet(REVIEW / "BIOLOGICAL_ROBERT_V21_PROTECTED_CONTACT_SHEET_FAILED_GATE.jpg",
      "BIOLOGICAL ROBERT V21 — BLOCKED ENGINEERING CANDIDATE", standard)

hand_entries = []
for view in ("hands_front", "hands_rear"):
    hand_entries += [(f"V15 {view}", DIAG / f"v15_{view}.png"), (f"V21 {view}", DIAG / f"v21_{view}.png")]
sheet(DIAG / "V15_V21_HAND_FINGER_COMPARISON.jpg", "V15 vs V21 — HAND/FINGER PRESERVATION", hand_entries, 2, (800, 720))

thigh_entries = []
for view in ("upper_thighs_front", "upper_thighs_rear", "upper_thighs_side"):
    thigh_entries += [(f"V15 {view}", DIAG / f"v15_{view}.png"), (f"V21 {view}", DIAG / f"v21_{view}.png")]
sheet(DIAG / "V15_V21_UPPER_LEG_COMPARISON.jpg", "V15 vs V21 — UPPER-LEG COMPARISON", thigh_entries, 2, (800, 720))
