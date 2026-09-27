"""Public source-only backup of reviewed combined habitat; no owner layout data."""
from pathlib import Path
import hashlib,json,re
H=Path(__file__).resolve().parent;W=H.parent;C=W/'world-combined-hatch-mars-069'
PREFIX='experiments/world-builder/combined-hatch-mars-069/'
def sha(b):return hashlib.sha256(b).hexdigest()
assert not (H/'manifest.json').exists()
(H/'blobs').mkdir(exist_ok=False);rows=[]
def add(p,rel):
 b=p.read_bytes();assert not p.is_symlink() and not getattr(p.lstat(),'st_file_attributes',0)&0x400
 assert not re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}',b)
 d=sha(b);target=H/'blobs'/d
 if not target.exists():target.write_bytes(b)
 rows.append({'path':PREFIX+rel,'file':str(target),'bytes':len(b),'sha256':d,'before_sha256':None})
manifest=json.loads((C/'FROZEN-MANIFEST.json').read_bytes());bindings={r['path']:r for r in manifest['files']}
for p in sorted((C/'candidate').rglob('*')):
 if not p.is_file():continue
 rel=p.relative_to(C).as_posix();r=bindings[rel]
 assert sha(p.read_bytes())==r['sha256'] and p.stat().st_size==r['bytes']
 add(p,rel)
add(H/'README.md','README.md');add(H/'prepare.py','prepare.py')
m={'repository':'rmcmurrer81/KiraWorld','clone':str(W/'kiraworld-shared-recall-publication-001/repo'),
 'base_commit':'d2bee15440c2d5182f8894c6a82fb727624f3593','receipt_prefix':'world-combined-source-036','reviewed':False,
 'allowed_prefixes':[PREFIX],'message':'Back up reviewed combined Mars habitat source and disclose export memory hold','files':rows}
(H/'manifest.json').write_text(json.dumps(m,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'files':len(rows),'bytes':sum(r['bytes'] for r in rows),'sha256':sha((H/'manifest.json').read_bytes())}))
