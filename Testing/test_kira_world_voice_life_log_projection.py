from __future__ import annotations

import json
import unittest

from tools import kira_world_shell_server as shell


class KiraWorldVoiceLifeLogProjectionTests(unittest.TestCase):
    def test_route_and_resource_proof_survives_without_private_diagnostics(self) -> None:
        raw = {
            "spoken": True,
            "generated": True,
            "reason": "ok",
            "text": "One approved public sentence.",
            "audio_path": "Voice/generated/kira/example.wav",
            "generation_elapsed_seconds": 4.25,
            "continuation_gap_seconds": 0.0,
            "route_id": "sealed_cpu",
            "approved_voice_path_used": "sealed_cpu",
            "device": "cpu",
            "approved_voice_attempts": [
                {
                    "route_id": "blackwell_gpu",
                    "role": "preferred",
                    "status": "synthesis_failed",
                    "reason": "gpu_synthesis_or_contract_failed",
                    "traceback": "PRIVATE NESTED TRACEBACK",
                },
                {
                    "route_id": "sealed_cpu",
                    "role": "automatic_fallback_only",
                    "status": "used",
                    "reason": "ok",
                },
            ],
            "approved_voice_routing": {
                "preferred_failure_reason": "gpu_synthesis_or_contract_failed",
                "raw_worker_payload": "PRIVATE ROUTE PAYLOAD",
            },
            "gpu_proof": {
                "actual_gpu_allocation": True,
                "peak_allocated_bytes": 2_000_000_000,
                "peak_reserved_bytes": 2_500_000_000,
                "raw_samples": "PRIVATE GPU SAMPLES",
            },
            "resources": {
                "peak_process_rss_mib": 1234.5,
                "peak_system_ram_used_mib": 8192.0,
                "baseline_gpu_vram_used_mib": 900.0,
                "peak_gpu_vram_used_mib": 3100.0,
                "peak_sidecar_gpu_delta_mib": 2200.0,
                "private_process_inventory": "PRIVATE PROCESS DATA",
            },
            "process_seconds": 4.1,
            "gpu_utilization_observed": True,
            "error": "PRIVATE TOP LEVEL ERROR",
            "traceback": "PRIVATE TOP LEVEL TRACEBACK",
            "captured_warnings": ["PRIVATE WARNING"],
        }

        projected = shell._voice_chunk_life_log_result(raw)

        self.assertEqual(projected["route_id"], "sealed_cpu")
        self.assertEqual(projected["approved_voice_path_used"], "sealed_cpu")
        self.assertEqual(projected["device"], "cpu")
        self.assertTrue(projected["gpu_synthesis_attempted"])
        self.assertTrue(projected["cpu_synthesis_attempted"])
        self.assertTrue(projected["automatic_cpu_fallback_used"])
        self.assertTrue(projected["gpu_actual_allocation"])
        self.assertTrue(projected["gpu_utilization_observed"])
        self.assertEqual(projected["peak_allocated_bytes"], 2_000_000_000)
        self.assertEqual(projected["peak_process_rss_mib"], 1234.5)
        self.assertEqual(projected["peak_sidecar_gpu_delta_mib"], 2200.0)
        self.assertEqual(projected["sidecar_process_seconds"], 4.1)
        self.assertEqual(
            projected["approved_voice_attempts"][0],
            {
                "route_id": "blackwell_gpu",
                "role": "preferred",
                "status": "synthesis_failed",
                "reason": "gpu_synthesis_or_contract_failed",
            },
        )
        serialized = json.dumps(projected).casefold()
        for forbidden in (
            "private nested traceback",
            "private route payload",
            "private gpu samples",
            "private process data",
            "private top level error",
            "private top level traceback",
            "private warning",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_projection_is_idempotent_for_streaming_chunk_evidence(self) -> None:
        first = shell._voice_chunk_life_log_result(
            {
                "played": True,
                "generated": True,
                "playback_reason": "ok",
                "route_id": "blackwell_gpu",
                "approved_voice_path_used": "blackwell_gpu",
                "device": "cuda",
                "approved_voice_attempts": [
                    {
                        "route_id": "blackwell_gpu",
                        "role": "preferred",
                        "status": "used",
                        "reason": "ok",
                    }
                ],
                "gpu_synthesis_attempted": True,
                "cpu_synthesis_attempted": False,
                "automatic_cpu_fallback_used": False,
                "gpu_actual_allocation": True,
                "peak_gpu_vram_used_mib": 3321.5,
                "peak_sidecar_gpu_delta_mib": 2410.0,
            }
        )
        second = shell._voice_chunk_life_log_result(first)

        self.assertEqual(second["approved_voice_path_used"], "blackwell_gpu")
        self.assertEqual(second["device"], "cuda")
        self.assertTrue(second["gpu_synthesis_attempted"])
        self.assertFalse(second["cpu_synthesis_attempted"])
        self.assertFalse(second["automatic_cpu_fallback_used"])
        self.assertTrue(second["gpu_actual_allocation"])
        self.assertEqual(second["peak_gpu_vram_used_mib"], 3321.5)
        self.assertEqual(second["peak_sidecar_gpu_delta_mib"], 2410.0)


if __name__ == "__main__":
    unittest.main()
