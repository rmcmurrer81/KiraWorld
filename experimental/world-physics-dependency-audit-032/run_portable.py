"""Replay frozen CPU snapshots away from the preserved historical receipts."""
from pathlib import Path
import argparse,json,shutil,subprocess,tempfile

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--node',default='node');args=parser.parse_args()
 here=Path(__file__).resolve().parent;temp_base=Path(tempfile.gettempdir()).resolve()
 stage=Path(tempfile.mkdtemp(prefix='world-replay-',dir=temp_base)).resolve()
 assert stage.parent==temp_base and stage.name.startswith('world-replay-')
 try:
  shutil.copytree(here,stage/'snapshot');root=stage/'snapshot'
  plan=json.loads((root/'PLAN.json').read_text(encoding='utf-8'))
  is032=(root/'check_relation.mjs').exists()
  for row in plan['sources']:
   row['path']=str(root/(row['snapshot'] if is032 else 'baseline/'+row['name']))
  (root/'PLAN.json').write_text(json.dumps(plan),encoding='utf-8')
  if is032:
   script=root/'check_relation.mjs';script.write_text(script.read_text(encoding='utf-8').replace('actual_installed015','portable_frozen015'),encoding='utf-8')
   jobs=[('check_relation.mjs',0)];outputs=['RESULT.json']
  else:
   pins=json.loads((root/'DIAGNOSTIC-PINS.json').read_text(encoding='utf-8'))
   for row in pins:row['source']=str(root/('/'.join(row['source'].replace('\\','/').split('/')[-2:])))
   (root/'DIAGNOSTIC-PINS.json').write_text(json.dumps(pins),encoding='utf-8')
   jobs=[('check_contact.mjs',1),('check_mixed_clarification.mjs',0),('check_default.mjs',0),('check_default_geometry.mjs',0)]
   outputs=['CONTACT-RESULT.json','MIXED-CLARIFICATION.json','DEFAULT-RESULT.json','DEFAULT-GEOMETRY-DIAGNOSIS.json']
  for name in outputs:
   target=(root/name).resolve();assert target.parent==root.resolve();target.unlink(missing_ok=True)
  outcomes=[]
  for script,expected in jobs:
   done=subprocess.run([args.node,'--max-old-space-size=384',str(root/script)],capture_output=True,text=True,timeout=30)
   assert done.returncode==expected,(script,done.stdout,done.stderr)
   outcomes.append({'script':script,'expected_exit':expected,'actual_exit':done.returncode})
  results={name:json.loads((root/name).read_text(encoding='utf-8')).get('status') for name in outputs}
  print(json.dumps({'status':'PORTABLE_SNAPSHOT_REPLAY_MATCHES_EXPECTED_SCOPED_OUTCOMES','actual_installed_runtime_tested':False,'jobs':outcomes,'results':results,'original_evidence_unchanged':True,'gpu_models':0}))
 finally:
  assert stage.parent==temp_base and stage.name.startswith('world-replay-')
  shutil.rmtree(stage)

if __name__=='__main__':main()
