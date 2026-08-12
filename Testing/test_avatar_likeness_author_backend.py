from __future__ import annotations

from contextlib import redirect_stderr
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zlib

from Core.avatar_likeness_author_backend import (
    AvatarLikenessAuthorError,
    DEFAULT_CAPABILITY_PATH,
    PROTOCOL,
    finalize_likeness_author_outputs,
    prepare_likeness_author_work_order,
    validate_likeness_author_work_order,
    validate_queued_evidence_job,
)
from Core.avatar_multiview_authoring import (
    queue_multiview_authoring_manifest,
    sha256_file,
)
from Core import avatar_likeness_author_backend as likeness_backend
from Core.avatar_component_production import AvatarProductionError
from Core.avatar_profile_preflight import AvatarProfilePreflightError
from tools import avatar_likeness_author_backend as likeness_cli


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def write_png(path: Path, *, tag: bytes, width: int = 640, height: int = 480) -> None:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    color = zlib.crc32(tag).to_bytes(4, "big")
    rgb = color[:3]
    scanline = b"\x00" + rgb * width
    pixels = scanline * height
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">II", width, height) + b"\x08\x02\x00\x00\x00")
        + chunk(b"IDAT", zlib.compress(pixels))
        + chunk(b"IEND", b"")
    )


def write_minimal_glb(
    path: Path,
    role: str,
    *,
    external_buffer_uri: bool = False,
    include_position: bool = True,
    include_skin: bool = True,
    active_mesh: bool = True,
    position_limit_violation: bool = False,
    scene_transform_limit_violation: bool = False,
) -> None:
    binary = bytearray()
    buffer_views: list[dict[str, int]] = []
    accessors: list[dict[str, object]] = []

    def add_view(payload: bytes) -> int:
        while len(binary) % 4:
            binary.append(0)
        offset = len(binary)
        binary.extend(payload)
        buffer_views.append(
            {"buffer": 0, "byteOffset": offset, "byteLength": len(payload)}
        )
        return len(buffer_views) - 1

    positions = (
        (0.0, 0.0, 0.0),
        (20_000.0 if position_limit_violation else 1.0, 0.0, 0.25),
        (0.0, 1.0, 0.0),
    )
    position_view = add_view(
        b"".join(struct.pack("<fff", *position) for position in positions)
    )
    accessors.append(
        {
            "bufferView": position_view,
            "componentType": 5126,
            "count": len(positions),
            "type": "VEC3",
        }
    )
    attributes: dict[str, int] = {"POSITION": 0} if include_position else {}
    nodes: list[dict[str, object]]
    skins: list[dict[str, object]] = []
    if role == "body" and include_skin:
        joint_view = add_view(bytes([0, 0, 0, 0] * len(positions)))
        accessors.append(
            {
                "bufferView": joint_view,
                "componentType": 5121,
                "count": len(positions),
                "type": "VEC4",
            }
        )
        weight_view = add_view(
            b"".join(struct.pack("<ffff", 1.0, 0.0, 0.0, 0.0) for _ in positions)
        )
        accessors.append(
            {
                "bufferView": weight_view,
                "componentType": 5126,
                "count": len(positions),
                "type": "VEC4",
            }
        )
        inverse_view = add_view(
            struct.pack(
                "<" + "f" * 16,
                1, 0, 0, 0,
                0, 1, 0, 0,
                0, 0, 1, 0,
                0, 0, 0, 1,
            )
        )
        accessors.append(
            {
                "bufferView": inverse_view,
                "componentType": 5126,
                "count": 1,
                "type": "MAT4",
            }
        )
        attributes.update({"JOINTS_0": 1, "WEIGHTS_0": 2})
        nodes = [
            {"name": "body_joint"},
            {"name": "body_mesh", "mesh": 0, "skin": 0},
        ]
        skins = [
            {
                "name": "body_rig",
                "joints": [0],
                "skeleton": 0,
                "inverseBindMatrices": 3,
            }
        ]
        scene_nodes = [0, 1]
    elif role == "body":
        nodes = [{"name": "body_mesh", "mesh": 0}]
        scene_nodes = [0]
    else:
        nodes = [{"name": f"{role}_mesh", "mesh": 0}]
        scene_nodes = [0]
    if not active_mesh:
        nodes.append({"name": f"{role}_inactive_scene_root"})
        scene_nodes = [len(nodes) - 1]
    if scene_transform_limit_violation:
        mesh_node = next(node for node in nodes if node.get("mesh") == 0)
        mesh_node["translation"] = [50_000.0, 0.0, 0.0]
    document = {
        "asset": {"version": "2.0", "generator": "likeness-author-test"},
        "scene": 0,
        "scenes": [{"nodes": scene_nodes}],
        "nodes": nodes,
        "meshes": [
            {
                "name": f"{role}_mesh",
                "primitives": [{"attributes": attributes, "mode": 4}],
            }
        ],
        "buffers": [
            {
                "byteLength": len(binary),
                **({"uri": "unbound-external.bin"} if external_buffer_uri else {}),
            }
        ],
        "bufferViews": buffer_views,
        "accessors": accessors,
    }
    if skins:
        document["skins"] = skins
    chunk = json.dumps(document, separators=(",", ":")).encode("utf-8")
    chunk += b" " * ((4 - len(chunk) % 4) % 4)
    binary.extend(b"\x00" * ((4 - len(binary) % 4) % 4))
    total = 12 + 8 + len(chunk) + 8 + len(binary)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        struct.pack("<4sII", b"glTF", 2, total)
        + struct.pack("<II", len(chunk), 0x4E4F534A)
        + chunk
        + struct.pack("<II", len(binary), 0x004E4942)
        + bytes(binary)
    )


