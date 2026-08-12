"""Signed, one-use static trust boundary for TemporaryAI Creator quality V4.

V4 is an append-only successor to the independently rejected V3 bytes.  It
retains V3's strict evidence validators, but no caller-created authority or
prepared object crosses the V4 API.  A separately controlled parent must sign
one exact, short-lived authorization envelope with Ed25519.  The envelope is
bound to the execution root, exact V3/V4/CLI code hashes, authority roots,
owner/request/evaluation identities, nonce, expiry, and one output namespace.

This module never signs an envelope.  It contains public verification keys
only.  The production signing key is not stored in this repository.  The
disposable unit-test signer is cryptographically scoped to a uniquely named
directory directly below the operating-system temporary directory, so it
cannot authorize the real project tree.

No model, GPU, voice, body, avatar, Blender, browser, activation, assignment,
publication, or runtime registration is performed here.
"""

from __future__ import annotations

import base64
import copy
import datetime as dt
import hashlib
import json
import os
import re
import secrets
import stat
import tempfile
from pathlib import Path
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from Core import temporary_ai_creator_quality_v3 as _v3


SCHEMA_VERSION = 4
CREATION_ENVELOPE_KIND = "temporary_ai_parent_creation_authorization_envelope_v4"
EVALUATION_ENVELOPE_KIND = "temporary_ai_parent_evaluation_authorization_envelope_v4"
CREATION_RESULT_KIND = "temporary_ai_creator_quality_record_v4"
EVALUATION_RESULT_KIND = "temporary_ai_expert_static_evaluation_result_v4"
HEAD_KIND = "temporary_ai_quality_head_v4"
OUTCOME_KIND = "temporary_ai_signed_authorization_outcome_v4"
CONSUMPTION_KIND = "temporary_ai_signed_authorization_consumption_v4"
PRIVATE_STATUS = "PRIVATE_INACTIVE_UNASSIGNED_STATIC_ONLY"
READY_STATUS = "V4_STATIC_EVIDENCE_READY_PRIVATE_INACTIVE_UNASSIGNED"
STATIC_EVALUATION_STATUS = "STATIC_RESPONSE_EVIDENCE_VALIDATED_NOT_LIVE_MODEL_ACCEPTANCE"

EXACT_QWEN_MODEL = _v3.EXACT_QWEN_MODEL
EXACT_QWEN_DIGEST = _v3.EXACT_QWEN_DIGEST
V3_CORE_SHA256 = "bd915c1a0d77268337ef3b22b68273a8c900629a910e9adc0d4087d63f37fd50"
V3_REJECTION_AUDIT_SHA256 = "2caa7161c79fba93447c4a9ef0dea96441edc70883f7457c7a38cd610a8ca45e"

SIGNATURE_ALGORITHM = "ed25519"
PRODUCTION_SIGNER_KEY_ID = "temporary_ai_parent_signer_v4_20260810"
TEST_SIGNER_KEY_ID = "temporary_ai_v4_disposable_temp_root_test_signer"
PRODUCTION_PUBLIC_KEY_B64 = "qejiz2al0/i6EILY8sCY0WHbjclVhY8bdqrUt+rFSKE="
# The corresponding test private seed may appear only in the hostile test.
# Its scope check below forbids every root except a disposable OS-temp child.
TEST_PUBLIC_KEY_B64 = "rVRvX02c23ojyjv2c7e38OvWXfts1MZrvYw7kC8cE4M="
TEST_ROOT_PREFIX = "kira_tempai_v4_test_"

CONTROL_ROOT = "TemporaryAI/quality_v4_control"
CONSUMPTION_NAMESPACE = f"{CONTROL_ROOT}/consumed"
EXECUTION_CLAIM_NAMESPACE = f"{CONTROL_ROOT}/execution_claims"
AUDIT_NAMESPACE = f"{CONTROL_ROOT}/audit"
ENVELOPE_NAMESPACE = "TemporaryAI/quality_v4_parent_authority/envelopes"
MAX_AUTHORIZATION_SECONDS = 15 * 60

