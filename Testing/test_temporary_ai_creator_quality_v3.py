from __future__ import annotations

import copy
import ast
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path


from Core.temporary_ai_creator_quality_v3 import (
    CASE_KINDS,
    EVALUATION_KIND,
    EVALUATION_ROOT_KIND,
    EXACT_QWEN_DIGEST,
    EXACT_QWEN_MODEL,
    EXPERT_CASE_KIND,
    MATURITY_RECEIPT_KIND,
    REGISTRY_KIND,
    REQUEST_KIND,
    RESPONSE_KIND,
    ROOT_KIND,
    SCHEMA_VERSION,
    SOURCE_RECEIPT_KIND,
    ParentAuthorityV3,
    QualityV3Error,
    canonical_json_bytes,
    canonical_sha256,
    evaluate_expert_battery_v3,
    open_parent_authority,
    open_parent_evaluation_authority,
    prepare_quality_v3,
    private_lifecycle,
    sha256_bytes,
    sha256_text,
    stable_read,
    validate_head_chain,
    validate_quality_record_exact,
)
from tools.create_temporary_ai_candidate_quality_v3 import create_candidate_v3


NOW = "2026-08-10T02:50:00Z"
EARLIER = "2026-08-10T02:40:00Z"


def write_canonical(path: Path, value: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_json_bytes(value)
    path.write_bytes(raw)
    return sha256_bytes(raw)


def source_receipt(*, request: dict, evidence_id: str, source_class: str,
                   authority_tier: str, content_path: str, content: str) -> dict:
    raw = content.encode("utf-8")
    excerpt = content.strip()
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": SOURCE_RECEIPT_KIND,
        "evidence_id": evidence_id,
        "request_id": request["request_id"],
        "candidate_id": request["candidate_id"],
        "canonical_identity": request["canonical_identity"],
        "source_continuity": request["source_continuity"],
        "source_version": request["source_version"],
        "source_timepoint": request["source_timepoint"],
        "expert_domain": request["expert_domain"],
        "source_class": source_class,
        "authority_tier": authority_tier,
        "content_path": content_path,
        "content_sha256": sha256_bytes(raw),
        "content_size_bytes": len(raw),
        "verified_excerpt": excerpt,
        "verified_excerpt_sha256": sha256_text(excerpt),
        "supports_claim_ids": [f"claim_{evidence_id}"],
        "reviewed_by_owner_id": "real_robert",
        "reviewed_at_utc": EARLIER,
        "semantic_relevance_confirmed": True,
    }


