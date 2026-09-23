"""Finalize only after explicit root-provided056 install and native review receipts."""
from pathlib import Path
import argparse,ast,hashlib,json,re,subprocess
H=Path(__file__).resolve().parent;W=H.parent;K=Path('@kira_root')
O=Path('@user_home/.codex/world056-public026-stage')
S=W/'world-observation-trim-056/native-successor-001';CLONE=W/'kiraworld-shared-recall-publication-001/repo'
BASE='ece863af2352fb4a872a8297333a1636cc63e4b6';PREFIX='experimental/world-observation-trim-056/'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def dump(v):return (json.dumps(v,indent=2)+'\n').encode()
def put(rel,raw):
 p=O/rel;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(raw)
def scrub(text):
 for path,label in ((W.parent,'@workspace'),(K,'@kira_root'),(Path.home(),'@user_home')):
  for old in (str(path).replace('\\','\\\\\\\\'),str(path).replace('\\','\\\\'),str(path),path.as_posix()):text=text.replace(old,label)
 return text
def git_read(path):return subprocess.run(['git','show',BASE+':'+path],cwd=CLONE,capture_output=True,check=True).stdout
def capture(source,repo,records):
 raw=source.read_bytes();public=scrub(raw.decode()).encode();put(repo,public)
 records.append({'path':repo,'original_sha256':sha(raw),'public_sha256':sha(public),'transformation':'exact' if raw==public else 'local identity paths redacted'})
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--installed',required=True,type=Path);parser.add_argument('--review',required=True,type=Path);args=parser.parse_args()
 manifest_path=W/'sep22-backups/world-observation-026.manifest.json';assert not manifest_path.exists()
 assert args.installed.resolve()==(S/'INSTALLED.json').resolve()
 installed=json.loads(args.installed.read_bytes());review=json.loads(args.review.read_bytes());plan=json.loads((S/'INSTALL-PLAN.json').read_bytes())
 assert installed['status']=='056_EXACT_SEVEN_FILE_INSTALL_PASS' and installed['installed_files']==7
 assert installed['install_plan_sha256']==sha((S/'INSTALL-PLAN.json').read_bytes())
 assert review['status']=='ROOT_APPROVED_056_INSTALL' and review['native_preview_review_complete'] and review['source_review_complete']
 assert sha(args.review.read_bytes())==installed['root_review']['sha256']
 assert review['install_plan_sha256']==installed['install_plan_sha256']
 assert len(plan['protected_inputs'])==116 and all(sha(Path(p).read_bytes())==s for p,s in plan['protected_inputs'].items())
 # Reverify every frozen proposal, independently of older pre-install assertions.
 for folder in (W/'world-observation-exclusion-055',S.parent,S):
  frozen=json.loads((folder/'FROZEN-MANIFEST.json').read_bytes())
  for rel,row in frozen['files'].items():
   p=folder/rel;assert sha(p.read_bytes())==row['sha256'] and p.stat().st_size==row['bytes'],str(p)
 before={};records=json.loads((O/PREFIX/'SOURCE-PROVENANCE.staged.json').read_bytes())
 for row in plan['files']:
  rel=row['relative_path'];raw=Path(row['target']).read_bytes()
  assert sha(raw)==row['after']['sha256'] and sha(git_read(rel))==row['before_sha256']
  assert sha(Path(row['preimage']).read_bytes())==row['before_sha256'];before[rel]=row['before_sha256'];put(rel,raw)
 capture(args.installed,PREFIX+'native-successor-001/INSTALLED.json',records)
 capture(args.review,PREFIX+'native-successor-001/ROOT-NATIVE-INSTALL-REVIEW.json',records)
 refresh=S/'installed-preview-001/REFRESH-RESULT.json';rv=json.loads(refresh.read_bytes())
 assert rv['status']=='INSTALLED056_CANONICAL_IMMUTABLE_PREVIEW_REFRESH_PASS' and rv['selected_job_pointer_unchanged'] and rv['reused_on_second_call']
 assert rv['protected_originals_unchanged']==116 and rv['browser_GPU_models_exports']==0
 capture(refresh,PREFIX+'native-successor-001/installed-preview-001/REFRESH-RESULT.json',records)
 capture(S/'refresh_installed_preview.py',PREFIX+'native-successor-001/refresh_installed_preview.py',records)
 closed=[]
 for parent,repo_prefix in ((W/'world-observation-exclusion-055','experimental/world-observation-exclusion-055/'),(S,PREFIX+'native-successor-001/')):
  for run in sorted((parent/'installation').glob('review-run-*')):
   receipt=run/'CLOSED.json';assert receipt.exists(),'Do not include an active native server'
   value=json.loads(receipt.read_bytes());assert value['status']=='CLOSED' and value['server_thread_closed'] is True
   for source in (run/'READY.json',receipt):capture(source,repo_prefix+source.relative_to(parent).as_posix(),records)
   closed.append({'path':repo_prefix+receipt.relative_to(parent).as_posix(),'local_sha256':sha(receipt.read_bytes())})
 assert any(r['path'].startswith(PREFIX) for r in closed)
 oldpins=json.loads((S/'SOURCE-PINS.json').read_bytes());oldrows=[];newrows={}
 for rel,digest in oldpins.items():
  target='tools/world_builder_engine/'+rel;assert sha(git_read(target))==digest
  oldrows.append({'source_path':target,'sha256':digest,'repository_path':PREFIX+'native-successor-001/canonical-preimages/'+target if target in before else target,'base_commit':None if target in before else BASE})
  raw=Path(K/target).read_bytes();assert sha(raw)==(next(x['after']['sha256'] for x in plan['files'] if x['relative_path']==target) if target in before else digest)
  newrows[target]={'repository_path':target,'sha256':sha(raw),'bytes':len(raw)}
 for rel,row in json.loads((S/'CANDIDATE-CLOSURE.json').read_bytes()).items():
  raw=(K/rel).read_bytes();assert sha(raw)==row['sha256'] and len(raw)==row['bytes']
  newrows[rel]={'repository_path':rel,**row}
 for rel,row in newrows.items():
  public=(O/rel).read_bytes() if (O/rel).exists() else git_read(rel)
  assert sha(public)==row['sha256'] and len(public)==row['bytes']
 put(PREFIX+'INSTALLED051-RECOVERY.json',dump({'status':'HISTORICAL051_EXACT_SOURCE_PATHS','files':oldrows}))
 put(PREFIX+'INSTALLED056-RECOVERY.json',dump({'status':'INSTALLED056_SOURCE_AND_PRODUCER_CLOSURE','files':newrows,'base_commit_for_unchanged_files':BASE}))
 # The earlier public map explicitly binds an immutable commit, so it survives root promotion without mutation.
 prior=json.loads(git_read('experimental/world-observation-setting-054/CANONICAL-BASE-MAP.json'))
 assert len(prior)==7
 for row in prior:
  raw=subprocess.run(['git','show',row['base_commit']+':'+row['repository_path']],cwd=CLONE,capture_output=True,check=True).stdout
  assert sha(raw)==row['sha256']
 put(PREFIX+'HISTORICAL-RECOVERY-CHECK.json',dump({'status':'PASS','prior_explicit_canonical_base_rows':7,'prior_map_unmodified':True,'historical051_rows_preserved':len(oldrows),'current056_source_rows':len(newrows),'held_proposals_remain_in_immutable_experimental_paths':True}))
 put(PREFIX+'SOURCE-PROVENANCE.json',dump(records));put(PREFIX+'finalize_public_backup.py',scrub(Path(__file__).read_text()).encode())
 put(PREFIX+'PUBLIC-BACKUP.md',('''# Observation window056 installed;055 and early056 held history

The seven canonical files are root-installed056.055 corrected explicit scenery exclusions, but native review found striped/flickering trim.056 shortens the metal reveal so it meets the ivory frame's back without coplanar front faces. The frame, glazing, wall bounds and full safety collision remain unchanged. The successor refreshes the export's exact viewer digest; its first preparation correctly held an outdated pin. Frozen proposals and that failure are retained as history, not alternative install recommendations.

The exact native result and limits are in native-successor-001/ROOT-NATIVE-INSTALL-REVIEW.json. Installation and root visual review do not imply Robert's realism approval. Appearance remains procedural. This increment does not claim a new GLB export, physics/pressure simulation, VR or engine-native controls.

test_public_closure.py replays30 synthetic setting checks,14 geometry cases/630 rays and14 installer fixtures in temporary folders. It reads no owner's world data and launches no server, UI, model or exporter. Candidate/source/preimages remain exact; local identity paths in operational receipts/helpers are redacted and paired original/public digests are recorded. Rebind local operational scripts before use; do not execute redacted install commands blindly.

Both immutable preview Data directories, raw brief, original geometry/research caches, screenshots, weights and native dependencies are excluded. No model media is required by this source backup. Three's source and license are included. Historical051 sources map to exact preimages or the immutable public base; installed056 source/producer closure is explicit. Earlier experimental snapshots and commit-bound recovery references remain unchanged.
''').encode())
 actual_prompt=json.loads((K/'Data/world_research_jobs/world_research_c391ffbffc7352612392/job.json').read_bytes())['brief']['prompt'].encode()
 files=[]
 for p in sorted(O.rglob('*')):
  if not p.is_file():continue
  rel=p.relative_to(O).as_posix();raw=p.read_bytes()
  assert 'runtime_context/' not in rel and actual_prompt not in raw
  assert not re.search(rb'C:[/\\]+Users[/\\]+robmc',raw,re.I),rel
  assert not re.search(rb'(?:gh[pousr]_[A-Za-z0-9]{24,}|github_pat_[A-Za-z0-9_]{30,}|sk-proj-[A-Za-z0-9_-]{20,})',raw),rel
  if p.suffix=='.py':ast.parse(raw.decode())
  if p.suffix=='.json':json.loads(raw)
  files.append({'path':rel,'file':str(p),'sha256':sha(raw),'bytes':len(raw),'before_sha256':before.get(rel)})
 manifest={'repository':'rmcmurrer81/KiraWorld','clone':str(CLONE),'base_commit':BASE,'receipt_prefix':'world-observation-026','reviewed':False,
  'allowed_prefixes':['experimental/world-observation-exclusion-055/',PREFIX,*before],
  'message':'Fix observation-window trim overlap and preserve exact source-bound scenery, native review and recovery','files':files}
 with manifest_path.open('xb') as f:f.write(dump(manifest))
 delivery={'status':'INSTALLED056_PUBLIC_BACKUP_READY_FOR_ROOT_REVIEW','manifest':str(manifest_path),'manifest_sha256':sha(manifest_path.read_bytes()),
  'files':len(files),'bytes':sum(r['bytes'] for r in files),'canonical_files':7,'source_closure_files':len(newrows),'protected_originals':116,
  'raw_owner_context_included':False,'git_mutations':0,'base_commit':BASE,'synthetic_closure':'PUBLIC056_SYNTHETIC_CLOSURE_PASS'}
 with (H/'DELIVERY.json').open('xb') as f:f.write(dump(delivery))
 print(json.dumps(delivery))
if __name__=='__main__':main()
