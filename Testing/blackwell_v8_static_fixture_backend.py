"""Standard-library-only v8 playback fixture; it never opens an audio device."""

from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any

from Core.blackwell_v7_process_boundary import process_identity_digest
from Testing.blackwell_v7_static_fixture_backend import (
    ManualClock,
    StaticConditions,
    StaticModel,
    StaticTensor,
    StaticV7Backend,
)
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v7 import (
    persistent_worker as v7,
)
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v8.candidate_contract import (
    PROJECT_ROOT,
    sha256_file,
)


class StaticPlaybackRunnerV8:
    def __init__(self, *, config: dict[str, Any], now=time.monotonic) -> None:
        self.config = config
        self.now = now
        self.mode = "valid"
        self.call_count = 0

    def play_exact(self, **values: Any) -> dict[str, Any]:
        self.call_count += 1
        if self.mode == "raise":
            raise RuntimeError("deliberate static playback failure")
        if self.mode == "hang":
            time.sleep(3600)
        started = float(self.now())
        ended = float(self.now())
        executable = PROJECT_ROOT / self.config["voice_live_component"]["python"]
        identity = {
            "pid": 70000 + self.call_count,
            "os_creation_token": 90000 + self.call_count,
            "executable_path": str(executable.resolve()),
            "executable_sha256": sha256_file(executable),
            "executable_size": executable.stat().st_size,
            "executable_volume_serial": 1,
            "executable_file_index": 2 + self.call_count,
        }
        result = {
            "schema_version": 1,
            "playback_id": values["playback_id"],
            "artifact_sha256": values["artifact_sha256"],
            "generation_id": values["generation_id"],
            "model_generation": values["model_generation"],
            "component_fingerprint": values["component_fingerprint"],
            "route": "blackwell_gpu",
            "device": "cuda",
            "generic_voice_used": False,
            "sapi_voice_used": False,
            "fallback_used": False,
            "playback_api_start_monotonic": started,
            "playback_api_end_monotonic": ended,
            "playback_api_completed": True,
            "owner_hearing_observation": None,
            "owner_hearing_proven": False,
            "wav_byte_length": len(values["retained_bytes"]),
            "playback_source": "verified_in_memory_wav_bytes",
            "played_memory_sha256": values["artifact_sha256"],
            "playback_process_identity": identity,
            "playback_process_identity_digest": process_identity_digest(identity),
            "playback_process_in_inherited_job": True,
            "parent_playback_start_monotonic": started,
            "parent_playback_end_monotonic": ended,
            "owned_copy_deleted_after_return": True,
            "playback_worker_sha256": self.config["playback"]["worker_sha256"],
            "playback_command_digest": hashlib.sha256(b"static-v8-playback-command").hexdigest(),
            "playback_capability_hash": hashlib.sha256(b"static-v8-playback-capability").hexdigest(),
        }
        if self.mode == "generic":
            result["generic_voice_used"] = True
        elif self.mode == "sapi":
            result["sapi_voice_used"] = True
        elif self.mode == "cpu":
            result["device"] = "cpu"
        elif self.mode == "owner_claim":
            result["owner_hearing_observation"] = "heard_complete"
            result["owner_hearing_proven"] = True
        elif self.mode == "not_in_job":
            result["playback_process_in_inherited_job"] = False
        elif self.mode == "wrong_wav":
            result["artifact_sha256"] = "0" * 64
        elif self.mode == "wrong_component":
            result["component_fingerprint"] = "0" * 64
        elif self.mode == "wrong_memory":
            result["played_memory_sha256"] = "0" * 64
        elif self.mode == "bad_process_identity":
            result["playback_process_identity"]["os_creation_token"] = 0
        elif self.mode == "future":
            result["playback_api_end_monotonic"] = ended + 10.0
        return result


class ReplacingStaticModule:
    """Mimic PyTorch: device conversion may replace registered tensors."""

    def __init__(self, name: str, device: str = "cuda") -> None:
        self.name = name
        self.parameter = StaticTensor(device, f"{name}-parameter".encode("utf-8"))
        self.buffer = StaticTensor(device, f"{name}-buffer".encode("utf-8"))
        self.corrupt_on_next_transfer = False

    def named_parameters(self):
        return [("weight", self.parameter)]

    def named_buffers(self):
        return [("running_state", self.buffer)]

    def parameters(self):
        return [self.parameter]

    def buffers(self):
        return [self.buffer]

    def to(self, device: str):
        parameter_payload = self.parameter.payload
        buffer_payload = self.buffer.payload
        if self.corrupt_on_next_transfer:
            buffer_payload += b"-corrupted"
            self.corrupt_on_next_transfer = False
        self.parameter = StaticTensor(device, parameter_payload)
        self.buffer = StaticTensor(device, buffer_payload)
        return self


class ReplacingStaticModel:
    def __init__(self, device: str = "cuda") -> None:
        self.t3 = ReplacingStaticModule("t3", device)
        self.s3gen = ReplacingStaticModule("s3gen", device)
        self.ve = ReplacingStaticModule("ve", device)
        self.conds = StaticConditions(device)
        self.device = device


class ReplacingTensorV8Backend(StaticV7Backend):
    def __init__(self, *, now, worker_pid: int, lease_id: str) -> None:
        super().__init__(now=now, worker_pid=worker_pid, lease_id=lease_id)
        self.model = ReplacingStaticModel()

    def load_voice(self, **kwargs):
        self.last_load_kwargs = dict(kwargs)
        self.model = ReplacingStaticModel()
        return {
            "model": self.model,
            "identity": v7.verify_identity_files(),
            "load_proof": {
                "from_pretrained_call_count": 1,
                "prepare_conditionals_call_count": 1,
                "approved_audio_prompt_path": kwargs["approved_audio_prompt_path"],
                "approved_audio_prompt_sha256": kwargs["approved_audio_prompt_sha256"],
                "serialization_lease_id": kwargs["serialization_lease_id"],
                "worker_pid": self.worker_pid,
            },
        }


__all__ = [
    "ManualClock",
    "ReplacingStaticModel",
    "ReplacingTensorV8Backend",
    "StaticModel",
    "StaticPlaybackRunnerV8",
    "StaticV7Backend",
]
