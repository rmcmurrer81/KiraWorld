#!/usr/bin/env python3
"""Inactive Blackwell v5 CPU-park/CUDA-restore static candidate.

The module deliberately imports no Torch or Chatterbox at import time.  Every
potentially blocking adapter operation must cross a separately supplied
killable-child boundary.  This file is static candidate code, not production
routing or authorization for a live model/audio run.
"""

from __future__ import annotations

import gc
import hashlib
import io
import json
import math
import struct
import threading
import time
import wave
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping

from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v3.persistent_worker import (
    condition_content_digest,
    device_evidence,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = Path(__file__).with_name("candidate_config.json")
CANONICAL_CONFIG_SHA256 = "c668472f132c9200d7e4056246f9341889e317b007f8f0c75cb84602b473c091"
EXACT_QWEN_MODEL = "qwen3.5:9b"
EXACT_QWEN_DIGEST = "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
EXACT_PROFILE_PATH = "Voice/profiles/temp_ai/kira_voice_profile.json"
EXACT_PROFILE_SHA256 = "102d17f5420a1a16b3a920204ebde0d532c0a9bfd2979dca28048378ecddc116"
EXACT_REFERENCE_PATH = (
    "Voice/reference_packs/kira/kira_online_source_20260706_221447/"
    "model_input/approved_reference.wav"
)
EXACT_REFERENCE_SHA256 = "2039a2abd600a63c294d69c2b2e4d450c64c850dc6d1c9a4fbfa1700ba92069c"
EXACT_CUDA_DEVICE_NAME = "NVIDIA GeForce RTX 5060 Ti"
EXACT_COMPUTE_CAPABILITY = [12, 0]


class VoiceState(str, Enum):
    UNLOADED = "UNLOADED"
    PARKED_CPU = "PARKED_CPU"
    LOADED_CUDA = "LOADED_CUDA"
    CLEANUP_DEBT = "CLEANUP_DEBT"


class V5ContractError(RuntimeError):
    pass


class V5BoundaryTimeout(V5ContractError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        char in "0123456789abcdef" for char in value
    )


def _validate_canonical_config(config: Any) -> dict[str, Any]:
    if not isinstance(config, dict):
        raise V5ContractError("canonical v5 config is not an object")
    exact = {
        "schema_version": 2,
        "candidate_id": "kira_chatterbox_blackwell_cpu_park_candidate_v5",
        "production_routing_authorized": False,
        "live_execution_authorized": False,
        "playback_authorized": False,
        "approved_profile": EXACT_PROFILE_PATH,
        "approved_profile_sha256": EXACT_PROFILE_SHA256,
        "approved_reference": EXACT_REFERENCE_PATH,
        "approved_reference_sha256": EXACT_REFERENCE_SHA256,
        "approved_audio_prompt": EXACT_REFERENCE_PATH,
        "approved_audio_prompt_sha256": EXACT_REFERENCE_SHA256,
        "owned_output_root": "RecoverySprint/runtime_cache/blackwell_chatterbox/v5_outputs",
        "qwen_model": EXACT_QWEN_MODEL,
        "qwen_digest": EXACT_QWEN_DIGEST,
        "input_channel": "public_spoken_only",
        "compute_device": "cuda",
        "cuda_device_name": EXACT_CUDA_DEVICE_NAME,
        "compute_capability": EXACT_COMPUTE_CAPABILITY,
        "cpu_synthesis_allowed": False,
        "generic_voice_allowed": False,
        "sapi_allowed": False,
        "substitute_reference_allowed": False,
        "automatic_fallback_inside_candidate": None,
        "production_fallback_retained_outside_candidate": "sealed_cpu_chatterbox_only",
    }
    for key, expected in exact.items():
        if config.get(key) != expected:
            raise V5ContractError(f"canonical immutable config mismatch: {key}")
    if config.get("allowed_states") != [item.value for item in VoiceState]:
        raise V5ContractError("canonical state set mismatch")
    if config.get("required_components") != ["t3", "s3gen", "ve"]:
        raise V5ContractError("canonical component set mismatch")
    expected_request = sorted(
        [
            "condition_digest",
            "input_channel",
            "profile_sha256",
            "reference_sha256",
            "text",
            "text_sha256",
        ]
    )
    if config.get("closed_synthesis_request_keys") != expected_request:
        raise V5ContractError("closed synthesis request schema mismatch")
    required_groups = {
        "resource_bounds",
        "adapter_operation_bounds_seconds",
        "operation_bounds_seconds",
        "qwen_load_only",
        "wav_bounds",
        "sealed_v2_baseline",
        "sealed_v3_rejected_baseline",
        "sealed_v4_rejected_baseline",
    }
    if not required_groups.issubset(config):
        raise V5ContractError("complete frozen policy groups are absent")
    for group in ("adapter_operation_bounds_seconds", "operation_bounds_seconds"):
        for key, value in config[group].items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise V5ContractError(f"{group}.{key} is not numeric")
            if not math.isfinite(float(value)) or float(value) <= 0:
                raise V5ContractError(f"{group}.{key} is not a positive finite bound")
    for group in ("sealed_v2_baseline", "sealed_v3_rejected_baseline", "sealed_v4_rejected_baseline"):
        for path, digest in config[group].items():
            if not isinstance(path, str) or not _is_sha256(digest):
                raise V5ContractError(f"invalid preserved baseline entry: {group}")
    return config


def load_canonical_config() -> dict[str, Any]:
    if sha256_file(CONFIG_PATH) != CANONICAL_CONFIG_SHA256:
        raise V5ContractError("canonical v5 config file hash drift")
    return _validate_canonical_config(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))


def verify_preserved_baselines(config: Mapping[str, Any]) -> dict[str, str]:
    observed: dict[str, str] = {}
    for group in ("sealed_v2_baseline", "sealed_v3_rejected_baseline", "sealed_v4_rejected_baseline"):
        for relative, expected in config[group].items():
            actual = sha256_file(PROJECT_ROOT / relative)
            observed[relative] = actual
            if actual != expected:
                raise V5ContractError(f"preserved baseline drift: {relative}")
    return observed


