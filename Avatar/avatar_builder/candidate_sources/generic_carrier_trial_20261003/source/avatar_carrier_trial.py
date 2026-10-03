"""Inactive Kira World Avatar Builder build/save/cold-reload/probe entrypoints.

No imports of bpy, producer, compiler, integration or person state. Root must
qualify and supply those exact objects and its finite IO/checkpoint route.
This is a mechanics carrier trial, not full anatomy, physiology or activation.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path

MODE='generic_female_pre_surface_rest_test_v1'
RECORD_CAP=16384
REQUIRED_SOURCE_PINS={
 'integration':'d42d2a0632a5d966815a5141e1e9cc157d9e1702547c3fa3f53cf4d245f9909e',
 'optional_controller':'21e28804a12dd61e840913c8b28681473e1b68b3d5b751b5beb2f53ca52af78d',
 'v3_producer':'63e968a6a6a3681b996228adee9e491581c6d75f507decba63d62cb9fd570b44',
 'rest_utility':'09dde1d9acfc6305fcb69ad739c8904af8c1e37ebe25660a2a5a3d97d6271b9b',
 'canonical_lineage':'8926c9b6736ae124287b97ef55f583742c1525f56daf57f81c9ac82648b31c29',
 'resolver':'e986c5c82596e043b7060d75a91b23fd8d1a6ab13f687f60373347a3ce257d33',
 'compiler':'2ea78d0694b33e006d7be713a0857cf65117cf4ce941ce46375549578c2ebbde',
 'backend':'c0af42735fbec2a70d76e65911a9e3cbb6063565e62490bfa3cc6b16c69abe5a',
 'profile':'271b660568ebd33c97950f9988888e36455d5637574f2a20724b436b6dd0488c',
}
# Exposed engineering diagnostics, frozen before any physical result. These
# angles are not an anatomical range-of-motion or validated bone-roll oracle.
POSES=(('arm_reach_diagnostic','upperarm01.L',(20.0,0.0,10.0),'lowerarm01.L'),
       ('left_knee_diagnostic','lowerleg01.L',(-35.0,0.0,0.0),'foot.L'))

class TrialError(RuntimeError):
    def __init__(self,state,primary):
        super().__init__('inactive_carrier_trial_failed_no_retry_or_cleanup')
        self.capture=state; self.primary=primary

def raw(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def digest(value): return hashlib.sha256(raw(value)).hexdigest()
def need(value,message):
    if not value: raise ValueError(message)
def pin(value):
    return type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value)
def distance(a,b): return math.sqrt(sum((a[i]-b[i])**2 for i in range(3)))
def state_for(stage):
    return {'stage':stage,'phase':'preflight','returns':[],'objects':{},'primary':None,
            'runtime_authority':False,'full_body_ready':False,'normal_exit_qualified':False}
def call(state,checkpoint,label,fn,*args,**kwargs):
    state['phase']=label
    value=fn(*args,**kwargs); state['returns'].append({'phase':label,'value':value})
    note=checkpoint(state,label); state['returns'].append({'phase':label+':checkpoint','value':note})
    return value
def source_guard(pins,profile_raw):
    need(type(pins) is dict and pins==REQUIRED_SOURCE_PINS,'exact selected source evidence')
    need(type(profile_raw) is bytes and hashlib.sha256(profile_raw).hexdigest()==pins['profile'],'exact generic rig profile')
def fixed_paths(options):
    need(type(options) is dict and set(options)=={'attempt_id','config_path','blend_path','record_path',
          'output_root','acknowledge_generic_inactive'},'closed inactive writer options')
    attempt=options['attempt_id']
    need(type(attempt) is str and len(attempt)==16 and all(c in '0123456789abcdef' for c in attempt),'fresh root trial ID')
    need(options['acknowledge_generic_inactive'] is True,'explicit generic inactive lane')
    root=Path(options['output_root']).absolute()
    paths=[Path(options[key]).absolute() for key in ('blend_path','record_path')]
    need(all(path.parent==root/attempt for path in paths) and paths[0].name=='carrier.blend'
         and paths[1].name=='BUILD-RECORD.json','two fixed new outputs in one fresh trial directory')
    need(not root.name.lower().startswith(('robert','kira','lisa')),'private named output root refused')
    return paths
def static_fingerprint(observation):
    # Full native observation includes all endpoints/parents/roll matrix hashes,
    # body topology/weights and matrices. The record stores a digest; physical
    # custody of the original full observation remains in the retained capture.
    return digest(observation)
def writer_return_guard(value,attempt):
    need(type(value) is dict and set(value)=={'attempt_id','exit_code','normal_exit_observed',
         'complete_original_envelope_qualified','record_sha256','genuine_tool_identity','full_review_sha256'},
         'closed actual writer receipt')
    need(type(value['exit_code']) is int and value['exit_code']==0
         and value['normal_exit_observed'] is True and value['complete_original_envelope_qualified'] is True
         and value['attempt_id']==attempt and pin(value['record_sha256']) and pin(value['full_review_sha256']),
         'separate actual completed writer receipt, not an in-process flag')
    identity=value['genuine_tool_identity']
    alphabet='abcdefghijklmnopqrstuvwxyz0123456789'
    need(type(identity) is dict and set(identity)=={'tool','chunk_id'} and identity['tool']=='exec_command'
         and type(identity['chunk_id']) is str and 6<=len(identity['chunk_id'])<=64
         and identity['chunk_id'][0] in alphabet and all(c in alphabet+'-' for c in identity['chunk_id']),
         'exact genuine writer tool identity; still requires external physical review')

def build_and_save(options,*,controller,integration,producer,compiler,backend_type,
                   profile_raw,source_pin_evidence,checkpoint,io_route):
    """One admitted fresh build, one save, one owned JSON record; no subprocess.

    io_route must be independently qualified. Its reserve_new_trial runs before
    allocation/save and refuses any existing trial or output; observe_saved
    binds one completed exact file and its original native/IO claims. A callback
    return is retained before validation. This interface does not grant IO or
    Blender admission and does not authenticate supplied code objects itself.
    """
    state=state_for('writer'); state['inputs']=(options,controller,integration,producer,compiler,backend_type,
      profile_raw,source_pin_evidence,checkpoint,io_route)
    try:
        need(callable(checkpoint),'root checkpoint required')
        source_guard(source_pin_evidence,profile_raw); blend_path,record_path=fixed_paths(options)
        need(producer.bpy.context.preferences.filepaths.save_version==0,'save backups must already be disabled in fresh admitted process')
        claim=call(state,checkpoint,'reserve_new_trial',io_route.reserve_new_trial,options,65536)
        state['objects']['trial_output_claim']=claim
        need(claim['fresh'] is True and claim['existing_outputs']==0 and claim['attempt_id']==options['attempt_id'],
             'fresh once-only output claim required')
        subset={key:source_pin_evidence[key] for key in integration.EXPECTED_SOURCE_PINS}
        result=call(state,checkpoint,'produce_normalized_weights_then_rest_attachment',controller.run_optional_rest_lane,
          {'mode':MODE,'config_path':options['config_path'],'acknowledge_inactive_authoring':True},
          integration=integration,producer=producer,compiler=compiler,backend_type=backend_type,
          profile_raw=profile_raw,source_pin_evidence=subset,checkpoint=checkpoint)
        state['objects']['producer_capture']=result
        need(result['report']['armature_present'] is True and result['report']['bone_count']==163
             and result['report']['surface_authoring_performed'] is False and result['full_body_ready'] is False,
             'actual selected pre-surface attachment return required')
        body=result['objects']['body']; backend=result['backend']; state['objects']['body']=body
        observation=call(state,checkpoint,'native_neutral_before_save',backend.observe,body)
        compiler._verify_attached(observation,result['attachment_capture']['plan'])
        need(all(bone.matrix_basis.is_identity for bone in body.parent.pose.bones),'neutral pose only at save')
        # Blender's writer is a separately admitted multi-write producer. Never
        # disguise it as one os.write or grant a fake native IO boundary.
        saved=call(state,checkpoint,'one_blender_save',producer.bpy.ops.wm.save_as_mainfile,
                   filepath=str(blend_path),check_existing=True)
        need(saved=={'FINISHED'},'one save did not finish; no retry')
        file_receipt=call(state,checkpoint,'observe_original_saved_file',io_route.observe_saved,claim,blend_path)
        state['objects']['file_receipt']=file_receipt
        need(file_receipt['path']==str(blend_path) and file_receipt['nlink']==1
             and type(file_receipt['bytes']) is int and 0<file_receipt['bytes']<=claim['blend_byte_cap']
             and pin(file_receipt['sha256'])
             and file_receipt['original_close_ack'] is True,'exact saved bytes and original IO close required')
        source_guard(source_pin_evidence,profile_raw)
        record={'schema':'kira.avatar.generic_carrier_trial.writer.v1','attempt_id':options['attempt_id'],
          'candidate_id':result['report']['candidate_id'],'source_pins':dict(source_pin_evidence),
          'lineage_binding':dict(result['lineage_binding']),'native_static_sha256':static_fingerprint(observation),
          'body_name':body.name,'armature_name':body.parent.name,'bone_count':163,
          'saved_file':file_receipt,'selected_mode':MODE,'surface_authoring_performed':False,
          'body_profile':'adult_female','identity_scope':'generic_identity_neutral',
          'save_operator_finished':True,'independent_reload':False,'movement_validated':False,
          'full_anatomy_validated':False,'physiology_validated':False,'full_body_ready':False,
          'normal_exit_qualified':False,'runtime_activation_allowed':False}
        encoded=raw(record); need(len(encoded)<=RECORD_CAP,'complete writer record cap; no truncation')
        state['record']=record
        published=call(state,checkpoint,'publish_original_build_record',io_route.write_record,claim,record_path,encoded,RECORD_CAP)
        state['objects']['record_receipt']=published
        need(published['sha256']==hashlib.sha256(encoded).hexdigest() and published['original_close_ack'] is True,
             'original writer record closed/read back')
        state['status']='BUILD_SAVE_OBSERVED_PENDING_GENUINE_NORMAL_RETURN_AND_COLD_READER'
        return state
    except Exception as primary:
        state['primary']=primary; state['underlying_capture']=getattr(primary,'capture',None)
        raise TrialError(state,primary) from primary

def evaluate_points(state,checkpoint,bpy,body,label):
    depsgraph=call(state,checkpoint,label+':depsgraph',bpy.context.evaluated_depsgraph_get)
    evaluated=call(state,checkpoint,label+':evaluated_body',body.evaluated_get,depsgraph)
    mesh=call(state,checkpoint,label+':evaluated_mesh',evaluated.to_mesh)
    owner={'object':evaluated,'mesh':mesh,'clear_entered':False,'clear_ack':False}
    state['objects'].setdefault('evaluated_owners',[]).append(owner)
    # Owner/returned mesh is retained before subsequent count/point access.
    need(len(mesh.vertices)==14658,'evaluated vertex identity count')
    points=tuple(tuple(float(v) for v in (evaluated.matrix_world @ vertex.co)) for vertex in mesh.vertices)
    need(all(all(math.isfinite(v) for v in point) for point in points),'finite evaluated coordinates')
    state['returns'].append({'phase':label+':complete_points','value':points})
    owner['clear_entered']=True
    call(state,checkpoint,label+':clear_original_evaluated_mesh',evaluated.to_mesh_clear)
    owner['clear_ack']=True
    return points
def group_indices(body,name):
    group=body.vertex_groups.get(name); need(group is not None,'selected sensory group absent: '+name)
    indices=tuple(vertex.index for vertex in body.data.vertices
      if any(binding.group==group.index and binding.weight>=0.1 for binding in vertex.groups))
    need(len(indices)>=25,'selected sensory group too small: '+name)
    return indices
def sensor_observation(points,indices,*,attempt,probe,bone,angles):
    height=min(points[index][2] for index in indices)
    return {'schema':'kira.avatar.synthetic_carrier_sensor.v1','attempt_id':attempt,'probe_id':probe,
      'channel':'geometric_contact_and_joint_command','region_weight_group':bone,'vertices':len(indices),
      'ground_plane_z_m':0.0,'minimum_signed_distance_m':height,'contact_band_m':0.002,
      'geometric_contact_observed':height<=0.002,'penetration_observed':height< -0.002,
      'joint_command_radians':[math.radians(v) for v in angles],
      'force_newtons':None,'neural_backend':None,'brain_input_delivered':False,
      'collision_response_validated':False,'physiology_or_sensation_claim':False}

def cold_reload_and_probe(options,*,bpy,backend_type,profile_raw,source_pin_evidence,
                          accepted_writer_return,checkpoint,io_route):
    """One new reader process after actual writer exit; one load, no save/retry.

    Output is observed diagnostic deformation and analytic sensor events. A
    commanded angle is labelled command, not independently measured joint
    motion. No neural model/person is called. Normal return, body readiness,
    anatomical motion correctness and actual collision physiology stay held.
    """
    state=state_for('reader'); state['inputs']=(options,bpy,backend_type,profile_raw,source_pin_evidence,
      accepted_writer_return,checkpoint,io_route)
    try:
        need(callable(checkpoint),'root checkpoint required'); source_guard(source_pin_evidence,profile_raw)
        blend_path,record_path=fixed_paths(options)
        writer_return_guard(accepted_writer_return,options['attempt_id'])
        need(len(bpy.data.objects)==0 and len(bpy.data.meshes)==0 and len(bpy.data.armatures)==0,
             'fresh empty reader only; preserve unsaved scene, never delete it')
        receipt=call(state,checkpoint,'read_bound_original_record',io_route.read_record,record_path,RECORD_CAP)
        state['objects']['record_input']=receipt
        encoded=receipt['raw']; need(type(encoded) is bytes and len(encoded)<=RECORD_CAP,'complete exact input record')
        need(hashlib.sha256(encoded).hexdigest()==accepted_writer_return['record_sha256'],'writer record matches independent receipt')
        record=json.loads(encoded); state['record']=record
        need(raw(record)==encoded and record['schema']=='kira.avatar.generic_carrier_trial.writer.v1'
             and record['attempt_id']==options['attempt_id'] and record['source_pins']==source_pin_evidence
             and record['saved_file']['path']==str(blend_path) and record['body_profile']=='adult_female'
             and record['identity_scope']=='generic_identity_neutral' and record['runtime_activation_allowed'] is False,
             'exact generic immutable saved record')
        source=call(state,checkpoint,'pin_original_blend_before_load',io_route.pin_existing_blend,blend_path,record['saved_file'])
        state['objects']['blend_input']=source
        need(source['sha256']==record['saved_file']['sha256'] and source['original_close_ack'] is True,
             'exact original saved blob; no old zero-armature substitution')
        loaded=call(state,checkpoint,'one_cold_blender_load',bpy.ops.wm.open_mainfile,filepath=str(blend_path),load_ui=False)
        need(loaded=={'FINISHED'},'cold load did not finish, no retry')
        body=bpy.data.objects.get(record['body_name']); state['objects']['body']=body
        need(body is not None and body.parent is not None and body.parent.name==record['armature_name'],
             'cold named parent binding absent')
        backend=backend_type.__new__(backend_type); state['objects']['backend']=backend
        call(state,checkpoint,'initialize_cold_backend',backend_type.__init__,backend,bpy,record['lineage_binding'])
        observation=call(state,checkpoint,'cold_native_neutral',backend.observe,body)
        need(static_fingerprint(observation)==record['native_static_sha256'],'cold full native topology/weights/rest/roll-matrix digest differs')
        armature=body.parent; state['objects']['armature']=armature
        need(all(bone.matrix_basis.is_identity for bone in armature.pose.bones),'cold neutral pose changed')
        neutral= evaluate_points(state,checkpoint,bpy,body,'neutral')
        rest=tuple(tuple(float(v) for v in (body.matrix_world @ vertex.co)) for vertex in body.data.vertices)
        neutral_max=max(distance(a,b) for a,b in zip(neutral,rest))
        need(neutral_max<=0.000001,'neutral evaluated deformation exceeds original1um diagnostic limit')
        reports=[]; sensors=[]
        for probe,bone_name,angles,region in POSES:
            bone=armature.pose.bones.get(bone_name); need(bone is not None,'selected diagnostic bone missing')
            need(not bone.constraints and armature.animation_data is None,'unselected constraint/animation route')
            # Original neutral basis and mode are retained before explicit pose
            # mutation. Restoration is one planned operation after SUCCESS;
            # failure preserves the partial scene and never retries cleanup.
            original_basis=bone.matrix_basis.copy(); original_mode=bone.rotation_mode
            state['objects'].setdefault('pose_owners',[]).append({'bone':bone,'basis':original_basis,'mode':original_mode})
            bone.rotation_mode='XYZ'; bone.rotation_euler=tuple(math.radians(v) for v in angles)
            call(state,checkpoint,probe+':update',bpy.context.view_layer.update)
            points=evaluate_points(state,checkpoint,bpy,body,probe)
            displacements=tuple(distance(a,b) for a,b in zip(points,neutral))
            indices=group_indices(body,region)
            selected_max=max(displacements[index] for index in indices)
            moved=sum(value>0.00001 for value in displacements); maximum=max(displacements)
            need(moved>=25 and maximum>=0.002 and selected_max>=0.001,'command produced insufficient actual evaluated deformation')
            reports.append({'probe_id':probe,'command_bone':bone_name,'command_degrees_xyz':list(angles),
              'moved_vertices_over_10um':moved,'maximum_displacement_m':maximum,
              'region_weight_group':region,'region_maximum_displacement_m':selected_max,
              'observed_geometry_sha256':digest(points),'anatomical_range_or_direction_validated':False})
            sensor=sensor_observation(points,indices,attempt=options['attempt_id'],probe=probe,bone=region,angles=angles)
            sensors.append(sensor)
            bone.matrix_basis=original_basis; bone.rotation_mode=original_mode
            call(state,checkpoint,probe+':restore_after_success',bpy.context.view_layer.update)
            restored=evaluate_points(state,checkpoint,bpy,body,probe+':restored_neutral')
            need(max(distance(a,b) for a,b in zip(restored,neutral))<=0.000001,'planned neutral restoration differs')
        final=call(state,checkpoint,'cold_final_static_neutral',backend.observe,body)
        need(static_fingerprint(final)==record['native_static_sha256'],'probes changed static body/rig/weights')
        source_guard(source_pin_evidence,profile_raw)
        summary={'schema':'kira.avatar.generic_carrier_trial.reader.v1','attempt_id':options['attempt_id'],
          'saved_reload_observed':True,'neutral_maximum_displacement_m':neutral_max,
          'diagnostic_deformation_observed':reports,'synthetic_sensor_events':sensors,
          'read_only_source_blob_sha256':record['saved_file']['sha256'],'brain_input_delivered':False,
          'rest_roll_oracle_validated':False,'full_collision_validated':False,'anatomy_validated':False,
          'physiology_validated':False,'full_body_ready':False,'normal_exit_qualified':False,
          'runtime_activation_allowed':False,'generic_builder_method_promoted':False}
        need(len(raw(summary))<=8192,'complete cold summary cap')
        state['summary']=summary; state['status']='COLD_RELOAD_AND_DIAGNOSTIC_GEOMETRY_OBSERVED_EXIT_AND_WHOLE_BODY_HOLD'
        return state
    except Exception as primary:
        state['primary']=primary; state['underlying_capture']=getattr(primary,'capture',None)
        raise TrialError(state,primary) from primary
