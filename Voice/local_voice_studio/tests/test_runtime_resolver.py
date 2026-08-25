from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from .support import generic_voice
from .test_voice_design import brief
from kira_local_voice.registry import VoiceRegistry
from kira_local_voice.runtime_resolver import (
    CURRENT_RUNTIME_PROVENANCE_SCOPE,
    ExactRuntimeVoiceResolver,
)
from kira_local_voice.voice_design import VoiceDesignEngine, VoiceDesignStore


def capabilities(
    *, revision: str, voices: list[str], grants: bool,
    provenance_scope: str = CURRENT_RUNTIME_PROVENANCE_SCOPE,
) -> dict:
    return {
        "schema": "kira.local-voice.capabilities.v1",
        "local_only": True,
        "backend": {
            "name": "exact-test-runtime",
            "version": "1",
            "ready": True,
            "formats": ["wav"],
            "languages": ["en-US"],
            "voice_cloning": False,
            "voice_design": False,
            "mock": False,
            "offline": True,
            "network_access": "none",
            "telemetry": "none",
            "model_source": "hexgrad/Kokoro-82M",
            "model_revision": revision,
            "license_id": "Apache-2.0",
            "voice_ids": voices,
            "provenance_scope": provenance_scope,
            "audition_evidence_revision": "f3ff3571791e39611d31c381e3a41a3af07b4987",
            "audition_evidence_grants_runtime_access": grants,
            "unavailable_reason": None,
        },
    }


class FakeService:
    def __init__(self, registry: VoiceRegistry, caps: dict):
        self.registry = registry
        self._caps = caps

    def capabilities(self) -> dict:
        return self._caps


class RuntimeResolverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.registry = VoiceRegistry(self.root / "voices")
        self.engine = VoiceDesignEngine(VoiceDesignStore(self.root / "design"), self.registry)
        self.bundle = self.engine.create_bundle(brief(candidate_count=5))
        self.by_voice = {item["backend_voice_id"]: item for item in self.bundle["candidates"]}

    def tearDown(self):
        self.temp.cleanup()

    def register(self, voice_id: str):
        self.registry.register(replace(generic_voice(voice_id), language="en-US"))

    def test_superseded_fbba_label_is_not_a_binding_for_f3ff_catalog_evidence(self):
        self.register("af_heart")
        service = FakeService(
            self.registry,
            capabilities(
                revision="fbba31e67ad83eb66394c926627e99d35abeb087",
                voices=["af_heart", "am_fenrir"],
                grants=False,
            ),
        )
        result = ExactRuntimeVoiceResolver(self.engine, service).resolve(
            self.bundle["bundle_id"], self.by_voice["af_heart"]["candidate_id"]
        )
        self.assertEqual(result["status"], "blocked")
        self.assertIn("runtime_model_revision_mismatch", result["blockers"])
        self.assertIn("runtime_evidence_does_not_grant_catalog_access", result["blockers"])
        self.assertFalse(result["activation_performed"])

    def test_seven_extra_design_voices_are_not_current_runtime_routes(self):
        self.register("af_bella")
        service = FakeService(
            self.registry,
            capabilities(
                revision="f3ff3571791e39611d31c381e3a41a3af07b4987",
                voices=["af_bella"],
                grants=True,
            ),
        )
        result = ExactRuntimeVoiceResolver(self.engine, service).resolve(
            self.bundle["bundle_id"], self.by_voice["af_bella"]["candidate_id"]
        )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["blockers"], ["voice_id_not_in_current_runtime_allowlist"])

    def test_exact_future_reviewed_bridge_can_resolve_without_activating(self):
        self.register("af_heart")
        service = FakeService(
            self.registry,
            capabilities(
                revision="f3ff3571791e39611d31c381e3a41a3af07b4987",
                voices=["af_heart"],
                grants=True,
            ),
        )
        result = ExactRuntimeVoiceResolver(self.engine, service).resolve(
            self.bundle["bundle_id"], self.by_voice["af_heart"]["candidate_id"]
        )
        self.assertEqual(result["status"], "ready_for_local_audition_synthesis")
        self.assertEqual(result["blockers"], [])
        self.assertEqual(result["candidate_spec"]["voice_id"], "af_heart")
        self.assertEqual(result["candidate_spec"]["model_revision"], "f3ff3571791e39611d31c381e3a41a3af07b4987")
        self.assertFalse(result["activation_performed"])

    def test_ready_runtime_with_widened_provenance_scope_is_blocked(self):
        self.register("af_heart")
        service = FakeService(
            self.registry,
            capabilities(
                revision="f3ff3571791e39611d31c381e3a41a3af07b4987",
                voices=["af_heart"],
                grants=True,
                provenance_scope="all-audition-catalog-voices",
            ),
        )
        result = ExactRuntimeVoiceResolver(self.engine, service).resolve(
            self.bundle["bundle_id"], self.by_voice["af_heart"]["candidate_id"]
        )
        self.assertEqual(result["status"], "blocked")
        self.assertIn("runtime_provenance_scope_mismatch", result["blockers"])

    def test_missing_or_deactivated_registry_profile_blocks_resolution(self):
        service = FakeService(
            self.registry,
            capabilities(
                revision="f3ff3571791e39611d31c381e3a41a3af07b4987",
                voices=["af_heart"],
                grants=True,
            ),
        )
        resolver = ExactRuntimeVoiceResolver(self.engine, service)
        candidate_id = self.by_voice["af_heart"]["candidate_id"]
        self.assertIn(
            "runtime_voice_profile_not_registered",
            resolver.resolve(self.bundle["bundle_id"], candidate_id)["blockers"],
        )
        self.register("af_heart")
        self.registry.deactivate("af_heart", reason="test deactivation", authority="test suite")
        self.assertIn(
            "runtime_voice_profile_deactivated",
            resolver.resolve(self.bundle["bundle_id"], candidate_id)["blockers"],
        )


if __name__ == "__main__":
    unittest.main()
