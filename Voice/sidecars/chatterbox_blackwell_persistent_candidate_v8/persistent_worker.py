#!/usr/bin/env python3
"""V8 adapter/playback extension around the exact accepted v7 state engine."""

from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path
from typing import Any, Mapping

from Core.blackwell_v7_process_boundary import process_identity_digest
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v7 import (
    persistent_worker as v7,
)
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v8.candidate_contract import (
    CANONICAL_CONFIG_SHA256,
    V8ContractError,
    canonical_json_sha256,
    is_sha256,
    load_canonical_config,
    sha256_file,
    verify_preserved_bytes,
)


def _component_snapshot_v8(
    model: Any, components: tuple[str, ...]
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    """Fingerprint complete tensor bytes without assuming ``Tensor.to`` identity.

    PyTorch may replace registered buffer tensor objects during an otherwise
    exact ``Module.to`` transfer.  V7 deliberately included those ephemeral
    tensor object IDs in its aggregate fingerprint, which can reject a genuine
    unchanged CUDA -> CPU -> CUDA transfer.  V8 keeps top-level component
    object identity immutable, fingerprints every complete parameter/buffer
    byte string and immutable descriptor, and tracks tensor object IDs in a
    separate transition ledger.  Tensor identity may change only at the exact
    owned transfer boundary; it is never ignored during ordinary snapshots or
    synthesis.
    """

    stable_manifest: list[dict[str, Any]] = []
    identity_manifest: list[dict[str, Any]] = []
    for component_name in components:
        component = getattr(model, component_name, None)
        if component is None:
            raise V8ContractError(f"required component is absent: {component_name}")
        stable_tensors: list[dict[str, Any]] = []
        identity_tensors: list[dict[str, Any]] = []
        for kind in ("parameters", "buffers"):
            for name, tensor in v7._named_component_tensors(component, kind):
                raw = v7._full_tensor_bytes(tensor)
                try:
                    shape = [int(item) for item in getattr(tensor, "shape", ())]
                except (TypeError, ValueError) as exc:
                    raise V8ContractError("parameter/buffer shape is invalid") from exc
                if any(item < 0 for item in shape):
                    raise V8ContractError("parameter/buffer shape is negative")
                record = {
                    "kind": kind[:-1],
                    "name": name,
                    "shape": shape,
                    "dtype": str(getattr(tensor, "dtype", "")),
                    "requires_grad": bool(getattr(tensor, "requires_grad", False)),
                    "byte_length": len(raw),
                    "content_sha256": hashlib.sha256(raw).hexdigest(),
                }
                stable_tensors.append(record)
                identity_tensors.append(
                    {
                        "kind": record["kind"],
                        "name": name,
                        "object_id": id(tensor),
                        "device": str(getattr(tensor, "device", "")),
                    }
                )
        if not any(record["kind"] == "parameter" for record in stable_tensors):
            raise V8ContractError(f"required component has no parameters: {component_name}")
        component_object_id = id(component)
        stable_manifest.append(
            {
                "component": component_name,
                "component_object_id": component_object_id,
                "tensors": stable_tensors,
            }
        )
        identity_manifest.append(
            {
                "component": component_name,
                "component_object_id": component_object_id,
                "tensors": identity_tensors,
            }
        )
    return canonical_json_sha256(stable_manifest), stable_manifest, identity_manifest


def _identity_replacement_count(
    before: list[dict[str, Any]], after: list[dict[str, Any]]
) -> int:
    def flatten(value: list[dict[str, Any]]) -> dict[tuple[str, str, str], int]:
        return {
            (component["component"], tensor["kind"], tensor["name"]): tensor["object_id"]
            for component in value
            for tensor in component["tensors"]
        }

    old = flatten(before)
    new = flatten(after)
    if set(old) != set(new):
        raise V8ContractError("parameter/buffer identity schema changed during transfer")
    return sum(old[key] != new[key] for key in old)


class PersistentWorkerV8:
    """Add exact retained-byte playback and explicit owner observation to v7."""

    def __init__(
        self,
        *,
        engine: v7.PersistentWorkerV7,
        playback_runner: Any,
        now=time.monotonic,
    ) -> None:
        self.config = load_canonical_config()
        verify_preserved_bytes(self.config)
        self.engine = engine
        self.playback_runner = playback_runner
        self._engine_object_id = id(engine)
        self._backend_object_id = id(engine.backend)
        self._playback_runner_object_id = id(playback_runner)
        self.now = now
        self.last_playback: dict[str, Any] | None = None
        self.owner_hearing: dict[str, Any] | None = None
        self._seen_playback_ids: set[str] = set()
        self._seen_acknowledgement_ids: set[str] = set()
        self.owner_hash: str | None = None

    def _clock(self, label: str) -> float:
        value = float(self.now())
        if not math.isfinite(value) or value < 0:
            raise V8ContractError(f"{label}: monotonic clock is invalid")
        return value

    def _require(self) -> None:
        if sha256_file(Path(__file__).with_name("candidate_config.json")) != CANONICAL_CONFIG_SHA256:
            raise V8ContractError("v8 config drift")
        load_canonical_config()
        verify_preserved_bytes(self.config)
        if (
            id(self.engine) != self._engine_object_id
            or id(self.engine.backend) != self._backend_object_id
            or id(self.playback_runner) != self._playback_runner_object_id
        ):
            raise V8ContractError("v8 engine/backend/playback object identity drift")

    @staticmethod
    def _validate_process_identity(identity: Any) -> dict[str, Any]:
        keys = {
            "pid",
            "os_creation_token",
            "executable_path",
            "executable_sha256",
            "executable_size",
            "executable_volume_serial",
            "executable_file_index",
        }
        if not isinstance(identity, dict) or set(identity) != keys:
            raise V8ContractError("playback process identity schema is not exact")
        if (
            isinstance(identity["pid"], bool)
            or not isinstance(identity["pid"], int)
            or identity["pid"] <= 0
            or isinstance(identity["os_creation_token"], bool)
            or not isinstance(identity["os_creation_token"], int)
            or identity["os_creation_token"] <= 0
            or not isinstance(identity["executable_path"], str)
            or not identity["executable_path"]
            or not is_sha256(identity["executable_sha256"])
            or any(
                isinstance(identity[key], bool)
                or not isinstance(identity[key], int)
                or identity[key] <= 0
                for key in ("executable_size", "executable_volume_serial", "executable_file_index")
            )
        ):
            raise V8ContractError("playback process durable identity is invalid")
        return dict(identity)

    def playback(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        try:
            self._require()
            keys = {"handle_id", "artifact_sha256", "generation_id", "playback_id"}
            if not isinstance(payload, Mapping) or set(payload) != keys:
                raise V8ContractError("playback request schema is not exact")
            if not all(is_sha256(payload[key]) for key in keys):
                raise V8ContractError("playback request binding is invalid")
            if payload["playback_id"] in self._seen_playback_ids:
                raise V8ContractError("one-time playback ID was reused")
            if not is_sha256(self.owner_hash):
                raise V8ContractError("playback has no exact loaded-owner binding")
            if self.engine.state not in {v7.WorkerState.LOADED_CUDA, v7.WorkerState.PARKED_CPU}:
                raise V8ContractError("playback requires loaded or parked exact voice")
            retained = self.engine.retained_artifact
            if not isinstance(retained, dict):
                raise V8ContractError("retained synthesis artifact is absent")
            for key in ("handle_id", "artifact_sha256", "generation_id"):
                if retained.get(key) != payload[key]:
                    raise V8ContractError("playback does not match the retained artifact")
            now = self._clock("playback_precheck")
            if now >= float(retained["expires_monotonic"]):
                raise V8ContractError("retained artifact expired before playback")
            retained_bytes = retained.get("retained_bytes")
            if not isinstance(retained_bytes, bytes):
                raise V8ContractError("authoritative retained bytes are absent")
            retained_sha = hashlib.sha256(retained_bytes).hexdigest()
            if retained_sha != payload["artifact_sha256"]:
                raise V8ContractError("retained bytes changed before playback")
            path = Path(retained["resolved_path"])
            if sha256_file(path) != retained_sha:
                raise V8ContractError("retained artifact path changed before playback")
            qwen_before = self.engine._qwen_absent("v8_playback_before")
            expected_device = "cuda" if self.engine.state is v7.WorkerState.LOADED_CUDA else "cpu"
            model_before = self.engine._model_snapshot(expected_device)
            started = self._clock("playback_call_start")
            value = self.playback_runner.play_exact(
                retained_bytes=retained_bytes,
                artifact_sha256=retained_sha,
                generation_id=payload["generation_id"],
                model_generation=self.engine.model_generation,
                component_fingerprint=self.engine.component_fingerprint,
                playback_id=payload["playback_id"],
            )
            ended = self._clock("playback_call_end")
            required = {
                "schema_version", "playback_id", "artifact_sha256", "generation_id",
                "model_generation", "component_fingerprint", "route", "device",
                "generic_voice_used", "sapi_voice_used", "fallback_used",
                "playback_api_start_monotonic", "playback_api_end_monotonic",
                "playback_api_completed", "owner_hearing_observation",
                "owner_hearing_proven", "wav_byte_length",
                "playback_process_identity", "playback_process_identity_digest",
                "playback_process_in_inherited_job", "parent_playback_start_monotonic",
                "parent_playback_end_monotonic", "owned_copy_deleted_after_return",
                "playback_worker_sha256", "playback_command_digest",
                "playback_capability_hash", "playback_source",
                "played_memory_sha256",
            }
            if not isinstance(value, dict) or set(value) != required:
                raise V8ContractError("playback telemetry schema is not exact")
            identity = self._validate_process_identity(value["playback_process_identity"])
            child_start = value["playback_api_start_monotonic"]
            child_end = value["playback_api_end_monotonic"]
            parent_start = value["parent_playback_start_monotonic"]
            parent_end = value["parent_playback_end_monotonic"]
            for label, item in (
                ("child_start", child_start), ("child_end", child_end),
                ("parent_start", parent_start), ("parent_end", parent_end),
            ):
                if isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(float(item)):
                    raise V8ContractError(f"playback {label} is invalid")
            if not float(parent_start) <= float(child_start) <= float(child_end) <= float(parent_end):
                raise V8ContractError("playback child/parent intervals are inconsistent")
            if not started <= float(parent_start) <= float(parent_end) <= ended:
                raise V8ContractError("playback operation interval is inconsistent")
            expected_executable = (
                v7.PROJECT_ROOT / self.config["voice_live_component"]["python"]
            ).resolve(strict=True)
            if (
                value["schema_version"] != 1
                or value["playback_id"] != payload["playback_id"]
                or value["artifact_sha256"] != retained_sha
                or value["generation_id"] != payload["generation_id"]
                or value["model_generation"] != self.engine.model_generation
                or value["component_fingerprint"] != self.engine.component_fingerprint
                or value["route"] != "blackwell_gpu"
                or value["device"] != "cuda"
                or value["generic_voice_used"] is not False
                or value["sapi_voice_used"] is not False
                or value["fallback_used"] is not False
                or value["playback_api_completed"] is not True
                or value["owner_hearing_observation"] is not None
                or value["owner_hearing_proven"] is not False
                or value["wav_byte_length"] != len(retained_bytes)
                or value["playback_process_in_inherited_job"] is not True
                or value["owned_copy_deleted_after_return"] is not True
                or value["playback_process_identity_digest"] != process_identity_digest(identity)
                or Path(identity["executable_path"]).resolve(strict=True) != expected_executable
                or identity["executable_sha256"]
                != self.config["voice_live_component"]["python_sha256"]
                or identity["executable_size"] != expected_executable.stat().st_size
                or value["playback_worker_sha256"] != self.config["playback"]["worker_sha256"]
                or not is_sha256(value["playback_command_digest"])
                or not is_sha256(value["playback_capability_hash"])
                or value["playback_source"] != "verified_in_memory_wav_bytes"
                or value["played_memory_sha256"] != retained_sha
            ):
                raise V8ContractError("playback route/hash/process/truth binding failed")
            if hashlib.sha256(retained_bytes).hexdigest() != retained_sha or sha256_file(path) != retained_sha:
                raise V8ContractError("retained artifact changed during playback")
            model_after = self.engine._model_snapshot(expected_device)
            qwen_after = self.engine._qwen_absent("v8_playback_after")
            self._seen_playback_ids.add(payload["playback_id"])
            self.last_playback = {
                **value,
                "qwen_absence_before": qwen_before,
                "qwen_absence_after": qwen_after,
                "model_device_evidence_before": model_before,
                "model_device_evidence_after": model_after,
                "owner_hearing_observation": None,
                "owner_hearing_proven": False,
                "owner_hearing_requires_explicit_ack": True,
                "owner_hash": self.owner_hash,
            }
            self.owner_hearing = None
            return {"success": True, "playback": dict(self.last_playback)}
        except Exception as exc:
            cleanup = self.engine.cleanup({"reason": "v8_playback_failure"})
            self.last_playback = None
            self.owner_hearing = None
            self.owner_hash = None
            return {
                "success": False,
                "operation": "playback",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "owner_hearing_proven": False,
                "cleanup": cleanup,
            }

    def owner_hearing_ack(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        try:
            self._require()
            keys = {
                "playback_id", "artifact_sha256", "generation_id",
                "observation", "acknowledgement_id", "owner_hash",
            }
            if not isinstance(payload, Mapping) or set(payload) != keys:
                raise V8ContractError("owner-hearing acknowledgement schema is not exact")
            if not all(
                is_sha256(payload[key])
                for key in ("playback_id", "artifact_sha256", "generation_id", "acknowledgement_id")
            ):
                raise V8ContractError("owner-hearing acknowledgement binding is invalid")
            if payload["observation"] not in self.config["playback"]["owner_hearing_observations"]:
                raise V8ContractError("owner-hearing observation is unsupported")
            if not is_sha256(payload["owner_hash"]) or payload["owner_hash"] != self.owner_hash:
                raise V8ContractError("owner-hearing acknowledgement owner binding is invalid")
            if payload["acknowledgement_id"] in self._seen_acknowledgement_ids:
                raise V8ContractError("owner-hearing acknowledgement ID was reused")
            playback = self.last_playback
            if not isinstance(playback, dict) or any(
                playback.get(key) != payload[key]
                for key in ("playback_id", "artifact_sha256", "generation_id")
            ):
                raise V8ContractError("owner-hearing acknowledgement has no exact completed playback")
            if self.owner_hearing is not None:
                raise V8ContractError("owner-hearing acknowledgement already exists")
            observed = self._clock("owner_hearing_ack")
            retained = self.engine.retained_artifact
            if (
                not isinstance(retained, dict)
                or observed < float(playback["parent_playback_end_monotonic"])
                or observed >= float(retained["expires_monotonic"])
                or observed - float(playback["parent_playback_end_monotonic"])
                > float(self.config["playback"]["maximum_owner_ack_delay_seconds"])
            ):
                raise V8ContractError("owner-hearing acknowledgement is stale or outside its lease")
            record = {
                "acknowledgement_id": payload["acknowledgement_id"],
                "playback_id": payload["playback_id"],
                "artifact_sha256": payload["artifact_sha256"],
                "generation_id": payload["generation_id"],
                "owner_hash": payload["owner_hash"],
                "observation": payload["observation"],
                "owner_acknowledgement_recorded_monotonic": observed,
                "owner_hearing_proven": payload["observation"] == "heard_complete",
                "automatic_claim": False,
                "evidence_kind": "explicit_owner_report_after_exact_playback",
            }
            record["record_sha256"] = canonical_json_sha256(record)
            self._seen_acknowledgement_ids.add(payload["acknowledgement_id"])
            self.owner_hearing = record
            return {"success": True, "owner_hearing": dict(record)}
        except Exception as exc:
            return {
                "success": False,
                "operation": "owner_hearing_ack",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "owner_hearing_proven": False,
            }

    def playback_status(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        if payload != {}:
            return {"success": False, "error": "playback status payload must be empty"}
        return {
            "success": True,
            "playback": dict(self.last_playback) if self.last_playback else None,
            "owner_hearing": dict(self.owner_hearing) if self.owner_hearing else None,
        }

    def dispatch(self, operation: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        if operation == "playback":
            return self.playback(payload)
        if operation == "owner_hearing_ack":
            return self.owner_hearing_ack(payload)
        if operation == "playback_status":
            return self.playback_status(payload)
        value = self.engine.dispatch(operation, payload)
        if operation == "load" and value.get("success") is True:
            owner_hash = payload.get("owner_hash")
            if not is_sha256(owner_hash):
                return self.engine._dispatch_failure(
                    "v8_owner_binding", V8ContractError("loaded owner hash is invalid")
                )
            self.owner_hash = owner_hash
        if operation in {"cleanup", "shutdown"}:
            self.last_playback = None
            self.owner_hearing = None
            self.owner_hash = None
        return value


class V8LiveStateEngine(v7.PersistentWorkerV7):
    """Exact v7 state machine whose static gate is replaced by v8 live gates."""

    def __init__(self, *args: Any, v8_config: dict[str, Any], **kwargs: Any) -> None:
        kwargs["allow_static_test"] = False
        super().__init__(*args, **kwargs)
        self._v8_config = v8_config
        self._v8_config_digest = CANONICAL_CONFIG_SHA256
        self._v8_initializing_load = False
        self._v8_current_device: str | None = None
        self._v8_tensor_identity_manifest: list[dict[str, Any]] = []
        self._v8_permitted_transition: tuple[str, str] | None = None
        self._v8_transfer_sequence = 0
        self.component_transfer_ledger: list[dict[str, Any]] = []
        self._v8_artifact_cleanup_records: list[dict[str, Any]] = []
        self._v8_artifact_cleanup_errors: list[str] = []

    def _require_policy(self) -> None:
        if self._v8_config_digest != CANONICAL_CONFIG_SHA256:
            raise V8ContractError("v8 live state config binding drift")
        load_canonical_config()
        verify_preserved_bytes(self._v8_config)
        if id(self.backend) != self._backend_object_id:
            raise V8ContractError("v8 live backend object identity drift")
        # The inherited v7 policy is still exact and immutable; only its
        # authoring-time static opt-in is replaced by the audited v8 live gate.
        thawed = v7._thaw(self._policy)
        v7.validate_canonical_config(thawed)
        payload = v7._canonical_bytes(thawed)
        if payload != self._policy_bytes or hashlib.sha256(payload).hexdigest() != self._policy_digest:
            raise V8ContractError("inherited immutable v7 state policy drift")

    def _model_snapshot(self, expected_device: str) -> dict[str, Any]:
        self._check_model_object()
        valid, devices = v7._all_on(
            self.model, tuple(self._p("required_components")), expected_device
        )
        if not valid:
            raise V8ContractError("model device evidence does not match the requested snapshot")
        condition_digest, condition_manifest = v7.condition_content_digest(self.model.conds)
        fingerprint, stable_manifest, identity_manifest = _component_snapshot_v8(
            self.model, tuple(self._p("required_components"))
        )
        if self._v8_initializing_load and self._v8_current_device is None:
            if condition_digest != self.condition_digest or condition_manifest != self.condition_manifest:
                raise V8ContractError("approved-reference conditioning drifted during v8 load")
            self.component_fingerprint = fingerprint
            self.component_manifest = stable_manifest
            self.model_generation = v7.sha256_text(
                f"{self.worker_instance_id}:{self.worker_pid}:{self._model_object_id}:"
                f"{self._backend_object_id}:{self._load_sequence}:{condition_digest}:"
                f"{fingerprint}:{v7.EXACT_REFERENCE_SHA256}"
            )
            self._v8_current_device = expected_device
            self._v8_tensor_identity_manifest = identity_manifest
        else:
            if (
                condition_digest != self.condition_digest
                or condition_manifest != self.condition_manifest
                or fingerprint != self.component_fingerprint
                or stable_manifest != self.component_manifest
            ):
                raise V8ContractError(
                    "model conditioning or complete component bytes/schema/object identity drifted"
                )
            transition = self._v8_permitted_transition
            if expected_device == self._v8_current_device:
                if identity_manifest != self._v8_tensor_identity_manifest:
                    raise V8ContractError(
                        "parameter/buffer object identity changed outside an owned device transfer"
                    )
            elif (
                transition is None
                or transition[0] != self._v8_current_device
                or transition[1] != expected_device
            ):
                raise V8ContractError("model device changed outside an exact owned transfer")
            else:
                before_identity = self._v8_tensor_identity_manifest
                replaced = _identity_replacement_count(before_identity, identity_manifest)
                self._v8_transfer_sequence += 1
                record = {
                    "transfer_sequence": self._v8_transfer_sequence,
                    "model_generation": self.model_generation,
                    "component_fingerprint": self.component_fingerprint,
                    "from_device": transition[0],
                    "to_device": transition[1],
                    "before_tensor_identity_sha256": canonical_json_sha256(before_identity),
                    "after_tensor_identity_sha256": canonical_json_sha256(identity_manifest),
                    "replaced_tensor_object_count": replaced,
                    "complete_component_bytes_unchanged": True,
                    "component_object_identities_unchanged": True,
                }
                record["record_sha256"] = canonical_json_sha256(record)
                self.component_transfer_ledger.append(record)
                self._v8_current_device = expected_device
                self._v8_tensor_identity_manifest = identity_manifest
        binding = self.backend.voice_model_binding(
            model=self.model,
            model_generation=self.model_generation,
            model_object_id=self._model_object_id,
            backend_object_id=self._backend_object_id,
            worker_pid=self.worker_pid,
        )
        if binding != {
            "same_object": True,
            "model_object_id": self._model_object_id,
            "backend_object_id": self._backend_object_id,
            "model_generation": self.model_generation,
            "worker_pid": self.worker_pid,
        }:
            raise V8ContractError("backend/exact model object binding drift")
        return devices

    def load_voice(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        self._v8_initializing_load = True
        self._v8_current_device = None
        self._v8_tensor_identity_manifest = []
        self._v8_transfer_sequence = 0
        self.component_transfer_ledger = []
        self._v8_artifact_cleanup_records = []
        self._v8_artifact_cleanup_errors = []
        try:
            result = super().load_voice(payload)
        finally:
            self._v8_initializing_load = False
        if result.get("success") is True:
            if (
                self._v8_current_device != "cuda"
                or result.get("component_fingerprint") != self.component_fingerprint
                or result.get("model_generation") != self.model_generation
            ):
                return self._dispatch_failure(
                    "load", V8ContractError("v8 stable component generation did not commit")
                )
        return result

    def _bounded_transfer(
        self, source: str, target: str, payload: Mapping[str, Any], operation: str
    ) -> dict[str, Any]:
        if self._v8_permitted_transition is not None:
            return self._dispatch_failure(
                operation, V8ContractError("nested component transfer is forbidden")
            )
        before_count = len(self.component_transfer_ledger)
        self._v8_permitted_transition = (source, target)
        try:
            result = (
                super().park_cpu(payload)
                if operation == "park"
                else super().resume_cuda(payload)
            )
        finally:
            self._v8_permitted_transition = None
        if result.get("success") is True:
            if (
                len(self.component_transfer_ledger) != before_count + 1
                or self.component_transfer_ledger[-1]["from_device"] != source
                or self.component_transfer_ledger[-1]["to_device"] != target
            ):
                return self._dispatch_failure(
                    operation, V8ContractError("exact component transfer ledger is absent")
                )
            result = {
                **result,
                "component_fingerprint": self.component_fingerprint,
                "component_transfer": dict(self.component_transfer_ledger[-1]),
            }
        return result

    def park_cpu(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self._bounded_transfer("cuda", "cpu", payload, "park")

    def resume_cuda(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self._bounded_transfer("cpu", "cuda", payload, "resume")

    def _clear_artifact(self) -> None:
        retained = self.retained_artifact
        if isinstance(retained, dict):
            record: dict[str, Any] = {
                "generation_id": retained.get("generation_id"),
                "artifact_sha256": retained.get("artifact_sha256"),
                "resolved_path": retained.get("resolved_path"),
                "deleted": False,
            }
            try:
                generation_id = retained.get("generation_id")
                artifact_sha = retained.get("artifact_sha256")
                if not is_sha256(generation_id) or not is_sha256(artifact_sha):
                    raise V8ContractError("retained artifact cleanup binding is invalid")
                raw = Path(str(retained.get("resolved_path") or ""))
                if not raw.is_absolute() or raw.is_symlink():
                    raise V8ContractError("retained artifact cleanup path is unsafe")
                runtime_root = (v7.PROJECT_ROOT / "RecoverySprint/runtime_cache").resolve()
                owned_root = (
                    v7.PROJECT_ROOT / str(self._p("owned_output_root"))
                ).resolve()
                owned_root.relative_to(runtime_root)
                path = raw.resolve(strict=False)
                path.relative_to(owned_root)
                if path.name != f"{generation_id}.wav":
                    raise V8ContractError("retained artifact cleanup filename is not exact")
                existed = path.exists()
                if existed:
                    if path.is_symlink() or sha256_file(path) != artifact_sha:
                        raise V8ContractError(
                            "retained artifact mutated; preserved for explicit diagnosis"
                        )
                    path.unlink()
                    if path.exists():
                        raise V8ContractError("retained artifact deletion did not complete")
                record["deleted"] = existed
                record["already_absent_before_cleanup"] = not existed
                record["absent_after_cleanup"] = not path.exists()
            except Exception as exc:
                error = f"{type(exc).__name__}:{exc}"
                record["error"] = error
                self._v8_artifact_cleanup_errors.append(error)
            self._v8_artifact_cleanup_records.append(record)
        self.retained_artifact = None

    def _cleanup(self, reason: str) -> dict[str, Any]:
        result = super()._cleanup(reason)
        errors = list(result.get("errors") or [])
        errors.extend(f"wav_cleanup:{item}" for item in self._v8_artifact_cleanup_errors)
        if errors:
            result["unloaded"] = False
            result["cleanup_debt"] = True
            result["errors"] = errors
            self.state = v7.WorkerState.CLEANUP_DEBT
        result["artifact_cleanup_records"] = [
            dict(item) for item in self._v8_artifact_cleanup_records
        ]
        self._v8_current_device = None
        self._v8_tensor_identity_manifest = []
        self._v8_permitted_transition = None
        return result


__all__ = [
    "PersistentWorkerV8",
    "V8LiveStateEngine",
    "_component_snapshot_v8",
]
