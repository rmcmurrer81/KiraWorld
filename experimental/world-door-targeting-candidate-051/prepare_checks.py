"""Reuse frozen meaningful050/045 checks without editing their history."""
from pathlib import Path
import hashlib,json,shutil
H=Path(__file__).resolve().parent;W=H.parent;F=W/'world-door-targeting-candidate-050';G=W/'world-galley-detail-045'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=sha(H/'INSTALL-PLAN.json')
shutil.copytree(F/'baseline',H/'baseline')
old=(F/'test_actual_doors.mjs').read_text(encoding='utf-8')
for mode,path in [('FRONTEND','./candidate/tools/world_builder_engine/walk_controller.mjs'),('PORTABLE','./candidate/tools/world_builder_engine/layout_package_assets/source/walk_controller.mjs')]:
 text=old.replace("'./candidate/tools/world_builder_engine/walk_controller.mjs'",repr(path))
 text=text.replace("./ACTUAL-DOOR-TEST-RESULT.json",'./'+mode+'-DOOR-TEST-RESULT.json').replace('ACTUAL_SAVED_MARS_FACING_AND_DOOR_MECHANICS_PASS',mode+'_ACTUAL_SAVED_MARS_FACING_AND_DOOR_MECHANICS_PASS')
 text=text.replace('No new visual review, renderer/export refresh or installation.','No visual review or installation; immutable preview/export checks are recorded separately.')
 (H/('test_'+mode.lower()+'_doors.mjs')).write_text(text,encoding='utf-8',newline='\n')
shutil.copyfile(F/'test_viewer_messages.mjs',H/'test_viewer_messages.mjs')
installer=(G/'install_exact.py').read_text(encoding='utf-8').replace('045','051')
installer=installer.replace('8d5160f30205936e015cf5938cbaa69e0caa68552553e1735b5db2f339a3ae71',plan)
installer=installer.replace("'tools/world_builder_engine/layout_package_assets/source/room_dressing_render.mjs'","'tools/world_builder_engine/layout_package_assets/source/walk_controller.mjs'")
installer=installer.replace("'tools/world_builder_engine/layout_package_assets/authored_scene.mjs'","'tools/world_builder_engine/walk_controller.mjs'")
(H/'install_exact.py').write_text(installer,encoding='utf-8',newline='\n')
(H/'test_installer.py').write_text((G/'test_installer.py').read_text(encoding='utf-8').replace('045','051'),encoding='utf-8',newline='\n')
runner=(G/'run_cpu_export.py').read_text(encoding='utf-8').replace('045','051').replace('8d5160f30205936e015cf5938cbaa69e0caa68552553e1735b5db2f339a3ae71',plan)
runner=runner.replace("if name=='viewer.mjs'", "if name in ('viewer.mjs','walk_controller.mjs')")
runner=runner.replace("frozen=preview.verify_preview(prepared['manifest_path'],prepared['manifest_sha256'])", "frozen=preview.verify_preview(prepared['manifest_path'],prepared['manifest_sha256'])\n repeat=preview.create_preview(i['geometry_source']['path'],i['research_packet']['path'],i['blueprint']['path'])\n assert repeat['reused'] is True and repeat['manifest_sha256']==prepared['manifest_sha256']")
runner=runner.replace("'preview_server_or_ui_started':False", "'preview_server_or_ui_started':False,'new_immutable_preview_reused_on_repeat':True")
# Validate appearance pins actually copied into the new immutable manifest.
runner=runner.replace("for key,row in i.items():", "assert all(frozen['source_pins'][name]['sha256']==sha(C/name) for name in ('viewer.mjs','walk_controller.mjs'))\n for key,row in i.items():")
(H/'run_cpu_export.py').write_text(runner,encoding='utf-8',newline='\n')
print(json.dumps({'status':'051_CHECK_HARNESSES_PREPARED','plan_sha256':plan,'reused_frozen_sources':['050 actual door/viewer tests','045 reversible installer/resource-bounded CPU exporter']}))