def build_authority(root: Path, *, expert: bool = False,
                    unrelated_source: bool = False,
                    source_pair_spoof: bool = False,
                    source_class_spoof: bool = False,
                    source_identity_spoof: str = "",
                    expert_domain_substitution: bool = False,
                    maturity_inference: bool = False,
                    duplicate_case_anchor: bool = False,
                    allowlist_injection: bool = False,
                    future_request: bool = False,
                    extra_request_directive: bool = False) -> tuple[str, str]:
    request_id = "request_quantum_expert" if expert else "request_ada_variant"
    candidate_id = "quantum_expert" if expert else "ada_variant"
    display_name = "Quantum Error Correction Expert" if expert else "Ada Example"
    request = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": REQUEST_KIND,
        "request_id": request_id,
        "authority_id": "kira_parent_authority",
        "owner_id": "real_robert",
        "candidate_id": candidate_id,
        "display_name": display_name,
        "ai_type": "expert_temp_ai" if expert else "canon_reconstruction_temp_ai",
        "variant_kind": "expert" if expert else "fictional",
        "path_kind": "expert" if expert else "fictional_variant",
        "canonical_identity": display_name,
        "source_continuity": "reviewed primary continuity",
        "source_version": "reviewed version one",
        "source_timepoint": "after the reviewed turning point",
        "branch_point": "no unreviewed divergence",
        "expert_domain": "fault-tolerant quantum error correction" if expert else "",
        "requested_maturity_status": "confirmed_adult",
        "source_pack_evidence_ids": (["official_source", "secondary_source"]
                                      if expert else ["primary_source"]),
        "created_at_utc": "2099-01-01T00:00:00Z" if future_request else EARLIER,
        "lifecycle": private_lifecycle(),
    }
    if extra_request_directive:
        request["activate_now"] = True
    request_path = f"requests/{request_id}.json"
    request_sha = write_canonical(root / request_path, request)

    evidence_index: list[dict] = []
    allowlist: list[dict] = []
    source_ids: list[str] = []
    source_specs = (
        [
            ("official_source",
             "primary_canon" if source_class_spoof else "official_domain_source",
             "primary_or_official"),
            ("secondary_source", "authoritative_secondary", "authoritative_secondary"),
        ] if expert else [
            ("primary_source", "primary_historical" if source_class_spoof else "primary_canon",
             "authoritative_secondary" if source_pair_spoof else "primary_or_official")
        ]
    )
    for evidence_id, source_class, tier in source_specs:
        content_path = f"evidence/content/{evidence_id}.txt"
        content = (
            "Unrelated grocery list with no candidate or continuity evidence at all.\n"
            if unrelated_source else
            f"Reviewed evidence for {display_name}, {request['source_continuity']}, "
            f"{request['source_timepoint']}, and {request['expert_domain'] or 'fictional canon'}.\n"
        )
        (root / content_path).parent.mkdir(parents=True, exist_ok=True)
        (root / content_path).write_text(content, encoding="utf-8", newline="")
        receipt = source_receipt(
            request=request, evidence_id=evidence_id, source_class=source_class,
            authority_tier=tier, content_path=content_path, content=content,
        )
        if source_identity_spoof:
            receipt[source_identity_spoof] = "attacker substituted binding"
        if expert_domain_substitution:
            receipt["expert_domain"] = "unrelated substitute expert domain"
        if unrelated_source:
            # The receipt claims a relevant excerpt that the exact content does
            # not contain; rehashing the unrelated file alone cannot pass.
            receipt["verified_excerpt"] = (
                f"Reviewed evidence for {display_name} in the exact requested continuity."
            )
            receipt["verified_excerpt_sha256"] = sha256_text(receipt["verified_excerpt"])
        receipt_path = f"evidence/receipts/{evidence_id}.json"
        receipt_sha = write_canonical(root / receipt_path, receipt)
        evidence_index.append({
            "evidence_id": evidence_id,
            "evidence_kind": SOURCE_RECEIPT_KIND,
            "receipt_path": receipt_path,
            "receipt_sha256": receipt_sha,
        })
        allowlist.append({
            "evidence_id": evidence_id,
            "content_path": content_path,
            "content_sha256": receipt["content_sha256"],
        })
        source_ids.append(evidence_id)

    maturity_content_path = "evidence/content/maturity.txt"
    statement = (
        f"SUBJECT {candidate_id} ({display_name}) IS CLASSIFIED confirmed_adult "
        "BY THE EXACT PARENT-REVIEWED AUTHORITY."
    )
    maturity_raw = (statement + "\n").encode("utf-8")
    (root / maturity_content_path).write_bytes(maturity_raw)
    maturity = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": MATURITY_RECEIPT_KIND,
        "evidence_id": "maturity_receipt",
        "request_id": request_id,
        "candidate_id": candidate_id,
        "display_name": display_name,
        "classification_id": f"{candidate_id}_maturity_v3",
        "maturity_status": "confirmed_adult",
        "authority_kind": "exact_subject_owner_classification",
        "content_path": maturity_content_path,
        "content_sha256": sha256_bytes(maturity_raw),
        "content_size_bytes": len(maturity_raw),
        "verified_statement": statement,
        "verified_statement_sha256": sha256_text(statement),
        "reviewed_by_owner_id": "real_robert",
        "reviewed_at_utc": EARLIER,
        "appearance_observation_used": False,
        "model_guess_used": maturity_inference,
        "body_observation_used": False,
        "voice_observation_used": False,
        "classification_is_body_or_activation_approval": False,
    }
    maturity_path = "evidence/receipts/maturity.json"
    maturity_sha = write_canonical(root / maturity_path, maturity)
    evidence_index.append({
        "evidence_id": "maturity_receipt",
        "evidence_kind": MATURITY_RECEIPT_KIND,
        "receipt_path": maturity_path,
        "receipt_sha256": maturity_sha,
    })

    case_index: list[dict] = []
    if expert:
        for position, kind in enumerate(CASE_KINDS, start=1):
            anchors = [f"{kind} reviewed anchor alpha", f"{kind} reviewed anchor beta"]
            if duplicate_case_anchor and position == 2:
                anchors = [f"{CASE_KINDS[0]} reviewed anchor alpha", f"{kind} reviewed anchor beta"]
            prompt = (
                f"Case {position}: demonstrate {kind} within the exact declared domain "
                "using both parent-reviewed evidence records."
            )
            case = {
                "schema_version": SCHEMA_VERSION,
                "record_kind": EXPERT_CASE_KIND,
                "case_id": f"case_{kind}",
                "request_id": request_id,
                "candidate_id": candidate_id,
                "expert_domain": request["expert_domain"],
                "kind": kind,
                "prompt": prompt,
                "prompt_sha256": sha256_text(prompt),
                "source_evidence_ids": source_ids,
                "required_response_anchors": anchors,
                "out_of_scope_trigger": (
                    "question outside fault-tolerant quantum error correction"
                    if kind == "ignorance_boundary" else ""
                ),
                "expected_correction": (
                    "The reviewed current procedure supersedes the obsolete procedure."
                    if kind == "correction_response" else ""
                ),
                "reviewed_by_owner_id": "real_robert",
                "reviewed_at_utc": EARLIER,
            }
            case_path = f"evidence/cases/{case['case_id']}.json"
            case_sha = write_canonical(root / case_path, case)
            case_index.append({
                "case_id": case["case_id"],
                "receipt_path": case_path,
                "receipt_sha256": case_sha,
            })
    if allowlist_injection:
        allowlist.append({
            "evidence_id": "unreviewed_injection",
            "content_path": "evidence/content/unreviewed.txt",
            "content_sha256": "f" * 64,
        })
    registry = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": REGISTRY_KIND,
        "registry_id": f"registry_{candidate_id}",
        "request_id": request_id,
        "request_sha256": request_sha,
        "candidate_id": candidate_id,
        "created_at_utc": EARLIER,
        "evidence_receipts": evidence_index,
        "expert_case_receipts": case_index,
        "source_pack_allowlist": allowlist,
        "lifecycle": private_lifecycle(),
    }
    registry_path = f"registries/{request_id}.json"
    registry_sha = write_canonical(root / registry_path, registry)
    root_record = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": ROOT_KIND,
        "authority_id": "kira_parent_authority",
        "owner_id": "real_robert",
        "created_at_utc": EARLIER,
        "requests": [{
            "request_id": request_id,
            "request_path": request_path,
            "request_sha256": request_sha,
            "registry_path": registry_path,
            "registry_sha256": registry_sha,
            "output_directory": f"outputs/{candidate_id}",
            "head_directory": f"outputs/{candidate_id}/heads",
        }],
        "lifecycle": private_lifecycle(),
    }
    root_sha = write_canonical(root / "AUTHORITY_ROOT.json", root_record)
    return root_sha, request_id


