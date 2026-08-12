from __future__ import annotations

import array
import ast
import contextlib
import io
import json
import tempfile
import unittest
import wave
from copy import deepcopy
from pathlib import Path

from Core.local_voice_workshop import (
    OWNER_PREVIEW_APPROVAL_TEXT,
    OWNER_PROMOTION_APPROVAL_TEXT,
    OWNER_ROLLBACK_APPROVAL_TEXT,
    VoiceWorkshopError,
    append_candidate_review,
    create_preview_request,
    create_promotion_proposal,
    create_rollback_proposal,
    file_sha256,
    initialize_version,
    inspect_pcm_wav,
    record_owner_approval,
    record_preview_result,
    select_clean_master,
    validate_history,
    validate_permission_record,
    verify_version,
)
from tools.local_voice_workshop import main as workshop_cli_main


UTC = "2026-08-08T12:00:00Z"


class LocalVoiceWorkshopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.source = self._write_wav("inputs/source.wav", 12.0)
        self.candidate_a = self._write_wav("inputs/candidate_a.wav", 7.5, amplitude=5000)
        self.candidate_b = self._write_wav("inputs/candidate_b.wav", 8.0, amplitude=7000)
        self.profile = self._write_json(
            "artifacts/alice_profile.json",
            {"record_type": "inactive_voice_profile", "profile_id": "alice_voice"},
        )
        self.config = self._write_json(
            "artifacts/chatterbox_config.json",
            {"engine": "chatterbox_tts", "version": "0.1.7", "inactive": True},
        )
        self.worker = self.root / "artifacts" / "sealed_worker.py"
        self.worker.write_text("# inert test evidence file\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _project_relative(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def _write_json(self, relative: str, value: dict) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        return path

    def _write_wav(
        self,
        relative: str,
        duration: float,
        *,
        amplitude: int = 6000,
        sample_rate: int = 24000,
        channels: int = 1,
    ) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        frame_count = int(round(duration * sample_rate))
        mono = array.array(
            "h", (amplitude if index % 2 == 0 else -amplitude for index in range(frame_count))
        )
        if channels == 1:
            samples = mono
        else:
            samples = array.array("h")
            for sample in mono:
                samples.extend([sample] * channels)
        with wave.open(str(path), "wb") as writer:
            writer.setnchannels(channels)
            writer.setsampwidth(2)
            writer.setframerate(sample_rate)
            writer.writeframes(samples.tobytes())
        return path

    def _permission(self) -> dict:
        return {
            "record_type": "permission_record",
            "permission_id": "permission-alice-001",
            "person_id": "alice",
            "profile_id": "alice_voice",
            "source": {
                "source_id": "alice-source-001",
                "speaker_id": "alice",
                "path": self._project_relative(self.source),
                "sha256": file_sha256(self.source),
                "recording_kind": "direct clean recording",
                "language": "en-US",
                "provenance": {
                    "origin": "owner-supplied local recording",
                    "recorder_or_publisher": "alice",
                    "chain_of_custody": "Alice supplied the exact local WAV to Robert for this private profile.",
                },
            },
            "rights": {
                "speaker_consent_confirmed": True,
                "recording_rights_confirmed": True,
                "recording_possession_and_processing": True,
                "voice_model_conditioning_rights_confirmed": True,
                "voice_conditioning_private_local": True,
                "named_person_private_local_synthesis": True,
                "public_distribution": False,
                "commercial_use": False,
            },
            "confirmed_by": {
                "authority_id": "owner-robert",
                "confirmation_text": "I confirm the exact named speaker granted these private local voice rights.",
                "confirmed_at": UTC,
            },
            "revoked": False,
        }

    def _version_relative(self, version_id: str) -> Path:
        return Path("Voice") / "workshop" / "alice" / "alice_voice" / version_id

    def _initialize(self, version_id: str = "v001", parent: str = "") -> Path:
        relative = self._version_relative(version_id)
        initialize_version(
            relative,
            {
                "person_id": "alice",
                "profile_id": "alice_voice",
                "version_id": version_id,
                "parent_version_id": parent,
                "created_by": "owner-robert",
                "created_at": UTC,
                "permission_record": self._permission(),
            },
            project_root=self.root,
        )
        return relative

    def _review(
        self,
        version: Path,
        *,
        version_id: str,
        review_id: str,
        candidate: Path,
        start: float,
        end: float,
        decision: str = "accepted_clean_master_candidate",
    ) -> dict:
        return append_candidate_review(
            version,
            {
                "review_id": review_id,
                "person_id": "alice",
                "profile_id": "alice_voice",
                "version_id": version_id,
                "decision": decision,
                "candidate": {
                    "path": self._project_relative(candidate),
                    "sha256": file_sha256(candidate),
                    "source_path": self._project_relative(self.source),
                    "source_sha256": file_sha256(self.source),
                    "source_start_seconds": start,
                    "source_end_seconds": end,
                    "derivation_method": "single_contiguous_clip_no_concatenation",
                },
                "human_review": {
                    "reviewer_id": "owner-robert",
                    "reviewed_at": UTC,
                    "review_statement": "The exact context and this contiguous clip were reviewed manually.",
                    "exact_source_context_opened": True,
                    "target_identity_confirmed": True,
                    "target_only_speech": True,
                    "no_overlapping_speech": True,
                    "no_music": True,
                    "no_material_sound_effects": True,
                    "no_material_background_noise": True,
                    "no_material_reverb": True,
                    "stable_delivery": True,
                    "transcript": "A clean private local preview sentence.",
                },
            },
            project_root=self.root,
        )

    def _select(self, version: Path, version_id: str, suffix: str) -> dict:
        return select_clean_master(
            version,
            {
                "selection_id": f"selection-{suffix}",
                "selected_by": "owner-robert",
                "selected_at": UTC,
            },
            project_root=self.root,
        )

    def _build_approved_promotion(self, version_id: str, *, parent: str = "") -> dict:
        suffix = version_id
        version = self._initialize(version_id, parent)
        self._review(
            version,
            version_id=version_id,
            review_id=f"review-{suffix}",
            candidate=self.candidate_b,
            start=1.0,
            end=9.0,
        )
        selection = self._select(version, version_id, suffix)
        version_abs = self.root / version
        selection_rel = f"selections/selection-{suffix}.json"
        selection_path = version_abs / selection_rel
        preview = create_preview_request(
            version,
            {
                "preview_id": f"preview-{suffix}",
                "requested_by": "owner-robert",
                "requested_at": UTC,
                "selection_path": selection_rel,
                "selection_sha256": file_sha256(selection_path),
                "profile_path": self._project_relative(self.profile),
                "profile_sha256": file_sha256(self.profile),
                "model_contract": {
                    "engine": "chatterbox_tts",
                    "model_name": "chatterbox-tts",
                    "model_version": "0.1.7",
                    "config_path": self._project_relative(self.config),
                    "config_sha256": file_sha256(self.config),
                },
                "phrases": [
                    {"phrase_id": "greeting", "text": "Hello Robert. This is an inactive preview."}
                ],
                "playback_allowed": False,
                "auto_activate": False,
                "generic_voice_fallback_allowed": False,
                "sapi_fallback_allowed": False,
            },
            project_root=self.root,
        )
        request_rel = f"previews/requests/preview-{suffix}.json"
        request_path = version_abs / request_rel
        preview_wav = self._write_wav(
            f"{version.as_posix()}/preview_audio/greeting.wav", 0.5
        )
        result = record_preview_result(
            version,
            {
                "result_id": f"result-{suffix}",
                "recorded_by": "acceptance-harness",
                "recorded_at": UTC,
                "request_path": request_rel,
                "request_sha256": file_sha256(request_path),
                "route": {
                    "engine": "chatterbox_tts",
                    "profile_sha256": preview["profile_sha256"],
                    "reference_sha256": preview["reference_sha256"],
                    "generic_voice_used": False,
                    "sapi_voice_used": False,
                    "playback": False,
                },
                "outputs": [
                    {
                        "phrase_id": "greeting",
                        "text_sha256": preview["phrases"][0]["text_sha256"],
                        "path": self._project_relative(preview_wav),
                        "sha256": file_sha256(preview_wav),
                    }
                ],
            },
            project_root=self.root,
        )
        result_rel = f"previews/results/result-{suffix}.json"
        result_path = version_abs / result_rel
        preview_approval = record_owner_approval(
            version,
            {
                "approval_id": f"preview-approval-{suffix}",
                "approval_kind": "preview",
                "owner_id": "owner-robert",
                "approved_at": UTC,
                "confirmation_text": OWNER_PREVIEW_APPROVAL_TEXT,
                "target_path": result_rel,
                "target_sha256": file_sha256(result_path),
            },
            project_root=self.root,
        )
        acceptance_gpu = self._write_json(
            f"{version.as_posix()}/seals/acceptance-gpu.json",
            {"status": "passed", "device": "cuda", "version_id": version_id},
        )
        acceptance_cpu = self._write_json(
            f"{version.as_posix()}/seals/acceptance-cpu.json",
            {"status": "passed", "device": "cpu", "version_id": version_id},
        )
        reference_path = selection["selected"]["candidate"]["path"]
        common = {
            "record_type": "sealed_route_receipt",
            "schema_version": 1,
            "status": "sealed_accepted",
            "engine": "chatterbox_tts",
            "person_id": "alice",
            "profile_id": "alice_voice",
            "version_id": version_id,
            "input_channel": "public_spoken_only",
            "offline_cache_only": True,
            "playback": False,
            "generic_voice_fallback_allowed": False,
            "sapi_fallback_allowed": False,
            "separately_sealed": True,
            "profile_path": self._project_relative(self.profile),
            "profile_sha256": file_sha256(self.profile),
            "reference_path": reference_path,
            "reference_sha256": selection["selected"]["candidate"]["sha256"],
            "worker_path": self._project_relative(self.worker),
            "worker_sha256": file_sha256(self.worker),
            "config_path": self._project_relative(self.config),
            "config_sha256": file_sha256(self.config),
        }
        gpu = {
            **common,
            "seal_id": f"gpu-seal-{suffix}",
            "compute_device": "cuda",
            "route_role": "preferred",
            "acceptance_path": self._project_relative(acceptance_gpu),
            "acceptance_sha256": file_sha256(acceptance_gpu),
        }
        cpu = {
            **common,
            "seal_id": f"cpu-seal-{suffix}",
            "compute_device": "cpu",
            "route_role": "same_identity_automatic_fallback_only",
            "acceptance_path": self._project_relative(acceptance_cpu),
            "acceptance_sha256": file_sha256(acceptance_cpu),
        }
        gpu_path = self._write_json(f"{version.as_posix()}/seals/gpu.json", gpu)
        cpu_path = self._write_json(f"{version.as_posix()}/seals/cpu.json", cpu)
        preview_approval_rel = f"approvals/preview-approval-{suffix}.json"
        proposal = create_promotion_proposal(
            version,
            {
                "proposal_id": f"promotion-{suffix}",
                "proposed_by": "owner-robert",
                "proposed_at": UTC,
                "selection_path": selection_rel,
                "selection_sha256": file_sha256(selection_path),
                "preview_result_path": result_rel,
                "preview_result_sha256": file_sha256(result_path),
                "preview_approval_path": preview_approval_rel,
                "preview_approval_sha256": file_sha256(version_abs / preview_approval_rel),
                "profile_path": self._project_relative(self.profile),
                "profile_sha256": file_sha256(self.profile),
                "gpu_seal_path": gpu_path.relative_to(version_abs).as_posix(),
                "gpu_seal_sha256": file_sha256(gpu_path),
                "cpu_seal_path": cpu_path.relative_to(version_abs).as_posix(),
                "cpu_seal_sha256": file_sha256(cpu_path),
                "rollback_target": None,
            },
            project_root=self.root,
        )
        proposal_rel = f"proposals/promotion/promotion-{suffix}.json"
        proposal_path = version_abs / proposal_rel
        promotion_approval = record_owner_approval(
            version,
            {
                "approval_id": f"promotion-approval-{suffix}",
                "approval_kind": "promotion",
                "owner_id": "owner-robert",
                "approved_at": UTC,
                "confirmation_text": OWNER_PROMOTION_APPROVAL_TEXT,
                "target_path": proposal_rel,
                "target_sha256": file_sha256(proposal_path),
            },
            project_root=self.root,
        )
        promotion_approval_rel = f"approvals/promotion-approval-{suffix}.json"
        return {
            "version": version,
            "selection": selection,
            "preview": preview,
            "result": result,
            "preview_approval": preview_approval,
            "proposal": proposal,
            "promotion_approval": promotion_approval,
            "proposal_path": proposal_path,
            "approval_path": version_abs / promotion_approval_rel,
        }

    def test_wav_inspection_accepts_clean_and_rejects_bad_signal_or_format(self) -> None:
        clean = inspect_pcm_wav(
            self.candidate_b, project_root=self.root, purpose="master_candidate"
        )
        self.assertTrue(clean["passed"])
        self.assertEqual(clean["duration_seconds"], 8.0)
        self.assertFalse(clean["operation"]["audio_played"])
        self.assertFalse(clean["operation"]["audio_generated"])
        short = self._write_wav("inputs/short.wav", 5.9)
        self.assertIn(
            "master_duration_must_be_6_to_10_seconds",
            inspect_pcm_wav(short, project_root=self.root, purpose="master_candidate")["reasons"],
        )
        clipped = self._write_wav("inputs/clipped.wav", 8.0, amplitude=32760)
        self.assertIn(
            "clipping_ratio_above_0_001",
            inspect_pcm_wav(clipped, project_root=self.root, purpose="master_candidate")["reasons"],
        )
        silent = self._write_wav("inputs/silent.wav", 8.0, amplitude=0)
        self.assertIn(
            "wav_is_silent",
            inspect_pcm_wav(silent, project_root=self.root, purpose="master_candidate")["reasons"],
        )
        stereo = self._write_wav("inputs/stereo.wav", 8.0, channels=2)
        self.assertIn(
            "wav_must_be_mono",
            inspect_pcm_wav(stereo, project_root=self.root, purpose="master_candidate")["reasons"],
        )

    def test_permission_requires_exact_identity_consent_rights_and_provenance(self) -> None:
        valid = validate_permission_record(self._permission(), project_root=self.root)
        self.assertEqual(valid["person_id"], "alice")
        self.assertFalse(valid["public_or_commercial_authority_granted"])
        missing = self._permission()
        missing["rights"]["speaker_consent_confirmed"] = False
        with self.assertRaisesRegex(VoiceWorkshopError, "speaker_consent_confirmed"):
            validate_permission_record(missing, project_root=self.root)
        wrong_speaker = self._permission()
        wrong_speaker["source"]["speaker_id"] = "someone_else"
        with self.assertRaisesRegex(VoiceWorkshopError, "speaker_id"):
            validate_permission_record(wrong_speaker, project_root=self.root)

    def test_initialization_is_inactive_immutable_and_fully_history_bound(self) -> None:
        version = self._initialize()
        version_abs = self.root / version
        manifest = json.loads((version_abs / "version_manifest.json").read_text())
        self.assertTrue(all(value is False for value in manifest["boundaries"].values()))
        self.assertEqual(list(version_abs.rglob("*.wav")), [])
        self.assertEqual(len(validate_history(version_abs)), 3)
        self.assertEqual(verify_version(version, project_root=self.root)["history_event_count"], 3)
        with self.assertRaisesRegex(VoiceWorkshopError, "already exists"):
            self._initialize()
        permission_path = version_abs / "permission_record.json"
        changed = json.loads(permission_path.read_text())
        changed["confirmed_by"]["confirmation_text"] += " changed"
        permission_path.write_text(json.dumps(changed), encoding="utf-8")
        with self.assertRaisesRegex(VoiceWorkshopError, "History-bound record changed"):
            verify_version(version, project_root=self.root)

    def test_candidate_requires_contiguous_exact_source_interval(self) -> None:
        version = self._initialize()
        accepted = self._review(
            version,
            version_id="v001",
            review_id="review-good",
            candidate=self.candidate_b,
            start=1.0,
            end=9.0,
        )
        self.assertTrue(accepted["technical_report"]["passed"])
        bad = deepcopy(accepted)
        bad.pop("record_type", None)
        bad.pop("technical_report", None)
        bad["review_id"] = "review-bad-interval"
        bad["candidate"]["source_end_seconds"] = 8.5
        with self.assertRaisesRegex(VoiceWorkshopError, "duration does not match"):
            append_candidate_review(version, bad, project_root=self.root)
        bad_method = deepcopy(bad)
        bad_method["review_id"] = "review-bad-method"
        bad_method["candidate"]["source_end_seconds"] = 9.0
        bad_method["candidate"]["derivation_method"] = "concatenated"
        with self.assertRaisesRegex(VoiceWorkshopError, "no concatenation"):
            append_candidate_review(version, bad_method, project_root=self.root)

    def test_deterministic_selection_and_later_rejection(self) -> None:
        version = self._initialize()
        self._review(
            version,
            version_id="v001",
            review_id="review-a",
            candidate=self.candidate_a,
            start=0.0,
            end=7.5,
        )
        self._review(
            version,
            version_id="v001",
            review_id="review-b",
            candidate=self.candidate_b,
            start=1.0,
            end=9.0,
        )
        first = self._select(version, "v001", "first")
        self.assertEqual(first["selected"]["candidate"]["sha256"], file_sha256(self.candidate_b))
        self.assertFalse(first["long_concatenation_used"])
        self.assertFalse(first["audio_created"])
        self._review(
            version,
            version_id="v001",
            review_id="review-b-rejected",
            candidate=self.candidate_b,
            start=1.0,
            end=9.0,
            decision="rejected",
        )
        second = self._select(version, "v001", "second")
        self.assertEqual(second["selected"]["candidate"]["sha256"], file_sha256(self.candidate_a))

    def test_preview_is_hash_bound_external_unplayed_and_fail_closed(self) -> None:
        built = self._build_approved_promotion("v001")
        preview = built["preview"]
        result = built["result"]
        self.assertFalse(preview["playback_allowed"])
        self.assertFalse(preview["generic_voice_fallback_allowed"])
        self.assertFalse(preview["sapi_fallback_allowed"])
        self.assertFalse(preview["workshop_generated_audio"])
        self.assertTrue(result["generated_by_external_harness"])
        self.assertFalse(result["playback_performed_by_workshop"])
        self.assertFalse(result["activation_performed"])
        self.assertEqual(result["route"]["engine"], "chatterbox_tts")
        with self.assertRaisesRegex(VoiceWorkshopError, "already exists"):
            record_owner_approval(
                built["version"],
                {
                    "approval_id": "preview-approval-v001",
                    "approval_kind": "preview",
                    "owner_id": "owner-robert",
                    "approved_at": UTC,
                    "confirmation_text": OWNER_PREVIEW_APPROVAL_TEXT,
                    "target_path": "previews/results/result-v001.json",
                    "target_sha256": file_sha256(
                        self.root / built["version"] / "previews/results/result-v001.json"
                    ),
                },
                project_root=self.root,
            )

    def test_owner_approval_requires_exact_sentence_and_target_hash(self) -> None:
        built = self._build_approved_promotion("v001")
        with self.assertRaisesRegex(VoiceWorkshopError, "Exact owner confirmation"):
            record_owner_approval(
                built["version"],
                {
                    "approval_id": "bad-approval",
                    "approval_kind": "promotion",
                    "owner_id": "owner-robert",
                    "approved_at": UTC,
                    "confirmation_text": "yes",
                    "target_path": "proposals/promotion/promotion-v001.json",
                    "target_sha256": file_sha256(built["proposal_path"]),
                },
                project_root=self.root,
            )
        self.assertEqual(
            built["promotion_approval"]["confirmation_text"], OWNER_PROMOTION_APPROVAL_TEXT
        )

    def test_promotion_requires_separate_gpu_and_same_identity_cpu_receipts(self) -> None:
        built = self._build_approved_promotion("v001")
        proposal = built["proposal"]
        self.assertEqual(proposal["preferred_route"]["device"], "cuda")
        self.assertEqual(proposal["automatic_fallback"]["device"], "cpu")
        self.assertTrue(proposal["automatic_fallback"]["same_exact_identity"])
        self.assertFalse(proposal["policy"]["generic_voice_fallback_allowed"])
        self.assertFalse(proposal["policy"]["sapi_fallback_allowed"])
        self.assertEqual(
            proposal["policy"]["fallback_if_both_sealed_routes_fail"],
            "text_only_voice_unavailable",
        )
        self.assertFalse(proposal["activation_performed"])
        self.assertFalse(proposal["default_changed"])
        self.assertFalse(proposal["apply_operation_exists"])

    def test_cross_version_rollback_is_only_an_inactive_exact_proposal(self) -> None:
        target = self._build_approved_promotion("v001")
        current = self._build_approved_promotion("v002", parent="v001")
        rollback = create_rollback_proposal(
            current["version"],
            {
                "rollback_id": "rollback-v002-to-v001",
                "proposed_by": "owner-robert",
                "proposed_at": UTC,
                "current_proposal_path": self._project_relative(current["proposal_path"]),
                "current_proposal_sha256": file_sha256(current["proposal_path"]),
                "current_approval_path": self._project_relative(current["approval_path"]),
                "current_approval_sha256": file_sha256(current["approval_path"]),
                "target_proposal_path": self._project_relative(target["proposal_path"]),
                "target_proposal_sha256": file_sha256(target["proposal_path"]),
                "target_approval_path": self._project_relative(target["approval_path"]),
                "target_approval_sha256": file_sha256(target["approval_path"]),
            },
            project_root=self.root,
        )
        self.assertEqual(rollback["current"]["version_id"], "v002")
        self.assertEqual(rollback["target"]["version_id"], "v001")
        self.assertTrue(rollback["requires_exact_owner_rollback_approval"])
        self.assertFalse(rollback["activation_performed"])
        self.assertFalse(rollback["default_changed"])
        self.assertFalse(rollback["apply_operation_exists"])
        rollback_path = (
            self.root
            / current["version"]
            / "proposals/rollback/rollback-v002-to-v001.json"
        )
        approval = record_owner_approval(
            current["version"],
            {
                "approval_id": "rollback-approval-v002-to-v001",
                "approval_kind": "rollback",
                "owner_id": "owner-robert",
                "approved_at": UTC,
                "confirmation_text": OWNER_ROLLBACK_APPROVAL_TEXT,
                "target_path": "proposals/rollback/rollback-v002-to-v001.json",
                "target_sha256": file_sha256(rollback_path),
            },
            project_root=self.root,
        )
        self.assertEqual(approval["confirmation_text"], OWNER_ROLLBACK_APPROVAL_TEXT)
        self.assertFalse(approval["activation_performed"])

    def test_cli_schema_and_sources_expose_no_audio_or_runtime_action(self) -> None:
        repository_root = Path(__file__).resolve().parents[1]
        schema = json.loads(
            (repository_root / "System/Schemas/local_voice_workshop_v1.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("oneOf", schema)
        core_source = (repository_root / "Core/local_voice_workshop.py").read_text(
            encoding="utf-8"
        )
        cli_source = (repository_root / "tools/local_voice_workshop.py").read_text(
            encoding="utf-8"
        )
        banned_imports = {"torch", "chatterbox", "subprocess", "winsound", "sounddevice", "pyaudio"}
        for source in (core_source, cli_source):
            tree = ast.parse(source)
            imported: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".")[0])
            self.assertTrue(banned_imports.isdisjoint(imported))
        for forbidden_command in ("generate", "play", "activate", "apply", "set-default"):
            self.assertNotIn(f'add_parser("{forbidden_command}"', cli_source)
        with contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(
            io.StringIO()
        ):
            exit_code = workshop_cli_main(
                [
                    "inspect-wav",
                    "--wav",
                    self._project_relative(self.candidate_b),
                    "--purpose",
                    "master_candidate",
                ]
            )
        # The real CLI is project-root bound, so a temp-project path must fail closed.
        self.assertEqual(exit_code, 2)
        self.assertEqual(output.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
