from __future__ import annotations

import hashlib
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "System" / "Docs" / "CURRENT_TRUTH_SUPERSESSION_REGISTRY_20260810.md"
POINTER_DOCS = (
    ROOT / "System" / "Docs" / "README_MASTER_INDEX.md",
    ROOT / "System" / "Docs" / "ACTIVE_SARAH_R3_AND_KIRA_R24_CHECKPOINT_20260809.md",
    ROOT / "HANDOFF_FOR_NEXT_CODEX_SESSION.md",
)


class CurrentTruthRegistryPointerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry_bytes = REGISTRY.read_bytes()
        cls.registry_text = cls.registry_bytes.decode("utf-8")
        cls.registry_normalized = " ".join(cls.registry_text.split())
        cls.registry_sha256 = hashlib.sha256(cls.registry_bytes).hexdigest()

    def test_read_first_pointers_bind_current_registry_bytes(self) -> None:
        size_text = f"{len(self.registry_bytes):,} bytes"
        registry_path = (
            "System/Docs/CURRENT_TRUTH_SUPERSESSION_REGISTRY_20260810.md"
        )
        stale_sha256 = (
            "53431d9f2b2a418d20f0dcfddab248a7ec5f45a25c8d09cd283f124f08cd01a9"
        )
        for path in POINTER_DOCS:
            with self.subTest(path=path.relative_to(ROOT).as_posix()):
                text = path.read_text(encoding="utf-8")
                read_first_header = text[:1600]
                self.assertIn(registry_path, read_first_header)
                self.assertIn(size_text, read_first_header)
                self.assertIn(self.registry_sha256, read_first_header)
                self.assertEqual(text.count(registry_path), 1)
                self.assertEqual(text.count(size_text), 1)
                self.assertEqual(text.count(self.registry_sha256), 1)
                self.assertNotIn(stale_sha256, text)

    def test_registry_uses_current_qwen_memory_and_voice_truth(self) -> None:
        required = (
            "PASS_EXACT_QWEN35_NATURAL_CURRENT_ACTIVITY_BOUNDARY",
            "Its exact-Qwen text Attempt 04 passed",
            "last-mile currentness failure",
            "c9b18090d034dfc2b76d517d6011a288fc0bc2169a4b1e7b7f30529bbcf36d00",
            "present-person-state repair",
            "ce8ce9682b652d5bd1b8323febe81884e77ddd437ebc63ca72f57c834ce3f886",
            "independently rejected before live use",
            "No live CPU park, Qwen sequence, GPU/audio, or owner-hearing run is authorized",
        )
        # The status is recorded in the final acceptance file; the registry
        # binds that exact path rather than copying every evidence field.
        final_acceptance = (
            ROOT
            / "RecoverySprint"
            / "continuation_20260810"
            / "qwen35_memory_temporal_context_repair"
            / "attempt_01"
            / "FINAL_ACCEPTANCE.md"
        ).read_text(encoding="utf-8")
        self.assertIn(required[0], final_acceptance)
        for value in required[1:]:
            self.assertIn(value, self.registry_normalized)
        self.assertNotIn(
            "one fresh exact-Qwen 3.5 text-content acceptance is still required",
            self.registry_text,
        )

    def test_registry_separates_policy_context_from_lived_implementation(self) -> None:
        for value in (
            "educational knowledge context",
            "not proof of a completed lesson",
            "No durable subjective emotion",
            "not automatically promoted lived memories",
        ):
            self.assertIn(value, self.registry_text)

    def test_temporal_final_acceptance_pointers_bind_current_bytes(self) -> None:
        final_path = (
            ROOT
            / "RecoverySprint"
            / "continuation_20260810"
            / "qwen35_memory_temporal_context_repair"
            / "attempt_01"
            / "FINAL_ACCEPTANCE.md"
        )
        payload = final_path.read_bytes()
        size_text = f"{len(payload):,} bytes"
        sha256 = hashlib.sha256(payload).hexdigest()
        for path in POINTER_DOCS[1:]:
            with self.subTest(path=path.relative_to(ROOT).as_posix()):
                text = path.read_text(encoding="utf-8")
                self.assertIn(final_path.relative_to(ROOT).as_posix(), text)
                self.assertIn(size_text, text)
                self.assertIn(sha256, text)

    def test_registry_preserves_current_body_media_and_reconstruction_boundaries(self) -> None:
        for value in (
            "No R25 body",
            "Live magazine, video, and music enjoyment is not accepted",
            "voluntary-media v3 pure core is independently rejected",
            "cd1425598b27af574e253e36d0f8115330fcbdb8697fb40d5df26f891baa6eb4",
            "voluntary-media v4 passed its authored 50/50",
            "227b17123a5d1ce3a3aac1942ddf7c8fd7ed9e937a7a2979c47297fdf9874ec5",
            "voluntary-media v5 passed its authored 69/69",
            "54d65343a7eca2c867d62b682cbffbccdc80508e788dae83c4f48f6ddb6be165",
            "startup_path_ancestor_hold_failed",
            "17c50e6ac857a5fb788fe1901b756deebb1531f54ccdf4b3bbc47af5a8ae2847",
            "v3r7 repaired the project-root identity boundary",
            "571c678f3db472c824a6ed1b4eb0508b93bb680b1da795dfb155e63513c14f10",
            "6604cebf9650033c76d1b893189bbb1fba76201a4ee47f7cace448fff1f9d1be",
            "Append-only v3r8 sealed static-only after 89/89",
            "execution_contract_top_level_drift",
            "a667b03f4a3de443609379cd3c7c368cfe1a1fd9dc9ca62e3593d4238cde10fe",
            "voluntary-media v6 was sealed after 85/85",
            "ba5ddf21a10044ae9304b1ef81961c52f6902c60548ed48a819b05082d12d785",
            "Fresh static-audit checkpoint SHA-256",
            "383d67fe8236fc3227b5ec3183436412bcc2e511b8cd8e977206e2ab14ac1f72",
            "Reconstruction-access v3 is a disconnected static implementation",
            "004648d71680ea12d3f48d394d003331cfdc5dd9a5c708faad8e80f1a08d10bb",
            "934091af02deda78ec607e696c088d01848db7451f2f25036b14ab64b87f4458",
            "b15b59e361f808b3522eb07483e78fd83175f91c57e714b658da50c722b69c8e",
            "e7dbc5c3345009d30a8b374ccd464b0c9c99b2b9de71ee58e5906c69a98604a3",
            "55388335001673f962b2c3eb2c2835c6a3c56a6eaa700c579cd8fdaf5afe6a93",
            "211c571d0a82f4a94b3eb04c1213d95920da5738b52cae11c3277b879a36a511",
            "7043923f02889ae9994a56af7a4cabaa74968dcc9902e74c2556bfcebc0fa83f",
            "dd76dda45f9c73855d6cc500649b7423f940449f87f6fbbd05c9836cb227a962",
            "ef88b5d11b5f7d82535138ac34b2a4c97415c7794294227a9db849732ab8204f",
            "Video Studio remains owner-frozen",
        ):
            self.assertIn(value, self.registry_text)

    def test_registry_records_voice_forge_r7_fresh_rejection(self) -> None:
        for value in (
            "different fresh audit also **rejects** R7",
            "year-9999 authorization",
            "CUDA allocated bytes greater than reserved bytes",
            "negative Windows Job termination counter",
            "577fd3cf047fbaa0abddeea7dfb7f86602b6b94f97b9f43a724d77affc7ab966",
            "941764a54f16ecafb2034c03cdfbb1060271a3c3eb539c2ff58aff603938c4aa",
        ):
            self.assertIn(value, self.registry_normalized)

    def test_registry_supersedes_rejected_blackwell_v4_without_deleting_history(self) -> None:
        for value in (
            "Append-only v4 also passed its own 27/27 static tests",
            "No live CPU park, Qwen sequence, synthesis, playback, or owner-hearing run is authorized for v4",
            "454462a6be1b4300d2c184149c1723f19dbecbf6b4aa8759f874919da6f1e7df",
            "Append-only v5 passed its authored 19/19",
            "51332bb0bf4796f2ed1cdf3bc047d09a00c0ff78df47c1021fae0427cc776fd0",
            "V6 is now sealed static-only",
            "fd782cce2a693b9e0d2fe59819a728984f58b1c1f2839a2ef13d35e49d89390b",
            "dcd260cd2e912db7d8018eb7cf781831b6d24c366d7edf8e162be1fa74894ed8",
            "Append-only v7 is sealed static-only after 32/32",
            "df3a5c6a62043fbcc4b890abbbd5d3a406bf66839f29b6edd116830864ddab33",
        ):
            self.assertIn(value, self.registry_normalized)
        self.assertNotIn(
            "Append-only v4 is limited to those repairs and requires another fresh audit",
            self.registry_normalized,
        )


if __name__ == "__main__":
    unittest.main()
