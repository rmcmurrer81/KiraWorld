from __future__ import annotations

import ast
import hashlib
import json
import os
import sys
import threading
import types
from pathlib import Path

import pytest

import voice_v20_worker as v20


HERE = Path(__file__).resolve().parent
GIB = 1024**3


def h(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


class StepClock:
    def __init__(self) -> None:
        self.value = 1_000_000_000

    def __call__(self) -> int:
        self.value += 1_000_000
        return self.value


class MockTensor:
    def __init__(self, name: str, device: str = "cuda") -> None:
        self.name = name
        self.device = device
        self.shape = (2, 2)
        self.dtype = "float32"
        self.requires_grad = name.startswith("parameter")
        self.payload = (name + ":immutable-v20-fixture").encode("ascii")

    def to(self, device: str) -> "MockTensor":
        self.device = device
        return self

    def content_bytes(self) -> bytes:
        return bytes(self.payload)


class MockComponent:
    def __init__(self, name: str) -> None:
        self.name = name
        self.parameter = MockTensor(f"parameter:{name}")
        self.buffer = MockTensor(f"buffer:{name}")

    def named_parameters(self):
        return [("weight", self.parameter)]

    def named_buffers(self):
        return [("running", self.buffer)]

    def to(self, device: str) -> "MockComponent":
        self.parameter.to(device)
        self.buffer.to(device)
        return self


class MockConditions:
    def __init__(self) -> None:
        self.speaker = MockTensor("condition:speaker")
        self.prompt = {"embedding": MockTensor("condition:prompt")}

    def to(self, device: str) -> "MockConditions":
        self.speaker.to(device)
        self.prompt["embedding"].to(device)
        return self


class MockModel:
    def __init__(self) -> None:
        self.t3 = MockComponent("t3")
        self.s3gen = MockComponent("s3gen")
        self.ve = MockComponent("ve")
        self.conds = MockConditions()
        self.device = "cuda"


class MockBackend:
    def __init__(self, clock: StepClock) -> None:
        self.clock = clock
        self.model = None
        self.sample_sequence = 0
        self.load_calls = 0
        self.condition_calls = 0
        self.fixture_synthesis_calls = 0
        self.release_calls = 0
        self.resource_mutator = None

    def load_conditioned_generation(self, **kwargs):
        assert kwargs["profile_sha256"] == v20.EXACT_VOICE_PROFILE_SHA256
        assert kwargs["reference_sha256"] == v20.EXACT_VOICE_REFERENCE_SHA256
        assert kwargs["required_components"] == ["t3", "s3gen", "ve"]
        self.load_calls += 1
        self.condition_calls += 1
        self.model = MockModel()
        return {
            "model": self.model,
            "profile_sha256": v20.EXACT_VOICE_PROFILE_SHA256,
            "reference_sha256": v20.EXACT_VOICE_REFERENCE_SHA256,
            "load_count": self.load_calls,
            "conditioning_count": self.condition_calls,
            "route": "blackwell_gpu",
            "device": "cuda",
            "generic_voice_used": False,
            "sapi_voice_used": False,
            "fallback_used": False,
        }

    def sample_resources(self, **kwargs):
        self.sample_sequence += 1
        device = "none" if self.model is None else self.model.device
        value = {
            "schema": "kira.blackwell.voice_v20.resource_sample.v1",
            "sample_id": "",
            "sample_sequence": self.sample_sequence,
            "captured_monotonic_ns": self.clock.value,
            "worker_pid": kwargs["worker_pid"],
            "process_rss_bytes": 2 * GIB,
            "commit_used_bytes": 8 * GIB,
            "commit_limit_bytes": 32 * GIB,
            "available_physical_bytes": 16 * GIB,
            "total_physical_bytes": 32 * GIB,
            "cuda_allocated_bytes": 2 * GIB if device == "cuda" else 0,
            "cuda_reserved_bytes": 3 * GIB if device == "cuda" else 0,
            "cuda_free_bytes": 10 * GIB,
            "cuda_total_bytes": 16 * GIB,
            "cuda_device_name": v20.EXACT_CUDA_DEVICE_NAME,
            "compute_capability": [12, 0],
            "qwen_records": [],
            "voice_device": device,
        }
        if self.resource_mutator is not None:
            self.resource_mutator(value)
        value["sample_id"] = v20.canonical_sha256(
            {key: value[key] for key in sorted(v20.RESOURCE_KEYS - {"sample_id"})}
        )
        return value

    def qwen_absence(self, **kwargs):
        assert kwargs["phase"]
        return {
            "query_succeeded": True,
            "qwen_absent_proven": True,
            "qwen_records": [],
            "model_state_changed": False,
            "model": v20.EXACT_TEXT_MODEL,
            "digest": v20.EXACT_TEXT_MODEL_DIGEST,
        }

    def cuda_cache_cleanup(self):
        return {
            "cache_cleared": True,
            "synchronize_before": True,
            "empty_cache_called": True,
            "synchronize_after": True,
        }

    def synthesize_exact(self, **kwargs):
        self.fixture_synthesis_calls += 1
        first = self.clock.value + 1
        return {
            "schema": "kira.blackwell.voice_v20.fixture_synthesis_result.v1",
            "artifact_sha256": h("no-audio-fixture-artifact"),
            "text_sha256": kwargs["text_sha256"],
            "synthesis_id": kwargs["synthesis_id"],
            "route": "blackwell_gpu",
            "device": "cuda",
            "generic_voice_used": False,
            "sapi_voice_used": False,
            "fallback_used": False,
            "model_generation": kwargs["generation_id"],
            "component_fingerprint": kwargs["component_fingerprint"],
            "condition_digest": kwargs["condition_digest"],
            "first_sample_monotonic_ns": first,
            "audio_ready_monotonic_ns": first + 1,
            "playback_performed": False,
            "fixture_audio_created": False,
        }

    def release_generation(self, **kwargs):
        assert kwargs["reason"]
        self.release_calls += 1
        self.model = None
        return {
            "released": True,
            "owned_model_count": 0,
            "owned_condition_count": 0,
        }


def make_authority(clock: StepClock, maximum_turns: int = 4):
    return v20.author_fixture_authority(
        session_id=h("session"),
        owner_hash=h("owner"),
        ledger_receipt_sha256=h("ledger"),
        maximum_turns=maximum_turns,
        expires_monotonic_ns=clock.value + 100_000_000_000,
    )


def make_worker(maximum_turns: int = 4):
    clock = StepClock()
    backend = MockBackend(clock)
    worker = v20.RetainedGenerationWorkerV20.author_fixture(
        backend=backend,
        authority=make_authority(clock, maximum_turns),
        worker_source_sha256=v20.sha256_file(Path(v20.__file__)),
        now_ns=clock.__call__,
        worker_pid=os.getpid(),
    )
    return worker, backend, clock


def deadline(clock: StepClock) -> int:
    return clock.value + 10_000_000_000


def qwen_receipt(worker, turn_id: str, token_hash: str, request_sha256: str):
    value = {
        "schema": "kira.blackwell.voice_v20.qwen_completion_receipt.v1",
        "turn_id": turn_id,
        "model": v20.EXACT_TEXT_MODEL,
        "digest": v20.EXACT_TEXT_MODEL_DIGEST,
        "owner_hash": worker.authority["owner_hash"],
        "session_id": worker.authority["session_id"],
        "token_hash": token_hash,
        "request_sha256": request_sha256,
        "response_text_sha256": h("exact-public-response-words"),
        "load_started_ns": 1,
        "load_completed_ns": 2,
        "generation_started_ns": 3,
        "first_token_ns": 4,
        "generation_completed_ns": 5,
        "unload_started_ns": 6,
        "unload_completed_ns": 7,
        "keep_alive": 0,
        "qwen_absent_after": True,
        "voice_cuda_overlap": False,
        "receipt_sha256": "",
    }
    value["receipt_sha256"] = v20.canonical_sha256(
        {key: value[key] for key in sorted(v20.QWEN_RECEIPT_KEYS - {"receipt_sha256"})}
    )
    return value


def prepare_parked_worker(maximum_turns: int = 4):
    worker, backend, clock = make_worker(maximum_turns)
    worker.load_once(deadline_ns=deadline(clock))
    worker.park_for_qwen(reason="author fixture initial park", deadline_ns=deadline(clock))
    return worker, backend, clock


def test_live_candidate_is_unconditionally_refused() -> None:
    with pytest.raises(v20.V20NotAuthorized):
        v20.RetainedGenerationWorkerV20.live_candidate(object())


def test_author_fixture_authority_is_exact_default_off_and_bounded() -> None:
    clock = StepClock()
    value = make_authority(clock)
    assert value["execution_authorized"] is False
    assert value["model_gpu_audio_camera_authorized"] is False
    for bad in (True, 0, 5):
        mutated = dict(value)
        mutated["maximum_turns"] = bad
        with pytest.raises(v20.V20NotAuthorized):
            v20.validate_author_fixture_authority(mutated, now_ns=clock.value)


def test_complete_mock_state_machine_retains_one_exact_generation() -> None:
    worker, backend, clock = prepare_parked_worker(maximum_turns=1)
    original_model = worker.model
    original_components = tuple(getattr(original_model, name) for name in v20.REQUIRED_COMPONENTS)
    turn_id, token_hash, request_hash = h("turn-1"), h("token-1"), h("request-1")
    worker.enter_qwen_window(
        turn_id=turn_id,
        token_hash=token_hash,
        request_sha256=request_hash,
        deadline_ns=deadline(clock),
    )
    receipt = qwen_receipt(worker, turn_id, token_hash, request_hash)
    worker.complete_qwen_window(receipt=receipt, deadline_ns=deadline(clock))
    worker.restore_for_synthesis(deadline_ns=deadline(clock))
    result = worker.synthesize_fixture_and_park(
        text_sha256=receipt["response_text_sha256"],
        synthesis_id=h("synthesis-1"),
        deadline_ns=deadline(clock),
    )
    assert result["latency_improvement_proven"] is False
    assert worker.model is original_model
    assert tuple(getattr(worker.model, name) for name in v20.REQUIRED_COMPONENTS) == original_components
    assert backend.load_calls == backend.condition_calls == backend.fixture_synthesis_calls == 1
    assert len(worker.transfer_ledger) == 3
    assert [row["to_device"] for row in worker.transfer_ledger] == ["cpu", "cuda", "cpu"]
    assert all(row["complete_component_and_condition_bytes_unchanged"] for row in worker.transfer_ledger)
    outcome = worker.close_fixture(reason="mock suite complete", deadline_ns=deadline(clock))
    assert outcome["status"] == "PASS_MOCK_CONTROL_ONLY"
    assert outcome["model_calls"] == outcome["gpu_calls"] == outcome["synthesis_calls"] == 0
    assert outcome["audio_created"] is outcome["latency_improvement_proven"] is False
    assert worker.state is v20.WorkerState.TERMINAL


def test_content_drift_fails_closed_and_releases_fixture() -> None:
    worker, backend, clock = make_worker()
    worker.load_once(deadline_ns=deadline(clock))
    worker.model.conds.speaker.payload += b":drift"
    with pytest.raises(v20.V20ContractError, match="content drift"):
        worker.park_for_qwen(reason="must reject drift", deadline_ns=deadline(clock))
    assert worker.state is v20.WorkerState.TERMINAL
    assert backend.release_calls == 1
    assert worker.model is None


def test_component_object_replacement_is_detected() -> None:
    worker, backend, clock = make_worker()
    worker.load_once(deadline_ns=deadline(clock))
    worker.model.t3 = MockComponent("t3")
    with pytest.raises(v20.V20ContractError, match="content drift"):
        worker.park_for_qwen(reason="must reject replacement", deadline_ns=deadline(clock))
    assert worker.state is v20.WorkerState.TERMINAL
    assert backend.release_calls == 1


def test_backend_callable_substitution_is_detected_before_use() -> None:
    worker, _backend, _clock = make_worker()
    original = MockBackend.sample_resources

    def substituted(self, **kwargs):
        return original(self, **kwargs)

    try:
        MockBackend.sample_resources = substituted
        with pytest.raises(v20.V20ContractError, match="backend callable drift"):
            worker.status()
    finally:
        MockBackend.sample_resources = original


def test_backend_module_object_substitution_is_detected() -> None:
    worker, _backend, _clock = make_worker()
    module_name = MockBackend.__module__
    original = sys.modules[module_name]
    try:
        sys.modules[module_name] = types.ModuleType(module_name)
        with pytest.raises(v20.V20ContractError, match="backend object/class/module drift"):
            worker.status()
    finally:
        sys.modules[module_name] = original


def test_control_callable_substitution_is_detected() -> None:
    worker, _backend, _clock = make_worker()
    original = v20.canonical_sha256

    def substituted(value):
        return original(value)

    try:
        v20.canonical_sha256 = substituted
        with pytest.raises(v20.V20ContractError, match="control callable drift"):
            worker.status()
    finally:
        v20.canonical_sha256 = original


def test_worker_control_method_descriptor_substitution_is_detected() -> None:
    worker, _backend, _clock = make_worker()
    original = v20.RetainedGenerationWorkerV20._preflight

    def substituted(self, **kwargs):
        return original(self, **kwargs)

    try:
        v20.RetainedGenerationWorkerV20._preflight = substituted
        with pytest.raises(v20.V20ContractError, match="worker method descriptor drift"):
            worker.status()
    finally:
        v20.RetainedGenerationWorkerV20._preflight = original


def valid_resource_sample(now_ns: int, worker_pid: int):
    clock = StepClock()
    clock.value = now_ns
    backend = MockBackend(clock)
    return backend.sample_resources(worker_pid=worker_pid, label="direct validator")


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("sample_sequence", True),
        ("captured_monotonic_ns", 2_000_000_001),
        ("process_rss_bytes", 0),
        ("commit_used_bytes", 33 * GIB),
        ("available_physical_bytes", 33 * GIB),
        ("cuda_free_bytes", 17 * GIB),
        ("cuda_device_name", "substitute GPU"),
        ("compute_capability", [8, 9]),
        ("qwen_records", [{"model": "other", "digest": h("other")}]),
        ("voice_device", "gpu"),
    ],
)
def test_resource_sample_rejects_wrong_types_ranges_and_identity(field, bad_value) -> None:
    now_ns = 2_000_000_000
    worker_pid = 4242
    value = valid_resource_sample(now_ns, worker_pid)
    value[field] = bad_value
    value["sample_id"] = v20.canonical_sha256(
        {key: value[key] for key in sorted(v20.RESOURCE_KEYS - {"sample_id"})}
    )
    with pytest.raises(v20.V20ContractError):
        v20.validate_resource_sample(
            value,
            worker_pid=worker_pid,
            minimum_sequence=1,
            now_ns=now_ns,
        )


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("keep_alive", 1),
        ("keep_alive", False),
        ("qwen_absent_after", 1),
        ("voice_cuda_overlap", True),
        ("model", "llama"),
        ("load_completed_ns", 8),
        ("first_token_ns", 3),
        ("response_text_sha256", "not-a-hash"),
    ],
)
def test_qwen_receipt_rejects_fallback_overlap_type_and_order(field, bad_value) -> None:
    worker, _backend, _clock = make_worker()
    turn_id, token_hash, request_hash = h("turn"), h("token"), h("request")
    value = qwen_receipt(worker, turn_id, token_hash, request_hash)
    value[field] = bad_value
    value["receipt_sha256"] = v20.canonical_sha256(
        {key: value[key] for key in sorted(v20.QWEN_RECEIPT_KEYS - {"receipt_sha256"})}
    )
    with pytest.raises(v20.V20ContractError):
        v20.validate_qwen_completion_receipt(
            value,
            turn_id=turn_id,
            owner_hash=worker.authority["owner_hash"],
            session_id=worker.authority["session_id"],
        )


