#!/usr/bin/env python3
"""Inactive Blackwell v4 CPU-park/CUDA-restore static candidate.

V4 repairs the ten blockers reproduced against v3.  It imports no Torch or
Chatterbox at module load, has no playback/fallback route, and is not connected
to production.  Bounded harnesses inject the live adapters only after a fresh
independent audit.
"""

from __future__ import annotations

import gc
import hashlib
import json
import math
import threading
import time
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterable

from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v3.persistent_worker import (
    condition_content_digest,
    device_evidence,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = Path(__file__).with_name("candidate_config.json")
CANONICAL_CONFIG_SHA256 = "1eccc9e7729c42fe9b228373b41846281d86450b9f2a4dd7a6fab46d6878a5d5"
EXACT_QWEN_MODEL = "qwen3.5:9b"
EXACT_QWEN_DIGEST = "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
EXACT_PROFILE_PATH = "Voice/profiles/temp_ai/kira_voice_profile.json"
EXACT_PROFILE_SHA256 = "102d17f5420a1a16b3a920204ebde0d532c0a9bfd2979dca28048378ecddc116"
EXACT_REFERENCE_PATH = (
    "Voice/reference_packs/kira/kira_online_source_20260706_221447/"
    "model_input/approved_reference.wav"
)
EXACT_REFERENCE_SHA256 = "2039a2abd600a63c294d69c2b2e4d450c64c850dc6d1c9a4fbfa1700ba92069c"


class VoiceState(str, Enum):
    UNLOADED = "UNLOADED"
    PARKED_CPU = "PARKED_CPU"
    LOADED_CUDA = "LOADED_CUDA"
    CLEANUP_DEBT = "CLEANUP_DEBT"


class V4ContractError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _validate_canonical_config(config: Any) -> dict[str, Any]:
    if not isinstance(config, dict):
        raise V4ContractError("canonical v4 config is not an object")
    exact = {
        "candidate_id": "kira_chatterbox_blackwell_cpu_park_candidate_v4",
        "production_routing_authorized": False,
        "live_execution_authorized": False,
        "playback_authorized": False,
        "approved_profile": EXACT_PROFILE_PATH,
        "approved_profile_sha256": EXACT_PROFILE_SHA256,
        "approved_reference": EXACT_REFERENCE_PATH,
        "approved_reference_sha256": EXACT_REFERENCE_SHA256,
        "approved_audio_prompt": EXACT_REFERENCE_PATH,
        "approved_audio_prompt_sha256": EXACT_REFERENCE_SHA256,
        "qwen_model": EXACT_QWEN_MODEL,
        "qwen_digest": EXACT_QWEN_DIGEST,
        "input_channel": "public_spoken_only",
        "compute_device": "cuda",
        "cpu_synthesis_allowed": False,
        "generic_voice_allowed": False,
        "sapi_allowed": False,
        "substitute_reference_allowed": False,
        "automatic_fallback_inside_candidate": None,
        "production_fallback_retained_outside_candidate": "sealed_cpu_chatterbox_only",
    }
    for key, expected in exact.items():
        if config.get(key) != expected:
            raise V4ContractError(f"canonical immutable config mismatch: {key}")
    if config.get("required_components") != ["t3", "s3gen", "ve"]:
        raise V4ContractError("canonical component set mismatch")
    if config.get("allowed_states") != [
        "UNLOADED",
        "PARKED_CPU",
        "LOADED_CUDA",
        "CLEANUP_DEBT",
    ]:
        raise V4ContractError("canonical state set mismatch")
    if config.get("closed_synthesis_request_keys") != sorted(
        [
            "condition_digest",
            "input_channel",
            "profile_sha256",
            "reference_sha256",
            "text",
            "text_sha256",
        ]
    ):
        raise V4ContractError("closed synthesis schema mismatch")
    return config


def load_canonical_config() -> dict[str, Any]:
    if sha256_file(CONFIG_PATH) != CANONICAL_CONFIG_SHA256:
        raise V4ContractError("canonical v4 config file hash drift")
    return _validate_canonical_config(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))


def verify_preserved_baselines(config: dict[str, Any]) -> dict[str, str]:
    observed: dict[str, str] = {}
    for group in ("sealed_v2_baseline", "sealed_v3_rejected_baseline"):
        for relative, expected in config[group].items():
            actual = sha256_file(PROJECT_ROOT / relative)
            observed[relative] = actual
            if actual != expected:
                raise V4ContractError(f"preserved baseline drift: {relative}")
    return observed