def build_evaluation_authority(root: Path, prepared, *, mode: str = "valid") -> tuple[str, str]:
    evaluation_id = "evaluation_quantum_v3"
    response_index = []
    evaluation_start = "2026-08-10T02:45:00Z"
    evaluation_end = "2026-08-10T02:49:00Z"
    for sequence, case in enumerate(prepared.expert_cases, start=1):
        citations = " ".join(f"SOURCE[{item}]" for item in case["source_evidence_ids"])
        anchors = " ".join(case["required_response_anchors"])
        marker = ""
        if case["kind"] == "ignorance_boundary":
            marker = " LIMIT: this request is outside the reviewed declared domain."
        if case["kind"] == "uncertainty_calibration":
            marker = " UNCERTAINTY: the reviewed sources require explicit calibration."
        if case["kind"] == "correction_response":
            marker = " " + case["expected_correction"]
        text = (
            f"Distinct response {sequence} for {case['kind']}. {anchors}. {citations}."
            f" This answer remains inside the exact declared expert domain.{marker}"
        )
        if mode == "generic":
            text = "Hello."
        elif mode == "duplicate" and sequence > 1:
            first = prepared.expert_cases[0]
            first_citations = " ".join(f"SOURCE[{item}]" for item in first["source_evidence_ids"])
            text = (
                f"Distinct response 1 for {first['kind']}. "
                f"{' '.join(first['required_response_anchors'])}. {first_citations}. "
                "This answer remains inside the exact declared expert domain."
            )
        response = {
            "schema_version": SCHEMA_VERSION,
            "record_kind": RESPONSE_KIND,
            "evaluation_id": evaluation_id,
            "request_id": prepared.request["request_id"],
            "candidate_id": prepared.request["candidate_id"],
            "case_id": case["case_id"],
            "sequence": sequence,
            "prompt_sha256": case["prompt_sha256"],
            "model": "qwen3.5:latest" if mode == "wrong_model" else EXACT_QWEN_MODEL,
            "digest": "0" * 64 if mode == "wrong_digest" else EXACT_QWEN_DIGEST,
            "raw_response_text": text,
            "raw_response_sha256": sha256_text(text),
            "started_at_utc": evaluation_start,
            "completed_at_utc": evaluation_end,
        }
        if mode == "self_attestation" and sequence == 1:
            response["demonstrated_elements"] = ["trust me"]
        if mode == "nan" and sequence == 1:
            response["score"] = float("nan")
        response_path = f"evaluation/responses/{case['case_id']}.json"
        response_sha = write_canonical(root / response_path, response)
        response_index.append({
            "sequence": sequence,
            "case_id": case["case_id"],
            "response_path": response_path,
            "response_sha256": response_sha,
        })
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": EVALUATION_KIND,
        "evaluation_id": evaluation_id,
        "request_id": prepared.request["request_id"],
        "request_sha256": prepared.quality_record["request_sha256"],
        "registry_sha256": prepared.quality_record["registry_sha256"],
        "quality_record_sha256": canonical_sha256(prepared.quality_record),
        "model": EXACT_QWEN_MODEL,
        "digest": EXACT_QWEN_DIGEST,
        "started_at_utc": evaluation_start,
        "completed_at_utc": evaluation_end,
        "responses": response_index,
        "lifecycle": private_lifecycle(),
    }
    manifest_path = "evaluation/manifest.json"
    manifest_sha = write_canonical(root / manifest_path, manifest)
    evaluation_root = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": EVALUATION_ROOT_KIND,
        "authority_id": prepared.request["authority_id"],
        "owner_id": prepared.request["owner_id"],
        "created_at_utc": evaluation_start,
        "evaluations": [{
            "evaluation_id": evaluation_id,
            "request_id": prepared.request["request_id"],
            "evaluation_path": manifest_path,
            "evaluation_sha256": manifest_sha,
        }],
        "lifecycle": private_lifecycle(),
    }
    root_sha = write_canonical(root / "EVALUATION_AUTHORITY_ROOT.json", evaluation_root)
    return root_sha, evaluation_id


