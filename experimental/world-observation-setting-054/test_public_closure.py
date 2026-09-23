"""Replay synthetic navigation, viewport and setting checks without owner inputs."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,tempfile
H=Path(__file__).resolve().parent
node=os.environ.get('KIRA_TEST_NODE') or shutil.which('node') or 'C:/Program Files/nodejs/node.exe'
names=('world-door-traversal-audit-052','world-observation-viewport-053','world-observation-setting-054');results=[]
with tempfile.TemporaryDirectory(prefix='world054-public-') as name:
 root=Path(name);assert root.resolve().parent==Path(tempfile.gettempdir()).resolve()
 for package in names:
  source=H.parent/package;dest=root/package;dest.mkdir()
  for part in ('candidate','baseline','preimages'):
   if (source/part).exists():shutil.copytree(source/part,dest/part)
  if package.endswith('052'):scripts=['audit.mjs']
  elif package.endswith('053'):scripts=['test_viewport.mjs']
  else:scripts=['test_setting.py','test_geometry_setting.mjs'];(dest/'fixtures').mkdir();shutil.copyfile(source/'fixtures/synthetic-habitat.json',dest/'fixtures/synthetic-habitat.json')
  for script in scripts:shutil.copyfile(source/script,dest/script)
 fixture=root/names[2]/'fixtures/synthetic-habitat.json';digest=hashlib.sha256(fixture.read_bytes()).hexdigest()
 engine=root/names[0]/'baseline/tools/world_builder_engine'
 commands=[(names[0],[node,'audit.mjs',str(fixture),digest,str(engine)]),(names[1],[node,'test_viewport.mjs',str(fixture),digest]),
           (names[2],[sys.executable,'-B','test_setting.py','--synthetic-only']),(names[2],[node,'test_geometry_setting.mjs'])]
 for package,cmd in commands:
  run=subprocess.run(cmd,cwd=root/package,capture_output=True,text=True,timeout=15,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
  if run.returncode:raise RuntimeError(package+' '+run.stdout+run.stderr)
  results.append({'package':package,'result':json.loads(run.stdout)})
print(json.dumps({'status':'PUBLIC_SYNTHETIC_NAVIGATION_VIEWPORT_SETTING_CLOSURE_PASS','fixture_sha256':digest,'results':results,'owner_source_reads_or_writes':0,'gpu_models_browser_native_ui':0,'real_export_rerun':False,'original_owner_recheck':False}))
