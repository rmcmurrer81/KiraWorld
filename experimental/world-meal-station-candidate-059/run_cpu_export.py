"""Root-authorized059 isolated CPU preview/export; no installation or saved pointer writes."""
from pathlib import Path
import datetime,hashlib,importlib.util,json,os,shutil,subprocess,sys,time
import psutil

H=Path(__file__).resolve().parent;W=H.parent;K=Path('@kira_root')
E=K/'tools/world_builder_engine';C=H/'candidate/tools/world_builder_engine'
P=W/'world-observation-trim-056/native-successor-001'
O=H/'actual-001';R=H/'runtime_context/tools/world_builder_engine'
sys.dont_write_bytecode=True;sys.path.insert(0,str(K/'tools'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(path,value):
 with path.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2);f.write('\n')
def inventory(folder):return {str(p):sha(p) for p in sorted(folder.rglob('*')) if p.is_file()}
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
 sys.modules[name]=m;spec.loader.exec_module(m);return m
def source_check(plan):
 assert sha(H/'INSTALL-PLAN.json')=='cd3d00f6a41929ec18946cd36f149469be7a34cc920887629218d28b143e1f99'
 assert all(sha(p)==s for p,s in plan['protected_inputs'].items())
 assert len(plan['protected_inputs'])==116
 for rel,row in json.loads((H/'SOURCE-PINS.json').read_bytes()).items():assert sha(K/rel)==row['sha256']
 for rel,row in json.loads((H/'CANDIDATE-CLOSURE.json').read_bytes()).items():assert sha(H/'candidate'/rel)==row['sha256']
 for rel,row in json.loads((H/'FROZEN-MANIFEST.json').read_bytes())['files'].items():
  assert sha(H/rel)==row['sha256'] and (H/rel).stat().st_size==row['bytes']
 for row in plan['files']:assert sha(row['target'])==row['before_sha256'] and sha(row['after']['path'])==row['after']['sha256']
def child():
 import world_builder_engine.world_layout_preview as installed_preview
 from world_builder_engine.pipeline import latest_preview
 job=K/'Data/world_research_jobs/world_research_c391ffbffc7352612392';previous=latest_preview(job)
 refreshed=json.loads((P/'installed-preview-001/REFRESH-RESULT.json').read_bytes());binding=refreshed['current']
 assert binding['manifest_sha256']=='b8c1173842f01d2a39d41c5e8d848eed4aedcc84be458770231c7a75609f440f'
 old=installed_preview.verify_preview(binding['manifest_path'],binding['manifest_sha256'])
 assert not R.exists();R.mkdir(parents=True)
 context={}
 for name in ('world_layout_preview.py','index.html','style.css','viewer.mjs','walk_controller.mjs','horizontal_navigation.mjs','preflight.mjs'):
  shutil.copyfile(C/name,R/name);context[name]={'sha256':sha(C/name),'source':str(C/name)}
 preview=load('world_builder_engine.world_layout_preview',R/'world_layout_preview.py')
 preview.THREE_BUILD=installed_preview.THREE_BUILD
 assert sha(R/'world_layout_preview.py')==sha(E/'world_layout_preview.py')
 i=old['inputs'];prepared_preview=preview.create_preview(i['geometry_source']['path'],i['research_packet']['path'],i['blueprint']['path'])
 frozen=preview.verify_preview(prepared_preview['manifest_path'],prepared_preview['manifest_sha256'])
 for key,row in i.items():
  if key in ('geometry_source','research_packet','blueprint') or key.startswith('research_cache_'):assert frozen['inputs'][key]==row
 assert frozen['presentation_setting']==old['presentation_setting']
 assert Path(prepared_preview['manifest_path']).is_relative_to(H/'runtime_context')
 put(O/'PREVIEW-RESULT.json',{'status':'ISOLATED_IMMUTABLE059_PREVIEW_CREATED','current':prepared_preview,'context':context,
  'backend_bytes_identical_to_installed':True,'renderer_sha256':sha(C/'viewer.mjs'),'preview_server_or_ui_started':False,
  'previous_pointer':previous,'installed056_binding':binding,'presentation':frozen['presentation_setting']})
 api=load('world_builder_engine.layout_package_export059',C/'layout_package_export.py');api.PROJECT=K
 assert api.verify_preview is preview.verify_preview
 new_binding={'manifest_path':prepared_preview['manifest_path'],'manifest_sha256':prepared_preview['manifest_sha256']}
 prepared=api.inspect_selected_layout(job,preview_binding=new_binding)
 assert prepared['presentation']==refreshed['presentation'] and prepared['eligibility']['eligibility_only']
 result=api.export_saved_layout_package(job,O/'package',preview_binding=new_binding)
 put(O/'API-RESULT.json',{'result':result,'installed':False,'candidate_api_sha256':sha(C/'layout_package_export.py'),
  'preview_manifest_sha256':new_binding['manifest_sha256'],'presentation':prepared['presentation']})
 assert result['status']=='created',result
 package=json.loads((O/'package/manifest.json').read_bytes());report=json.loads((O/'package/ROUNDTRIP.json').read_bytes())
 assert package['presentation_setting']==report['presentation_setting']==frozen['presentation_setting']
 assert report['status']=='CPU_AUTHORED_GLB_EXPORT_IMPORT_PASS' and report['glb_sha256']==sha(O/'package/scene.glb')
 assert report['checks']['airlock_pair_metadata_preserved'] is True
 assert report['checks']['airlock_pairs']==package['airlock_pair_policy']
 for pair in package['airlock_pair_policy']:assert pair['pressure_simulation'] is False and pair['engine_runtime_included'] is False
 for name,pin in package['files'].items():assert sha(O/'package'/name)==pin['sha256'] and (O/'package'/name).stat().st_size==pin['bytes']
 # Immutable preview privately references the source brief; portable package must not carry it.
 prompt=frozen['presentation_source_brief']['prompt'].encode()
 for path in (O/'package').iterdir():
  raw=path.read_bytes();assert prompt not in raw and b'presentation_source_brief' not in raw,path
 assert api.inspect_selected_layout(job,preview_binding=new_binding)==prepared
 assert preview.verify_preview(new_binding['manifest_path'],new_binding['manifest_sha256'])==frozen
 sys.modules['world_builder_engine.world_layout_preview']=installed_preview
 assert latest_preview(job)==previous
 assert installed_preview.verify_preview(binding['manifest_path'],binding['manifest_sha256'])==old
 installed_preview.verify_preview(previous['manifest_path'],previous['manifest_sha256'])
 put(O/'SOURCE-CONSISTENCY.json',{'status':'PASS','selected_job_id':job.name,'preview_manifest_sha256':new_binding['manifest_sha256'],
  'source_chain_and_presentation_rechecked':True,'selected_pointer_unchanged':True,'exported_raw_brief':False,
  'package_source_digests':package['verified_source_digests'],'counts':report['counts'],
  'pressure_simulation':False,'engine_native_controls':False,'visual_or_owner_approval':False})
 print(json.dumps({'status':'ISOLATED059_CPU_EXPORT_CREATED','glb_sha256':report['glb_sha256']}))
def main():
 if '--child' in sys.argv:return child()
 plan=json.loads((H/'INSTALL-PLAN.json').read_bytes());source_check(plan)
 start_free=psutil.virtual_memory().available
 assert start_free>=5*1024**3,'Need5GiB free RAM before export; Studio retains priority'
 assert not O.exists() and not R.exists();O.mkdir()
 refresh=json.loads((P/'installed-preview-001/REFRESH-RESULT.json').read_bytes());protected={}
 for key in ('current','previous'):protected.update(inventory(Path(refresh[key]['manifest_path']).parent))
 for name in ('world-installed-observation-export-057','world-observation-viewport-053','world-observation-setting-054','world-door-targeting-candidate-051'):
  folder=W/name/'actual-001/package'
  if folder.exists():protected.update(inventory(folder))
 put(O/'PROTECTED-DERIVED-FILES.json',{'files':protected,'originals_inventory_sha256':sha(H/'INSTALL-PLAN.json')})
 peak=0;samples=0;owned={};reason=None;started=time.monotonic();minimum_free=start_free
 with (O/'stdout.log').open('xb') as stdout,(O/'stderr.log').open('xb') as stderr,(O/'RESOURCES.jsonl').open('x',encoding='utf-8') as trace:
  proc=subprocess.Popen([sys.executable,'-B',str(Path(__file__)), '--child'],stdout=stdout,stderr=stderr,
   env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},creationflags=subprocess.CREATE_NO_WINDOW)
  parent=psutil.Process(proc.pid);owned[proc.pid]=parent.create_time()
  while True:
   family=[]
   for pid,born in list(owned.items()):
    try:
     p=psutil.Process(pid)
     if p.create_time()!=born:continue
     family.append(p)
     for q in p.children(recursive=True):
      if q.pid not in owned:owned[q.pid]=q.create_time();family.append(q)
    except (psutil.NoSuchProcess,psutil.AccessDenied):continue
   live={p.pid:p for p in family};rss=0;identities=[]
   for p in live.values():
    try:
     m=p.memory_info();rss+=m.rss;identities.append({'pid':p.pid,'create_time':owned[p.pid],'name':p.name(),'rss':m.rss,'os_peak':getattr(m,'peak_wset',m.rss)})
    except (psutil.NoSuchProcess,psutil.AccessDenied):pass
   free=psutil.virtual_memory().available;elapsed=time.monotonic()-started;peak=max(peak,rss);minimum_free=min(minimum_free,free);samples+=1
   trace.write(json.dumps({'seconds':elapsed,'family_rss':rss,'free_ram':free,'identities':identities})+'\n')
   if rss>.8*1024**3 or free<3*1024**3 or elapsed>150:
    reason='Owned export resource/deadline limit exceeded'
    for pid,born in reversed(list(owned.items())):
     try:
      p=psutil.Process(pid)
      if p.create_time()==born:p.kill()
     except psutil.NoSuchProcess:pass
    proc.wait(timeout=5);break
   if proc.poll() is not None and not live:break
   time.sleep(.01)
  proc.wait(timeout=5)
 remaining=[]
 for pid,born in owned.items():
  try:
   if psutil.Process(pid).create_time()==born:remaining.append(pid)
  except psutil.NoSuchProcess:pass
 source_check(plan);assert all(sha(p)==s for p,s in protected.items())
 result={'status':'ISOLATED059_CPU_EXPORT_PASS' if not reason and proc.returncode==0 and not remaining else 'HELD_CPU_EXPORT',
  'root_authorization':'Root approved isolated059 CPU export/import,0.8GiB family cap,5GiB start and3GiB reserve; no rendering/UI/install.',
  'created_utc':datetime.datetime.now(datetime.UTC).isoformat(),'elapsed_seconds':time.monotonic()-started,'exit_code':proc.returncode,
  'start_available_ram_bytes':start_free,'minimum_available_ram_bytes':minimum_free,
  'sampled_family_peak_rss_bytes':peak,'samples':samples,'rss_cap_bytes':int(.8*1024**3),'ram_reserve_bytes':3*1024**3,'deadline_seconds':150,
  'owned_identities':[{'pid':p,'create_time':t} for p,t in owned.items()],'remaining_owned_pids':remaining,'failure':reason,
  'protected_originals_unchanged':116,'previous_derived_files_unchanged':len(protected),'canonical_unchanged':True,
  'frozen059_files_unchanged':69,'native_UI_GPU_models':0,'visual_or_owner_approval':False,
  'sampling_limit':'Supervisor excluded;10ms sampling can miss transient peaks.'}
 put(H/'SUPERVISOR.json',result);print(json.dumps(result))
 if result['status']!='ISOLATED059_CPU_EXPORT_PASS':raise SystemExit(1)
if __name__=='__main__':main()
