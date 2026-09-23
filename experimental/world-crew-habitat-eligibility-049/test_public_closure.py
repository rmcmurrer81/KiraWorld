"""Portable parser/callback/planner + installer fixtures; no owner state reads."""
from pathlib import Path
import json,os,shutil,subprocess,sys,tempfile
H=Path(__file__).resolve().parent;checkout=Path(os.environ.get('KIRA_TEST_ROOT',str(H.parents[1]))).resolve()
results=[]
with tempfile.TemporaryDirectory(prefix='world049-public-') as name:
    root=Path(name);dest=root/H.name;dest.mkdir();prior=root/'world-chat-delay-candidate-048';prior.mkdir()
    shutil.copyfile(H.parent/'world-chat-delay-candidate-048/harness.py',prior/'harness.py')
    for part in ['candidate','baseline']:shutil.copytree(H/part,dest/part)
    for script in ['capture.py','cases.py','test_evidence.py','install_exact.py','test_installer.py']:shutil.copyfile(H/script,dest/script)
    for args in [['capture.py','baseline'],['capture.py','candidate'],['test_evidence.py'],['test_installer.py']]:
        result=subprocess.run([sys.executable,'-B',*args],cwd=dest,env={**os.environ,'KIRA_TEST_ROOT':str(checkout),'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True,timeout=20)
        if result.returncode:raise RuntimeError(str(args)+' failed: '+result.stdout+result.stderr)
        results.append({'command':args,'result':json.loads(result.stdout)})
print(json.dumps({'status':'PUBLIC_CALLBACK_PLANNER_AND_RECOVERY_CLOSURE_PASS','results':results,'owner_original_recheck':False,'models_workers_ui_network':0}))
