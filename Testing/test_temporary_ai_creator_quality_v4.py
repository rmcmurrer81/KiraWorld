from __future__ import annotations

import ast
import base64
import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from Core import temporary_ai_creator_quality_v3 as v3
from Core import temporary_ai_creator_quality_v4 as v4
from Testing.test_temporary_ai_creator_quality_v3 import (
    build_authority,
    build_evaluation_authority,
    write_canonical,
)


ISSUED = "2026-08-10T04:30:00Z"
NOW = "2026-08-10T04:35:00Z"
EXPIRES = "2026-08-10T04:40:00Z"
TEST_PRIVATE_SEED_B64 = "zmqSoniEnFLrkL1YSM0w5PY7/p8OLtNuAnQ2IDP5s04="
PROJECT_ROOT = Path(__file__).resolve().parents[1]
V3_FROZEN = {
    "Core/temporary_ai_creator_quality_v3.py":
        "bd915c1a0d77268337ef3b22b68273a8c900629a910e9adc0d4087d63f37fd50",
    "tools/create_temporary_ai_candidate_quality_v3.py":
        "521c64fa573d81d7ed30f552d7ebe382e569f46a3fbacf40b4876829b35bb8fd",
    "Testing/test_temporary_ai_creator_quality_v3.py":
        "24bb3742f8e9a4d9e0c4b6b6ce655bee1f69bf6f933198f39269910c27b07d9e",
    "RecoverySprint/continuation_20260809/temporary_ai_creator_qwen35_quality_v3_attempt_01/CHECKPOINT.md":
        "d2f3551dffc86693b8d085dba304ca940719c397dce083bcd9e5f6646acd696b",
    "RecoverySprint/continuation_20260809/temporary_ai_creator_qwen35_quality_v3_attempt_01/INDEPENDENT_STATIC_AUDIT.md":
        "2caa7161c79fba93447c4a9ef0dea96441edc70883f7457c7a38cd610a8ca45e",
}


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execution_root_sha(root: Path) -> str:
    spelling = os.path.normcase(os.path.normpath(str(root.absolute())))
    return hashlib.sha256(spelling.encode("utf-8")).hexdigest()


def code_hashes() -> dict[str, str]:
    return {
        "v3_core_sha256": file_sha(PROJECT_ROOT / "Core/temporary_ai_creator_quality_v3.py"),
        "v4_core_sha256": file_sha(PROJECT_ROOT / "Core/temporary_ai_creator_quality_v4.py"),
        "v4_cli_sha256": file_sha(PROJECT_ROOT / "tools/create_temporary_ai_candidate_quality_v4.py"),
    }


def signed_envelope(value: dict) -> dict:
    unsigned = copy.deepcopy(value)
    unsigned["signature_base64"] = ""
    payload = dict(unsigned)
    payload.pop("signature_base64")
    private = Ed25519PrivateKey.from_private_bytes(
        base64.b64decode(TEST_PRIVATE_SEED_B64, validate=True)
    )
    signature = private.sign(v4.canonical_json_bytes(payload))
    unsigned["signature_base64"] = base64.b64encode(signature).decode("ascii")
    return unsigned


def base_envelope(
    root: Path,
    *,
    root_sha: str,
    request_id: str,
    expert: bool,
    authorization_id: str,
    nonce_seed: str,
) -> dict:
    candidate = "quantum_expert" if expert else "ada_variant"
    result = {
        "schema_version": v4.SCHEMA_VERSION,
        "record_kind": v4.CREATION_ENVELOPE_KIND,
        "authorization_id": authorization_id,
        "operation": "create_static_quality",
        "nonce": hashlib.sha256(nonce_seed.encode("utf-8")).hexdigest(),
        "signer_key_id": v4.TEST_SIGNER_KEY_ID,
        "signature_algorithm": v4.SIGNATURE_ALGORITHM,
        "execution_root_sha256": execution_root_sha(root),
        "authority_id": "kira_parent_authority",
        "owner_id": "real_robert",
        "request_id": request_id,
        "evaluation_id": "",
        "authority_root_relative": "authority",
        "authority_root_sha256": root_sha,
        "evaluation_root_relative": "",
        "evaluation_root_sha256": "",
        "output_namespace": f"authority/outputs/{candidate}",
        "head_namespace": f"authority/outputs/{candidate}/heads",
        "quality_record_relative": "",
        "quality_record_sha256": "",
        "creation_authorization_sha256": "",
        "consumption_namespace": v4.CONSUMPTION_NAMESPACE,
        "audit_namespace": v4.AUDIT_NAMESPACE,
        "issued_at_utc": ISSUED,
        "expires_at_utc": EXPIRES,
        **code_hashes(),
        "signature_base64": "",
    }
    return signed_envelope(result)


