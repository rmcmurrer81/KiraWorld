"""Run historical callback fixtures in disposable copies; no owner-file claims."""
from pathlib import Path
import json,os,shutil,subprocess,sys,tempfile
H=Path(__file__).resolve().parent
checkout=Path(os.environ.get('KIRA_TEST_ROOT',str(H.parents[1]))).resolve()
previous=H.parent/'world-chat-usability-audit-046/test_context.py'
results=[]
with tempfile.TemporaryDirectory(prefix='world048-public-') as name:
    root=Path(name)
    prior=root/'world-chat-usability-audit-046';prior.mkdir();shutil.copyfile(previous,prior/'test_context.py')
    for package in ['world-chat-dispatch-candidate-047','world-chat-delay-candidate-048']:
        source=H.parent/package;dest=root/package;dest.mkdir()
        for item in ['candidate','baseline','prior047']:
            if (source/item).exists():shutil.copytree(source/item,dest/item)
        scripts=['harness.py','test_dispatch.py','test_retained_context.py']
        if package.endswith('048'):scripts+=['install_exact.py','test_installer.py']
        for script in scripts:shutil.copyfile(source/script,dest/script)
        for script in ['test_dispatch.py','test_retained_context.py']+(['test_installer.py'] if package.endswith('048') else []):
            result=subprocess.run([sys.executable,'-B',script],cwd=dest,env={**os.environ,'KIRA_TEST_ROOT':str(checkout),'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True,timeout=20)
            if result.returncode:raise RuntimeError(package+' '+script+' failed: '+result.stdout+result.stderr)
            results.append({'package':package,'test':script,'result':json.loads(result.stdout)})
print(json.dumps({'status':'PUBLIC_DISPOSABLE_CALLBACK_AND_RECOVERY_TESTS_PASS','results':results,'owner_original_recheck':False,'models_gpu_native_ui':0}))
