from __future__ import annotations

import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from Core.adult_reference_avatar_backend import (
    authorize_adult_reference_worker_request,
    validate_adult_reference_request,
    validate_adult_reference_request_file,
    validate_worker_evidence_request_binding,
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")
    return path


class AdultReferenceAvatarBackendTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[dict, Path]:
        candidate_id = "adult_subject_temp_20260716"
        subject_id = "adult_subject"
        variant = "ordinary_home_variant"
        candidate_root = root / "Avatar" / "temp_ai" / candidate_id
        source = (
            root
            / "Avatar"
            / "avatar_builder"
            / "asset_library"
            / "adult_anatomy_reference"
            / "adult_reference.glb"
        )
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(b"licensed-adult-reference")
        source_hash = digest(source)

        source_root = root / "source_packages"
        source_root.mkdir(parents=True)
        license_text = b"CC-BY-4.0 test license"
        license_archive = source_root / "licensed.zip"
        with zipfile.ZipFile(license_archive, "w") as package:
            package.writestr("license.txt", license_text)

        obj_bytes = b"o Body_Nude\nusemtl BodyMat\n"
        mtl_bytes = b"newmtl BodyMat\n"
        nested_buffer = io.BytesIO()
        with zipfile.ZipFile(nested_buffer, "w") as nested:
            nested.writestr("source.obj", obj_bytes)
            nested.writestr("source.mtl", mtl_bytes)
        nested_bytes = nested_buffer.getvalue()
        role_archive = source_root / "roles.zip"
        with zipfile.ZipFile(role_archive, "w") as outer:
            outer.writestr("source/nested.zip", nested_bytes)

        asset_manifest = write_json(
            root / "Avatar" / "avatar_builder" / "asset_library" / "manifest.json",
            {
                "records": [
                    {
                        "id": "adult_anatomy_reference:test",
                        "sha256": source_hash,
                        "local_file": source.relative_to(root).as_posix(),
                        "category": "adult_anatomy_reference",
                        "adult_only": True,
                        "allowed_for_non_adult": False,
                        "usage_policy": "reference only; never copy as an avatar body",
                    }
                ]
            },
        )
        reference_manifest = write_json(
            root / "Avatar" / "avatar_builder" / "reference_models" / "test" / "reference_model_manifest.json",
            {
                "maturity_policy": {"maturity_class": "adult"},
                "models": [
                    {
                        "sha256": source_hash,
                        "reference_only": True,
                        "copy_as_avatar_body_allowed": False,
                    },
                    {"sha256": digest(license_archive), "source_file": str(license_archive)},
                    {"sha256": digest(role_archive), "source_file": str(role_archive)},
                ],
            },
        )
        attribution = {
            "title": "Reference",
            "author": "Artist",
            "source_url": "https://example.invalid/source",
            "license_url": "https://creativecommons.org/licenses/by/4.0/",
        }
        license_evidence = write_json(
            root / "Avatar" / "avatar_builder" / "reference_models" / "test" / "license_evidence.json",
            {
                "source_glb_sha256": source_hash,
                "license_archive": {
                    "sha256": digest(license_archive),
                    "member": "license.txt",
                    "member_sha256": hashlib.sha256(license_text).hexdigest(),
                },
                "license": {
                    "id": "CC-BY-4.0",
                    "adaptation_allowed": True,
                    "license_url": attribution["license_url"],
                },
                "attribution": {key: attribution[key] for key in ("title", "author", "source_url")},
            },
        )
        role_evidence = write_json(
            root / "Avatar" / "avatar_builder" / "reference_models" / "test" / "source_role_map_evidence.json",
            {
                "source_glb_sha256": source_hash,
                "source_package": {
                    "sha256": digest(role_archive),
                    "nested_member": "source/nested.zip",
                    "nested_member_sha256": hashlib.sha256(nested_bytes).hexdigest(),
                    "obj_member": "source.obj",
                    "obj_member_sha256": hashlib.sha256(obj_bytes).hexdigest(),
                    "mtl_member": "source.mtl",
                    "mtl_member_sha256": hashlib.sha256(mtl_bytes).hexdigest(),
                },
                "glb_component_contract": {
                    "body_and_head_surface_mesh_count": 3,
                    "hair_mesh_count": 1,
                    "eye_mesh_count": 1,
                    "discarded_outline_mesh_count": 3,
                },
            },
        )
        profile = write_json(
            candidate_root / "subject_profile.json",
            {
                "candidate_id": candidate_id,
                "maturity_class": "adult",
                "continuity": {"selected_form": variant, "excluded": []},
            },
        )
        brief = write_json(
            candidate_root / "source_brief.json",
            {
                "candidate_id": candidate_id,
                "target": {"maturity_class": "adult", "form": variant, "explicitly_not": []},
                "build_decision": {
                    "body_candidate_may_be_staged_for_private_review_after_backend_validation": True,
                    "runtime_activation_allowed": False,
                },
            },
        )
        reliable = write_json(
            root / "TemporaryAI" / "candidates" / candidate_id / "reliable_source_pack.json",
            {"candidate_id": candidate_id},
        )

        def binding(path: Path) -> dict:
            return {"path": path.relative_to(root).as_posix(), "sha256": digest(path)}

        generated = candidate_root / "generated_body"
        request = {
            "project_root": str(root),
            "candidate_id": candidate_id,
            "subject_id": subject_id,
            "target_type": "temporary_ai",
            "variant": variant,
            "excluded_variants": [],
            "maturity_class": "adult",
            "runtime_activation_requested": False,
            "source": {
                "asset_id": "adult_anatomy_reference:test",
                "path": source.relative_to(root).as_posix(),
                "expected_sha256": source_hash,
                "reference_only": True,
                "copy_as_avatar_body_allowed": False,
                "attribution": attribution,
            },
            "policy_evidence": {
                "asset_library_manifest": binding(asset_manifest),
                "reference_manifest": binding(reference_manifest),
                "license_evidence": binding(license_evidence),
                "source_role_map_evidence": binding(role_evidence),
                "maturity_and_variant_profile": binding(profile),
                "avatar_source_brief": binding(brief),
                "reliable_source_pack": binding(reliable),
            },
            "derivative_plan": {
                "mode": "shape_preserving_licensed_rig_derivative",
                "preserve_source_surface_shape": True,
                "new_skinning_and_rig_required": True,
                "discard_duplicate_outline_shells": True,
                "discard_all_source_materials_and_textures": True,
                "separate_body_clothes": True,
                "separate_body_hair_eyes_clothes": True,
                "expected_component_counts": {
                    "discard": 3,
                    "body_surface": 3,
                    "hair": 1,
                    "eyes": 1,
                },
            },
            "privacy": {
                "normal_review_route": "clothed_only",
                "intimate_render_allowed": False,
                "public_export_allowed": False,
            },
            "outputs": {
                "body_glb": (generated / "test_private_body.glb").relative_to(root).as_posix(),
                "hair_glb": (generated / "test_separate_hair.glb").relative_to(root).as_posix(),
                "eyes_glb": (generated / "test_separate_eyes.glb").relative_to(root).as_posix(),
                "clothes_glb": (generated / "test_separate_clothes.glb").relative_to(root).as_posix(),
                "clothed_review_glb": (generated / "test_clothed_review_assembly.glb").relative_to(root).as_posix(),
                "build_evidence": (generated / "adult_reference_build_evidence.json").relative_to(root).as_posix(),
                "rig_attestation": (generated / "rig_mechanical_attestation.json").relative_to(root).as_posix(),
                "attribution": (generated / "CC_BY_4_attribution.json").relative_to(root).as_posix(),
            },
        }
        request_path = write_json(candidate_root / "adult_reference_derivative_request.json", request)
        return request, request_path

    def test_fully_bound_general_adult_request_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            request, request_path = self.fixture(root)
            result = validate_adult_reference_request(request, project_root=root)
            self.assertTrue(result["preflight_passed"], result["failures"])
            self.assertEqual([], validate_adult_reference_request_file(request_path, request, project_root=root))
            self.assertFalse(result["runtime_activation_allowed"])

    def test_non_adult_and_activation_are_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            request, _ = self.fixture(root)
            request["maturity_class"] = "non_adult_doll_safe"
            request["runtime_activation_requested"] = True
            failures = validate_adult_reference_request(request, project_root=root)["failures"]
            self.assertIn("adult_reference_backend_requires_confirmed_adult_subject", failures)
            self.assertIn("runtime_activation_must_be_explicitly_false", failures)

    def test_beth_space_variant_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            request, _ = self.fixture(root)
            request["subject_id"] = "beth_smith"
            request["variant"] = "space_beth"
            failures = validate_adult_reference_request(request, project_root=root)["failures"]
            self.assertIn("ordinary_non_space_variant_required", failures)
            self.assertIn("beth_request_must_explicitly_exclude_space_beth", failures)

    def test_output_escape_live_absolute_duplicate_and_extension_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            request, _ = self.fixture(root)
            request["outputs"]["body_glb"] = "../escape_private_body.glb"
            request["outputs"]["hair_glb"] = str((root / "live" / "test_separate_hair.glb").resolve())
            request["outputs"]["eyes_glb"] = request["outputs"]["clothes_glb"]
            request["outputs"]["rig_attestation"] = request["outputs"]["rig_attestation"].replace(".json", ".glb")
            failures = validate_adult_reference_request(request, project_root=root)["failures"]
            self.assertIn("output_body_glb_must_be_safe_project_relative", failures)
            self.assertIn("output_hair_glb_must_be_safe_project_relative", failures)
            self.assertIn("output_paths_must_be_distinct", failures)
            self.assertIn("output_rig_attestation_filename_or_extension_invalid", failures)

    def test_unindexed_source_and_bound_evidence_tamper_are_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            request, _ = self.fixture(root)
            request["source"]["asset_id"] = "adult_anatomy_reference:unindexed"
            request["policy_evidence"]["license_evidence"]["sha256"] = "0" * 64
            request["policy_evidence"]["maturity_and_variant_profile"]["sha256"] = "1" * 64
            failures = validate_adult_reference_request(request, project_root=root)["failures"]
            self.assertIn("source_not_exactly_bound_in_asset_library", failures)
            self.assertIn("license_evidence_sha256_mismatch", failures)
            self.assertIn("maturity_and_variant_profile_sha256_mismatch", failures)

    def test_missing_attribution_and_request_relocation_are_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            request, _ = self.fixture(root)
            request["source"]["attribution"].pop("author")
            failures = validate_adult_reference_request(request, project_root=root)["failures"]
            self.assertIn("attribution_author_not_bound_to_license_evidence", failures)
            moved = root / "wrong" / "request.json"
            moved.parent.mkdir()
            moved.write_text("{}", encoding="utf-8")
            self.assertIn(
                "request_file_must_be_in_exact_candidate_root",
                validate_adult_reference_request_file(moved, request, project_root=root),
            )

    def test_worker_authorization_rechecks_hash_and_rejects_direct_output_escape(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            request, request_path = self.fixture(root)
            original_hash = digest(request_path)
            authorization = authorize_adult_reference_worker_request(
                request_path,
                project_root=root,
                expected_request_sha256=original_hash,
            )
            self.assertEqual(original_hash, authorization["request_sha256"])
            self.assertEqual("adult_subject", authorization["request"]["subject_id"])

            request["outputs"]["body_glb"] = str((root / "live" / "escaped_private_body.glb").resolve())
            write_json(request_path, request)
            self.assertEqual(original_hash, authorization["request_sha256"])
            self.assertEqual("adult_subject", authorization["request"]["subject_id"])
            with self.assertRaisesRegex(ValueError, "changed after wrapper preflight"):
                authorize_adult_reference_worker_request(
                    request_path,
                    project_root=root,
                    expected_request_sha256=original_hash,
                )

            with self.assertRaisesRegex(ValueError, "output_body_glb_must_be_safe_project_relative"):
                authorize_adult_reference_worker_request(
                    request_path,
                    project_root=root,
                    expected_request_sha256=digest(request_path),
                )

    def test_post_authorization_identity_or_request_edit_fails_evidence_binding(self) -> None:
        evidence = {
            "candidate_id": "adult_subject_temp_20260716",
            "subject_id": "adult_subject",
            "variant": "ordinary_home_variant",
            "artifact_bindings": {"request_sha256": "a" * 64},
        }
        edited_request = {
            "candidate_id": "different_candidate",
            "subject_id": "different_subject",
            "variant": "different_variant",
        }
        failures = validate_worker_evidence_request_binding(
            evidence,
            edited_request,
            authorized_request_sha256="b" * 64,
        )
        self.assertEqual(
            {
                "build_evidence_request_sha256_mismatch",
                "build_evidence_candidate_id_mismatch",
                "build_evidence_subject_id_mismatch",
                "build_evidence_variant_mismatch",
            },
            set(failures),
        )


if __name__ == "__main__":
    unittest.main()
