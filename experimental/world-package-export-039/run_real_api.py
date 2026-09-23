"""Deferred root-supervised real API check. Do not run during the Studio render."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,sys,types
H=Path(__file__).resolve().parent;K=Path('@kira_root')
sys.dont_write_bytecode=True;sys.path.insert(0,str(K/'tools'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for field in ('job','manifest','manifest-sha256','output'):p.add_argument('--'+field,required=True)
 args=p.parse_args();protected=json.loads((H/'INSTALL-PLAN.json').read_text())['protected_inputs']
 assert all(sha(path)==value for path,value in protected.items())
 source=H/'candidate/tools/world_builder_engine'
 policy_spec=importlib.util.spec_from_file_location('world_builder_engine.layout_airlock_policy',source/'layout_airlock_policy.py');policy=importlib.util.module_from_spec(policy_spec);policy_spec.loader.exec_module(policy);sys.modules[policy_spec.name]=policy
 package=types.ModuleType('world_builder_engine.layout_package_assets');package.__path__=[str(source/'layout_package_assets')]
 sys.modules[package.__name__]=package
 spec=importlib.util.spec_from_file_location('world_builder_engine.layout_package_export039',source/'layout_package_export.py');api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api);api.PROJECT=K
 result=api.export_saved_layout_package(args.job,args.output,preview_binding={'manifest_path':args.manifest,'manifest_sha256':args.manifest_sha256})
 assert all(sha(path)==value for path,value in protected.items())
 receipt={'status':'REAL_API_EXPORT_PASS' if result['status']=='created' else 'REAL_API_EXPORT_HELD','result':result,'protected_original_files_unchanged':len(protected),'installed':False,'native_ui_opened':False,'gpu_models_browser':0}
 target=H/('REAL-API-RESULT-'+str(len(list(H.glob('REAL-API-RESULT-*.json')))+1)+'.json');target.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps(receipt));return 0 if result['status']=='created' else 1
if __name__=='__main__':raise SystemExit(main())