ID_RE = re.compile(r"^[a-z0-9][a-z0-9_]{2,79}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
NONCE_RE = re.compile(r"^[0-9a-f]{64}$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
BASE64_RE = re.compile(r"^[A-Za-z0-9+/]+={0,2}$")

ENVELOPE_KEYS = (
    "schema_version", "record_kind", "authorization_id", "operation",
    "nonce", "signer_key_id", "signature_algorithm",
    "execution_root_sha256", "authority_id", "owner_id", "request_id",
    "evaluation_id", "authority_root_relative", "authority_root_sha256",
    "evaluation_root_relative", "evaluation_root_sha256",
    "output_namespace", "head_namespace", "quality_record_relative",
    "quality_record_sha256", "creation_authorization_sha256",
    "consumption_namespace", "audit_namespace", "issued_at_utc",
    "expires_at_utc", "v3_core_sha256", "v4_core_sha256",
    "v4_cli_sha256", "signature_base64",
)
CONSUMPTION_KEYS = (
    "schema_version", "record_kind", "authorization_id", "operation", "nonce",
    "owner_id", "request_id", "evaluation_id", "envelope_relative",
    "envelope_sha256", "output_namespace", "consumed_at_utc", "lifecycle",
)


class QualityV4Error(ValueError):
    """A signed V4 authorization, replay, or evidence boundary failed."""


def canonical_json_bytes(value: Any) -> bytes:
    return _v3.canonical_json_bytes(value)


def canonical_sha256(value: Any) -> str:
    return _v3.canonical_sha256(value)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def private_lifecycle() -> dict[str, Any]:
    return copy.deepcopy(_v3.private_lifecycle())


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or ID_RE.fullmatch(value) is None:
        raise QualityV4Error(f"{label}: canonical identifier required")
    return value


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or SHA_RE.fullmatch(value) is None:
        raise QualityV4Error(f"{label}: lowercase SHA-256 required")
    return value


def _utc(value: Any, label: str) -> dt.datetime:
    if not isinstance(value, str) or UTC_RE.fullmatch(value) is None:
        raise QualityV4Error(f"{label}: exact second-precision UTC Z required")
    try:
        return dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise QualityV4Error(f"{label}: invalid UTC timestamp") from exc


def _canonical_relative(value: Any, label: str, *, allow_empty: bool = False) -> str:
    if allow_empty and value == "":
        return ""
    try:
        return _v3._canonical_relative(value, label)
    except Exception as exc:
        raise QualityV4Error(str(exc)) from exc


def _exact_keys(value: Mapping[str, Any], expected: tuple[str, ...], label: str) -> None:
    if set(value) != set(expected):
        raise QualityV4Error(
            f"{label}: exact schema mismatch missing={sorted(set(expected)-set(value))} "
            f"extra={sorted(set(value)-set(expected))}"
        )


def _decode_canonical(raw: bytes, label: str) -> dict[str, Any]:
    try:
        return _v3._decode_canonical_json(raw, label=label)
    except Exception as exc:
        raise QualityV4Error(str(exc)) from exc


def _normalized_root_hash(root: Path) -> str:
    try:
        real = _v3._validated_real_root(root)
    except Exception as exc:
        raise QualityV4Error(str(exc)) from exc
    spelling = os.path.normcase(os.path.normpath(str(real)))
    return sha256_bytes(spelling.encode("utf-8"))


def _is_disposable_test_root(root: Path) -> bool:
    absolute = Path(os.path.abspath(os.fspath(root)))
    temp = Path(os.path.abspath(tempfile.gettempdir()))
    return (
        os.path.normcase(str(absolute.parent)) == os.path.normcase(str(temp))
        and absolute.name.startswith(TEST_ROOT_PREFIX)
        and len(absolute.name) >= len(TEST_ROOT_PREFIX) + 8
    )


def _public_key_for(signer_key_id: str, execution_root: Path) -> bytes:
    if signer_key_id == PRODUCTION_SIGNER_KEY_ID:
        return base64.b64decode(PRODUCTION_PUBLIC_KEY_B64, validate=True)
    if signer_key_id == TEST_SIGNER_KEY_ID:
        if not _is_disposable_test_root(execution_root):
            raise QualityV4Error("disposable test signer cannot authorize this execution root")
        return base64.b64decode(TEST_PUBLIC_KEY_B64, validate=True)
    raise QualityV4Error("untrusted V4 parent signer key ID")


def _signature_payload(envelope: Mapping[str, Any]) -> bytes:
    unsigned = dict(envelope)
    unsigned.pop("signature_base64", None)
    return canonical_json_bytes(unsigned)


def _verify_signature(envelope: Mapping[str, Any], execution_root: Path) -> None:
    if envelope["signature_algorithm"] != SIGNATURE_ALGORITHM:
        raise QualityV4Error("only exact Ed25519 parent signatures are accepted")
    signature_text = envelope["signature_base64"]
    if not isinstance(signature_text, str) or BASE64_RE.fullmatch(signature_text) is None:
        raise QualityV4Error("canonical base64 signature required")
    try:
        signature = base64.b64decode(signature_text, validate=True)
    except Exception as exc:
        raise QualityV4Error("invalid base64 signature") from exc
    if len(signature) != 64 or base64.b64encode(signature).decode("ascii") != signature_text:
        raise QualityV4Error("exact canonical Ed25519 signature bytes required")
    public_key = _public_key_for(envelope["signer_key_id"], execution_root)
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(
            signature, _signature_payload(envelope)
        )
    except (InvalidSignature, ValueError) as exc:
        raise QualityV4Error("parent envelope signature verification failed") from exc


def _code_hashes() -> dict[str, str]:
    code_root = Path(__file__).resolve().parents[1]
    core = Path(__file__).resolve()
    v3 = code_root / "Core" / "temporary_ai_creator_quality_v3.py"
    cli = code_root / "tools" / "create_temporary_ai_candidate_quality_v4.py"
    if core != code_root / "Core" / "temporary_ai_creator_quality_v4.py":
        raise QualityV4Error("V4 core imported through an unexpected path")
    if not v3.is_file() or not cli.is_file():
        raise QualityV4Error("exact V3 core and V4 CLI files are required")
    result = {
        "v3_core_sha256": sha256_file(v3),
        "v4_core_sha256": sha256_file(core),
        "v4_cli_sha256": sha256_file(cli),
    }
    if result["v3_core_sha256"] != V3_CORE_SHA256:
        raise QualityV4Error("frozen V3 core bytes changed")
    return result


def _ensure_safe_directory(root: Path, relative: str) -> Path:
    relative = _canonical_relative(relative, "directory")
    try:
        root = _v3._validated_real_root(root)
    except Exception as exc:
        raise QualityV4Error(str(exc)) from exc
    current = root
    parts = Path(relative).parts
    for part in parts:
        current = current / part
        try:
            os.mkdir(current)
        except FileExistsError:
            pass
        st = os.lstat(current)
        if (
            not stat.S_ISDIR(st.st_mode)
            or stat.S_ISLNK(st.st_mode)
            or bool(getattr(st, "st_file_attributes", 0) & _v3.REPARSE_ATTRIBUTE)
        ):
            raise QualityV4Error(f"unsafe directory component: {relative}")
    return current


def _audit_relative(status: str, envelope_sha256: str) -> str:
    attempt = secrets.token_hex(16)
    return f"{AUDIT_NAMESPACE}/{status}/{envelope_sha256}_{attempt}.json"


def _append_outcome(
    execution_root: Path,
    *,
    status: str,
    operation: str,
    stage: str,
    envelope_relative: str,
    envelope_sha256: str,
    trusted_now_utc: str,
    authorization_id: str,
    nonce: str,
    error: BaseException | None,
    outputs: Mapping[str, str] | None = None,
) -> str:
    directory = f"{AUDIT_NAMESPACE}/{status}"
    _ensure_safe_directory(execution_root, directory)
    record = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": OUTCOME_KIND,
        "status": status,
        "operation": operation,
        "stage": stage,
        "authorization_id": authorization_id,
        "nonce": nonce,
        "envelope_relative": envelope_relative,
        "envelope_sha256": envelope_sha256,
        "recorded_at_utc": trusted_now_utc,
        "error_type": "" if error is None else type(error).__name__,
        "error_message": "" if error is None else str(error)[:1000],
        "outputs": dict(outputs or {}),
        "model_loaded_or_called": False,
        "model_body_voice_avatar_blender_browser_or_live_work_started": False,
        "activation_assignment_publication_or_registration_changed": False,
        "lifecycle": private_lifecycle(),
    }
    relative = _audit_relative(status, envelope_sha256)
    _v3.exclusive_write(execution_root, relative, canonical_json_bytes(record))
    return relative


def _consume_once(
    execution_root: Path,
    envelope: Mapping[str, Any],
    envelope_relative: str,
    envelope_sha256: str,
    trusted_now_utc: str,
) -> str:
    # This helper is deliberately self-defending even when an importing caller
    # invokes its underscored name directly.  Python naming conventions are not
    # an authority boundary.
    _verify_signature(envelope, execution_root)
    if envelope.get("execution_root_sha256") != _normalized_root_hash(execution_root):
        raise QualityV4Error("cannot consume envelope for a different execution root")
    for field, observed in _code_hashes().items():
        if envelope.get(field) != observed:
            raise QualityV4Error(f"cannot consume envelope with code mismatch: {field}")
    _ensure_safe_directory(execution_root, CONSUMPTION_NAMESPACE)
    relative = (
        f"{CONSUMPTION_NAMESPACE}/{envelope['authorization_id']}--"
        f"{envelope['nonce']}.json"
    )
    marker = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": CONSUMPTION_KIND,
        "authorization_id": envelope["authorization_id"],
        "operation": envelope["operation"],
        "nonce": envelope["nonce"],
        "owner_id": envelope["owner_id"],
        "request_id": envelope["request_id"],
        "evaluation_id": envelope["evaluation_id"],
        "envelope_relative": envelope_relative,
        "envelope_sha256": envelope_sha256,
        "output_namespace": envelope["output_namespace"],
        "consumed_at_utc": trusted_now_utc,
        "lifecycle": private_lifecycle(),
    }
    try:
        return _v3.exclusive_write(execution_root, relative, canonical_json_bytes(marker))
    except FileExistsError as exc:
        raise QualityV4Error("signed authorization replay rejected: marker already exists") from exc


