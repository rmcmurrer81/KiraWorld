"""Run the small contact suite and preserve a deterministic source-bound receipt."""
from pathlib import Path
import hashlib,json,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    node=shutil.which('node')
    if not node:raise SystemExit('Install Node.js and make node available on PATH.')
    test=ROOT/'Testing/test_bedding_frame_contacts.mjs'
    subprocess.run([node,'--max-old-space-size=384',str(test)],check=True,timeout=120)
    result=json.loads((test.parent/'CONTACT-UNIT-RESULT.json').read_text())
    if result['status']!='PASS' or len(result['checks'])!=13:raise RuntimeError('Contact smoke checks did not pass')
    base=ROOT/'tools/world_builder_components/bedding'
    evidence={'status':'PASS','scope':'contact_smoke_only',
        'source_pins':{k:sha(base/n) for k,n in {'base':'bedding_base.mjs','solver':'mattress_physics.mjs','contacts':'surface_contacts.mjs','frame_contacts':'frame_contacts.mjs'}.items()},
        'test_sha256':sha(test),'fixture_sha256':sha(test.parent/'fixtures/bed_contact_single.json'),'checks':result['checks'],
        'limits':['Thirteen finite contact unit checks, not full dynamics, no CCD/self collision or visual acceptance.',
                  'Dense release instability and below-mattress false upper contacts remain known unresolved issues.',
                  'No owner worlds or studies used.']}
    payload=(json.dumps(evidence,indent=2)+'\n').encode('utf-8');target=base/'CONTACT-TEST-RESULT.json'
    if target.exists():
        if json.loads(target.read_text(encoding='utf-8'))!=evidence:raise RuntimeError('Preserve the prior qualification; changed sources need a fresh reviewed package')
    else:
        with target.open('xb') as stream:stream.write(payload)
    print('Contact smoke qualification ready; this is not a full physics or visual pass.')
if __name__=='__main__':main()
