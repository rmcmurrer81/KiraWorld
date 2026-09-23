"""Deferred API-only preview refresh after the exact039 plan is installed.

Does not start a server, browser, native window, model, research or export job.
It may create one new immutable preview directory; source files stay unchanged.
"""
from pathlib import Path
import argparse,hashlib,json,sys
H=Path(__file__).resolve().parent;K=Path('@kira_root')
sys.dont_write_bytecode=True;sys.path.insert(0,str(K/'tools'))

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--job',required=True);parser.add_argument('--receipt',required=True)
 args=parser.parse_args();receipt=Path(args.receipt).resolve();plan=json.loads((H/'INSTALL-PLAN.json').read_bytes())
 assert not receipt.exists() and receipt.parent.is_dir(),'Choose a new receipt in an existing work directory'
 assert not receipt.is_relative_to(K/'Data'),'Do not write a receipt inside owner data'
 assert all(sha(row['target'])==row['after']['sha256'] for row in plan['files']),'Exact039 installation required before refresh'
 context=json.loads((H/'PREVIEW-CONTEXT-PINS.json').read_bytes())
 assert all(sha(K/relative)==digest for relative,digest in context.items()),'Preview context changed; review before continuing'
 protected=plan['protected_inputs'];assert all(sha(p)==digest for p,digest in protected.items())
 from world_builder_engine.pipeline import latest_preview
 from world_builder_engine.preview_refresh import refresh_saved_preview
 from world_builder_engine.world_layout_preview import verify_preview
 job=Path(args.job).resolve();before=latest_preview(job);verify_preview(before['manifest_path'],before['manifest_sha256'])
 refreshed=refresh_saved_preview(job);current=verify_preview(refreshed['manifest_path'],refreshed['manifest_sha256'])
 assert current['source_pins']['walk_controller.mjs']['sha256']=='0884cce50d33a66e4a974a76fc7a0a15947bcb776f130b1b0a81b43adef76791'
 assert latest_preview(job)==before,'Saved job pointer unexpectedly changed'
 assert all(sha(p)==digest for p,digest in protected.items()),'Protected source changed'
 verify_preview(before['manifest_path'],before['manifest_sha256'])
 result={'status':'039_API_ONLY_CURRENT_PREVIEW_PREPARED','job':str(job),'previous':before,'current':refreshed,
  'protected_original_files_unchanged':len(protected),'saved_pointer_unchanged':True,'server_browser_native_ui_model_export_calls':0,
  'visual_approval':False,'next':'Pass current.manifest_path and current.manifest_sha256 explicitly to run_real_api.py; visual review remains pending.'}
 with receipt.open('x',encoding='utf-8') as out:json.dump(result,out,indent=2);out.write('\n')
 print(json.dumps(result));return 0
if __name__=='__main__':raise SystemExit(main())