def _assert_material_authorized(
    execution_root: Path,
    envelope: Mapping[str, Any],
    envelope_sha256: str,
) -> None:
    """Re-prove the signature and durable consume marker at every write helper."""
    _exact_keys(envelope, ENVELOPE_KEYS, "material authorization envelope")
    observed_envelope_sha = sha256_bytes(canonical_json_bytes(dict(envelope)))
    if observed_envelope_sha != envelope_sha256:
        raise QualityV4Error("material helper envelope hash mismatch")
    _verify_signature(envelope, execution_root)
    if envelope["execution_root_sha256"] != _normalized_root_hash(execution_root):
        raise QualityV4Error("material helper execution-root binding mismatch")
    for field, observed in _code_hashes().items():
        if envelope[field] != observed:
            raise QualityV4Error(f"material helper exact code mismatch: {field}")
    marker_relative = (
        f"{CONSUMPTION_NAMESPACE}/{envelope['authorization_id']}--"
        f"{envelope['nonce']}.json"
    )
    try:
        marker = _v3.stable_load_json(execution_root, marker_relative)
    except Exception as exc:
        raise QualityV4Error("material helper requires exact durable consumption marker") from exc
    _exact_keys(marker, CONSUMPTION_KEYS, "consumption marker")
    expected = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": CONSUMPTION_KIND,
        "authorization_id": envelope["authorization_id"],
        "operation": envelope["operation"],
        "nonce": envelope["nonce"],
        "owner_id": envelope["owner_id"],
        "request_id": envelope["request_id"],
        "evaluation_id": envelope["evaluation_id"],
        "envelope_sha256": envelope_sha256,
        "output_namespace": envelope["output_namespace"],
        "lifecycle": private_lifecycle(),
    }
    for field, value in expected.items():
        if marker[field] != value:
            raise QualityV4Error(f"consumption marker exact binding mismatch: {field}")
    _ensure_safe_directory(execution_root, EXECUTION_CLAIM_NAMESPACE)
    claim_relative = (
        f"{EXECUTION_CLAIM_NAMESPACE}/{envelope['authorization_id']}--"
        f"{envelope['nonce']}.json"
    )
    claim = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": "temporary_ai_signed_authorization_execution_claim_v4",
        "authorization_id": envelope["authorization_id"],
        "operation": envelope["operation"],
        "nonce": envelope["nonce"],
        "envelope_sha256": envelope_sha256,
        "output_namespace": envelope["output_namespace"],
        "lifecycle": private_lifecycle(),
    }
    try:
        _v3.exclusive_write(
            execution_root, claim_relative, canonical_json_bytes(claim)
        )
    except FileExistsError as exc:
        raise QualityV4Error("material execution replay rejected: claim already exists") from exc