def verify_identity_files() -> dict[str, str]:
    observed = {
        "profile_path": EXACT_PROFILE_PATH,
        "profile_sha256": sha256_file(PROJECT_ROOT / EXACT_PROFILE_PATH),
        "reference_path": EXACT_REFERENCE_PATH,
        "reference_sha256": sha256_file(PROJECT_ROOT / EXACT_REFERENCE_PATH),
        "audio_prompt_path": EXACT_REFERENCE_PATH,
        "audio_prompt_sha256": sha256_file(PROJECT_ROOT / EXACT_REFERENCE_PATH),
    }
    expected = {
        "profile_path": EXACT_PROFILE_PATH,
        "profile_sha256": EXACT_PROFILE_SHA256,
        "reference_path": EXACT_REFERENCE_PATH,
        "reference_sha256": EXACT_REFERENCE_SHA256,
        "audio_prompt_path": EXACT_REFERENCE_PATH,
        "audio_prompt_sha256": EXACT_REFERENCE_SHA256,
    }
    if observed != expected:
        raise V5ContractError("approved profile/reference/audio-prompt identity drift")
    return observed


def _all_on(model: Any, components: Iterable[str], expected: str) -> tuple[bool, dict[str, Any]]:
    evidence = device_evidence(model, components)
    valid = (
        evidence.get("model_device") == expected
        and evidence.get("condition_devices") == [expected]
        and bool(evidence.get("components"))
        and all(
            item.get("tensor_count", 0) > 0 and item.get("devices") == [expected]
            for item in evidence["components"].values()
        )
    )
    return valid, evidence


def _move_exact_model(model: Any, components: Iterable[str], device: str) -> None:
    for name in components:
        component = getattr(model, name, None)
        mover = getattr(component, "to", None)
        if component is None or not callable(mover):
            raise V5ContractError(f"required component is not movable: {name}")
        result = mover(device)
        if result is not None and result is not component:
            setattr(model, name, result)
    conditions = getattr(model, "conds", None)
    mover = getattr(conditions, "to", None)
    if conditions is None or not callable(mover):
        raise V5ContractError("conditionals are not movable")
    result = mover(device)
    if result is not None:
        model.conds = result
    model.device = device


def _exact_cache_cleanup(value: Any) -> bool:
    required = {"resampler_cache", "mel_basis", "hann_window"}
    return bool(
        isinstance(value, dict)
        and set(value) == required
        and all(isinstance(value[key], dict) and value[key].get("cleared") is True for key in required)
    )


def _exact_cuda_cleanup(value: Any) -> bool:
    return bool(
        isinstance(value, dict)
        and set(value) == {"synchronize_before", "empty_cache_called", "synchronize_after"}
        and value.get("synchronize_before") is True
        and value.get("empty_cache_called") is True
        and value.get("synchronize_after") is True
    )


def _validate_boundary(boundary: Any) -> None:
    if (
        getattr(boundary, "contract_version", None) != "killable_child_v1"
        or getattr(boundary, "enforces_process_termination", None) is not True
        or not callable(getattr(boundary, "invoke", None))
    ):
        raise V5ContractError("a killable-child v1 adapter boundary is mandatory")


def _bounded_call(boundary: Any, operation: str, timeout: float, callback: Callable[[], Any]) -> Any:
    _validate_boundary(boundary)
    envelope = boundary.invoke(operation=operation, timeout_seconds=timeout, callback=callback)
    expected_keys = {
        "operation",
        "completed",
        "timed_out",
        "child_terminated",
        "elapsed_seconds",
        "value",
        "error_type",
        "error",
    }
    if not isinstance(envelope, dict) or set(envelope) != expected_keys:
        raise V5ContractError(f"{operation}: watchdog returned an open/incomplete envelope")
    if envelope["operation"] != operation:
        raise V5ContractError(f"{operation}: watchdog operation binding mismatch")
    elapsed = envelope["elapsed_seconds"]
    if isinstance(elapsed, bool) or not isinstance(elapsed, (int, float)):
        raise V5ContractError(f"{operation}: watchdog elapsed value is invalid")
    elapsed = float(elapsed)
    if not math.isfinite(elapsed) or elapsed < 0:
        raise V5ContractError(f"{operation}: watchdog elapsed value is invalid")
    if envelope["timed_out"] is True:
        if envelope["completed"] is not False or envelope["child_terminated"] is not True:
            raise V5ContractError(f"{operation}: timeout lacks forced child termination proof")
        raise V5BoundaryTimeout(f"{operation} timed out and its child was terminated")
    if envelope["completed"] is not True or envelope["child_terminated"] is not False:
        raise V5ContractError(f"{operation}: watchdog completion contract failed")
    if elapsed > timeout:
        raise V5ContractError(f"{operation}: watchdog accepted a late completion")
    if envelope["error_type"] is not None or envelope["error"] is not None:
        raise V5ContractError(
            f"{operation}: adapter failed: {envelope['error_type']}:{envelope['error']}"
        )
    return envelope["value"]


