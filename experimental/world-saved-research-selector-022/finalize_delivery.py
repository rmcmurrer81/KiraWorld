from pathlib import Path
import datetime
import hashlib
import json
import re
import shutil
H=Path(__file__).resolve().parent;K=Path('@user_home/Kira');W=H.parent.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def row(p):return {'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size}
staging=json.loads((H/'STAGING.json').read_text(encoding='utf-8'))
assert sha(Path(staging['installed_baseline']['path']))==staging['installed_baseline']['sha256']
assert not (K/'tools/world_saved_research.py').exists()
for p in (H/'candidate/tools').glob('*.py'):compile(p.read_text(encoding='utf-8'),str(p),'exec')
files=[]
for name in ['world_builder_workspace.py','world_saved_research.py']:
 source=H/'candidate/tools'/name;target=K/'tools'/name
 files.append({'source':row(source),'target':str(target),'before_sha256':sha(target) if target.exists() else None})
plan={'status':'CANDIDATE_READY_FOR_INDEPENDENT_REVIEW_NOT_INSTALLED','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':files,'scope':'Saved research selection/reopening only; no physics, project creation, model-budget or placement changes','validation':{'headless_actual_callback_tests':16,'real_link_tests_skipped':2,'existing_catalog_jobs_read':2,'owner_research_component_files_unchanged':104,'native_window_review':False},'installed':False,'owner_data_writes':False,'model_calls':0,'gpu_jobs':0,'note':'Installation would require updating the source closure inventory for the workspace plus its new helper, preserving existing36-file World015 and56 owner inventories as historical receipts.'}
(H/'DELIVERY.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
(H/'README.md').write_text('''# World022 saved research selector — candidate, not installed

Problem: after closing and reopening World Builder, Open Layout Preview asks the
owner to choose a saved research job, but the existing UI only lists Notebook
Worlds. Typing resume also queues research and the layout pipeline.

This candidate adds a Saved research/layouts selector and Refresh saved control.
Selecting a saved job restores its folder, layout preview, reference-photo and
component context without starting research or generation. Metadata is read
again on selection. Damaged jobs remain listed and their files are preserved;
selecting a damaged job clears any previous preview context to avoid opening
the wrong study. Existing notebook-world controls and explicit research/resume
behavior remain separate.

16 headless tests executing the actual candidate callbacks passed; two real
symlink tests were skipped because Windows denied creating a disposable link.
The existing two research jobs were recognized by a read-only scan. All104
research/component files and the installed workspace remained byte-identical.
No real Tk window, browser, model, GPU job, installation or Git operation ran.

DELIVERY.json lists exactly two candidate files and their current installed
before hashes. Independent review and native-window checking remain needed.
The installed World015 physics and protected56 owner frame/study files are
unchanged. This is a usability fix, not finished world generation or placement.
''',encoding='utf-8')
P=H/'public-backup-002';P.mkdir(exist_ok=False)
entries=[]
def redact(t):
 for value,alias in [(str(W),'@workspace'),(W.as_posix(),'@workspace'),(str(Path.home()),'@user_home'),(Path.home().as_posix(),'@user_home')]:t=t.replace(json.dumps(value)[1:-1],alias).replace(value,alias)
 return re.sub(r'C:[\\/]+Users[\\/]+'+re.escape(Path.home().name), '@user_home',t,flags=re.I)
source_files=[f for f in sorted(H.rglob('*')) if f.is_file() and not any(part.startswith('public-backup-') for part in f.relative_to(H).parts) and '__pycache__' not in f.parts]
for f in source_files:
 relative=f.relative_to(H).as_posix();dest=P/relative;dest.parent.mkdir(parents=True,exist_ok=True)
 original=f.read_text(encoding='utf-8');text=redact(original)
 dest.write_text(text,encoding='utf-8',newline='\n')
 entries.append({'path':relative,'sha256':sha(dest),'bytes':dest.stat().st_size,'original_sha256':sha(f),'identity_paths_redacted':text!=original})
for e in entries:assert Path.home().name.lower() not in (P/e['path']).read_text(encoding='utf-8').lower()
manifest={'status':'ISOLATED_SAVED_RESEARCH_SELECTOR_BACKUP_UNINSTALLED','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':entries,'identity_paths_redacted':True,'installation_or_portable_test_replay_performed':False,'reproduction_note':'Evidence contains local path placeholders; run tests against an explicitly configured Kira installation with its dependencies. Source behavior and original hashes are preserved; this backup is not a turnkey install.'}
(P/'BACKUP-MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'delivery_sha256':sha(H/'DELIVERY.json'),'backup_manifest_sha256':sha(P/'BACKUP-MANIFEST.json'),'files':len(entries)+1,'candidate_files':files}))
