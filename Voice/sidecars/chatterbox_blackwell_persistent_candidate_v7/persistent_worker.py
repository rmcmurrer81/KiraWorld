#!/usr/bin/env python3
"""Child-owned state machine for the inactive Blackwell v7 candidate.

The object in this module is constructed inside the persistent worker process.
Model/backend objects never cross IPC; only closed JSON values do.  The parent
supervisor kills this entire process tree when a command exceeds its deadline.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
import struct
import time
import wave
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v3.persistent_worker import (
    condition_content_digest,
    device_evidence,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = Path(__file__).with_name("candidate_config.json")
CANONICAL_CONFIG_SHA256 = "35b7307901eceffe45466eb996950976e607bb3c8a25f830ffe9f78161da3182"
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


class WorkerState(str, Enum):
    UNLOADED = "UNLOADED"
    LOADED_CUDA = "LOADED_CUDA"
    PARKED_CPU = "PARKED_CPU"
    QWEN_OWNED = "QWEN_OWNED"
    CLEANUP_DEBT = "CLEANUP_DEBT"


class V7ContractError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
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


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise V7ContractError(f"policy is not finite canonical JSON: {exc}") from exc


def _positive_finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise V7ContractError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise V7ContractError(f"{label} must be positive and finite")
    return result


def validate_canonical_config(config: Any) -> dict[str, Any]:
    if not isinstance(config, dict):
        raise V7ContractError("v7 config must be an object")
    exact = {
        "schema_version": 4,
        "candidate_id": "kira_chatterbox_blackwell_cpu_park_candidate_v7",
        "production_routing_authorized": False,
        "live_execution_authorized": False,
        "playback_authorized": False,
        "live_adapter_available": False,
        "worker_ownership": "persistent_child_only",
        "ipc_protocol": "kira_blackwell_v7_jsonl_1",
        "required_start_method": "spawn",
        "required_windows_termination": "job_object_kill_on_close",
        "required_windows_start_order": "create_suspended_assign_job_prove_then_resume",
        "bounded_cancellable_writer": True,
        "strict_finite_json_both_directions": True,
        "component_fingerprint_algorithm": "sha256_full_required_parameter_buffer_bytes_v1",
        "approved_profile": EXACT_PROFILE_PATH,
        "approved_profile_sha256": EXACT_PROFILE_SHA256,
        "approved_reference": EXACT_REFERENCE_PATH,
        "approved_reference_sha256": EXACT_REFERENCE_SHA256,
        "approved_audio_prompt": EXACT_REFERENCE_PATH,
        "approved_audio_prompt_sha256": EXACT_REFERENCE_SHA256,
        "owned_output_root": "RecoverySprint/runtime_cache/blackwell_chatterbox/v7_outputs",
        "qwen_model": EXACT_QWEN_MODEL,
        "qwen_digest": EXACT_QWEN_DIGEST,
        "input_channel": "public_spoken_only",
        "compute_device": "cuda",
        "cuda_device_name": EXACT_CUDA_DEVICE_NAME,
        "compute_capability": EXACT_COMPUTE_CAPABILITY,
        "cpu_synthesis_allowed": False,
        "generic_voice_allowed": False,
        "sapi_allowed": False,
        "llama_allowed": False,
        "substitute_reference_allowed": False,
        "automatic_fallback_inside_candidate": None,
        "production_fallback_retained_outside_candidate": "sealed_cpu_chatterbox_only",
    }
    for key, expected in exact.items():
        if config.get(key) != expected:
            raise V7ContractError(f"canonical v7 mismatch: {key}")
    if config.get("allowed_states") != [item.value for item in WorkerState]:
        raise V7ContractError("canonical v7 state set mismatch")
    if config.get("required_components") != ["t3", "s3gen", "ve"]:
        raise V7ContractError("canonical v7 component set mismatch")
    if config.get("durable_process_identity_fields") != [
        "pid",
        "os_creation_token",
        "executable_path",
        "executable_sha256",
        "executable_size",
        "executable_volume_serial",
        "executable_file_index",
    ]:
        raise V7ContractError("canonical v7 process identity fields mismatch")
    required_groups = {
        "resource_bounds",
        "operation_bounds_seconds",
        "qwen_policy",
        "ipc_bounds",
        "wav_bounds",
        "sealed_prior_evidence",
        "sealed_v5_baseline",
        "sealed_v2_baseline",
        "sealed_v3_rejected_baseline",
        "sealed_v4_rejected_baseline",
        "sealed_v6_baseline",
        "sealed_v6_rejecting_audit",
    }
    if not required_groups.issubset(config):
        raise V7ContractError("canonical v7 policy groups are incomplete")
    for group in ("resource_bounds", "operation_bounds_seconds", "ipc_bounds", "wav_bounds"):
        for key, value in config[group].items():
            if isinstance(value, list):
                if not value:
                    raise V7ContractError(f"{group}.{key} may not be empty")
                for index, item in enumerate(value):
                    _positive_finite(item, f"{group}.{key}[{index}]")
            else:
                _positive_finite(value, f"{group}.{key}")
    for key, value in config["qwen_policy"].items():
        if isinstance(value, bool):
            if key != "one_owned_operation_only" or value is not True:
                raise V7ContractError(f"invalid qwen policy: {key}")
        elif key == "real_reply_keep_alive":
            if value != 0:
                raise V7ContractError("real Qwen reply keep-alive must be exactly zero")
        else:
            _positive_finite(value, f"qwen_policy.{key}")
    for group in (
        "sealed_prior_evidence",
        "sealed_v5_baseline",
        "sealed_v2_baseline",
        "sealed_v3_rejected_baseline",
        "sealed_v4_rejected_baseline",
        "sealed_v6_baseline",
        "sealed_v6_rejecting_audit",
    ):
        for relative, digest in config[group].items():
            if not isinstance(relative, str) or not _is_sha256(digest):
                raise V7ContractError(f"invalid preserved entry in {group}")
    return config


def load_canonical_config() -> dict[str, Any]:
    observed = sha256_file(CONFIG_PATH)
    if CANONICAL_CONFIG_SHA256 == "CONFIG_SHA256_PENDING_SEAL":
        raise V7ContractError("v7 config is not sealed")
    if observed != CANONICAL_CONFIG_SHA256:
        raise V7ContractError("canonical v7 config hash drift")
    return validate_canonical_config(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))


def verify_preserved_bytes(config: Mapping[str, Any]) -> dict[str, str]:
    observed: dict[str, str] = {}
    for group in (
        "sealed_prior_evidence",
        "sealed_v5_baseline",
        "sealed_v2_baseline",
        "sealed_v3_rejected_baseline",
        "sealed_v4_rejected_baseline",
        "sealed_v6_baseline",
        "sealed_v6_rejecting_audit",
    ):
        for relative, expected in config[group].items():
            actual = sha256_file(PROJECT_ROOT / relative)
            observed[relative] = actual
            if actual != expected:
                raise V7ContractError(f"preserved prior byte drift: {relative}")
    return observed


def verify_identity_files() -> dict[str, str]:
    result = {
        "profile_path": EXACT_PROFILE_PATH,
        "profile_sha256": sha256_file(PROJECT_ROOT / EXACT_PROFILE_PATH),
        "reference_path": EXACT_REFERENCE_PATH,
        "reference_sha256": sha256_file(PROJECT_ROOT / EXACT_REFERENCE_PATH),
        "audio_prompt_path": EXACT_REFERENCE_PATH,
        "audio_prompt_sha256": sha256_file(PROJECT_ROOT / EXACT_REFERENCE_PATH),
    }
    if result != {
        "profile_path": EXACT_PROFILE_PATH,
        "profile_sha256": EXACT_PROFILE_SHA256,
        "reference_path": EXACT_REFERENCE_PATH,
        "reference_sha256": EXACT_REFERENCE_SHA256,
        "audio_prompt_path": EXACT_REFERENCE_PATH,
        "audio_prompt_sha256": EXACT_REFERENCE_SHA256,
    }:
        raise V7ContractError("approved identity file drift")
    return result


def _all_on(model: Any, components: tuple[str, ...], expected: str) -> tuple[bool, dict[str, Any]]:
    evidence = device_evidence(model, components)
    valid = (
        evidence.get("model_device") == expected
        and evidence.get("condition_devices") == [expected]
        and set(evidence.get("components") or {}) == set(components)
        and all(
            item.get("tensor_count", 0) > 0 and item.get("devices") == [expected]
            for item in evidence["components"].values()
        )
    )
    return valid, evidence


def _move_exact_model(model: Any, components: tuple[str, ...], device: str) -> None:
    for name in components:
        component = getattr(model, name, None)
        mover = getattr(component, "to", None)
        if component is None or not callable(mover):
            raise V7ContractError(f"required component is not movable: {name}")
        moved = mover(device)
        if moved is not None and moved is not component:
            setattr(model, name, moved)
    conditions = getattr(model, "conds", None)
    mover = getattr(conditions, "to", None)
    if conditions is None or not callable(mover):
        raise V7ContractError("conditions are not movable")
    moved = mover(device)
    if moved is not None:
        model.conds = moved
    model.device = device


def _full_tensor_bytes(tensor: Any) -> bytes:
    """Return all parameter/buffer content; sampled fingerprints are forbidden."""
    provider = getattr(tensor, "content_bytes", None)
    if callable(provider):
        value = provider()
    else:
        value = tensor
        for method_name in ("detach", "cpu", "contiguous"):
            method = getattr(value, method_name, None)
            if callable(method):
                value = method()
        numpy_method = getattr(value, "numpy", None)
        if not callable(numpy_method):
            raise V7ContractError("parameter/buffer cannot provide complete immutable bytes")
        array = numpy_method()
        tobytes = getattr(array, "tobytes", None)
        if not callable(tobytes):
            raise V7ContractError("parameter/buffer NumPy value cannot provide bytes")
        value = tobytes(order="C")
    if not isinstance(value, (bytes, bytearray, memoryview)):
        raise V7ContractError("parameter/buffer byte provider returned a non-byte value")
    return bytes(value)


def _named_component_tensors(component: Any, method_name: str) -> list[tuple[str, Any]]:
    named = getattr(component, f"named_{method_name}", None)
    if callable(named):
        values = list(named())
    else:
        plain = getattr(component, method_name, None)
        if not callable(plain):
            raise V7ContractError(f"required component has no {method_name} enumerator")
        values = [(str(index), item) for index, item in enumerate(plain())]
    if any(
        not isinstance(item, tuple)
        or len(item) != 2
        or not isinstance(item[0], str)
        or not item[0]
        for item in values
    ):
        raise V7ContractError(f"required component {method_name} names are not exact")
    names = [name for name, _ in values]
    if len(names) != len(set(names)):
        raise V7ContractError(f"required component {method_name} names are duplicated")
    return values


def component_parameter_fingerprint(
    model: Any, components: tuple[str, ...]
) -> tuple[str, list[dict[str, Any]]]:
    manifest: list[dict[str, Any]] = []
    for component_name in components:
        component = getattr(model, component_name, None)
        if component is None:
            raise V7ContractError(f"required component is absent: {component_name}")
        records: list[dict[str, Any]] = []
        for kind in ("parameters", "buffers"):
            for name, tensor in _named_component_tensors(component, kind):
                raw = _full_tensor_bytes(tensor)
                shape_raw = getattr(tensor, "shape", ())
                try:
                    shape = [int(item) for item in shape_raw]
                except (TypeError, ValueError) as exc:
                    raise V7ContractError("parameter/buffer shape is invalid") from exc
                if any(item < 0 for item in shape):
                    raise V7ContractError("parameter/buffer shape is negative")
                records.append(
                    {
                        "kind": kind[:-1],
                        "name": name,
                        "object_id": id(tensor),
                        "shape": shape,
                        "dtype": str(getattr(tensor, "dtype", "")),
                        "requires_grad": bool(getattr(tensor, "requires_grad", False)),
                        "byte_length": len(raw),
                        "content_sha256": hashlib.sha256(raw).hexdigest(),
                    }
                )
        if not any(record["kind"] == "parameter" for record in records):
            raise V7ContractError(f"required component has no parameters: {component_name}")
        manifest.append(
            {
                "component": component_name,
                "component_object_id": id(component),
                "tensors": records,
            }
        )
    encoded = _canonical_bytes(manifest)
    return hashlib.sha256(encoded).hexdigest(), manifest


def validate_resource_snapshot(
    raw: Any,
    *,
    label: str,
    now_monotonic: float,
    maximum_age_seconds: float,
    exact_worker_pid: int,
) -> dict[str, Any]:
    now = float(now_monotonic)
    if not math.isfinite(now) or now < 0:
        raise V7ContractError(f"{label}: current monotonic clock is invalid")
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
    keys = set(numeric) | {
        "sample_id",
        "sample_sequence",
        "pid",
        "cuda_device_name",
        "compute_capability",
    }
    if not isinstance(raw, dict) or set(raw) != keys:
        raise V7ContractError(f"{label}: resource schema is not exact")
    value = dict(raw)
    for key in numeric:
        item = value[key]
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise V7ContractError(f"{label}: {key} is not numeric")
        item = float(item)
        if not math.isfinite(item) or item < 0:
            raise V7ContractError(f"{label}: {key} is non-finite or negative")
        value[key] = item
    if (
        not _is_sha256(value["sample_id"])
        or isinstance(value["sample_sequence"], bool)
        or not isinstance(value["sample_sequence"], int)
        or value["sample_sequence"] <= 0
        or value["pid"] != exact_worker_pid
        or value["cuda_device_name"] != EXACT_CUDA_DEVICE_NAME
        or value["compute_capability"] != EXACT_COMPUTE_CAPABILITY
    ):
        raise V7ContractError(f"{label}: resource identity mismatch")
    captured = value["captured_monotonic"]
    if captured > now or now - captured > maximum_age_seconds:
        raise V7ContractError(f"{label}: stale or future resource evidence")
    if (
        value["total_physical_mib"] <= 0
        or value["system_commit_limit_mib"] <= 0
        or value["cuda_total_mib"] <= 0
        or value["available_physical_mib"] > value["total_physical_mib"]
        or value["system_commit_used_mib"] > value["system_commit_limit_mib"]
        or value["process_rss_mib"] > value["system_commit_used_mib"]
        or value["cuda_free_mib"] > value["cuda_total_mib"]
        or value["cuda_allocated_bytes"] > value["cuda_reserved_bytes"]
        or value["cuda_reserved_bytes"] > value["cuda_total_mib"] * 1024 * 1024
    ):
        raise V7ContractError(f"{label}: resource relationships are inconsistent")
    fraction = value["system_commit_used_mib"] / value["system_commit_limit_mib"]
    if abs(fraction - value["system_commit_fraction"]) > 1e-6:
        raise V7ContractError(f"{label}: commit fraction is inconsistent")
    return value


class PersistentWorkerV7:
    """One model/backend generation wholly owned inside one worker process."""

    def __init__(
        self,
        *,
        backend: Any,
        serialization_lease_id: str,
        worker_instance_id: str,
        config: dict[str, Any] | None = None,
        worker_pid: int | None = None,
        now=time.monotonic,
        allow_static_test: bool = False,
    ) -> None:
        canonical = load_canonical_config()
        if config is not None and config != canonical:
            raise V7ContractError("injected config is not exactly canonical")
        if not _is_sha256(serialization_lease_id) or not _is_sha256(worker_instance_id):
            raise V7ContractError("lease and worker instance must be SHA-256 values")
        self._policy = _freeze(canonical)
        self._policy_bytes = _canonical_bytes(canonical)
        self._policy_digest = hashlib.sha256(self._policy_bytes).hexdigest()
        self.backend = backend
        self._backend_object_id = id(backend)
        self.serialization_lease_id = serialization_lease_id
        self.worker_instance_id = worker_instance_id
        self.worker_pid = int(worker_pid if worker_pid is not None else os.getpid())
        if self.worker_pid <= 0:
            raise V7ContractError("worker PID must be positive")
        self.now = now
        self.allow_static_test = allow_static_test
        self.state = WorkerState.UNLOADED
        self.model: Any | None = None
        self._model_object_id: int | None = None
        self.model_generation: str | None = None
        self.component_fingerprint: str | None = None
        self.component_manifest: list[dict[str, Any]] = []
        self.condition_digest: str | None = None
        self.condition_manifest: list[dict[str, Any]] = []
        self.identity: dict[str, str] | None = None
        self.baseline_resources: dict[str, Any] | None = None
        self.qwen_binding: dict[str, Any] | None = None
        self.retained_artifact: dict[str, Any] | None = None
        self._resource_sequence = 0
        self._resource_ids: set[str] = set()
        self._qwen_sequence = 0
        self._qwen_ids: set[str] = set()
        self._load_sequence = 0
        self._generation_sequence = 0
        self.last_cleanup: dict[str, Any] | None = None

    @property
    def config(self) -> dict[str, Any]:
        return json.loads(self._policy_bytes.decode("utf-8"))

    def _p(self, *keys: str) -> Any:
        value: Any = self._policy
        for key in keys:
            value = value[key]
        return value

    def _clock(self, label: str) -> float:
        value = float(self.now())
        if not math.isfinite(value) or value < 0:
            raise V7ContractError(f"{label}: monotonic clock is invalid")
        return value

    def _require_policy(self) -> None:
        if not self.allow_static_test:
            raise V7ContractError("v7 remains inactive without static-test opt-in")
        if sha256_file(CONFIG_PATH) != CANONICAL_CONFIG_SHA256:
            raise V7ContractError("canonical v7 config hash drift")
        thawed = _thaw(self._policy)
        validate_canonical_config(thawed)
        payload = _canonical_bytes(thawed)
        if payload != self._policy_bytes or hashlib.sha256(payload).hexdigest() != self._policy_digest:
            raise V7ContractError("immutable internal v7 policy drift")
        if id(self.backend) != self._backend_object_id:
            raise V7ContractError("worker backend object identity drift")

    def _check_model_object(self) -> None:
        if self.model is None or self._model_object_id is None or id(self.model) != self._model_object_id:
            raise V7ContractError("exact child-owned model object identity drift")

    def _resources(self, label: str) -> dict[str, Any]:
        raw = self.backend.resources(label=label, worker_pid=self.worker_pid)
        value = validate_resource_snapshot(
            raw,
            label=label,
            now_monotonic=self._clock(label),
            maximum_age_seconds=float(self._p("resource_bounds", "maximum_evidence_age_seconds")),
            exact_worker_pid=self.worker_pid,
        )
        if value["sample_sequence"] <= self._resource_sequence or value["sample_id"] in self._resource_ids:
            raise V7ContractError(f"{label}: replayed resource evidence")
        self._resource_sequence = value["sample_sequence"]
        self._resource_ids.add(value["sample_id"])
        return value

    def _host_gate(self, value: Mapping[str, Any], minimum_available: float, label: str) -> None:
        if value["available_physical_mib"] < minimum_available:
            raise V7ContractError(f"{label}: insufficient available physical RAM")
        if value["system_commit_fraction"] > float(
            self._p("resource_bounds", "maximum_system_commit_fraction")
        ):
            raise V7ContractError(f"{label}: commit pressure exceeds bound")

    def _qwen_residency(self, phase: str) -> dict[str, Any]:
        result = self.backend.qwen_residency(
            phase=phase,
            serialization_lease_id=self.serialization_lease_id,
            worker_pid=self.worker_pid,
        )
        keys = {
            "query_succeeded",
            "records",
            "serialization_lease_id",
            "lease_exclusive",
            "sample_id",
            "sample_sequence",
            "captured_monotonic",
            "phase",
            "worker_pid",
        }
        now = self._clock(phase)
        if not isinstance(result, dict) or set(result) != keys:
            raise V7ContractError("Qwen residency schema is not exact")
        captured = result["captured_monotonic"]
        sequence = result["sample_sequence"]
        if (
            result["query_succeeded"] is not True
            or not isinstance(result["records"], list)
            or result["serialization_lease_id"] != self.serialization_lease_id
            or result["lease_exclusive"] is not True
            or result["phase"] != phase
            or result["worker_pid"] != self.worker_pid
            or not _is_sha256(result["sample_id"])
            or isinstance(sequence, bool)
            or not isinstance(sequence, int)
            or sequence <= self._qwen_sequence
            or result["sample_id"] in self._qwen_ids
            or isinstance(captured, bool)
            or not isinstance(captured, (int, float))
            or not math.isfinite(float(captured))
            or float(captured) > now
            or now - float(captured) > float(self._p("resource_bounds", "maximum_evidence_age_seconds"))
        ):
            raise V7ContractError("fresh worker/lease-bound Qwen residency was not proven")
        self._qwen_sequence = sequence
        self._qwen_ids.add(result["sample_id"])
        return dict(result)

    def _qwen_absent(self, phase: str) -> dict[str, Any]:
        result = self._qwen_residency(phase)
        if result["records"] != []:
            raise V7ContractError(f"{phase}: Qwen/unknown residency is not absent")
        return result

    @staticmethod
    def _exact_qwen_resident(result: Mapping[str, Any]) -> bool:
        return result.get("records") == [{"model": EXACT_QWEN_MODEL, "digest": EXACT_QWEN_DIGEST}]

    def _validated_qwen_binding(self) -> dict[str, Any]:
        binding = self.qwen_binding
        keys = {
            "owner_hash",
            "session_hash",
            "token_hash",
            "started_monotonic",
            "expires_monotonic",
        }
        if not isinstance(binding, Mapping) or set(binding) != keys:
            raise V7ContractError("Qwen ownership binding schema drift")
        if not all(_is_sha256(binding[key]) for key in ("owner_hash", "session_hash", "token_hash")):
            raise V7ContractError("Qwen ownership hashes drifted")
        if len({binding["owner_hash"], binding["session_hash"], binding["token_hash"]}) != 3:
            raise V7ContractError("Qwen ownership bindings are no longer distinct")
        started = binding["started_monotonic"]
        expiry = binding["expires_monotonic"]
        if any(
            isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(float(value)) or float(value) < 0
            for value in (started, expiry)
        ):
            raise V7ContractError("Qwen ownership clock binding drift")
        exact_ttl = float(self._p("qwen_policy", "positive_residency_ttl_seconds"))
        if float(expiry) <= float(started) or abs((float(expiry) - float(started)) - exact_ttl) > 1e-9:
            raise V7ContractError("Qwen ownership TTL binding drift")
        return dict(binding)

    def _model_snapshot(self, expected_device: str) -> dict[str, Any]:
        self._check_model_object()
        binding = self.backend.voice_model_binding(
            model=self.model,
            model_generation=self.model_generation,
            model_object_id=self._model_object_id,
            backend_object_id=self._backend_object_id,
            worker_pid=self.worker_pid,
        )
        expected_binding = {
            "same_object": True,
            "model_object_id": self._model_object_id,
            "backend_object_id": self._backend_object_id,
            "model_generation": self.model_generation,
            "worker_pid": self.worker_pid,
        }
        if binding != expected_binding:
            raise V7ContractError("backend/exact model object binding drift")
        valid, devices = _all_on(self.model, tuple(self._p("required_components")), expected_device)
        digest, manifest = condition_content_digest(self.model.conds)
        component_fingerprint, component_manifest = component_parameter_fingerprint(
            self.model, tuple(self._p("required_components"))
        )
        if (
            not valid
            or digest != self.condition_digest
            or manifest != self.condition_manifest
            or component_fingerprint != self.component_fingerprint
            or component_manifest != self.component_manifest
        ):
            raise V7ContractError(
                "model device/conditioning/component fingerprint identity drift"
            )
        return devices

    def _clear_artifact(self) -> None:
        self.retained_artifact = None

    def _cleanup(self, reason: str) -> dict[str, Any]:
        errors: list[str] = []
        qwen_result: Any = None
        release_result: Any = None
        retained_qwen_binding = dict(self.qwen_binding) if self.qwen_binding is not None else None
        qwen_proven_absent = False
        if retained_qwen_binding is not None or self.state is WorkerState.QWEN_OWNED:
            try:
                qwen_result = self.backend.qwen_unload_owned(
                    token_hash=(retained_qwen_binding or {}).get("token_hash"),
                    model=EXACT_QWEN_MODEL,
                    digest=EXACT_QWEN_DIGEST,
                    serialization_lease_id=self.serialization_lease_id,
                )
                if qwen_result != {
                    "unloaded": True,
                    "model": EXACT_QWEN_MODEL,
                    "digest": EXACT_QWEN_DIGEST,
                    "token_hash": (retained_qwen_binding or {}).get("token_hash"),
                    "serialization_lease_id": self.serialization_lease_id,
                }:
                    errors.append("exact_qwen_unload_not_proven")
                absence = self._qwen_absent("cleanup_after_qwen_unload")
                qwen_proven_absent = not errors
            except Exception as exc:
                absence = None
                errors.append(f"qwen_cleanup:{type(exc).__name__}:{exc}")
        else:
            try:
                absence = self._qwen_absent("cleanup_qwen_absence")
                qwen_proven_absent = True
            except Exception as exc:
                absence = None
                errors.append(f"qwen_absence:{type(exc).__name__}:{exc}")
        try:
            release_result = self.backend.release_voice()
            if release_result != {
                "released": True,
                "owned_model_count": 0,
                "owned_condition_count": 0,
            }:
                errors.append("voice_release_not_proven")
        except Exception as exc:
            errors.append(f"voice_release:{type(exc).__name__}:{exc}")
        self.model = None
        self._model_object_id = None
        self.model_generation = None
        self.component_fingerprint = None
        self.component_manifest = []
        self.condition_digest = None
        self.condition_manifest = []
        self.identity = None
        self.qwen_binding = None if qwen_proven_absent else retained_qwen_binding
        self._clear_artifact()
        try:
            after = self._resources("cleanup_after")
            baseline = self.baseline_resources or after
            bounds = self._p("resource_bounds")
            if (
                after["cuda_allocated_bytes"]
                > baseline["cuda_allocated_bytes"]
                + float(bounds["maximum_unload_cuda_allocated_above_baseline_bytes"])
                or after["cuda_reserved_bytes"]
                > baseline["cuda_reserved_bytes"]
                + float(bounds["maximum_unload_cuda_reserved_above_baseline_bytes"])
                or after["process_rss_mib"]
                > baseline["process_rss_mib"]
                + float(bounds["maximum_unload_process_rss_above_baseline_mib"])
            ):
                errors.append("cleanup_resource_return_not_proven")
        except Exception as exc:
            after = None
            errors.append(f"cleanup_resources:{type(exc).__name__}:{exc}")
        proven = not errors
        self.state = WorkerState.UNLOADED if proven else WorkerState.CLEANUP_DEBT
        result = {
            "unloaded": proven,
            "cleanup_debt": not proven,
            "reason": reason,
            "qwen_result": qwen_result,
            "qwen_absence": absence,
            "release_result": release_result,
            "resources_after": after,
            "errors": errors,
        }
        self.last_cleanup = result
        return result

    def _dispatch_failure(self, operation: str, exc: Exception) -> dict[str, Any]:
        cleanup = self._cleanup(f"{operation}_failure")
        return {
            "success": False,
            "operation": operation,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "cleanup": cleanup,
            "state": self.state.value,
        }

    def load_voice(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        try:
            self._require_policy()
            if set(payload) != {"owner_hash"} or not _is_sha256(payload["owner_hash"]):
                raise V7ContractError("load owner binding is not exact")
            if self.state is not WorkerState.UNLOADED:
                raise V7ContractError("initial load requires UNLOADED")
            verify_preserved_bytes(self._policy)
            identity = verify_identity_files()
            self._qwen_absent("load_before")
            baseline = self._resources("load_before")
            self._host_gate(
                baseline,
                float(self._p("resource_bounds", "minimum_available_physical_mib_before_park")),
                "load_before",
            )
            loaded = self.backend.load_voice(
                config=self.config,
                approved_audio_prompt_path=str((PROJECT_ROOT / EXACT_REFERENCE_PATH).resolve()),
                approved_audio_prompt_sha256=EXACT_REFERENCE_SHA256,
                serialization_lease_id=self.serialization_lease_id,
            )
            if not isinstance(loaded, dict) or set(loaded) != {"model", "identity", "load_proof"}:
                raise V7ContractError("child loader result schema is not exact")
            if loaded["identity"] != identity or loaded["load_proof"] != {
                "from_pretrained_call_count": 1,
                "prepare_conditionals_call_count": 1,
                "approved_audio_prompt_path": str((PROJECT_ROOT / EXACT_REFERENCE_PATH).resolve()),
                "approved_audio_prompt_sha256": EXACT_REFERENCE_SHA256,
                "serialization_lease_id": self.serialization_lease_id,
                "worker_pid": self.worker_pid,
            }:
                raise V7ContractError("exact child load/conditioning proof is absent")
            self.model = loaded["model"]
            self._model_object_id = id(self.model)
            valid, devices = _all_on(self.model, tuple(self._p("required_components")), "cuda")
            if not valid:
                raise V7ContractError("loaded child model is mixed/non-CUDA")
            digest, manifest = condition_content_digest(self.model.conds)
            component_fingerprint, component_manifest = component_parameter_fingerprint(
                self.model, tuple(self._p("required_components"))
            )
            self._load_sequence += 1
            self.model_generation = sha256_text(
                f"{self.worker_instance_id}:{self.worker_pid}:{self._model_object_id}:"
                f"{self._backend_object_id}:{self._load_sequence}:{digest}:"
                f"{component_fingerprint}:{EXACT_REFERENCE_SHA256}"
            )
            self.component_fingerprint = component_fingerprint
            self.component_manifest = component_manifest
            self.condition_digest = digest
            self.condition_manifest = manifest
            self.identity = identity
            self.baseline_resources = baseline
            devices = self._model_snapshot("cuda")
            after = self._resources("load_after")
            self._host_gate(
                after,
                float(self._p("resource_bounds", "minimum_available_physical_mib_after_resume")),
                "load_after",
            )
            self._qwen_absent("load_precommit")
            self.state = WorkerState.LOADED_CUDA
            self._qwen_absent("load_after")
            return {
                "success": True,
                "state": self.state.value,
                "model_generation": self.model_generation,
                "component_fingerprint": self.component_fingerprint,
                "condition_digest": digest,
                "device_evidence": devices,
                "worker_pid": self.worker_pid,
            }
        except Exception as exc:
            return self._dispatch_failure("load", exc)

    def park_cpu(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        try:
            self._require_policy()
            if set(payload) != {"reason"} or not isinstance(payload["reason"], str) or not payload["reason"]:
                raise V7ContractError("park reason is not exact")
            if self.state is not WorkerState.LOADED_CUDA:
                raise V7ContractError("park requires LOADED_CUDA")
            self._qwen_absent("park_before")
            self._model_snapshot("cuda")
            before = self._resources("park_before")
            _move_exact_model(self.model, tuple(self._p("required_components")), "cpu")
            cleanup = self.backend.cuda_cache_cleanup()
            if cleanup != {
                "cache_cleared": True,
                "synchronize_before": True,
                "empty_cache_called": True,
                "synchronize_after": True,
            }:
                raise V7ContractError("park CUDA/cache cleanup is not exact")
            devices = self._model_snapshot("cpu")
            after = self._resources("park_after")
            self._host_gate(
                after,
                float(self._p("resource_bounds", "minimum_available_physical_mib_after_park")),
                "park_after",
            )
            baseline = self.baseline_resources
            if baseline is None:
                raise V7ContractError("park baseline is absent")
            bounds = self._p("resource_bounds")
            if (
                after["process_rss_mib"] > float(bounds["maximum_park_process_rss_mib"])
                or after["process_rss_mib"]
                > baseline["process_rss_mib"] + float(bounds["maximum_park_process_rss_above_baseline_mib"])
                or after["cuda_allocated_bytes"]
                > baseline["cuda_allocated_bytes"]
                + float(bounds["maximum_park_cuda_allocated_above_baseline_bytes"])
                or after["cuda_reserved_bytes"]
                > baseline["cuda_reserved_bytes"]
                + float(bounds["maximum_park_cuda_reserved_above_baseline_bytes"])
            ):
                raise V7ContractError("parked RAM/VRAM bounds were not met")
            self._qwen_absent("park_precommit")
            self.state = WorkerState.PARKED_CPU
            self._qwen_absent("park_after")
            return {
                "success": True,
                "state": self.state.value,
                "model_generation": self.model_generation,
                "device_evidence": devices,
                "resources_before": before,
                "resources_after": after,
            }
        except Exception as exc:
            return self._dispatch_failure("park", exc)

    def resume_cuda(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        try:
            self._require_policy()
            if set(payload) != {"reason"} or not isinstance(payload["reason"], str) or not payload["reason"]:
                raise V7ContractError("resume reason is not exact")
            if self.state is not WorkerState.PARKED_CPU:
                raise V7ContractError("resume requires PARKED_CPU")
            self._qwen_absent("resume_before")
            self._model_snapshot("cpu")
            before = self._resources("resume_before")
            self._host_gate(
                before,
                float(self._p("resource_bounds", "minimum_available_physical_mib_after_resume")),
                "resume_before",
            )
            if before["cuda_free_mib"] < float(
                self._p("resource_bounds", "minimum_cuda_free_mib_before_resume")
            ):
                raise V7ContractError("resume CUDA headroom is insufficient")
            _move_exact_model(self.model, tuple(self._p("required_components")), "cuda")
            devices = self._model_snapshot("cuda")
            after = self._resources("resume_after")
            self._host_gate(
                after,
                float(self._p("resource_bounds", "minimum_available_physical_mib_after_resume")),
                "resume_after",
            )
            if after["cuda_free_mib"] < float(
                self._p("resource_bounds", "minimum_cuda_free_mib_after_resume")
            ):
                raise V7ContractError("resume post-CUDA headroom is insufficient")
            self._qwen_absent("resume_precommit")
            self.state = WorkerState.LOADED_CUDA
            self._qwen_absent("resume_after")
            return {
                "success": True,
                "state": self.state.value,
                "model_generation": self.model_generation,
                "device_evidence": devices,
            }
        except Exception as exc:
            return self._dispatch_failure("resume", exc)

    def qwen_load_only(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        try:
            self._require_policy()
            keys = {"owner_hash", "session_hash", "token_hash", "ttl_seconds"}
            if not isinstance(payload, Mapping) or set(payload) != keys:
                raise V7ContractError("Qwen load binding schema is not exact")
            if not all(_is_sha256(payload[key]) for key in ("owner_hash", "session_hash", "token_hash")):
                raise V7ContractError("Qwen owner/session/token hashes are invalid")
            if len({payload["owner_hash"], payload["session_hash"], payload["token_hash"]}) != 3:
                raise V7ContractError("Qwen bindings must be distinct")
            ttl = payload["ttl_seconds"]
            if isinstance(ttl, bool) or not isinstance(ttl, int):
                raise V7ContractError("Qwen TTL must be an exact integer")
            if ttl != int(self._p("qwen_policy", "positive_residency_ttl_seconds")):
                raise V7ContractError("Qwen TTL is not the immutable exact residency TTL")
            if ttl > int(self._p("qwen_policy", "maximum_residency_ttl_seconds")):
                raise V7ContractError("Qwen TTL exceeds the immutable maximum")
            if self.state is not WorkerState.PARKED_CPU or self.qwen_binding is not None:
                raise V7ContractError("Qwen load requires unowned PARKED_CPU")
            self._model_snapshot("cpu")
            self._qwen_absent("qwen_load_before")
            started = self._clock("qwen_load_start")
            expiry = started + ttl
            self.qwen_binding = _freeze({
                "owner_hash": payload["owner_hash"],
                "session_hash": payload["session_hash"],
                "token_hash": payload["token_hash"],
                "started_monotonic": started,
                "expires_monotonic": expiry,
            })
            request = {
                "purpose": "load_only",
                "model": EXACT_QWEN_MODEL,
                "expected_digest": EXACT_QWEN_DIGEST,
                "prompt": "",
                "messages": [],
                "context": [],
                "stream": False,
                "keep_alive_seconds": ttl,
                "options": {"num_predict": 0},
                "owned_token_hash": payload["token_hash"],
                "serialization_lease_id": self.serialization_lease_id,
            }
            response = self.backend.qwen_load_only(request=request)
            request_hash = hashlib.sha256(_canonical_bytes(request)).hexdigest()
            if response != {
                "model": EXACT_QWEN_MODEL,
                "digest": EXACT_QWEN_DIGEST,
                "request_hash": request_hash,
                "response": "",
                "message": {"content": ""},
                "eval_count": 0,
                "prompt_eval_count": 0,
                "serialization_lease_id": self.serialization_lease_id,
            }:
                raise V7ContractError("Qwen load-only response is not exact")
            now = self._clock("qwen_load_commit")
            if now >= expiry:
                raise V7ContractError("Qwen load completed at/after TTL")
            residency = self._qwen_residency("qwen_load_commit")
            if not self._exact_qwen_resident(residency):
                raise V7ContractError("exact Qwen digest is not solely resident")
            self.state = WorkerState.QWEN_OWNED
            committed = self._qwen_residency("qwen_load_after")
            if not self._exact_qwen_resident(committed):
                raise V7ContractError("exact Qwen digest changed after ownership commit")
            return {
                "success": True,
                "state": self.state.value,
                "expires_monotonic": expiry,
                "request_hash": request_hash,
            }
        except Exception as exc:
            return self._dispatch_failure("qwen_load", exc)

    def qwen_real_stream(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        try:
            self._require_policy()
            keys = {"owner_hash", "session_hash", "token_hash", "messages"}
            if not isinstance(payload, Mapping) or set(payload) != keys:
                raise V7ContractError("Qwen real request schema is not exact")
            if self.state is not WorkerState.QWEN_OWNED or self.qwen_binding is None:
                raise V7ContractError("Qwen real stream requires exact ownership")
            binding = self._validated_qwen_binding()
            if any(payload[key] != binding[key] for key in ("owner_hash", "session_hash", "token_hash")):
                raise V7ContractError("Qwen real stream ownership mismatch")
            messages = payload["messages"]
            if not isinstance(messages, list) or not messages:
                raise V7ContractError("Qwen real messages must be a nonempty list")
            closed_messages: list[dict[str, str]] = []
            for index, item in enumerate(messages):
                if (
                    not isinstance(item, dict)
                    or set(item) != {"role", "content"}
                    or item["role"] not in {"system", "user", "assistant"}
                    or not isinstance(item["content"], str)
                    or not item["content"].strip()
                ):
                    raise V7ContractError(f"Qwen message {index} violates closed schema")
                closed_messages.append(dict(item))
            started = self._clock("qwen_stream_start")
            expiry = float(binding["expires_monotonic"])
            if started >= expiry:
                raise V7ContractError("Qwen ownership expired before stream")
            request = {
                "model": EXACT_QWEN_MODEL,
                "expected_digest": EXACT_QWEN_DIGEST,
                "messages": closed_messages,
                "stream": True,
                "keep_alive": 0,
                "owned_token_hash": binding["token_hash"],
                "serialization_lease_id": self.serialization_lease_id,
            }
            request_hash = hashlib.sha256(_canonical_bytes(request)).hexdigest()
            envelope = self.backend.qwen_stream(request=request)
            keys = {
                "model",
                "digest",
                "request_hash",
                "chunks",
                "final_text_sha256",
                "keep_alive",
                "serialization_lease_id",
            }
            if not isinstance(envelope, dict) or set(envelope) != keys:
                raise V7ContractError("Qwen stream envelope is not exact")
            chunks = envelope["chunks"]
            maximum_chunks = int(self._p("qwen_policy", "maximum_stream_chunks"))
            maximum_bytes = int(self._p("qwen_policy", "maximum_stream_utf8_bytes"))
            if (
                not isinstance(chunks, list)
                or not chunks
                or len(chunks) > maximum_chunks
                or not all(isinstance(item, str) and item for item in chunks)
            ):
                raise V7ContractError("Qwen stream chunk count/content is outside bounds")
            total_bytes = 0
            accepted: list[str] = []
            aggregate = float(self._p("operation_bounds_seconds", "qwen_real_stream"))
            for chunk in chunks:
                total_bytes += len(chunk.encode("utf-8"))
                if total_bytes > maximum_bytes:
                    raise V7ContractError("Qwen stream exceeds UTF-8 byte bound")
                now = self._clock("qwen_stream_chunk")
                if now >= expiry or now - started > aggregate:
                    raise V7ContractError("Qwen stream exceeded TTL/aggregate deadline")
                accepted.append(chunk)
            text = "".join(accepted)
            ended = self._clock("qwen_stream_end")
            if ended >= expiry or ended - started > aggregate:
                raise V7ContractError("Qwen stream completed outside TTL/aggregate deadline")
            if (
                envelope["model"] != EXACT_QWEN_MODEL
                or envelope["digest"] != EXACT_QWEN_DIGEST
                or envelope["request_hash"] != request_hash
                or envelope["final_text_sha256"] != sha256_text(text)
                or envelope["keep_alive"] != 0
                or envelope["serialization_lease_id"] != self.serialization_lease_id
                or not text.strip()
            ):
                raise V7ContractError("Qwen stream identity/text binding failed")
            absence = self._qwen_absent("qwen_stream_precommit")
            self.qwen_binding = None
            self.state = WorkerState.PARKED_CPU
            absence_after = self._qwen_absent("qwen_stream_after")
            return {
                "success": True,
                "state": self.state.value,
                "text": text,
                "text_sha256": sha256_text(text),
                "chunk_count": len(chunks),
                "utf8_bytes": total_bytes,
                "residency_precommit": absence,
                "residency_after": absence_after,
            }
        except Exception as exc:
            return self._dispatch_failure("qwen_stream", exc)

    def _verify_wav_and_retain(
        self, artifact: Mapping[str, Any], text_sha: str, generation_id: str
    ) -> dict[str, Any]:
        keys = {
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
            "model_generation",
            "component_fingerprint",
            "model_object_id",
            "backend_object_id",
        }
        if not isinstance(artifact, Mapping) or set(artifact) != keys:
            raise V7ContractError("artifact schema is not exact")
        prompt_path = str((PROJECT_ROOT / EXACT_REFERENCE_PATH).resolve())
        if (
            artifact["generation_id"] != generation_id
            or artifact["model_generation"] != self.model_generation
            or artifact["component_fingerprint"] != self.component_fingerprint
            or artifact["model_object_id"] != self._model_object_id
            or artifact["backend_object_id"] != self._backend_object_id
            or artifact["text_sha256"] != text_sha
            or artifact["prompt_path"] != prompt_path
            or artifact["prompt_sha256"] != EXACT_REFERENCE_SHA256
            or artifact["route"] != "blackwell_gpu"
            or artifact["device"] != "cuda"
            or artifact["generic_voice_used"] is not False
            or artifact["sapi_voice_used"] is not False
            or artifact["fallback_used"] is not False
            or not _is_sha256(artifact["artifact_sha256"])
        ):
            raise V7ContractError("artifact route/identity binding failed")
        now = self._clock("artifact_verify")
        started = artifact["generation_started_monotonic"]
        ended = artifact["generation_ended_monotonic"]
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in (started, ended)):
            raise V7ContractError("artifact generation interval is invalid")
        maximum_age = float(self._p("resource_bounds", "maximum_evidence_age_seconds"))
        if (
            not math.isfinite(float(started))
            or not math.isfinite(float(ended))
            or not 0 <= float(started) <= float(ended) <= now
            or now - float(ended) > maximum_age
        ):
            raise V7ContractError("artifact generation interval is invalid")
        raw_path = Path(artifact["artifact_path"])
        if not raw_path.is_absolute() or raw_path.is_symlink():
            raise V7ContractError("artifact path is not absolute/non-symlink")
        path = raw_path.resolve(strict=True)
        root = (PROJECT_ROOT / str(self._p("owned_output_root"))).resolve()
        try:
            relative = path.relative_to(root)
        except ValueError as exc:
            raise V7ContractError("artifact escaped owned root") from exc
        cursor = root
        for part in relative.parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise V7ContractError("artifact path contains symbolic link")
        if not path.is_file() or path.suffix.lower() != ".wav":
            raise V7ContractError("artifact is not an owned WAV")
        maximum = int(self._p("wav_bounds", "maximum_file_bytes"))
        with path.open("rb") as handle:
            wav_bytes = handle.read(maximum + 1)
        if not wav_bytes or len(wav_bytes) > maximum:
            raise V7ContractError("artifact byte length is outside bounds")
        actual_sha = hashlib.sha256(wav_bytes).hexdigest()
        if actual_sha != artifact["artifact_sha256"]:
            raise V7ContractError("artifact exact-byte SHA-256 mismatch")
        try:
            with wave.open(io.BytesIO(wav_bytes), "rb") as handle:
                channels = handle.getnchannels()
                width = handle.getsampwidth()
                rate = handle.getframerate()
                frames = handle.getnframes()
                compression = handle.getcomptype()
                pcm = handle.readframes(frames)
        except (wave.Error, OSError, EOFError) as exc:
            raise V7ContractError(f"artifact WAV is unreadable: {exc}") from exc
        bounds = self._p("wav_bounds")
        duration = frames / rate if rate else 0
        if (
            channels not in bounds["allowed_channels"]
            or width not in bounds["allowed_sample_width_bytes"]
            or not int(bounds["minimum_sample_rate_hz"]) <= rate <= int(bounds["maximum_sample_rate_hz"])
            or compression != "NONE"
            or not float(bounds["minimum_duration_seconds"]) <= duration <= float(bounds["maximum_duration_seconds"])
            or len(pcm) != frames * channels * width
        ):
            raise V7ContractError("artifact WAV structure is outside bounds")
        peak = max((abs(value) for value in struct.unpack(f"<{len(pcm) // 2}h", pcm)), default=0)
        if peak < int(bounds["minimum_absolute_pcm_peak"]):
            raise V7ContractError("artifact WAV is silent")
        handle_id = sha256_text(
            f"{self.worker_instance_id}:{generation_id}:{actual_sha}:{len(wav_bytes)}"
        )
        self.retained_artifact = {
            "handle_id": handle_id,
            "generation_id": generation_id,
            "artifact_sha256": actual_sha,
            "resolved_path": str(path),
            "byte_length": len(wav_bytes),
            "retained_bytes": bytes(wav_bytes),
            "retained_monotonic": now,
            "expires_monotonic": now + float(bounds["retained_artifact_ttl_seconds"]),
        }
        return {
            "handle_id": handle_id,
            "generation_id": generation_id,
            "artifact_sha256": actual_sha,
            "resolved_path": str(path),
            "byte_length": len(wav_bytes),
            "channels": channels,
            "sample_width_bytes": width,
            "sample_rate_hz": rate,
            "frame_count": frames,
            "duration_seconds": duration,
            "absolute_pcm_peak": peak,
            "expires_monotonic": self.retained_artifact["expires_monotonic"],
            "consumer_contract": "same_worker_retained_bytes_only_playback_not_implemented",
        }

    def _verify_cuda_generation(
        self,
        evidence: Any,
        *,
        generation_id: str,
        text_sha: str,
        artifact_sha: str,
        generation_started: float,
        generation_ended: float,
    ) -> dict[str, Any]:
        keys = {
            "generation_id",
            "text_sha256",
            "artifact_sha256",
            "model_generation",
            "component_fingerprint",
            "worker_instance_id",
            "worker_pid",
            "model_object_id",
            "backend_object_id",
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
            raise V7ContractError("CUDA generation evidence schema is not exact")
        allocations = (
            evidence["allocated_before_bytes"],
            evidence["peak_allocated_bytes"],
            evidence["allocated_after_bytes"],
        )
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in allocations):
            raise V7ContractError("CUDA allocation values are invalid")
        start = evidence["sample_start_monotonic"]
        end = evidence["sample_end_monotonic"]
        now = self._clock("cuda_generation_verify")
        maximum_age = float(self._p("resource_bounds", "maximum_evidence_age_seconds"))
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in (start, end)):
            raise V7ContractError("CUDA sample interval is invalid")
        if (
            not math.isfinite(float(start))
            or not math.isfinite(float(end))
            or not 0 <= float(start) <= generation_started <= generation_ended <= float(end) <= now
            or now - float(end) > maximum_age
            or evidence["generation_id"] != generation_id
            or evidence["text_sha256"] != text_sha
            or evidence["artifact_sha256"] != artifact_sha
            or evidence["model_generation"] != self.model_generation
            or evidence["component_fingerprint"] != self.component_fingerprint
            or evidence["model_object_id"] != self._model_object_id
            or evidence["backend_object_id"] != self._backend_object_id
            or evidence["worker_instance_id"] != self.worker_instance_id
            or evidence["worker_pid"] != self.worker_pid
            or evidence["device"] != "cuda"
            or evidence["cuda_device_name"] != EXACT_CUDA_DEVICE_NAME
            or evidence["compute_capability"] != EXACT_COMPUTE_CAPABILITY
            or evidence["peak_allocated_bytes"] <= evidence["allocated_before_bytes"]
            or evidence["allocated_after_bytes"] > evidence["peak_allocated_bytes"]
            or evidence["synchronize_before"] is not True
            or evidence["synchronize_after"] is not True
            or evidence["unsupported_architecture_warning"] is not False
            or evidence["no_kernel_image_error"] is not False
        ):
            raise V7ContractError("fresh generation-scoped CUDA proof failed")
        return dict(evidence)

    def synthesize(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        try:
            self._require_policy()
            keys = {
                "text",
                "text_sha256",
                "input_channel",
                "profile_sha256",
                "reference_sha256",
                "condition_digest",
            }
            if not isinstance(payload, Mapping) or set(payload) != keys:
                raise V7ContractError("synthesis request schema is not exact")
            text = payload["text"]
            if not isinstance(text, str) or not text.strip():
                raise V7ContractError("public SPOKEN text is empty")
            if dict(payload) != {
                "text": text,
                "text_sha256": sha256_text(text),
                "input_channel": "public_spoken_only",
                "profile_sha256": EXACT_PROFILE_SHA256,
                "reference_sha256": EXACT_REFERENCE_SHA256,
                "condition_digest": self.condition_digest,
            }:
                raise V7ContractError("synthesis identity/text binding failed")
            if self.state is not WorkerState.LOADED_CUDA:
                raise V7ContractError("CPU/unloaded synthesis is forbidden")
            verify_identity_files()
            self._qwen_absent("synthesis_before")
            devices_before = self._model_snapshot("cuda")
            self._generation_sequence += 1
            generation_id = sha256_text(
                f"{self.worker_instance_id}:{self.worker_pid}:{self.model_generation}:"
                f"{payload['text_sha256']}:{self._generation_sequence}:{self.serialization_lease_id}"
            )
            artifact = self.backend.synthesize_cuda(
                model=self.model,
                model_object_id=self._model_object_id,
                backend_object_id=self._backend_object_id,
                text=text,
                text_sha256=payload["text_sha256"],
                generation_id=generation_id,
                model_generation=self.model_generation,
                component_fingerprint=self.component_fingerprint,
                approved_audio_prompt_path=str((PROJECT_ROOT / EXACT_REFERENCE_PATH).resolve()),
                approved_audio_prompt_sha256=EXACT_REFERENCE_SHA256,
                owned_output_root=str((PROJECT_ROOT / str(self._p("owned_output_root"))).resolve()),
                serialization_lease_id=self.serialization_lease_id,
                worker_instance_id=self.worker_instance_id,
                worker_pid=self.worker_pid,
            )
            lease = self._verify_wav_and_retain(artifact, payload["text_sha256"], generation_id)
            evidence = self.backend.cuda_generation_evidence(
                generation_id=generation_id,
                text_sha256=payload["text_sha256"],
                artifact_sha256=lease["artifact_sha256"],
                model_generation=self.model_generation,
                component_fingerprint=self.component_fingerprint,
                worker_instance_id=self.worker_instance_id,
                worker_pid=self.worker_pid,
            )
            cuda = self._verify_cuda_generation(
                evidence,
                generation_id=generation_id,
                text_sha=payload["text_sha256"],
                artifact_sha=lease["artifact_sha256"],
                generation_started=float(artifact["generation_started_monotonic"]),
                generation_ended=float(artifact["generation_ended_monotonic"]),
            )
            self._qwen_absent("synthesis_precommit")
            devices_after = self._model_snapshot("cuda")
            self._qwen_absent("synthesis_after")
            return {
                "success": True,
                "state": self.state.value,
                "device": "cuda",
                "generation_id": generation_id,
                "model_generation": self.model_generation,
                "component_fingerprint": self.component_fingerprint,
                "text_sha256": payload["text_sha256"],
                "profile_sha256": EXACT_PROFILE_SHA256,
                "reference_sha256": EXACT_REFERENCE_SHA256,
                "generic_voice_used": False,
                "sapi_voice_used": False,
                "fallback_used": False,
                "artifact_lease": lease,
                "cuda_execution": cuda,
                "device_evidence_before": devices_before,
                "device_evidence_after": devices_after,
                "playback_implemented": False,
            }
        except Exception as exc:
            return self._dispatch_failure("synthesis", exc)

    def artifact_status(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        try:
            self._require_policy()
            if set(payload) != {"handle_id", "artifact_sha256", "generation_id"}:
                raise V7ContractError("artifact status request is not exact")
            retained = self.retained_artifact
            if retained is None or any(retained[key] != payload[key] for key in payload):
                raise V7ContractError("retained artifact identity mismatch")
            now = self._clock("artifact_status")
            if now >= float(retained["expires_monotonic"]):
                self._clear_artifact()
                raise V7ContractError("retained artifact expired")
            retained_sha = hashlib.sha256(retained["retained_bytes"]).hexdigest()
            path = Path(retained["resolved_path"])
            try:
                path_sha = sha256_file(path)
            except OSError as exc:
                raise V7ContractError(f"artifact path is unreadable: {exc}") from exc
            if retained_sha != retained["artifact_sha256"] or path_sha != retained_sha:
                raise V7ContractError("artifact changed after verification")
            return {
                "success": True,
                "handle_id": retained["handle_id"],
                "artifact_sha256": retained_sha,
                "generation_id": retained["generation_id"],
                "byte_length": retained["byte_length"],
                "retained_bytes_authoritative": True,
                "playback_implemented": False,
            }
        except Exception as exc:
            return {
                "success": False,
                "operation": "artifact_status",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "state": self.state.value,
            }

    def cleanup(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        reason = payload.get("reason") if isinstance(payload, Mapping) else None
        if not isinstance(reason, str) or not reason:
            reason = "malformed_cleanup_request"
        result = self._cleanup(reason)
        return {**result, "success": result["unloaded"], "state": self.state.value}

    def recover_external_cleanup(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Fresh-worker recovery after the prior owned worker tree was killed."""
        try:
            self._require_policy()
            if (
                not isinstance(payload, Mapping)
                or set(payload) != {"token_hash", "reason"}
                or not _is_sha256(payload["token_hash"])
                or not isinstance(payload["reason"], str)
                or not payload["reason"]
            ):
                raise V7ContractError("external recovery binding is not exact")
            self.qwen_binding = {
                "owner_hash": "recovery_only",
                "session_hash": "recovery_only",
                "token_hash": payload["token_hash"],
                "started_monotonic": self._clock("external_recovery_start"),
                "expires_monotonic": self._clock("external_recovery_expiry") + 1.0,
            }
            self.state = WorkerState.CLEANUP_DEBT
            result = self._cleanup(payload["reason"])
            return {
                "success": result["unloaded"],
                "external_qwen_cleanup_proven": result["unloaded"],
                "cleanup": result,
                "state": self.state.value,
            }
        except Exception as exc:
            return self._dispatch_failure("recover_external", exc)

    def dispatch(self, operation: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        methods = {
            "load": self.load_voice,
            "park": self.park_cpu,
            "resume": self.resume_cuda,
            "qwen_load": self.qwen_load_only,
            "qwen_stream": self.qwen_real_stream,
            "synthesis": self.synthesize,
            "artifact_status": self.artifact_status,
            "cleanup": self.cleanup,
            "shutdown": self.cleanup,
            "recover_external": self.recover_external_cleanup,
        }
        if operation not in methods:
            result = self._dispatch_failure(
                "malformed_request", V7ContractError("unknown worker operation")
            )
            return result
        return methods[operation](payload)


__all__ = [
    "CANONICAL_CONFIG_SHA256",
    "EXACT_CUDA_DEVICE_NAME",
    "EXACT_PROFILE_SHA256",
    "EXACT_QWEN_DIGEST",
    "EXACT_QWEN_MODEL",
    "EXACT_REFERENCE_SHA256",
    "PersistentWorkerV7",
    "V7ContractError",
    "WorkerState",
    "load_canonical_config",
    "sha256_file",
    "sha256_text",
    "validate_resource_snapshot",
    "verify_identity_files",
    "verify_preserved_bytes",
]
