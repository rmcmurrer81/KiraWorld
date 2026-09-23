from pathlib import Path
import datetime
import hashlib
import json
import re
H=Path(__file__).resolve().parent;K=Path('@user_home/Kira');W=H.parent.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def row(p):return {'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size}
baseline=json.loads((H/'BASELINE.json').read_text(encoding='utf-8'))
assert sha(Path(baseline['installed_workspace']))==baseline['sha256']
assert not (K/'tools/world_saved_research.py').exists()
files=[]
for name in ['world_builder_workspace.py','world_saved_research.py']:
 source=H/'candidate/tools'/name;target=K/'tools'/name
 compile(source.read_text(encoding='utf-8'),str(source),'exec')
 files.append({'source':row(source),'target':str(target),'before_sha256':sha(target) if target.exists() else None})
report=json.loads((H/'TEST-RESULT.json').read_text(encoding='utf-8'));assert report['status']=='PASS' and report['tests']==22 and len(report['skipped'])==2
launcher=K/'Start_Kira_World_Builder_Workspace.bat'
delivery={'status':'CANDIDATE023_READY_FOR_REVIEW_NOT_INSTALLED','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':files,'changes':'Adds saved research selector from022; valid or failed selection now closes layout and previous reference photos and updates any open component view to the selected job or None.','validation':{'actual_callback_checks_passed':20,'real_symlink_checks_skipped_for_windows_privilege':2,'native_ui_window_opened':False,'model_or_research_queue_calls':0},'native_shortcut':{'path':str(Path.home()/'Desktop/Kira World Builder Workspace.lnk'),'target':str(launcher),'arguments':'','working_directory':str(K),'launcher':row(launcher),'runtime_script':str(K/'tools/world_builder_workspace.py'),'runtime_selection':'Launcher uses py if present, otherwise python. Root can use C:/Python314/python.exe for an explicitly chosen interpreter.'},'owner_or_canonical_writes':False,'installed':False,'predecessor022_preserved':True}
(H/'DELIVERY.json').write_text(json.dumps(delivery,indent=2)+'\n',encoding='utf-8')
(H/'README.md').write_text('''# World023 saved-project context — candidate, not installed

This supersedes isolated022 without changing its files. The saved research/layout
selector still reopens existing work without running research or generation.
When a job is selected, its layout preview and any previous reference-photo
window are closed, and an already-open Original Components view receives the
new selected job immediately. On failed selection it receives None and the
old reference/preview contexts are cleared. Existing components are not rebuilt
or placed, and the binding checkbox is reset by its existing set_world_job API.

20 headless checks executing actual candidate methods passed; two real symlink
checks were skipped because Windows denied creating disposable links. Tests
cover valid, missing, damaged, foreign and ambiguous-title selections, plus
active/already-closed child views and no automatic queue/model work. They do not
claim a native Tk visual pass. No installed or owner file was changed.

DELIVERY.json lists exactly two candidate files, current installed before hashes
and the observed Desktop shortcut/runtime chain. Root should review the small
CHANGES-FROM-022.patch before guarded installation and native UI validation.
World015 physics and all existing owner projects remain unchanged by this work.
''',encoding='utf-8')
P=H/'public-backup-001';P.mkdir(exist_ok=False)
def redact(t):
 for value,alias in [(str(W),'@workspace'),(W.as_posix(),'@workspace'),(str(Path.home()),'@user_home'),(Path.home().as_posix(),'@user_home')]:t=t.replace(json.dumps(value)[1:-1],alias).replace(value,alias)
 return re.sub(r'C:[\\/]+Users[\\/]+'+re.escape(Path.home().name),'@user_home',t,flags=re.I)
entries=[]
for f in sorted(H.rglob('*')):
 if not f.is_file() or P in f.parents or '__pycache__' in f.parts:continue
 relative=f.relative_to(H).as_posix();dest=P/relative;dest.parent.mkdir(parents=True,exist_ok=True)
 original=f.read_text(encoding='utf-8');text=redact(original);dest.write_text(text,encoding='utf-8',newline='\n')
 assert Path.home().name.lower() not in text.lower()
 entries.append({'path':relative,'sha256':sha(dest),'bytes':dest.stat().st_size,'original_sha256':sha(f),'identity_paths_redacted':text!=original})
manifest={'status':'SAVED_CONTEXT023_BACKUP_UNINSTALLED','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':entries,'identity_paths_redacted':True,'portable_replay_executed':False,'reproduction_note':'Evidence scripts use local path placeholders. Configure a Kira installation with its dependencies before rerunning tests in a fresh output directory.'}
(P/'BACKUP-MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'delivery_sha256':sha(H/'DELIVERY.json'),'backup_manifest_sha256':sha(P/'BACKUP-MANIFEST.json'),'backup_files':len(entries)+1,'candidate_files':files}))