def evaluation_envelope(
    root: Path,
    *,
    root_sha: str,
    evaluation_root_sha: str,
    request_id: str,
    evaluation_id: str,
    creation_result: dict,
    authorization_id: str,
) -> dict:
    quality_path = creation_result["outputs"]["quality_record"]
    quality_sha = creation_result["outputs"]["quality_record_sha256"]
    result = {
        "schema_version": v4.SCHEMA_VERSION,
        "record_kind": v4.EVALUATION_ENVELOPE_KIND,
        "authorization_id": authorization_id,
        "operation": "evaluate_static_responses",
        "nonce": hashlib.sha256((authorization_id + "-nonce").encode()).hexdigest(),
        "signer_key_id": v4.TEST_SIGNER_KEY_ID,
        "signature_algorithm": v4.SIGNATURE_ALGORITHM,
        "execution_root_sha256": execution_root_sha(root),
        "authority_id": "kira_parent_authority",
        "owner_id": "real_robert",
        "request_id": request_id,
        "evaluation_id": evaluation_id,
        "authority_root_relative": "authority",
        "authority_root_sha256": root_sha,
        "evaluation_root_relative": "evaluation_authority",
        "evaluation_root_sha256": evaluation_root_sha,
        "output_namespace": (
            f"authority/outputs/quantum_expert/evaluations/{evaluation_id}"
        ),
        "head_namespace": "",
        "quality_record_relative": quality_path,
        "quality_record_sha256": quality_sha,
        "creation_authorization_sha256": creation_result["envelope_sha256"],
        "consumption_namespace": v4.CONSUMPTION_NAMESPACE,
        "audit_namespace": v4.AUDIT_NAMESPACE,
        "issued_at_utc": ISSUED,
        "expires_at_utc": EXPIRES,
        **code_hashes(),
        "signature_base64": "",
    }
    return signed_envelope(result)


def write_envelope(root: Path, envelope: dict) -> tuple[str, str]:
    relative = f"{v4.ENVELOPE_NAMESPACE}/{envelope['authorization_id']}.json"
    sha = write_canonical(root / relative, envelope)
    return relative, sha


