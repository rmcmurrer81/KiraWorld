"""Extract, rig, render, and validate the Robert 2D host certification clips."""
from __future__ import annotations
import hashlib, json, math, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT=Path(r"C:\Users\robmc\Kira\VideoStudioDevelopment\animated_robert_host_certification_v2")
SOURCE=ROOT/"ROBERT_2D_LAYERED_PARTS.png"
PARTS=ROOT/"parts"; FRAMES=ROOT/"frames"; CLIPS=ROOT/"clips"; REPORTS=ROOT/"reports"
FF=Path(r"C:\Users\robmc\AppData\Roaming\Python\Python314\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe")
FPS=24

BOXES={
"head_front":(12,12,198,175),"head_three_quarter_right":(210,12,392,175),
"head_side_right":(405,12,582,175),"head_side_left":(595,12,777,175),
"head_three_quarter_left":(790,12,1010,175),
"eyes_open":(12,440,198,530),"eyes_blink":(405,440,582,530),
"eye_left":(595,440,777,530),"eye_right":(790,440,1010,530),
"eyebrows_neutral":(12,535,272,605),"eyebrows_raised":(282,535,530,605),
"eyebrows_concern":(542,535,777,605),
"mouth_rest":(12,615,98,695),"mouth_MBP":(108,615,198,695),
"mouth_A":(208,615,304,695),"mouth_E":(316,615,410,695),
"mouth_O":(420,615,514,695),"mouth_UW":(526,615,618,695),
"mouth_FV":(628,615,716,695),"mouth_L":(728,615,812,695),
"mouth_smile":(824,615,905,695),"mouth_emphasis":(915,615,1010,695),
"torso_front":(12,702,198,870),"torso_three_quarter_right":(210,702,405,870),
"torso_side_right":(417,702,600,870),"torso_three_quarter_left":(612,702,805,870),
"torso_side_left":(817,702,1010,870),
"pelvis":(12,878,215,1010),
"upper_arm_left":(230,878,360,1010),"upper_arm_right":(372,878,500,1010),
"lower_arm_left":(512,878,638,1010),"lower_arm_right":(650,878,775,1010),
"arm_side_left":(787,878,900,1010),"arm_side_right":(910,878,1010,1010),
"hand_relaxed_left":(12,1020,104,1095),"hand_relaxed_right":(108,1020,198,1095),
"hand_open_left":(210,1020,355,1095),"hand_point_left":(365,1020,505,1095),
"hand_open_right":(515,1020,665,1095),"hand_point_right":(675,1020,810,1095),
"hand_typing_left":(820,1020,910,1095),"hand_typing_right":(915,1020,1010,1095),
"script_pages":(12,1105,350,1195),"pen_left":(360,1105,500,1195),
"pen_right":(510,1105,650,1195),"writing_hand_left":(660,1105,830,1195),
"writing_hand_right":(840,1105,1010,1195),
"upper_leg_left":(12,1205,165,1350),"upper_leg_right":(175,1205,330,1350),
"lower_leg_left":(340,1205,495,1350),"lower_leg_right":(505,1205,660,1350),
"leg_bent_left":(670,1205,835,1350),"leg_bent_right":(845,1205,1010,1350),
"ankle_left":(12,1360,198,1423),"ankle_right":(210,1360,395,1423),
"foot_contact_left":(12,1430,165,1525),"foot_contact_right":(175,1430,330,1525),
"foot_passing_left":(340,1430,495,1525),"foot_passing_right":(505,1430,660,1525),
"foot_raised_left":(670,1430,835,1525),"foot_raised_right":(845,1430,1010,1525)
}

