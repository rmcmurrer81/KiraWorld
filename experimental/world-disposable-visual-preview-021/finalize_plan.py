from pathlib import Path
import hashlib
import json
H=Path(__file__).resolve().parent
K=Path('@user_home/Kira')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=H/'PLAN.json';plan=json.loads(p.read_text(encoding='utf-8'))
assert not (H/'SERVER-STARTED.json').exists()
plan['owner_files_before']={str(f.relative_to(K)).replace('\\','/'):sha(f) for folder in ['Data/world_bedding_studies','Data/world_original_components'] for f in sorted((K/folder).rglob('*')) if f.is_file()}
historical=json.loads((H.parent/'world-portable-native-preview-candidate-015/INSTALL-STARTED.json').read_text())['owner_inventory']
assert len(plan['owner_files_before'])==56
assert all(sha(K/name)==digest for name,digest in historical.items())
server=H/'serve_preview.py'
compile(server.read_text(encoding='utf-8'),str(server),'exec')
plan.update(server={'path':str(server),'sha256':sha(server)},server_scope='Read-only 127.0.0.1 only, exact pinned asset allowlist, no POST, expires after 300 seconds, consumed-run guard')
p.write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'plan_sha256':sha(p),'owner_files':len(plan['owner_files_before']),'server_sha256':sha(server),'status':'STATIC_READY_NOT_LAUNCHED'}))
