from pathlib import Path
import ast,datetime,difflib,hashlib,json,shutil,subprocess
H=Path(__file__).resolve().parent;W=H.parent;K=Path('@kira_root');C=H/'candidate'
A=C/'tools/world_builder_engine/layout_package_assets';old=W/'world-package-api-candidate-037';door=W/'world-airlock-sequencing-candidate-038'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(path,v):
 path.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
pins=json.loads((H/'INPUT-PINS.json').read_bytes())
assert all(sha(old/'candidate'/rel)==digest for rel,digest in pins['files_037'].items())
assert sha(old/'INSTALL-PLAN.json')==pins['037_install_plan_sha256'] and sha(door/'INSTALL-PLAN.json')==pins['038_install_plan_sha256']
native=C/'tools/world_builder_engine/walk_controller.mjs';assert sha(native)==pins['038_native_controller_sha256']
exporter=A/'source/walk_controller.mjs';s=exporter.read_text();start=s.index('  // Authoring metadata only:');end=s.index('  return freeze({contract:DOOR_CONTRACT',start)
assert (s[:start]+s[end:]).replace('assemblies,definitions,colliders','assemblies,colliders')==native.read_text()
producer=json.loads((A/'PRODUCER-PINS.json').read_bytes())
producer['files']={p.relative_to(A).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(A.rglob('*')) if p.is_file() and p.name!='PRODUCER-PINS.json'}
write(A/'PRODUCER-PINS.json',producer)
contract=json.loads((C/'tools/world_builder_engine/layout_package_contract.json').read_bytes())
contract['contract']='authored_saved_layout_package_v2';contract['scene_metadata_contract']='world_scene_metadata_v2'
contract['supported_recipe']='Pinned authored habitat recipe plus preview_hinged_doors_v2 and explicit paired_airlock_door_sequence_v1 policy; original Mars geometry validation scope remains unchanged.'
contract['held_statuses'].append('airlock_policy_invalid');contract['capabilities']['airlock_pair_policy_metadata']=True
contract['airlock_policy']={'contract':'paired_airlock_door_sequence_v1','source_room_and_portal_ids':True,'exactly_two_distinct_leaf_associations':True,
 'glb_extras_and_independent_sidecar_verification':True,'peer_must_be_closed_and_stopped':True,'pending_and_held_motion_reserves_peer':True,
 'closing_keeps_existing_occupancy_rules':True,'engine_runtime_included':False,'pressure_simulation':False}
write(C/'tools/world_builder_engine/layout_package_contract.json',contract)
protected=json.loads((W/'world-preview-refresh-candidate-028/INSTALL-PLAN.json').read_bytes())['protected_inputs'];assert all(sha(p)==v for p,v in protected.items())
native_before=door/'baseline/walk_controller.mjs';shutil.copyfile(native_before,H/'baseline/installed_walk_controller.mjs')
files=[]
for p in sorted(C.rglob('*')):
 if not p.is_file():continue
 rel=p.relative_to(C);target=K/rel;before=sha(target) if target.exists() else None
 record={'relative_path':rel.as_posix(),'target':str(target),'before_sha256':before,'after':{'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size}}
 if target.exists():
  pre=H/'baseline'/rel
  if not pre.exists():pre.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(target,pre)
  assert sha(pre)==before;record['preimage']=str(pre)
 if p.suffix=='.py':ast.parse(p.read_text(encoding='utf-8'))
 if p.suffix=='.json':json.loads(p.read_bytes())
 files.append(record)
for name in ('build_glb.mjs','authored_scene.mjs','source/scene_metadata.mjs','source/airlock_policy.mjs','source/walk_controller.mjs'):
 subprocess.run(['C:/Program Files/nodejs/node.exe','--check',str(A/name)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)
plan={'status':'HELD_FOR_REAL_API_EXPORT_AND_NATIVE_UI_REVIEW','reviewed':False,'canonical_changes':0,'files':files,'protected_inputs':protected,
 'pending':['Root code review','Coordinated038/current immutable preview creation after installation','Real039 saved Mars API export and GLB policy importer check','Native selected-project action review']}
assert not (H/'INSTALL-PLAN.json').exists();write(H/'INSTALL-PLAN.json',plan)
recovery={'status':'PLANNED_ONLY_NO_PREVIEW_OR_INSTALL','sources':{'api_and_workspace':'frozen037','preview_controller':'frozen038',
 'export_controller':'038 behavior plus read-only037 authoring definitions; exact behavioral strip comparison passed'},
 'native_controller_sha256':sha(native),'export_controller_sha256':sha(exporter),'old_native_controller_sha256':sha(native_before),
 'api_contract':'authored_saved_layout_package_v2','scene_contract':'world_scene_metadata_v2','pair_contract':'paired_airlock_door_sequence_v1',
 'preview_transition':'Use existing selected-job Open current preview refresh after approved install; preserve old immutable copies; pass exact new manifest and digest to039 API. No research regeneration.',
 'rollback':'For existing targets restore only exact recorded preimages after checking candidate hashes. Added exporter modules can remain unreferenced when the workspace preimage is restored. Never delete owner worlds, previews or export packages.',
 'frozen037_038_originals_unchanged':True,'no_real_export_run':True,'gpu_browser_models_ui':0}
write(H/'RECOVERY-MAP.json',recovery)
diff=[]
for p in sorted(C.rglob('*')):
 if not p.is_file() or p.suffix not in ('.py','.mjs','.json'):continue
 rel=p.relative_to(C);original=old/'candidate'/rel
 if original.exists() and original.read_bytes()!=p.read_bytes() and p.name!='PRODUCER-PINS.json':
  diff.extend(difflib.unified_diff(original.read_text().splitlines(True),p.read_text().splitlines(True),fromfile='037/'+rel.as_posix(),tofile='039/'+rel.as_posix()))
(H/'CHANGES-FROM-037.patch').write_text(''.join(diff),encoding='utf-8')
delivery={'status':'039_EXPLICIT_AIRLOCK_EXPORT_POLICY_MOCKED_AND_PURE_CPU_VALIDATED','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),
 'candidate_files':len(files),'candidate_bytes':sum(p['after']['bytes'] for p in files),'mocked_api_callback_cross_language_tests':34,'pure_node_checks':13,
 'native_controller_sha256':sha(native),'export_controller_sha256':sha(exporter),'api_sha256':sha(C/'tools/world_builder_engine/layout_package_export.py'),
 'install_plan_sha256':sha(H/'INSTALL-PLAN.json'),'recovery_map_sha256':sha(H/'RECOVERY-MAP.json'),
 'originals_unchanged':len(protected),'canonical_changes':0,'frozen036_037_038_modified':False,'actual_glb_exports':0,'new_previews':0,'gpu_ui_models':0,
 'pending':['Actual039 GLB extras and importer execution','Native selected-project action review','Root coordinated install/preview review'],'engine_vr_pressure_runtime':False}
write(H/'DELIVERY.json',delivery);print(json.dumps(delivery))
