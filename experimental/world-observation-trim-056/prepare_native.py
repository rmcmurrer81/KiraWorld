"""Add native-review/installer preparation without changing frozen056 sources."""
from pathlib import Path
import copy,difflib,hashlib,json,shutil
import verify
H=Path(__file__).resolve().parent;B=H.parent/'world-observation-exclusion-055'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,indent=2);f.write('\n')
def write(p,s):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8',newline='\n') as f:f.write(s)
verify.verify();plan=json.loads((B/'INSTALL-PLAN.json').read_bytes());diff=[]
for row in plan['files']:
 rel=row['relative_path'];pre=H/'canonical-preimages'/rel;pre.parent.mkdir(parents=True,exist_ok=True)
 assert sha(row['target'])==row['before_sha256'];shutil.copyfile(row['target'],pre)
 after=H/'candidate'/rel;row['preimage']=str(pre);row['after']={'path':str(after),'sha256':sha(after),'bytes':after.stat().st_size}
 diff.extend(difflib.unified_diff(pre.read_text(encoding='utf-8').splitlines(True),after.read_text(encoding='utf-8').splitlines(True),fromfile='installed051/'+rel,tofile='candidate056/'+rel))
save(H/'INSTALL-PLAN.json',plan);write(H/'SOURCE.diff',''.join(diff))
for name in ('SOURCE-PINS.json','ACTUAL-PRESENTATION.json'):shutil.copyfile(B/name,H/name)
installer=(B/'installation/install_exact.py').read_text(encoding='utf-8').replace('055','056').replace("workspace/'preimages'","workspace/'canonical-preimages'")
installer=installer.replace('5e6384c3d1bb3d617d1f10e4bb71359e7ee1e50021654bf8096850145dcf7f43',sha(H/'INSTALL-PLAN.json'))
needle='def selected_source_paths(manifest,root,job_id):'
insert='''def check_candidate_closure(workspace=H):
    closure=workspace/'CANDIDATE-CLOSURE.json'
    assert sha(closure)=='7bd507bcf8fb7647a66ce7e8ae8e122ee4c0296aacddd4867a09691e7ae106b3','Unexpected source closure'
    rows=json.loads(closure.read_bytes());assert len(rows)==22
    for rel,row in rows.items():
        p=workspace/'candidate'/rel
        assert p.resolve().is_relative_to((workspace/'candidate').resolve())
        assert sha(p)==row['sha256'] and p.stat().st_size==row['bytes'],'Candidate closure changed'
    assets=workspace/'candidate/tools/world_builder_engine/layout_package_assets'
    pins=json.loads((assets/'PRODUCER-PINS.json').read_bytes())
    for rel,row in pins['files'].items():
        p=assets/rel;assert sha(p)==row['sha256'] and p.stat().st_size==row['bytes'],'Producer source changed'
    return len(rows)

'''
assert installer.count(needle)==1;installer=installer.replace(needle,insert+needle)
installer=installer.replace("plan=json.loads((H/'INSTALL-PLAN.json').read_bytes());check_other_sources(plan)","plan=json.loads((H/'INSTALL-PLAN.json').read_bytes());check_candidate_closure();check_other_sources(plan)")
write(H/'installation/install_exact.py',installer)
server=(B/'installation/serve_review.py').read_text(encoding='utf-8').replace('055','056')
server=server.replace('guard.check_other_sources(plan);guard.validate(plan,guard.K,guard.H)','guard.check_candidate_closure();guard.check_other_sources(plan);guard.validate(plan,guard.K,guard.H)')
write(H/'installation/serve_review.py',server)
tests=(B/'installation/test_installer.py').read_text(encoding='utf-8').replace('055','056').replace("self.work/'preimages'","self.work/'canonical-preimages'")
insert_tests=''' def test_foreign_sibling_temporary_is_preserved(self):
  sibling=Path(self.rows[0]['target']).parent/'.codex056-foreign-owner.tmp';sibling.write_text('foreign pending bytes')
  api.apply(self.plan,self.root,self.work);api.rollback(self.plan,self.root,self.work)
  self.assertEqual(sibling.read_text(),'foreign pending bytes');self.assert_before()
 def test_full_candidate_closure_rejects_unrelated_source_tamper(self):
  import shutil
  shutil.copytree(api.H/'candidate',self.work/'candidate',dirs_exist_ok=True)
  shutil.copyfile(api.H/'CANDIDATE-CLOSURE.json',self.work/'CANDIDATE-CLOSURE.json')
  self.assertEqual(api.check_candidate_closure(self.work),22)
  path=self.work/'candidate/tools/world_builder_engine/layout_package_assets/source/scene_metadata.mjs'
  path.write_text(path.read_text()+'\\n// injected unrelated change')
  with self.assertRaises(AssertionError):api.check_candidate_closure(self.work)
'''
anchor="if __name__=='__main__':";assert tests.count(anchor)==1;tests=tests.replace(anchor,insert_tests+anchor)
write(H/'installation/test_installer.py',tests)
prepare=(B/'prepare_review.py').read_text(encoding='utf-8').replace('055','056')
prepare=prepare.replace("prior=json.loads((H.parent/'world-observation-setting-054/actual-001/PREVIEW-RESULT.json').read_bytes())","prior=json.loads((H.parent/'world-observation-exclusion-055/PREVIEW-PREPARATION.json').read_bytes())")
prepare=prepare.replace("assert all(manifest['source_pins'][name]['sha256']==row['sha256'] for name,row in prior_manifest['source_pins'].items())","assert [name for name,row in prior_manifest['source_pins'].items() if manifest['source_pins'][name]['sha256']!=row['sha256']]==['viewer.mjs']")
prepare=prepare.replace("'actual_original_brief_and_presentation_identical_to054':True,'all_renderer_source_pins_identical_to054':True", "'actual_original_brief_and_presentation_identical_to055':True,'only_viewer_pin_changed_from055':True")
prepare=prepare.replace("'scope':'Only backend scenery-negative grammar changed. Actual bound Mars setting and all rendering/export sources are exact054; its transport evidence is retained, not relabeled as a new export.'", "'scope':'Only reveal mesh dimensions and matching source pin change from055. Actual brief/setting and geometry remain exact055. No GLB export or native visual test is claimed.'")
write(H/'prepare_review.py',prepare)
verify.verify();print(json.dumps({'status':'056_NATIVE_TOOLS_PREPARED_NOT_RUN','targets':len(plan['files']),'plan_sha256':sha(H/'INSTALL-PLAN.json'),'installer_sha256':sha(H/'installation/install_exact.py')}))
