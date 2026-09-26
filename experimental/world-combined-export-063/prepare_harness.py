"""Derive one constrained export harness from the reviewed059 mechanism."""
from pathlib import Path
import hashlib,difflib,json
H=Path(__file__).resolve().parent;W=H.parent
source=W/'world-meal-station-candidate-059/run_cpu_export.py'
before=source.read_text(encoding='utf-8');text=before
text=text.replace('Root-authorized059 isolated CPU preview/export','Root-authorized063 combined CPU preview/export')
text=text.replace("E=K/'tools/world_builder_engine';C=H/'candidate/tools/world_builder_engine'", "E=K/'tools/world_builder_engine';F=W/'world-combined-followup-062';C=F/'candidate/tools/world_builder_engine'")
start=text.index('def source_check(plan):');end=text.index('\ndef child():',start)
text=text[:start]+'''def source_check(plan):
 assert sha(F/'FROZEN-MANIFEST.json')=='c54ef25dab757ca2689a030749d81e21ddef14ecaca999c411759301ee345207'
 assert len(plan['protected_inputs'])==116 and all(sha(p)==s for p,s in plan['protected_inputs'].items())
 source=json.loads((F/'SOURCE-PINS.json').read_bytes());closure=json.loads((F/'CANDIDATE-CLOSURE.json').read_bytes())
 assert len(source)==len(closure)==42
 for rel,row in source.items():assert sha(K/rel)==row['sha256'] and (K/rel).stat().st_size==row['bytes']
 for rel,row in closure.items():assert sha(F/'candidate'/rel)==row['sha256'] and (F/'candidate'/rel).stat().st_size==row['bytes']
 for rel,row in json.loads((F/'FROZEN-MANIFEST.json').read_bytes())['files'].items():
  assert sha(F/rel)==row['sha256'] and (F/rel).stat().st_size==row['bytes']

def preflight():
 from world_builder_engine import layout_package_export
 api=load('world_builder_engine.layout_package_export063_preflight',C/'layout_package_export.py')
 verified=api.verify_dependencies()
 ancestors={p.pid for p in psutil.Process().parents()}|{os.getpid()}
 conflicts=[]
 for p in psutil.process_iter(['pid','name','cmdline']):
  if p.pid in ancestors:continue
  name=(p.info['name'] or '').lower();cmd=' '.join(p.info['cmdline'] or []).lower()
  if name in ('python.exe','pythonw.exe','blender.exe','ffmpeg.exe') or (name=='node.exe' and 'build_glb.mjs' in cmd):
   conflicts.append({'pid':p.pid,'name':name})
 assert not conflicts, 'Another render/service process is present; hold without stopping it: '+str(conflicts)
 return {'source_producer_files_verified':len(verified['pins']['files']),'external_dependencies_verified':len(verified['pins']['external']),'conflicting_processes':conflicts,'resource_limits_unchanged_from059':True}
''' + text[end:]
text=text.replace("plan=json.loads((H/'INSTALL-PLAN.json').read_bytes());source_check(plan)","plan={'protected_inputs':json.loads((F/'OWNER-PRESERVATION.local.json').read_bytes())};source_check(plan);checked_preflight=preflight()")
text=text.replace("assert not O.exists() and not R.exists();O.mkdir()","assert not O.exists() and not R.exists();O.mkdir();put(O/'PREFLIGHT.json',checked_preflight)")
text=text.replace("refreshed['presentation']", "refreshed['presentation']")
text=text.replace("for name in ('world-installed-observation-export-057','world-observation-viewport-053','world-observation-setting-054','world-door-targeting-candidate-051'):","protected.update(inventory(K/'Data/world_layout_previews'))\n protected.update(inventory(W/'world-meal-station-candidate-059/runtime_context/Data/world_layout_previews'))\n for name in ('world-installed-observation-export-057','world-meal-station-candidate-059','world-observation-viewport-053','world-observation-setting-054','world-door-targeting-candidate-051'):")
text=text.replace("'PROTECTED-DERIVED-FILES.json'","'PROTECTED-DERIVED-FILES.local.json'")
text=text.replace("'originals_inventory_sha256':sha(H/'INSTALL-PLAN.json')","'originals_inventory_sha256':sha(F/'OWNER-PRESERVATION.local.json')")
text=text.replace("'frozen059_files_unchanged':69","'frozen062_files_unchanged':110")
text=text.replace("ISOLATED059", "ISOLATED063").replace('layout_package_export059','layout_package_export063')
text=text.replace('IMMUTABLE059_PREVIEW_CREATED','IMMUTABLE063_PREVIEW_CREATED')
text=text.replace('isolated059 CPU export/import','isolated063 CPU export/import')
text=text.replace('no rendering/UI/install.', 'no rendering/UI/install; exact frozen062 sources.')
with (H/'run_cpu_export.py').open('x',encoding='utf-8',newline='\n') as f:f.write(text)
with (H/'HARNESS-FROM059.diff').open('x',encoding='utf-8',newline='\n') as f:f.write(''.join(difflib.unified_diff(before.splitlines(True),text.splitlines(True),fromfile='reviewed059/run_cpu_export.py',tofile='isolated063/run_cpu_export.py')))
receipt={'prior_harness_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256((H/'run_cpu_export.py').read_bytes()).hexdigest(),'root_authorized_exports':1,'attempt_directory_must_not_exist':'actual-001','family_rss_cap_bytes':int(.8*1024**3),'start_free_bytes':5*1024**3,'reserve_free_bytes':3*1024**3,'deadline_seconds':150,'changes':'Use frozen062 closure; verify producer+external dependencies before launch; hold on foreign render/service processes; preserve all canonical previews and059 preview/package too. Export implementation and original resource caps unchanged.'}
with (H/'HARNESS-PREPARATION.json').open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