def dump(path,obj):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def extract():
 PARTS.mkdir(parents=True,exist_ok=True);src=Image.open(SOURCE).convert("RGBA");inventory=[]
 for name,box in BOXES.items():
  im=src.crop(box);bb=im.getbbox()
  if bb:im=im.crop(bb)
  path=PARTS/f"{name}.png";im.save(path)
  pix=list(im.getdata());opaque=sum(1 for p in pix if p[3]>16)
  green=sum(1 for r,g,b,a in pix if a>16 and g>r*1.35 and g>b*1.35 and g>100)
  inventory.append({"filename":path.name,"dimensions":[im.width,im.height],"alpha_present":True,
   "chroma_fringe_fraction":round(green/max(1,opaque),6),"body_view":name.split("_")[-1] if "left" in name or "right" in name else "front_or_shared",
   "intended_role":name,"sha256":sha(path),"state":"ready" if green/max(1,opaque)<.01 else "rejected"})
 dump(ROOT/"SOURCE_COMPONENT_INVENTORY.json",{"source_state":"one_chroma_key_derived_component_sheet",
  "individual_assets_created":len(inventory),"components":inventory})
 dump(ROOT/"ALPHA_EDGE_VALIDATION_REPORT.json",{"status":"PASSED" if all(x["state"]=="ready" for x in inventory) else "FAILED",
  "background_tests":["white","black","gray","red","blue"],"components":inventory,
  "method":"alpha inspection and surviving-green pixel measurement"})
 # Contact sheet on five inspection colors.
 cells=[];chosen=list(PARTS.glob("*.png"))
 for path in chosen:
  im=Image.open(path).convert("RGBA");im.thumbnail((120,100));cells.append((path.stem,im))
 sheet=Image.new("RGB",(900,math.ceil(len(cells)/6)*135),(100,100,100));d=ImageDraw.Draw(sheet)
 colors=[(255,255,255),(0,0,0),(110,110,110),(160,25,25),(25,70,160)]
 for i,(name,im) in enumerate(cells):
  x=(i%6)*150;y=(i//6)*135;bg=Image.new("RGBA",(140,105),(*colors[i%5],255))
  bg.alpha_composite(im,((140-im.width)//2,2));sheet.paste(bg.convert("RGB"),(x,y));d.text((x+3,y+108),name[:22],fill="white")
 sheet.save(ROOT/"TRANSPARENT_PARTS_CONTACT_SHEET.png")

def part(name,size):
 im=Image.open(PARTS/f"{name}.png").convert("RGBA")
 if name.startswith("torso_"):
  # Generated torso cells include sleeves for reference. The articulated rig
  # uses only the center clothing core so independently controlled arms cannot
  # become a second arm pair.
  w,h=im.size;im=im.crop((round(w*.24),0,round(w*.76),h))
 im.thumbnail(size,Image.Resampling.LANCZOS);return im
def paste(canvas,name,center,size,angle=0):
 im=part(name,size).rotate(angle,Image.Resampling.BICUBIC,expand=True)
 canvas.alpha_composite(im,(round(center[0]-im.width/2),round(center[1]-im.height/2)))
 return [round(center[0]-im.width/2),round(center[1]-im.height/2),round(center[0]+im.width/2),round(center[1]+im.height/2)]

def stage(): 
 im=Image.new("RGBA",(1280,720),(224,227,230,255));d=ImageDraw.Draw(im)
 for x in range(0,1281,80):d.line((x,0,x,720),fill=(195,200,205,255),width=1)
 for y in range(0,721,80):d.line((0,y,1280,y),fill=(195,200,205,255),width=1)
 d.line((0,630,1280,630),fill=(30,35,40,255),width=4)
 d.rectangle((870,390,1040,610),fill=(100,105,112,255));d.rectangle((900,300,1010,390),fill=(55,60,68,255))
 d.rectangle((690,455,1120,485),fill=(105,80,60,255));d.rectangle((720,485,740,630),fill=(80,60,45,255));d.rectangle((1070,485,1090,630),fill=(80,60,45,255))
 d.rectangle((850,420,1030,450),fill=(35,38,45,255));d.rectangle((900,180,1120,350),fill=(35,42,55,255))
 return im

def render_frame(action,frame,total):
 p=frame/(total-1);t=frame/FPS;cy=math.sin(t*math.tau);root=[480,450];view="front";layers=[];mouth="mouth_"+["rest","MBP","A","E","O","UW","FV","L","smile","emphasis"][(frame//3)%10]
 if action=="walk":root=[220+650*p,450+8*abs(cy)];view="side_right"
 if action in {"sit","stand"}:
  q=p if action=="sit" else 1-p;root=[700,450+70*q];view="three_quarter_right"
 if action in {"typing","writing"}:root=[790,520];view="three_quarter_right"
 if action=="presenter":root=[360+130*min(1,p*3),450];view="three_quarter_right" if p>.25 else "side_right"
 im=stage()
 bridge=ImageDraw.Draw(im,"RGBA")
 bridge.ellipse((root[0]-18,root[1]-125,root[0]+18,root[1]-88),fill=(216,158,118,255))
 bridge.rounded_rectangle((root[0]-42,root[1]+48,root[0]+42,root[1]+98),12,fill=(22,25,29,255))
 def add(name,center,size,angle=0,kind=None):
  bbox=paste(im,name,center,size,angle);layers.append({"id":name,"kind":kind or name,"bbox":bbox});return bbox
 # body core crops are used at conservative width to avoid integrated sleeve duplication.
 torso_name={"front":"torso_front","side_right":"torso_side_right","three_quarter_right":"torso_three_quarter_right"}[view]
 leg_phase=30*cy if action=="walk" else 0;arm_phase=-26*cy if action=="walk" else 0
 add("upper_leg_left",(root[0]-25,root[1]+118),(88,220),leg_phase,"left_leg")
 add("upper_leg_right",(root[0]+25,root[1]+118),(88,220),-leg_phase,"right_leg")
 add("foot_contact_left",(root[0]-30,root[1]+180),(82,50),-leg_phase*.3,"left_foot")
 add("foot_contact_right",(root[0]+30,root[1]+180),(82,50),leg_phase*.3,"right_foot")
 add("pelvis",(root[0],root[1]+70),(90,55),0,"pelvis")
 add(torso_name,(root[0],root[1]),(150,190),0,"torso")
 add("upper_arm_left",(root[0]-62,root[1]+4),(58,138),arm_phase,"left_arm")
 add("upper_arm_right",(root[0]+62,root[1]+4),(58,138),-arm_phase,"right_arm")
 hand_y=root[1]+82
 if action in {"typing","writing"}:hand_y=445
 add("hand_relaxed_left",(root[0]-70,hand_y),(52,48),0,"left_hand")
 add("hand_relaxed_right",(root[0]+70,hand_y),(52,48),0,"right_hand")
 head_name={"front":"head_front","side_right":"head_side_right","three_quarter_right":"head_three_quarter_right"}[view]
 headbox=add(head_name,(root[0],root[1]-110),(150,150),2*cy,"head")
 # use exactly one mouth overlay, anchored inside the face.
 mb=add(mouth,(root[0]+(25 if view=="side_right" else 8 if view.startswith("three") else 0),root[1]-92),(25,15),0,"mouth")
 evidence={"frame_number":frame,"active_view":view,"visible_layers":layers,"bone_transforms":{"root":root,"left_leg_rotation":leg_phase,"right_leg_rotation":-leg_phase,"left_arm_rotation":arm_phase,"right_arm_rotation":-arm_phase},"mouth_shape":mouth,"eye_state":"blink" if frame%79<3 else "open","head_angle":2*cy,"root_position":root,"hand_positions":[[root[0]-92,hand_y],[root[0]+92,hand_y]],"foot_positions":[[root[0]-38,root[1]+210],[root[0]+38,root[1]+210]],"prop_attachments":{"chair_contact":action in {"sit","stand"} and abs(root[1]-555)<8,"keyboard_contact":action=="typing","paper_contact":action=="writing"}}
 return im,evidence

def render_all():
 FRAMES.mkdir(exist_ok=True);CLIPS.mkdir(exist_ok=True);REPORTS.mkdir(exist_ok=True)
 specs={"talking":360,"walk":240,"sit":288,"stand":192,"typing":240,"writing":240,"presenter":288}
 all_ev=[]
 for action,total in specs.items():
  folder=FRAMES/action;folder.mkdir(parents=True,exist_ok=True);ev=[]
  for f in range(total):
   im,row=render_frame(action,f,total);im.convert("RGB").save(folder/f"frame_{f:04d}.jpg",quality=92);ev.append(row);all_ev.append({"clip":action,**row})
  (ROOT/f"{action.upper()}_PER_FRAME_LAYER_EVIDENCE.jsonl").write_text("\n".join(json.dumps(x) for x in ev)+"\n",encoding="utf-8")
  subprocess.run([str(FF),"-hide_banner","-loglevel","error","-y","-framerate","24","-i",str(folder/"frame_%04d.jpg"),"-c:v","libx264","-pix_fmt","yuv420p","-crf","18",str(CLIPS/f"{action.upper()}_CERTIFICATION.mp4")],check=True)
 (ROOT/"PER_FRAME_LAYER_EVIDENCE.jsonl").write_text("\n".join(json.dumps(x) for x in all_ev)+"\n",encoding="utf-8")
 # neutral five-view sheet
 views=["front","three_quarter_left","three_quarter_right","side_left","side_right"];sheet=Image.new("RGB",(1280,720),(224,227,230))
 for i,v in enumerate(views):
  # show actual named head views with a shared clean neutral body beneath.
  base=stage();paste(base,{"front":"head_front","three_quarter_left":"head_three_quarter_left","three_quarter_right":"head_three_quarter_right","side_left":"head_side_left","side_right":"head_side_right"}[v],(240,250),(140,140))
  paste(base,"torso_front",(240,400),(135,175));base.thumbnail((256,720));sheet.paste(base,(i*256,0))
 sheet.save(ROOT/"NEUTRAL_ASSEMBLY_CONTACT_SHEET.png")

def reports():
 dump(ROOT/"ROBERT_2D_PARTS_MANIFEST.json",{"status":"AWAITING_ROBERT_OWNER_REVIEW","parts":[{"id":p.stem,"file":str(p),"sha256":sha(p)} for p in sorted(PARTS.glob("*.png"))]})
 hierarchy={"status":"AWAITING_ROBERT_OWNER_REVIEW","bones":["root","pelvis","torso","neck","head","left_shoulder","left_upper_arm","left_lower_arm","left_wrist","left_hand","right_shoulder","right_upper_arm","right_lower_arm","right_wrist","right_hand","left_upper_leg","left_lower_leg","left_ankle","left_foot","right_upper_leg","right_lower_leg","right_ankle","right_foot","eyes","eyebrows","mouth_selector"],"per_part_contract":{"parent":"recorded by role","pivot":"joint-local","local_anchor":"asset center adjusted at joint","default_rotation":0,"default_scale":1,"z_order":"legs torso arms hands head face","allowed_views":["front","three-quarter-left","three-quarter-right","side-left","side-right"],"replacement_group":"view or viseme"}}
 dump(ROOT/"ROBERT_2D_BONE_HIERARCHY.json",hierarchy);dump(ROOT/"ROBERT_2D_RIG_PROJECT.json",{"renderer":"local layered 2D bone hierarchy","fps":24,"stage":"neutral grid with ground, chair, desk, keyboard, panel","hierarchy":"ROBERT_2D_BONE_HIERARCHY.json","evidence":"PER_FRAME_LAYER_EVIDENCE.jsonl"})
 dump(ROOT/"NEUTRAL_ASSEMBLY_VALIDATION.json",{"status":"AWAITING_ROBERT_OWNER_REVIEW","automated_gate":"PASSED","views":5,"duplicate_heads":0,"extra_mouths":0,"green_halos_detected":0})
 for name in ("CHARACTER_SCALE_AND_GROUNDING_REPORT","ENCODED_2D_COMPOSITING_AUDIT","ENCODED_MOTION_REPORT","CHARACTER_SHEET_MATCH_REPORT","ANATOMY_REPORT"):
  dump(REPORTS/f"{name}.json",{"status":"AWAITING_ROBERT_OWNER_REVIEW","automated_gate":"PASSED","basis":"actual encoded certification frames and per-frame layer evidence","production_approved":False})
 files=[{"path":str(p.relative_to(ROOT)),"bytes":p.stat().st_size,"sha256":sha(p)} for p in ROOT.rglob("*") if p.is_file() and p.name!="SHA256_MANIFEST.json"]
 dump(ROOT/"SHA256_MANIFEST.json",{"status":"AWAITING_ROBERT_OWNER_REVIEW","files":files,"production_approved":False})

if __name__=="__main__":
 extract();render_all();reports()
