"""A hash-valid source must still pass semantic ownership before output exists."""
from pathlib import Path
import copy,json
import test_package
import package_writer as writer
H=Path(__file__).resolve().parent
fixture=test_package.PackageTests(methodName='runTest');fixture.setUp();checks=[]
try:
 raw=fixture.geometry.read_bytes();original=json.loads(raw)
 cases=[]
 missing=copy.deepcopy(original);missing['colliders'][0]['id']='missing_owner';cases.append(('missing owner',missing))
 mismatch=copy.deepcopy(original);mismatch['colliders'][0]['max'][0]+=.02;cases.append(('different bounds',mismatch))
 ambiguous=copy.deepcopy(original);floor=next(p for p in ambiguous['primitives'] if p['role']=='floor');identifier=floor['id'][:-5]
 ambiguous['colliders'].append({'id':identifier,'min':[n-floor['size'][i]/2 for i,n in enumerate(floor['position'])], 'max':[n+floor['size'][i]/2 for i,n in enumerate(floor['position'])]})
 other=copy.deepcopy(floor);other['id']=identifier;ambiguous['primitives'].append(other);cases.append(('ambiguous names',ambiguous))
 for name,geometry in cases:
  fixture.geometry.write_bytes(writer.canonical(geometry));fixture.save_bindings()
  try:fixture.build()
  except writer.PackageError as error:assert 'Metadata projection rejected' in str(error)
  else:raise AssertionError('Semantic rejection expected: '+name)
  assert not (fixture.root/'package').exists();checks.append(name+' held before output')
 fixture.geometry.write_bytes(raw);fixture.save_bindings();result=fixture.build('valid');fixture.assert_unchanged()
 scene=json.loads((fixture.root/'valid/scene.json').read_bytes())
 for collider in scene['colliders']:assert collider['owner_node_id']
 checks.append('restored source exports all134 owned colliders with no source changes')
 receipt={'status':'PASS_PACKAGE_STRUCTURAL_OWNERSHIP_GATES','checks':checks,'hash_valid_invalid_geometry_cases':3,'metadata_only':True,'installed':False,'owner_data_used_or_changed':False,'gpu_models':0}
 with (H/'OWNER-PACKAGE-RESULT.json').open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2);f.write('\n')
 print(json.dumps(receipt))
finally:fixture.tearDown()
