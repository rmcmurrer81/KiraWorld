"""Root-approved isolated CPU trials; never install or open a preview/UI."""
from pathlib import Path
import datetime,hashlib,importlib.util,json,os,subprocess,sys,time,types
import psutil
H=Path(__file__).resolve().parent;W=H.parent;K=Path('@kira_root');C=H/'candidate/tools/world_builder_engine';A=C/'layout_package_assets'
sys.dont_write_bytecode=True;sys.path.insert(0,str(K/'tools'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module
def json_write(path,value):
 with Path(path).open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2);stream.write('\n')

def child(variant):
 folder=H/'trials-001'/variant;output=folder/'package'
 profile=load('world_builder_engine.layout_recipe_profile',C/'layout_recipe_profile.py')
 package=types.ModuleType('world_builder_engine.layout_package_assets');package.__path__=[str(A)];sys.modules[package.__name__]=package
 api=load('world_builder_engine.layout_package_export041',C/'layout_package_export.py');api.PROJECT=K;bindings=api.bindings
 if variant=='mars':
  manifest=K/'Data/world_layout_previews/layout-174d4bddd3f8efcf689c7e40/manifest.json'
  result=api.export_saved_layout_package(K/'Data/world_research_jobs/world_research_c391ffbffc7352612392',output,
   preview_binding={'manifest_path':str(manifest),'manifest_sha256':'ef58d7b81e37182f86dd22defea9294ccfa4b1696fb7bb3810ca80069b85fe0a'})
  json_write(folder/'API-RESULT.json',{'variant':'saved_Mars_regression','result':result,'candidate_installed':False,'existing039_unchanged':True,'ui_calls':0})
  assert result['status']=='created',result
 else:
  from fixture_builder import build_fixture
  sources=folder/'synthetic_sources';sources.mkdir()
  packet=sources/'research_packet.json';json_write(packet,{'packet_kind':'world_public_text_research_packet','research_mode':'analog_to_original','sources':[],
   'fixture_notice':'Synthetic engineering test input; no researched fact, real place or owner source claim.'})
  blueprint,geometry=build_fixture(sha(packet),variant);bp=sources/'blueprint.json';gp=sources/'geometry.json';json_write(bp,blueprint);json_write(gp,geometry)
  bound=sources/'bindings.json';json_write(bound,{'contract':bindings.INPUT_CONTRACT,'inputs':{name:bindings.binding(p) for name,p in [('geometry_source',gp),('blueprint',bp),('research_packet',packet)]}})
  g,verified,input_pin=bindings.source_chain(bound,sha(bound));eligible=profile.validate_recipe_profile(g,blueprint,sha(packet))
  runtime=api.verify_dependencies();pins=runtime['pins'];loc=runtime['locations'];output.mkdir()
  options={'sceneId':'synthetic_'+variant,'sourceDigests':{'geometry':verified['geometry_source']['sha256'],
   'dressing_recipe':pins['files']['source/room_dressing_plan.mjs']['sha256'],'door_controller':pins['files']['source/walk_controller.mjs']['sha256']}}
  request={'geometry':g,'options':options,'output':str(output),'canvasModule':str(Path(loc['canvas-package']).parent),
   'fontPaths':[[str(loc['font-segoe-regular']),'Segoe UI'],[str(loc['font-segoe-semibold']),'Segoe UI'],[str(loc['font-monospace']),'Consolas']]}
  run=subprocess.run([str(loc['node']),str(A/'build_glb.mjs')],input=bindings.canonical(request),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
  (folder/'worker.stdout.log').write_bytes(run.stdout);(folder/'worker.stderr.log').write_bytes(run.stderr);assert run.returncode==0,run.stderr.decode()
  for row in [input_pin,*verified.values()]:bindings.exact(row)
  api.verify_dependencies();scene=bindings.parse(bindings.read(output/'scene.json'));pairs=api.validate_airlock_metadata(scene,g,options['sourceDigests'])
  report=bindings.parse(bindings.read(output/'ROUNDTRIP.json'));assert report['status']=='CPU_AUTHORED_GLB_EXPORT_IMPORT_PASS' and report['glb_sha256']==sha(output/'scene.glb')
  assert report['checks']['airlock_pair_metadata_preserved'] and report['checks']['airlock_pairs']==pairs
  json_write(output/'manifest.json',{'contract':'synthetic_authored_export_validation_trial_v1','status':'passed','synthetic_fixture':variant,
   'verified_input_digests':bindings.portable_pins(verified),'producer_digests':pins,'recipe_eligibility':eligible,'airlock_pairs':pairs,
   'files':{p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in output.iterdir()},'ui_models_gpu':0,'installed':False,'visual_approval':False})
 report=json.loads((output/'ROUNDTRIP.json').read_bytes())
 print(json.dumps({'variant':variant,'status':'ACTUAL041_CPU_EXPORT_IMPORT_PASS','package_manifest_sha256':sha(output/'manifest.json'),
  'glb_sha256':sha(output/'scene.glb'),'glb_bytes':(output/'scene.glb').stat().st_size,'counts':report['counts']}))

def main():
 if len(sys.argv)>1:
  assert sys.argv[1]=='--child' and sys.argv[2] in ('renamed','wider','mars');child(sys.argv[2]);return
 root=H/'trials-001';assert not root.exists();root.mkdir()
 protected=json.loads((H/'INSTALL-PLAN-REV2.json').read_bytes())['protected_inputs'];base=json.loads((H/'BASELINE-PINS.json').read_bytes())
 assert all(sha(p)==v for p,v in protected.items());assert all(sha(K/r)==v for r,v in base.items())
 results=[]
 for variant in ('renamed','wider','mars'):
  folder=root/variant;folder.mkdir();processes={};peak=0;samples=0
  with (folder/'stdout.log').open('xb') as stdout,(folder/'stderr.log').open('xb') as stderr:
   started=time.perf_counter();proc=subprocess.Popen([sys.executable,str(Path(__file__)), '--child',variant],stdout=stdout,stderr=stderr,
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},creationflags=subprocess.CREATE_NO_WINDOW);parent=psutil.Process(proc.pid)
   while proc.poll() is None:
    try:family=[parent,*parent.children(recursive=True)]
    except psutil.NoSuchProcess:family=[]
    rss=0
    for p in family:
     try:
      memory=p.memory_info();rss+=memory.rss;row=processes.setdefault(str(p.pid),{'name':p.name(),'observed_rss':0,'os_peak_working_set':0})
      row['observed_rss']=max(row['observed_rss'],memory.rss);row['os_peak_working_set']=max(row['os_peak_working_set'],getattr(memory,'peak_wset',memory.rss))
     except (psutil.NoSuchProcess,psutil.AccessDenied):pass
    peak=max(peak,rss);samples+=1
    if time.perf_counter()-started>180:
     for p in reversed(family):
      try:p.terminate()
      except psutil.NoSuchProcess:pass
     raise TimeoutError('Owned isolated trial timed out')
    time.sleep(.01)
   elapsed=time.perf_counter()-started
  result={'variant':variant,'returncode':proc.returncode,'elapsed_seconds':elapsed,'sampled_family_peak_rss_bytes':peak,'samples':samples,'processes':processes}
  if proc.returncode==0:result['export']=json.loads((folder/'stdout.log').read_bytes())
  else:result['error']=(folder/'stderr.log').read_text()[-3000:]
  results.append(result);json_write(folder/'MEASURED-RESULT.json',result)
  assert all(sha(p)==v for p,v in protected.items());assert all(sha(K/r)==v for r,v in base.items())
  if proc.returncode:break
 passed=len(results)==3 and all(r['returncode']==0 for r in results)
 report={'status':'THREE_ACTUAL041_EXPORT_IMPORT_TRIALS_PASS' if passed else 'ACTUAL041_TRIAL_HELD','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),
  'root_authorized':True,'results':results,'protected_original_files_unchanged':len(protected),'installed039_unchanged':True,'candidate041_installed':False,
  'sample_interval_seconds':.01,'measurement_scope':'Launched child process and descendants only, supervisory process excluded; sampled RSS may miss brief peaks.',
  'native_ui_models_gpu':0,'visual_or_owner_approval':False}
 json_write(H/'ACTUAL-TRIAL-RESULT.json',report);print(json.dumps(report));raise SystemExit(not passed)
if __name__=='__main__':main()
