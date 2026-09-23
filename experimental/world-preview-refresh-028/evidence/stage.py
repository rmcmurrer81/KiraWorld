from pathlib import Path
import hashlib,json,shutil
H=Path(__file__).resolve().parent;K=Path.home()/'Kira'
names=('tools/world_builder_engine/preview_server.py','tools/world_builder_engine/workspace_adapter.py','tools/world_builder_workspace.py')
files=[]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
for rel in names:
 source=K/rel;before=H/'baseline'/rel;after=H/'candidate'/rel
 before.parent.mkdir(parents=True,exist_ok=True);after.parent.mkdir(parents=True,exist_ok=True)
 assert not before.exists() and not after.exists();shutil.copyfile(source,before);shutil.copyfile(source,after)
 files.append({'relative_path':rel,'before_sha256':sha(before)})
p=H/'candidate/tools/world_builder_engine/preview_server.py';s=p.read_text(encoding='utf-8')
s=s.replace('from world_builder_engine.pipeline import latest_preview','from world_builder_engine.preview_refresh import refresh_saved_preview')
s=s.replace('manifest=latest_preview(args.job)','manifest=refresh_saved_preview(args.job)');p.write_text(s,encoding='utf-8',newline='\n')
p=H/'candidate/tools/world_builder_engine/workspace_adapter.py';s=p.read_text(encoding='utf-8');assert s.count('ready.get(timeout=12)')==1
s=s.replace('ready.get(timeout=12)','ready.get(timeout=32)');p.write_text(s,encoding='utf-8',newline='\n')
p=H/'candidate/tools/world_builder_workspace.py';s=p.read_text(encoding='utf-8')
s=s.replace('text="Open Layout Preview", command=self.open_layout_preview','text="Open current preview", command=self.open_layout_preview')
s=s.replace('Use Open Layout Preview or Reference Photos to inspect saved results. No research or generation was started.','Use Open current preview to view the saved layout with current appearance and controls, or Reference Photos. Original layout files are preserved.')
s=s.replace('Use Open Layout Preview to explore.','Use Open current preview to explore.')
s=s.replace('Opened the original layout prototype. This is not a finished world.','Opened the current presentation of your saved layout. Earlier previews are preserved; no research or model generation was rerun. This remains a prototype.')
p.write_text(s,encoding='utf-8',newline='\n')
(H/'BASELINES.json').write_text(json.dumps(files,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':'028_STAGED_NO_INSTALL','existing_files':3,'new_helper_pending':True}))
