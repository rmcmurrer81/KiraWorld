"""Read-only future-install compatibility check; no owner or canonical writes."""
from pathlib import Path
import hashlib,json,sys,types
H=Path(__file__).resolve().parent;ENGINE=Path('@user_home/Kira/tools/world_builder_engine')
SOURCE=H/'candidate/tools/world_builder_engine/world_layout_preview.py';TARGET=ENGINE/'world_layout_preview.py'
MANIFEST=Path('@user_home/Kira/Data/world_layout_previews/layout-a37f864587b3ee075e21ccd1/manifest.json')
EXPECTED='f99bbbe4fde564e1f48814c899b85ca6f78b0ffe9466a4a88ccabd139999313a'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def deny(event,args):
    if event in ('socket.connect','socket.bind','subprocess.Popen'):raise RuntimeError('Read-only compatibility check prohibits network/processes')
sys.addaudithook(deny)
assert sha(MANIFEST)==EXPECTED
saved=json.loads(MANIFEST.read_text());rows=list(saved['inputs'].values())+list(saved['source_pins'].values())+list(saved['assets'].values())
before={row['path']:sha(row['path']) for row in rows};before[str(MANIFEST)]=EXPECTED
module=types.ModuleType('readonly_preview026');module.__file__=str(TARGET)
exec(compile(SOURCE.read_bytes(),str(SOURCE),'exec'),module.__dict__)
native_binding=module.binding
def future_binding(path):
    # Only simulate the proposed installed backend's own bytes. Every owner,
    # asset, navigation, research and Node read uses the real verifier unchanged.
    if Path(path).absolute()==TARGET:return {'path':str(TARGET),'bytes':SOURCE.stat().st_size,'sha256':sha(SOURCE)}
    return native_binding(path)
module.binding=future_binding
result=module.verify_preview(MANIFEST,EXPECTED)
assert all(sha(path)==digest for path,digest in before.items())
receipt={'status':'PASS_READONLY_EXISTING_PREVIEW_WITH_PROPOSED_BACKEND_IDENTITY',
 'manifest_sha256':EXPECTED,'build_id':result['build_id'],'assets':len(result['assets']),
 'source_mode':result['source_mode'],'candidate_sha256':sha(SOURCE),'canonical_backend_sha256':sha(TARGET),
 'actual_files_hashed_before_and_after':len(before),'all_bytes_unchanged':True,
 'simulation':'Candidate code evaluated at canonical module location; only current backend self-binding substituted with proposed bytes. All asset/provenance/Node checks read actual pinned files.',
 'owner_data_modified':False,'canonical_installed':False,'model_network_browser_calls':0,'visual_or_owner_approval':False}
with (H/'READONLY-SAVED-PREVIEW-CHECK.json').open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2);f.write('\n')
print(json.dumps(receipt))
