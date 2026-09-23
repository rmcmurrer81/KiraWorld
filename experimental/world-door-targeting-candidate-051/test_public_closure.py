"""Portable synthetic door, UI-callback and recovery checks; no owner reads."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,tempfile
H=Path(__file__).resolve().parent
node=os.environ.get('KIRA_TEST_NODE') or shutil.which('node') or 'C:/Program Files/nodejs/node.exe'
results=[]
with tempfile.TemporaryDirectory(prefix='world051-public-') as name:
 root=Path(name)
 for package in ('world-door-targeting-candidate-050','world-door-targeting-candidate-051'):
  source=H.parent/package;dest=root/package;dest.mkdir()
  for part in ('candidate','baseline','preimages','fixtures'):
   if (source/part).exists():shutil.copytree(source/part,dest/part)
  scripts=['test_viewer_messages.mjs']
  if package.endswith('050'):scripts+=['test_actual_doors.mjs']
  else:scripts+=['test_frontend_doors.mjs','test_portable_doors.mjs','test_portable_contract.mjs','install_exact.py','test_installer.py']
  for script in scripts:
   text=(source/script).read_text(encoding='utf8')
   # Change reporting labels only for synthetic replay; historical actual-Mars
   # receipts and frozen original test files are never overwritten.
   if script.endswith('.mjs'):text=text.replace('Actual saved','Synthetic').replace('Actual furnished','Synthetic furnished').replace('Actual airlock','Synthetic airlock').replace('Actual two-leaf','Synthetic two-leaf').replace('All six actual','All six synthetic').replace('ACTUAL_SAVED_MARS','SYNTHETIC_HABITAT')
   (dest/script).write_text(text,encoding='utf8',newline='\n')
 fixture=H/'fixtures/synthetic-habitat.json';digest=hashlib.sha256(fixture.read_bytes()).hexdigest()
 engine=root/'world-door-targeting-candidate-051/candidate/tools/world_builder_engine'
 for package,script in [('world-door-targeting-candidate-050','test_actual_doors.mjs'),('world-door-targeting-candidate-051','test_frontend_doors.mjs'),('world-door-targeting-candidate-051','test_portable_doors.mjs'),('world-door-targeting-candidate-051','test_portable_contract.mjs')]:
  result=subprocess.run([node,script,str(fixture),digest,str(engine)],cwd=root/package,capture_output=True,text=True,timeout=10)
  if result.returncode:raise RuntimeError(package+' '+script+' failed: '+result.stdout+result.stderr)
  results.append({'package':package,'test':script,'result':json.loads(result.stdout)})
 for package,script,exe in [('world-door-targeting-candidate-050','test_viewer_messages.mjs',node),('world-door-targeting-candidate-051','test_viewer_messages.mjs',node),('world-door-targeting-candidate-051','test_installer.py',sys.executable)]:
  result=subprocess.run([exe,script],cwd=root/package,capture_output=True,text=True,timeout=10,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
  if result.returncode:raise RuntimeError(script+' failed: '+result.stdout+result.stderr)
  results.append({'package':package,'test':script,'result':json.loads(result.stdout)})
print(json.dumps({'status':'PUBLIC_SYNTHETIC_DOOR_AND_RECOVERY_CLOSURE_PASS','fixture_sha256':digest,'results':results,'original_owner_recheck':False,'owner_data_reads_or_writes':0,'export_models_gpu_ui':0}))
