"""Hostile static-only tests for append-only Blackwell v8.

No test imports/runs Torch, Ollama, Chatterbox, CUDA, winsound playback, a
person route, or Blender.  Static synthetic PCM is never played.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import shutil
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from Core.blackwell_v7_process_boundary import V7ProcessTimeout
from Core.persistent_blackwell_voice_integration_v8 import (
    BlackwellV8Coordinator,
    LIVE_ADAPTER_AVAILABLE,
    PLAYBACK_AUTHORIZED,
    PLAYBACK_IMPLEMENTED,
    PRODUCTION_ROUTING_AUTHORIZED,
)
from Testing.blackwell_v8_static_fixture_backend import (
    ManualClock,
    ReplacingTensorV8Backend,
    StaticPlaybackRunnerV8,
    StaticV7Backend,
)
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v7 import (
    persistent_worker as v7,
)
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v8.candidate_contract import (
    CANONICAL_CONFIG_SHA256,
    CONFIG_PATH,
    EXACT_PROFILE_SHA256,
    EXACT_REFERENCE_SHA256,
    V8ContractError,
    load_canonical_config,
    sha256_file,
    strict_json_loads,
    verify_fresh_audit_authorization,
    verify_preserved_bytes,
    verify_seal_manifest,
)
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v8.persistent_worker import (
    PersistentWorkerV8,
    V8LiveStateEngine,
)


ROOT = Path(__file__).resolve().parents[1]
V8_PACKAGE = ROOT / "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v8"


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class DirectEngine:
    def __init__(self):
        self.clock = ManualClock(1000.0)
        self.lease = _sha("v8-static-direct-lease")
        self.backend = StaticV7Backend(
            now=self.clock, worker_pid=43210, lease_id=self.lease
        )
        self.core = V8LiveStateEngine(
            backend=self.backend,
            serialization_lease_id=self.lease,
            worker_instance_id=_sha("v8-static-direct-worker"),
            worker_pid=43210,
            now=self.clock,
            v8_config=load_canonical_config(),
        )
        self.runner = StaticPlaybackRunnerV8(
            config=load_canonical_config(), now=self.clock
        )
        self.v8 = PersistentWorkerV8(
            engine=self.core, playback_runner=self.runner, now=self.clock
        )

    def load_and_synthesize(self):
        loaded = self.v8.dispatch("load", {"owner_hash": _sha("owner")})
        if loaded.get("success") is not True:
            raise AssertionError(loaded)
        text = "Static Kira voice bytes for v8 playback contract testing."
        result = self.v8.dispatch(
            "synthesis",
            {
                "text": text,
                "text_sha256": _sha(text),
                "input_channel": "public_spoken_only",
                "profile_sha256": EXACT_PROFILE_SHA256,
                "reference_sha256": EXACT_REFERENCE_SHA256,
                "condition_digest": loaded["condition_digest"],
            },
        )
        if result.get("success") is not True:
            raise AssertionError(result)
        return result["artifact_lease"]

    def close(self):
        try:
            self.v8.dispatch("cleanup", {"reason": "static_test_end"})
        finally:
            self.backend.close()


class V8ConfigTruthTests(unittest.TestCase):
    def test_config_and_preserved_bytes_are_exact(self):
        config = load_canonical_config()
        self.assertEqual(sha256_file(CONFIG_PATH), CANONICAL_CONFIG_SHA256)
        self.assertEqual(len(verify_preserved_bytes(config)), 16)
        self.assertTrue(config["live_adapter_available"])
        self.assertFalse(config["live_adapter_live_validated"])
        self.assertTrue(config["playback_implemented"])
        self.assertFalse(config["playback_live_validated"])
        self.assertFalse(config["production_routing_authorized"])
        self.assertFalse(config["playback_authorized_by_this_candidate"])

    def test_module_truth_matches_config(self):
        self.assertTrue(LIVE_ADAPTER_AVAILABLE)
        self.assertTrue(PLAYBACK_IMPLEMENTED)
        self.assertFalse(PLAYBACK_AUTHORIZED)
        self.assertFalse(PRODUCTION_ROUTING_AUTHORIZED)

    def test_current_production_routing_manifest_is_still_exact(self):
        config = load_canonical_config()
        expected = config["sealed_v2_production_components"][
            "Voice/sidecars/kira_approved_voice_routing.json"
        ]
        self.assertEqual(
            sha256_file(ROOT / "Voice/sidecars/kira_approved_voice_routing.json"),
            expected,
        )

    def test_production_and_unaudited_engineering_factories_refuse(self):
        with self.assertRaisesRegex(V8ContractError, "not production"):
            BlackwellV8Coordinator.production_candidate()
        with self.assertRaises(V8ContractError):
            BlackwellV8Coordinator.bounded_engineering_candidate(
                nonce=_sha("nonce"), accepted_audit_sha256="0" * 64
            )

    def test_author_did_not_create_future_audit_authorization(self):
        config = load_canonical_config()
        path = ROOT / config["fresh_audit_contract"]["required_relative_path"]
        self.assertFalse(path.exists())
        with self.assertRaises(V8ContractError):
            verify_fresh_audit_authorization(
                config, expected_audit_sha256="0" * 64
            )

    def test_static_seal_rehashes_every_required_v8_file(self):
        config = load_canonical_config()
        seal = ROOT / config["fresh_audit_contract"]["required_seal_manifest_path"]
        value = verify_seal_manifest(config, seal)
        self.assertEqual(len(value["files"]), 10)

    def test_import_is_inert_and_does_not_import_live_stacks(self):
        before = {name: name in sys.modules for name in (
            "torch", "torchaudio", "chatterbox", "winsound", "bpy"
        )}
        with patch("urllib.request.urlopen") as network, patch("subprocess.Popen") as popen:
            __import__(
                "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v8.live_adapter"
            )
        network.assert_not_called()
        popen.assert_not_called()
        for name, existed in before.items():
            if not existed:
                self.assertNotIn(name, sys.modules)

    def test_strict_json_rejects_nonfinite_duplicate_and_deep(self):
        for raw in (b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1,"x":2}'):
            with self.assertRaises(Exception):
                strict_json_loads(raw)
        with self.assertRaises(Exception):
            strict_json_loads("[" * 70 + "0" + "]" * 70)

    def test_live_source_binds_exact_components_and_no_fallback(self):
        source = (V8_PACKAGE / "live_adapter.py").read_text(encoding="utf-8")
        self.assertIn("PersistentVoiceRuntime", source)
        self.assertIn("t3", json.dumps(load_canonical_config()))
        self.assertIn("/api/ps", source)
        self.assertIn("/api/chat", source)
        self.assertIn('"device": "cuda"', source)
        self.assertIn('"generic_voice_used": False', source)
        self.assertIn('"sapi_voice_used": False', source)
        self.assertNotIn("pyttsx", source.casefold())
        self.assertNotIn("child_environment = dict(os.environ)", source)
        self.assertIn("_playback_child_environment", source)

    def test_only_playback_worker_contains_winsound(self):
        for path in V8_PACKAGE.glob("*.py"):
            source = path.read_text(encoding="utf-8")
            if path.name == "playback_worker.py":
                self.assertIn("import winsound", source)
                self.assertIn("SND_SYNC", source)
                self.assertIn("SND_MEMORY", source)
            else:
                self.assertNotIn("import winsound", source)


class V8PlaybackTruthTests(unittest.TestCase):
    def _case(self):
        case = DirectEngine()
        self.addCleanup(case.close)
        lease = case.load_and_synthesize()
        playback_id = _sha(f"playback-{id(case)}")
        return case, lease, playback_id

    def test_playback_and_explicit_owner_hearing_are_separate(self):
        case, lease, playback_id = self._case()
        played = case.v8.dispatch(
            "playback",
            {**{key: lease[key] for key in ("handle_id", "artifact_sha256", "generation_id")},
             "playback_id": playback_id},
        )
        self.assertTrue(played["success"])
        self.assertFalse(played["playback"]["owner_hearing_proven"])
        self.assertIsNone(played["playback"]["owner_hearing_observation"])
        self.assertEqual(
            played["playback"]["played_memory_sha256"], lease["artifact_sha256"]
        )
        ack = case.v8.dispatch(
            "owner_hearing_ack",
            {
                "playback_id": playback_id,
                "artifact_sha256": lease["artifact_sha256"],
                "generation_id": lease["generation_id"],
                "owner_hash": _sha("owner"),
                "observation": "heard_complete",
                "acknowledgement_id": _sha("owner-heard-this-once"),
            },
        )
        self.assertTrue(ack["success"])
        self.assertTrue(ack["owner_hearing"]["owner_hearing_proven"])
        self.assertFalse(ack["owner_hearing"]["automatic_claim"])

    def test_partial_nothing_and_uncertain_never_claim_complete_hearing(self):
        for observation in ("heard_partial", "heard_nothing", "uncertain"):
            case = DirectEngine()
            try:
                lease = case.load_and_synthesize()
                playback_id = _sha(f"{observation}-playback")
                self.assertTrue(case.v8.dispatch("playback", {
                    "handle_id": lease["handle_id"],
                    "artifact_sha256": lease["artifact_sha256"],
                    "generation_id": lease["generation_id"],
                    "playback_id": playback_id,
                })["success"])
                ack = case.v8.dispatch("owner_hearing_ack", {
                    "playback_id": playback_id,
                    "artifact_sha256": lease["artifact_sha256"],
                    "generation_id": lease["generation_id"],
                    "owner_hash": _sha("owner"),
                    "observation": observation,
                    "acknowledgement_id": _sha(observation),
                })
                self.assertFalse(ack["owner_hearing"]["owner_hearing_proven"])
            finally:
                case.close()

    def test_playback_rejects_route_substitution_false_hearing_and_escape(self):
        modes = (
            "generic", "sapi", "cpu", "owner_claim", "not_in_job",
            "wrong_wav", "wrong_component", "wrong_memory",
            "bad_process_identity", "future",
        )
        for mode in modes:
            case = DirectEngine()
            try:
                lease = case.load_and_synthesize()
                case.runner.mode = mode
                result = case.v8.dispatch("playback", {
                    "handle_id": lease["handle_id"],
                    "artifact_sha256": lease["artifact_sha256"],
                    "generation_id": lease["generation_id"],
                    "playback_id": _sha("hostile-" + mode),
                })
                self.assertFalse(result["success"], mode)
                self.assertFalse(result["owner_hearing_proven"], mode)
            finally:
                case.close()

    def test_retained_path_mutation_is_rejected_before_consumer(self):
        case, lease, playback_id = self._case()
        path = Path(case.core.retained_artifact["resolved_path"])
        with path.open("ab") as handle:
            handle.write(b"mutated")
        result = case.v8.dispatch("playback", {
            "handle_id": lease["handle_id"],
            "artifact_sha256": lease["artifact_sha256"],
            "generation_id": lease["generation_id"],
            "playback_id": playback_id,
        })
        self.assertFalse(result["success"])
        self.assertEqual(case.runner.call_count, 0)

    def test_component_mutation_is_rejected_before_consumer(self):
        case, lease, playback_id = self._case()
        case.core.model.t3.tensor.payload = b"changed-t3-parameter"
        result = case.v8.dispatch("playback", {
            "handle_id": lease["handle_id"],
            "artifact_sha256": lease["artifact_sha256"],
            "generation_id": lease["generation_id"],
            "playback_id": playback_id,
        })
        self.assertFalse(result["success"])
        self.assertEqual(case.runner.call_count, 0)

    def test_qwen_appearance_race_rejects_playback(self):
        case, lease, playback_id = self._case()
        case.backend.qwen_race_phase = "v8_playback_before"
        result = case.v8.dispatch("playback", {
            "handle_id": lease["handle_id"],
            "artifact_sha256": lease["artifact_sha256"],
            "generation_id": lease["generation_id"],
            "playback_id": playback_id,
        })
        self.assertFalse(result["success"])
        self.assertEqual(case.runner.call_count, 0)

    def test_playback_id_and_owner_ack_are_one_time(self):
        case, lease, playback_id = self._case()
        payload = {
            "handle_id": lease["handle_id"],
            "artifact_sha256": lease["artifact_sha256"],
            "generation_id": lease["generation_id"],
            "playback_id": playback_id,
        }
        self.assertTrue(case.v8.dispatch("playback", payload)["success"])
        ack = {
            "playback_id": playback_id,
            "artifact_sha256": lease["artifact_sha256"],
            "generation_id": lease["generation_id"],
            "owner_hash": _sha("owner"),
            "observation": "heard_complete",
            "acknowledgement_id": _sha("one-ack"),
        }
        self.assertTrue(case.v8.dispatch("owner_hearing_ack", ack)["success"])
        self.assertFalse(case.v8.dispatch("playback", payload)["success"])
        self.assertFalse(case.v8.dispatch("owner_hearing_ack", ack)["success"])

    def test_owner_ack_rejects_wrong_owner_and_stale_observation(self):
        case, lease, playback_id = self._case()
        self.assertTrue(case.v8.dispatch("playback", {
            "handle_id": lease["handle_id"],
            "artifact_sha256": lease["artifact_sha256"],
            "generation_id": lease["generation_id"],
            "playback_id": playback_id,
        })["success"])
        base = {
            "playback_id": playback_id,
            "artifact_sha256": lease["artifact_sha256"],
            "generation_id": lease["generation_id"],
            "observation": "heard_complete",
        }
        wrong = case.v8.dispatch("owner_hearing_ack", {
            **base,
            "owner_hash": _sha("not-the-loaded-owner"),
            "acknowledgement_id": _sha("wrong-owner-ack"),
        })
        self.assertFalse(wrong["success"])
        case.clock.advance(31.0)
        stale = case.v8.dispatch("owner_hearing_ack", {
            **base,
            "owner_hash": _sha("owner"),
            "acknowledgement_id": _sha("stale-owner-ack"),
        })
        self.assertFalse(stale["success"])

    def test_qwen_after_playback_race_is_rejected(self):
        case, lease, playback_id = self._case()
        case.backend.qwen_race_phase = "v8_playback_after"
        result = case.v8.dispatch("playback", {
            "handle_id": lease["handle_id"],
            "artifact_sha256": lease["artifact_sha256"],
            "generation_id": lease["generation_id"],
            "playback_id": playback_id,
        })
        self.assertFalse(result["success"])
        self.assertFalse(result["owner_hearing_proven"])


class V8ComponentTransferTruthTests(unittest.TestCase):
    def _engine(self):
        clock = ManualClock(2000.0)
        lease = _sha(f"v8-replacing-lease-{id(clock)}")
        backend = ReplacingTensorV8Backend(
            now=clock, worker_pid=43333, lease_id=lease
        )
        engine = V8LiveStateEngine(
            backend=backend,
            serialization_lease_id=lease,
            worker_instance_id=_sha(f"v8-replacing-worker-{id(clock)}"),
            worker_pid=43333,
            now=clock,
            v8_config=load_canonical_config(),
        )
        self.addCleanup(backend.close)
        return clock, backend, engine

    def test_torch_like_tensor_replacement_is_ledgered_without_byte_drift(self):
        _clock, _backend, engine = self._engine()
        loaded = engine.load_voice({"owner_hash": _sha("transfer-owner")})
        self.assertTrue(loaded["success"])
        generation = loaded["model_generation"]
        fingerprint = loaded["component_fingerprint"]
        parked = engine.park_cpu({"reason": "static replacement test"})
        self.assertTrue(parked["success"])
        self.assertEqual(parked["component_fingerprint"], fingerprint)
        self.assertEqual(parked["model_generation"], generation)
        self.assertGreater(
            parked["component_transfer"]["replaced_tensor_object_count"], 0
        )
        resumed = engine.resume_cuda({"reason": "static replacement test"})
        self.assertTrue(resumed["success"])
        self.assertEqual(resumed["component_fingerprint"], fingerprint)
        self.assertEqual(resumed["model_generation"], generation)
        self.assertEqual(len(engine.component_transfer_ledger), 2)
        self.assertTrue(engine.cleanup({"reason": "static end"})["unloaded"])

    def test_tensor_identity_change_outside_transfer_is_rejected(self):
        _clock, _backend, engine = self._engine()
        self.assertTrue(engine.load_voice({"owner_hash": _sha("identity-owner")})["success"])
        module = engine.model.t3
        module.buffer = type(module.buffer)("cuda", module.buffer.payload)
        with self.assertRaisesRegex(V8ContractError, "outside an owned device transfer"):
            engine._model_snapshot("cuda")

    def test_content_mutation_inside_transfer_fails_closed(self):
        _clock, backend, engine = self._engine()
        self.assertTrue(engine.load_voice({"owner_hash": _sha("drift-owner")})["success"])
        backend.model.t3.corrupt_on_next_transfer = True
        result = engine.park_cpu({"reason": "hostile content drift"})
        self.assertFalse(result["success"])
        self.assertIn("complete component bytes", result["error"])

    def test_synthesis_after_snapshot_detects_component_mutation_and_removes_wav(self):
        _clock, backend, engine = self._engine()
        loaded = engine.load_voice({"owner_hash": _sha("synth-owner")})
        original = backend.synthesize_cuda

        def mutating_synthesis(**values):
            result = original(**values)
            backend.model.s3gen.parameter.payload += b"-post-generation-mutation"
            return result

        backend.synthesize_cuda = mutating_synthesis
        text = "Static post-generation component mutation probe."
        result = engine.synthesize({
            "text": text,
            "text_sha256": _sha(text),
            "input_channel": "public_spoken_only",
            "profile_sha256": EXACT_PROFILE_SHA256,
            "reference_sha256": EXACT_REFERENCE_SHA256,
            "condition_digest": loaded["condition_digest"],
        })
        self.assertFalse(result["success"])
        self.assertTrue(result["cleanup"]["artifact_cleanup_records"][0]["deleted"])

    def test_mutated_retained_wav_is_preserved_and_creates_cleanup_debt(self):
        _clock, _backend, engine = self._engine()
        loaded = engine.load_voice({"owner_hash": _sha("wav-owner")})
        text = "Static retained WAV mutation cleanup probe."
        made = engine.synthesize({
            "text": text,
            "text_sha256": _sha(text),
            "input_channel": "public_spoken_only",
            "profile_sha256": EXACT_PROFILE_SHA256,
            "reference_sha256": EXACT_REFERENCE_SHA256,
            "condition_digest": loaded["condition_digest"],
        })
        self.assertTrue(made["success"])
        path = Path(made["artifact_lease"]["resolved_path"])
        with path.open("ab") as handle:
            handle.write(b"hostile-mutation")
        cleanup = engine.cleanup({"reason": "mutated retained evidence"})
        self.assertFalse(cleanup["unloaded"])
        self.assertTrue(cleanup["cleanup_debt"])
        self.assertTrue(path.exists())


class V8ProcessBoundaryTests(unittest.TestCase):
    def test_static_worker_runs_in_job_and_never_claims_live(self):
        nonce = _sha("v8-process-static")
        coordinator = BlackwellV8Coordinator.static_fixture_candidate(nonce=nonce)
        try:
            started = coordinator.start()
            self.assertTrue(started["job_or_process_group_owned"])
            self.assertTrue(started["job_assignment_proof"]["assigned_before_resume"])
            self.assertTrue(started["job_assignment_proof"]["kill_on_close"])
            echo = coordinator._invoke("fixture_echo", {"static": True})
            self.assertEqual(echo["value"], {"static": True})
        finally:
            coordinator.close()

    def test_pre_ready_descendant_is_job_contained(self):
        nonce = _sha("v8-process-descendant")
        coordinator = BlackwellV8Coordinator.static_fixture_candidate(
            nonce=nonce, startup_descendant=True
        )
        try:
            started = coordinator.start()
            self.assertIsInstance(started["startup_descendant_pid"], int)
            self.assertTrue(started["job_assignment_proof"]["assigned_before_resume"])
        finally:
            result = coordinator.process.terminate_tree("v8_static_descendant_test")
            self.assertTrue(result["root_exited"])

    def test_blocked_maximum_request_writer_is_bounded_and_killed(self):
        nonce = _sha("v8-process-blocked-writer")
        coordinator = BlackwellV8Coordinator.static_fixture_candidate(nonce=nonce)
        try:
            coordinator.start()
            coordinator._invoke("fixture_stop_reading", {})
            payload = {"blob": "x" * 249_000}
            started = time.monotonic()
            with self.assertRaises(V7ProcessTimeout):
                coordinator.process.invoke("fixture_echo", payload, 0.25)
            self.assertLess(time.monotonic() - started, 4.0)
            self.assertTrue(coordinator.process.last_termination["root_exited"])
            self.assertTrue(coordinator.process.last_termination["writer_exited"])
        finally:
            coordinator.process.terminate_tree("v8_blocked_writer_finally")

    def test_static_ipc_synthesis_playback_is_synthetic_and_unheard(self):
        nonce = _sha("v8-process-playback")
        coordinator = BlackwellV8Coordinator.static_fixture_candidate(nonce=nonce)
        try:
            coordinator.start()
            loaded = coordinator.load(owner="static-owner")["value"]
            text = "Synthetic static v8 IPC bytes, never sent to a speaker."
            made = coordinator.synthesize({
                "text": text,
                "text_sha256": _sha(text),
                "input_channel": "public_spoken_only",
                "profile_sha256": EXACT_PROFILE_SHA256,
                "reference_sha256": EXACT_REFERENCE_SHA256,
                "condition_digest": loaded["condition_digest"],
            })["value"]
            played = coordinator.playback(
                made["artifact_lease"], playback_id=_sha("static-ipc-playback")
            )["value"]
            self.assertTrue(played["success"])
            self.assertFalse(played["playback"]["owner_hearing_proven"])
            self.assertNotIn("winsound", sys.modules)
        finally:
            coordinator.close()

    def test_hung_synthetic_playback_operation_kills_owned_worker_tree(self):
        nonce = _sha("v8-process-hung-playback")
        coordinator = BlackwellV8Coordinator.static_fixture_candidate(nonce=nonce)
        output_dir: Path | None = None
        try:
            coordinator.start()
            loaded = coordinator.load(owner="static-owner")["value"]
            text = "Synthetic v8 playback timeout bytes, never played."
            made = coordinator.synthesize({
                "text": text,
                "text_sha256": _sha(text),
                "input_channel": "public_spoken_only",
                "profile_sha256": EXACT_PROFILE_SHA256,
                "reference_sha256": EXACT_REFERENCE_SHA256,
                "condition_digest": loaded["condition_digest"],
            })["value"]
            lease = made["artifact_lease"]
            output_dir = Path(lease["resolved_path"]).parent
            coordinator._invoke("fixture_set_mode", {
                "target": "playback", "name": "mode", "value": "hang"
            })
            payload = {
                "handle_id": lease["handle_id"],
                "artifact_sha256": lease["artifact_sha256"],
                "generation_id": lease["generation_id"],
                "playback_id": _sha("hung-static-playback"),
            }
            with self.assertRaises(V7ProcessTimeout):
                coordinator.process.invoke("playback", payload, 0.25)
            self.assertTrue(coordinator.process.last_termination["root_exited"])
        finally:
            coordinator.process.terminate_tree("v8_hung_playback_finally")
            if output_dir is not None:
                shutil.rmtree(output_dir, ignore_errors=True)


class V8StaticSourceTests(unittest.TestCase):
    def test_all_v8_python_parses_and_has_no_top_level_live_calls(self):
        paths = list(V8_PACKAGE.glob("*.py")) + [
            ROOT / "Core/persistent_blackwell_voice_integration_v8.py",
            ROOT / "Testing/blackwell_v8_static_fixture_backend.py",
            ROOT / "Testing/test_blackwell_persistent_voice_candidate_v8_hostile_static.py",
        ]
        for path in paths:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in tree.body:
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                    self.fail(f"top-level call in {path}: {ast.dump(node.value)}")

    def test_worker_live_import_occurs_after_audit_and_capability_checks(self):
        source = (V8_PACKAGE / "worker_entry.py").read_text(encoding="utf-8")
        audit = source.index("verify_fresh_audit_authorization(")
        live_import = source.index("from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v8.live_adapter")
        self.assertLess(audit, live_import)
        self.assertIn("verify_per_run_live_capability(config)", source[:live_import])


if __name__ == "__main__":
    unittest.main()
