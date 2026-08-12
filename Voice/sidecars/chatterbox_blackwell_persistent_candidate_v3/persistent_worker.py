#!/usr/bin/env python3
"""Inactive Blackwell v3 CPU-park/CUDA-restore state machine.

This module deliberately imports only the standard library.  A later bounded
engineering harness must inject the accepted loader and probes.  The static
candidate has no playback, fallback, SAPI, generic voice, or production route.
"""

from __future__ import annotations

import gc
import hashlib
import importlib
import json
import threading
import time
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = Path(__file__).with_name("candidate_config.json")


class VoiceState(str, Enum):
    UNLOADED = "UNLOADED"
    PARKED_CPU = "PARKED_CPU"
    LOADED_CUDA = "LOADED_CUDA"


class V3ContractError(RuntimeError):
    """A fail-closed v3 contract violation."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("production_routing_authorized") is not False:
        raise V3ContractError("v3 candidate must not authorize production routing")
    if value.get("live_execution_authorized") is not False:
        raise V3ContractError("static v3 candidate must keep live execution disabled")
    if value.get("playback_authorized") is not False:
        raise V3ContractError("v3 candidate must not authorize playback")
    return value


def verify_identity_files(config: dict[str, Any]) -> dict[str, str]:
    profile = PROJECT_ROOT / str(config["approved_profile"])
    reference = PROJECT_ROOT / str(config["approved_reference"])
    observed = {
        "profile_sha256": sha256_file(profile),
        "reference_sha256": sha256_file(reference),
    }
    expected = {
        "profile_sha256": str(config["approved_profile_sha256"]),
        "reference_sha256": str(config["approved_reference_sha256"]),
    }
    if observed != expected:
        raise V3ContractError(f"approved voice identity drift: {observed}")
    return observed


def verify_v2_baseline(config: dict[str, Any]) -> dict[str, str]:
    observed: dict[str, str] = {}
    for relative, expected in config["sealed_v2_baseline"].items():
        value = sha256_file(PROJECT_ROOT / relative)
        observed[relative] = value
        if value != expected:
            raise V3ContractError(f"sealed v2 drift: {relative}")
    return observed


def _device_type(value: Any) -> str:
    direct = getattr(value, "type", None)
    if direct:
        return str(direct).split(":", 1)[0].casefold()
    text = str(value or "").strip().casefold()
    return text.split(":", 1)[0] if text else ""


def _module_tensors(module: Any) -> Iterable[Any]:
    for provider_name in ("parameters", "buffers"):
        provider = getattr(module, provider_name, None)
        if not callable(provider):
            continue
        try:
            values = provider()
        except TypeError:
            values = provider(recurse=True)
        yield from values


def _looks_like_tensor(value: Any) -> bool:
    return all(hasattr(value, name) for name in ("device", "shape", "dtype", "to"))


def _condition_tensors(value: Any, path: str = "conds", seen: set[int] | None = None):
    if seen is None:
        seen = set()
    marker = id(value)
    if marker in seen:
        return
    seen.add(marker)
    if _looks_like_tensor(value):
        yield path, value
        return
    if isinstance(value, dict):
        for key in sorted(value, key=lambda item: str(item)):
            yield from _condition_tensors(value[key], f"{path}.{key}", seen)
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            yield from _condition_tensors(item, f"{path}[{index}]", seen)
        return
    namespace = getattr(value, "__dict__", None)
    if isinstance(namespace, dict):
        for key in sorted(namespace):
            if not key.startswith("__"):
                yield from _condition_tensors(namespace[key], f"{path}.{key}", seen)


def _tensor_content_bytes(tensor: Any) -> bytes:
    provider = getattr(tensor, "content_bytes", None)
    if callable(provider):
        value = provider()
        return value if isinstance(value, bytes) else bytes(value)
    value = tensor.detach() if callable(getattr(tensor, "detach", None)) else tensor
    value = value.cpu() if callable(getattr(value, "cpu", None)) else value
    value = value.contiguous() if callable(getattr(value, "contiguous", None)) else value
    value = value.numpy() if callable(getattr(value, "numpy", None)) else value
    tobytes = getattr(value, "tobytes", None)
    if callable(tobytes):
        return tobytes()
    tolist = getattr(value, "tolist", None)
    serializable = tolist() if callable(tolist) else repr(value)
    return json.dumps(serializable, sort_keys=True, default=str).encode("utf-8")


def condition_content_digest(conditions: Any) -> tuple[str, list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    digest = hashlib.sha256()
    for path, tensor in _condition_tensors(conditions):
        record = {
            "path": path,
            "shape": [int(item) for item in getattr(tensor, "shape", ())],
            "dtype": str(getattr(tensor, "dtype", "")),
        }
        payload = json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
        content = _tensor_content_bytes(tensor)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
        records.append(record)
    if not records:
        raise V3ContractError("approved-reference condition tensors were not found")
    return digest.hexdigest(), records


def _module_device_evidence(module: Any) -> dict[str, Any]:
    tensors = list(_module_tensors(module))
    devices = sorted({_device_type(getattr(item, "device", None)) for item in tensors})
    return {"tensor_count": len(tensors), "devices": devices}


def device_evidence(model: Any, required_components: Iterable[str]) -> dict[str, Any]:
    components = {
        name: _module_device_evidence(getattr(model, name, None))
        for name in required_components
    }
    condition_devices = sorted(
        {
            _device_type(getattr(tensor, "device", None))
            for _path, tensor in _condition_tensors(getattr(model, "conds", None))
        }
    )
    return {
        "model_device": _device_type(getattr(model, "device", None)),
        "components": components,
        "condition_devices": condition_devices,
    }


def _all_on(evidence: dict[str, Any], expected: str) -> bool:
    if evidence.get("model_device") != expected:
        return False
    if evidence.get("condition_devices") != [expected]:
        return False
    components = evidence.get("components") or {}
    return bool(components) and all(
        item.get("tensor_count", 0) > 0 and item.get("devices") == [expected]
        for item in components.values()
    )


def _move_model(model: Any, required_components: Iterable[str], device: str) -> None:
    for name in required_components:
        component = getattr(model, name, None)
        mover = getattr(component, "to", None)
        if component is None or not callable(mover):
            raise V3ContractError(f"required movable component missing: {name}")
        moved = mover(device)
        if moved is not None and moved is not component:
            setattr(model, name, moved)
    conditions = getattr(model, "conds", None)
    condition_mover = getattr(conditions, "to", None)
    if conditions is None or not callable(condition_mover):
        raise V3ContractError("approved-reference conditionals are not movable")
    moved_conditions = condition_mover(device)
    if moved_conditions is not None:
        model.conds = moved_conditions
    model.device = device


def clear_known_derived_cuda_caches() -> dict[str, Any]:
    """Clear only Chatterbox's documented device-derived cache objects.

    Imports are deliberately local so static import/self-checks never import
    Torch or Chatterbox.  These caches are reproducible derivatives; this does
    not touch model files, weights, the approved reference, or disk caches.
    """

    s3gen = importlib.import_module("chatterbox.models.s3gen.s3gen")
    mel = importlib.import_module("chatterbox.models.s3gen.utils.mel")
    get_resampler = getattr(s3gen, "get_resampler", None)
    cache_clear = getattr(get_resampler, "cache_clear", None)
    cache_info = getattr(get_resampler, "cache_info", None)
    if not callable(cache_clear) or not isinstance(getattr(mel, "mel_basis", None), dict) or not isinstance(
        getattr(mel, "hann_window", None), dict
    ):
        raise V3ContractError("installed Chatterbox known-cache contract changed")
    resampler_before = int(cache_info().currsize) if callable(cache_info) else None
    mel_before = len(mel.mel_basis)
    hann_before = len(mel.hann_window)
    cache_clear()
    mel.mel_basis.clear()
    mel.hann_window.clear()
    resampler_after = int(cache_info().currsize) if callable(cache_info) else 0
    return {
        "resampler_cache": {
            "cleared": resampler_after == 0,
            "entries_before": resampler_before,
            "entries_after": resampler_after,
        },
        "mel_basis": {
            "cleared": len(mel.mel_basis) == 0,
            "entries_before": mel_before,
            "entries_after": len(mel.mel_basis),
        },
        "hann_window": {
            "cleared": len(mel.hann_window) == 0,
            "entries_before": hann_before,
            "entries_after": len(mel.hann_window),
        },
    }


def _qwen_absent(evidence: Any, config: dict[str, Any]) -> bool:
    if not isinstance(evidence, dict):
        return False
    return all(
        (
            evidence.get("query_succeeded") is True,
            evidence.get("qwen_absent_proven") is True,
            evidence.get("qwen_records") == [],
            evidence.get("model_state_changed") is False,
            evidence.get("target_model") == config["qwen_model"],
            evidence.get("target_digest") == config["qwen_digest"],
        )
    )


class PersistentVoiceRuntimeV3:
    """One owned Chatterbox object with explicit CPU-park/CUDA states."""

    def __init__(
        self,
        *,
        config: dict[str, Any] | None = None,
        loader: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        identity_verifier: Callable[[dict[str, Any]], dict[str, str]] | None = None,
        qwen_probe: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        resource_probe: Callable[[], dict[str, Any]] | None = None,
        cache_clearer: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        allow_inactive_static_execution: bool = False,
    ) -> None:
        self.config = config or load_config()
        self._loader = loader
        self._identity_verifier = identity_verifier or verify_identity_files
        self._qwen_probe = qwen_probe
        self._resource_probe = resource_probe
        self._cache_clearer = cache_clearer
        self._allow_static = bool(allow_inactive_static_execution)
        self.operation_lock = threading.RLock()
        self.state = VoiceState.UNLOADED
        self.model: Any | None = None
        self.backend: dict[str, Any] | None = None
        self.model_object_generation: str | None = None
        self.condition_digest: str | None = None
        self.condition_manifest: list[dict[str, Any]] = []
        self.identity: dict[str, str] | None = None
        self.cuda_baseline_allocated_bytes: int | None = None
        self.model_load_count = 0
        self.conditioning_count = 0
        self.park_count = 0
        self.resume_count = 0
        self.synthesis_count = 0
        self.full_unload_count = 0
        self.last_activity_monotonic = time.monotonic()
        self.audit_events: list[dict[str, Any]] = []
        self._sequence = 0

    def _event(self, name: str, **fields: Any) -> None:
        self._sequence += 1
        self.audit_events.append(
            {
                "sequence": self._sequence,
                "event": name,
                "state": self.state.value,
                "monotonic": round(time.monotonic(), 6),
                **fields,
            }
        )

    def _require_static_opt_in(self) -> None:
        if not self._allow_static:
            raise V3ContractError("inactive v3 execution requires a bounded harness opt-in")
        if self.config.get("production_routing_authorized") is not False:
            raise V3ContractError("production routing must remain disabled")

    def _resources(self) -> dict[str, Any]:
        if not callable(self._resource_probe):
            raise V3ContractError("bounded resource probe is required")
        value = self._resource_probe()
        required = {
            "process_rss_mib",
            "system_commit_used_mib",
            "system_commit_limit_mib",
            "available_physical_mib",
            "system_commit_fraction",
            "cuda_allocated_bytes",
            "cuda_reserved_bytes",
            "cuda_free_mib",
        }
        if not isinstance(value, dict) or not required.issubset(value):
            raise V3ContractError("resource probe omitted required RAM/VRAM fields")
        return dict(value)

    def _probe_qwen_absent(self) -> dict[str, Any]:
        if not callable(self._qwen_probe):
            raise V3ContractError("exact-Qwen residency probe is required")
        evidence = self._qwen_probe(self.config)
        if not _qwen_absent(evidence, self.config):
            raise V3ContractError("exact Qwen absence was not proven")
        return dict(evidence)

    def _clear_known_caches(self) -> dict[str, Any]:
        if callable(self._cache_clearer):
            result = self._cache_clearer(self.backend or {})
        elif self.backend and callable(self.backend.get("clear_known_derived_caches")):
            result = self.backend["clear_known_derived_caches"]()
        else:
            result = clear_known_derived_cuda_caches()
        required = {"resampler_cache", "mel_basis", "hann_window"}
        if not isinstance(result, dict) or set(result) != required:
            raise V3ContractError("cache cleanup did not report the exact known cache set")
        if not all(item.get("cleared") is True for item in result.values()):
            raise V3ContractError("one or more known derived CUDA caches were not cleared")
        return result

    def _cuda_sync_and_empty(self) -> None:
        torch = (self.backend or {}).get("torch")
        if torch is None:
            callback = (self.backend or {}).get("cuda_sync_and_empty")
            if not callable(callback):
                raise V3ContractError("CUDA synchronization/empty-cache callback is required")
            callback()
            return
        torch.cuda.synchronize(0)
        torch.cuda.empty_cache()
        torch.cuda.synchronize(0)

    def lifecycle(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "model_object_generation": self.model_object_generation,
            "model_load_count": self.model_load_count,
            "conditioning_count": self.conditioning_count,
            "park_count": self.park_count,
            "resume_count": self.resume_count,
            "synthesis_count": self.synthesis_count,
            "full_unload_count": self.full_unload_count,
            "condition_digest": self.condition_digest,
            "identity": dict(self.identity or {}),
        }

    def load_initial(self, owner: str) -> dict[str, Any]:
        with self.operation_lock:
            self._require_static_opt_in()
            if self.state is not VoiceState.UNLOADED:
                return {"loaded": False, "reason": "initial_load_requires_unloaded", "lifecycle": self.lifecycle()}
            try:
                verify_v2_baseline(self.config)
                identity = self._identity_verifier(self.config)
                if identity != {
                    "profile_sha256": self.config["approved_profile_sha256"],
                    "reference_sha256": self.config["approved_reference_sha256"],
                }:
                    raise V3ContractError("identity verifier did not return the exact approved pair")
                qwen = self._probe_qwen_absent()
                baseline = self._resources()
                if not callable(self._loader):
                    raise V3ContractError("bounded v3 loader is not configured")
                payload = self._loader(self.config)
                if not isinstance(payload, dict):
                    raise V3ContractError("loader response is not an object")
                if payload.get("profile_sha256") != identity["profile_sha256"]:
                    raise V3ContractError("loader profile identity mismatch")
                if payload.get("reference_sha256") != identity["reference_sha256"]:
                    raise V3ContractError("loader reference identity mismatch")
                if payload.get("conditioned_reference_sha256") != identity["reference_sha256"]:
                    raise V3ContractError("conditioning reference identity mismatch")
                self.model = payload.get("model")
                self.backend = payload.get("backend")
                if self.model is None or not isinstance(self.backend, dict):
                    raise V3ContractError("loader omitted exact owned model/backend")
                evidence = device_evidence(self.model, self.config["required_components"])
                if not _all_on(evidence, "cuda"):
                    raise V3ContractError(f"initial model is not wholly CUDA resident: {evidence}")
                digest, manifest = condition_content_digest(self.model.conds)
                self.model_load_count += 1
                self.conditioning_count += 1
                self.model_object_generation = sha256_text(
                    f"{id(self.model)}:{self.model_load_count}:{identity['reference_sha256']}"
                )
                self.condition_digest = digest
                self.condition_manifest = manifest
                self.identity = dict(identity)
                self.cuda_baseline_allocated_bytes = int(baseline["cuda_allocated_bytes"])
                self.state = VoiceState.LOADED_CUDA
                self.last_activity_monotonic = time.monotonic()
                self._event("v3_initial_load_complete", owner_hash=sha256_text(owner), qwen=qwen)
                return {
                    "loaded": True,
                    "reason": "one_model_generation_and_one_approved_conditioning_loaded",
                    "device_evidence": evidence,
                    "baseline_resources": baseline,
                    "lifecycle": self.lifecycle(),
                }
            except Exception as exc:
                cleanup = self._force_unload_locked("initial_load_failure")
                return {
                    "loaded": False,
                    "reason": "v3_initial_load_failed_closed",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "cleanup": cleanup,
                    "lifecycle": self.lifecycle(),
                }

    def park_cpu(self, reason: str) -> dict[str, Any]:
        with self.operation_lock:
            self._require_static_opt_in()
            if self.state is not VoiceState.LOADED_CUDA or self.model is None:
                return {"parked": False, "reason": "park_requires_loaded_cuda", "lifecycle": self.lifecycle()}
            before_generation = self.model_object_generation
            before_digest = self.condition_digest
            try:
                if self._identity_verifier(self.config) != self.identity:
                    raise V3ContractError("approved identity drift before CPU park")
                before = self._resources()
                bounds = self.config["resource_bounds"]
                if float(before["available_physical_mib"]) < float(
                    bounds["minimum_available_physical_mib_before_cpu_park"]
                ):
                    raise V3ContractError("insufficient available physical RAM for CPU park")
                if float(before["system_commit_fraction"]) > float(
                    bounds["maximum_system_commit_fraction_before_cpu_park"]
                ):
                    raise V3ContractError("system commit pressure blocks CPU park")
                _move_model(self.model, self.config["required_components"], "cpu")
                cache_cleanup = self._clear_known_caches()
                self._cuda_sync_and_empty()
                evidence = device_evidence(self.model, self.config["required_components"])
                if not _all_on(evidence, "cpu"):
                    raise V3ContractError(f"mixed-device CPU park: {evidence}")
                digest, manifest = condition_content_digest(self.model.conds)
                if digest != before_digest or manifest != self.condition_manifest:
                    raise V3ContractError("approved condition content changed during CPU park")
                after = self._resources()
                maximum_residual = int(bounds["maximum_voice_cuda_residual_above_baseline_bytes"])
                baseline = int(self.cuda_baseline_allocated_bytes or 0)
                if int(after["cuda_allocated_bytes"]) > baseline + maximum_residual:
                    raise V3ContractError("CPU park did not return bounded owned CUDA allocation")
                if self.model_object_generation != before_generation:
                    raise V3ContractError("model object generation changed during CPU park")
                self.state = VoiceState.PARKED_CPU
                self.park_count += 1
                self.last_activity_monotonic = time.monotonic()
                self._event("v3_cpu_park_complete", reason=reason)
                return {
                    "parked": True,
                    "reason": reason,
                    "cache_cleanup": cache_cleanup,
                    "resources_before": before,
                    "resources_after": after,
                    "device_evidence": evidence,
                    "lifecycle": self.lifecycle(),
                }
            except Exception as exc:
                cleanup = self._force_unload_locked("cpu_park_failure")
                return {
                    "parked": False,
                    "reason": "v3_cpu_park_failed_closed_to_unloaded",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "cleanup": cleanup,
                    "lifecycle": self.lifecycle(),
                }

    def resume_cuda(self, reason: str) -> dict[str, Any]:
        with self.operation_lock:
            self._require_static_opt_in()
            if self.state is not VoiceState.PARKED_CPU or self.model is None:
                return {"resumed": False, "reason": "resume_requires_parked_cpu", "lifecycle": self.lifecycle()}
            before_generation = self.model_object_generation
            before_digest = self.condition_digest
            try:
                qwen = self._probe_qwen_absent()
                if self._identity_verifier(self.config) != self.identity:
                    raise V3ContractError("approved identity drift before CUDA resume")
                before = self._resources()
                if float(before["cuda_free_mib"]) < float(
                    self.config["resource_bounds"]["minimum_cuda_free_mib_before_resume"]
                ):
                    raise V3ContractError("insufficient CUDA headroom for voice resume")
                _move_model(self.model, self.config["required_components"], "cuda")
                self._cuda_sync_and_empty()
                evidence = device_evidence(self.model, self.config["required_components"])
                if not _all_on(evidence, "cuda"):
                    raise V3ContractError(f"mixed-device CUDA resume: {evidence}")
                digest, manifest = condition_content_digest(self.model.conds)
                if digest != before_digest or manifest != self.condition_manifest:
                    raise V3ContractError("approved condition content changed during CUDA resume")
                if self.model_object_generation != before_generation:
                    raise V3ContractError("model object generation changed during CUDA resume")
                after = self._resources()
                self.state = VoiceState.LOADED_CUDA
                self.resume_count += 1
                self.last_activity_monotonic = time.monotonic()
                self._event("v3_cuda_resume_complete", reason=reason, qwen=qwen)
                return {
                    "resumed": True,
                    "reason": reason,
                    "resources_before": before,
                    "resources_after": after,
                    "device_evidence": evidence,
                    "lifecycle": self.lifecycle(),
                }
            except Exception as exc:
                cleanup = self._force_unload_locked("cuda_resume_failure")
                return {
                    "resumed": False,
                    "reason": "v3_cuda_resume_failed_closed_to_unloaded",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "cleanup": cleanup,
                    "lifecycle": self.lifecycle(),
                }

    def synthesize(self, request: dict[str, Any]) -> dict[str, Any]:
        with self.operation_lock:
            self._require_static_opt_in()
            if self.state is not VoiceState.LOADED_CUDA:
                return {
                    "generated": False,
                    "reason": "cpu_or_unloaded_synthesis_forbidden",
                    "generic_voice_used": False,
                    "sapi_voice_used": False,
                    "fallback_used": False,
                    "lifecycle": self.lifecycle(),
                }
            try:
                text = str(request.get("text") or "")
                exact = all(
                    (
                        request.get("input_channel") == "public_spoken_only",
                        request.get("profile_sha256") == self.config["approved_profile_sha256"],
                        request.get("reference_sha256") == self.config["approved_reference_sha256"],
                        request.get("condition_digest") == self.condition_digest,
                        request.get("text_sha256") == sha256_text(text),
                        bool(text.strip()),
                    )
                )
                if not exact:
                    raise V3ContractError("synthesis request identity/text binding mismatch")
                self._probe_qwen_absent()
                generator = (self.backend or {}).get("synthesize_cuda")
                if not callable(generator):
                    raise V3ContractError("CUDA-only synthesis callback is unavailable")
                response = generator(dict(request))
                if not isinstance(response, dict):
                    raise V3ContractError("synthesis response is not an object")
                accepted = all(
                    (
                        response.get("generated") is True,
                        response.get("device") == "cuda",
                        response.get("profile_sha256") == self.config["approved_profile_sha256"],
                        response.get("reference_sha256") == self.config["approved_reference_sha256"],
                        response.get("condition_digest") == self.condition_digest,
                        response.get("text_sha256") == sha256_text(text),
                        response.get("generic_voice_used") is False,
                        response.get("sapi_voice_used") is False,
                        response.get("fallback_used") is False,
                    )
                )
                if not accepted:
                    raise V3ContractError("CUDA synthesis route/identity contract failed")
                self.synthesis_count += 1
                self.last_activity_monotonic = time.monotonic()
                self._event("v3_cuda_synthesis_complete", text_sha256=sha256_text(text))
                return {**response, "lifecycle": self.lifecycle()}
            except Exception as exc:
                cleanup = self._force_unload_locked("synthesis_contract_failure")
                return {
                    "generated": False,
                    "reason": "v3_synthesis_failed_closed_to_unloaded",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "generic_voice_used": False,
                    "sapi_voice_used": False,
                    "fallback_used": False,
                    "cleanup": cleanup,
                    "lifecycle": self.lifecycle(),
                }

    def _force_unload_locked(self, reason: str) -> dict[str, Any]:
        previous = self.state
        errors: list[str] = []
        backend = self.backend or {}
        cuda_cleanup_attempted = False
        releaser = backend.get("release_owned")
        if callable(releaser):
            try:
                releaser()
            except Exception as exc:  # State still becomes fail-closed UNLOADED.
                errors.append(f"release_owned:{type(exc).__name__}:{exc}")
        try:
            if self.backend is not None and (
                callable(self._cache_clearer) or callable(backend.get("clear_known_derived_caches"))
            ):
                self._clear_known_caches()
        except Exception as exc:
            errors.append(f"cache_cleanup:{type(exc).__name__}:{exc}")
        self.model = None
        self.model_object_generation = None
        self.condition_digest = None
        self.condition_manifest = []
        self.identity = None
        self.cuda_baseline_allocated_bytes = None
        gc.collect()
        if self.backend is not None:
            cuda_cleanup_attempted = True
            try:
                self._cuda_sync_and_empty()
            except Exception as exc:
                errors.append(f"cuda_sync_empty:{type(exc).__name__}:{exc}")
        self.backend = None
        self.state = VoiceState.UNLOADED
        if previous is not VoiceState.UNLOADED:
            self.full_unload_count += 1
        self.last_activity_monotonic = time.monotonic()
        self._event("v3_full_unload", reason=reason, cleanup_errors=errors)
        return {
            "unloaded": True,
            "reason": reason,
            "previous_state": previous.value,
            "owned_references_cleared": self.model is None and self.backend is None,
            "cuda_sync_and_empty_attempted": cuda_cleanup_attempted,
            "cleanup_errors": errors,
        }

    def full_unload(self, reason: str) -> dict[str, Any]:
        with self.operation_lock:
            return self._force_unload_locked(reason)

    def idle_cleanup(self, *, now_monotonic: float, idle_seconds: float) -> dict[str, Any]:
        with self.operation_lock:
            if now_monotonic - self.last_activity_monotonic < idle_seconds:
                return {"cleaned": False, "reason": "idle_bound_not_reached", "lifecycle": self.lifecycle()}
            cleanup = self._force_unload_locked("idle_timeout")
            return {"cleaned": True, "cleanup": cleanup, "lifecycle": self.lifecycle()}


__all__ = [
    "PersistentVoiceRuntimeV3",
    "V3ContractError",
    "VoiceState",
    "condition_content_digest",
    "clear_known_derived_cuda_caches",
    "device_evidence",
    "load_config",
    "sha256_file",
    "sha256_text",
    "verify_identity_files",
    "verify_v2_baseline",
]
