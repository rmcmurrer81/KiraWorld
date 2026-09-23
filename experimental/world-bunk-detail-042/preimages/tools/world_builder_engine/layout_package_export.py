"""Export one explicitly selected saved layout without research or world writes."""
from pathlib import Path
import hashlib,json,os,subprocess
from world_saved_research import read_saved_research
from .pipeline import latest_preview
from .world_layout_preview import verify_preview
from .layout_package_assets import source_bindings as bindings
from .layout_airlock_policy import validate_airlock_metadata
from .layout_recipe_profile import validate_recipe_profile,RecipeUnsupported

PROJECT=Path(__file__).resolve().parents[2]
ASSETS=Path(__file__).resolve().with_name('layout_package_assets')
CONTRACT='authored_saved_layout_package_v2'
RENDERER={
 'viewer.mjs':'e6f101d016cd40b923c678f3db39b1ec7ec50b1c44684f255bcd1efb8b9fcfda',
 'walk_controller.mjs':'0884cce50d33a66e4a974a76fc7a0a15947bcb776f130b1b0a81b43adef76791',
 'horizontal_navigation.mjs':'bae0be9fa5c170aab83d5a63833dfa5b2534ff1e3745df1df71cc94f5652b5f7',
 'three.module.js':'c8211c69345d2e9949dc7a8ac969380497aa0600a5a8ac6a459c8cd02dd9cb8a',
 'three.core.js':'eb077d2417f61d3e6d9264c317cabc4ea35769ed6b0ab533067292a550784c20'}
CAPABILITIES={'experimental':True,'authored_meshes':True,'embedded_textures':True,'door_hinge_hierarchy':True,'linked_collider_metadata':True,'airlock_pair_policy_metadata':True,
 'engine_native_interaction':False,'engine_native_collision':False,'pressure_simulation':False,'vr_runtime':False,'visual_or_owner_approval':False}

class ExportHeld(ValueError):
 def __init__(self,status,message):super().__init__(message);self.status=status
def require(ok,status,message):
 if not ok:raise ExportHeld(status,message)
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as stream:
  for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def seal(value):return hashlib.sha256(bindings.canonical(value)).hexdigest()
def write_json(path,value):
 with Path(path).open('xb') as stream:stream.write(bindings.canonical(value)+b'\n')

def inspect_selected_layout(job_dir,preview_binding=None):
 """Read only this job; an explicit open-preview binding can select its new copy."""
 job=read_saved_research(Path(job_dir),job_root=PROJECT/'Data/world_research_jobs')
 selected=dict(preview_binding) if preview_binding is not None else latest_preview(job['job_dir'])
 require(isinstance(selected,dict) and isinstance(selected.get('manifest_path'),str) and isinstance(selected.get('manifest_sha256'),str),
  'invalid_selection','The selected layout has no verified preview. Open its current preview first.')
 manifest=verify_preview(selected['manifest_path'],selected['manifest_sha256'])
 require(manifest.get('source_mode')=='source_bound_original_layout','unsupported_preview','Only an original saved layout can be exported.')
 require(Path(manifest['inputs']['research_packet']['path']).parent==job['job_dir'],
  'invalid_selection','That preview belongs to a different saved project. Select the intended project again.')
 require(all(manifest['source_pins'].get(k,{}).get('sha256')==v for k,v in RENDERER.items()),
  'unsupported_preview','This saved preview uses an unsupported appearance version. Open current preview, then export again.')
 geometry,sources,input_pin=bindings.source_chain(selected['manifest_path'],selected['manifest_sha256'])
 try:
  eligibility=validate_recipe_profile(geometry,bindings.parse(bindings.exact(sources['blueprint'])),sources['research_packet']['sha256'])
 except RecipeUnsupported as exc:raise ExportHeld(exc.status,str(exc)) from exc
 return {'job':job,'selection':selected,'geometry':geometry,'sources':sources,'input_pin':input_pin,'eligibility':eligibility}