def install_fixture_identity_registry(
    root: Path,
    *,
    candidate_id: str,
    subject_id: str,
    version_id: str,
) -> None:
    profile_root = root / "TemporaryAI" / "candidates" / candidate_id
    write_json(
        profile_root / "temporary_ai_profile.json",
        {
            "candidate_id": candidate_id,
            "display_name": "Fixture Person",
            "knowledge_plan": {"version_or_life_point": version_id},
            "avatar_plan": {"maturity_policy": "adult"},
        },
    )
    write_json(
        profile_root / "creation_request.json",
        {"candidate_id": candidate_id},
    )
    write_json(
        root
        / "Avatar"
        / "avatar_builder"
        / "policies"
        / "candidate_identity_variant_registry.json",
        {
            "schema_version": 1,
            "candidates": [
                {
                    "canonical_candidate_id": candidate_id,
                    "aliases": [],
                    "subject_id": subject_id,
                    "identity_class": "original_person",
                    "variant_kind": "reviewed_fixture_version",
                    "version_policy": {
                        "required": True,
                        "binding": {
                            "source": "temporary_ai_profile",
                            "path": ["knowledge_plan", "version_or_life_point"],
                            "expected": version_id,
                        },
                    },
                    "maturity_policy": {
                        "lane": "adult",
                        "binding": {
                            "source": "temporary_ai_profile",
                            "path": ["avatar_plan", "maturity_policy"],
                            "accepted_values": ["adult"],
                        },
                    },
                    "adult_variant_policy": {
                        "separate_variant_required": False,
                        "adult_variant_candidate_id": "",
                    },
                    "manual_review_notes": [],
                }
            ],
        },
    )