def validate_resource_snapshot(
    raw: Any,
    *,
    label: str,
    now_monotonic: float,
    maximum_age_seconds: float,
) -> dict[str, Any]:
    numeric = (
        "process_rss_mib",
        "system_commit_used_mib",
        "system_commit_limit_mib",
        "available_physical_mib",
        "total_physical_mib",
        "system_commit_fraction",
        "cuda_allocated_bytes",
        "cuda_reserved_bytes",
        "cuda_free_mib",
        "cuda_total_mib",
        "captured_monotonic",
    )
    exact_keys = set(numeric) | {
        "sample_id",
        "sample_sequence",
        "pid",
        "cuda_device_name",
        "compute_capability",
    }
    if not isinstance(raw, dict) or set(raw) != exact_keys:
        raise V5ContractError(f"{label}: resource schema is not exact")
    values = dict(raw)
    for key in numeric:
        value = values[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise V5ContractError(f"{label}: {key} is not numeric")
        value = float(value)
        if not math.isfinite(value) or value < 0:
            raise V5ContractError(f"{label}: {key} is non-finite or negative")
        values[key] = value
    if not _is_sha256(values["sample_id"]):
        raise V5ContractError(f"{label}: sample ID is not a SHA-256 value")
    if isinstance(values["sample_sequence"], bool) or not isinstance(values["sample_sequence"], int):
        raise V5ContractError(f"{label}: sample sequence is invalid")
    if values["sample_sequence"] <= 0:
        raise V5ContractError(f"{label}: sample sequence is invalid")
    if isinstance(values["pid"], bool) or not isinstance(values["pid"], int) or values["pid"] <= 0:
        raise V5ContractError(f"{label}: PID is invalid")
    if values["cuda_device_name"] != EXACT_CUDA_DEVICE_NAME:
        raise V5ContractError(f"{label}: CUDA device identity mismatch")
    if values["compute_capability"] != EXACT_COMPUTE_CAPABILITY:
        raise V5ContractError(f"{label}: compute capability mismatch")
    captured = values["captured_monotonic"]
    if captured > now_monotonic or now_monotonic - captured > maximum_age_seconds:
        raise V5ContractError(f"{label}: stale/future resource evidence")
    if values["total_physical_mib"] <= 0 or values["system_commit_limit_mib"] <= 0:
        raise V5ContractError(f"{label}: total RAM/commit limit must be positive")
    if values["cuda_total_mib"] <= 0:
        raise V5ContractError(f"{label}: total CUDA memory must be positive")
    if values["available_physical_mib"] > values["total_physical_mib"]:
        raise V5ContractError(f"{label}: available RAM exceeds total")
    if values["system_commit_used_mib"] > values["system_commit_limit_mib"]:
        raise V5ContractError(f"{label}: committed memory exceeds limit")
    if values["process_rss_mib"] > values["system_commit_used_mib"]:
        raise V5ContractError(f"{label}: process RSS exceeds commit")
    recomputed = values["system_commit_used_mib"] / values["system_commit_limit_mib"]
    if abs(recomputed - values["system_commit_fraction"]) > 1e-6:
        raise V5ContractError(f"{label}: commit fraction is inconsistent")
    if values["cuda_free_mib"] > values["cuda_total_mib"]:
        raise V5ContractError(f"{label}: CUDA free exceeds total")
    if values["cuda_allocated_bytes"] > values["cuda_reserved_bytes"]:
        raise V5ContractError(f"{label}: CUDA allocation exceeds reservation")
    if values["cuda_reserved_bytes"] > values["cuda_total_mib"] * 1024 * 1024:
        raise V5ContractError(f"{label}: CUDA reservation exceeds total")
    return values


class PersistentVoiceRuntimeV5:
    def __init__(
        self,
        *,
        config: dict[str, Any] | None = None,
        loader: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        qwen_probe: Callable[[str], dict[str, Any]] | None = None,
        resource_probe: Callable[[], dict[str, Any]] | None = None,
        cache_clearer: Callable[[], dict[str, Any]] | None = None,
        cuda_cleanup: Callable[[], dict[str, Any]] | None = None,
        call_boundary: Any = None,
        serialization_lease_id: str = "",
        now: Callable[[], float] | None = None,
        allow_inactive_static_execution: bool = False,
    ) -> None:
        canonical = load_canonical_config()
        if config is not None and config != canonical:
            raise V5ContractError("injected config is not exactly canonical")
        if not _is_sha256(serialization_lease_id):
            raise V5ContractError("exclusive serialization lease must be a SHA-256 value")
        _validate_boundary(call_boundary)
        self._policy = _freeze(canonical)
        self._policy_bytes = _canonical_bytes(canonical)
        self._policy_digest = hashlib.sha256(self._policy_bytes).hexdigest()
        self.serialization_lease_id = serialization_lease_id
        self._loader = loader
        self._qwen_probe = qwen_probe
        self._resource_probe = resource_probe
        self._cache_clearer = cache_clearer
        self._cuda_cleanup = cuda_cleanup
        self._boundary = call_boundary
        self._now = now or time.monotonic
        self._allow_static = bool(allow_inactive_static_execution)
        self.operation_lock = threading.RLock()
        self.state = VoiceState.UNLOADED
        self.model: Any | None = None
        self.backend: dict[str, Any] | None = None
        self.identity: dict[str, str] | None = None
        self.condition_digest: str | None = None
        self.condition_manifest: list[dict[str, Any]] = []
        self.model_object_generation: str | None = None
        self.baseline_resources: dict[str, Any] | None = None
        self.model_load_count = 0
        self.conditioning_count = 0
        self.park_count = 0
        self.resume_count = 0
        self.synthesis_count = 0
        self.proven_unload_count = 0
        self.audit_events: list[dict[str, Any]] = []
        self._event_sequence = 0
        self._resource_sequence = 0
        self._resource_ids: set[str] = set()
        self._qwen_sequence = 0
        self._qwen_ids: set[str] = set()
        self._generation_sequence = 0
        self.last_activity_monotonic = self._now()

    @property
    def config(self) -> dict[str, Any]:
        """Return a detached copy; runtime decisions never read mutable public data."""
        return json.loads(self._policy_bytes.decode("utf-8"))

    @property
    def policy_digest(self) -> str:
        return self._policy_digest

    def _p(self, *keys: str) -> Any:
        value: Any = self._policy
        for key in keys:
            value = value[key]
        return value

    def _require_policy(self) -> None:
        if not self._allow_static:
            raise V5ContractError("inactive v5 requires bounded static harness opt-in")
        if sha256_file(CONFIG_PATH) != CANONICAL_CONFIG_SHA256:
            raise V5ContractError("canonical v5 config file hash drift")
        thawed = _thaw(self._policy)
        _validate_canonical_config(thawed)
        observed = hashlib.sha256(_canonical_bytes(thawed)).hexdigest()
        if observed != self._policy_digest or _canonical_bytes(thawed) != self._policy_bytes:
            raise V5ContractError("immutable internal policy digest drift")

    def _event(self, event: str, **fields: Any) -> None:
        self._event_sequence += 1
        self.audit_events.append(
            {"sequence": self._event_sequence, "event": event, "state": self.state.value, **fields}
        )

    def call_bounded(self, operation: str, callback: Callable[[], Any]) -> Any:
        bounds = self._p("adapter_operation_bounds_seconds")
        if operation not in bounds:
            raise V5ContractError(f"unrecognized bounded adapter operation: {operation}")
        return _bounded_call(self._boundary, operation, float(bounds[operation]), callback)

    def _resources(self, label: str) -> dict[str, Any]:
        if not callable(self._resource_probe):
            raise V5ContractError("resource probe is required")
        raw = self.call_bounded("resource_probe", self._resource_probe)
        value = validate_resource_snapshot(
            raw,
            label=label,
            now_monotonic=float(self._now()),
            maximum_age_seconds=float(self._p("resource_bounds", "maximum_evidence_age_seconds")),
        )
        sequence = value["sample_sequence"]
        sample_id = value["sample_id"]
        if sequence <= self._resource_sequence or sample_id in self._resource_ids:
            raise V5ContractError(f"{label}: replayed/out-of-order resource evidence")
        self._resource_sequence = sequence
        self._resource_ids.add(sample_id)
        return value

    def _qwen_absence(self, phase: str) -> dict[str, Any]:
        if not callable(self._qwen_probe):
            raise V5ContractError("exact Qwen probe is required")
        result = self.call_bounded("qwen_probe", lambda: self._qwen_probe(phase))
        expected = {
            "query_succeeded",
            "target_model",
            "target_digest",
            "records",
            "model_state_changed",
            "serialization_lease_id",
            "lease_exclusive",
            "sample_id",
            "sample_sequence",
            "captured_monotonic",
            "phase",
        }
        if not isinstance(result, dict) or set(result) != expected:
            raise V5ContractError("exact Qwen absence evidence schema mismatch")
        captured = result["captured_monotonic"]
        now = float(self._now())
        if isinstance(captured, bool) or not isinstance(captured, (int, float)):
            raise V5ContractError("Qwen evidence timestamp is invalid")
        if float(captured) > now or now - float(captured) > float(
            self._p("resource_bounds", "maximum_evidence_age_seconds")
        ):
            raise V5ContractError("Qwen absence evidence is stale/future")
        sequence = result["sample_sequence"]
        sample_id = result["sample_id"]
        if (
            result["query_succeeded"] is not True
            or result["target_model"] != EXACT_QWEN_MODEL
            or result["target_digest"] != EXACT_QWEN_DIGEST
            or result["records"] != []
            or result["model_state_changed"] is not False
            or result["serialization_lease_id"] != self.serialization_lease_id
            or result["lease_exclusive"] is not True
            or result["phase"] != phase
            or not _is_sha256(sample_id)
            or isinstance(sequence, bool)
            or not isinstance(sequence, int)
            or sequence <= self._qwen_sequence
            or sample_id in self._qwen_ids
        ):
            raise V5ContractError("fresh lease-bound exact Qwen absence was not proven")
        self._qwen_sequence = sequence
        self._qwen_ids.add(sample_id)
        return dict(result)

    def _check_elapsed(self, started: float, operation: str) -> float:
        elapsed = float(self._now()) - float(started)
        bound = float(self._p("operation_bounds_seconds", operation))
        if not math.isfinite(elapsed) or elapsed < 0 or elapsed > bound:
            raise V5ContractError(f"{operation} exceeded aggregate deadline")
        return elapsed

    def _host_gate(self, resources: Mapping[str, Any], minimum_available: float, label: str) -> None:
        if resources["available_physical_mib"] < minimum_available:
            raise V5ContractError(f"{label}: insufficient available physical RAM")
        if resources["system_commit_fraction"] > float(
            self._p("resource_bounds", "maximum_system_commit_fraction")
        ):
            raise V5ContractError(f"{label}: system commit pressure exceeds bound")

    def lifecycle(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "model_object_generation": self.model_object_generation,
            "condition_digest": self.condition_digest,
            "model_load_count": self.model_load_count,
            "conditioning_count": self.conditioning_count,
            "park_count": self.park_count,
            "resume_count": self.resume_count,
            "synthesis_count": self.synthesis_count,
            "proven_unload_count": self.proven_unload_count,
            "policy_digest": self._policy_digest,
            "serialization_lease_id": self.serialization_lease_id,
        }

    def load_initial(self, owner: str) -> dict[str, Any]:
        with self.operation_lock:
            started = self._now()
            try:
                self._require_policy()
                if self.state is not VoiceState.UNLOADED:
                    return {"loaded": False, "reason": "initial_load_requires_unloaded"}
                if not isinstance(owner, str) or not owner.strip():
                    raise V5ContractError("nonempty owner is required")
                verify_preserved_baselines(self._policy)
                identity = verify_identity_files()
                qwen_before = self._qwen_absence("initial_cuda_transition_before")
                baseline = self._resources("load_before")
                self._host_gate(
                    baseline,
                    float(self._p("resource_bounds", "minimum_available_physical_mib_before_park")),
                    "load_before",
                )
                self.baseline_resources = baseline
                if not callable(self._loader):
                    raise V5ContractError("bounded loader is unavailable")
                payload = self.call_bounded("loader", lambda: self._loader(self.config))
                if not isinstance(payload, dict) or set(payload) != {"model", "backend", "identity", "load_proof"}:
                    raise V5ContractError("loader response schema is not exact")
                expected_proof = {
                    "from_pretrained_call_count": 1,
                    "prepare_conditionals_call_count": 1,
                    "approved_audio_prompt_path": str((PROJECT_ROOT / EXACT_REFERENCE_PATH).resolve()),
                    "approved_audio_prompt_sha256": EXACT_REFERENCE_SHA256,
                    "serialization_lease_id": self.serialization_lease_id,
                }
                if payload["load_proof"] != expected_proof or payload["identity"] != identity:
                    raise V5ContractError("one exact leased load/conditioning proof is absent")
                self.model = payload["model"]
                self.backend = payload["backend"]
                if self.model is None or not isinstance(self.backend, dict):
                    raise V5ContractError("loader omitted owned model/backend")
                all_cuda, devices = _all_on(self.model, self._p("required_components"), "cuda")
                if not all_cuda:
                    raise V5ContractError(f"loaded model is mixed/non-CUDA: {devices}")
                digest, manifest = condition_content_digest(self.model.conds)
                after = self._resources("load_after")
                self._host_gate(
                    after,
                    float(self._p("resource_bounds", "minimum_available_physical_mib_after_resume")),
                    "load_after",
                )
                if after["cuda_free_mib"] < float(
                    self._p("resource_bounds", "minimum_cuda_free_mib_after_resume")
                ):
                    raise V5ContractError("load_after: insufficient CUDA free headroom")
                qwen_precommit = self._qwen_absence("initial_cuda_transition_precommit")
                self._check_elapsed(started, "load")
                self.identity = identity
                self.condition_digest = digest
                self.condition_manifest = manifest
                self.model_load_count = 1
                self.conditioning_count = 1
                self.model_object_generation = sha256_text(
                    f"{id(self.model)}:{digest}:{EXACT_REFERENCE_SHA256}:{self.serialization_lease_id}"
                )
                self.state = VoiceState.LOADED_CUDA
                qwen_after = self._qwen_absence("initial_cuda_transition_after")
                self.last_activity_monotonic = self._now()
                self._event("v5_initial_load_proven")
                return {
                    "loaded": True,
                    "identity": identity,
                    "device_evidence": devices,
                    "resources_before": baseline,
                    "resources_after": after,
                    "qwen_before": qwen_before,
                    "qwen_precommit": qwen_precommit,
                    "qwen_after": qwen_after,
                    "lifecycle": self.lifecycle(),
                }
            except Exception as exc:
                cleanup = self._full_unload_locked("load_failure")
                return self._failure("load", exc, cleanup)

    def park_cpu(self, reason: str) -> dict[str, Any]:
        with self.operation_lock:
            started = self._now()
            try:
                self._require_policy()
                if self.state is not VoiceState.LOADED_CUDA or self.model is None:
                    return {"parked": False, "reason": "park_requires_loaded_cuda"}
                generation = self.model_object_generation
                digest = self.condition_digest
                if verify_identity_files() != self.identity:
                    raise V5ContractError("identity drift before park")
                before = self._resources("park_before")
                self._host_gate(
                    before,
                    float(self._p("resource_bounds", "minimum_available_physical_mib_before_park")),
                    "park_before",
                )
                self.call_bounded(
                    "tensor_move",
                    lambda: _move_exact_model(self.model, self._p("required_components"), "cpu"),
                )
                if not callable(self._cache_clearer) or not callable(self._cuda_cleanup):
                    raise V5ContractError("independent cache/CUDA callbacks are required")
                cache = self.call_bounded("cache_clear", self._cache_clearer)
                cuda = self.call_bounded("cuda_cleanup", self._cuda_cleanup)
                if not _exact_cache_cleanup(cache) or not _exact_cuda_cleanup(cuda):
                    raise V5ContractError("park cache/CUDA cleanup proof failed")
                all_cpu, devices = _all_on(self.model, self._p("required_components"), "cpu")
                after_digest, after_manifest = condition_content_digest(self.model.conds)
                if not all_cpu or after_digest != digest or after_manifest != self.condition_manifest:
                    raise V5ContractError("CPU park changed model/condition identity")
                if self.model_object_generation != generation:
                    raise V5ContractError("model object generation drift during park")
                after = self._resources("park_after")
                self._host_gate(
                    after,
                    float(self._p("resource_bounds", "minimum_available_physical_mib_after_park")),
                    "park_after",
                )
                baseline = self.baseline_resources
                if baseline is None:
                    raise V5ContractError("park baseline unavailable")
                if after["cuda_allocated_bytes"] > baseline["cuda_allocated_bytes"] + float(
                    self._p("resource_bounds", "maximum_park_cuda_allocated_above_baseline_bytes")
                ):
                    raise V5ContractError("park_after: CUDA allocation did not return")
                if after["cuda_reserved_bytes"] > baseline["cuda_reserved_bytes"] + float(
                    self._p("resource_bounds", "maximum_park_cuda_reserved_above_baseline_bytes")
                ):
                    raise V5ContractError("park_after: CUDA reservation did not return")
                self._check_elapsed(started, "park")
                self.state = VoiceState.PARKED_CPU
                self.park_count += 1
                self._event("v5_cpu_park_proven", reason=reason)
                return {
                    "parked": True,
                    "device_evidence": devices,
                    "resources_before": before,
                    "resources_after": after,
                    "cache_cleanup": cache,
                    "cuda_cleanup": cuda,
                    "lifecycle": self.lifecycle(),
                }
            except Exception as exc:
                cleanup = self._full_unload_locked("park_failure")
                return self._failure("park", exc, cleanup)

    def resume_cuda(self, reason: str) -> dict[str, Any]:
        with self.operation_lock:
            started = self._now()
            try:
                self._require_policy()
                if self.state is not VoiceState.PARKED_CPU or self.model is None:
                    return {"resumed": False, "reason": "resume_requires_parked_cpu"}
                generation = self.model_object_generation
                digest = self.condition_digest
                qwen_before = self._qwen_absence("resume_cuda_transition_before")
                if verify_identity_files() != self.identity:
                    raise V5ContractError("identity drift before resume")
                before = self._resources("resume_before")
                self._host_gate(
                    before,
                    float(self._p("resource_bounds", "minimum_available_physical_mib_after_resume")),
                    "resume_before",
                )
                if before["cuda_free_mib"] < float(
                    self._p("resource_bounds", "minimum_cuda_free_mib_before_resume")
                ):
                    raise V5ContractError("resume_before: insufficient CUDA free headroom")
                self.call_bounded(
                    "tensor_move",
                    lambda: _move_exact_model(self.model, self._p("required_components"), "cuda"),
                )
                if not callable(self._cuda_cleanup):
                    raise V5ContractError("CUDA cleanup callback missing")
                cuda = self.call_bounded("cuda_cleanup", self._cuda_cleanup)
                if not _exact_cuda_cleanup(cuda):
                    raise V5ContractError("resume CUDA synchronization proof failed")
                all_cuda, devices = _all_on(self.model, self._p("required_components"), "cuda")
                after_digest, after_manifest = condition_content_digest(self.model.conds)
                if not all_cuda or after_digest != digest or after_manifest != self.condition_manifest:
                    raise V5ContractError("CUDA resume changed model/condition identity")
                if self.model_object_generation != generation:
                    raise V5ContractError("model object generation drift during resume")
                after = self._resources("resume_after")
                self._host_gate(
                    after,
                    float(self._p("resource_bounds", "minimum_available_physical_mib_after_resume")),
                    "resume_after",
                )
                if after["cuda_free_mib"] < float(
                    self._p("resource_bounds", "minimum_cuda_free_mib_after_resume")
                ):
                    raise V5ContractError("resume_after: insufficient CUDA free headroom")
                qwen_precommit = self._qwen_absence("resume_cuda_transition_precommit")
                self._check_elapsed(started, "resume")
                self.state = VoiceState.LOADED_CUDA
                qwen_after = self._qwen_absence("resume_cuda_transition_after")
                self.resume_count += 1
                self._event("v5_cuda_resume_proven", reason=reason)
                return {
                    "resumed": True,
                    "device_evidence": devices,
                    "resources_before": before,
                    "resources_after": after,
                    "qwen_before": qwen_before,
                    "qwen_precommit": qwen_precommit,
                    "qwen_after": qwen_after,
                    "lifecycle": self.lifecycle(),
                }
            except Exception as exc:
                cleanup = self._full_unload_locked("resume_failure")
                return self._failure("resume", exc, cleanup)

    def _verify_wav(self, artifact: Mapping[str, Any], text_sha: str, generation_id: str) -> dict[str, Any]:
        exact_keys = {
            "artifact_path",
            "artifact_sha256",
            "generation_id",
            "text_sha256",
            "prompt_path",
            "prompt_sha256",
            "route",
            "device",
            "generic_voice_used",
            "sapi_voice_used",
            "fallback_used",
            "generation_started_monotonic",
            "generation_ended_monotonic",
        }
        if not isinstance(artifact, Mapping) or set(artifact) != exact_keys:
            raise V5ContractError("synthesis artifact schema is not exact")
        if (
            artifact["generation_id"] != generation_id
            or artifact["text_sha256"] != text_sha
            or artifact["prompt_path"] != str((PROJECT_ROOT / EXACT_REFERENCE_PATH).resolve())
            or artifact["prompt_sha256"] != EXACT_REFERENCE_SHA256
            or artifact["route"] != "blackwell_gpu"
            or artifact["device"] != "cuda"
            or artifact["generic_voice_used"] is not False
            or artifact["sapi_voice_used"] is not False
            or artifact["fallback_used"] is not False
            or not _is_sha256(artifact["artifact_sha256"])
        ):
            raise V5ContractError("artifact identity/route binding mismatch")
        started = artifact["generation_started_monotonic"]
        ended = artifact["generation_ended_monotonic"]
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in (started, ended)):
            raise V5ContractError("artifact generation interval is invalid")
        now = float(self._now())
        maximum_age = float(self._p("resource_bounds", "maximum_evidence_age_seconds"))
        if not (
            math.isfinite(float(started))
            and math.isfinite(float(ended))
            and 0 <= started <= ended <= now
            and now - float(ended) <= maximum_age
        ):
            raise V5ContractError("artifact generation interval is invalid")
        path_value = artifact["artifact_path"]
        if not isinstance(path_value, str) or not path_value:
            raise V5ContractError("artifact path is absent")
        raw_path = Path(path_value)
        if not raw_path.is_absolute():
            raise V5ContractError("artifact path must be absolute")
        if raw_path.is_symlink():
            raise V5ContractError("artifact path may not be a symbolic link")
        path = raw_path.resolve(strict=True)
        root = (PROJECT_ROOT / str(self._p("owned_output_root"))).resolve()
        try:
            relative = path.relative_to(root)
        except ValueError as exc:
            raise V5ContractError("artifact escaped the owned output root") from exc
        cursor = root
        for part in relative.parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise V5ContractError("artifact path contains a symbolic link")
        if not path.is_file() or path.suffix.lower() != ".wav":
            raise V5ContractError("artifact is not a regular owned WAV")
        maximum_bytes = int(self._p("wav_bounds", "maximum_file_bytes"))
        if path.stat().st_size <= 0 or path.stat().st_size > maximum_bytes:
            raise V5ContractError("artifact WAV byte length is outside the closed bounds")
        with path.open("rb") as handle:
            wav_bytes = handle.read(maximum_bytes + 1)
        if not wav_bytes or len(wav_bytes) > maximum_bytes:
            raise V5ContractError("artifact WAV byte length is outside the closed bounds")
        actual_sha = hashlib.sha256(wav_bytes).hexdigest()
        if actual_sha != artifact["artifact_sha256"]:
            raise V5ContractError("artifact SHA-256 does not match exact file bytes")
        try:
            with wave.open(io.BytesIO(wav_bytes), "rb") as handle:
                channels = handle.getnchannels()
                sample_width = handle.getsampwidth()
                sample_rate = handle.getframerate()
                frames = handle.getnframes()
                compression = handle.getcomptype()
                pcm = handle.readframes(frames)
        except (wave.Error, OSError, EOFError) as exc:
            raise V5ContractError(f"artifact WAV is unreadable: {exc}") from exc
        bounds = self._p("wav_bounds")
        duration = frames / sample_rate if sample_rate else 0.0
        if (
            channels not in bounds["allowed_channels"]
            or sample_width not in bounds["allowed_sample_width_bytes"]
            or not int(bounds["minimum_sample_rate_hz"]) <= sample_rate <= int(bounds["maximum_sample_rate_hz"])
            or compression != "NONE"
            or not float(bounds["minimum_duration_seconds"]) <= duration <= float(bounds["maximum_duration_seconds"])
            or len(pcm) != frames * channels * sample_width
        ):
            raise V5ContractError("artifact WAV structure is outside the closed bounds")
        samples = struct.unpack(f"<{len(pcm) // 2}h", pcm)
        peak = max((abs(value) for value in samples), default=0)
        if peak < int(bounds["minimum_absolute_pcm_peak"]):
            raise V5ContractError("artifact WAV is silent")
        return {
            "resolved_path": str(path),
            "artifact_sha256": actual_sha,
            "channels": channels,
            "sample_width_bytes": sample_width,
            "sample_rate_hz": sample_rate,
            "frame_count": frames,
            "duration_seconds": duration,
            "absolute_pcm_peak": peak,
            "generation_started_monotonic": float(started),
            "generation_ended_monotonic": float(ended),
        }

    def _verify_cuda_generation(
        self,
        evidence: Any,
        *,
        generation_id: str,
        text_sha: str,
        artifact_sha: str,
        wav: Mapping[str, Any],
    ) -> dict[str, Any]:
        keys = {
            "generation_id",
            "text_sha256",
            "artifact_sha256",
            "device",
            "cuda_device_name",
            "compute_capability",
            "allocated_before_bytes",
            "peak_allocated_bytes",
            "allocated_after_bytes",
            "synchronize_before",
            "synchronize_after",
            "unsupported_architecture_warning",
            "no_kernel_image_error",
            "sample_start_monotonic",
            "sample_end_monotonic",
        }
        if not isinstance(evidence, dict) or set(evidence) != keys:
            raise V5ContractError("CUDA generation evidence schema is not exact")
        integers = ("allocated_before_bytes", "peak_allocated_bytes", "allocated_after_bytes")
        if any(
            isinstance(evidence[key], bool) or not isinstance(evidence[key], int) or evidence[key] < 0
            for key in integers
        ):
            raise V5ContractError("CUDA allocation evidence is invalid")
        sample_start = evidence["sample_start_monotonic"]
        sample_end = evidence["sample_end_monotonic"]
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in (sample_start, sample_end)):
            raise V5ContractError("CUDA sample interval is invalid")
        if (
            evidence["generation_id"] != generation_id
            or evidence["text_sha256"] != text_sha
            or evidence["artifact_sha256"] != artifact_sha
            or evidence["device"] != "cuda"
            or evidence["cuda_device_name"] != EXACT_CUDA_DEVICE_NAME
            or evidence["compute_capability"] != EXACT_COMPUTE_CAPABILITY
            or evidence["peak_allocated_bytes"] <= evidence["allocated_before_bytes"]
            or evidence["synchronize_before"] is not True
            or evidence["synchronize_after"] is not True
            or evidence["unsupported_architecture_warning"] is not False
            or evidence["no_kernel_image_error"] is not False
            or not math.isfinite(float(sample_start))
            or not math.isfinite(float(sample_end))
            or float(sample_start) > float(wav["generation_started_monotonic"])
            or float(sample_end) < float(wav["generation_ended_monotonic"])
        ):
            raise V5ContractError("generation-scoped eager-CUDA proof failed")
        return dict(evidence)

    def synthesize(self, request: dict[str, Any]) -> dict[str, Any]:
        with self.operation_lock:
            started = self._now()
            try:
                self._require_policy()
                if self.state is not VoiceState.LOADED_CUDA or self.model is None:
                    return {
                        "generated": False,
                        "reason": "CPU_or_unloaded_synthesis_forbidden",
                        "generic_voice_used": False,
                        "sapi_voice_used": False,
                        "fallback_used": False,
                    }
                if not isinstance(request, dict) or set(request) != set(
                    self._p("closed_synthesis_request_keys")
                ):
                    raise V5ContractError("synthesis request violates closed schema")
                text = request.get("text")
                if not isinstance(text, str) or not text.strip():
                    raise V5ContractError("public SPOKEN text must be nonempty")
                text_sha = sha256_text(text)
                if request != {
                    "text": text,
                    "text_sha256": text_sha,
                    "input_channel": "public_spoken_only",
                    "profile_sha256": EXACT_PROFILE_SHA256,
                    "reference_sha256": EXACT_REFERENCE_SHA256,
                    "condition_digest": self.condition_digest,
                }:
                    raise V5ContractError("synthesis identity/text binding mismatch")
                identity_before = verify_identity_files()
                if identity_before != self.identity:
                    raise V5ContractError("approved files drifted before synthesis")
                self._qwen_absence("synthesis_before")
                all_cuda, devices_before = _all_on(self.model, self._p("required_components"), "cuda")
                digest_before, manifest_before = condition_content_digest(self.model.conds)
                if not all_cuda or digest_before != self.condition_digest or manifest_before != self.condition_manifest:
                    raise V5ContractError("live model identity/device proof failed before synthesis")
                generator = (self.backend or {}).get("synthesize_cuda")
                execution_probe = (self.backend or {}).get("cuda_execution_evidence")
                if not callable(generator) or not callable(execution_probe):
                    raise V5ContractError("bounded synthesis/CUDA evidence adapters are unavailable")
                self._generation_sequence += 1
                generation_id = sha256_text(
                    f"{self.model_object_generation}:{text_sha}:{self._generation_sequence}:{self.serialization_lease_id}"
                )
                artifact = self.call_bounded(
                    "synthesis",
                    lambda: generator(
                        text=text,
                        text_sha256=text_sha,
                        generation_id=generation_id,
                        approved_audio_prompt_path=str((PROJECT_ROOT / EXACT_REFERENCE_PATH).resolve()),
                        approved_audio_prompt_sha256=EXACT_REFERENCE_SHA256,
                        owned_output_root=str((PROJECT_ROOT / str(self._p("owned_output_root"))).resolve()),
                        serialization_lease_id=self.serialization_lease_id,
                    ),
                )
                wav = self._verify_wav(artifact, text_sha, generation_id)
                execution_raw = self.call_bounded(
                    "cuda_execution_evidence",
                    lambda: execution_probe(
                        generation_id=generation_id,
                        text_sha256=text_sha,
                        artifact_sha256=wav["artifact_sha256"],
                    ),
                )
                execution = self._verify_cuda_generation(
                    execution_raw,
                    generation_id=generation_id,
                    text_sha=text_sha,
                    artifact_sha=wav["artifact_sha256"],
                    wav=wav,
                )
                identity_after = verify_identity_files()
                all_cuda_after, devices_after = _all_on(
                    self.model, self._p("required_components"), "cuda"
                )
                digest_after, manifest_after = condition_content_digest(self.model.conds)
                self._qwen_absence("synthesis_after")
                if identity_after != identity_before:
                    raise V5ContractError("approved files changed during synthesis")
                if not all_cuda_after or digest_after != digest_before or manifest_after != manifest_before:
                    raise V5ContractError("model/condition identity changed during synthesis")
                self._check_elapsed(started, "synthesis")
                self.synthesis_count += 1
                self._event("v5_cuda_synthesis_proven", generation_id=generation_id, text_sha256=text_sha)
                return {
                    "generated": True,
                    "device": "cuda",
                    "profile_sha256": EXACT_PROFILE_SHA256,
                    "reference_sha256": EXACT_REFERENCE_SHA256,
                    "condition_digest": self.condition_digest,
                    "text_sha256": text_sha,
                    "generation_id": generation_id,
                    "generic_voice_used": False,
                    "sapi_voice_used": False,
                    "fallback_used": False,
                    "artifact": dict(artifact),
                    "wav_verification": wav,
                    "cuda_execution": execution,
                    "device_evidence_before": devices_before,
                    "device_evidence_after": devices_after,
                    "lifecycle": self.lifecycle(),
                }
            except Exception as exc:
                cleanup = self._full_unload_locked("synthesis_failure")
                return self._failure("synthesis", exc, cleanup)

    def _failure(self, operation: str, exc: Exception, cleanup: dict[str, Any]) -> dict[str, Any]:
        result_key = {"load": "loaded", "park": "parked", "resume": "resumed"}.get(
            operation, "generated"
        )
        return {
            result_key: False,
            "reason": f"v5_{operation}_failed_closed",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "generic_voice_used": False,
            "sapi_voice_used": False,
            "fallback_used": False,
            "cleanup": cleanup,
            "lifecycle": self.lifecycle(),
        }

    def _full_unload_locked(self, reason: str) -> dict[str, Any]:
        started = self._now()
        previous = self.state
        errors: list[str] = []
        before: dict[str, Any] | None = None
        after: dict[str, Any] | None = None
        release_result: Any = None
        try:
            before = self._resources("unload_before")
        except Exception as exc:
            errors.append(f"resource_before:{type(exc).__name__}:{exc}")
        release = (self.backend or {}).get("release_owned")
        release_required = self.model is not None or self.backend is not None
        if release_required:
            if not callable(release):
                errors.append("release_owned:missing")
            else:
                try:
                    release_result = self.call_bounded("release_owned", release)
                    if release_result != {
                        "released": True,
                        "owned_model_count": 0,
                        "owned_condition_count": 0,
                    }:
                        errors.append("release_owned:exact_release_not_proven")
                except Exception as exc:
                    errors.append(f"release_owned:{type(exc).__name__}:{exc}")
        else:
            release_result = {"released": True, "owned_model_count": 0, "owned_condition_count": 0}
        self.model = None
        self.backend = None
        self.identity = None
        self.condition_digest = None
        self.condition_manifest = []
        self.model_object_generation = None
        gc.collect()
        cache_results: list[Any] = []
        cuda_results: list[Any] = []
        for index in range(2):
            try:
                if not callable(self._cache_clearer):
                    raise V5ContractError("independent cache clearer missing")
                cache = self.call_bounded("cache_clear", self._cache_clearer)
                cache_results.append(cache)
                if not _exact_cache_cleanup(cache):
                    raise V5ContractError("cache cleanup not proven")
            except Exception as exc:
                errors.append(f"cache_cleanup_{index + 1}:{type(exc).__name__}:{exc}")
            try:
                if not callable(self._cuda_cleanup):
                    raise V5ContractError("independent CUDA cleanup missing")
                cuda = self.call_bounded("cuda_cleanup", self._cuda_cleanup)
                cuda_results.append(cuda)
                if not _exact_cuda_cleanup(cuda):
                    raise V5ContractError("CUDA cleanup not proven")
            except Exception as exc:
                errors.append(f"cuda_cleanup_{index + 1}:{type(exc).__name__}:{exc}")
            gc.collect()
        try:
            qwen = self._qwen_absence("unload_after")
        except Exception as exc:
            qwen = None
            errors.append(f"qwen_absence:{type(exc).__name__}:{exc}")
        try:
            after = self._resources("unload_after")
            baseline = self.baseline_resources or before
            if baseline is None:
                raise V5ContractError("unload baseline unavailable")
            if after["cuda_allocated_bytes"] > baseline["cuda_allocated_bytes"] + float(
                self._p("resource_bounds", "maximum_unload_cuda_allocated_above_baseline_bytes")
            ):
                raise V5ContractError("unload CUDA allocation absence not proven")
            if after["cuda_reserved_bytes"] > baseline["cuda_reserved_bytes"] + float(
                self._p("resource_bounds", "maximum_unload_cuda_reserved_above_baseline_bytes")
            ):
                raise V5ContractError("unload CUDA reservation absence not proven")
            if after["process_rss_mib"] > baseline["process_rss_mib"] + float(
                self._p("resource_bounds", "maximum_unload_process_rss_above_baseline_mib")
            ):
                raise V5ContractError("unload process-RSS return not proven")
            self._host_gate(after, 0.0, "unload_after")
        except Exception as exc:
            errors.append(f"resource_after:{type(exc).__name__}:{exc}")
        try:
            self._check_elapsed(started, "cleanup")
        except Exception as exc:
            errors.append(f"cleanup_deadline:{type(exc).__name__}:{exc}")
        proven = not errors and self.model is None and self.backend is None and isinstance(qwen, dict)
        self.state = VoiceState.UNLOADED if proven else VoiceState.CLEANUP_DEBT
        if proven and previous is not VoiceState.UNLOADED:
            self.proven_unload_count += 1
        self._event("v5_unload_proven" if proven else "v5_cleanup_debt", reason=reason)
        return {
            "unloaded": proven,
            "cleanup_debt": not proven,
            "reason": reason,
            "previous_state": previous.value,
            "owned_python_references_absent": self.model is None and self.backend is None,
            "release_result": release_result,
            "cache_cleanup_results": cache_results,
            "cuda_cleanup_results": cuda_results,
            "qwen_absence": qwen,
            "resources_before": before,
            "resources_after": after,
            "errors": errors,
        }

    def full_unload(self, reason: str) -> dict[str, Any]:
        with self.operation_lock:
            return self._full_unload_locked(reason)

    def recover_cleanup_debt(self, reason: str = "cleanup_debt_retry") -> dict[str, Any]:
        with self.operation_lock:
            if self.state is not VoiceState.CLEANUP_DEBT:
                return {"recovered": False, "reason": "no_cleanup_debt"}
            result = self._full_unload_locked(reason)
            return {"recovered": result["unloaded"], "cleanup": result}


__all__ = [
    "CANONICAL_CONFIG_SHA256",
    "EXACT_CUDA_DEVICE_NAME",
    "EXACT_PROFILE_SHA256",
    "EXACT_QWEN_DIGEST",
    "EXACT_QWEN_MODEL",
    "EXACT_REFERENCE_SHA256",
    "PersistentVoiceRuntimeV5",
    "V5BoundaryTimeout",
    "V5ContractError",
    "VoiceState",
    "load_canonical_config",
    "sha256_file",
    "sha256_text",
    "validate_resource_snapshot",
    "verify_identity_files",
    "verify_preserved_baselines",
]
