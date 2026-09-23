"""Serve the exact isolated059 preview only after a pinned terminal Studio012 receipt."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,sys,time
import psutil

H=Path(__file__).resolve().parents[1];K=Path('@kira_root');E=K/'tools/world_builder_engine'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def put(path,value):
 with path.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2);f.write('\n')
def unchanged():
 plan=json.loads((H/'INSTALL-PLAN.json').read_bytes())
 assert all(sha(Path(path))==digest for path,digest in plan['protected_inputs'].items())
 assert all(sha(K/rel)==row['sha256'] for rel,row in json.loads((H/'SOURCE-PINS.json').read_bytes()).items())
 frozen=json.loads((H/'FROZEN-MANIFEST.json').read_bytes())['files']
 assert all(sha(H/rel)==row['sha256'] for rel,row in frozen.items())
def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--closed-studio012-sha256',required=True)
 parser.add_argument('--serve',action='store_true');parser.add_argument('--seconds',type=int,default=300)
 args=parser.parse_args();assert 1<=args.seconds<=600
 receipt=H.parent/'studio-garden-video-chat-live-012/actual-run-001/SUPERVISOR.json'
 assert sha(receipt)==args.closed_studio012_sha256,'Root must supply the exact terminal012 receipt digest'
 closed=json.loads(receipt.read_bytes())
 assert closed.get('cleanup_pending') is False and closed.get('remaining_owned_pids')==[]
 assert closed.get('job_closed') is True and closed.get('owner_state_unchanged') is True
 assert closed.get('status') in ('NATIVE_SOUND_VIDEO_READY_FOR_REVIEW','FAILED')
 assert psutil.virtual_memory().available>=5*1024**3
 unchanged()
 sys.dont_write_bytecode=True;sys.path.insert(0,str(K/'tools'))
 import world_builder_engine.world_layout_preview as installed
 path=H/'runtime_context/tools/world_builder_engine/world_layout_preview.py'
 assert sha(path)==sha(E/'world_layout_preview.py')
 spec=importlib.util.spec_from_file_location('isolated059_preview',path);preview=importlib.util.module_from_spec(spec);spec.loader.exec_module(preview)
 preview.THREE_BUILD=installed.THREE_BUILD
 selected=json.loads((H/'actual-001/PREVIEW-RESULT.json').read_bytes())['current']
 assert selected['manifest_sha256']=='6339588041a8d1ab39dc82d02d007fa9340c2cd18708faa6b509bacf3bc1486c'
 manifest=preview.verify_preview(selected['manifest_path'],selected['manifest_sha256'])
 if not args.serve:
  print(json.dumps({'status':'READY_NO_SERVER_STARTED','manifest_sha256':selected['manifest_sha256']}));return
 output=H/'native-review-001';assert not output.exists();output.mkdir()
 stop=output/'STOP';started=time.monotonic();server=preview.make_server(selected['manifest_path'],0,selected['manifest_sha256']);server.timeout=.5
 put(output/'STARTED.json',{'url':'http://127.0.0.1:'+str(server.server_port)+'/',
  'pid':psutil.Process().pid,'create_time':psutil.Process().create_time(),'lease_seconds':args.seconds,
  'closed_studio012_receipt_sha256':args.closed_studio012_sha256,'preview_manifest_sha256':selected['manifest_sha256'],
  'browser_started':False,'installed':False})
 print((output/'STARTED.json').read_text(encoding='utf-8'),flush=True)
 reason='lease_expired'
 try:
  while time.monotonic()-started<args.seconds:
   if stop.exists():reason='root_stop_file';break
   if psutil.virtual_memory().available<3*1024**3:reason='free_RAM_reserve';break
   server.handle_request()
 finally:
  server.server_close();unchanged()
  assert preview.verify_preview(selected['manifest_path'],selected['manifest_sha256'])==manifest
  put(output/'CLOSED.json',{'status':'OWNED059_PREVIEW_SERVER_CLOSED','reason':reason,'elapsed_seconds':time.monotonic()-started,
   'protected_originals_unchanged':116,'canonical_files_unchanged':42,'old_previews_unchanged':True,
   'browser_cleanup_requires_root':True,'visual_approval_not_inferred':True})
if __name__=='__main__':main()
