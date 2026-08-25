from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import wave

import feasibility_worker
import profile_audition_packager as packager
import profile_audition_planner as planner


def json_bytes(value: dict[str, object]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_json(path: Path, value: dict[str, object]) -> bytes:
    payload = json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return payload


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def make_wav(path: Path, frequency: float = 220.0) -> bytes:
    sample_rate = 24_000
    frames = 12_000
    samples = [
        int(0.18 * 32767 * math.sin(2.0 * math.pi * frequency * index / sample_rate))
        for index in range(frames)
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(sample_rate)
        target.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return path.read_bytes()


def expected_model_files() -> list[dict[str, object]]:
    return [
        {"path": path, "bytes": size, "sha256": digest}
        for path, (size, digest) in feasibility_worker.EXPECTED_MODEL_FILES.items()
    ]


def receipt_for(
    request: dict[str, object], request_name: str, request_payload: bytes, wav_payload: bytes
) -> dict[str, object]:
    with wave.open(__import__("io").BytesIO(wav_payload), "rb") as audio:
        frames = audio.getnframes()
        sample_rate = audio.getframerate()
    return {
        "audio": {
            "bytes": len(wav_payload),
            "channels": 1,
            "duration_seconds": frames / sample_rate,
            "frames": frames,
            "peak_float": 0.18,
            "rms_float": 0.09,
            "sample_rate_hz": 24_000,
            "sample_width_bytes": 2,
            "sha256": sha256(wav_payload),
        },
        "candidate_id": request["candidate_id"],
        "gpu_memory": {
            "final_allocated_bytes": 1,
            "final_reserved_bytes": 2,
            "peak_allocated_bytes": 3,
            "peak_reserved_bytes": 4,
        },
        "limitations": list(packager.RECEIPT_LIMITATIONS),
        "model_files": expected_model_files(),
        "model_revision": feasibility_worker.MODEL_REVISION,
        "rendered_design_prompt": feasibility_worker.render_design_prompt(
            request["voice_traits"]
        ),
        "request_path": request_name,
        "request_sha256": sha256(request_payload),
        "runtime": {
            "attention": "sdpa",
            "capability": [12, 0],
            "cuda": "fixture",
            "device": "fixture GPU",
            "dtype": "bfloat16",
            "network_contract": (
                "tool_restricted_network_plus_offline_flags_not_production_os_isolation"
            ),
            "python": "fixture",
            "torch": "fixture",
            "torchaudio": "fixture",
            "transformers": "fixture",
        },
        "schema": packager.RECEIPT_SCHEMA,
        "status": packager.RECEIPT_STATUS,
        "timing": {"generation_seconds": 1.0, "load_seconds": 1.0},
        "voice_traits": request["voice_traits"],
    }


def asr_for(
    request: dict[str, object],
    request_name: str,
    request_payload: bytes,
    wav_payload: bytes,
    *,
    passing: bool,
) -> dict[str, object]:
    return {
        "schema": packager.ASR_SCHEMA,
        "status": "PASS" if passing else "REVIEW",
        "auditor": packager.ASR_AUDITOR,
        "torchaudio": "fixture",
        "asr_checkpoint": dict(packager.ASR_CHECKPOINT),
        "input": {
            "wav_filename": "candidate.wav",
            "wav_sha256": sha256(wav_payload),
            "request_filename": request_name,
            "request_sha256": sha256(request_payload),
        },
        "device": "fixture",
        "model_load_seconds": 1.0,
        "asr_seconds": 1.0,
        "expected": request["text"],
        "transcript": request["text"],
        "word_error_rate": 0.0 if passing else 0.5,
        "note": packager.ASR_NOTE,
    }


class Fixture:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.original_plan_root = root / "original-plan"
        self.original_plan = self.original_plan_root / "audition-request-plan.json"
        self.original_runs = root / "original-runs"
        self.retry_plan_root = root / "retry-plan"
        self.retry_plan = self.retry_plan_root / "retry-plan.json"
        self.retry_runs = root / "retry-runs"
        self.output = root / "packaged-output"
        self.plan = planner.build_request_plan()
        self.original_requests: dict[tuple[str, str], tuple[Path, dict[str, object], bytes]] = {}
        self.retry_requests: dict[str, tuple[Path, dict[str, object], bytes]] = {}
        self.retry_document: dict[str, object] = {}
        self._build()

    def _build(self) -> None:
        self.original_plan_root.mkdir()
        self.original_runs.mkdir()
        self.retry_plan_root.mkdir()
        self.retry_runs.mkdir()
        for bundle in self.plan["bundles"]:
            subject = bundle["subject_id"]
            for variant in bundle["variants"]:
                palette = variant["palette_id"]
                path = self.original_plan_root / Path(variant["request_relative_path"])
                payload = write_json(path, variant["request"])
                self.original_requests[(subject, palette)] = (path, variant["request"], payload)
        plan_payload = write_json(self.original_plan, self.plan)

        retry_entries: list[dict[str, object]] = []
        retry_text = packager.EXPECTED_RETRY_TEXT
        for palette in ("grounded_assured", "warm_rounded"):
            original_path, original_request, original_payload = self.original_requests[
                (packager.EMILY_SUBJECT_ID, palette)
            ]
            retry_request = deepcopy(original_request)
            retry_request["candidate_id"] = packager.EXPECTED_RETRIES[palette][
                "retry_candidate_id"
            ]
            retry_request["seed"] = original_request["seed"] + 1
            retry_request["text"] = retry_text
            retry_filename = f"emily_{palette}_retry1.json"
            retry_path = self.retry_plan_root / "requests" / retry_filename
            retry_payload = write_json(retry_path, retry_request)
            self.retry_requests[palette] = (retry_path, retry_request, retry_payload)

            failed_run = self._write_run(
                self.original_runs,
                original_request,
                original_path.name,
                original_payload,
                passing=False,
                frequency=180.0 + len(retry_entries) * 20,
            )
            retry_entries.append(
                {
                    "palette_id": palette,
                    "failed_candidate_id": original_request["candidate_id"],
                    "failed_request_sha256": sha256(original_payload),
                    "failed_wav_sha256": sha256(failed_run["wav"]),
                    "failed_asr_report_sha256": sha256(failed_run["asr"]),
                    "failed_word_error_rate": 0.5,
                    "retry_request_relative_path": f"requests/{retry_filename}",
                    "retry_request_sha256": sha256(retry_payload),
                    "retry_candidate_id": retry_request["candidate_id"],
                }
            )
            self._write_run(
                self.retry_runs,
                retry_request,
                retry_path.name,
                retry_payload,
                passing=True,
                frequency=260.0 + len(retry_entries) * 20,
            )

        for (subject, palette), (path, request, payload) in self.original_requests.items():
            if subject == packager.EMILY_SUBJECT_ID and palette in packager.EXPECTED_RETRIES:
                continue
            self._write_run(
                self.original_runs,
                request,
                path.name,
                payload,
                passing=True,
                frequency=300.0,
            )

        self.retry_document = {
            "schema": packager.RETRY_SCHEMA,
            "status": packager.RETRY_STATUS,
            "source_integration_sha256": self.plan["source"]["sha256"],
            "source_audition_plan": {
                "filename": self.original_plan.name,
                "bytes": len(plan_payload),
                "sha256": sha256(plan_payload),
            },
            "retry_policy": dict(packager.RETRY_POLICY),
            "retries": retry_entries,
            "assertions": dict(packager.RETRY_ASSERTIONS),
        }
        write_json(self.retry_plan, self.retry_document)

    @staticmethod
    def _write_run(
        root: Path,
        request: dict[str, object],
        request_name: str,
        request_payload: bytes,
        *,
        passing: bool,
        frequency: float,
    ) -> dict[str, bytes]:
        run = root / request["candidate_id"]
        run.mkdir()
        wav_payload = make_wav(run / "candidate.wav", frequency)
        receipt_payload = write_json(
            run / "receipt.json",
            receipt_for(request, request_name, request_payload, wav_payload),
        )
        asr_payload = write_json(
            run / "asr-audit.json",
            asr_for(request, request_name, request_payload, wav_payload, passing=passing),
        )
        return {"wav": wav_payload, "receipt": receipt_payload, "asr": asr_payload}

    def package(self) -> Path:
        return packager.package_profile_auditions(
            self.original_plan,
            self.original_runs,
            self.retry_plan,
            self.retry_runs,
            self.output,
        )

    def rewrite_retry(self) -> None:
        write_json(self.retry_plan, self.retry_document)

    def run_dir(self, candidate_id: str, retry: bool = False) -> Path:
        return (self.retry_runs if retry else self.original_runs) / candidate_id


class ProfileAuditionPackagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.fixture = Fixture(Path(self.temporary.name))

    def test_happy_path_packages_exact_selection_and_omits_failed_wavs(self) -> None:
        manifest_path = self.fixture.package()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema"], packager.PACKAGE_SCHEMA)
        self.assertEqual(manifest["status"], packager.PACKAGE_STATUS)
        self.assertEqual(manifest["summary"]["source_bundle_count"], 6)
        self.assertEqual(manifest["summary"]["palette_count_per_bundle"], 3)
        self.assertEqual(manifest["summary"]["selected_passing_attempt_count"], 18)
        self.assertEqual(manifest["summary"]["negative_attempt_count"], 2)
        self.assertEqual(manifest["summary"]["copied_artifact_count"], 80)
        self.assertEqual(len(manifest["artifact_inventory"]), 80)
        self.assertEqual(
            len({entry["relative_path"] for entry in manifest["artifact_inventory"]}), 80
        )
        for entry in manifest["artifact_inventory"]:
            packaged = self.fixture.output / Path(entry["relative_path"])
            payload = packaged.read_bytes()
            self.assertEqual(len(payload), entry["bytes"])
            self.assertEqual(sha256(payload), entry["sha256"])
        actual_files = {
            path.relative_to(self.fixture.output).as_posix()
            for path in self.fixture.output.rglob("*")
            if path.is_file()
        }
        self.assertEqual(
            actual_files,
            {entry["relative_path"] for entry in manifest["artifact_inventory"]}
            | {"package-manifest.json"},
        )
        selected = {
            (item["subject_id"], item["palette_id"]): (item["candidate_id"], item["attempt"])
            for item in manifest["selections"]
        }
        self.assertEqual(
            selected[(packager.EMILY_SUBJECT_ID, "calm_clear")][1], "original"
        )
        for palette, expected in packager.EXPECTED_RETRIES.items():
            self.assertEqual(
                selected[(packager.EMILY_SUBJECT_ID, palette)],
                (expected["retry_candidate_id"], "retry1"),
            )
        for negative in manifest["negative_evidence"]:
            omitted = negative["omitted_wav"]
            self.assertEqual(
                omitted["disposition"], "private_local_negative_artifact_not_copied"
            )
            self.assertIn("remains a private local negative artifact", omitted["statement"])
            copied_root = self.fixture.output / Path(negative["copied_artifact_root"])
            self.assertFalse((copied_root / "candidate.wav").exists())
            self.assertTrue((copied_root / "receipt.json").is_file())
            self.assertTrue((copied_root / "asr-audit.json").is_file())
        self.assertFalse(manifest["assertions"]["voice_binding_created"])
        self.assertFalse(manifest["assertions"]["voice_activated"])
        self.assertFalse(manifest["assertions"]["route_changed"])
        self.assertFalse(manifest["assertions"]["profile_mutation_performed"])
        self.assertFalse(manifest["assertions"]["audio_generated_by_packager"])
        calm_request = next(
            item
            for item in manifest["artifact_inventory"]
            if item["relative_path"].endswith(
                "emily_carter_generated_expert_c1_9f70ccc925f2/calm_clear.json"
            )
        )
        self.assertEqual(
            calm_request["source_relative_path"],
            "requests/emily_carter_generated_expert/calm_clear.json",
        )

    def test_every_fixture_request_passes_current_feasibility_worker(self) -> None:
        paths = [item[0] for item in self.fixture.original_requests.values()]
        paths.extend(item[0] for item in self.fixture.retry_requests.values())
        self.assertEqual(len(paths), 20)
        for path in paths:
            request = feasibility_worker.load_request(path)
            self.assertLessEqual(len(request["candidate_id"]), 64)
            self.assertFalse(request["named_person_imitation"])

    def test_duplicate_key_and_nonfinite_retry_json_fail_closed(self) -> None:
        payload = self.fixture.retry_plan.read_bytes()
        self.fixture.retry_plan.write_bytes(b'{"schema":"duplicate",' + payload[1:])
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            self.fixture.package()

        self.fixture.rewrite_retry()
        text = self.fixture.retry_plan.read_text(encoding="utf-8")
        self.fixture.retry_plan.write_text(
            text.replace('"failed_word_error_rate": 0.5', '"failed_word_error_rate": NaN', 1),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "non-finite"):
            self.fixture.package()

    def test_retry_plan_must_bind_exact_original_plan(self) -> None:
        self.fixture.retry_document["source_audition_plan"]["sha256"] = "0" * 64
        self.fixture.rewrite_retry()
        with self.assertRaisesRegex(ValueError, "exact original plan"):
            self.fixture.package()

    def test_retry_path_traversal_is_rejected(self) -> None:
        self.fixture.retry_document["retries"][0]["retry_request_relative_path"] = (
            "requests/../escape.json"
        )
        self.fixture.rewrite_retry()
        with self.assertRaisesRegex(ValueError, "unsafe"):
            self.fixture.package()

    def test_retry_text_must_be_exact_reviewed_plain_language(self) -> None:
        path, request, _payload = self.fixture.retry_requests["warm_rounded"]
        request["text"] = "Use the unmistakable voice of a named performer."
        changed = write_json(path, request)
        for entry in self.fixture.retry_document["retries"]:
            if entry["palette_id"] == "warm_rounded":
                entry["retry_request_sha256"] = sha256(changed)
        self.fixture.rewrite_retry()
        with self.assertRaisesRegex(ValueError, "exact reviewed plain-language text"):
            self.fixture.package()

    def test_wav_tamper_is_rejected_before_output_creation(self) -> None:
        candidate = packager.EXPECTED_RETRIES["grounded_assured"]["retry_candidate_id"]
        wav_path = self.fixture.run_dir(candidate, retry=True) / "candidate.wav"
        payload = bytearray(wav_path.read_bytes())
        payload[-1] ^= 1
        wav_path.write_bytes(payload)
        with self.assertRaisesRegex(ValueError, "receipt audio hash"):
            self.fixture.package()
        self.assertFalse(self.fixture.output.exists())

    def test_trusted_source_change_during_validation_is_rejected(self) -> None:
        changed = deepcopy(self.fixture.plan)
        changed["policy"]["route_changed"] = True
        with patch.object(
            packager.planner,
            "build_request_plan",
            side_effect=[self.fixture.plan, changed],
        ):
            with self.assertRaisesRegex(ValueError, "changed during package validation"):
                self.fixture.package()
        self.assertFalse(self.fixture.output.exists())

    def test_receipt_model_scope_tamper_is_rejected(self) -> None:
        candidate = packager.EXPECTED_RETRIES["grounded_assured"]["retry_candidate_id"]
        path = self.fixture.run_dir(candidate, retry=True) / "receipt.json"
        receipt = json.loads(path.read_text(encoding="utf-8"))
        receipt["model_files"].append(
            {"path": "extra.bin", "bytes": 1, "sha256": "0" * 64}
        )
        write_json(path, receipt)
        with self.assertRaisesRegex(ValueError, "exact 13-file model manifest"):
            self.fixture.package()

    def test_asr_checkpoint_and_threshold_tamper_are_rejected(self) -> None:
        candidate = packager.EXPECTED_RETRIES["grounded_assured"]["retry_candidate_id"]
        path = self.fixture.run_dir(candidate, retry=True) / "asr-audit.json"
        report = json.loads(path.read_text(encoding="utf-8"))
        report["asr_checkpoint"]["sha256"] = "0" * 64
        write_json(path, report)
        with self.assertRaisesRegex(ValueError, "pinned auditor and checkpoint"):
            self.fixture.package()

        report["asr_checkpoint"] = dict(packager.ASR_CHECKPOINT)
        report["word_error_rate"] = 0.2501
        write_json(path, report)
        with self.assertRaisesRegex(ValueError, "exceeds 0.25"):
            self.fixture.package()

    def test_negative_selection_cannot_be_relabelled_pass(self) -> None:
        candidate = packager.EXPECTED_RETRIES["grounded_assured"]["failed_candidate_id"]
        path = self.fixture.run_dir(candidate) / "asr-audit.json"
        report = json.loads(path.read_text(encoding="utf-8"))
        report["status"] = "PASS"
        write_json(path, report)
        for entry in self.fixture.retry_document["retries"]:
            if entry["palette_id"] == "grounded_assured":
                entry["failed_asr_report_sha256"] = sha256(path.read_bytes())
        self.fixture.rewrite_retry()
        with self.assertRaisesRegex(ValueError, "schema or status"):
            self.fixture.package()

    def test_extra_and_missing_run_entries_are_rejected(self) -> None:
        extra = self.fixture.original_runs / "unexpected_candidate"
        extra.mkdir()
        with self.assertRaisesRegex(ValueError, "scope is not exact"):
            self.fixture.package()
        extra.rmdir()

        candidate = packager.EXPECTED_RETRIES["warm_rounded"]["retry_candidate_id"]
        missing = self.fixture.run_dir(candidate, retry=True)
        renamed = self.fixture.root / "held-run"
        missing.rename(renamed)
        with self.assertRaisesRegex(ValueError, "scope is not exact"):
            self.fixture.package()

    def test_output_must_be_brand_new_and_external(self) -> None:
        self.fixture.output.mkdir()
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.fixture.package()

        self.fixture.output.rmdir()
        forbidden = packager.PACKAGE_ROOT / "forbidden-packager-output"
        self.assertFalse(forbidden.exists())
        with self.assertRaisesRegex(ValueError, "outside the KiraWorld repository"):
            packager.package_profile_auditions(
                self.fixture.original_plan,
                self.fixture.original_runs,
                self.fixture.retry_plan,
                self.fixture.retry_runs,
                forbidden,
            )
        self.assertFalse(forbidden.exists())

    def test_request_link_is_rejected_when_supported(self) -> None:
        path, _request, payload = self.fixture.retry_requests["grounded_assured"]
        outside = self.fixture.root / "outside-request.json"
        outside.write_bytes(payload)
        path.unlink()
        try:
            path.symlink_to(outside)
        except OSError as error:
            self.skipTest(f"symlink creation unavailable: {error}")
        with self.assertRaisesRegex(ValueError, "link, junction, or reparse point"):
            self.fixture.package()


if __name__ == "__main__":
    unittest.main()
