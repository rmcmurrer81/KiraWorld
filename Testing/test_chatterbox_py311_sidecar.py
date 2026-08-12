from __future__ import annotations

import hashlib
import json
import os
import subprocess
import unittest
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "Voice" / "sidecars" / "chatterbox_py311"
CONFIG = SIDECAR / "sidecar_config.json"
WORKER = SIDECAR / "sidecar_worker.py"
PYTHON = SIDECAR / ".venv" / "Scripts" / "python.exe"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ChatterboxPy311SidecarTests(unittest.TestCase):
    def test_sealed_config_preserves_exact_kira_voice_and_dependency_manifest(self) -> None:
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(config["python_version"], "3.11.9")
        self.assertEqual(config["chatterbox_version"], "0.1.7")
        self.assertEqual(config["compute_device"], "cpu")
        self.assertFalse(config["playback"])
        self.assertFalse(config["generic_voice_fallback_allowed"])
        self.assertEqual(config["input_channel"], "public_spoken_only")
        self.assertEqual(sha256_file(WORKER), config["worker_sha256"])
        for path_key, hash_key in (
            ("dependency_manifest", "dependency_manifest_sha256"),
            ("approved_profile", "approved_profile_sha256"),
            ("approved_reference", "approved_reference_sha256"),
        ):
            path = ROOT / config[path_key]
            self.assertTrue(path.is_file())
            self.assertEqual(sha256_file(path), config[hash_key])

    def test_dependency_manifest_has_archive_hashes_and_exact_runtime_versions(self) -> None:
        manifest = json.loads((SIDECAR / "evidence" / "dependency_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["python"]["version"], "3.11.9")
        self.assertEqual(manifest["pip_check"], "No broken requirements found.")
        self.assertEqual(manifest["installed_distribution_count"], 113)
        records = {item["name"].casefold(): item for item in manifest["installed_distributions"]}
        expected = {
            "chatterbox-tts": "0.1.7",
            "torch": "2.6.0+cu124",
            "torchaudio": "2.6.0+cu124",
            "psutil": "7.1.3",
        }
        for name, version in expected.items():
            record = records[name]
            self.assertEqual(record["version"], version)
            self.assertRegex(record["archive_sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(record["metadata_sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(record["record_sha256"], r"^[0-9a-f]{64}$")

    def test_worker_self_check_is_offline_stateless_and_playback_free(self) -> None:
        self.assertTrue(PYTHON.is_file())
        env = {
            **os.environ,
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_HUB_DISABLE_TELEMETRY": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "CUDA_VISIBLE_DEVICES": "",
        }
        completed = subprocess.run(
            [str(PYTHON), str(WORKER), "--self-check"],
            cwd=str(ROOT),
            env=env,
            text=True,
            capture_output=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertTrue(result["ready"])
        self.assertFalse(result["model_loaded"])
        self.assertFalse(result["playback"])
        self.assertEqual(result["chatterbox_version"], "0.1.7")

    def test_worker_rejects_private_channel_marker_before_synthesis(self) -> None:
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        text = "PRIVATE MIND: this must never reach voice output."
        request = {
            "schema_version": 1,
            "request_id": str(uuid.uuid4()),
            "channel": "public_spoken_only",
            "text": text,
            "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "reference_sha256": config["approved_reference_sha256"],
            "output_relative": "RecoverySprint/verification_scratch/forbidden.wav",
        }
        env = {
            **os.environ,
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "CUDA_VISIBLE_DEVICES": "",
        }
        completed = subprocess.run(
            [str(PYTHON), str(WORKER)],
            cwd=str(ROOT),
            env=env,
            input=json.dumps(request),
            text=True,
            capture_output=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(completed.returncode, 2)
        result = json.loads(completed.stdout)
        self.assertFalse(result["generated"])
        self.assertIn("private or factual channel marker", result["error"])
        self.assertFalse((ROOT / request["output_relative"]).exists())


if __name__ == "__main__":
    unittest.main()
