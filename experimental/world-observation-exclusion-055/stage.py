from pathlib import Path
import hashlib,json,shutil,difflib
H=Path(__file__).resolve().parent;S=H.parent/'world-observation-setting-054';E=Path('@kira_root/tools/world_builder_engine');C=H/'candidate/tools/world_builder_engine'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert not C.exists();shutil.copytree(S/'candidate',H/'candidate',ignore=shutil.ignore_patterns('__pycache__'))
shutil.copytree(S/'preimages',H/'preimages');shutil.copytree(S/'baseline',H/'baseline');(H/'fixtures').mkdir();shutil.copyfile(S/'fixtures/synthetic-habitat.json',H/'fixtures/synthetic-habitat.json')
path=C/'world_layout_preview.py';old=path.read_text(encoding='utf-8')
needle='''    denied = re.search(r"\b(?:don't|do not|not|no|without)\b[^.!?]*\b(?:mars|ground|terrain|surface|exterior)\b",clean)'''
# Keep a negative attached to the object it governs, rather than letting
# "no weapons" negate a later positive landscape clause in the same sentence.
needle=needle.replace('\b','\\b') if '\x08' in needle else needle
assert old.count(needle)==1
replacement='''    exterior_object = r'(?:(?:a|an|any|the|realistic|procedural|new)\\s+){0,3}(?:(?:outdoor|outside|exterior)\\s+)?(?:landscapes?|scenery|terrain|ground|surface|exterior|view|mars(?:\\s+surface)?(?:\\s+(?:base|habitat))?)\\b'
    negative_action = r"\\b(?:don't|do not|never)\\s+(?:(?:ever|automatically)\\s+)?(?:show|create|add|generate|include|draw|render|put|make|build|use|place|want)\\s+"
    denied = (re.search(negative_action+exterior_object,clean) or
              re.search(r'\\b(?:no|without|not)\\s+'+exterior_object,clean) or
              re.search(r'\\bnot\\s+(?:on\\s+)?(?:the\\s+)?(?:ground|surface|mars)\\b',clean))'''
new=old.replace(needle,replacement,1);path.write_text(new,encoding='utf-8',newline='\n')
plan=json.loads((S/'INSTALL-PLAN.json').read_bytes())
for row in plan['files']:
 rel=row['relative_path'];p=H/'candidate'/rel;row['preimage']=str(H/'preimages'/rel);row['after']={'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size};assert sha(row['target'])==row['before_sha256']
assert all(sha(p)==v for p,v in plan['protected_inputs'].items())
(H/'INSTALL-PLAN.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
diff=[]
for row in plan['files']:
 rel=row['relative_path'];diff.extend(difflib.unified_diff(Path(row['target']).read_text(encoding='utf-8').splitlines(True),(H/'candidate'/rel).read_text(encoding='utf-8').splitlines(True),fromfile='installed051/'+rel,tofile='candidate055/'+rel))
(H/'SOURCE.diff').write_text(''.join(diff),encoding='utf-8',newline='\n')
(H/'FROM054.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='candidate054/world_layout_preview.py',tofile='candidate055/world_layout_preview.py')),encoding='utf-8',newline='\n')
shutil.copyfile(S/'SOURCE-PINS.json',H/'SOURCE-PINS.json')
(H/'CANDIDATE-CLOSURE.json').write_text(json.dumps({p.relative_to(H/'candidate').as_posix():{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(C.rglob('*')) if p.is_file() and '__pycache__' not in p.parts},indent=2)+'\n',encoding='utf-8')
test=(S/'test_setting.py').read_text(encoding='utf-8').replace('054','055')
anchor=" ('research request','Research an original Mars base.','unspecified'),"
assert test.count(anchor)==1
test=test.replace(anchor,anchor+'''
 ('landscape exclusion','Build an original Mars base. Do not show a landscape beyond the window.','unspecified'),
 ('outdoor scenery exclusion','Build an original Mars base. Do not create outdoor scenery.','unspecified'),
 ('scenery without','Build an original Mars base without outdoor scenery.','unspecified'),
 ('no landscape','Build an original Mars base. No landscape beyond the window.','unspecified'),
 ('positive landforms','Build an original Mars base with a landscape of cliffs, dunes and hills outside the window.','mars_surface'),
 ('unrelated negative then landscape','Build an original Mars base with no weapons, and add a landscape beyond the window.','mars_surface'),
 ('unrelated negative then scenery','Build an original Mars base. Do not add weapons, but create outdoor scenery.','mars_surface'),
 ('quoted exclusion is data','Build an original Mars base. The reference says "Do not create outdoor scenery."','mars_surface'),
 ('use excluded','Build an original Mars base. Do not use exterior terrain.','unspecified'),
 ('want excluded','Build an original Mars base. I do not want a landscape outside.','unspecified'),
 ('not terrain','Build an original Mars base, not any exterior terrain.','unspecified'),
 ('negative view','Build an original Mars base. Do not show any view outside.','unspecified'),''',1)
(H/'test_setting.py').write_text(test,encoding='utf-8',newline='\n')
print(json.dumps({'status':'055_STAGED','plan_sha256':sha(H/'INSTALL-PLAN.json'),'backend_only_delta_from054':True}))
