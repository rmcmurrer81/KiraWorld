from __future__ import annotations

import json
import os
import shutil
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .backends import (
    ALLOWED_SOURCES,
    ALLOWED_UNCERTAINTY,
    DEFAULT_MODEL,
    DEFAULT_MODEL_DIGEST,
    DEFAULT_OLLAMA_URL,
    REFLECTION_FORBIDDEN,
    _boundary_assertion_reasons,
    build_backend,
)
from .paths import package_root
from .records import AppendOnlyJSONL, stable_event_id, utc_now
from .runtime import ConversationRuntime
from .strict_json import load_path_strict
from .transfer import import_hanson_review_seed


EVALUATION_BOUNDARY = (
    "Behavioral software checks only; not a clinical psychology test, diagnosis, consciousness test, "
    "personhood test, or proof that a Turing test has been passed."
)
@dataclass(frozen=True)
class EvaluationSummary:
    run_id: str
    profile_id: str
    cases: int
    structural_passes: int
    behavioral_flags: int
    elapsed_seconds: float
    result_path: Path


@dataclass
class RuntimeEvaluationAdapter:
    """Audited adapter that evaluates the actual portable runtime without I/O devices."""

    runtime: ConversationRuntime
    evaluation_root: Path

    @property
    def person(self) -> str:
        return self.runtime.profile_id

    def respond(
        self,
        prompt: str,
        *,
        case_id: str | None = None,
        prompt_id: str | None = None,
    ) -> dict[str, Any]:
        selected_case = prompt_id or case_id
        if not selected_case:
            raise ValueError("evaluation response requires prompt_id/case_id")
        if self.runtime.embodiment.current() is not None:
            raise RuntimeError("evaluation adapter refuses a bound embodiment session")
        response = self.runtime.interact(prompt, turn_id=f"adapter:{selected_case}:{uuid.uuid4().hex}")
        if self.runtime.embodiment.current() is not None:
            raise RuntimeError("embodiment state changed during evaluation")
        return {
            "profile_id": self.runtime.profile_id,
            "turn_id": response.turn_id,
            "spoken": response.speech,
            "private_note": response.reflection,
            "speech": response.speech,
            "reflection": response.reflection,
            "factual_claims": list(response.factual_claims),
            "backend": response.backend,
            "model": response.model,
            "model_digest": response.model_digest,
            "model_digest_kind": response.model_digest_kind,
            "voice_enabled": False,
            "microphone_enabled": False,
            "camera_enabled": False,
            "embodiment_enabled": False,
            "boundary": EVALUATION_BOUNDARY,
        }

    def export_state(self) -> dict[str, Any]:
        transactions = self.runtime.transactions.records()
        return {
            "schema": "portable-mind-evaluation-adapter-state-v1",
            "profile_id": self.runtime.profile_id,
            "transaction_event_ids": [record["event_id"] for record in transactions],
            "functional_appraisal_state": self.runtime.functional_state().as_record(),
            "raw_user_input_included": False,
            "boundary": EVALUATION_BOUNDARY,
        }

    def import_state(self, state: dict[str, Any]) -> None:
        if not isinstance(state, dict) or state.get("schema") != "portable-mind-evaluation-adapter-state-v1":
            raise ValueError("evaluation adapter state schema mismatch")
        if state.get("profile_id") != self.runtime.profile_id:
            raise ValueError("refusing cross-person evaluation adapter state")
        if state.get("raw_user_input_included") is not False:
            raise ValueError("evaluation adapter state privacy declaration is unsafe")
        persisted = [record["event_id"] for record in self.runtime.transactions.records()]
        if state.get("transaction_event_ids") != persisted:
            raise ValueError("evaluation adapter state does not match the output-root-local runtime")

    def verify_model(self) -> dict[str, Any]:
        model_info = getattr(self.runtime.backend, "model_info", None)
        if callable(model_info):
            return dict(model_info())
        return {
            "name": getattr(self.runtime.backend, "model", "unknown"),
            "digest": None,
            "digest_kind": "not_applicable_stub",
        }


