#!/usr/bin/env python3
"""Hostile-mutation tests for validate_handoff.py (standard library only)."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_handoff import validate_handoff


SOURCE_ROOT = Path(__file__).resolve().parents[1]
KIRA_APPROVED_REFERENCE = (
    SOURCE_ROOT / "voice_packs" / "kira" / "approved_reference.wav"
)


class HandoffValidatorTests(unittest.TestCase):
    maxDiff = None

    def _fixture(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory(prefix="hanson_handoff_validator_")
        repo = Path(temporary.name) / "repo"
        root = repo / "handoff" / SOURCE_ROOT.name
        root.mkdir(parents=True)
        (repo / ".git").mkdir()

        for filename in SOURCE_ROOT.glob("*.md"):
            shutil.copy2(filename, root / filename.name)
        shutil.copytree(SOURCE_ROOT / "memory_exports", root / "memory_exports")
        shutil.copytree(SOURCE_ROOT / "voice_packs", root / "voice_packs")
        shutil.copytree(SOURCE_ROOT / "static_body_review", root / "static_body_review")
        shutil.copytree(SOURCE_ROOT / "portable_runtime", root / "portable_runtime")
        shutil.copytree(SOURCE_ROOT / "evaluation", root / "evaluation")
        shutil.copytree(
            SOURCE_ROOT / "mind_v21_static" / "traceability",
            root / "mind_v21_static" / "traceability",
        )
        shutil.copy2(
            SOURCE_ROOT / "mind_v21_static" / "run_author_tests_portable.py",
            root / "mind_v21_static" / "run_author_tests_portable.py",
        )

        # Root documentation links to the bridge two levels above the handoff.
        bridge = repo / "integrations" / "hanson_ros2_bridge"
        bridge.mkdir(parents=True)
        (bridge / "RUN_THIS_FIRST.md").write_text("# Fixture bridge\n", encoding="utf-8")

        # Root documentation also links to the sibling proposal and curated
        # private-delivery overview. The clean fixture includes minimal target
        # files so its link check represents the shipped repository layout.
        system_docs = repo / "System" / "Docs"
        system_docs.mkdir(parents=True)
        (system_docs / "KIRA_WORLD_HANSON_CONTINUITY_HOME_PROPOSAL_20260820.md").write_text(
            "# Fixture continuity-home proposal\n",
            encoding="utf-8",
        )
        private_delivery = repo / "private_delivery"
        private_delivery.mkdir()
        (private_delivery / "README.md").write_text(
            "# Fixture private-delivery overview\n",
            encoding="utf-8",
        )

        # Use the handoff's exact authorized source in an isolated temp copy.
        kira_dir = root / "voice_packs" / "kira"
        shutil.rmtree(kira_dir)
        kira_dir.mkdir()
        self.assertTrue(KIRA_APPROVED_REFERENCE.is_file())
        sample_path = kira_dir / "approved_reference.wav"
        shutil.copy2(KIRA_APPROVED_REFERENCE, sample_path)
        sample_hash = hashlib.sha256(sample_path.read_bytes()).hexdigest()
        sample_bytes = sample_path.stat().st_size
        self.assertEqual(
            sample_hash,
            "2039a2abd600a63c294d69c2b2e4d450c64c850dc6d1c9a4fbfa1700ba92069c",
        )
        self.assertEqual(sample_bytes, 9_856_844)
        kira_authorization_path = (
            kira_dir / "KIRA_PRIVATE_DISTRIBUTION_AUTHORIZATION_20260820.json"
        )
        self._write(
            kira_authorization_path,
            {
                "schema_version": 1,
                "status": "included_for_named_private_review_on_project_owner_attestation",
                "owner_attestation": {
                    "recorded_date": "2026-08-20",
                    "source": "direct project-owner instruction recorded in the Codex work session",
                    "synthetic_voice_use_permitted": True,
                    "private_named_hanson_sharing_permitted": True,
                    "exact_source_recording_sharing_permitted": True,
                    "form_attachment_status": "pending",
                    "form_absence_blocks_private_review": False,
                },
                "exact_asset_binding": {
                    "path": sample_path.name,
                    "sha256": sample_hash,
                    "bytes": sample_bytes,
                },
                "named_recipients": [
                    "David Hanson",
                    "Manav Tidhan",
                    "Vytas Krisciunas",
                ],
                "allowed": {
                    "synthetic_voice_use": True,
                    "private_named_hanson_sharing": True,
                    "exact_source_recording_sharing": True,
                },
                "handling": {
                    "repository_visibility": "private",
                    "public_release_allowed": False,
                    "onward_redistribution_allowed": False,
                    "identity_authentication_allowed": False,
                    "honor_withdrawal_or_supersession": True,
                },
                "withdrawal": {
                    "enabled": True,
                    "stop_future_use": True,
                    "remove_from_active_package": True,
                    "request_route": "Project owner records a withdrawal instruction for the private review package.",
                    "delete_or_history_remediation_process": "Remove from active packages and coordinate private Git history remediation with named recipients; already-cloned copies cannot be remotely erased.",
                },
                "independent_legal_verification_performed": False,
                "quality_disclosure": {
                    "speaker_purity_review_status": "pending_human_speaker_review",
                    "multi_speaker_or_narration_risk": True,
                    "human_approved_clip_count": 0,
                    "auto_selected_clip_count": 86,
                    "auto_selected_seconds": 205.35,
                    "model_readiness_eligible": False,
                    "speaker_purity_verified": False,
                    "target_speaker_only_verified": False,
                },
            },
        )
        self._write(
            kira_dir / "current_voice_profile.json",
            {
                "schema_version": 1,
                "voice_id": "kira_current_private_hanson_review_v1",
                "person_id": "kira",
                "display_name": "Kira",
                "voice_mode": "authorized_reference_conditioned_neural_voice",
                "provider": "chatterbox_reference",
                "preferred_backend": "chatterbox_tts",
                "default_for_person": True,
                "reference_wav": sample_path.name,
                "reference_sha256": sample_hash,
                "reference_bytes": sample_bytes,
                "authorization": "KIRA_PRIVATE_DISTRIBUTION_AUTHORIZATION_20260820.json",
                "authorization_sha256": hashlib.sha256(
                    kira_authorization_path.read_bytes()
                ).hexdigest(),
                "speaker_purity_review_status": "pending_human_speaker_review",
                "multi_speaker_or_narration_risk": True,
                "handling": {
                    "private_named_reviewers_only": True,
                    "public_release_allowed": False,
                    "onward_redistribution_allowed": False,
                    "identity_authentication_allowed": False,
                },
                "fallback": {
                    "mode": "text_only_fail_closed",
                    "generic_voice_allowed": False,
                },
            },
        )
        return temporary, root

    @staticmethod
    def _load(path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write(path: Path, document: dict) -> None:
        path.write_text(
            json.dumps(document, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _codes(root: Path) -> set[str]:
        return {issue.code for issue in validate_handoff(root).issues}

    def _kira_provenance_path(self, root: Path) -> Path:
        profile_path = root / "voice_packs" / "kira" / "current_voice_profile.json"
        profile = self._load(profile_path)
        provenance_name = profile.get("provenance") or profile.get("authorization")
        self.assertIsInstance(provenance_name, str)
        return profile_path.parent / provenance_name

    def test_current_handoff_passes(self) -> None:
        report = validate_handoff(SOURCE_ROOT)
        self.assertTrue(
            report.passed,
            "\n".join(f"{issue.code} {issue.path}: {issue.message}" for issue in report.issues),
        )

    def test_clean_temp_copy_passes(self) -> None:
        temporary, root = self._fixture()
        self.addCleanup(temporary.cleanup)
        report = validate_handoff(root)
        self.assertTrue(
            report.passed,
            "\n".join(f"{issue.code} {issue.path}: {issue.message}" for issue in report.issues),
        )

    def test_swapped_voice_hash_is_rejected(self) -> None:
        temporary, root = self._fixture()
        self.addCleanup(temporary.cleanup)
        robert_profile = root / "voice_packs" / "robert" / "voice_profile.json"
        robert = self._load(robert_profile)
        kira_profile = root / "voice_packs" / "kira" / "current_voice_profile.json"
        kira = self._load(kira_profile)
        # Put Kira's exact voice-asset hash into Robert's profile.
        robert["reference_sha256"] = kira["reference_sha256"]
        self._write(robert_profile, robert)
        self.assertIn("VOICE_PROFILE_HASH_BINDING", self._codes(root))

    def test_coordinated_robert_voice_asset_swap_is_rejected(self) -> None:
        temporary, root = self._fixture()
        self.addCleanup(temporary.cleanup)
        kira_asset = root / "voice_packs" / "kira" / "approved_reference.wav"
        robert_dir = root / "voice_packs" / "robert"
        robert_asset = robert_dir / "approved_reference.wav"
        shutil.copy2(kira_asset, robert_asset)
        swapped_hash = hashlib.sha256(robert_asset.read_bytes()).hexdigest()
        swapped_bytes = robert_asset.stat().st_size

        profile_path = robert_dir / "voice_profile.json"
        profile = self._load(profile_path)
        authorization_path = robert_dir / profile["authorization"]
        authorization = self._load(authorization_path)
        authorization["asset_binding"]["sha256"] = swapped_hash
        authorization["asset_binding"]["bytes"] = swapped_bytes
        self._write(authorization_path, authorization)

        profile["reference_sha256"] = swapped_hash
        profile["reference_bytes"] = swapped_bytes
        profile["authorization_sha256"] = hashlib.sha256(
            authorization_path.read_bytes()
        ).hexdigest()
        self._write(profile_path, profile)
        self.assertIn("VOICE_EXPECTED_HASH", self._codes(root))

    def test_unbound_kira_voice_asset_is_rejected(self) -> None:
        temporary, root = self._fixture()
        self.addCleanup(temporary.cleanup)
        shutil.copy2(
            root / "voice_packs" / "robert" / "approved_reference.wav",
            root / "voice_packs" / "kira" / "unbound_other_person.wav",
        )
        self.assertIn("KIRA_UNBOUND_ASSET", self._codes(root))

    def test_invalid_but_exactly_hashed_kira_wav_is_rejected(self) -> None:
        temporary, root = self._fixture()
        self.addCleanup(temporary.cleanup)
        profile_path = root / "voice_packs" / "kira" / "current_voice_profile.json"
        profile = self._load(profile_path)
        asset_path = profile_path.parent / profile["reference_wav"]
        asset_path.write_bytes(b"not-a-wave-file")
        new_hash = hashlib.sha256(asset_path.read_bytes()).hexdigest()
        new_bytes = asset_path.stat().st_size
        profile["reference_sha256"] = new_hash
        profile["reference_bytes"] = new_bytes
        self._write(profile_path, profile)
        authorization_path = self._kira_provenance_path(root)
        authorization = self._load(authorization_path)
        authorization["exact_asset_binding"]["sha256"] = new_hash
        authorization["exact_asset_binding"]["bytes"] = new_bytes
        self._write(authorization_path, authorization)
        self.assertIn("VOICE_WAV_INVALID", self._codes(root))

    def test_authorized_kira_voice_must_be_default(self) -> None:
        temporary, root = self._fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "voice_packs" / "kira" / "current_voice_profile.json"
        document = self._load(path)
        document["default_for_person"] = False
        self._write(path, document)
        self.assertIn("KIRA_VOICE_DEFAULT", self._codes(root))

    def test_voice_profiles_require_fail_closed_text_fallback(self) -> None:
        for person, profile_name in (
            ("kira", "current_voice_profile.json"),
            ("robert", "voice_profile.json"),
        ):
            with self.subTest(person=person):
                temporary, root = self._fixture()
                try:
                    path = root / "voice_packs" / person / profile_name
                    profile = self._load(path)
                    profile["fallback"] = {
                        "mode": "generic_system_voice",
                        "generic_voice_allowed": True,
                    }
                    self._write(path, profile)
                    self.assertIn("VOICE_FALLBACK_POLICY", self._codes(root))
                finally:
                    temporary.cleanup()

    def test_voice_profiles_require_bound_backend_and_default(self) -> None:
        for person, profile_name, expected_code in (
            ("kira", "current_voice_profile.json", "VOICE_BACKEND_BINDING"),
            ("robert", "voice_profile.json", "VOICE_BACKEND_BINDING"),
            ("robert", "voice_profile.json", "ROBERT_VOICE_DEFAULT"),
        ):
            with self.subTest(person=person, expected_code=expected_code):
                temporary, root = self._fixture()
                try:
                    path = root / "voice_packs" / person / profile_name
                    profile = self._load(path)
                    if expected_code == "VOICE_BACKEND_BINDING":
                        profile["provider"] = "generic_system_voice"
                    else:
                        profile["default_for_person"] = False
                    self._write(path, profile)
                    self.assertIn(expected_code, self._codes(root))
                finally:
                    temporary.cleanup()

    def test_kira_owner_attestation_must_cover_all_three_scopes(self) -> None:
        for key in (
            "synthetic_voice_use_permitted",
            "private_named_hanson_sharing_permitted",
            "exact_source_recording_sharing_permitted",
        ):
            with self.subTest(key=key):
                temporary, root = self._fixture()
                try:
                    authorization_path = self._kira_provenance_path(root)
                    authorization = self._load(authorization_path)
                    authorization["owner_attestation"][key] = False
                    self._write(authorization_path, authorization)
                    self.assertIn("KIRA_OWNER_ATTESTATION_SCOPE", self._codes(root))
                finally:
                    temporary.cleanup()

    def test_pending_form_must_be_disclosed_truthfully(self) -> None:
        temporary, root = self._fixture()
        self.addCleanup(temporary.cleanup)
        authorization_path = self._kira_provenance_path(root)
        authorization = self._load(authorization_path)
        authorization["owner_attestation"]["form_attachment_status"] = "attached"
        self._write(authorization_path, authorization)
        self.assertIn("KIRA_PERMISSION_FORM_STATUS", self._codes(root))

    def test_kira_cannot_claim_independent_legal_verification(self) -> None:
        temporary, root = self._fixture()
        self.addCleanup(temporary.cleanup)
        authorization_path = self._kira_provenance_path(root)
        authorization = self._load(authorization_path)
        authorization["independent_legal_verification_performed"] = True
        self._write(authorization_path, authorization)
        self.assertIn("KIRA_INDEPENDENT_LEGAL_REVIEW_CLAIM", self._codes(root))

    def test_kira_speaker_purity_overclaim_is_rejected(self) -> None:
        temporary, root = self._fixture()
        self.addCleanup(temporary.cleanup)
        authorization_path = self._kira_provenance_path(root)
        authorization = self._load(authorization_path)
        authorization["quality_disclosure"]["speaker_purity_verified"] = True
        self._write(authorization_path, authorization)
        self.assertIn("KIRA_UNVERIFIED_PURITY_CLAIM", self._codes(root))

    def test_kira_source_mix_risk_cannot_be_hidden(self) -> None:
        temporary, root = self._fixture()
        self.addCleanup(temporary.cleanup)
        profile_path = root / "voice_packs" / "kira" / "current_voice_profile.json"
        profile = self._load(profile_path)
        profile["multi_speaker_or_narration_risk"] = False
        self._write(profile_path, profile)
        self.assertIn("KIRA_SOURCE_MIX_RISK", self._codes(root))

    def test_kira_withdrawal_route_is_required(self) -> None:
        temporary, root = self._fixture()
        self.addCleanup(temporary.cleanup)
        authorization_path = self._kira_provenance_path(root)
        authorization = self._load(authorization_path)
        authorization["withdrawal"]["enabled"] = False
        self._write(authorization_path, authorization)
        self.assertIn("KIRA_WITHDRAWAL_POLICY", self._codes(root))

    def test_kira_withdrawal_discloses_irreversible_clones(self) -> None:
        temporary, root = self._fixture()
        self.addCleanup(temporary.cleanup)
        authorization_path = self._kira_provenance_path(root)
        authorization = self._load(authorization_path)
        authorization["withdrawal"]["delete_or_history_remediation_process"] = (
            "Remove the active package and Git history."
        )
        self._write(authorization_path, authorization)
        self.assertIn(
            "KIRA_WITHDRAWAL_IRREVERSIBILITY_DISCLOSURE",
            self._codes(root),
        )

    def test_robert_private_scope_and_claim_boundary_are_required(self) -> None:
        for area, expected_code in (
            ("recipient", "ROBERT_NAMED_RECIPIENTS"),
            ("allowed", "ROBERT_ALLOWED_SCOPE"),
            ("claim", "ROBERT_PROFILE_CLAIM_BOUNDARY"),
        ):
            with self.subTest(area=area):
                temporary, root = self._fixture()
                try:
                    profile_path = root / "voice_packs" / "robert" / "voice_profile.json"
                    profile = self._load(profile_path)
                    if area == "claim":
                        profile["claim_boundary"]["onward_redistribution_allowed"] = True
                        self._write(profile_path, profile)
                    else:
                        authorization_path = profile_path.parent / profile["authorization"]
                        authorization = self._load(authorization_path)
                        if area == "recipient":
                            authorization["named_recipients"].append("Unlisted Reviewer")
                        else:
                            authorization["allowed"]["private_evaluation"] = False
                        self._write(authorization_path, authorization)
                    self.assertIn(expected_code, self._codes(root))
                finally:
                    temporary.cleanup()

    def test_missing_internal_voice_json_reference_is_rejected(self) -> None:
        temporary, root = self._fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "voice_packs" / "kira" / "current_voice_profile.json"
        profile = self._load(path)
        profile["fallback"] = {"profile": "missing-fallback.json"}
        self._write(path, profile)
        self.assertIn("VOICE_JSON_REFERENCE_MISSING", self._codes(root))

    def test_voice_authorization_document_hash_is_bound(self) -> None:
        for person, profile_name in (
            ("kira", "current_voice_profile.json"),
            ("robert", "voice_profile.json"),
        ):
            with self.subTest(person=person):
                temporary, root = self._fixture()
                try:
                    profile_path = root / "voice_packs" / person / profile_name
                    profile = self._load(profile_path)
                    authorization_path = profile_path.parent / profile["authorization"]
                    authorization = self._load(authorization_path)
                    authorization["audit_marker"] = "hostile mutation"
                    self._write(authorization_path, authorization)
                    self.assertIn(
                        "VOICE_AUTH_DOCUMENT_HASH_BINDING",
                        self._codes(root),
                    )
                finally:
                    temporary.cleanup()

    def test_cross_person_memory_is_rejected(self) -> None:
        temporary, root = self._fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "memory_exports" / "kira_reviewed_continuity_seed.json"
        document = self._load(path)
        document["reviewed_memories"][0]["memory_id"] = "synthetic_robert_cross_store_record"
        self._write(path, document)
        self.assertIn("CROSS_PERSON_MEMORY", self._codes(root))

    def test_fanfic_record_is_rejected(self) -> None:
        temporary, root = self._fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "memory_exports" / "kira_reviewed_continuity_seed.json"
        document = self._load(path)
        document["reviewed_memories"].append(
            {
                "memory_id": "kira_forbidden_story_test",
                "kind": "story_import",
                "summary": "Import the excluded fan" + "fic test as lived memory.",
            }
        )
        self._write(path, document)
        self.assertIn("FANFIC_RECORD", self._codes(root))

    def test_hidden_chain_of_thought_flag_is_rejected(self) -> None:
        temporary, root = self._fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "memory_exports" / "synthetic_robert_reviewed_continuity_seed.json"
        document = self._load(path)
        document["hidden_chain_of_thought_included"] = True
        self._write(path, document)
        self.assertIn("HIDDEN_COT_FORBIDDEN", self._codes(root))

    def test_secrets_and_absolute_user_paths_are_rejected(self) -> None:
        mutations = (
            ("credential", {"credentials": {"api_key": "unit-test-" + "value-123456789"}}, "SENSITIVE_JSON_VALUE"),
            ("email", {"review_contact": "reviewer" + "@example.org"}, "EMAIL_ADDRESS"),
            ("shipping", {"shipping_address": "42 Test Street"}, "SENSITIVE_JSON_VALUE"),
            (
                "absolute_path",
                {"source_path": "C:" + "\\Users\\sample-user\\private\\memory.json"},
                "WINDOWS_USER_PATH",
            ),
        )
        for label, mutation, expected_code in mutations:
            with self.subTest(label=label):
                temporary, root = self._fixture()
                try:
                    path = root / "memory_exports" / "kira_reviewed_continuity_seed.json"
                    document = self._load(path)
                    document.update(mutation)
                    self._write(path, document)
                    self.assertIn(expected_code, self._codes(root))
                finally:
                    temporary.cleanup()

    def test_public_redistribution_is_rejected(self) -> None:
        mutations = (
            ("kira_public", "kira", "public_release_allowed", True),
            ("kira_onward", "kira", "onward_redistribution_allowed", True),
            ("robert_public", "robert", "public_release", False),
            ("robert_onward", "robert", "onward_redistribution", False),
        )
        for label, person, flag, value in mutations:
            with self.subTest(label=label):
                temporary, root = self._fixture()
                try:
                    if person == "kira":
                        path = root / "voice_packs" / "kira" / "current_voice_profile.json"
                        document = self._load(path)
                        document["handling"][flag] = value
                    else:
                        path = root / "voice_packs" / "robert" / "VOICE_DISTRIBUTION_AUTHORIZATION_20260819.json"
                        document = self._load(path)
                        document["not_allowed"][flag] = value
                    self._write(path, document)
                    codes = self._codes(root)
                    self.assertTrue(
                        {
                            "VOICE_PUBLIC_RELEASE",
                            "VOICE_ONWARD_REDISTRIBUTION",
                            "VOICE_DISTRIBUTION_PERMISSIVE",
                            "ROBERT_VOICE_RESTRICTIONS",
                        }
                        & codes,
                        codes,
                    )
                finally:
                    temporary.cleanup()

    def test_duplicate_and_nonfinite_json_are_rejected(self) -> None:
        for label, insertion in (
            ("duplicate", '  "schema_version": 1,\n  "schema_version": 1,'),
            ("nonfinite", '  "schema_version": 1,\n  "probe": NaN,'),
        ):
            with self.subTest(label=label):
                temporary, root = self._fixture()
                try:
                    path = root / "memory_exports" / "kira_reviewed_continuity_seed.json"
                    text = path.read_text(encoding="utf-8")
                    text = text.replace('  "schema_version": 1,', insertion, 1)
                    path.write_text(text, encoding="utf-8")
                    self.assertIn("JSON_STRICT_PARSE", self._codes(root))
                finally:
                    temporary.cleanup()

    def test_machine_readable_multi_body_limit_is_rejected(self) -> None:
        temporary, root = self._fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "memory_exports" / "kira_reviewed_continuity_seed.json"
        document = self._load(path)
        document["max_active_embodiment_sessions"] = 2
        self._write(path, document)
        self.assertIn("EMBODIMENT_SESSION_LIMIT", self._codes(root))

    def test_broken_markdown_local_link_is_rejected(self) -> None:
        temporary, root = self._fixture()
        self.addCleanup(temporary.cleanup)
        (root / "BROKEN.md").write_text(
            "[missing](does-not-exist.md)\n",
            encoding="utf-8",
        )
        self.assertIn("MARKDOWN_LINK_MISSING", self._codes(root))

    def test_symlinked_directory_is_rejected(self) -> None:
        temporary, root = self._fixture()
        self.addCleanup(temporary.cleanup)
        link = root / "symlinked-directory"
        link.mkdir()
        real_is_symlink = Path.is_symlink
        with patch.object(
            Path,
            "is_symlink",
            autospec=True,
            side_effect=lambda candidate: candidate == link or real_is_symlink(candidate),
        ):
            self.assertIn("SYMLINK_FORBIDDEN", self._codes(root))


if __name__ == "__main__":
    unittest.main(verbosity=2)