class TemporaryAiCreatorQualityV4Tests(unittest.TestCase):
    def test_reproduces_exact_v3_public_capability_attack(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root_sha, request_id = build_authority(root, expert=True)
            root_record = json.loads((root / "AUTHORITY_ROOT.json").read_text("utf-8"))
            forged = v3.ParentAuthorityV3(
                root=root,
                root_sha256=root_sha,
                authority_id=root_record["authority_id"],
                owner_id=root_record["owner_id"],
                trusted_now_utc=NOW,
                root_record=root_record,
                _capability=v3._AUTHORITY_CAPABILITY,
            )
            prepared = v3.prepare_quality_v3(forged, request_id)
            eval_sha, eval_id = build_evaluation_authority(root, prepared)
            eval_root_record = json.loads(
                (root / "EVALUATION_AUTHORITY_ROOT.json").read_text("utf-8")
            )
            forged_eval = v3.ParentEvaluationAuthorityV3(
                root=root,
                root_sha256=eval_sha,
                authority_id=eval_root_record["authority_id"],
                owner_id=eval_root_record["owner_id"],
                trusted_now_utc=NOW,
                root_record=eval_root_record,
                _capability=v3._EVALUATION_AUTHORITY_CAPABILITY,
            )
            result = v3.evaluate_expert_battery_v3(prepared, forged_eval, eval_id)
            self.assertEqual(
                prepared.quality_record["quality_status"],
                "V3_STATIC_EVIDENCE_READY_PRIVATE_INACTIVE_UNASSIGNED",
            )
            self.assertTrue(result["passed"])

    def test_v4_exports_no_authority_or_prepared_constructor_or_capability(self) -> None:
        public = set(v4.__all__)
        self.assertFalse(any("Authority" in name or "Prepared" in name for name in public))
        self.assertFalse(any("CAPABILITY" in name for name in vars(v4)))
        source = (PROJECT_ROOT / "Core/temporary_ai_creator_quality_v4.py").read_text("utf-8")
        tree = ast.parse(source)
        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        self.assertEqual(classes, ["QualityV4Error"])
        with self.assertRaises(TypeError):
            v4.consume_signed_envelope_v4(  # type: ignore[call-arg]
                Path(tempfile.gettempdir()), authority={"forged": True}
            )

    def test_valid_signed_creation_is_inert_append_only_and_replay_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix=v4.TEST_ROOT_PREFIX) as temporary:
            root = Path(temporary)
            root_sha, request_id = build_authority(root / "authority")
            envelope = base_envelope(
                root, root_sha=root_sha, request_id=request_id, expert=False,
                authorization_id="authorization_ada_create_v4",
                nonce_seed="ada-create-once",
            )
            relative, envelope_sha = write_envelope(root, envelope)
            result = v4.consume_signed_envelope_v4(
                root, envelope_relative=relative,
                expected_envelope_sha256=envelope_sha, trusted_now_utc=NOW,
            )
            self.assertEqual(result["operation"], "create_static_quality")
            self.assertFalse(
                result["model_body_voice_avatar_blender_browser_or_live_work_started"]
            )
            emitted = "\n".join(
                (root / path).read_text("utf-8")
                for key, path in result["outputs"].items()
                if not key.endswith("_sha256")
            ).casefold()
            self.assertIn("v4_static_evidence_ready", emitted)
            self.assertNotIn('"model_loaded_or_called": true', emitted)
            self.assertNotIn('"activation_allowed": true', emitted)
            with self.assertRaisesRegex(v4.QualityV4Error, "replay rejected"):
                v4.consume_signed_envelope_v4(
                    root, envelope_relative=relative,
                    expected_envelope_sha256=envelope_sha, trusted_now_utc=NOW,
                )
            failures = list((root / v4.AUDIT_NAMESPACE / "failure").glob("*.json"))
            self.assertEqual(len(failures), 1)
            failure = json.loads(failures[0].read_text("utf-8"))
            self.assertEqual(failure["stage"], "consume_once")
            self.assertFalse(failure["model_loaded_or_called"])
            with self.assertRaisesRegex(v4.QualityV4Error, "execution replay rejected"):
                v4._creation_outputs(root, envelope, envelope_sha)

    def test_signature_tamper_code_substitution_and_root_scope_fail_with_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix=v4.TEST_ROOT_PREFIX) as temporary:
            root = Path(temporary)
            root_sha, request_id = build_authority(root / "authority")
            envelope = base_envelope(
                root, root_sha=root_sha, request_id=request_id, expert=False,
                authorization_id="authorization_signature_tamper_v4",
                nonce_seed="signature-tamper",
            )
            envelope["output_namespace"] = "authority/outputs/attacker_substitution"
            relative, envelope_sha = write_envelope(root, envelope)
            with self.assertRaisesRegex(v4.QualityV4Error, "signature verification failed"):
                v4.consume_signed_envelope_v4(
                    root, envelope_relative=relative,
                    expected_envelope_sha256=envelope_sha, trusted_now_utc=NOW,
                )
            self.assertTrue(list((root / v4.AUDIT_NAMESPACE / "failure").glob("*.json")))
            self.assertFalse((root / v4.CONSUMPTION_NAMESPACE).exists())

        with tempfile.TemporaryDirectory(prefix=v4.TEST_ROOT_PREFIX) as temporary:
            root = Path(temporary)
            root_sha, request_id = build_authority(root / "authority")
            envelope = base_envelope(
                root, root_sha=root_sha, request_id=request_id, expert=False,
                authorization_id="authorization_code_substitution_v4",
                nonce_seed="code-substitution",
            )
            envelope["v4_core_sha256"] = "f" * 64
            envelope = signed_envelope(envelope)
            relative, envelope_sha = write_envelope(root, envelope)
            with self.assertRaisesRegex(v4.QualityV4Error, "code hash mismatch"):
                v4.consume_signed_envelope_v4(
                    root, envelope_relative=relative,
                    expected_envelope_sha256=envelope_sha, trusted_now_utc=NOW,
                )

        with tempfile.TemporaryDirectory() as outer:
            root = Path(outer) / "nested_not_direct_temp_child"
            root.mkdir()
            root_sha, request_id = build_authority(root / "authority")
            envelope = base_envelope(
                root, root_sha=root_sha, request_id=request_id, expert=False,
                authorization_id="authorization_test_scope_escape_v4",
                nonce_seed="scope-escape",
            )
            relative, envelope_sha = write_envelope(root, envelope)
            with self.assertRaisesRegex(v4.QualityV4Error, "test signer cannot authorize"):
                v4.consume_signed_envelope_v4(
                    root, envelope_relative=relative,
                    expected_envelope_sha256=envelope_sha, trusted_now_utc=NOW,
                )

    def test_expiry_nonce_namespace_and_unknown_fields_fail_closed(self) -> None:
        modes = ("expired", "long", "nonce", "namespace", "unknown")
        for mode in modes:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(
                prefix=v4.TEST_ROOT_PREFIX
            ) as temporary:
                root = Path(temporary)
                root_sha, request_id = build_authority(root / "authority")
                envelope = base_envelope(
                    root, root_sha=root_sha, request_id=request_id, expert=False,
                    authorization_id=f"authorization_{mode}_v4",
                    nonce_seed=f"nonce-{mode}",
                )
                if mode == "expired":
                    trusted = "2026-08-10T04:41:00Z"
                else:
                    trusted = NOW
                if mode == "long":
                    envelope["expires_at_utc"] = "2026-08-10T05:30:00Z"
                elif mode == "nonce":
                    envelope["nonce"] = "short"
                elif mode == "namespace":
                    envelope["consumption_namespace"] = "attacker/consumed"
                elif mode == "unknown":
                    envelope["activate_now"] = True
                envelope = signed_envelope(envelope)
                relative, envelope_sha = write_envelope(root, envelope)
                with self.assertRaises(v4.QualityV4Error):
                    v4.consume_signed_envelope_v4(
                        root, envelope_relative=relative,
                        expected_envelope_sha256=envelope_sha,
                        trusted_now_utc=trusted,
                    )

    def test_valid_expert_evaluation_is_static_not_live_acceptance(self) -> None:
        with tempfile.TemporaryDirectory(prefix=v4.TEST_ROOT_PREFIX) as temporary:
            root = Path(temporary)
            authority_root = root / "authority"
            root_sha, request_id = build_authority(authority_root, expert=True)
            create_envelope = base_envelope(
                root, root_sha=root_sha, request_id=request_id, expert=True,
                authorization_id="authorization_quantum_create_v4",
                nonce_seed="quantum-create",
            )
            create_relative, create_sha = write_envelope(root, create_envelope)
            creation = v4.consume_signed_envelope_v4(
                root, envelope_relative=create_relative,
                expected_envelope_sha256=create_sha, trusted_now_utc=NOW,
            )
            authority = v3.open_parent_authority(
                authority_root, expected_root_sha256=root_sha, trusted_now_utc=NOW
            )
            prepared = v3.prepare_quality_v3(authority, request_id)
            eval_root = root / "evaluation_authority"
            eval_root.mkdir()
            eval_sha, eval_id = build_evaluation_authority(eval_root, prepared)
            eval_envelope = evaluation_envelope(
                root, root_sha=root_sha, evaluation_root_sha=eval_sha,
                request_id=request_id, evaluation_id=eval_id,
                creation_result=creation,
                authorization_id="authorization_quantum_evaluation_v4",
            )
            eval_relative, eval_envelope_sha = write_envelope(root, eval_envelope)
            evaluation = v4.consume_signed_envelope_v4(
                root, envelope_relative=eval_relative,
                expected_envelope_sha256=eval_envelope_sha, trusted_now_utc=NOW,
            )
            result = json.loads(
                (root / evaluation["outputs"]["evaluation_result"]).read_text("utf-8")
            )
            self.assertTrue(result["static_response_receipts_passed"])
            self.assertFalse(result["live_model_execution_verified"])
            self.assertFalse(result["live_qwen_quality_accepted"])
            self.assertEqual(result["status"], v4.STATIC_EVALUATION_STATUS)

    def test_direct_public_value_forgery_cannot_replace_signed_envelope(self) -> None:
        with tempfile.TemporaryDirectory(prefix=v4.TEST_ROOT_PREFIX) as temporary:
            root = Path(temporary)
            root_sha, request_id = build_authority(root / "authority")
            forged = base_envelope(
                root, root_sha=root_sha, request_id=request_id, expert=False,
                authorization_id="authorization_direct_forgery_v4",
                nonce_seed="direct-forgery",
            )
            forged["signature_base64"] = base64.b64encode(b"x" * 64).decode("ascii")
            relative, envelope_sha = write_envelope(root, forged)
            with self.assertRaisesRegex(v4.QualityV4Error, "signature verification failed"):
                v4.consume_signed_envelope_v4(
                    root, envelope_relative=relative,
                    expected_envelope_sha256=envelope_sha, trusted_now_utc=NOW,
                )
            self.assertFalse((root / "authority/outputs/ada_variant").exists())

    def test_direct_private_helper_names_do_not_bypass_signature_or_consumption(self) -> None:
        with tempfile.TemporaryDirectory(prefix=v4.TEST_ROOT_PREFIX) as temporary:
            root = Path(temporary)
            root_sha, request_id = build_authority(root / "authority")
            forged = base_envelope(
                root, root_sha=root_sha, request_id=request_id, expert=False,
                authorization_id="authorization_helper_bypass_v4",
                nonce_seed="helper-bypass",
            )
            forged["signature_base64"] = base64.b64encode(b"z" * 64).decode("ascii")
            forged_sha = v4.sha256_bytes(v4.canonical_json_bytes(forged))
            with self.assertRaisesRegex(v4.QualityV4Error, "signature verification failed"):
                v4._consume_once(  # exact hostile import of underscored helper
                    root, forged, "forged/envelope.json", forged_sha, NOW
                )
            self.assertFalse((root / v4.CONSUMPTION_NAMESPACE).exists())
            with self.assertRaisesRegex(v4.QualityV4Error, "signature verification failed"):
                v4._creation_outputs(root, forged, forged_sha)
            self.assertFalse((root / "authority/outputs/ada_variant").exists())

    def test_rejected_v3_exact_bytes_and_audit_remain_preserved(self) -> None:
        for relative, expected in V3_FROZEN.items():
            self.assertEqual(file_sha(PROJECT_ROOT / relative), expected, relative)

    def test_v4_source_has_no_signing_private_key_or_live_lane(self) -> None:
        core = (PROJECT_ROOT / "Core/temporary_ai_creator_quality_v4.py").read_text("utf-8")
        cli = (PROJECT_ROOT / "tools/create_temporary_ai_candidate_quality_v4.py").read_text("utf-8")
        lowered = (core + "\n" + cli).casefold()
        self.assertNotIn("ed25519privatekey", lowered)
        self.assertNotIn("ollama", lowered)
        self.assertNotIn("subprocess", lowered)
        self.assertNotIn("bpy", lowered)
        self.assertNotIn("automatic_fast_build", lowered)
        self.assertNotIn("activate_candidate", lowered)


if __name__ == "__main__":
    unittest.main()