def _load_and_validate_envelope(
    execution_root: Path,
    envelope_relative: str,
    expected_envelope_sha256: str,
    trusted_now_utc: str,
) -> tuple[dict[str, Any], str]:
    envelope_relative = _canonical_relative(envelope_relative, "envelope_relative")
    if not envelope_relative.startswith(ENVELOPE_NAMESPACE + "/"):
        raise QualityV4Error("envelope must come from the fixed parent envelope namespace")
    expected = _sha(expected_envelope_sha256, "expected_envelope_sha256")
    try:
        raw = _v3.stable_read(
            execution_root, envelope_relative, expected_sha256=expected,
            require_canonical_json=True,
        )
    except Exception as exc:
        raise QualityV4Error(str(exc)) from exc
    envelope = _decode_canonical(raw, envelope_relative)
    _exact_keys(envelope, ENVELOPE_KEYS, "authorization envelope")
    if envelope["schema_version"] != SCHEMA_VERSION:
        raise QualityV4Error("authorization envelope schema version mismatch")
    operation = envelope["operation"]
    expected_kind = {
        "create_static_quality": CREATION_ENVELOPE_KIND,
        "evaluate_static_responses": EVALUATION_ENVELOPE_KIND,
    }.get(operation)
    if expected_kind is None or envelope["record_kind"] != expected_kind:
        raise QualityV4Error("authorization envelope operation/kind mismatch")
    _identifier(envelope["authorization_id"], "authorization_id")
    _identifier(envelope["signer_key_id"], "signer_key_id")
    _identifier(envelope["authority_id"], "authority_id")
    _identifier(envelope["owner_id"], "owner_id")
    _identifier(envelope["request_id"], "request_id")
    if not isinstance(envelope["nonce"], str) or NONCE_RE.fullmatch(envelope["nonce"]) is None:
        raise QualityV4Error("64-hex parent nonce required")
    if envelope["execution_root_sha256"] != _normalized_root_hash(execution_root):
        raise QualityV4Error("signed envelope execution-root binding mismatch")
    for field in (
        "authority_root_sha256", "v3_core_sha256", "v4_core_sha256",
        "v4_cli_sha256",
    ):
        _sha(envelope[field], field)
    for field in (
        "authority_root_relative", "output_namespace", "consumption_namespace",
        "audit_namespace",
    ):
        _canonical_relative(envelope[field], field)
    _canonical_relative(envelope["head_namespace"], "head_namespace", allow_empty=True)
    _canonical_relative(envelope["evaluation_root_relative"], "evaluation_root_relative", allow_empty=True)
    _canonical_relative(envelope["quality_record_relative"], "quality_record_relative", allow_empty=True)
    for field in (
        "evaluation_root_sha256", "quality_record_sha256",
        "creation_authorization_sha256",
    ):
        if envelope[field] != "":
            _sha(envelope[field], field)
    if envelope["consumption_namespace"] != CONSUMPTION_NAMESPACE:
        raise QualityV4Error("signed consumption namespace mismatch")
    if envelope["audit_namespace"] != AUDIT_NAMESPACE:
        raise QualityV4Error("signed audit namespace mismatch")
    issued = _utc(envelope["issued_at_utc"], "issued_at_utc")
    expires = _utc(envelope["expires_at_utc"], "expires_at_utc")
    now = _utc(trusted_now_utc, "trusted_now_utc")
    if expires <= issued or (expires - issued).total_seconds() > MAX_AUTHORIZATION_SECONDS:
        raise QualityV4Error("authorization lifetime must be positive and at most 15 minutes")
    if now < issued or now > expires:
        raise QualityV4Error("authorization is not active at the parent-supplied trusted time")
    if operation == "create_static_quality":
        if any(envelope[field] != "" for field in (
            "evaluation_id", "evaluation_root_relative", "evaluation_root_sha256",
            "quality_record_relative", "quality_record_sha256",
            "creation_authorization_sha256",
        )):
            raise QualityV4Error("creation envelope contains evaluation-only fields")
        _canonical_relative(envelope["head_namespace"], "head_namespace")
    else:
        _identifier(envelope["evaluation_id"], "evaluation_id")
        for field in (
            "evaluation_root_relative", "quality_record_relative",
        ):
            _canonical_relative(envelope[field], field)
        for field in (
            "evaluation_root_sha256", "quality_record_sha256",
            "creation_authorization_sha256",
        ):
            _sha(envelope[field], field)
        if envelope["head_namespace"] != "":
            raise QualityV4Error("evaluation envelope must not declare a head namespace")
    _verify_signature(envelope, execution_root)
    code = _code_hashes()
    for field, observed in code.items():
        if envelope[field] != observed:
            raise QualityV4Error(f"signed exact code hash mismatch: {field}")
    if Path(envelope_relative).name != f"{envelope['authorization_id']}.json":
        raise QualityV4Error("envelope filename does not match signed authorization ID")
    return envelope, sha256_bytes(raw)


