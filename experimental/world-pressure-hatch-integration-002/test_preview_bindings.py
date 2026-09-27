"""CPU import/validation only. Never creates a preview or binds a server."""
from pathlib import Path
import importlib.util
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parent
path=ROOT/'candidate/tools/world_builder_engine/world_layout_preview.py'
spec=importlib.util.spec_from_file_location('candidate_hatch_preview',path)
preview=importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)

class ExactRevisionTests(unittest.TestCase):
    def manifest(self,names,backend):
        return {'contract':preview.CONTRACT,'source_pins':{n:{} for n in names if n!='geometry.json'},'inputs':{'backend':backend}}

    def test_current_complete_set_admits_only_current_creator(self):
        manifest=self.manifest(preview.ASSETS,preview.binding(path))
        self.assertEqual(preview.renderer_asset_names(manifest),set(preview.ASSETS))
        manifest['inputs']['backend']['sha256']='0'*64
        with self.assertRaises(preview.PreviewError):preview.renderer_asset_names(manifest)

    def test_reviewed_old_set_retains_exact_historical_size_and_hash(self):
        for digest,size in preview.COMPATIBLE_CREATOR_BACKENDS[preview.CONTRACT].items():
            manifest=self.manifest(preview.LEGACY_ASSET_NAMES,{'sha256':digest,'bytes':size})
            self.assertEqual(preview.renderer_asset_names(manifest),preview.LEGACY_ASSET_NAMES)
            manifest['inputs']['backend']['bytes']+=1
            with self.assertRaises(preview.PreviewError):preview.renderer_asset_names(manifest)

    def test_partial_new_set_and_current_creator_with_old_set_fail_closed(self):
        manifest=self.manifest(set(preview.ASSETS)-{'pressure_hatch_architecture.mjs'},preview.binding(path))
        with self.assertRaises(preview.PreviewError):preview.renderer_asset_names(manifest)
        manifest=self.manifest(preview.LEGACY_ASSET_NAMES,preview.binding(path))
        with self.assertRaises(preview.PreviewError):preview.renderer_asset_names(manifest)

    def test_existing_navigation_preflight_is_unchanged(self):
        relative='tools/world_builder_engine/preflight.mjs'
        self.assertEqual((ROOT/'candidate'/relative).read_bytes(),(ROOT/'preimages'/relative).read_bytes())

    def current(self):
        result=self.manifest(preview.ASSETS,preview.binding(path))
        result['inputs']['hatch_preflight_source']=preview.binding(preview.ROOT/'hatch_preflight.mjs')
        result['inputs']['hatch_dressing_plan_source']=preview.binding(preview.ROOT/'layout_package_assets/source/room_dressing_plan.mjs')
        result['hatch_preflight']={'status':'PASS','contract':'paired_hatch_geometry_preflight_v1'}
        return result

    def test_missing_planner_pin_is_rejected_before_other_input_processing(self):
        manifest=self.current();del manifest['inputs']['hatch_dressing_plan_source']
        with patch.object(preview,'verify_creator'):
            with self.assertRaisesRegex(preview.PreviewError,'Hatch dressing preflight source changed'):
                preview.verify_source(manifest)

    def test_changed_planner_size_hash_or_path_is_rejected(self):
        for field,value in [('sha256','0'*64),('bytes',1),('path',str(ROOT/'other.mjs'))]:
            manifest=self.current();manifest['inputs']['hatch_dressing_plan_source'][field]=value
            with self.subTest(field=field),patch.object(preview,'verify_creator'):
                with self.assertRaisesRegex(preview.PreviewError,'Hatch dressing preflight source changed'):
                    preview.verify_source(manifest)

    def test_exact_planner_binding_proceeds_to_existing_runtime_validation(self):
        manifest=self.current();manifest['inputs']['node']={'path':str(ROOT/'wrong-node.exe')}
        with patch.object(preview,'verify_creator'):
            with self.assertRaisesRegex(preview.PreviewError,'Pinned Node runtime path changed'):
                preview.verify_source(manifest)

    def test_preflight_planner_has_no_omitted_transitive_imports(self):
        source=(preview.ROOT/'layout_package_assets/source/room_dressing_plan.mjs').read_text(encoding='utf-8')
        self.assertNotRegex(source,r'(?m)^\s*(?:import\s|export\s[^;]*\sfrom\s)')
        self.assertNotRegex(source,r'\bimport\s*\(')

if __name__=='__main__':unittest.main(verbosity=2)
