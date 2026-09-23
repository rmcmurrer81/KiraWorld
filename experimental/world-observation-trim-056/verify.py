"""Read-only exact source/protection verification; no UI, process or model launch."""
from pathlib import Path
import hashlib,json
H=Path(__file__).resolve().parent
B=H.parent/'world-observation-exclusion-055'
K=Path('@kira_root')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p): return json.loads(Path(p).read_bytes())
def check(p,row):
    assert sha(p)==row['sha256'],str(p)
    assert Path(p).stat().st_size==row['bytes'],str(p)
def verify():
    overlay=load(H/'OVERLAY.json');closure=load(H/'CANDIDATE-CLOSURE.json')
    base=load(B/'CANDIDATE-CLOSURE.json');changed={r['path'] for r in overlay['files']}
    assert len(changed)==3 and len(closure)==len(base)==22
    assert set(closure)==set(base)
    assert {r for r in closure if closure[r]!=base[r]}==changed
    for r,row in closure.items():check(H/'candidate'/r,row)
    for r,row in base.items():check(B/'candidate'/r,row)
    for row in overlay['files']:
        r=row['path'];assert sha(H/'preimages'/r)==row['before_sha256']==base[r]['sha256']
        assert row['sha256']==closure[r]['sha256'] and row['bytes']==closure[r]['bytes']
    protected=load(B/'INSTALL-PLAN.json')['protected_inputs']
    assert len(protected)==116 and protected==overlay['protected_inputs']
    for p,s in protected.items():assert sha(p)==s,p
    originals=load(B/'SOURCE-PINS.json')
    for r,s in originals.items():assert sha(K/'tools/world_builder_engine'/r)==s,r
    frozen=load(B/'FROZEN-MANIFEST.json')['files']
    for r,row in frozen.items():check(B/r,row)
    assets=H/'candidate/tools/world_builder_engine/layout_package_assets'
    pins=load(assets/'PRODUCER-PINS.json');old=load(B/'candidate/tools/world_builder_engine/layout_package_assets/PRODUCER-PINS.json')
    assert pins['external']==old['external'] and pins['contract']==old['contract']
    assert set(pins['files'])==set(old['files'])
    assert [r for r in pins['files'] if pins['files'][r]!=old['files'][r]]==['source/room_dressing_render.mjs']
    for r,row in pins['files'].items():check(assets/r,row)
    check(overlay['node'],pins['external']['node'])
    test=load(H/'GEOMETRY-TESTS.json')
    assert test['status']=='PASS' and test['cases']==14 and test['rays']==630
    assert test['visual_flicker_resolution_claim'] is False
    delivery=H/'FROZEN-MANIFEST.json'
    if delivery.exists():
        for r,row in load(delivery)['files'].items():check(H/r,row)
    return {'status':'PASS','candidate_files':len(closure),'changed_files':3,
        'frozen055_files_unchanged':len(frozen),'protected_originals_unchanged':len(protected),
        'canonical_source_pins_unchanged':len(originals),'producer_file_pins_verified':len(pins['files']),
        'producer_external_pins_unchanged':True,'selected_job_and_source_files_unchanged':True,
        'no_install_or_native_visual_claim':True}
if __name__=='__main__':print(json.dumps(verify()))
