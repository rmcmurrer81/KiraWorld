"""Freeze only after successful combined CPU evidence and fresh preservation."""
from pathlib import Path
import hashlib,json
H=Path(__file__).resolve().parent;K=Path('C:/Users/robmc/Kira')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())
def pin(p):return {'sha256':sha(p),'bytes':p.stat().st_size}
def write(name,value):
    with (H/name).open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(value,indent=2)+'\n')
source=read(H/'SOURCE-PINS.json');closure=read(H/'CANDIDATE-CLOSURE.json');protected=read(H/'OWNER-PRESERVATION.local.json')
assert len(source)==len(closure)==42 and len(protected)==116
assert all(pin(K/r)==v for r,v in source.items())
assert all(pin(H/'preimages'/r)==v for r,v in source.items())
assert all(pin(H/'candidate'/r)==v for r,v in closure.items())
assert all(sha(p)==v for p,v in protected.items())
meal=read(H/'TEST-RESULT.json');saved=read(H/'TEST-RESULT-SAVED.json');hardware=read(H/'HARDWARE-TEST-RESULT.json');contract=read(H/'CONTRACT-RESULT.json')
assert len(meal['shapes'])==4 and len(saved['shapes'])==1
assert meal['status']==saved['status']=='PASS_MEAL_GEOMETRY_PLACEMENT_OMISSION_AND_SHARED_EXPORT'
assert hardware['status']=='PASS_CPU_HARDWARE_COLLISION' and len(hardware['reports'])==5
assert contract['status']=='PASS_COMBINED_READ_ONLY_ADMISSION_AND_PRESERVATION'
changed={r:{'before':source[r],'after':closure[r]} for r in source if source[r]!=closure[r]}
assert len(changed)==9
write('RESULT.json',{'status':'ISOLATED062_COMBINED_CPU_PASS_NOT_INSTALLED','changed_files':changed,'source_closure_files':42,'canonical_sources_unchanged':42,'owner_originals_unchanged':116,'meal_layouts':5,'hardware_layouts':5,'hardware_door_poses':sum(c['door_poses'] for r in hardware['reports'] for c in r['consumers']),'hardware_assertions':hardware['checks'],'renderer_admission_cases':len(contract['combined_admission_cases']),'producer_pins_verified':17,'selected_job_pointer_unchanged':contract['selected_job_pointer_unchanged'],'exact_seven_parent_source_files':True,'deliberately_merged_pin_files':2,'new_preview_export_renderer_model_GPU_UI_install_calls':0,'visual_approval':False,'owner_approval':False,'source_diff':pin(H/'SOURCE.diff'),'evidence':{n:pin(H/n) for n in ['MERGE-PROVENANCE.json','TEST-RESULT.json','TEST-RESULT-SAVED.json','HARDWARE-TEST-RESULT.json','CONTRACT-RESULT.json']},'remaining':['Independent source review','New immutable combined preview','Supervised CPU export/import','Native visual and traversal inspection','Guarded installation only after review']})
files={p.relative_to(H).as_posix():pin(p) for p in sorted(H.rglob('*')) if p.is_file() and p.name not in {'OWNER-PRESERVATION.local.json','FROZEN-MANIFEST.json'}}
write('FROZEN-MANIFEST.json',{'schema':'world062-isolated-combination.v1','status':'CPU_REVIEW_READY_NOT_INSTALLED','files':files,'local_preservation_manifest_sha256':sha(H/'OWNER-PRESERVATION.local.json'),'visual_or_owner_approval':False})
print(json.dumps({'status':'FROZEN','files':len(files),'manifest':pin(H/'FROZEN-MANIFEST.json'),'result':pin(H/'RESULT.json')}))
