"""Fail-closed intake boundary for visual/body media entering KiraWorld.

The repository may contain synthetic bodies, neutral design charts, and
licensed non-photographic medical references.  It may not contain photographs
of real people or files that embed their source pixels.  Local private photos
can remain outside the repository while neutral replacements are proven.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping


FORBIDDEN_CLASSES = frozenset(
    {
        "real_person_photograph",
        "cropped_real_person_photograph",
        "annotated_real_person_photograph",
        "real_person_photograph_contact_sheet",
        "real_person_photograph_texture",
        "real_person_photograph_embedded_in_document",
        "real_person_photograph_embedded_in_model",
    }
)
ALLOWED_CLASSES = frozenset(
    {
        "synthetic_avatar_geometry",
        "synthetic_avatar_render",
        "neutral_nonperson_design_chart",
        "licensed_nonphotographic_medical_illustration",
        "licensed_medical_geometry",
        "procedural_nonperson_texture",
        "manifest_or_test_evidence",
    }
)
GEOMETRY_SUFFIXES = frozenset({".blend", ".fbx", ".glb", ".gltf", ".obj", ".usd", ".usdz"})
ROBERT_TARGETS = frozenset(
    {"BIOLOGICAL_ROBERT_AVATAR", "SYNTHETIC_ROBERT_TWIN_BODY"}
)


def evaluate_repository_media_candidate(candidate: Mapping[str, Any] | None) -> dict[str, Any]:
    data = candidate if isinstance(candidate, Mapping) else {}
    failures: list[str] = []
    content_class = str(data.get("content_class") or "").strip()
    path = Path(str(data.get("repository_path") or "").strip())

    if content_class in FORBIDDEN_CLASSES:
        failures.append("real_person_photographic_content_is_forbidden")
    elif content_class not in ALLOWED_CLASSES:
        failures.append("content_class_is_not_allowlisted")
    if data.get("repository_visibility") != "private":
        failures.append("repository_visibility_must_be_private")
    for field in (
        "is_real_person_photograph",
        "contains_real_person_photograph_pixels",
        "source_photographs_included",
        "public_export",
    ):
        if data.get(field) is not False:
            failures.append(f"{field}_must_be_false")

    is_unclothed = data.get("synthetic_unclothed_body") is True
    if data.get("synthetic_unclothed_body") not in (True, False):
        failures.append("synthetic_unclothed_body_must_be_boolean")
    if is_unclothed:
        if content_class != "synthetic_avatar_geometry":
            failures.append("unclothed_body_must_be_synthetic_geometry")
        if data.get("confirmed_adult") is not True:
            failures.append("unclothed_body_requires_confirmed_adult")
        if path.suffix.lower() not in GEOMETRY_SUFFIXES:
            failures.append("unclothed_body_requires_geometry_file")
    elif data.get("confirmed_adult") not in (True, False):
        failures.append("confirmed_adult_must_be_boolean")

    target_id = str(data.get("target_id") or "").strip()
    if target_id in ROBERT_TARGETS and content_class == "synthetic_avatar_geometry":
        if data.get("synthetic_geometry") is not True:
            failures.append("robert_body_must_be_declared_synthetic_geometry")

    return {
        "schema_version": 1,
        "allowed_for_private_repository": not failures,
        "content_class": content_class,
        "target_id": target_id,
        "real_person_photographs_allowed": False,
        "local_photo_deletion_authorized": False,
        "failures": failures,
    }


def replacement_chart_is_machine_useful(evidence: Mapping[str, Any] | None) -> bool:
    data = evidence if isinstance(evidence, Mapping) else {}
    required_true = (
        "exact_chart_hash_verified",
        "machine_readable_selector_ids_verified",
        "avatar_builder_selection_receipt_verified",
        "synthetic_before_after_hashes_verified",
        "repeatable_change_verified",
        "visual_and_structural_review_passed",
        "photo_coverage_mapping_verified",
    )
    return all(data.get(field) is True for field in required_true)