def default_dependencies():
 canvas=Path(os.environ.get('KIRA_CPU_CANVAS_MODULE') or Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@napi-rs/canvas')
 fonts=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'
 return {'node':Path(os.environ.get('KIRA_EXPORT_NODE','C:/Program Files/nodejs/node.exe')),
  'canvas-package':canvas/'package.json','canvas-native':canvas.parent/'canvas-win32-x64-msvc/skia.win32-x64-msvc.node',
  'font-segoe-regular':fonts/'segoeui.ttf','font-segoe-semibold':fonts/'seguisb.ttf','font-monospace':fonts/'consola.ttf',
  **{'canvas/'+name:canvas/name for name in ('index.js','js-binding.js','geometry.js','load-image.js')}}

def verify_dependencies(dependencies=None):
 locations=dependencies if dependencies is not None else default_dependencies()
 pins=bindings.parse(bindings.read(ASSETS/'PRODUCER-PINS.json'))
 for relative,pin in pins['files'].items():
  path=bindings.local_path(ASSETS/relative)
  require(path.is_file() and sha(path)==pin['sha256'],'producer_changed','The installed 3D exporter files changed. Repair the exporter before retrying.')
 for role,pin in pins['external'].items():
  require(role in locations,'dependency_missing','A required local 3D export dependency is not configured: '+role)
  path=bindings.local_path(locations[role])
  require(path.is_file(),'dependency_missing','A required local 3D export dependency is missing: '+role+'. Install or restore the local export runtime; no download was started.')
  require(path.stat().st_size==pin['bytes'] and sha(path)==pin['sha256'],'dependency_changed','A required local 3D export dependency differs from the tested version: '+role)
 return {'locations':locations,'pins':pins}

def export_saved_layout_package(job_dir,destination,*,preview_binding=None,dependencies=None):
 """Create a new output folder; returns structured ready/held state and location.

 No globally newest job lookup, research generation, GPU work, source repair or
 overwrite. Failures after creation retain clearly incomplete output evidence.
 """
 output=None
 try:
  prepared=inspect_selected_layout(job_dir,preview_binding)
  target=bindings.local_path(destination)
  require(not target.exists(),'destination_exists','That export folder already exists. Choose a new folder; existing files were preserved.')
  require(target.parent.is_dir(),'invalid_destination','Choose an existing parent folder for the export.')
  protected=[PROJECT/'Data/world_research_jobs',PROJECT/'Data/world_layout_previews',PROJECT/'Data/world_builds']
  require(not any(target.is_relative_to(path) for path in protected),'invalid_destination','Choose an export folder outside saved worlds and research folders.')
  runtime=verify_dependencies(dependencies);loc=runtime['locations'];pins=runtime['pins']
  opts={'sceneId':'saved_layout_'+prepared['job']['job_id'].removeprefix('world_research_'),
   'sourceDigests':{'geometry':prepared['sources']['geometry_source']['sha256'],
    'dressing_recipe':pins['files']['source/room_dressing_plan.mjs']['sha256'],
    'door_controller':pins['files']['source/walk_controller.mjs']['sha256']}}
  request={'geometry':prepared['geometry'],'options':opts,'output':str(target),
   'canvasModule':str(Path(loc['canvas-package']).parent),
   'fontPaths':[[str(loc['font-segoe-regular']),'Segoe UI'],[str(loc['font-segoe-semibold']),'Segoe UI'],[str(loc['font-monospace']),'Consolas']]}
  target.mkdir(exist_ok=False);output=target
  run=subprocess.run([str(loc['node']),str(ASSETS/'build_glb.mjs')],input=bindings.canonical(request),
   stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
  require(run.returncode==0,'export_failed','The 3D asset could not complete its export checks. The original layout is unchanged.')
  # Recheck the same selected job and manifest, never a newly selected UI job.
  current=inspect_selected_layout(job_dir,prepared['selection'])
  require(current==prepared,'source_changed','The saved layout changed during export. No ready package was issued.')
  if preview_binding is None:
   require(latest_preview(prepared['job']['job_dir'])==prepared['selection'],'source_changed','The saved layout pointer changed during export. No ready package was issued.')
  verify_dependencies(dependencies)
  expected={'scene.glb','scene.json','ROUNDTRIP.json'}
  require({p.name for p in target.iterdir()}==expected,'export_failed','The exporter returned an incomplete asset package.')
  report=bindings.parse(bindings.read(target/'ROUNDTRIP.json'))
  require(report.get('status')=='CPU_AUTHORED_GLB_EXPORT_IMPORT_PASS' and report.get('glb_sha256')==sha(target/'scene.glb'),
   'export_failed','The exported asset did not pass its importer checks.')
  scene=bindings.parse(bindings.read(target/'scene.json'))
  try:
   pairs=validate_airlock_metadata(scene,prepared['geometry'],opts['sourceDigests'])
  except (ValueError,KeyError,TypeError) as exc:
   raise ExportHeld('airlock_policy_invalid','The exported airlock door policy did not match the selected layout. No ready package was issued.') from exc
  require(report.get('checks',{}).get('airlock_pair_metadata_preserved') is True and report['checks'].get('airlock_pairs')==pairs,
   'airlock_policy_invalid','The exported door policy did not pass its importer checks. No ready package was issued.')
  readme='Original authored 3D layout package: scene.glb plus linked collider/door metadata in scene.json. Game-engine interaction/collision and VR runtime are not implemented. Static equipment has no operational science/life-support behavior. No pressure simulation or visual-realism approval. See ROUNDTRIP.json for renderer limitations. Original sources were not changed or bundled.\n'
  with (target/'README.txt').open('x',encoding='utf-8') as stream:stream.write(readme)
  result={'contract':CONTRACT,'status':'created','scene_id':opts['sceneId'],'source_bindings_manifest_sha256':prepared['input_pin']['sha256'],
   'verified_source_digests':bindings.portable_pins(prepared['sources']),'producer_digests':pins,
   'airlock_pair_policy':pairs,'preview_controller_sha256':RENDERER['walk_controller.mjs'],
   'recipe_eligibility':prepared['eligibility'],
   'files':{p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in target.iterdir()},'capabilities':CAPABILITIES,
   'research_regenerated':False,'model_jobs':0,'sources_modified':False}
  result['receipt_sha256']=seal(result);write_json(target/'manifest.json',result)
  return {'status':'created','output_dir':str(target),'manifest_sha256':sha(target/'manifest.json'),'job_id':prepared['job']['job_id'],
   'message':'Your 3D package is ready. It includes meshes, textures and door/collider metadata. Game and VR controls still require an adapter.', 'capabilities':dict(CAPABILITIES)}
 except (OSError,ValueError,KeyError,TypeError,subprocess.TimeoutExpired) as exc:
  status=exc.status if isinstance(exc,ExportHeld) else 'source_or_export_held'
  message=str(exc) if isinstance(exc,ExportHeld) else 'The export was held because a saved source, dependency or output could not be verified. Original files were preserved.'
  if output is not None:
   write_json(output/'EXPORT-INCOMPLETE.json',{'status':status,'message':message,'ready':False,'sources_modified':False})
  return {'status':status,'message':message,'output_dir':str(output) if output else None,'ready':False}