def test_expired_deadline_and_cancelled_operation_fail_closed() -> None:
    worker, backend, clock = make_worker()
    cancelled = threading.Event()
    cancelled.set()
    with pytest.raises(v20.V20ContractError, match="cancelled"):
        worker.load_once(deadline_ns=deadline(clock), cancel_event=cancelled)
    assert worker.state is v20.WorkerState.TERMINAL
    assert backend.release_calls == 1


def test_worker_source_has_no_runtime_monkeypatch_or_live_dependency_imports() -> None:
    source = (HERE / "voice_v20_worker.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert imported.isdisjoint({"torch", "chatterbox", "ollama", "cv2", "sounddevice", "pyaudio"})
    assert "importlib" not in source
    assert "subprocess" not in imported


def test_native_supervisor_has_fail_closed_windows_boundaries() -> None:
    source = (HERE / "voice_v20_native_supervisor.c").read_text(encoding="utf-8")
    for token in (
        "CREATE_SUSPENDED",
        "PROC_THREAD_ATTRIBUTE_HANDLE_LIST",
        "JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE",
        "JOB_OBJECT_LIMIT_JOB_MEMORY",
        "AssignProcessToJobObject",
        "IsProcessInJob",
        "ResumeThread",
        "FILE_FLAG_OPEN_REPARSE_POINT",
        "GetFileInformationByHandleEx",
        "BY_HANDLE_FILE_INFORMATION",
        "GetFinalPathNameByHandleW",
        "GetSecurityInfo",
        "CREATE_NEW",
        "FILE_SHARE_READ",
        "BCryptHashData",
        "FlushFileBuffers",
    ):
        assert token in source
    assert "V20_REFUSAL_EXIT" in source
    assert "author source has no execution authority" in source


def test_matched_schema_retains_exact_v19_cardinalities() -> None:
    schema = json.loads((HERE / "MATCHED_EXPERIMENT_SCHEMA.json").read_text(encoding="utf-8"))
    assert schema["status"] == "SCHEMA_ONLY_NON_EXECUTABLE_NO_MEASUREMENTS"
    assert schema["execution_authority"] == "NONE"
    assert schema["live_measurements_present"] is False
    assert len(schema["conditions"]) == 4
    assert len(schema["required_monotonic_timestamps"]) == 51
    assert len(schema["required_metadata"]) == 42
    assert len(schema["required_derived_durations"]) == 30
    assert len(schema["ordering_requirements"]) == 15
    assert "audio_device_first_sample" in schema["v20_required_timestamps_additions"]
    assert "owner_heard_onset_optional" in schema["v20_required_metadata_additions"]
    assert "person_spec_sha256" in schema["v20_required_metadata_additions"]
    assert schema["voice_provenance_contract"]["windows_voice_may_be_labeled_historical_authentic"] is False
    assert schema["success_rule"]["requires_lower_median"] is True
    assert schema["success_rule"]["requires_lower_worst_case"] is True
    assert schema["success_rule"]["one_faster_sample_is_success"] is False
