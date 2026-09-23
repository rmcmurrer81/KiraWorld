"""Preserve first combined026 proposal, stage successor027 metadata correction."""
from pathlib import Path
import hashlib,json,shutil
H=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
archive=H/'revision-001';archive.mkdir(exist_ok=False)
for n in ('INSTALL-PLAN.json','VALIDATION.json','validate_combined.py','apply_guarded.py'):
 shutil.copyfile(H/n,archive/n)
p=H/'candidate/tools/world_builder_engine/world_layout_preview.py';shutil.copyfile(p,archive/p.name)
s=p.read_text();assert sha(p)=='fe8cfb9ca9754f71dd223b16ec941753b368b48ded9a5fa0cbe82c83503bec28'
s=s.replace("CONTRACT: {'2d5a27e7137011872a0d9645cbfdd96646e592334b44d9d6e800389518604cb9': 22133},", "CONTRACT: {\n        '2d5a27e7137011872a0d9645cbfdd96646e592334b44d9d6e800389518604cb9': 22133,\n        'fe8cfb9ca9754f71dd223b16ec941753b368b48ded9a5fa0cbe82c83503bec28': 24195,\n    },")
s=s.replace("'Simple layout materials and lighting; appearance is unfinished.',\n                               'Open passages are not moving or pressure-controlled doors.'", "'Authored procedural equipment and materials; appearance is not realism approval.',\n                               'Moving doors have session-local state; no pressure or airlock-cycle simulation.',\n                               'Equipment is static; science and life-support behavior are not simulated.'")
p.write_text(s,encoding='utf-8',newline='\n')
plan=json.loads((H/'INSTALL-PLAN.json').read_text());plan['package']='combined-habitat025-preview027';plan['supersedes']='revision-001/INSTALL-PLAN.json'
for f in plan['files']:
 if f['relative_path'].endswith('world_layout_preview.py'):f['after'].update(sha256=sha(p),bytes=p.stat().st_size)
with (H/'INSTALL-PLAN.json').open('w',encoding='utf-8') as f:json.dump(plan,f,indent=2);f.write('\n')
print(json.dumps({'backend_sha256':sha(p),'backend_bytes':p.stat().st_size,'plan_sha256':sha(H/'INSTALL-PLAN.json')}))