def _prepare_v3(execution_root: Path, envelope: Mapping[str, Any]):
    authority_root = execution_root / envelope["authority_root_relative"]
    try:
        authority = _v3.open_parent_authority(
            authority_root,
            expected_root_sha256=envelope["authority_root_sha256"],
            trusted_now_utc=envelope["expires_at_utc"],
        )
        prepared = _v3.prepare_quality_v3(authority, envelope["request_id"])
    except Exception as exc:
        raise QualityV4Error(str(exc)) from exc
    if authority.authority_id != envelope["authority_id"] or authority.owner_id != envelope["owner_id"]:
        raise QualityV4Error("signed owner/authority does not match exact authority root")
    return authority, prepared


def _creation_outputs(
    execution_root: Path,
    envelope: Mapping[str, Any],
    envelope_sha256: str,
) -> dict[str, str]:
    _assert_material_authorized(execution_root, envelope, envelope_sha256)
    authority, prepared = _prepare_v3(execution_root, envelope)
    output_expected = (
        f"{envelope['authority_root_relative'].rstrip('/')}/"
        f"{str(prepared.index['output_directory']).rstrip('/')}"
    )
    head_expected = (
        f"{envelope['authority_root_relative'].rstrip('/')}/"
        f"{str(prepared.index['head_directory']).rstrip('/')}"
    )
    if envelope["output_namespace"] != output_expected or envelope["head_namespace"] != head_expected:
        raise QualityV4Error("signed output/head namespace does not match parent authority root")
    # The final output namespace is exclusive; pre-existing output is refusal.
    _v3.safe_make_directory(execution_root, envelope["output_namespace"])
    _v3.safe_make_directory(execution_root, envelope["head_namespace"])
    output = envelope["output_namespace"].rstrip("/")
    head_ns = envelope["head_namespace"].rstrip("/")
    source_pack_path = f"{output}/source_pack_v4.json"
    quality_path = f"{output}/creator_quality_v4_revision_000001.json"
    summary_path = f"{output}/creation_summary_v4.json"
    head_path = f"{head_ns}/head_000001.json"
    source_pack = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": "temporary_ai_sealed_source_pack_v4",
        "creation_authorization_sha256": envelope_sha256,
        "request_id": prepared.request["request_id"],
        "candidate_id": prepared.request["candidate_id"],
        "v3_source_pack_sha256": canonical_sha256(prepared.source_pack),
        "v3_source_pack": copy.deepcopy(prepared.source_pack),
        "lifecycle": private_lifecycle(),
    }
    source_pack_sha = _v3.exclusive_write(
        execution_root, source_pack_path, canonical_json_bytes(source_pack)
    )
    quality = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": CREATION_RESULT_KIND,
        "revision": 1,
        "creation_authorization_sha256": envelope_sha256,
        "authority_root_sha256": envelope["authority_root_sha256"],
        "request_id": prepared.request["request_id"],
        "request_sha256": prepared.quality_record["request_sha256"],
        "registry_sha256": prepared.quality_record["registry_sha256"],
        "candidate_id": prepared.request["candidate_id"],
        "display_name": prepared.request["display_name"],
        "canonical_identity": prepared.request["canonical_identity"],
        "source_continuity": prepared.request["source_continuity"],
        "source_version": prepared.request["source_version"],
        "source_timepoint": prepared.request["source_timepoint"],
        "expert_domain": prepared.request["expert_domain"],
        "maturity_status": prepared.maturity_receipt["maturity_status"],
        "source_pack_sha256": source_pack_sha,
        "v3_quality_record_sha256": canonical_sha256(prepared.quality_record),
        "exact_future_evaluation_model": EXACT_QWEN_MODEL,
        "exact_future_evaluation_digest": EXACT_QWEN_DIGEST,
        "model_loaded_or_called": False,
        "quality_status": READY_STATUS,
        "created_at_utc": envelope["issued_at_utc"],
        "lifecycle": private_lifecycle(),
    }
    quality_sha = _v3.exclusive_write(
        execution_root, quality_path, canonical_json_bytes(quality)
    )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": "temporary_ai_creator_quality_v4_static_summary",
        "request_id": prepared.request["request_id"],
        "candidate_id": prepared.request["candidate_id"],
        "creation_authorization_sha256": envelope_sha256,
        "quality_record_relative": quality_path,
        "quality_record_sha256": quality_sha,
        "source_pack_relative": source_pack_path,
        "source_pack_sha256": source_pack_sha,
        "status": READY_STATUS,
        "model_body_voice_avatar_blender_browser_or_live_queue_created": False,
        "lifecycle": private_lifecycle(),
    }
    summary_sha = _v3.exclusive_write(
        execution_root, summary_path, canonical_json_bytes(summary)
    )
    head = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": HEAD_KIND,
        "generation": 1,
        "revision": 1,
        "request_id": prepared.request["request_id"],
        "candidate_id": prepared.request["candidate_id"],
        "creation_authorization_sha256": envelope_sha256,
        "record_relative": quality_path,
        "record_sha256": quality_sha,
        "previous_head_sha256": "",
        "created_at_utc": envelope["issued_at_utc"],
        "lifecycle": private_lifecycle(),
    }
    head_sha = _v3.exclusive_write(execution_root, head_path, canonical_json_bytes(head))
    return {
        "source_pack": source_pack_path,
        "source_pack_sha256": source_pack_sha,
        "quality_record": quality_path,
        "quality_record_sha256": quality_sha,
        "summary": summary_path,
        "summary_sha256": summary_sha,
        "head": head_path,
        "head_sha256": head_sha,
    }


