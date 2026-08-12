import tempfile
import unittest
from pathlib import Path

from Core.artifact_binding import (
    bind_artifact_hashes,
    canonical_json_sha256,
    sha256_file,
)


class ArtifactBindingTests(unittest.TestCase):
    def test_file_hash_is_streamed_and_stable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "artifact.bin"
            path.write_bytes(b"Kira artifact")
            self.assertEqual(
                "70d3b9d3da70e07e8096099ebad14195cf96e90b608ff91fd3778885f7a736a6",
                sha256_file(path),
            )

    def test_binding_is_independent_of_artifact_order(self):
        first = bind_artifact_hashes(
            {"source": "a" * 64, "wav": "b" * 64},
            metadata={"voice_mode": "test"},
        )
        second = bind_artifact_hashes(
            {"wav": "b" * 64, "source": "a" * 64},
            metadata={"voice_mode": "test"},
        )
        self.assertEqual(first["binding_sha256"], second["binding_sha256"])
        self.assertEqual(first["binding_sha256"], canonical_json_sha256({
            "schema_version": 1,
            "algorithm": "sha256",
            "artifacts": {"source": "a" * 64, "wav": "b" * 64},
            "metadata": {"voice_mode": "test"},
        }))

    def test_rejects_non_hash_values(self):
        with self.assertRaises(ValueError):
            bind_artifact_hashes({"source": "not-a-hash"})


if __name__ == "__main__":
    unittest.main()