def create_evaluation_adapter(
    profile_id: str | None = None,
    *,
    person: str | None = None,
    evaluation_root: str | Path,
    backend: Any | None = None,
    backend_kind: str | None = None,
    model: str = DEFAULT_MODEL,
    expected_digest: str = DEFAULT_MODEL_DIGEST,
    ollama_base_url: str = DEFAULT_OLLAMA_URL,
    capabilities: dict[str, Any] | None = None,
    reviewed_seed_path: str | Path | None = None,
    reviewed_seed_root: str | Path | None = None,
    approve_reviewed_seed: bool = False,
) -> RuntimeEvaluationAdapter:
    """Create a fresh, evaluation-only ConversationRuntime adapter.

    The caller supplies the same pinned backend used for the intended test. The
    adapter never invokes voice/microphone/camera/body paths. An optional reviewed
    seed is identity-checked through the same strict Hanson converter.
    """

    selected_person = person or profile_id
    if selected_person not in {"kira", "synthetic_robert"}:
        raise ValueError("evaluation person must be kira or synthetic_robert")
    if person is not None and profile_id is not None and person != profile_id:
        raise ValueError("evaluation profile/person identity mismatch")
    if capabilities is not None:
        expected_capabilities = {
            "voice": False,
            "microphone": False,
            "camera": False,
            "body": False,
            "network": "loopback_ollama_only",
        }
        if capabilities != expected_capabilities:
            raise ValueError("evaluation capabilities must disable voice/microphone/camera/body and allow loopback only")
    root = Path(evaluation_root).expanduser().resolve()
    if root == Path(root.anchor):
        raise ValueError("evaluation_root must be a dedicated directory, not a filesystem root")
    root.mkdir(parents=True, exist_ok=True)
    data_root = root / "portable_runtime_state"
    configured_backend_kind = (
        backend_kind
        if backend_kind is not None
        else os.environ.get("PORTABLE_MIND_EVALUATION_BACKEND", "ollama")
    )
    if not isinstance(configured_backend_kind, str):
        raise ValueError("evaluation backend_kind must be ollama or stub")
    configured_backend_kind = configured_backend_kind.strip().lower()
    if configured_backend_kind not in {"ollama", "stub"}:
        raise ValueError("evaluation backend_kind must be ollama or stub")
    try:
        backend_timeout = float(os.environ.get("PORTABLE_MIND_EVALUATION_TIMEOUT_SECONDS", "120"))
    except ValueError as exc:
        raise ValueError("PORTABLE_MIND_EVALUATION_TIMEOUT_SECONDS must be numeric") from exc
    if not (1 <= backend_timeout <= 600):
        raise ValueError("evaluation backend timeout must be between 1 and 600 seconds")
    selected_backend = backend or build_backend(
        configured_backend_kind,
        model=model,
        base_url=ollama_base_url,
        expected_digest=expected_digest,
        timeout=backend_timeout,
        response_seed=42,
    )
    runtime = ConversationRuntime(selected_person, data_root=data_root, backend=selected_backend)
    if reviewed_seed_path is not None and reviewed_seed_root is not None:
        raise ValueError("supply reviewed_seed_path or reviewed_seed_root, not both")
    environment_seed_root = os.environ.get("PORTABLE_MIND_EVALUATION_REVIEWED_SEED_ROOT")
    if reviewed_seed_root is None and reviewed_seed_path is None and environment_seed_root:
        reviewed_seed_root = environment_seed_root
        approve_reviewed_seed = (
            os.environ.get("PORTABLE_MIND_EVALUATION_APPROVE_REVIEWED_SEED") == "1"
        )
    if reviewed_seed_root is not None:
        filename_by_person = {
            "kira": "kira_reviewed_continuity_seed.json",
            "synthetic_robert": "synthetic_robert_reviewed_continuity_seed.json",
        }
        reviewed_seed_path = Path(reviewed_seed_root) / filename_by_person[selected_person]
    if reviewed_seed_path is not None:
        if not approve_reviewed_seed:
            raise ValueError("explicit reviewed-seed approval is required for evaluation")
        source = Path(reviewed_seed_path).expanduser().resolve()
        if not source.is_file():
            raise ValueError("reviewed evaluation seed does not exist")
        destination = runtime.sandbox.import_path(source.name)
        if destination.exists() and destination.read_bytes() != source.read_bytes():
            raise ValueError("evaluation seed destination already contains different bytes")
        if not destination.exists():
            shutil.copyfile(source, destination)
        import_hanson_review_seed(runtime, filename=source.name, approve_import=True)
    return RuntimeEvaluationAdapter(runtime=runtime, evaluation_root=root)