def verify_identity_files(_config: dict[str, Any] | None = None) -> dict[str, str]:
    observed = {
        "profile_path": EXACT_PROFILE_PATH,
        "profile_sha256": sha256_file(PROJECT_ROOT / EXACT_PROFILE_PATH),
        "reference_path": EXACT_REFERENCE_PATH,
        "reference_sha256": sha256_file(PROJECT_ROOT / EXACT_REFERENCE_PATH),
        "audio_prompt_path": EXACT_REFERENCE_PATH,
        "audio_prompt_sha256": sha256_file(PROJECT_ROOT / EXACT_REFERENCE_PATH),
    }
    if observed != {
        "profile_path": EXACT_PROFILE_PATH,
        "profile_sha256": EXACT_PROFILE_SHA256,
        "reference_path": EXACT_REFERENCE_PATH,
        "reference_sha256": EXACT_REFERENCE_SHA256,
        "audio_prompt_path": EXACT_REFERENCE_PATH,
        "audio_prompt_sha256": EXACT_REFERENCE_SHA256,
    }:
        raise V4ContractError("approved profile/reference/audio-prompt identity drift")
    return observed


def validate_resource_snapshot(raw: Any, *, label: str) -> dict[str, float]:
    required = (
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
    )
    if not isinstance(raw, dict) or not set(required).issubset(raw):
        raise V4ContractError(f"{label}: resource fields missing")
    values: dict[str, float] = {}
    for key in required:
        value = raw[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise V4ContractError(f"{label}: {key} is not numeric")
        numeric = float(value)
        if not math.isfinite(numeric) or numeric < 0:
            raise V4ContractError(f"{label}: {key} is non-finite or negative")
        values[key] = numeric
    if values["total_physical_mib"] <= 0 or values["system_commit_limit_mib"] <= 0:
        raise V4ContractError(f"{label}: total RAM/commit limit must be positive")
    if values["cuda_total_mib"] <= 0:
        raise V4ContractError(f"{label}: total CUDA memory must be positive")
    if values["available_physical_mib"] > values["total_physical_mib"]:
        raise V4ContractError(f"{label}: available RAM exceeds total")
    if values["system_commit_used_mib"] > values["system_commit_limit_mib"]:
        raise V4ContractError(f"{label}: committed memory exceeds limit")
    if values["process_rss_mib"] > values["system_commit_used_mib"]:
        raise V4ContractError(f"{label}: process RSS exceeds total committed memory")
    recomputed = values["system_commit_used_mib"] / values["system_commit_limit_mib"]
    if abs(recomputed - values["system_commit_fraction"]) > 1e-6:
        raise V4ContractError(f"{label}: commit fraction is internally inconsistent")
    if values["cuda_free_mib"] > values["cuda_total_mib"]:
        raise V4ContractError(f"{label}: CUDA free exceeds total")
    cuda_total_bytes = values["cuda_total_mib"] * 1024 * 1024
    if values["cuda_allocated_bytes"] > values["cuda_reserved_bytes"]:
        raise V4ContractError(f"{label}: CUDA allocated exceeds reserved")
    if values["cuda_reserved_bytes"] > cuda_total_bytes:
        raise V4ContractError(f"{label}: CUDA reservation exceeds total memory")
    return values


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
            raise V4ContractError(f"required component is not movable: {name}")
        result = mover(device)
        if result is not None and result is not component:
            setattr(model, name, result)
    conditions = getattr(model, "conds", None)
    mover = getattr(conditions, "to", None)
    if conditions is None or not callable(mover):
        raise V4ContractError("conditionals are not movable")
    result = mover(device)
    if result is not None:
        model.conds = result
    model.device = device


def _qwen_absent(evidence: Any) -> bool:
    return bool(
        isinstance(evidence, dict)
        and evidence.get("query_succeeded") is True
        and evidence.get("target_model") == EXACT_QWEN_MODEL
        and evidence.get("target_digest") == EXACT_QWEN_DIGEST
        and evidence.get("records") == []
        and evidence.get("model_state_changed") is False
    )


class PersistentVoiceRuntimeV4:
    def __init__(
        self,
        *,
        config: dict[str, Any] | None = None,
        loader: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        qwen_probe: Callable[[], dict[str, Any]] | None = None,
        resource_probe: Callable[[], dict[str, Any]] | None = None,
        cache_clearer: Callable[[], dict[str, Any]] | None = None,
        cuda_cleanup: Callable[[], dict[str, Any]] | None = None,
        now: Callable[[], float] | None = None,
        allow_inactive_static_execution: bool = False,
    ) -> None:
        canonical = load_canonical_config()
        if config is not None and config != canonical:
            raise V4ContractError("injected config is not exactly canonical")
        self.config = canonical
        self._loader = loader
        self._qwen_probe = qwen_probe
        self._resource_probe = resource_probe
        self._cache_clearer = cache_clearer
        self._cuda_cleanup = cuda_cleanup
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
        self.baseline_resources: dict[str, float] | None = None
        self.model_load_count = 0
        self.conditioning_count = 0
        self.park_count = 0
        self.resume_count = 0
        self.synthesis_count = 0
        self.proven_unload_count = 0
        self.audit_events: list[dict[str, Any]] = []
        self._sequence = 0
        self.last_activity_monotonic = self._now()

    def _require_opt_in(self) -> None:
        if not self._allow_static:
            raise V4ContractError("inactive v4 requires bounded static harness opt-in")
        _validate_canonical_config(self.config)

    def _event(self, event: str, **fields: Any) -> None:
        self._sequence += 1
        self.audit_events.append(
            {"sequence": self._sequence, "event": event, "state": self.state.value, **fields}
        )

    def _resources(self, label: str) -> dict[str, float]:
        if not callable(self._resource_probe):
            raise V4ContractError("resource probe is required")
        return validate_resource_snapshot(self._resource_probe(), label=label)

    def _qwen_absence(self) -> dict[str, Any]:
        if not callable(self._qwen_probe):
            raise V4ContractError("exact Qwen probe is required")
        result = self._qwen_probe()
        if not _qwen_absent(result):
            raise V4ContractError("exact Qwen absence was not freshly proven")
        return dict(result)

    def _check_elapsed(self, started: float, operation: str) -> float:
        elapsed = float(self._now()) - float(started)
        bound = float(self.config["operation_bounds_seconds"][operation])
        if not math.isfinite(elapsed) or elapsed < 0 or elapsed > bound:
            raise V4ContractError(f"{operation} exceeded bounded deadline")
        return elapsed

    def _host_gate(self, resources: dict[str, float], *, minimum_available: float, label: str) -> None:
        if resources["available_physical_mib"] < minimum_available:
            raise V4ContractError(f"{label}: insufficient available physical RAM")
        if resources["system_commit_fraction"] > float(
            self.config["resource_bounds"]["maximum_system_commit_fraction"]
        ):
            raise V4ContractError(f"{label}: system commit pressure exceeds bound")

    def _identity_now(self) -> dict[str, str]:
        return verify_identity_files(self.config)

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
        }

    def load_initial(self, owner: str) -> dict[str, Any]:
        with self.operation_lock:
            self._require_opt_in()
            started = self._now()
            if self.state is not VoiceState.UNLOADED:
                return {"loaded": False, "reason": "initial_load_requires_unloaded"}
            try:
                if not isinstance(owner, str) or not owner.strip():
                    raise V4ContractError("nonempty owner is required")
                verify_preserved_baselines(self.config)
                identity = self._identity_now()
                self._qwen_absence()
                baseline = self._resources("load_before")
                self._host_gate(
                    baseline,
                    minimum_available=float(
                        self.config["resource_bounds"]["minimum_available_physical_mib_before_park"]
                    ),
                    label="load_before",
                )
                self.baseline_resources = baseline
                if not callable(self._loader):
                    raise V4ContractError("bounded loader is unavailable")
                payload = self._loader(self.config)
                if not isinstance(payload, dict):
                    raise V4ContractError("loader response is not an object")
                proof = payload.get("load_proof")
                if proof != {
                    "from_pretrained_call_count": 1,
                    "prepare_conditionals_call_count": 1,
                    "approved_audio_prompt_path": str((PROJECT_ROOT / EXACT_REFERENCE_PATH).resolve()),
                    "approved_audio_prompt_sha256": EXACT_REFERENCE_SHA256,
                }:
                    raise V4ContractError("one exact load/conditioning proof is absent")
                if payload.get("identity") != identity:
                    raise V4ContractError("loader identity differs from freshly hashed identity")
                self.model = payload.get("model")
                self.backend = payload.get("backend")
                if self.model is None or not isinstance(self.backend, dict):
                    raise V4ContractError("loader omitted owned model/backend")
                all_cuda, devices = _all_on(
                    self.model, self.config["required_components"], "cuda"
                )
                if not all_cuda:
                    raise V4ContractError(f"loaded model is mixed/non-CUDA: {devices}")
                digest, manifest = condition_content_digest(self.model.conds)
                after = self._resources("load_after")
                self._host_gate(
                    after,
                    minimum_available=float(
                        self.config["resource_bounds"]["minimum_available_physical_mib_after_resume"]
                    ),
                    label="load_after",
                )
                if after["cuda_free_mib"] < float(
                    self.config["resource_bounds"]["minimum_cuda_free_mib_after_resume"]
                ):
                    raise V4ContractError("load_after: insufficient CUDA free headroom")
                self._check_elapsed(started, "load")
                self.identity = identity
                self.condition_digest = digest
                self.condition_manifest = manifest
                self.model_load_count = 1
                self.conditioning_count = 1
                self.model_object_generation = sha256_text(
                    f"{id(self.model)}:{digest}:{EXACT_REFERENCE_SHA256}"
                )
                self.state = VoiceState.LOADED_CUDA
                self.last_activity_monotonic = self._now()
                self._event("v4_initial_load_proven")
                return {
                    "loaded": True,
                    "identity": identity,
                    "device_evidence": devices,
                    "resources_before": baseline,
                    "resources_after": after,
                    "lifecycle": self.lifecycle(),
                }
            except Exception as exc:
                cleanup = self._full_unload_locked("load_failure")
                return {
                    "loaded": False,
                    "reason": "v4_load_failed_closed",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "cleanup": cleanup,
                    "lifecycle": self.lifecycle(),
                }

    def park_cpu(self, reason: str) -> dict[str, Any]:
        with self.operation_lock:
            self._require_opt_in()
            started = self._now()
            if self.state is not VoiceState.LOADED_CUDA or self.model is None:
                return {"parked": False, "reason": "park_requires_loaded_cuda"}
            generation = self.model_object_generation
            digest = self.condition_digest
            try:
                if self._identity_now() != self.identity:
                    raise V4ContractError("identity drift before park")
                before = self._resources("park_before")
                self._host_gate(
                    before,
                    minimum_available=float(
                        self.config["resource_bounds"]["minimum_available_physical_mib_before_park"]
                    ),
                    label="park_before",
                )
                _move_exact_model(self.model, self.config["required_components"], "cpu")
                if not callable(self._cache_clearer) or not callable(self._cuda_cleanup):
                    raise V4ContractError("independent cache/CUDA cleanup callbacks are required")
                cache = self._cache_clearer()
                cuda_cleanup = self._cuda_cleanup()
                if not _exact_cache_cleanup(cache) or not _exact_cuda_cleanup(cuda_cleanup):
                    raise V4ContractError("park cache/CUDA cleanup proof failed")
                all_cpu, devices = _all_on(self.model, self.config["required_components"], "cpu")
                if not all_cpu:
                    raise V4ContractError(f"mixed-device CPU park: {devices}")
                after_digest, after_manifest = condition_content_digest(self.model.conds)
                if after_digest != digest or after_manifest != self.condition_manifest:
                    raise V4ContractError("condition identity drift during park")
                if self.model_object_generation != generation:
                    raise V4ContractError("model object generation drift during park")
                after = self._resources("park_after")
                self._host_gate(
                    after,
                    minimum_available=float(
                        self.config["resource_bounds"]["minimum_available_physical_mib_after_park"]
                    ),
                    label="park_after",
                )
                baseline = self.baseline_resources or {}
                bounds = self.config["resource_bounds"]
                if after["cuda_allocated_bytes"] > baseline["cuda_allocated_bytes"] + float(
                    bounds["maximum_park_cuda_allocated_above_baseline_bytes"]
                ):
                    raise V4ContractError("park_after: CUDA allocation did not return")
                if after["cuda_reserved_bytes"] > baseline["cuda_reserved_bytes"] + float(
                    bounds["maximum_park_cuda_reserved_above_baseline_bytes"]
                ):
                    raise V4ContractError("park_after: CUDA reservation did not return")
                self._check_elapsed(started, "park")
                self.state = VoiceState.PARKED_CPU
                self.park_count += 1
                self.last_activity_monotonic = self._now()
                self._event("v4_cpu_park_proven", reason=reason)
                return {
                    "parked": True,
                    "device_evidence": devices,
                    "resources_before": before,
                    "resources_after": after,
                    "cache_cleanup": cache,
                    "cuda_cleanup": cuda_cleanup,
                    "lifecycle": self.lifecycle(),
                }
            except Exception as exc:
                cleanup = self._full_unload_locked("park_failure")
                return {
                    "parked": False,
                    "reason": "v4_park_failed_closed",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "cleanup": cleanup,
                    "lifecycle": self.lifecycle(),
                }

    def resume_cuda(self, reason: str) -> dict[str, Any]:
        with self.operation_lock:
            self._require_opt_in()
            started = self._now()
            if self.state is not VoiceState.PARKED_CPU or self.model is None:
                return {"resumed": False, "reason": "resume_requires_parked_cpu"}
            generation = self.model_object_generation
            digest = self.condition_digest
            try:
                self._qwen_absence()
                if self._identity_now() != self.identity:
                    raise V4ContractError("identity drift before resume")
                before = self._resources("resume_before")
                self._host_gate(
                    before,
                    minimum_available=float(
                        self.config["resource_bounds"]["minimum_available_physical_mib_after_resume"]
                    ),
                    label="resume_before",
                )
                if before["cuda_free_mib"] < float(
                    self.config["resource_bounds"]["minimum_cuda_free_mib_before_resume"]
                ):
                    raise V4ContractError("resume_before: insufficient CUDA free headroom")
                _move_exact_model(self.model, self.config["required_components"], "cuda")
                if not callable(self._cuda_cleanup) or not _exact_cuda_cleanup(self._cuda_cleanup()):
                    raise V4ContractError("resume CUDA synchronization proof failed")
                all_cuda, devices = _all_on(self.model, self.config["required_components"], "cuda")
                if not all_cuda:
                    raise V4ContractError(f"mixed-device CUDA resume: {devices}")
                after_digest, after_manifest = condition_content_digest(self.model.conds)
                if after_digest != digest or after_manifest != self.condition_manifest:
                    raise V4ContractError("condition identity drift during resume")
                if self.model_object_generation != generation:
                    raise V4ContractError("model object generation drift during resume")
                after = self._resources("resume_after")
                self._host_gate(
                    after,
                    minimum_available=float(
                        self.config["resource_bounds"]["minimum_available_physical_mib_after_resume"]
                    ),
                    label="resume_after",
                )
                if after["cuda_free_mib"] < float(
                    self.config["resource_bounds"]["minimum_cuda_free_mib_after_resume"]
                ):
                    raise V4ContractError("resume_after: insufficient CUDA free headroom")
                self._check_elapsed(started, "resume")
                self.state = VoiceState.LOADED_CUDA
                self.resume_count += 1
                self.last_activity_monotonic = self._now()
                self._event("v4_cuda_resume_proven", reason=reason)
                return {
                    "resumed": True,
                    "device_evidence": devices,
                    "resources_before": before,
                    "resources_after": after,
                    "lifecycle": self.lifecycle(),
                }
            except Exception as exc:
                cleanup = self._full_unload_locked("resume_failure")
                return {
                    "resumed": False,
                    "reason": "v4_resume_failed_closed",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "cleanup": cleanup,
                    "lifecycle": self.lifecycle(),
                }

    def synthesize(self, request: dict[str, Any]) -> dict[str, Any]:
        with self.operation_lock:
            self._require_opt_in()
            started = self._now()
            if self.state is not VoiceState.LOADED_CUDA or self.model is None:
                return {
                    "generated": False,
                    "reason": "CPU_or_unloaded_synthesis_forbidden",
                    "generic_voice_used": False,
                    "sapi_voice_used": False,
                    "fallback_used": False,
                }
            try:
                if not isinstance(request, dict) or set(request) != set(
                    self.config["closed_synthesis_request_keys"]
                ):
                    raise V4ContractError("synthesis request violates closed schema")
                text = request["text"]
                if not isinstance(text, str) or not text.strip():
                    raise V4ContractError("public SPOKEN text must be nonempty")
                if request != {
                    "text": text,
                    "text_sha256": sha256_text(text),
                    "input_channel": "public_spoken_only",
                    "profile_sha256": EXACT_PROFILE_SHA256,
                    "reference_sha256": EXACT_REFERENCE_SHA256,
                    "condition_digest": self.condition_digest,
                }:
                    raise V4ContractError("synthesis identity/text binding mismatch")
                identity_before = self._identity_now()
                if identity_before != self.identity:
                    raise V4ContractError("approved files drifted before synthesis")
                self._qwen_absence()
                all_cuda, devices_before = _all_on(
                    self.model, self.config["required_components"], "cuda"
                )
                digest_before, manifest_before = condition_content_digest(self.model.conds)
                if (
                    not all_cuda
                    or digest_before != self.condition_digest
                    or manifest_before != self.condition_manifest
                ):
                    raise V4ContractError("live object identity/device proof failed before synthesis")
                generator = (self.backend or {}).get("synthesize_cuda")
                if not callable(generator):
                    raise V4ContractError("CUDA synthesis adapter is unavailable")
                artifact = generator(
                    text=text,
                    approved_audio_prompt_path=str((PROJECT_ROOT / EXACT_REFERENCE_PATH).resolve()),
                    approved_audio_prompt_sha256=EXACT_REFERENCE_SHA256,
                )
                allowed_artifact_keys = {
                    "artifact_path",
                    "artifact_sha256",
                    "generation_id",
                    "non_silent",
                    "wav_valid",
                }
                if not isinstance(artifact, dict) or set(artifact) != allowed_artifact_keys:
                    raise V4ContractError("synthesis adapter returned an open or incomplete schema")
                if artifact.get("wav_valid") is not True or artifact.get("non_silent") is not True:
                    raise V4ContractError("synthesis artifact is invalid or silent")
                execution_probe = (self.backend or {}).get("cuda_execution_evidence")
                if not callable(execution_probe):
                    raise V4ContractError("independent CUDA execution evidence is unavailable")
                execution = execution_probe()
                if not _exact_cuda_execution(execution):
                    raise V4ContractError("actual eager-CUDA synthesis proof failed")
                identity_after = self._identity_now()
                all_cuda_after, devices_after = _all_on(
                    self.model, self.config["required_components"], "cuda"
                )
                digest_after, manifest_after = condition_content_digest(self.model.conds)
                self._qwen_absence()
                if identity_after != identity_before:
                    raise V4ContractError("approved files changed during synthesis")
                if not all_cuda_after:
                    raise V4ContractError(f"mixed-device state after synthesis: {devices_after}")
                if digest_after != digest_before or manifest_after != manifest_before:
                    raise V4ContractError("condition identity changed during synthesis")
                self._check_elapsed(started, "synthesis")
                self.synthesis_count += 1
                self.last_activity_monotonic = self._now()
                self._event("v4_cuda_synthesis_proven", text_sha256=sha256_text(text))
                return {
                    "generated": True,
                    "device": "cuda",
                    "profile_sha256": EXACT_PROFILE_SHA256,
                    "reference_sha256": EXACT_REFERENCE_SHA256,
                    "condition_digest": self.condition_digest,
                    "text_sha256": sha256_text(text),
                    "approved_audio_prompt_path": str(
                        (PROJECT_ROOT / EXACT_REFERENCE_PATH).resolve()
                    ),
                    "approved_audio_prompt_sha256": EXACT_REFERENCE_SHA256,
                    "generic_voice_used": False,
                    "sapi_voice_used": False,
                    "fallback_used": False,
                    "artifact": artifact,
                    "cuda_execution": execution,
                    "device_evidence_before": devices_before,
                    "device_evidence_after": devices_after,
                    "lifecycle": self.lifecycle(),
                }
            except Exception as exc:
                cleanup = self._full_unload_locked("synthesis_failure")
                return {
                    "generated": False,
                    "reason": "v4_synthesis_failed_closed",
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
        before: dict[str, float] | None = None
        after: dict[str, float] | None = None
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
                    release_result = release()
                    if release_result != {
                        "released": True,
                        "owned_model_count": 0,
                        "owned_condition_count": 0,
                    }:
                        errors.append("release_owned:exact_release_not_proven")
                except Exception as exc:
                    errors.append(f"release_owned:{type(exc).__name__}:{exc}")
        else:
            release_result = {
                "released": True,
                "owned_model_count": 0,
                "owned_condition_count": 0,
            }
        release = None
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
                    raise V4ContractError("independent cache clearer missing")
                cache = self._cache_clearer()
                cache_results.append(cache)
                if not _exact_cache_cleanup(cache):
                    raise V4ContractError("cache cleanup not proven")
            except Exception as exc:
                errors.append(f"cache_cleanup_{index + 1}:{type(exc).__name__}:{exc}")
            try:
                if not callable(self._cuda_cleanup):
                    raise V4ContractError("independent CUDA cleanup missing")
                cuda = self._cuda_cleanup()
                cuda_results.append(cuda)
                if not _exact_cuda_cleanup(cuda):
                    raise V4ContractError("CUDA cleanup not proven")
            except Exception as exc:
                errors.append(f"cuda_cleanup_{index + 1}:{type(exc).__name__}:{exc}")
            gc.collect()
        try:
            qwen = self._qwen_absence()
        except Exception as exc:
            qwen = None
            errors.append(f"qwen_absence:{type(exc).__name__}:{exc}")
        try:
            after = self._resources("unload_after")
            baseline = self.baseline_resources or before
            if baseline is None:
                raise V4ContractError("unload baseline is unavailable")
            bounds = self.config["resource_bounds"]
            if after["cuda_allocated_bytes"] > baseline["cuda_allocated_bytes"] + float(
                bounds["maximum_unload_cuda_allocated_above_baseline_bytes"]
            ):
                raise V4ContractError("unload CUDA allocation absence not proven")
            if after["cuda_reserved_bytes"] > baseline["cuda_reserved_bytes"] + float(
                bounds["maximum_unload_cuda_reserved_above_baseline_bytes"]
            ):
                raise V4ContractError("unload CUDA reservation absence not proven")
            if after["process_rss_mib"] > baseline["process_rss_mib"] + float(
                bounds["maximum_unload_process_rss_above_baseline_mib"]
            ):
                raise V4ContractError("unload process-RSS return not proven")
            self._host_gate(after, minimum_available=0, label="unload_after")
        except Exception as exc:
            errors.append(f"resource_after:{type(exc).__name__}:{exc}")
        try:
            self._check_elapsed(started, "cleanup")
        except Exception as exc:
            errors.append(f"cleanup_deadline:{type(exc).__name__}:{exc}")
        proven = not errors and self.model is None and self.backend is None and _qwen_absent(qwen)
        if proven:
            self.state = VoiceState.UNLOADED
            if previous is not VoiceState.UNLOADED:
                self.proven_unload_count += 1
        else:
            self.state = VoiceState.CLEANUP_DEBT
        self.last_activity_monotonic = self._now()
        self._event("v4_unload_proven" if proven else "v4_cleanup_debt", reason=reason)
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
        and value.get("synchronize_before") is True
        and value.get("empty_cache_called") is True
        and value.get("synchronize_after") is True
    )


def _exact_cuda_execution(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    before = value.get("allocated_before_bytes")
    peak = value.get("peak_allocated_bytes")
    return bool(
        isinstance(before, int)
        and not isinstance(before, bool)
        and before >= 0
        and isinstance(peak, int)
        and not isinstance(peak, bool)
        and peak > before
        and value.get("synchronize_before") is True
        and value.get("synchronize_after") is True
        and value.get("unsupported_architecture_warning") is False
        and value.get("no_kernel_image_error") is False
    )


__all__ = [
    "CANONICAL_CONFIG_SHA256",
    "EXACT_PROFILE_SHA256",
    "EXACT_QWEN_DIGEST",
    "EXACT_QWEN_MODEL",
    "EXACT_REFERENCE_SHA256",
    "PersistentVoiceRuntimeV4",
    "V4ContractError",
    "VoiceState",
    "load_canonical_config",
    "sha256_file",
    "sha256_text",
    "validate_resource_snapshot",
    "verify_identity_files",
    "verify_preserved_baselines",
]
