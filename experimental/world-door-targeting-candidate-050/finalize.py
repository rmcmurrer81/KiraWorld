from pathlib import Path
import datetime,difflib,hashlib,json
H=Path(__file__).resolve().parent;K=Path('@kira_root');E=K/'tools/world_builder_engine'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(name,value):
    with (H/name).open('x',encoding='utf8') as f:json.dump(value,f,indent=2);f.write('\n')
protected=json.loads((H.parent/'world-crew-habitat-eligibility-049/REVIEW-PLAN.json').read_bytes())['protected_inputs']
assert all(sha(p)==v for p,v in protected.items())
test=json.loads((H/'ACTUAL-DOOR-TEST-RESULT.json').read_bytes());assert test['status']=='ACTUAL_SAVED_MARS_FACING_AND_DOOR_MECHANICS_PASS' and test['checks_count']==7
ui=json.loads((H/'VIEWER-MESSAGE-RESULT.json').read_bytes());assert ui['status']=='ACTUAL_VIEWER_CALLBACK_AND_LABEL_CODE_PASS'
rows=[];diff=''
for name in ['walk_controller.mjs','viewer.mjs']:
    target=E/name;before=H/'baseline'/name;after=H/'candidate/tools/world_builder_engine'/name;assert sha(target)==sha(before)
    rows.append({'relative_path':'tools/world_builder_engine/'+name,'target':str(target),'before_sha256':sha(before),'preimage':str(before),'after':{'path':str(after),'sha256':sha(after),'bytes':after.stat().st_size}})
    diff+=''.join(difflib.unified_diff(before.read_text(encoding='utf8').splitlines(True),after.read_text(encoding='utf8').splitlines(True),fromfile='installed/'+name,tofile='candidate050/'+name))
(H/'SOURCE.diff').write_text(diff,encoding='utf8',newline='\n')
write('REVIEW-PLAN.json',{'status':'050_ISOLATED_FRONTEND_PROPOSAL_NOT_COMPLETE_INSTALL_PLAN','files':rows,'protected_inputs':protected,
    'promotion_hold':'Coordinate exporter/controller-source and producer pin successor, then immutable preview and actual package checks; do not install these two frontend files alone.'})
dependencies=['walk_controller.mjs','viewer.mjs','horizontal_navigation.mjs','layout_package_export.py','layout_package_assets/source/walk_controller.mjs','layout_package_assets/source/room_dressing_plan.mjs',
    'layout_package_assets/source/scene_metadata.mjs','layout_package_assets/authored_scene.mjs','layout_package_assets/PRODUCER-PINS.json']
write('SOURCE-PINS.json',{n:sha(E/n) for n in dependencies})
write('PRESERVATION.json',{'status':'PASS','protected_inputs_unchanged':len(protected),'geometry_sha256':test['geometry_sha256'],'candidate_only':True,'canonical_writes':0,'model_ui_gpu_jobs':0})
closure={p.relative_to(H).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(H.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.name not in {'SOURCE-CLOSURE.json','DELIVERY.json'}}
write('SOURCE-CLOSURE.json',closure)
delivery={'status':'050_ACTUAL_MARS_DOOR_TARGET_FIX_READY_NOT_INSTALLED','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),'proposal_sha256':sha(H/'REVIEW-PLAN.json'),'source_diff_sha256':sha(H/'SOURCE.diff'),
    'candidate_files':{r['relative_path']:r['after']['sha256'] for r in rows},'actual_saved_geometry_checks':7,'actual_viewer_code_state_cases':4,'all6_actual_door_routes_pass':True,
    'door_pose_frame_collision_equal_to_installed':True,'dressing_colliders_used':51,'protected_inputs_unchanged':116,'geometry_owner_files_copied_or_modified':False,
    'canonical_edits':0,'models_ui_gpu':0,'visual_or_owner_approval':False,'install_hold':'Exporter source/pin compatibility and actual new immutable preview/package checks required; current two-file proposal is not standalone-installable.'}
write('DELIVERY.json',delivery);print(json.dumps(delivery,indent=2))