def _evaluation_outputs(
    execution_root: Path,
    envelope: Mapping[str, Any],
    envelope_sha256: str,
) -> dict[str, str]:
    _assert_material_authorized(execution_root, envelope, envelope_sha256)
    authority, prepared = _prepare_v3(execution_root, envelope)
    quality_raw = _v3.stable_read(
        execution_root,
        envelope["quality_record_relative"],
        expected_sha256=envelope["quality_record_sha256"],
        require_canonical_json=True,
    )
    quality = _decode_canonical(quality_raw, "V4 quality record")
    if (
        quality.get("schema_version") != SCHEMA_VERSION
        or quality.get("record_kind") != CREATION_RESULT_KIND
        or quality.get("creation_authorization_sha256")
        != envelope["creation_authorization_sha256"]
        or quality.get("request_id") != envelope["request_id"]
        or quality.get("authority_root_sha256") != envelope["authority_root_sha256"]
        or quality.get("v3_quality_record_sha256") != canonical_sha256(prepared.quality_record)
        or quality.get("model_loaded_or_called") is not False
        or quality.get("lifecycle") != private_lifecycle()
    ):
        raise QualityV4Error("evaluation is not bound to the exact inert V4 creation record")
    evaluation_root = execution_root / envelope["evaluation_root_relative"]
    try:
        eval_authority = _v3.open_parent_evaluation_authority(
            evaluation_root,
            expected_root_sha256=envelope["evaluation_root_sha256"],
            trusted_now_utc=envelope["expires_at_utc"],
        )
        v3_result = _v3.evaluate_expert_battery_v3(
            prepared, eval_authority, envelope["evaluation_id"]
        )
    except Exception as exc:
        raise QualityV4Error(str(exc)) from exc
    if eval_authority.authority_id != envelope["authority_id"] or eval_authority.owner_id != envelope["owner_id"]:
        raise QualityV4Error("signed evaluation owner/authority mismatch")
    output_expected = (
        f"{envelope['authority_root_relative'].rstrip('/')}/"
        f"{str(prepared.index['output_directory']).rstrip('/')}/evaluations/"
        f"{envelope['evaluation_id']}"
    )
    if envelope["output_namespace"] != output_expected:
        raise QualityV4Error("signed evaluation output namespace mismatch")
    _v3.safe_make_directory(execution_root, envelope["output_namespace"])
    result_path = f"{envelope['output_namespace'].rstrip('/')}/static_evaluation_result_v4.json"
    result = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": EVALUATION_RESULT_KIND,
        "evaluation_authorization_sha256": envelope_sha256,
        "creation_authorization_sha256": envelope["creation_authorization_sha256"],
        "quality_record_sha256": envelope["quality_record_sha256"],
        "authority_root_sha256": envelope["authority_root_sha256"],
        "evaluation_root_sha256": envelope["evaluation_root_sha256"],
        "evaluation_id": envelope["evaluation_id"],
        "request_id": envelope["request_id"],
        "model": EXACT_QWEN_MODEL,
        "digest": EXACT_QWEN_DIGEST,
        "v3_static_response_validation_sha256": canonical_sha256(v3_result),
        "static_response_receipts_passed": bool(v3_result.get("passed")),
        "live_model_execution_verified": False,
        "live_qwen_quality_accepted": False,
        "status": STATIC_EVALUATION_STATUS,
        "activation_assignment_publication_or_registration_changed": False,
        "lifecycle": private_lifecycle(),
    }
    result_sha = _v3.exclusive_write(
        execution_root, result_path, canonical_json_bytes(result)
    )
    return {"evaluation_result": result_path, "evaluation_result_sha256": result_sha}


