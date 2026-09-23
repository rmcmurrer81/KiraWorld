from pathlib import Path
import hashlib,json,shutil
H=Path(__file__).resolve().parent;W=H.parent;K=Path('@kira_root')
source=K/'tools/world_builder_engine';target=H/'candidate/tools/world_builder_engine';target.mkdir(parents=True)
for name in ('layout_package_export.py','layout_package_contract.json'):
 shutil.copyfile(source/name,target/name)
assets=target/'layout_package_assets';shutil.copytree(source/'layout_package_assets',assets)
(H/'baseline').mkdir();shutil.copyfile(source/'layout_package_export.py',H/'baseline/layout_package_export.py');shutil.copyfile(assets/'authored_scene.mjs',H/'baseline/authored_scene.mjs')
shutil.copytree(W/'world-package-039/fixtures',H/'fixtures')
for name in ('test_api.py','SYNTHETIC-POLICY-METADATA.json'):shutil.copyfile(W/'world-package-039'/name,H/name)
rows=[]
for p in (K/'Data/world_research_jobs').glob('*/job.json'):
 blueprints=[]
 for b in p.parent.rglob('blueprint.json'):
  value=json.loads(b.read_bytes());blueprints.append({'file':str(b.relative_to(p.parent)),'sha256':hashlib.sha256(b.read_bytes()).hexdigest(),'contract':value.get('contract'),
   'top_fields':sorted(value),'room_count':len(value.get('rooms',[])),'room_fields':sorted(value.get('rooms',[{}])[0]),'opening_count':len(value.get('openings',[]))})
 rows.append({'job_id':p.parent.name,'job_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'metadata_fields':sorted(json.loads(p.read_bytes())),'blueprints':blueprints})
(H/'SAVED-SCHEMA-AUDIT.json').write_text(json.dumps({'read_only':True,'job_count':len(rows),'jobs':rows,'personal_brief_or_research_contents_copied':False},indent=2)+'\n',encoding='utf-8')
(H/'BASELINE-PINS.json').write_text(json.dumps({str(p.relative_to(K)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source/'layout_package_export.py',source/'layout_package_contract.json',source/'world_blueprint.py',source/'layout_package_assets/PRODUCER-PINS.json',source/'layout_package_assets/authored_scene.mjs']},indent=2)+'\n',encoding='utf-8')
print('041 isolated; two saved-job schemas read, no sources changed')
