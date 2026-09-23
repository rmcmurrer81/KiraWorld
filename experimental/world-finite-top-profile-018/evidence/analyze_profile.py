from pathlib import Path
from collections import defaultdict
import json,hashlib,datetime
H=Path(__file__).resolve().parent
W=H.parent.parent
OLD=H.parent/'world-finite-top-domain-candidate-017'
def pin(p):
 b=p.read_bytes();return {'path':str(p.resolve()),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
profile=json.loads((H/'profile/world017.cpuprofile').read_text(encoding='utf-8'))
nodes={n['id']:n for n in profile['nodes']};parents={c:n['id'] for n in profile['nodes'] for c in n.get('children',[])}
self_us=defaultdict(float);inclusive_us=defaultdict(float);hits=defaultdict(int)
def label(n):
 c=nodes[n]['callFrame'];url=c['url'].replace('file:///'+W.as_posix()+'/', '')
 return (url,c['functionName'],c['lineNumber']+1)
for nid,dt in zip(profile['samples'],profile['timeDeltas']):
 self_us[label(nid)]+=dt;hits[label(nid)]+=1
 visited=set()
 while nid in nodes:
  k=label(nid)
  if k not in visited:inclusive_us[k]+=dt;visited.add(k)
  if nid not in parents:break
  nid=parents[nid]
sampled=sum(profile['timeDeltas'])
rows=[{'source':k[0],'function':k[1],'line':k[2],'self_ms':v/1000,'inclusive_ms':inclusive_us[k]/1000,'self_percent_of_all_samples':100*v/sampled,'samples':hits[k]} for k,v in self_us.items()]
rows.sort(key=lambda r:r['self_ms'],reverse=True)
old=json.loads((OLD/'FULL-PILOT-RESULT.json').read_text());new=json.loads((H/'FULL-PILOT-RESULT.json').read_text())
assert new['initial']==old['initial'] and new['rows']==old['rows']
assert new['status']=='PASS_12_FRAME_FULL_CLOTH_REGRESSION_ONLY'
pre=json.loads((H/'PRECONDITIONS.json').read_text())
unchanged=all(pin(Path(r['path']))['sha256']==r['sha256'] for r in [pre['predecessor_delivery'],pre['portable003_manifest']]+pre['source_files'])
assert unchanged
helper=[r for r in rows if r['source'].endswith('/candidate/finite_top_domain.mjs')]
out={'status':'SINGLE_PROFILE_COMPLETE_MEASURED_HELPER_HOTSPOTS_NO_OPTIMIZATION','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'profile':pin(H/'profile/world017.cpuprofile'),'supervisor':pin(H/'PROFILE-SUPERVISOR.json'),'physical_result':pin(H/'FULL-PILOT-RESULT.json'),'profile_samples':len(profile['samples']),'sampled_ms':sampled/1000,'profile_span_ms':(profile['endTime']-profile['startTime'])/1000,'all_per_frame_observations_exactly_match_prior_unprofiled_pilot':True,'p_prev_v_exact_between_candidate_and_baseline_every_frame':True,'prior017_and_portable003_unchanged':unchanged,'helper_exclusive_sample_ms':sum(r['self_ms'] for r in helper),'helper_exclusive_sample_percent':sum(r['self_percent_of_all_samples'] for r in helper),'helper_functions':helper,'top_functions':rows[:30],'profile_run_candidate_ms':new['candidate_ms'],'profile_run_baseline_ms':new['baseline_ms'],'limitations':['One short mixed candidate/baseline process; percentages use all sampled runtime including startup and both implementations.','CPU sampling assigns time approximately and may fold inlined work into caller frames; it is not a separate allocation profile.','No optimized code was implemented and no speedup is claimed.','The exact 12-frame observation match does not establish all longer trajectories under profiling.'],'next':'Consider one isolated019 helper-only change: allocation-free key creation for validated1/2/3-integer IDs with unchanged fallback, or explicit loops in observeVertex. Preserve all observation calls, finiteXYZ checks, EPS, holds and counters; evaluate independently before any installation.'}
(H/'PROFILE-ANALYSIS.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'analysis':pin(H/'PROFILE-ANALYSIS.json'),'helper_exclusive_sample_percent':out['helper_exclusive_sample_percent'],'helper_functions':helper,'physical_observations_exact':True}))
