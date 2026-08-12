"""Hostile static author tests for disconnected Blackwell V13."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Core/persistent_blackwell_voice_integration_v13.py"
CONFIG = (
    ROOT
    / "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v13/candidate_config.json"
)


def run_probe(source: str) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-c", source],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )


class BlackwellV13ControlBindingStaticTests(unittest.TestCase):
    def test_01_config_binds_exact_control_source_and_is_default_off(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        raw = SOURCE.read_bytes()
        self.assertEqual(config["control_module_bytes"], len(raw))
        self.assertEqual(config["control_module_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertIs(config["production_routing_authorized"], False)
        self.assertIs(config["live_execution_authorized"], False)
        self.assertIs(config["future_harness_authoring_authorized"], False)
        self.assertIs(config["playback_authorized"], False)
        self.assertIs(config["different_fresh_static_audit_required"], True)

    def test_02_static_lifecycle_revalidates_and_never_constructs_live_backend(self):
        result = run_probe(
            "import Core.persistent_blackwell_voice_integration_v13 as v; "
            "b=v.create_static_control_plane_binding_v13(); "
            "assert b.public_state()['prepared_static'] is False; "
            "assert b.prepare_static()['prepared_static'] is True; "
            "x=b.read_typed_memory_mib(); assert type(x) is tuple and len(x)==4; "
            "s=b.revalidate(); assert s['prepared_static'] is True; "
            "assert s['live_execution_authorized'] is False; print('V13_LIFECYCLE_PASS')"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("V13_LIFECYCLE_PASS", result.stdout)

    def test_03_self_module_and_package_replacement_fail_closed(self):
        result = run_probe(
            "import sys,types,Core; import Core.persistent_blackwell_voice_integration_v13 as v; "
            "b=v.create_static_control_plane_binding_v13(); "
            "fake=types.ModuleType(v.__name__); sys.modules[v.__name__]=fake; "
            "setattr(Core,'persistent_blackwell_voice_integration_v13',fake); "
            "\ntry: b.public_state()\nexcept v.V13ControlPlaneError: print('V13_SWAP_REJECT')\n"
            "else: raise AssertionError('module replacement accepted')"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("V13_SWAP_REJECT", result.stdout)

    def test_04_self_validator_global_replacement_fails_closed(self):
        result = run_probe(
            "import Core.persistent_blackwell_voice_integration_v13 as v; "
            "b=v.create_static_control_plane_binding_v13(); "
            "v._ensure_v12_import_slots_clean=lambda:None; "
            "\ntry: b.public_state()\nexcept v.V13ControlPlaneError: print('V13_GLOBAL_REJECT')\n"
            "else: raise AssertionError('validator replacement accepted')"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("V13_GLOBAL_REJECT", result.stdout)

    def test_05_private_v12_function_and_class_mutation_fail_closed(self):
        result = run_probe(
            "import Core.persistent_blackwell_voice_integration_v13 as v; "
            "b=v.create_static_control_plane_binding_v13(); m=b._v12_module; "
            "m._ensure_import_slots_clean=lambda:None; "
            "\ntry: b.public_state()\nexcept v.V13ControlPlaneError: print('V12_GLOBAL_REJECT')\n"
            "else: raise AssertionError('private V12 mutation accepted')"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("V12_GLOBAL_REJECT", result.stdout)

    def test_06_preexisting_normal_v12_module_slot_is_rejected(self):
        result = run_probe(
            "import sys,types; import Core.persistent_blackwell_voice_integration_v13 as v; "
            "sys.modules[v.V12_NAME]=types.ModuleType(v.V12_NAME); "
            "\ntry: v.create_static_control_plane_binding_v13()\n"
            "except v.V13ControlPlaneError: print('V12_SLOT_REJECT')\n"
            "else: raise AssertionError('normal V12 slot accepted')"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("V12_SLOT_REJECT", result.stdout)

    def test_07_public_live_entrypoints_refuse(self):
        result = run_probe(
            "import Core.persistent_blackwell_voice_integration_v13 as v; "
            "\nfor f in (v.open_production_blackwell_v13,v.bounded_engineering_candidate_v13):\n"
            "  try: f()\n  except v.V13ControlPlaneError: pass\n"
            "  else: raise AssertionError('live entrypoint accepted')\n"
            "print('V13_LIVE_REFUSAL_PASS')"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("V13_LIVE_REFUSAL_PASS", result.stdout)

    def test_08_duplicate_config_keys_and_numeric_only_digests_reject(self):
        result = run_probe(
            "import Core.persistent_blackwell_voice_integration_v13 as v; "
            "\ntry: v._strict_object([('x',1),('x',2)])\n"
            "except v.V13ControlPlaneError: pass\nelse: raise AssertionError('duplicate accepted')\n"
            "assert v._is_sha256('0'*64) is False; assert v._is_sha256('a'+'0'*63) is True; "
            "print('V13_STRICT_TYPES_PASS')"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("V13_STRICT_TYPES_PASS", result.stdout)

    def test_09_no_heavy_module_or_audio_playback_import(self):
        result = run_probe(
            "import sys; before={n:n in sys.modules for n in ('torch','ollama','chatterbox','bpy')}; "
            "import Core.persistent_blackwell_voice_integration_v13 as v; "
            "b=v.create_static_control_plane_binding_v13(); b.prepare_static(); "
            "assert before=={n:n in sys.modules for n in before}; print('V13_NO_HEAVY_IMPORT_PASS')"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("V13_NO_HEAVY_IMPORT_PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
