from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(r"C:\Users\robmc\Kira")
OUT=ROOT/"Avatar/avatar_builder/proofs/neutral_adult_foundation_20260728"
OUT.mkdir(parents=True,exist_ok=True)
def dump(name,value):
    value={"generated_at_utc":datetime.now(timezone.utc).isoformat(),**value}
    (OUT/name).write_text(json.dumps(value,indent=2)+"\n",encoding="utf-8")
def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()

glb=OUT/"neutral_adult_foundation.glb"
dump("BASE_BODY_EVALUATION_REPORT.json",{
 "status":"PARTIAL","selected_candidate":"existing game-ready adult intake reference",
 "comparisons":[
  {"candidate":"current procedural primitives","result":"FAILED","reason":"not a realistic human foundation"},
  {"candidate":"MakeHuman/MPFB","result":"BLOCKED_NOT_INSTALLED","reason":"no approved local installation or reviewed export was present"},
  {"candidate":"existing game-ready adult","result":"SELECTED_FOR_INACTIVE_PRIVATE_PROOF","body_vertices":5909,"bones":54},
 ],
 "visual_review":"upright source verified in Blender; exported GLB requires recorded Z-up to Y-up runtime adapter",
 "rights":"BLOCKED_FOR_DISTRIBUTION: source asset and license are not present in the intake manifest",
 "activation_allowed":False})
dump("STANDARD_AVATAR_TOPOLOGY_SPEC.json",{
 "status":"PARTIAL","version":"STANDARD_AVATAR_TOPOLOGY_SPEC.v1",
 "requirements":{"separate_meshes":["body","clothing","eyes","hair","hair_extra","mouth"],
 "skeleton_bones":54,"height_m":1.78235,"required_face_keys":["smile","frown","surprise","concern","anger","blink","viseme_AA","viseme_EE","viseme_OO","viseme_MBP"]},
 "known_limits":["source redistribution rights unresolved","action library not yet safely embedded in GLB"]})
dump("FACE_RECONSTRUCTION_COMPARISON_REPORT.json",{
 "status":"BLOCKED","isolated_environment":str(ROOT/"Avatar/avatar_builder/ml_face_reconstruction_20260728/.venv"),
 "available_python":"3.14.4","methods":[
  {"name":"MICA","isolated":True,"source_commit":"af22e7a5810d474bc28a1433db533723d6bd2b07",
   "inference":"NOT_RUN","blocker":"upstream environment and pretrained model assets are not compatible/installed in the isolated Python 3.14 environment"},
  {"name":"DECA","isolated":True,"source_commit":"a11554ae2a2b0f3998cf1fa94dd4db03babb34a2",
   "inference":"NOT_RUN","blocker":"upstream environment and required pretrained data are not installed in the isolated Python 3.14 environment"},
  {"name":"EMOCA","isolated":True,"source_commit":"e0be0dbc2d32629ae384ae10c0b7974948c994fd",
   "inference":"NOT_RUN","blocker":"upstream Python 3.6/3.8 environments, submodules, and model assets are unavailable"}],
 "selection":None,"reason":"No method may win without real inference and identity/expression comparison."})
dump("IDENTITY_TRANSFER_REPORT.json",{
 "status":"BLOCKED","face_transfer_attempted":False,
 "reason":"No consented target portrait set and no successful isolated reconstruction output were available.",
 "base_body_changed_to_live_person":False})
dump("IDENTITY_EXPRESSION_STABILITY_REPORT.json",{
 "status":"PARTIAL","expressions_defined":["neutral","smile","frown","surprise","concern","anger"],
 "visemes_defined":["AA","EE","OO","MBP"],"rendered_identity_stability_test":"NOT_COMPLETED",
 "pass_claimed":False})
dump("EYE_SOCKET_VALIDATION_REPORT.json",{
 "status":"FAILED","profile_definitions":{
  "realistic_adult":{"eyeball_diameter_to_head_width":[0.09,0.13],"visible_sclera":"limited","protrusion_m":[-0.002,0.004]},
  "realistic_non_adult":{"eyeball_diameter_to_head_width":[0.10,0.15],"visible_sclera":"limited"},
  "stylized_adult":{"intentional_override_required":True},
  "stylized_non_adult":{"intentional_override_required":True}},
 "selected_profile":"realistic_adult","measured_combined_eye_mesh_m":{"width":0.1107197,"depth":0.0169121,"height":0.0382613},
 "numerical_decision":"FAIL: the combined eye geometry is too shallow to prove two seated globes",
 "separate_eye_mesh":True,"blink_key_defined":True,"gaze_controller":"NOT_IMPLEMENTED",
 "eyelid_contact_measured":False,"globe_protrusion_measured":False,"pass_claimed":False})
dump("HAIR_RUNTIME_VALIDATION_REPORT.json",{
 "status":"PARTIAL","hair_meshes":2,"retarget_motion_test":"NOT_COMPLETED",
 "penetration_test":"NOT_COMPLETED","pass_claimed":False})
dump("FACIAL_RIG_VALIDATION_REPORT.json",{
 "status":"PARTIAL","expression_keys":6,"viseme_keys":4,"blink_key":True,
 "recorded_speech_animation":"NOT_COMPLETED","pass_claimed":False})
dump("GARMENT_TEMPLATE_MATCH_REPORT.json",{
 "status":"BLOCKED","photo_to_garment_inference":"NOT_IMPLEMENTED",
 "existing_garment_mesh_present":True,"template_match_evidence":False})
dump("GARMENT_STATE_VALIDATION_REPORT.json",{
 "status":"PARTIAL","state_contract":["stored","held","dressing-start","partly-inserted","pulled-into-place","partly-fastened","fully-worn","removing","returned-to-storage"],
 "button_contract":["button_id","buttonhole_id","fastened_state","permitted_order","morph_or_bone_response"],
 "simulation":"NOT_IMPLEMENTED","pass_claimed":False})
dump("AVATAR_MOVEMENT_VALIDATION_REPORT.json",{
 "status":"BLOCKED","authored_action_names":["NeutralStanding","Walk","Turn","Sit","StandFromChair","ReachAndHold","DoorThreshold","BasicStairs"],
 "embedded_in_review_glb":False,"reason":"Action export changed the neutral pose; the invalid animated export was rejected.",
 "collision_and_contact_validation":"NOT_COMPLETED","pass_claimed":False})
dump("BODY_STATE_TRUTH_CONTRACT.json",{
 "status":"IMPLEMENTED_SCHEMA_ONLY","channels":["SPOKEN","PRIVATE_MIND","FACTUAL_RUNTIME_TRUTH"],
 "required_runtime_fields":["requested_action","controller_result","body_pose","held_objects","garment_states","location","collision_state"],
 "runtime_binding":"NOT_CONNECTED_IN_THIS_INACTIVE_PROOF"})
dump("FOUNDATION_MANIFEST.json",{
 "status":"PARTIAL","glb":str(glb),"glb_sha256":sha(glb),"blend":str(OUT/"neutral_adult_foundation.blend"),
 "browser_preview":str(OUT/"threejs_preview/index.html"),
 "source_rights":"UNRESOLVED","runtime_activation_allowed":False,"Kira_body_replaced":False,
 "active_v1_9_modified":False,"resident_activation":False,"uploaded":False,"published":False})
print(OUT)