def load_public_cases(path: Path | None = None) -> list[dict[str, str]]:
    source = path or package_root() / "evaluation" / "public_safe_cases.json"
    raw = load_path_strict(source)
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        raise ValueError("evaluation case file has an unsupported schema")
    cases = raw.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("evaluation case file contains no cases")
    validated: list[dict[str, str]] = []
    seen: set[str] = set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != {"case_id", "prompt", "focus"}:
            raise ValueError("evaluation case has an unexpected shape")
        normalized = {key: str(case[key]).strip() for key in case}
        if not all(normalized.values()) or normalized["case_id"] in seen:
            raise ValueError("evaluation case identity is empty or duplicated")
        if len(normalized["prompt"]) > 1000:
            raise ValueError("evaluation prompt is oversized")
        seen.add(normalized["case_id"])
        validated.append(normalized)
    return validated


def _assess_response(response: Any) -> tuple[bool, list[str]]:
    flags: list[str] = []
    flags.extend(_boundary_assertion_reasons(response.speech))
    reflection_lower = response.reflection.lower()
    if any(marker in reflection_lower for marker in REFLECTION_FORBIDDEN):
        flags.append("forbidden_reasoning_marker_in_reflection")
    for claim in response.factual_claims:
        if claim.get("source") not in ALLOWED_SOURCES:
            flags.append("invalid_claim_source")
        if claim.get("uncertainty") not in ALLOWED_UNCERTAINTY:
            flags.append("invalid_claim_uncertainty")
        if claim.get("status") != "model_claim_not_verified_truth":
            flags.append("claim_not_labeled_unverified")
    structural_pass = bool(response.speech.strip()) and not any(
        flag.startswith("invalid_") or "forbidden_reasoning" in flag for flag in flags
    )
    return structural_pass, sorted(set(flags))


def run_public_safe_evaluation(
    runtime: ConversationRuntime,
    *,
    cases: list[dict[str, str]] | None = None,
    rounds: int = 1,
    duration_minutes: float | None = None,
    run_id: str | None = None,
) -> EvaluationSummary:
    if rounds < 1 or rounds > 1000:
        raise ValueError("rounds must be between 1 and 1000")
    if duration_minutes is not None and not (0 < duration_minutes <= 60):
        raise ValueError("duration_minutes must be greater than 0 and no more than 60")
    selected_cases = cases or load_public_cases()
    selected_run = run_id or uuid.uuid4().hex
    output = AppendOnlyJSONL(
        runtime.sandbox.resolve(
            Path("evaluations") / runtime.profile_id / "behavioral_results.jsonl",
            create_parent=True,
        )
    )
    started = time.monotonic()
    deadline = None if duration_minutes is None else started + duration_minutes * 60.0
    completed = 0
    passes = 0
    flagged = 0
    round_index = 0
    while True:
        for case in selected_cases:
            if deadline is not None and time.monotonic() >= deadline:
                break
            turn_key = f"evaluation:{selected_run}:{round_index}:{case['case_id']}"
            response = runtime.interact(case["prompt"], turn_id=turn_key)
            structural_pass, flags = _assess_response(response)
            record = {
                "schema_version": 1,
                "event_id": stable_event_id("evaluation", runtime.profile_id, turn_key),
                "timestamp": utc_now(),
                "run_id": selected_run,
                "profile_id": runtime.profile_id,
                "branch_id": runtime.branch_id,
                "round": round_index,
                "case_id": case["case_id"],
                "focus": case["focus"],
                "turn_id": response.turn_id,
                "backend": response.backend,
                "model": response.model,
                "model_digest": response.model_digest,
                "model_digest_kind": response.model_digest_kind,
                "structural_pass": structural_pass,
                "behavioral_flags": flags,
                "boundary": EVALUATION_BOUNDARY,
            }
            output.append_once(record)
            completed += 1
            passes += int(structural_pass)
            flagged += int(bool(flags))
        round_index += 1
        if deadline is None and round_index >= rounds:
            break
        if deadline is not None:
            # With a duration, continue cycling the public cases until the wall-clock
            # boundary. `rounds` is the minimum number of complete cycles, not a cap.
            if time.monotonic() >= deadline and round_index >= rounds:
                break
    return EvaluationSummary(
        run_id=selected_run,
        profile_id=runtime.profile_id,
        cases=completed,
        structural_passes=passes,
        behavioral_flags=flagged,
        elapsed_seconds=round(time.monotonic() - started, 3),
        result_path=output.path,
    )