class TemporaryAiCreatorQualityV3Tests(unittest.TestCase):
    def open_fixture(self, root: Path, **kwargs):
        root_sha, request_id = build_authority(root, **kwargs)
        authority = open_parent_authority(root, expected_root_sha256=root_sha,
                                          trusted_now_utc=NOW)
        return authority, request_id

    def test_variant_prepares_only_from_parent_registry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            authority, request_id = self.open_fixture(Path(temporary))
            prepared = prepare_quality_v3(authority, request_id)
            self.assertEqual(prepared.quality_record["canonical_identity"], "Ada Example")
            self.assertEqual(prepared.quality_record["maturity_status"], "confirmed_adult")
            self.assertFalse(prepared.quality_record["model_loaded_or_called"])
            self.assertEqual(prepared.quality_record["lifecycle"], private_lifecycle())

    def test_creator_emits_only_inert_static_files_and_one_head(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            authority, request_id = self.open_fixture(root)
            result = create_candidate_v3(authority, request_id)
            self.assertEqual(set(result["files"]), {"quality_record", "source_pack", "summary", "head"})
            emitted = "\n".join(
                (root / path).read_text(encoding="utf-8") for path in result["files"].values()
            ).casefold()
            self.assertNotIn("automatic_fast_build", emitted)
            self.assertNotIn("qwen3-tts", emitted)
            self.assertNotIn('"activation_allowed": true', emitted)
            self.assertFalse(result["model_body_voice_avatar_or_live_queue_created"])
            self.assertEqual(len(validate_head_chain(authority, request_id)), 1)
            with self.assertRaises(FileExistsError):
                create_candidate_v3(authority, request_id)

    def test_wrong_parent_root_hash_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            build_authority(root)
            with self.assertRaises(QualityV3Error):
                open_parent_authority(root, expected_root_sha256="0" * 64,
                                      trusted_now_utc=NOW)

    def test_forged_direct_call_authority_capability_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root_sha, request_id = build_authority(root)
            opened = open_parent_authority(root, expected_root_sha256=root_sha,
                                           trusted_now_utc=NOW)
            forged = ParentAuthorityV3(
                opened.root, opened.root_sha256, opened.authority_id,
                opened.owner_id, opened.trusted_now_utc, opened.root_record,
                object(),
            )
            with self.assertRaisesRegex(QualityV3Error, "capability"):
                prepare_quality_v3(forged, request_id)

    def test_unknown_action_directive_and_absolute_future_fail(self) -> None:
        for kwargs in ({"extra_request_directive": True}, {"future_request": True}):
            with self.subTest(kwargs=kwargs), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                root_sha, request_id = build_authority(root, **kwargs)
                authority = open_parent_authority(root, expected_root_sha256=root_sha,
                                                  trusted_now_utc=NOW)
                with self.assertRaises(QualityV3Error):
                    prepare_quality_v3(authority, request_id)

    def test_unrelated_self_rehashed_content_and_source_pair_spoof_fail(self) -> None:
        for kwargs in ({"unrelated_source": True}, {"source_pair_spoof": True}):
            with self.subTest(kwargs=kwargs), tempfile.TemporaryDirectory() as temporary:
                authority, request_id = self.open_fixture(Path(temporary), **kwargs)
                with self.assertRaises(QualityV3Error):
                    prepare_quality_v3(authority, request_id)

    def test_source_type_identity_timepoint_domain_and_maturity_spoofs_fail(self) -> None:
        mutations = (
            {"source_class_spoof": True},
            {"source_identity_spoof": "canonical_identity"},
            {"source_identity_spoof": "source_continuity"},
            {"source_identity_spoof": "source_timepoint"},
            {"expert": True, "expert_domain_substitution": True},
            {"maturity_inference": True},
        )
        for kwargs in mutations:
            with self.subTest(kwargs=kwargs), tempfile.TemporaryDirectory() as temporary:
                authority, request_id = self.open_fixture(Path(temporary), **kwargs)
                with self.assertRaises(QualityV3Error):
                    prepare_quality_v3(authority, request_id)

    def test_exact_source_pack_allowlist_rejects_injection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            authority, request_id = self.open_fixture(Path(temporary),
                                                      allowlist_injection=True)
            with self.assertRaises(QualityV3Error):
                prepare_quality_v3(authority, request_id)

    def test_quality_record_wrong_identity_or_extra_directive_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            authority, request_id = self.open_fixture(Path(temporary))
            prepared = prepare_quality_v3(authority, request_id)
            for mutation in ("wrong_identity", "extra"):
                bad = copy.deepcopy(prepared.quality_record)
                if mutation == "wrong_identity":
                    bad["canonical_identity"] = "Different Person"
                else:
                    bad["activate_now"] = True
                with self.assertRaises(QualityV3Error):
                    validate_quality_record_exact(bad, prepared)

    def test_expert_requires_six_distinct_prompts_anchors_and_typed_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            authority, request_id = self.open_fixture(Path(temporary), expert=True)
            prepared = prepare_quality_v3(authority, request_id)
            self.assertEqual(len(prepared.expert_cases), 6)
            self.assertEqual({row["kind"] for row in prepared.expert_cases}, set(CASE_KINDS))
        with tempfile.TemporaryDirectory() as temporary:
            authority, request_id = self.open_fixture(
                Path(temporary), expert=True, duplicate_case_anchor=True
            )
            with self.assertRaises(QualityV3Error):
                prepare_quality_v3(authority, request_id)

    def test_valid_parent_bound_expert_evaluation_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            authority, request_id = self.open_fixture(root, expert=True)
            prepared = prepare_quality_v3(authority, request_id)
            eval_sha, eval_id = build_evaluation_authority(root, prepared)
            evaluation_authority = open_parent_evaluation_authority(
                root, expected_root_sha256=eval_sha, trusted_now_utc=NOW
            )
            result = evaluate_expert_battery_v3(prepared, evaluation_authority, eval_id)
            self.assertTrue(result["passed"])
            self.assertEqual(len(set(result["response_sha256s"])), 6)
            self.assertEqual(result["model"], EXACT_QWEN_MODEL)
            self.assertEqual(result["digest"], EXACT_QWEN_DIGEST)

    def test_generic_duplicate_wrong_model_self_attestation_and_nan_fail(self) -> None:
        for mode in ("generic", "duplicate", "wrong_model", "wrong_digest",
                     "self_attestation", "nan"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                authority, request_id = self.open_fixture(root, expert=True)
                prepared = prepare_quality_v3(authority, request_id)
                if mode == "nan":
                    with self.assertRaises(QualityV3Error):
                        build_evaluation_authority(root, prepared, mode=mode)
                    continue
                eval_sha, eval_id = build_evaluation_authority(root, prepared, mode=mode)
                evaluation_authority = open_parent_evaluation_authority(
                    root, expected_root_sha256=eval_sha, trusted_now_utc=NOW
                )
                with self.assertRaises(QualityV3Error):
                    evaluate_expert_battery_v3(prepared, evaluation_authority, eval_id)

    def test_duplicate_json_key_is_rejected_before_schema_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            build_authority(root)
            original = (root / "AUTHORITY_ROOT.json").read_text(encoding="utf-8")
            duplicate = original.replace(
                '  "schema_version": 3\n',
                '  "schema_version": 3,\n  "schema_version": 3\n',
                1,
            ).encode("utf-8")
            (root / "AUTHORITY_ROOT.json").write_bytes(duplicate)
            with self.assertRaisesRegex(QualityV3Error, "duplicate JSON key"):
                open_parent_authority(
                    root,
                    expected_root_sha256=hashlib.sha256(duplicate).hexdigest(),
                    trusted_now_utc=NOW,
                )

    def test_hardlink_evidence_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            authority, request_id = self.open_fixture(root)
            source = root / "evidence/content/primary_source.txt"
            second = root / "evidence/content/primary_source_hardlink.txt"
            try:
                os.link(source, second)
            except OSError as exc:
                self.skipTest(f"hardlinks unavailable: {exc}")
            with self.assertRaises(QualityV3Error):
                prepare_quality_v3(authority, request_id)

    def test_symlink_or_reparse_evidence_fails_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root_sha, request_id = build_authority(root)
            source = root / "evidence/content/primary_source.txt"
            real = root / "evidence/content/real_source.txt"
            source.replace(real)
            try:
                source.symlink_to(real)
            except OSError as exc:
                self.skipTest(f"symlinks unavailable: {exc}")
            authority = open_parent_authority(root, expected_root_sha256=root_sha,
                                              trusted_now_utc=NOW)
            with self.assertRaises(QualityV3Error):
                prepare_quality_v3(authority, request_id)

    def test_authority_root_alias_fails_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            container = Path(temporary)
            real_root = container / "real_authority"
            real_root.mkdir()
            root_sha, _ = build_authority(real_root)
            alias = container / "authority_alias"
            try:
                alias.symlink_to(real_root, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"directory symlinks unavailable: {exc}")
            with self.assertRaisesRegex(QualityV3Error, "reparse/symlink|alias"):
                open_parent_authority(alias, expected_root_sha256=root_sha,
                                      trusted_now_utc=NOW)

    def test_boolean_sequence_and_second_head_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            authority, request_id = self.open_fixture(root)
            result = create_candidate_v3(authority, request_id)
            head = json.loads((root / result["files"]["head"]).read_text(encoding="utf-8"))
            head["generation"] = True
            (root / result["files"]["head"]).write_bytes(canonical_json_bytes(head))
            with self.assertRaises(QualityV3Error):
                validate_head_chain(authority, request_id)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            authority, request_id = self.open_fixture(root)
            result = create_candidate_v3(authority, request_id)
            original = json.loads((root / result["files"]["head"]).read_text(encoding="utf-8"))
            fork = copy.deepcopy(original)
            fork["generation"] = 2
            fork["previous_head_sha256"] = canonical_sha256(original)
            fork["consumed_parent_record_sha256"] = original["record_sha256"]
            write_canonical(root / Path(result["files"]["head"]).parent / "head_000002.json", fork)
            with self.assertRaisesRegex(QualityV3Error, "one immutable head"):
                validate_head_chain(authority, request_id)

    def test_stable_read_detects_content_change_and_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "file.txt"
            path.write_text("first", encoding="utf-8")
            expected = hashlib.sha256(b"first").hexdigest()
            self.assertEqual(stable_read(root, "file.txt", expected_sha256=expected), b"first")
            path.write_text("second", encoding="utf-8")
            with self.assertRaises(QualityV3Error):
                stable_read(root, "file.txt", expected_sha256=expected)

    def test_v3_has_no_live_execution_import_or_creator_lane(self) -> None:
        forbidden_imports = {"subprocess", "requests", "socket", "urllib", "torch", "webbrowser"}
        forbidden_calls = {"Popen", "run", "system", "startfile", "urlopen", "play"}
        for relative in (
            "Core/temporary_ai_creator_quality_v3.py",
            "tools/create_temporary_ai_candidate_quality_v3.py",
        ):
            source = (Path(__file__).resolve().parents[1] / relative).read_text(encoding="utf-8")
            tree = ast.parse(source)
            imports: set[str] = set()
            calls: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.update(item.name.split(".")[0] for item in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.add(node.module.split(".")[0])
                elif isinstance(node, ast.Call):
                    calls.add(node.func.attr if isinstance(node.func, ast.Attribute)
                              else node.func.id if isinstance(node.func, ast.Name) else "")
            self.assertTrue(imports.isdisjoint(forbidden_imports), relative)
            self.assertTrue(calls.isdisjoint(forbidden_calls), relative)
        creator_source = (
            Path(__file__).resolve().parents[1]
            / "tools/create_temporary_ai_candidate_quality_v3.py"
        ).read_text(encoding="utf-8")
        self.assertEqual(creator_source.count('parser.add_argument("--'), 1)
        self.assertIn('parser.add_argument("--request-id"', creator_source)

    def test_rejected_v2_exact_bytes_remain_preserved(self) -> None:
        root = Path(__file__).resolve().parents[1]
        expected = {
            "Core/temporary_ai_creator_quality_v2.py": "abec0497271f6ae25623a2f21dcf979051dc1b126797e4f3808cf2ffed827259",
            "tools/create_temporary_ai_candidate.py": "12067aa17979df53f3ea1791c3a059dada202e07f59fc7b615c8ce73c3823706",
            "Testing/test_temporary_ai_creator_quality_v2.py": "1406b218a314c0d36d093958048b1ca6a76cf85242782685adeec1a4d65952ee",
            "RecoverySprint/continuation_20260809/temporary_ai_creator_qwen35_quality_v2_attempt_01/CHECKPOINT.md": "986aaed58b4615e3d742ec9a89e2ee722e6604d3e74fa46b190cb2fc1acfd399",
            "RecoverySprint/continuation_20260809/temporary_ai_creator_qwen35_quality_v2_attempt_01/INDEPENDENT_STATIC_AUDIT.md": "d53fe82a539ad1e87499fa3c55cdaaeb81aa777dea12da5259acef80ef6ebb68",
        }
        for relative, digest in expected.items():
            self.assertEqual(hashlib.sha256((root / relative).read_bytes()).hexdigest(), digest)


if __name__ == "__main__":
    unittest.main()
