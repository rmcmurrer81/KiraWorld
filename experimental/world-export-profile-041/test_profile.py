import os
from pathlib import Path
import copy,hashlib,importlib.util,json,sys,unittest
H=Path(__file__).resolve().parent;K=Path(os.environ.get('KIRA_TEST_ROOT',str(H.parents[1])));sys.dont_write_bytecode=True;sys.path.insert(0,str(K/'tools'))
from fixture_builder import build_fixture
from world_builder_engine.world_blueprint import compile_blueprint
spec=importlib.util.spec_from_file_location('world_builder_engine.layout_recipe_profile041',H/'candidate/tools/world_builder_engine/layout_recipe_profile.py');profile=importlib.util.module_from_spec(spec);spec.loader.exec_module(profile)
def rebuilt(b,program):
 g=compile_blueprint(b,b['research_packet_sha256'],'analog_to_original');g.update(functional_program=program,layout_template='single_level_entry_chain_and_corridor_branches_v2');return g
class ProfileTests(unittest.TestCase):
 def setUp(self):self.b,self.g=build_fixture()
 def check(self,b=None,g=None):return profile.validate_recipe_profile(g or self.g,b or self.b,(b or self.b)['research_packet_sha256'])
 def reject(self):
  with self.assertRaises(profile.RecipeUnsupported):self.check()
 def test_three_new_source_hashes_have_recompiled_roles_and_bounded_ownership(self):
  hashes=set()
  for variant in ('renamed','wider','translated'):
   b,g=build_fixture(variant=variant);before=json.dumps((b,g),sort_keys=True);result=self.check(b,g)
   self.assertTrue(result['eligibility_only']);self.assertTrue(result['source_structure_recompiled']);self.assertEqual(json.dumps((b,g),sort_keys=True),before)
   hashes.add(hashlib.sha256(json.dumps(g,sort_keys=True).encode()).hexdigest())
  self.assertEqual(len(hashes),3)
 def test_unknown_template_held(self):self.g['layout_template']='other';self.reject()
 def test_unknown_role_held(self):self.g['functional_program']['operations']='shopping_mall';self.reject()
 def test_missing_role_held(self):self.g['functional_program'].pop('operations');self.reject()
 def test_unknown_role_room_held(self):self.g['functional_program']['missing']='laboratory';self.reject()
 def test_transformed_structural_primitive_without_blueprint_change_held(self):self.g['primitives'][1]['position'][0]+=.2;self.reject()
 def test_changed_route_held_even_if_blueprint_digest_was_preserved(self):self.g['routes'][0]['points'][0][0]+=.1;self.reject()
 def test_claimed_visual_approval_held(self):self.g['photorealism_verified']=True;self.reject()
 def test_vertical_layout_held(self):
  for r in self.b['rooms']:r['floor_y']=2
  self.g=rebuilt(self.b,self.g['functional_program']);self.reject()
 def test_large_room_held(self):
  r=next(r for r in self.b['rooms'] if r['id']=='operations');r['x']-=8;r['width']+=8
  self.g=rebuilt(self.b,self.g['functional_program']);self.reject()
 def test_ambiguous_room_prefix_held(self):self.b,self.g=build_fixture(variant='ambiguous');self.reject()
 def test_two_portals_on_same_branch_held(self):
  p=copy.deepcopy(next(p for p in self.b['openings'] if p['room_a']=='operations'));p.update(id='extra_door',center=4.9,width=.9)
  self.b['openings'].append(p);self.g=rebuilt(self.b,self.g['functional_program']);self.reject()
 def test_two_circulation_roles_held(self):self.g['functional_program']['operations']='circulation';self.reject()
 def test_airlock_with_one_attached_door_held(self):self.g['functional_program']['equipment_vestibule']='airlock';self.reject()
 def test_too_many_rooms_held(self):
  self.g['rooms']+=copy.deepcopy(self.g['rooms'][:3]);self.reject()
if __name__=='__main__':
 import io
 stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ProfileTests))
 report={'status':'PROFILE_PURE_TESTS_PASS' if result.wasSuccessful() else 'FAIL','tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'output':stream.getvalue(),'models_exports_ui':0,'original_data_writes':0}
 p=H/('PROFILE-TEST-RESULT-'+str(len(list(H.glob('PROFILE-TEST-RESULT*.json')))+1)+'.json');assert not p.exists();p.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 if result.wasSuccessful():
  for variant in ('base','renamed','wider','translated'):
   b,g=build_fixture(variant=variant);p=H/'fixtures'/('profile_'+variant+'.json')
   if p.exists():assert json.loads(p.read_bytes())==g
   else:p.write_text(json.dumps(g,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:v for k,v in report.items() if k!='output'}));print('' if result.wasSuccessful() else stream.getvalue());raise SystemExit(not result.wasSuccessful())