def consume_signed_envelope_v4(
    execution_root: Path,
    *,
    envelope_relative: str,
    expected_envelope_sha256: str,
    trusted_now_utc: str,
) -> dict[str, Any]:
    """Consume one signed creation/evaluation envelope and emit inert evidence.

    Only primitive path/hash/time inputs cross this public API.  There are no
    public authority or prepared-value constructors.  A valid signed envelope
    is durably consumed before any candidate/evaluation output is attempted.
    """
    stage = "entry"
    operation = "unknown"
    envelope_sha = expected_envelope_sha256 if isinstance(expected_envelope_sha256, str) else ""
    auth_id = "unknown_authorization"
    nonce = "0" * 64
    consumed_sha = ""
    try:
        stage = "load_validate_signature_and_code"
        envelope, envelope_sha = _load_and_validate_envelope(
            execution_root, envelope_relative, expected_envelope_sha256,
            trusted_now_utc,
        )
        operation = envelope["operation"]
        auth_id = envelope["authorization_id"]
        nonce = envelope["nonce"]
        stage = "consume_once"
        consumed_sha = _consume_once(
            execution_root, envelope, envelope_relative, envelope_sha,
            trusted_now_utc,
        )
        stage = "derive_validate_and_write_static_outputs"
        if operation == "create_static_quality":
            outputs = _creation_outputs(execution_root, envelope, envelope_sha)
        elif operation == "evaluate_static_responses":
            outputs = _evaluation_outputs(execution_root, envelope, envelope_sha)
        else:  # defensive; schema validation already excludes this.
            raise QualityV4Error("unsupported signed operation")
        stage = "append_success_outcome"
        outcome = _append_outcome(
            execution_root, status="success", operation=operation, stage="complete",
            envelope_relative=envelope_relative, envelope_sha256=envelope_sha,
            trusted_now_utc=trusted_now_utc, authorization_id=auth_id,
            nonce=nonce, error=None, outputs=outputs,
        )
        return {
            "schema_version": SCHEMA_VERSION,
            "authorization_id": auth_id,
            "operation": operation,
            "envelope_sha256": envelope_sha,
            "consumption_marker_sha256": consumed_sha,
            "outputs": outputs,
            "outcome_receipt": outcome,
            "model_body_voice_avatar_blender_browser_or_live_work_started": False,
            "activation_assignment_publication_or_registration_changed": False,
        }
    except Exception as exc:
        try:
            _append_outcome(
                execution_root, status="failure", operation=operation, stage=stage,
                envelope_relative=str(envelope_relative),
                envelope_sha256=(envelope_sha if SHA_RE.fullmatch(envelope_sha or "") else "0" * 64),
                trusted_now_utc=str(trusted_now_utc), authorization_id=auth_id,
                nonce=nonce, error=exc,
            )
        except Exception:
            # The original exact failure remains authoritative.  A root so
            # malformed that a safe append is impossible must not be weakened
            # merely to manufacture audit output.
            pass
        if isinstance(exc, QualityV4Error):
            raise
        raise QualityV4Error(str(exc)) from exc


__all__ = [
    "AUDIT_NAMESPACE", "CONSUMPTION_NAMESPACE", "CREATION_ENVELOPE_KIND",
    "CREATION_RESULT_KIND", "ENVELOPE_KEYS", "ENVELOPE_NAMESPACE",
    "EVALUATION_ENVELOPE_KIND", "EVALUATION_RESULT_KIND", "EXECUTION_CLAIM_NAMESPACE",
    "EXACT_QWEN_DIGEST", "EXACT_QWEN_MODEL", "MAX_AUTHORIZATION_SECONDS",
    "PRIVATE_STATUS", "PRODUCTION_SIGNER_KEY_ID", "QualityV4Error",
    "READY_STATUS", "SCHEMA_VERSION", "SIGNATURE_ALGORITHM",
    "STATIC_EVALUATION_STATUS", "TEST_ROOT_PREFIX", "TEST_SIGNER_KEY_ID",
    "V3_CORE_SHA256", "V3_REJECTION_AUDIT_SHA256", "canonical_json_bytes",
    "canonical_sha256", "consume_signed_envelope_v4", "private_lifecycle",
    "sha256_bytes", "sha256_file",
]
