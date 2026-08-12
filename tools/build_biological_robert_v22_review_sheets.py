"""Build protected V22 blocked-review contact sheets."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v22_protected_bridge_rebuild"
R=BASE/"private_review";D=BASE/"diagnostics"
font=ImageFont.truetype("C:/Windows/Fonts/arial.ttf",22);small=ImageFont.truetype("C:/Windows/Fonts/arial.ttf",16)
def build(path,title,items,cols=3):
    cw,ch=600,760;rows=(len(items)+cols-1)//cols;canvas=Image.new("RGB",(cw*cols,85+ch*rows),(20,22,28));draw=ImageDraw.Draw(canvas);draw.text((25,22),title,fill=(255,150,100),font=font)
    for i,(label,p) in enumerate(items):
        row,col=divmod(i,cols);x,y=col*cw,85+row*ch;draw.text((x+18,y+8),label,fill=(240,240,245),font=small)
        image=Image.open(p).convert("RGB");image.thumbnail((cw-25,ch-50),Image.Resampling.LANCZOS);canvas.paste(image,(x+(cw-image.width)//2,y+42))
    canvas.save(path,quality=94,subsampling=0)
standard=[(name.replace("_"," ").upper(),R/f"{name}.png") for name in ("front","rear","left_profile","right_profile","left_three_quarter","right_three_quarter","close_face","close_pelvis_front","close_pelvis_left_three_quarter","close_pelvis_right_three_quarter","close_pelvis_side")]
build(R/"BIOLOGICAL_ROBERT_V22_BLOCKED_CONTACT_SHEET.jpg","V22 — BLOCKED: MEDICAL-FORM/BRIDGE/HAND GATES INCOMPLETE",standard)
diag=[(name.replace("_"," ").upper(),D/f"{name}.png") for name in ("local_front_flat","local_side_flat","local_three_quarter_flat","local_rear_perineal","local_wireframe","normal_direction","albedo_only","roughness_only","material_id","hair_front","hair_side","hair_three_quarter","hands_nails_front","hands_nails_rear")]
build(D/"BIOLOGICAL_ROBERT_V22_DIAGNOSTIC_SHEET.jpg","V22 DIAGNOSTICS — ENGINEERING EVIDENCE ONLY",diag)
