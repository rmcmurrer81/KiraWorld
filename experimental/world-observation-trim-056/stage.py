"""Isolated056: remove overlapping reveal/frame surfaces without changing bounds."""
from pathlib import Path
import difflib,hashlib,json,shutil
H=Path(__file__).resolve().parent;B=H.parent/'world-observation-exclusion-055';C=H/'candidate'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert not C.exists()
closure=json.loads((B/'CANDIDATE-CLOSURE.json').read_bytes());plan=json.loads((B/'INSTALL-PLAN.json').read_bytes())
assert len(plan['protected_inputs'])==116 and all(sha(p)==s for p,s in plan['protected_inputs'].items())
for rel,row in closure.items():
    p=B/'candidate'/rel;assert sha(p)==row['sha256'] and p.stat().st_size==row['bytes']
shutil.copytree(B/'candidate',C,ignore=shutil.ignore_patterns('__pycache__'))
shared=Path('tools/world_builder_engine/layout_package_assets/source/room_dressing_render.mjs')
viewer=Path('tools/world_builder_engine/viewer.mjs')
old=(C/shared).read_text(encoding='utf-8')
needle="  ring('reveal',.036,thickness,0,width,height,materials.basic.metal);"
replacement="""  // The reveal starts at the frame's back, not at its coplanar front.
  // Both parts stay within the original wall bounds and meet without overlap.
  ring('reveal',.036,thickness-.026,sign*.013,width,height,materials.basic.metal);"""
assert old.count(needle)==1;new=old.replace(needle,replacement)
(C/shared).write_text(new,encoding='utf-8',newline='\n')
v=(C/viewer).read_text(encoding='utf-8');old_inline=old.replace('export function ','function ').strip();new_inline=new.replace('export function ','function ').strip()
assert v.count(old_inline)==1;(C/viewer).write_text(v.replace(old_inline,new_inline),encoding='utf-8',newline='\n')
pinfile=Path('tools/world_builder_engine/layout_package_assets/PRODUCER-PINS.json')
pins=json.loads((C/pinfile).read_bytes());pins['files']['source/room_dressing_render.mjs']={'sha256':sha(C/shared),'bytes':(C/shared).stat().st_size}
(C/pinfile).write_text(json.dumps(pins,indent=2)+'\n',encoding='utf-8')
changed=[shared,viewer,pinfile];diff=[];rows=[]
for rel in changed:
    before=B/'candidate'/rel;after=C/rel;pre=H/'preimages'/rel;pre.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(before,pre)
    diff.extend(difflib.unified_diff(before.read_text().splitlines(True),after.read_text().splitlines(True),fromfile='055/'+rel.as_posix(),tofile='056/'+rel.as_posix()))
    rows.append({'path':rel.as_posix(),'before_sha256':sha(before),'sha256':sha(after),'bytes':after.stat().st_size})
(H/'FROM055.diff').write_text(''.join(diff),encoding='utf-8')
(H/'OVERLAY.json').write_text(json.dumps({'status':'ISOLATED_NOT_INSTALLED','files':rows,'protected_inputs':plan['protected_inputs'],'node':str(Path('C:/Program Files/nodejs/node.exe'))},indent=2)+'\n',encoding='utf-8')
(H/'CANDIDATE-CLOSURE.json').write_text(json.dumps({p.relative_to(C).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(C.rglob('*')) if p.is_file()},indent=2)+'\n',encoding='utf-8')
(H/'fixtures').mkdir();shutil.copyfile(B/'fixtures/supported-layouts.json',H/'fixtures/supported-layouts.json')
assert all(sha(p)==s for p,s in plan['protected_inputs'].items())
print(json.dumps({'status':'STAGED056','changed_files':3,'protected_originals':116}))
