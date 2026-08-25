"""Bounded, non-activating local audition-audio queue."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import uuid
from pathlib import Path
from typing import Any

from .errors import ValidationError
from .models import JobState, SynthesisRequest
from .paths import PinnedDirectory, atomic_write_json_new, safe_component
from .runtime_resolver import ExactRuntimeVoiceResolver
from .voice_design import MAX_CANDIDATES, VoiceDesignEngine

QUEUE_SCHEMA = "kira.local-voice.candidate-audio-queue.v1"
MAX_AUDITION_CASES = 3
MAX_QUEUE_RECORD_BYTES = 512 * 1024
_SHA256 = __import__("re").compile(r"^[a-f0-9]{64}$")


def _is_reparse(path: Path) -> bool:
    info = path.lstat()
    attributes = getattr(info, "st_file_attributes", 0)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return path.is_symlink() or bool(attributes & reparse) or (
        hasattr(os.path, "isjunction") and os.path.isjunction(path)
    )


def _prepare_local_root(path: Path) -> Path:
    absolute = path.expanduser().absolute()
    text = str(absolute)
    if text.startswith("\\\\") or absolute.drive.startswith("\\\\"):
        raise ValidationError("candidate queue root must be on a local non-UNC path")

    def inspect_existing_ancestors() -> None:
        cursor = Path(absolute.anchor)
        for part in absolute.parts[1:]:
            cursor = cursor / part
            if cursor.exists() and _is_reparse(cursor):
                raise ValidationError("candidate queue root cannot traverse a link, junction, or reparse point")

    inspect_existing_ancestors()
    absolute.mkdir(parents=True, exist_ok=True)
    inspect_existing_ancestors()
    if absolute.resolve(strict=True) != absolute or _is_reparse(absolute):
        raise ValidationError("candidate queue root is not a stable local directory")
    return absolute


def _canonical_digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _regular_digest(path: Path, *, allowed_root: Path) -> str:
    root = allowed_root.resolve(strict=True)
    absolute = path.resolve(strict=True)
    try:
        absolute.relative_to(root)
    except ValueError as exc:
        raise ValidationError("audition artifact escapes the local service root") from exc
    before = absolute.lstat()
    attributes = getattr(before, "st_file_attributes", 0)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if absolute.is_symlink() or bool(attributes & reparse) or not stat.S_ISREG(before.st_mode):
        raise ValidationError("audition artifact is not an unlinked regular file")
    with absolute.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
        after_read = os.fstat(stream.fileno())
    after = absolute.lstat()
    identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
    if identity(before) != identity(opened) or identity(opened) != identity(after_read) or identity(opened) != identity(after):
        raise ValidationError("audition artifact changed while hashing")
    return digest.hexdigest()


class CandidateAudioQueue:
    """Submit exact resolved candidate specs and save append-only evidence."""

    def __init__(
        self,
        queue_root: Path,
        engine: VoiceDesignEngine,
        resolver: ExactRuntimeVoiceResolver,
        service: object,
    ):
        self.queue_root = _prepare_local_root(queue_root)
        self.receipt_root = self.queue_root / "receipts"
        self.receipt_root.mkdir(parents=True, exist_ok=True)
        self._root_pin = PinnedDirectory.capture(self.queue_root)
        self._receipt_pin = PinnedDirectory.capture(self.receipt_root)
        self.engine = engine
        self.resolver = resolver
        self.service = service

    def _assert_roots(self) -> None:
        self._root_pin.assert_unchanged()
        self._receipt_pin.assert_unchanged()

    @staticmethod
    def _audition_text(bundle: dict[str, Any]) -> str:
        cases = bundle.get("audition_cases")
        if not isinstance(cases, list) or not 1 <= len(cases) <= MAX_AUDITION_CASES:
            raise ValidationError("audition bundle must contain 1-3 exact audition cases")
        parts = []
        for item in cases:
            if not isinstance(item, dict) or not isinstance(item.get("case_id"), str) or not isinstance(item.get("text"), str):
                raise ValidationError("audition case is invalid")
            safe_component(item["case_id"], field="audition case_id")
            parts.append(item["text"].strip())
        text = "\n\n".join(parts)
        if not text:
            raise ValidationError("audition text is empty")
        return text

    @staticmethod
    def _verify_resolution(candidate: dict[str, Any], resolution: dict[str, Any]) -> dict[str, Any]:
        spec = resolution.get("candidate_spec")
        if not isinstance(spec, dict):
            raise ValidationError("runtime resolution omitted the exact candidate spec")
        delivery = candidate.get("delivery")
        attestation = candidate.get("source_attestation")
        expected = {
            "bundle_id": resolution.get("bundle_id"),
            "candidate_id": candidate.get("candidate_id"),
            "catalog_id": candidate.get("catalog_id"),
            "voice_id": candidate.get("backend_voice_id"),
            "language": candidate.get("language"),
            "language_provenance": candidate.get("language_provenance"),
            "speed": delivery.get("speed") if isinstance(delivery, dict) else None,
            "style": delivery.get("style") if isinstance(delivery, dict) else None,
            "shared_spec_sha256": candidate.get("shared_spec_sha256"),
            "source_attestation_sha256": (
                attestation.get("source_attestation_sha256") if isinstance(attestation, dict) else None
            ),
            "model_source": attestation.get("model_repo") if isinstance(attestation, dict) else None,
            "model_revision": attestation.get("model_revision") if isinstance(attestation, dict) else None,
            "license_id": candidate.get("license_id"),
        }
        if spec != expected or resolution.get("candidate_spec_sha256") != _canonical_digest(expected):
            raise ValidationError("runtime resolution differs from the immutable audition candidate")
        return spec

    def run_bundle(self, bundle_id: str, *, timeout_seconds: float = 120.0) -> dict[str, Any]:
        """Attempt each candidate once; never approve, select, bind, or activate."""

        self._assert_roots()
        if (
            not isinstance(timeout_seconds, (int, float))
            or isinstance(timeout_seconds, bool)
            or not 1 <= float(timeout_seconds) <= 600
        ):
            raise ValidationError("queue timeout_seconds must be between 1 and 600")
        bundle = self.engine._validated_bundle(bundle_id)
        candidates = bundle.get("candidates")
        if not isinstance(candidates, list) or not 1 <= len(candidates) <= MAX_CANDIDATES:
            raise ValidationError("bundle does not contain a bounded candidate audition set")
        text = self._audition_text(bundle)
        queue_id = f"cq-{uuid.uuid4().hex}"
        results: list[dict[str, Any]] = []

        for candidate in candidates:
            if not isinstance(candidate, dict):
                raise ValidationError("bundle candidate must be an object")
            candidate_id = safe_component(candidate.get("candidate_id"), field="candidate_id")
            resolution = self.resolver.resolve(bundle_id, candidate_id)
            if resolution.get("status") != "ready_for_local_audition_synthesis":
                results.append(
                    {
                        "candidate_id": candidate_id,
                        "status": "blocked_before_submission",
                        "resolution_sha256": _canonical_digest(resolution),
                        "blockers": list(resolution.get("blockers", [])),
                        "job_id": None,
                        "sample_path": None,
                        "sample_sha256": None,
                        "service_receipt_path": None,
                        "service_receipt_sha256": None,
                        "activation_performed": False,
                    }
                )
                continue

            spec = self._verify_resolution(candidate, resolution)
            output_name = f"aud-{candidate_id[-28:]}-{queue_id[-12:]}"
            request = SynthesisRequest(
                text=text,
                voice_id=spec["voice_id"],
                output_name=output_name,
                language=spec["language"],
                speed=spec["speed"],
                style=spec["style"],
                metadata={
                    "bundle_id": bundle_id,
                    "candidate_id": candidate_id,
                    "candidate_spec_sha256": resolution["candidate_spec_sha256"],
                    "shared_spec_sha256": spec["shared_spec_sha256"],
                    "queue_id": queue_id,
                },
            )
            try:
                submitted = self.service.submit(request, timeout_seconds=float(timeout_seconds))
                done = self.service.jobs.wait(submitted.job_id, float(timeout_seconds) + 5.0)
                job_id = safe_component(done.job_id, field="job_id")
                output_filename = (
                    safe_component(done.output_path, field="sample output filename")
                    if isinstance(done.output_path, str) else None
                )
                receipt_filename = (
                    safe_component(done.receipt_path, field="service receipt filename")
                    if isinstance(done.receipt_path, str) else None
                )
                item = {
                    "candidate_id": candidate_id,
                    "status": done.state.value,
                    "resolution_sha256": _canonical_digest(resolution),
                    "blockers": [],
                    "job_id": job_id,
                    "sample_path": output_filename,
                    "sample_sha256": None,
                    "service_receipt_path": receipt_filename,
                    "service_receipt_sha256": None,
                    "activation_performed": False,
                }
                if done.state is JobState.SUCCEEDED:
                    if not isinstance(done.output_path, str) or not isinstance(done.receipt_path, str):
                        raise ValidationError("successful local job omitted output or receipt")
                    output_name_safe = safe_component(done.output_path, field="sample output filename")
                    receipt_name_safe = safe_component(done.receipt_path, field="service receipt filename")
                    item["sample_sha256"] = _regular_digest(
                        self.service.outputs_root / output_name_safe,
                        allowed_root=self.service.outputs_root,
                    )
                    item["service_receipt_sha256"] = _regular_digest(
                        self.service.receipts_root / receipt_name_safe,
                        allowed_root=self.service.receipts_root,
                    )
                results.append(item)
            except Exception as exc:
                results.append(
                    {
                        "candidate_id": candidate_id,
                        "status": "submission_failed",
                        "resolution_sha256": _canonical_digest(resolution),
                        "blockers": [f"local_submission_error:{type(exc).__name__}"],
                        "job_id": None,
                        "sample_path": None,
                        "sample_sha256": None,
                        "service_receipt_path": None,
                        "service_receipt_sha256": None,
                        "activation_performed": False,
                    }
                )

        record: dict[str, Any] = {
            "schema": QUEUE_SCHEMA,
            "queue_id": queue_id,
            "bundle_id": bundle_id,
            "bundle_digest": _canonical_digest(bundle),
            "candidate_count": len(candidates),
            "audition_case_count": len(bundle["audition_cases"]),
            "results": results,
            "all_samples_ready": all(item["status"] == JobState.SUCCEEDED.value for item in results),
            "human_audition_required": True,
            "approval_performed": False,
            "selection_performed": False,
            "binding_performed": False,
            "activation_performed": False,
        }
        record["record_sha256"] = _canonical_digest(record)
        encoded = json.dumps(record, sort_keys=True, ensure_ascii=False).encode("utf-8")
        if len(encoded) > MAX_QUEUE_RECORD_BYTES:
            raise ValidationError("candidate audio queue record exceeds the storage bound")
        self._assert_roots()
        atomic_write_json_new(self.receipt_root / f"{queue_id}.json", record)
        return record

    def get_receipt(self, queue_id: str) -> dict[str, Any]:
        """Strictly verify an append-only queue receipt before it is used as evidence."""

        self._assert_roots()
        queue_id = safe_component(queue_id, field="queue_id")
        path = self.receipt_root / f"{queue_id}.json"
        if not path.exists() or _is_reparse(path):
            raise ValidationError("candidate queue receipt is missing or linked")
        info = path.stat(follow_symlinks=False)
        if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= MAX_QUEUE_RECORD_BYTES:
            raise ValidationError("candidate queue receipt is not a bounded regular file")
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            payload = stream.read(MAX_QUEUE_RECORD_BYTES + 1)
            after_read = os.fstat(stream.fileno())
        after = path.stat(follow_symlinks=False)
        identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
        if (
            len(payload) != opened.st_size
            or len(payload) > MAX_QUEUE_RECORD_BYTES
            or identity(info) != identity(opened)
            or identity(opened) != identity(after_read)
            or identity(opened) != identity(after)
        ):
            raise ValidationError("candidate queue receipt changed while reading")

        def reject_constant(value: str) -> object:
            raise ValidationError(f"non-finite queue receipt number is forbidden: {value}")

        def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in pairs:
                if key in result:
                    raise ValidationError(f"duplicate queue receipt key is forbidden: {key}")
                result[key] = value
            return result

        try:
            record = json.loads(
                payload.decode("utf-8"),
                object_pairs_hook=unique_object,
                parse_constant=reject_constant,
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValidationError("candidate queue receipt is not strict UTF-8 JSON") from exc
        if not isinstance(record, dict):
            raise ValidationError("candidate queue receipt must be an object")
        required = {
            "schema", "queue_id", "bundle_id", "bundle_digest", "candidate_count",
            "audition_case_count", "results", "all_samples_ready", "human_audition_required",
            "approval_performed", "selection_performed", "binding_performed",
            "activation_performed", "record_sha256",
        }
        if set(record) != required or record.get("schema") != QUEUE_SCHEMA or record.get("queue_id") != queue_id:
            raise ValidationError("candidate queue receipt schema or filename identity is invalid")
        claimed = record.get("record_sha256")
        unsigned = {key: value for key, value in record.items() if key != "record_sha256"}
        if not isinstance(claimed, str) or not _SHA256.fullmatch(claimed) or claimed != _canonical_digest(unsigned):
            raise ValidationError("candidate queue receipt canonical digest is invalid")
        results = record.get("results")
        if (
            not isinstance(results, list)
            or not 1 <= len(results) <= MAX_CANDIDATES
            or record.get("candidate_count") != len(results)
            or not isinstance(record.get("audition_case_count"), int)
            or not 1 <= record["audition_case_count"] <= MAX_AUDITION_CASES
        ):
            raise ValidationError("candidate queue receipt bounds are invalid")
        result_keys = {
            "candidate_id", "status", "resolution_sha256", "blockers", "job_id",
            "sample_path", "sample_sha256", "service_receipt_path",
            "service_receipt_sha256", "activation_performed",
        }
        for item in results:
            if not isinstance(item, dict) or set(item) != result_keys:
                raise ValidationError("candidate queue result schema is invalid")
            safe_component(item.get("candidate_id"), field="receipt candidate_id")
            if not isinstance(item.get("resolution_sha256"), str) or not _SHA256.fullmatch(item["resolution_sha256"]):
                raise ValidationError("candidate queue resolution digest is invalid")
            for field in ("job_id", "sample_path", "service_receipt_path"):
                if item[field] is not None:
                    safe_component(item[field], field=f"receipt {field}")
            for field in ("sample_sha256", "service_receipt_sha256"):
                if item[field] is not None and (not isinstance(item[field], str) or not _SHA256.fullmatch(item[field])):
                    raise ValidationError(f"candidate queue {field} is invalid")
            if not isinstance(item.get("blockers"), list) or not all(isinstance(value, str) for value in item["blockers"]):
                raise ValidationError("candidate queue blockers are invalid")
            if item.get("activation_performed") is not False:
                raise ValidationError("candidate queue result cannot claim activation")
            if item.get("status") == JobState.SUCCEEDED.value and (
                item.get("sample_sha256") is None or item.get("service_receipt_sha256") is None
            ):
                raise ValidationError("successful candidate queue result lacks artifact digests")
        if (
            record.get("all_samples_ready")
            != all(item.get("status") == JobState.SUCCEEDED.value for item in results)
            or record.get("human_audition_required") is not True
            or any(record.get(field) is not False for field in (
                "approval_performed", "selection_performed", "binding_performed", "activation_performed"
            ))
        ):
            raise ValidationError("candidate queue receipt approval or activation policy is invalid")
        return record
