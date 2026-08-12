from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path, PurePosixPath

from tools.verify_kira_r25_r19_attempt06_package import (
    EVIDENCE_BASE_RELATIVE,
    MANIFEST_NAME,
    PackageIntegrityError,
    _write_append_only_evidence,
    validate_evidence_relative,
    verify_package,
)
import tools.verify_kira_r25_r19_attempt06_package as gate


def _identity(data: bytes) -> dict[str, object]:
    return {"size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


class R25R19Attempt06PackageIntegrityGateTests(unittest.TestCase):
    def _fixture(
        self,
        root: Path,
        entries: list[dict[str, object]],
        files: dict[str, bytes],
    ) -> tuple[PurePosixPath, int, str]:
        package = PurePosixPath("sealed/attempt_06")
        package_dir = root.joinpath(*package.parts)
        package_dir.mkdir(parents=True)
        for relative, data in files.items():
            target = root.joinpath(*PurePosixPath(relative).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        manifest = {
            "append_only_attempt": "attempt_06",
            "created_utc": "2026-08-09T00:00:00+00:00",
            "files_excluding_this_manifest": entries,
            "schema_version": 1,
        }
        raw = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")
        (package_dir / MANIFEST_NAME).write_bytes(raw)
        return package, len(raw), hashlib.sha256(raw).hexdigest()

    def _verify(
        self,
        root: Path,
        package: PurePosixPath,
        manifest_size: int,
        manifest_hash: str,
        count: int,
    ) -> dict[str, object]:
        return verify_package(
            project_root=root,
            package_relative=package,
            expected_manifest_size=manifest_size,
            expected_manifest_sha256=manifest_hash,
            expected_member_count=count,
            expected_identities={},
        )

    def test_valid_exact_package_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = {
                "sealed/attempt_06/a.bin": b"alpha",
                "sealed/attempt_06/nested/b.bin": b"beta",
            }
            entries = [
                {"path": path, **_identity(data)} for path, data in files.items()
            ]
            package, size, digest = self._fixture(root, entries, files)
            result = self._verify(root, package, size, digest, 2)
            self.assertEqual("READ_ONLY_PACKAGE_INTEGRITY_PASS", result["status"])
            self.assertEqual(2, result["member_count"])
            self.assertTrue(result["complete_file_set_exact"])
            self.assertFalse(result["atomic_snapshot"])
            self.assertFalse(result["atomic_authoring_binding"])

    def test_duplicate_normalized_member_path_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = "sealed/attempt_06/a.bin"
            data = b"alpha"
            entry = {"path": path, **_identity(data)}
            package, size, digest = self._fixture(root, [entry, dict(entry)], {path: data})
            with self.assertRaisesRegex(PackageIntegrityError, "duplicate normalized"):
                self._verify(root, package, size, digest, 2)

    def test_traversal_outside_package_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            escaped = "sealed/attempt_06/../outside.bin"
            entry = {"path": escaped, **_identity(b"outside")}
            package, size, digest = self._fixture(root, [entry], {})
            with self.assertRaisesRegex(PackageIntegrityError, "non-normalized|traversal"):
                self._verify(root, package, size, digest, 1)

    def test_member_hash_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = "sealed/attempt_06/a.bin"
            entry = {"path": path, **_identity(b"claimed")}
            package, size, digest = self._fixture(root, [entry], {path: b"actual!"})
            with self.assertRaisesRegex(PackageIntegrityError, "SHA-256 mismatch"):
                self._verify(root, package, size, digest, 1)

    def test_windows_casefold_collision_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lower = "sealed/attempt_06/a.bin"
            upper = "sealed/attempt_06/A.bin"
            data = b"alpha"
            entries = [
                {"path": lower, **_identity(data)},
                {"path": upper, **_identity(data)},
            ]
            package, size, digest = self._fixture(root, entries, {lower: data})
            with self.assertRaisesRegex(PackageIntegrityError, "duplicate normalized"):
                self._verify(root, package, size, digest, 2)

    def test_unmanifested_extra_file_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = "sealed/attempt_06/a.bin"
            data = b"alpha"
            entries = [{"path": path, **_identity(data)}]
            files = {path: data, "sealed/attempt_06/extra.bin": b"extra"}
            package, size, digest = self._fixture(root, entries, files)
            with self.assertRaisesRegex(PackageIntegrityError, "file-set mismatch"):
                self._verify(root, package, size, digest, 1)

    def test_missing_manifest_member_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = "sealed/attempt_06/missing.bin"
            entries = [{"path": path, **_identity(b"missing")}]
            package, size, digest = self._fixture(root, entries, {})
            with self.assertRaisesRegex(PackageIntegrityError, "required path component is absent"):
                self._verify(root, package, size, digest, 1)

    def test_required_identity_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = "sealed/attempt_06/a.bin"
            data = b"alpha"
            entries = [{"path": path, **_identity(data)}]
            package, size, digest = self._fixture(root, entries, {path: data})
            wrong = {path: {"size_bytes": len(data), "sha256": "0" * 64}}
            with self.assertRaisesRegex(PackageIntegrityError, "required sealed identity"):
                verify_package(
                    project_root=root,
                    package_relative=package,
                    expected_manifest_size=size,
                    expected_manifest_sha256=digest,
                    expected_member_count=1,
                    expected_identities=wrong,
                )

    def test_duplicate_json_object_key_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = PurePosixPath("sealed/attempt_06")
            package_dir = root.joinpath(*package.parts)
            package_dir.mkdir(parents=True)
            raw = (
                b'{"append_only_attempt":"attempt_06",'
                b'"append_only_attempt":"attempt_06",'
                b'"created_utc":"2026-08-09T00:00:00+00:00",'
                b'"files_excluding_this_manifest":[],"schema_version":1}'
            )
            (package_dir / MANIFEST_NAME).write_bytes(raw)
            with self.assertRaisesRegex(PackageIntegrityError, "duplicate JSON object key"):
                self._verify(root, package, len(raw), hashlib.sha256(raw).hexdigest(), 0)

    def test_evidence_output_confinement_accepts_only_exact_gate_child(self) -> None:
        base = EVIDENCE_BASE_RELATIVE.as_posix()
        valid = f"{base}/attempt_99"
        self.assertEqual(valid, validate_evidence_relative(valid).as_posix())
        rejected = [
            "",
            ".",
            "..",
            r"C:\Temp",
            "C:/Temp",
            r"..\outside",
            "../outside",
            f"{base}/../outside",
            f"{base}//attempt_02",
            f"{base}/attempt:02",
            r"\\server\share\attempt_02",
            "//server/share/attempt_02",
            r"\\?\C:\Temp\attempt_02",
            (
                "RecoverySprint/continuation_20260802/"
                "kira_r19_bald_targeted_correction/attempt_06"
            ),
            base,
            f"{base}/nested/attempt_02",
        ]
        for value in rejected:
            with self.subTest(value=value):
                with self.assertRaises(PackageIntegrityError):
                    validate_evidence_relative(value)

    def test_append_only_evidence_is_self_consistent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "attempt"
            result = {
                "schema_version": 1,
                "artifact_kind": "TEST",
                "status": "QUIET_TREE_POINT_IN_TIME_PASS",
                "manifest": {
                    "path": "sealed/attempt_06/PACKAGE_MANIFEST.json",
                    "size_bytes": 1,
                    "sha256": "a" * 64,
                },
                "member_count": 0,
                "atomic_snapshot": False,
                "atomic_authoring_binding": False,
            }
            _write_append_only_evidence(output, result)
            evidence_bytes = (output / "PACKAGE_INTEGRITY_EVIDENCE.json").read_bytes()
            record = json.loads(evidence_bytes)
            readme = (output / "README.md").read_text(encoding="utf-8")
            evidence_hash = hashlib.sha256(evidence_bytes).hexdigest()
            verifier_hash = hashlib.sha256(Path(gate.__file__).read_bytes()).hexdigest()
            self.assertIn(evidence_hash, readme)
            self.assertEqual(verifier_hash, record["verifier"]["sha256"])
            self.assertFalse(record["atomic_snapshot"])
            self.assertFalse(record["atomic_authoring_binding"])
            self.assertIn("not an atomic filesystem snapshot", readme)


if __name__ == "__main__":
    unittest.main()
