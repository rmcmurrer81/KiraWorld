"""Replay only synthetic-source regression tests in an isolated temporary copy."""
from pathlib import Path
import argparse,json,os,shutil,subprocess,sys,tempfile
parser=argparse.ArgumentParser();parser.add_argument('--node',default=shutil.which('node'));args=parser.parse_args()
here=Path(__file__).resolve().parent;parent=Path(tempfile.gettempdir()).resolve()
temp=Path(tempfile.mkdtemp(prefix='world-owner034-',dir=parent)).resolve()
assert temp.parent==parent and temp.name.startswith('world-owner034-')
try:
 root=temp/'copy';shutil.copytree(here,root)
 for relative in ['OWNERSHIP-RESULT.json','package/OWNER-PACKAGE-RESULT.json']:
  path=(root/relative).resolve();assert path.is_relative_to(root.resolve());path.unlink()
 env=dict(os.environ);env['PATH']=str(Path(args.node).resolve().parent)+os.pathsep+env.get('PATH','')
 commands=[
  [args.node,'--max-old-space-size=384',str(root/'test_ownership.mjs')],
  [args.node,'--max-old-space-size=384',str(root/'core/test_metadata.mjs'),'-902'],
  [sys.executable,'-B',str(root/'package/test_package.py')],
  [sys.executable,'-B',str(root/'package/test_owner_package.py')],
  [sys.executable,'-B',str(root/'package/make_example.py'),'--destination',str(temp/'new-example')],
  [sys.executable,'-B',str(root/'package/package_writer.py'),'verify','--package',str(root/'actual-mars-001')]]
 for command in commands:
  run=subprocess.run(command,env=env,capture_output=True,text=True,timeout=30)
  assert run.returncode==0,(command,run.stdout,run.stderr)
 out={'status':'PASS_PORTABLE034_CLOSURE','ownership_groups':10,'inherited_metadata_groups':11,'inherited_package_tests':15,'additional_package_gates':4,
  'default_core_example_created':True,'derived_actual_package_integrity':'PASS','actual_owner_source_files_needed_or_opened':False,
  'metadata_only':True,'gpu_models':0,'canonical_files_changed':False}
 print(json.dumps(out))
finally:
 assert temp.parent==parent and temp.name.startswith('world-owner034-')
 shutil.rmtree(temp)
