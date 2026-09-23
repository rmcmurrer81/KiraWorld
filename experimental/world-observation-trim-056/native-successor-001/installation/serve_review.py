"""Explicit, bounded loopback review server. No automatic browser or camera input.

Root must first confirm Studio014 has exited and its owned workers are cleaned up.
Without --serve this only validates the review copy and prints the manifest pin.
"""
from pathlib import Path
import argparse,datetime,importlib.util,json,os,threading,time
import install_exact as guard

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--serve',metavar='EXACT_MANIFEST_SHA');parser.add_argument('--duration-seconds',type=int,default=600);args=parser.parse_args()
 assert 30<=args.duration_seconds<=600
 contract=json.loads((guard.H/'installation/REVIEW-BINDING.json').read_bytes())
 provenance=guard.verify_presentation_path();plan=json.loads((guard.H/'INSTALL-PLAN.json').read_bytes())
 guard.check_candidate_closure();guard.check_other_sources(plan);guard.validate(plan,guard.K,guard.H)
 if not args.serve:
  print(json.dumps({'status':'056_REVIEW_SERVER_NOT_STARTED','manifest_sha256':contract['preview_manifest_sha256'],'provenance':provenance}));return
 assert args.serve==contract['preview_manifest_sha256'],'Bind the exact review manifest'
 runtime=guard.H/'runtime_context/tools/world_builder_engine/world_layout_preview.py'
 spec=importlib.util.spec_from_file_location('review056_preview',runtime);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 module.THREE_BUILD=guard.K/'Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/node_modules/three/build'
 server=module.make_server(contract['preview_manifest_path'],expected_manifest_sha256=args.serve)
 stamp=datetime.datetime.now(datetime.UTC).strftime('%Y%m%dT%H%M%S%fZ');run=guard.H/'installation'/('review-run-'+stamp);run.mkdir()
 stop=run/'STOP';ready={'status':'056_OWNED_LOOPBACK_REVIEW_SERVER','pid':os.getpid(),'url':'http://127.0.0.1:'+str(server.server_port),
  'stop_file':str(stop),'duration_limit_seconds':args.duration_seconds,'preview_manifest_sha256':args.serve,'automatic_browser_or_input':False}
 (run/'READY.json').write_text(json.dumps(ready,indent=2)+'\n',encoding='utf-8');print(json.dumps(ready),flush=True)
 thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();started=time.monotonic()
 try:
  while time.monotonic()-started<args.duration_seconds and not stop.exists():time.sleep(.2)
 finally:
  server.shutdown();server.server_close();thread.join(timeout=3)
  closed={'status':'CLOSED','server_thread_closed':not thread.is_alive(),'seconds':time.monotonic()-started,'preview_manifest_sha256':args.serve,'preview_and_owner_files_modified':False}
  (run/'CLOSED.json').write_text(json.dumps(closed,indent=2)+'\n',encoding='utf-8');print(json.dumps(closed),flush=True)
if __name__=='__main__':main()
