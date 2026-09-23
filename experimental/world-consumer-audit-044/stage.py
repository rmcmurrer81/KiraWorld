from pathlib import Path
import hashlib,json,shutil
H=Path(__file__).resolve().parent;S=H.parent/'world-package-consumer-043'
review=json.loads((S/'REVIEW-PLAN.json').read_bytes())
def pin(p):
 b=p.read_bytes();return {'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
files=list(review['runtime_files'])+['test_admission.mjs','test_runtime.mjs','test_import.mjs']
files += [p.relative_to(S).as_posix() for p in (S/'sample-package').iterdir()]
for rel in files:
 p=H/'candidate'/rel;p.parent.mkdir(parents=True,exist_ok=True);assert not p.exists();shutil.copy2(S/rel,p)
for rel in ['app.mjs','package_loader.mjs']:
 p=H/'baseline'/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(S/rel,p)
(H/'SOURCE-PINS.json').write_text(json.dumps({'base_public_commit':'2ad6feef562ae87c443499415520ba5c97684c67','baseline043_review_plan_sha256':pin(S/'REVIEW-PLAN.json')['sha256'],
 'files':{rel:pin(S/rel) for rel in files},'canonical_writes':False},indent=2)+'\n',encoding='utf-8')
