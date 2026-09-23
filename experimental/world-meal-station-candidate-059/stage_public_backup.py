"""Stage additive058/059 public recovery and evidence; no Git mutations or launch."""
from pathlib import Path
import ast,hashlib,importlib.util,json,re,subprocess,sys

H=Path(__file__).resolve().parent;W=H.parent;K=Path('@kira_root')
S=W/'world-meal-station-candidate-059';A=W/'world-crew-dining-assessment-058'
O=Path('@user_home/.codex/world059-public028-stage002')
BASE='9f2663a13ee553db27acc5cf4791e495c0ade351';CLONE=W/'kiraworld-shared-recall-publication-001/repo'
P='experimental/world-meal-station-candidate-059/';Q='experimental/world-crew-dining-assessment-058/'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
load=lambda p:json.loads(p.read_bytes())
dump=lambda value:(json.dumps(value,indent=2)+'\n').encode()
def scrub(text):
 for path,label in ((W.parent,'@workspace'),(K,'@kira_root'),(Path.home(),'@user_home')):
  for old in (str(path).replace('\\','\\\\\\\\'),str(path).replace('\\','\\\\'),str(path),path.as_posix()):text=text.replace(old,label)
 return text
def put(rel,raw):
 p=O/rel;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(raw)
def git_read(path):return subprocess.run(['git','show',BASE+':'+path],cwd=CLONE,check=True,capture_output=True).stdout
def main():
 assert not O.exists()
 records=[]
 def capture(source,rel,exact=False,transform=None):
  raw=source.read_bytes();public=raw if exact else scrub(raw.decode('utf-8')).encode()
  description='exact' if public==raw else 'identity paths redacted; original digest retained'
  if transform:public=transform(public);description+='; portable test import/output handling only, writes report to stdout'
  put(rel,public);records.append({'path':rel,'original_sha256':sha(raw),'public_sha256':sha(public),'transformation':description})
 assert sha((A/'DELIVERY.json').read_bytes())=='0742c7522db456e38aee92ff8bc13071b22c975c2022043d2daf260800564d8c'
 for row in load(A/'DELIVERY.json')['files']:
  raw=(A/row['path']).read_bytes();assert sha(raw)==row['sha256'] and len(raw)==row['bytes']
  capture(A/row['path'],Q+row['path'])
 capture(A/'DELIVERY.json',Q+'DELIVERY.json')
 assert sha((S/'DELIVERY.json').read_bytes())=='a0a03777caa3c8424e81416686101cdc0131d2728b9483695a275dda441aae82'
 def portable_geometry(raw):
  lines=raw.decode().splitlines(keepends=True)
  selected=[i for i,line in enumerate(lines) if line.startswith("const out=process.argv[4]||'TEST-RESULT.json';")]
  assert len(selected)==1;lines[selected[0]]='console.log(JSON.stringify(result));\n';return ''.join(lines).encode()
 for rel,row in load(S/'FROZEN-MANIFEST.json')['files'].items():
  raw=(S/rel).read_bytes();assert sha(raw)==row['sha256'] and len(raw)==row['bytes']
  capture(S/rel,P+rel,transform=portable_geometry if rel=='test_meal_station.mjs' else None)
 for rel in ('FROZEN-MANIFEST.json','DELIVERY.json'):capture(S/rel,P+rel)
 def portable_checker(raw):
  old=b"AUDIT=W/'world-installed-observation-export-057-independent-review-001/check_package.py'"
  assert raw.count(old)==1;raw=raw.replace(old,b"AUDIT=H/'dependencies/check_package.py'")
  old=b" with (H/'ACTUAL-DELTA-RESULT.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\\n')\n print(json.dumps({k:result[k] for k in ('status','candidate_glb_sha256','added_mesh_nodes','overall_scene_bounds_unchanged')}))"
  assert raw.count(old)==1;return raw.replace(old,b" print(json.dumps(result,indent=2))")
 for rel,row in load(S/'ACTUAL-FROZEN-MANIFEST.json')['files'].items():
  raw=(S/rel).read_bytes();assert sha(raw)==row['sha256'] and len(raw)==row['bytes']
  capture(S/rel,P+rel,exact=rel.startswith('actual-001/package/'),transform=portable_checker if rel=='check_actual_delta.py' else None)
 for rel in ('ACTUAL-FROZEN-MANIFEST.json','ACTUAL-DELIVERY.json'):capture(S/rel,P+rel)
 prep=S/'native-review-preparation';prepared=load(prep/'PREPARED.json')
 for rel,row in prepared['files'].items():
  assert sha((prep/rel).read_bytes())==row['sha256'];capture(prep/rel,P+'native-review-preparation/'+rel)
 capture(prep/'PREPARED.json',P+'native-review-preparation/PREPARED.json')
 for name in ('WORLD059-ROOT-SOURCE-REVIEW.json','WORLD059-ACTUAL-ROOT-REVIEW.json'):
  capture(W/'sep23-continuation'/name,P+'root-review/'+name)
 helper=W/'world-installed-observation-export-057-independent-review-001/check_package.py'
 assert sha(helper.read_bytes())=='4f39cfdc434a608ce2333c17a959676e2cbe03043bb60f1320e32eae34220fb9'
 assert git_read('experimental/world-installed-observation-export-057/independent-review-001/check_package.py')==helper.read_bytes()
 capture(helper,P+'dependencies/check_package.py',exact=True)
 rows=[];source=load(S/'SOURCE-PINS.json');candidate=load(S/'CANDIDATE-CLOSURE.json');plan=load(S/'INSTALL-PLAN.json')
 assert len(source)==len(candidate)==42 and all(sha(Path(path).read_bytes())==value for path,value in plan['protected_inputs'].items())
 changed={row['relative_path'] for row in plan['files']};assert len(changed)==6
 for rel,row in source.items():
  prior=git_read(rel);assert sha(prior)==row['sha256'] and sha((K/rel).read_bytes())==row['sha256']
  proposed=(S/'candidate'/rel).read_bytes();public=(O/P/'candidate'/rel).read_bytes()
  assert sha(proposed)==candidate[rel]['sha256'] and public==proposed,'Executable source must remain exact: '+rel
  rows.append({'source_relative_path':rel,'installed056_repository_path':rel,'installed056_commit':BASE,'installed056_sha256':row['sha256'],
   'candidate_repository_path':P+'candidate/'+rel,'candidate_sha256':sha(public),'bytes':len(public),'changed':rel in changed})
 dependencies=[]
 dep_paths={row['path']:row for row in load(S/'DEPENDENCIES.json')['files']}
 for path,row in dep_paths.items():
  local=Path(path);raw=local.read_bytes();assert sha(raw)==row['sha256']
  if local.is_relative_to(A):repo=Q+local.relative_to(A).as_posix();public=(O/repo).read_bytes();commit=None
  elif local.is_relative_to(K/'tools'):repo=local.relative_to(K).as_posix();public=git_read(repo);commit=BASE
  else:repo='experimental/'+local.relative_to(W).as_posix();public=git_read(repo);commit=BASE
  assert public==raw or public==scrub(raw.decode()).encode()
  dependencies.append({'repository_path':repo,'commit':commit,'public_sha256':sha(public),'original_local_sha256':sha(raw)})
 prior=[]
 for name in ('scene.glb','scene.json','manifest.json','ROUNDTRIP.json','README.txt'):
  repo='experimental/world-installed-observation-export-057/actual-001/package/'+name;raw=git_read(repo)
  assert raw==(W/'world-installed-observation-export-057/actual-001/package'/name).read_bytes()
  prior.append({'repository_path':repo,'commit':BASE,'sha256':sha(raw),'bytes':len(raw)})
 for rel,row in load(S/'ACTUAL-DEPENDENCIES.json')['files_relative_to_work'].items():
  local=W/rel;assert sha(local.read_bytes())==row['sha256']
  repo='experimental/'+rel
  if rel.startswith('world-installed-observation-export-057-independent-review-001/'):
   repo='experimental/world-installed-observation-export-057/independent-review-001/check_package.py'
  public=git_read(repo);assert public==local.read_bytes() or public==scrub(local.read_bytes().decode()).encode()
  dependencies.append({'repository_path':repo,'commit':BASE,'public_sha256':sha(public),'original_local_sha256':row['sha256']})
 put(P+'RECOVERY-MAP.json',dump({'status':'COMPLETE42_SOURCE_CANDIDATE_CLOSURE_NO_PROMOTION','installed_release':'056','candidate_release':'059',
  'source_files':rows,'external_references':dependencies,'comparison_package':prior,
  'private_source_dependencies':'Original saved geometry, research, raw brief and immutable local bindings are excluded; operational preview/export reruns need those owner-local inputs.',
  'portable_tests':'Four synthetic geometry fixtures and actual GLB package checker use only backed-up files plus Node/Python. Native external runtime binaries/fonts are pinned but not bundled.'}))
 checkpoint=W/'sep23-continuation/history/20260923T165822778841Z/RECEIPT.json';cp=load(checkpoint);copies=[]
 for i,row in enumerate(cp['files'],1):
  raw=Path(row['path']).read_bytes();before=Path(row['backup']).read_bytes()
  assert sha(raw)==row['sha256'] and len(raw)==row['bytes'] and sha(before)==row['before_sha256']
  copies.append({'ordinal':i,'document':Path(row['path']).name,'current_sha256':sha(raw),'bytes':len(raw),
   'historical_before_sha256':sha(before),'historical_snapshot_is_current':False})
 excerpt_source=Path(cp['files'][0]['path']).read_text(encoding='utf-8')
 start=excerpt_source.index('### Latest continuation checkpoint038');end=excerpt_source.index('<!-- current-continuation:end -->',start)
 excerpt=excerpt_source[start:end].strip()+'\n'
 put(P+'checkpoint038/CURRENT-EXCERPT.md',scrub(excerpt).encode())
 put(P+'checkpoint038/SNAPSHOT-RECEIPT.json',dump({'status':'TEN_DOCUMENTS_VERIFIED_AS_OF_CHECKPOINT038','at_utc':cp['at_utc'],
  'source_receipt_sha256':sha(checkpoint.read_bytes()),'documents':copies,'excerpt_utf8_lf_sha256':sha(excerpt.encode()),'source_body_sha256':cp['body_sha256'],
  'scope':'Technical current excerpt only. No full prior private messages or raw active Studio012 run/admission/grant files. Historical beforeimages are not the checkpoint current files.'}))
 capture(Path(__file__),P+'stage_public_backup.py')
 put(P+'PUBLIC-BACKUP.md',('''# Experimental crew meal station059

This additive backup preserves assessment058, the original six-file059 proposal and complete42-file candidate source, unchanged preimages, synthetic fixtures, CPU checks, the actual1.43MB authored GLB/package, independent structural comparison and root source/export reviews. It does not replace installed056 or any earlier preview/package/history. All executable candidate source bytes are exact;42 baseline hashes were checked against public commit9f2663a13ee553db27acc5cf4791e495c0ade351 and the installed source.

The static meal station adds20 meshes, a semantic assembly and a conservative collider. Existing geometry/materials/textures/rooms/door hierarchy/navigation remain exact after accounting for generated export-ID shifts. There is no sitting interaction, food simulation, comfort certification, finished realism or game/VR runtime. Actual export/import passed; visual inspection and installation remain pending. The prepared native review command was not launched and must wait for root-verified Studio012 closure and a coordinated free model lane.

From this directory run the portable, source-independent checks:

    node test_meal_station.mjs
    python -B dependencies/check_package.py --package actual-001/package
    python -B check_actual_delta.py

The delta checker uses the prior057 package already committed in the sibling experimental directory. Its public copy relocates one helper import. Both public geometry/delta tests write reports to stdout instead of overwriting frozen evidence; original and public hashes are retained in SOURCE-PROVENANCE.json. These are CPU geometric/transport checks, not new renderer or native-user-interface checks. The inherited admission/source checks require owner-local inputs and cannot be replayed as standalone public demos.

Raw saved layout/brief/research, runtime_context, runtimeData, active Studio012 run state/grants, personal context, fonts and native binaries are excluded. The derived fictional GLB and portable package remain byte-exact and contain only minimal setting IDs/digests. Identity paths in local scripts/receipts are redacted; original hashes and dependency maps preserve recovery history. Original69-file and additive21-file delivery inventories remain distinct; each was verified before staging. Checkpoint038 is an as-of technical excerpt with hashes for all ten handoff/status documents; full historical documents stay private.
''').encode())
 put(P+'SOURCE-PROVENANCE.json',dump(records))
 # Exercise portable geometry and actual-package checks without private source/model/UI.
 result=subprocess.run(['C:/Program Files/nodejs/node.exe',str(O/P/'test_meal_station.mjs')],capture_output=True,text=True,timeout=30)
 assert result.returncode==0,result.stdout+result.stderr
 put(P+'PUBLIC-GEOMETRY-CHECK.json',dump(json.loads(result.stdout)))
 spec=importlib.util.spec_from_file_location('public059_delta',O/P/'check_actual_delta.py');checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
 checker.OLD=W/'world-installed-observation-export-057/actual-001/package'
 import contextlib,io
 output=io.StringIO()
 with contextlib.redirect_stdout(output):checker.main()
 put(P+'PUBLIC-PACKAGE-CHECK.json',dump(json.loads(output.getvalue())))
 prompt=load(K/'Data/world_research_jobs/world_research_c391ffbffc7352612392/job.json')['brief']['prompt'].encode();files=[]
 for path in sorted(O.rglob('*')):
  if not path.is_file():continue
  rel=path.relative_to(O).as_posix();raw=path.read_bytes()
  assert 'runtime_context/' not in rel and 'runtimeData/' not in rel and prompt not in raw and path.suffix!='.pyc',rel
  assert not re.search(rb'C:[/\\]+Users[/\\]+robmc',raw,re.I),rel
  assert not re.search(rb'(?:gh[pousr]_[A-Za-z0-9]{24,}|github_pat_[A-Za-z0-9_]{30,}|sk-proj-[A-Za-z0-9_-]{20,})',raw),rel
  if path.suffix=='.py':ast.parse(raw.decode())
  if path.suffix=='.json':json.loads(raw)
  if path.suffix=='.jsonl':
   for line in raw.splitlines():json.loads(line)
  assert subprocess.run(['git','cat-file','-e',BASE+':'+rel],cwd=CLONE,capture_output=True).returncode!=0,'Nonadditive path: '+rel
  files.append({'path':rel,'file':str(path),'sha256':sha(raw),'bytes':len(raw),'before_sha256':None})
 manifest={'repository':'rmcmurrer81/KiraWorld','clone':str(CLONE),'base_commit':BASE,'receipt_prefix':'world-meal-028','reviewed':False,
  'allowed_prefixes':[P,Q],'message':'Back up experimental crew meal station, exact CPU export and checkpoint038','files':files}
 mp=W/'sep22-backups/world-meal-028.manifest.json'
 with mp.open('xb') as f:f.write(dump(manifest))
 result={'status':'PUBLIC028_STAGED_FOR_ROOT_REVIEW_NO_PUSH','manifest':str(mp),'manifest_sha256':sha(mp.read_bytes()),'base_commit':BASE,
  'files':len(files),'bytes':sum(r['bytes'] for r in files),'candidate_source_files':42,'candidate_changed_files':6,
  'original_frozen_files_verified':69,'actual_appendix_files_verified':21,'protected_originals_verified':116,
  'technical_checkpoint':'038','handoff_hashes_verified':10,'canonical_promotions':0,'git_mutations':0,
  'portable_four_fixture_geometry_check':'PASS','portable_actual_package_delta_check':'PASS','native_server_or_browser_started':False,
  'private_source_brief_or_geometry_bundled':False,'visual_or_owner_approval':False}
 with (H/'DELIVERY.json').open('xb') as f:f.write(dump(result))
 print(json.dumps(result))
if __name__=='__main__':main()