class AvatarLikenessAuthorBackendTests(unittest.TestCase):
    def make_reviewed_queue(self) -> tuple[tempfile.TemporaryDirectory, Path, Path, Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        candidate_id = "fixture_person_001"
        subject_id = "fixture_subject"
        version_id = "fixture_version_v1"
        install_fixture_identity_registry(
            root,
            candidate_id=candidate_id,
            subject_id=subject_id,
            version_id=version_id,
        )
        multiview_root = root / "Avatar" / "avatar_builder" / "multiview_authoring"
        source_root = multiview_root / "private_sources" / candidate_id
        review_root = multiview_root / "private_reviews" / candidate_id
        views = ("head_front", "three_quarter_left", "full_body_front")
        region_groups = (
            ("face_outline", "brow", "eye_socket_rims", "nose", "lips", "chin", "ears", "neck"),
            ("shoulders", "chest", "waist", "hips"),
            ("elbows", "wrists", "hands", "knees", "ankles", "feet"),
        )
        source_records = []
        for index, (view, regions) in enumerate(zip(views, region_groups), start=1):
            source_id = f"source_{index:03d}"
            source_path = source_root / f"{source_id}.png"
            write_png(source_path, tag=f"source-{index}".encode())
            source_sha = sha256_file(source_path)
            review = {
                "schema_version": 1,
                "artifact_type": "avatar_multiview_source_review",
                "candidate_id": candidate_id,
                "subject_id": subject_id,
                "selected_version_id": version_id,
                "source_id": source_id,
                "source_sha256": source_sha,
                "review_status": "approved",
                "reviewed_by": "fixture_owner",
                "reviewed_at": "2026-07-16T12:00:00Z",
                "same_subject_and_version_confirmed": True,
                "view_label": view,
                "source_dimensions": {"width": 640, "height": 480},
                "crop_pixels": {"x": 0, "y": 0, "width": 640, "height": 480},
                "calibration": {
                    "status": "reviewed",
                    "camera_model": "perspective",
                    "coordinate_frame_id": "fixture_frame_v1",
                },
                "landmark_origin": "human_placed",
                "landmarks": [
                    {
                        "name": f"{region}_{point}",
                        "region": region,
                        "x": 100.0 + point,
                        "y": 100.0 + point,
                        "reviewed": True,
                    }
                    for point, region in enumerate(regions)
                ],
            }
            review_path = review_root / f"{source_id}.json"
            write_json(review_path, review)
            source_records.append(
                {
                    "source_id": source_id,
                    "source_path": source_path.relative_to(root).as_posix(),
                    "sha256": source_sha,
                    "dimensions": {"width": 640, "height": 480},
                    "review_artifact": {
                        "path": review_path.relative_to(root).as_posix(),
                        "sha256": sha256_file(review_path),
                    },
                }
            )
        scale = {
            "schema_version": 1,
            "artifact_type": "avatar_multiview_scale_review",
            "candidate_id": candidate_id,
            "subject_id": subject_id,
            "selected_version_id": version_id,
            "review_status": "approved",
            "reviewed_by": "fixture_owner",
            "reviewed_at": "2026-07-16T12:00:00Z",
            "scale_mode": "reviewed_metric",
            "target_height_m": 1.75,
        }
        scale_path = review_root / "scale.json"
        write_json(scale_path, scale)
        base_path = multiview_root / "bases" / "reviewed_base.glb"
        write_minimal_glb(base_path, "reviewed_base")
        base_sha = sha256_file(base_path)
        base_review = {
            "schema_version": 1,
            "artifact_type": "avatar_multiview_base_review",
            "candidate_id": candidate_id,
            "subject_id": subject_id,
            "selected_version_id": version_id,
            "base_body_sha256": base_sha,
            "topology_lane": "confirmed_adult_topology",
            "review_status": "approved",
            "reviewed_by": "fixture_owner",
            "reviewed_at": "2026-07-16T12:00:00Z",
            "rig_compatible_cage_source_confirmed": True,
            "new_candidate_surface_required": True,
        }
        base_review_path = review_root / "base.json"
        write_json(base_review_path, base_review)
        manifest = {
            "schema_version": 1,
            "manifest_type": "avatar_multiview_likeness_evidence",
            "candidate_id": candidate_id,
            "subject_id": subject_id,
            "selected_version_id": version_id,
            "topology_lane": "confirmed_adult_topology",
            "output_rule": "private_review_only_not_runtime",
            "runtime_activation_requested": False,
            "public_export_allowed": False,
            "source_images": source_records,
            "scale_review_artifact": {
                "path": scale_path.relative_to(root).as_posix(),
                "sha256": sha256_file(scale_path),
            },
            "base_body": {
                "status": "reviewed",
                "path": base_path.relative_to(root).as_posix(),
                "sha256": base_sha,
                "topology_lane": "confirmed_adult_topology",
                "allowed_use": "cage_fit_source_new_surface_required",
                "copy_as_candidate_body_allowed": False,
                "review_artifact": {
                    "path": base_review_path.relative_to(root).as_posix(),
                    "sha256": sha256_file(base_review_path),
                },
            },
            "reference_models": [],
        }
        manifest_path = multiview_root / "manifests" / "private" / f"{candidate_id}.json"
        write_json(manifest_path, manifest)
        queued = queue_multiview_authoring_manifest(root, manifest_path)
        queue_path = root / queued["job_path"]
        return temporary, root, manifest_path, queue_path

    def install_test_capability(self, root: Path) -> Path:
        worker = root / "tools" / "blender_fit_reviewed_multiview_surface.py"
        worker.parent.mkdir(parents=True, exist_ok=True)
        worker.write_text("# fixture reviewed multiview worker\n", encoding="utf-8")
        blender = root / "fixture_tools" / "blender.exe"
        blender.parent.mkdir(parents=True, exist_ok=True)
        blender.write_bytes(b"fixture-blender-executable")
        capability = {
            "schema_version": 1,
            "artifact_type": "avatar_likeness_author_tool_capability",
            "protocol": PROTOCOL,
            "status": "operator_approved_available",
            "operator_approved": True,
            "reviewed_by": "fixture_operator",
            "reviewed_at": "2026-07-16T12:00:00Z",
            "algorithm_id": "fixture_reviewed_cage_fit_v1",
            "worker": {
                "path": worker.relative_to(root).as_posix(),
                "sha256": sha256_file(worker),
            },
            "blender": {
                "executable_path": str(blender.resolve()),
                "sha256": sha256_file(blender),
            },
            "capabilities": {
                "consumes_only_reviewed_landmarks": True,
                "authors_new_surface_from_cage": True,
                "forbids_reference_surface_copy": True,
                "exports_separate_components": True,
                "exports_landmark_reprojection_metrics": True,
                "exports_rig_mechanical_smoke": True,
                "renders_clothed_private_review_views": True,
            },
            "runtime_activation_allowed": False,
            "public_export_allowed": False,
        }
        path = root / DEFAULT_CAPABILITY_PATH
        write_json(path, capability)
        return path

    def prepare(self) -> tuple[tempfile.TemporaryDirectory, Path, Path, dict]:
        temporary, root, _, queue_path = self.make_reviewed_queue()
        capability = self.install_test_capability(root)
        prepared = prepare_likeness_author_work_order(
            root, queue_path, capability_path=capability
        )
        order_path = root / prepared["work_order_path"]
        return temporary, root, order_path, json.loads(order_path.read_text())

    def create_worker_outputs(self, root: Path, order_path: Path, order: dict) -> Path:
        outputs = order["required_outputs"]
        artifact_bindings: dict[str, dict[str, str]] = {}
        for role, relative in outputs["components"].items():
            path = root / relative
            write_minimal_glb(path, role)
            artifact_bindings[role] = {"path": relative, "sha256": sha256_file(path)}
        body_sha = artifact_bindings["body"]["sha256"]
        base_sha = order["evidence_summary"]["base_body_review"]["sha256"]
        declarations = {
            "surface_authorship": {
                "schema_version": 1,
                "artifact_type": "avatar_new_surface_worker_declaration",
                "protocol": PROTOCOL,
                "author_job_id": order["author_job_id"],
                "candidate_id": order["identity"]["candidate_id"],
                "subject_id": order["identity"]["subject_id"],
                "base_body_sha256": base_sha,
                "candidate_body_sha256": body_sha,
                "method": "reviewed_multiview_cage_lattice_sculpt",
                "new_surface_authored": True,
                "base_used_as_cage_only": True,
                "reference_surface_copied": False,
                "reference_material_or_texture_copied": False,
                "identity_likeness_proven": False,
                "anatomical_completeness_proven": False,
                "runtime_activation_allowed": False,
            },
            "landmark_reprojection": {
                "schema_version": 1,
                "artifact_type": "avatar_landmark_reprojection_metrics",
                "protocol": PROTOCOL,
                "author_job_id": order["author_job_id"],
                "candidate_body_sha256": body_sha,
                "source_results": [
                    {
                        "source_id": item["source_id"],
                        "source_review_sha256": item["source_review_sha256"],
                        "compared_landmark_count": item[
                            "reviewed_landmark_count"
                        ],
                        "mean_error_px": 1.5,
                        "max_error_px": 3.0,
                    }
                    for item in order["reviewed_source_bindings"]
                ],
                "automatic_acceptance_allowed": False,
                "owner_review_required": True,
                "runtime_activation_allowed": False,
            },
            "rig_mechanical_smoke": {
                "schema_version": 1,
                "artifact_type": "avatar_rig_mechanical_smoke",
                "protocol": PROTOCOL,
                "author_job_id": order["author_job_id"],
                "candidate_body_sha256": body_sha,
                "finite_bounded_mechanical_smoke_completed": True,
                "stable_working_rig_proven": False,
                "visual_deformation_quality_proven": False,
                "runtime_activation_allowed": False,
            },
        }
        for role, value in declarations.items():
            relative = outputs["worker_declarations"][role]
            path = root / relative
            write_json(path, value)
            artifact_bindings[role] = {"path": relative, "sha256": sha256_file(path)}
        for index, (role, relative) in enumerate(outputs["review_renders"].items()):
            path = root / relative
            write_png(path, tag=f"render-{index}".encode())
            artifact_bindings[role] = {"path": relative, "sha256": sha256_file(path)}
        worker_result = {
            "schema_version": 1,
            "artifact_type": "avatar_likeness_author_worker_result",
            "protocol": PROTOCOL,
            "author_job_id": order["author_job_id"],
            "work_order_sha256": sha256_file(order_path),
            "capability_sha256": order["identity"]["capability_sha256"],
            "artifacts": artifact_bindings,
            "runtime_activation_allowed": False,
            "public_export_allowed": False,
        }
        result_path = root / outputs["worker_result"]
        write_json(result_path, worker_result)
        return result_path

    def replace_worker_component(
        self,
        root: Path,
        order: dict,
        result_path: Path,
        role: str,
        **options: object,
    ) -> None:
        result = json.loads(result_path.read_text())
        binding = result["artifacts"][role]
        path = root / binding["path"]
        write_minimal_glb(path, role, **options)
        binding["sha256"] = sha256_file(path)
        write_json(result_path, result)

    def mutate_worker_declaration(
        self,
        root: Path,
        result_path: Path,
        role: str,
        mutate,
    ) -> None:
        result = json.loads(result_path.read_text())
        binding = result["artifacts"][role]
        path = root / binding["path"]
        declaration = json.loads(path.read_text())
        mutate(declaration)
        write_json(path, declaration)
        binding["sha256"] = sha256_file(path)
        write_json(result_path, result)

    def test_missing_reviewed_tooling_blocks_without_work_order(self) -> None:
        temporary, root, _, queue_path = self.make_reviewed_queue()
        self.addCleanup(temporary.cleanup)

        result = prepare_likeness_author_work_order(root, queue_path)

        self.assertEqual("blocked_required_author_tooling_missing", result["status"])
        self.assertTrue(result["reviewed_evidence_verified"])
        self.assertFalse(result["work_order_created"])
        self.assertFalse(result["runtime_activation_allowed"])

    def test_missing_canonical_registry_fails_closed(self) -> None:
        temporary, root, _, queue_path = self.make_reviewed_queue()
        self.addCleanup(temporary.cleanup)
        registry = (
            root
            / "Avatar"
            / "avatar_builder"
            / "policies"
            / "candidate_identity_variant_registry.json"
        )
        registry.unlink()

        with self.assertRaisesRegex(
            AvatarLikenessAuthorError, "registry is unavailable"
        ):
            validate_queued_evidence_job(root, queue_path)

    def test_required_canonical_version_must_match_queue_version(self) -> None:
        temporary, root, _, queue_path = self.make_reviewed_queue()
        self.addCleanup(temporary.cleanup)
        profile = (
            root
            / "TemporaryAI"
            / "candidates"
            / "fixture_person_001"
            / "temporary_ai_profile.json"
        )
        value = json.loads(profile.read_text())
        value["knowledge_plan"]["version_or_life_point"] = "wrong_version"
        write_json(profile, value)

        with self.assertRaisesRegex(AvatarLikenessAuthorError, "canonical identity"):
            validate_queued_evidence_job(root, queue_path)

    def test_optional_canonical_version_uses_exact_reviewed_manifest_binding(self) -> None:
        temporary, root, _, queue_path = self.make_reviewed_queue()
        self.addCleanup(temporary.cleanup)
        registry = (
            root
            / "Avatar"
            / "avatar_builder"
            / "policies"
            / "candidate_identity_variant_registry.json"
        )
        value = json.loads(registry.read_text())
        value["candidates"][0]["version_policy"] = {"required": False}
        write_json(registry, value)

        validated = validate_queued_evidence_job(root, queue_path)
        binding = validated["identity_preflight"][
            "likeness_author_version_binding"
        ]

        self.assertEqual(
            "reviewed_manifest_exact_optional_canonical_version",
            binding["binding_mode"],
        )
        self.assertEqual("fixture_version_v1", binding["selected_version_id"])
        self.assertEqual("", binding["canonical_selected_version"])

    def test_preparation_is_content_addressed_idempotent_and_inactive(self) -> None:
        temporary, root, _, queue_path = self.make_reviewed_queue()
        self.addCleanup(temporary.cleanup)
        capability = self.install_test_capability(root)

        first = prepare_likeness_author_work_order(root, queue_path, capability_path=capability)
        second = prepare_likeness_author_work_order(root, queue_path, capability_path=capability)
        order = json.loads((root / first["work_order_path"]).read_text())

        self.assertEqual(first["author_job_id"], second["author_job_id"])
        self.assertEqual("prepared_inactive_author_work_order", first["status"])
        self.assertEqual("already_prepared_verified", second["status"])
        self.assertFalse(first["body_candidate_created"])
        self.assertFalse(order["runtime_activation_requested"])
        self.assertEqual(5, len(order["required_outputs"]["components"]))
        self.assertIn("rig_structure", order["required_outputs"]["backend_proofs"])
        self.assertEqual(
            "canonical_profile_exact",
            order["evidence_summary"]["identity_preflight"]
            ["likeness_author_version_binding"]["binding_mode"],
        )
        self.assertEqual(
            order["evidence_summary"]["reviewed_landmark_count"],
            sum(
                item["reviewed_landmark_count"]
                for item in order["reviewed_source_bindings"]
            ),
        )

    def test_work_order_write_rejects_symlinked_output_ancestry_before_write(self) -> None:
        temporary, root, _, queue_path = self.make_reviewed_queue()
        self.addCleanup(temporary.cleanup)
        capability = self.install_test_capability(root)
        original = likeness_backend._has_symlink_component

        def report_work_order_symlink(path: Path, stop: Path) -> bool:
            if "work_orders" in Path(path).parts:
                return True
            return original(path, stop)

        with (
            patch.object(
                likeness_backend,
                "_has_symlink_component",
                side_effect=report_work_order_symlink,
            ),
            self.assertRaisesRegex(AvatarLikenessAuthorError, "contains a symlink"),
        ):
            prepare_likeness_author_work_order(
                root, queue_path, capability_path=capability
            )
        self.assertFalse(
            (root / "Avatar/avatar_builder/likeness_authoring/work_orders").exists()
        )

    def test_queue_revalidation_rejects_changed_source_after_queueing(self) -> None:
        temporary, root, manifest_path, queue_path = self.make_reviewed_queue()
        self.addCleanup(temporary.cleanup)
        manifest = json.loads(manifest_path.read_text())
        source = root / manifest["source_images"][0]["source_path"]
        source.write_bytes(source.read_bytes() + b"changed")

        with self.assertRaisesRegex(AvatarLikenessAuthorError, "no longer fully reviewed"):
            validate_queued_evidence_job(root, queue_path)

    def test_canonical_identity_preflight_cannot_be_bypassed(self) -> None:
        temporary, root, _, queue_path = self.make_reviewed_queue()
        self.addCleanup(temporary.cleanup)

        with (
            patch(
                "Core.avatar_likeness_author_backend.identity_registry_available",
                return_value=True,
            ),
            patch(
                "Core.avatar_likeness_author_backend.evaluate_avatar_profile_preflight",
                return_value={
                    "status": "blocked",
                    "authoring_allowed": False,
                    "failures": ["fictional_version_blank"],
                    "runtime_activation_allowed": False,
                },
            ),
            self.assertRaisesRegex(AvatarLikenessAuthorError, "canonical identity"),
        ):
            validate_queued_evidence_job(root, queue_path)

    def test_work_order_fails_when_approved_worker_changes(self) -> None:
        temporary, root, order_path, _ = self.prepare()
        self.addCleanup(temporary.cleanup)
        worker = root / "tools" / "blender_fit_reviewed_multiview_surface.py"
        worker.write_text("# changed\n", encoding="utf-8")

        with self.assertRaisesRegex(AvatarLikenessAuthorError, "tooling"):
            validate_likeness_author_work_order(root, order_path)

    def test_work_order_review_summary_cannot_be_rewritten(self) -> None:
        temporary, root, order_path, order = self.prepare()
        self.addCleanup(temporary.cleanup)
        order["evidence_summary"]["reviewed_landmark_count"] += 1
        write_json(order_path, order)

        with self.assertRaisesRegex(AvatarLikenessAuthorError, "evidence summary"):
            validate_likeness_author_work_order(root, order_path)

    def test_finalize_requires_every_worker_output(self) -> None:
        temporary, root, order_path, _ = self.prepare()
        self.addCleanup(temporary.cleanup)

        with self.assertRaisesRegex(AvatarLikenessAuthorError, "worker result"):
            finalize_likeness_author_outputs(root, order_path)

    def test_owner_review_stage_requires_self_contained_real_scene_skin_geometry(self) -> None:
        cases = (
            ("external buffer", {"external_buffer_uri": True}, "external buffer"),
            ("missing POSITION", {"include_position": False}, "no POSITION"),
            (
                "unbounded POSITION",
                {"position_limit_violation": True},
                "unbounded geometry",
            ),
            ("missing skin", {"include_skin": False}, "no exported skin"),
            ("inactive mesh", {"active_mesh": False}, "missing or inactive"),
            (
                "unbounded scene transform",
                {"scene_transform_limit_violation": True},
                "transform is invalid or unbounded",
            ),
        )
        for label, options, error in cases:
            with self.subTest(label=label):
                temporary, root, order_path, order = self.prepare()
                try:
                    result_path = self.create_worker_outputs(root, order_path, order)
                    self.replace_worker_component(
                        root, order, result_path, "body", **options
                    )
                    with self.assertRaisesRegex(AvatarLikenessAuthorError, error):
                        finalize_likeness_author_outputs(root, order_path)
                finally:
                    temporary.cleanup()

    def test_reprojection_must_cover_all_reviewed_landmarks_with_sane_metrics(self) -> None:
        mutations = (
            (
                "count mismatch",
                lambda value: value["source_results"][0].__setitem__(
                    "compared_landmark_count",
                    value["source_results"][0]["compared_landmark_count"] - 1,
                ),
            ),
            (
                "mean exceeds max",
                lambda value: value["source_results"][0].update(
                    {"mean_error_px": 4.0, "max_error_px": 3.0}
                ),
            ),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                temporary, root, order_path, order = self.prepare()
                try:
                    result_path = self.create_worker_outputs(root, order_path, order)
                    self.mutate_worker_declaration(
                        root, result_path, "landmark_reprojection", mutate
                    )
                    with self.assertRaisesRegex(
                        AvatarLikenessAuthorError, "reprojection result"
                    ):
                        finalize_likeness_author_outputs(root, order_path)
                finally:
                    temporary.cleanup()

    def test_valid_outputs_stage_separate_component_and_rig_proofs_only(self) -> None:
        temporary, root, order_path, order = self.prepare()
        self.addCleanup(temporary.cleanup)
        self.create_worker_outputs(root, order_path, order)

        result = finalize_likeness_author_outputs(root, order_path)
        second = finalize_likeness_author_outputs(root, order_path)
        manifest = json.loads((root / result["review_candidate_manifest"]).read_text())
        component_proof = root / order["required_outputs"]["backend_proofs"]["component_integrity"]
        rig_proof = root / order["required_outputs"]["backend_proofs"]["rig_structure"]

        self.assertEqual("staged_for_private_owner_review_not_approved", result["status"])
        self.assertEqual("already_staged_verified", second["status"])
        self.assertTrue(component_proof.is_file())
        self.assertTrue(rig_proof.is_file())
        self.assertTrue(manifest["private_owner_review_ready"])
        self.assertFalse(manifest["identity_likeness_proven"])
        self.assertFalse(manifest["anatomical_completeness_proven"])
        self.assertFalse(manifest["stable_working_rig_proven"])
        self.assertFalse(manifest["runtime_activation_allowed"])

    def test_worker_cannot_self_approve_likeness(self) -> None:
        temporary, root, order_path, order = self.prepare()
        self.addCleanup(temporary.cleanup)
        result_path = self.create_worker_outputs(root, order_path, order)
        result = json.loads(result_path.read_text())
        declaration_binding = result["artifacts"]["surface_authorship"]
        declaration_path = root / declaration_binding["path"]
        declaration = json.loads(declaration_path.read_text())
        declaration["identity_likeness_proven"] = True
        write_json(declaration_path, declaration)
        declaration_binding["sha256"] = sha256_file(declaration_path)
        write_json(result_path, result)

        with self.assertRaisesRegex(AvatarLikenessAuthorError, "surface authorship"):
            finalize_likeness_author_outputs(root, order_path)

    def test_cli_returns_structured_block_for_dependency_validation_errors(self) -> None:
        for error in (
            AvatarProfilePreflightError("broken canonical registry"),
            AvatarProductionError("broken component GLB"),
        ):
            with self.subTest(error=type(error).__name__):
                stderr = io.StringIO()
                with (
                    patch.object(
                        likeness_cli,
                        "validate_queued_evidence_job",
                        side_effect=error,
                    ),
                    redirect_stderr(stderr),
                ):
                    exit_code = likeness_cli.main(
                        ["inspect", "--queued-job", "fixture.json"]
                    )
                payload = json.loads(stderr.getvalue())
                self.assertEqual(6, exit_code)
                self.assertEqual("blocked", payload["status"])
                self.assertFalse(payload["runtime_activation_allowed"])


if __name__ == "__main__":
    unittest.main()
