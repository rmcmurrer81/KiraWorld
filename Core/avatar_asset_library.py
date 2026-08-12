"""Reusable Avatar Builder asset library, safety policy, and hair trials."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AVATAR_BUILDER_ROOT = PROJECT_ROOT / "Avatar" / "avatar_builder"
DEFAULT_LIBRARY_ROOT = AVATAR_BUILDER_ROOT / "asset_library"
DEFAULT_HAIR_TRIAL_ROOT = AVATAR_BUILDER_ROOT / "hair_training"
DEFAULT_BODY_TRAINING_ROOT = AVATAR_BUILDER_ROOT / "body_training"
DEFAULT_FACE_BODY_TRAINING_ROOT = AVATAR_BUILDER_ROOT / "face_body_training"
DEFAULT_WARDROBE_TRAINING_ROOT = AVATAR_BUILDER_ROOT / "wardrobe_training"
DEFAULT_SKIN_TONE_ROOT = AVATAR_BUILDER_ROOT / "skin_tone"
DEFAULT_POLICY_ROOT = AVATAR_BUILDER_ROOT / "policies"
MODEL_EXTENSIONS = {".glb", ".gltf", ".fbx", ".obj"}

ADULT_ANATOMY_TERMS = {
    "anatomy",
    "bone",
    "bones",
    "breast",
    "breasts",
    "female",
    "pelvis",
    "ligament",
    "ligaments",
    "organ",
    "organs",
    "muscle",
    "muscles",
    "naked",
    "reproductive",
    "nude",
    "nsfw",
    "sexy",
    "skeleton",
    "topless",
    "woman",
    "women",
}
NON_ADULT_TERMS = {
    "child",
    "children",
    "kid",
    "minor",
    "teen",
    "teenage",
    "student",
    "schoolgirl",
    "marinette",
    "ladybug",
}
ADULT_TERMS = {
    "adult",
    "aged_up",
    "aged-up",
    "age_up",
    "age-up",
    "kira",
    "lisa",
}

# These IDs are identity contracts, not fuzzy search terms. In particular,
# aliases such as ``minor_gwen`` or ``child_kira`` must never inherit the adult
# policy merely because their text contains a canonical adult's name.
NORMAL_MARINETTE_CANDIDATE_ID = "ladybug_marinette_expanded_smoke"
CANONICAL_ADULT_CANDIDATE_IDS = frozenset(
    {
        "kira",
        "lisa",
        "elsa_frozen_2013",
        "elsa_frozen_ii_2019",
        "peter_parker_spider_man_no_way_home_final_suit",
        "robert_mcmurrer_presence_ai",
        "spider_gwen_spider_gwen_20260606_013325",
    }
)
CANONICAL_NON_ADULT_CANDIDATE_IDS = frozenset({NORMAL_MARINETTE_CANDIDATE_ID})
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class AvatarMaturityPolicyError(ValueError):
    """Raised before writes when candidate identity and maturity conflict."""

    def __init__(self, validation: dict[str, Any]):
        self.validation = validation
        failures = validation.get("failures") or ["candidate_maturity_identity_policy_failed"]
        super().__init__(
            f"Avatar maturity policy blocked {validation.get('candidate_id')}: "
            + ", ".join(str(item) for item in failures)
        )


def _has_exact_confirmed_adult_classification(
    candidate_id: str,
    profile: dict[str, Any],
) -> bool:
    """Require exact subject-bound provenance; an age-up label is not enough."""

    age_review = (
        profile.get("age_review")
        if isinstance(profile.get("age_review"), dict)
        else {}
    )
    evidence = age_review.get("confirmed_adult_classification_evidence")
    if not isinstance(evidence, dict):
        return False
    recorded_at = str(evidence.get("recorded_at_utc") or "").strip()
    source_text = str(evidence.get("source_text") or "")
    source_text_sha256 = str(
        evidence.get("source_text_sha256") or ""
    ).strip().lower()
    try:
        parsed_at = datetime.fromisoformat(
            recorded_at[:-1] + "+00:00" if recorded_at.endswith("Z") else recorded_at
        )
    except ValueError:
        return False
    return (
        str(evidence.get("classification_id") or "").strip() != ""
        and str(evidence.get("subject_id") or "").strip().lower()
        == candidate_id.strip().lower()
        and evidence.get("maturity_status") == "confirmed_adult"
        and evidence.get("authority") == "Robert_explicit_owner_confirmation"
        and evidence.get("offline_confirmation_allowed") is True
        and evidence.get("network_lookup_required") is False
        and parsed_at.tzinfo is not None
        and parsed_at.utcoffset() is not None
        and source_text.strip() != ""
        and bool(SHA256_RE.fullmatch(source_text_sha256))
        and hashlib.sha256(source_text.encode("utf-8")).hexdigest()
        == source_text_sha256
    )


def _has_age_progression_provenance(profile: dict[str, Any]) -> bool:
    """Recognize durable spa-origin presentation metadata without inferring age."""

    age_review = (
        profile.get("age_review")
        if isinstance(profile.get("age_review"), dict)
        else {}
    )
    metadata = (
        profile.get("metadata")
        if isinstance(profile.get("metadata"), dict)
        else {}
    )
    contract = age_review.get("age_progression_contract")
    return (
        age_review.get("age_progression_presentation_label")
        == "adult_aged_up_variant"
        or (
            isinstance(contract, dict)
            and contract.get("contract") == "two_stage_spa_age_progression_v1"
        )
        or metadata.get("age_up_variant") is True
        or metadata.get("aged_up_variant") is True
    )


FACE_MOUTH_TERMS = {
    "mouth",
    "teeth",
    "tooth",
    "tongue",
    "gum",
    "gums",
    "jaw",
    "lip",
    "lips",
}
MOTION_TERMS = {
    "animation",
    "animated",
    "movement",
    "motion",
    "pose",
    "walk",
    "walking",
    "gait",
    "run",
    "running",
}
HAND_REFERENCE_TERMS = {
    "hand",
    "hands",
    "finger",
    "fingers",
    "gesture",
    "gestures",
}
HEAD_STRUCTURE_TERMS = {
    "head",
    "loomis",
    "planes",
    "expression",
    "expressions",
    "brow",
    "brows",
}
CHARACTER_REFERENCE_TERMS = {
    "alpha",
    "batgirl",
    "beth",
    "dulcea",
    "elsa",
    "fortnite",
    "frozen",
    "gogh",
    "gwen",
    "harley",
    "lucifer",
    "miles",
    "morales",
    "parker",
    "peter",
    "quinn",
    "raimi",
    "spider",
    "spiderman",
    "stacy",
    "stark",
    "tony",
    "vincent",
    "sarah",
    "michelle",
    "gellar",
    "geller",
    "zedd",
}
ADULT_CHARACTER_REFERENCE_TERMS = {
    "batgirl",
    "beth",
    "elsa",
    "gellar",
    "geller",
    "gogh",
    "harley",
    "quinn",
    "sarah",
    "vincent",
}
EXPLICIT_ADULT_FILE_TERMS = {
    "adult",
    "naked",
    "nsfw",
    "nude",
    "sexy",
    "topless",
}
ADULT_ANATOMY_REFERENCE_TERMS = {
    "adult",
    "anatomy",
    "bones",
    "female",
    "muscle",
    "muscles",
    "skeleton",
    "woman",
    "women",
}
PROP_REFERENCE_TERMS = {
    "dagger",
    "dragon",
    "mask",
    "morpher",
    "powermorpher",
    "power",
    "ranger",
    "rangers",
    "weapon",
}

# Wardrobe intake deliberately keeps construction references, world-state
# forms, and potentially wearable meshes separate.  A folded robe is useful to
# World Builder, for example, but it is not evidence that the same mesh can be
# skinned to a person and worn safely.
GARMENT_TERMS = {
    "apparel",
    "bathrobe",
    "blouse",
    "cardigan",
    "clothes",
    "clothing",
    "coat",
    "dress",
    "garment",
    "gown",
    "hoodie",
    "jacket",
    "leggings",
    "outfit",
    "pajama",
    "pajamas",
    "pyjama",
    "pyjamas",
    "robe",
    "shirt",
    "shorts",
    "skirt",
    "sleeve",
    "sweater",
    "trousers",
    "tunic",
    "wearable",
}
FABRIC_TERMS = {
    "canvas",
    "cloth",
    "cotton",
    "denim",
    "fabric",
    "fleece",
    "linen",
    "satin",
    "silk",
    "terry",
    "textile",
    "velvet",
    "wool",
}
PATTERN_TERMS = {"pattern", "sewing", "tailoring", "template"}
WORLD_FORM_TERMS = {"draped", "folded", "hanging", "hung", "worldform"}
WEARABLE_TERMS = {"fitted", "skinned", "wearable", "worn"}
WARDROBE_CATEGORIES = frozenset(
    {
        "garment_reference",
        "fabric_reference",
        "sewing_pattern_reference",
        "world_form_reference",
        "wearable_reference",
    }
)
MAX_GLTF_JSON_BYTES = 64 * 1024 * 1024
MAX_WARDROBE_ARTIFACT_BYTES = 2 * 1024 * 1024
WARDROBE_APPROVAL_REGISTRY_PATH = (
    DEFAULT_POLICY_ROOT / "wardrobe_runtime_approval_registry.json"
)
# Updating the owner registry requires an explicit matching code review/update;
# editing the JSON alone invalidates the trust anchor and keeps activation off.
WARDROBE_APPROVAL_REGISTRY_PINNED_SHA256 = (
    "916b71a614abd0d96eccf6537cdd6d430e76a8444c13335af308b44c919b906a"
)
WARDROBE_EVIDENCE_REQUIRED_CHECKS = (
    "glb_structure",
    "body_fit",
    "rig_compatibility",
    "skinning",
    "sleeve_openings",
    "collision",
)

HAIR_STYLE_TARGETS: dict[str, dict[str, Any]] = {
    "tom_holland_peter_parker": {
        "display_name": "Tom Holland / Peter Parker",
        "required_traits": ["short", "layered", "side_swept", "brown", "natural"],
        "helpful_traits": ["wavy", "male", "soft_volume"],
        "wrong_traits": ["long", "pigtails", "ponytail", "red"],
    },
    "marinette_dupain_cheng": {
        "display_name": "Marinette Dupain-Cheng",
        "required_traits": ["dark_blue", "side_swept", "bangs", "twin_pigtails", "low_pigtails"],
        "helpful_traits": ["stylized", "round_volume", "teen_safe"],
        "wrong_traits": ["red", "blonde", "single_ponytail", "short_male"],
    },
    "earth65_gwen_stacy": {
        "display_name": "Gwen Stacy / Earth-65",
        "required_traits": ["blonde", "short", "side_swept", "bob_or_undercut"],
        "helpful_traits": ["pink_tint", "punk", "asymmetrical"],
        "wrong_traits": ["long_red", "pigtails", "dark_blue"],
    },
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def project_relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def asset_library_manifest_path(library_root: Path | None = None) -> Path:
    return (library_root or DEFAULT_LIBRARY_ROOT) / "manifest.json"


def hair_trial_report_path(trial_root: Path | None = None) -> Path:
    return (trial_root or DEFAULT_HAIR_TRIAL_ROOT) / "hair_style_trials.json"


def hair_generation_curriculum_path(root: Path | None = None) -> Path:
    return (root or DEFAULT_HAIR_TRIAL_ROOT) / "hair_generation_curriculum.json"


def body_generation_curriculum_path(root: Path | None = None) -> Path:
    return (root or DEFAULT_BODY_TRAINING_ROOT) / "body_generation_curriculum.json"


def adult_face_body_trials_path(root: Path | None = None) -> Path:
    return (root or DEFAULT_FACE_BODY_TRAINING_ROOT) / "adult_face_body_trials.json"


def shoe_generation_curriculum_path(root: Path | None = None) -> Path:
    return (root or DEFAULT_WARDROBE_TRAINING_ROOT) / "shoe_generation_curriculum.json"


def skin_tone_template_path(root: Path | None = None) -> Path:
    return (root or DEFAULT_SKIN_TONE_ROOT) / "skin_tone_templates.json"


def spa_age_up_policy_path(root: Path | None = None) -> Path:
    return (root or DEFAULT_POLICY_ROOT) / "spa_age_up_policy.json"


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "asset"


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.lower()) if token}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _glb_embedded_terms(path: Path) -> set[str]:
    """Extract lightweight node/material hints from a binary GLB JSON chunk."""
    if path.suffix.lower() != ".glb":
        return set()
    try:
        # Only the JSON chunk is needed.  Do not read a potentially huge GLB
        # binary payload into RAM during reference intake.
        with path.open("rb") as handle:
            header = handle.read(12)
            if len(header) != 12 or header[:4] != b"glTF":
                return set()
            total_length = int.from_bytes(header[8:12], "little")
            consumed = 12
            while consumed + 8 <= total_length:
                chunk_header = handle.read(8)
                if len(chunk_header) != 8:
                    return set()
                chunk_len = int.from_bytes(chunk_header[:4], "little")
                chunk_type = int.from_bytes(chunk_header[4:8], "little")
                consumed += 8
                if chunk_type != 0x4E4F534A:
                    handle.seek(chunk_len, 1)
                    consumed += chunk_len
                    continue
                chunk = handle.read(chunk_len)
                if len(chunk) != chunk_len:
                    return set()
                parsed = json.loads(chunk.decode("utf-8").rstrip("\x00 "))
                names: list[str] = []
                for key in ("nodes", "meshes", "materials", "skins", "animations"):
                    for item in parsed.get(key, []) or []:
                        name = item.get("name") if isinstance(item, dict) else None
                        if name:
                            names.append(str(name))
                text = " ".join(names).lower()
                terms = _tokens(text)
                if parsed.get("animations"):
                    terms.update({"animation", "motion_reference"})
                if parsed.get("skins"):
                    terms.update({"rigged", "skin"})
                if "hairtie" in text or "hair_tie" in text or "hair tie" in text:
                    terms.update({"hair_tie", "tie"})
                if "scalp" in text:
                    terms.add("scalp")
                if re.search(r"\bm[_-]?hair\b|[_-]m[_-]hair|_m_hair", text):
                    terms.add("male")
                if len(re.findall(r"\bhair\d+", text)) >= 4:
                    terms.add("multi_style_pack")
                return terms
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return set()
    return set()


def _default_source_roots() -> list[Path]:
    desktop = Path.home() / "Desktop"
    return [
        desktop / "1model",
        desktop / "21",
        desktop / "40",
        desktop / "45",
        desktop / "more models",
        desktop / "real acting",
        desktop / "3d models",
        desktop / "3d model 2",
        desktop / "3d model 3",
        desktop / "3d model 4",
        desktop / "3d model 5",
        desktop / "beds models",
        desktop / "school",
    ]


def classify_avatar_asset(path: Path) -> dict[str, Any] | None:
    """Classify a model only when it helps the Avatar Builder directly."""
    name = path.stem.lower()
    name_tokens = _tokens(name)
    tokens = name_tokens | _glb_embedded_terms(path)
    tags: set[str] = set(tokens)

    # Classify from the filename before inspecting embedded node/bone names.
    # A complete rig normally contains nodes named hand, head, eye, pelvis,
    # and so on; treating those node names as the asset's primary purpose was
    # incorrectly turning whole character models into hand references.
    explicit_adult_file = bool(EXPLICIT_ADULT_FILE_TERMS & name_tokens)
    character_file = bool(CHARACTER_REFERENCE_TERMS & name_tokens)
    garment_file = bool(GARMENT_TERMS & name_tokens)
    pattern_file = bool(PATTERN_TERMS & name_tokens) and (
        garment_file or "sewing_pattern" in name or "sewing-pattern" in name
    )
    world_form_file = garment_file and bool(
        WORLD_FORM_TERMS & name_tokens
        or "world_form" in name
        or "world-form" in name
    )
    wearable_file = garment_file and bool(WEARABLE_TERMS & name_tokens)

    # Wardrobe intent in a filename wins over character names embedded in the
    # garment name (for example ``kira_robe_wearable.glb``).  It must never be
    # ingested as a complete character body merely because it names its owner.
    if pattern_file:
        tags.update({"wardrobe", "construction_pattern", "reference_only"})
        return _asset_policy("sewing_pattern_reference", tags, adult_only=explicit_adult_file)
    if world_form_file:
        tags.update({"wardrobe", "world_form", "not_wearable_evidence"})
        return _asset_policy("world_form_reference", tags, adult_only=explicit_adult_file)
    if wearable_file:
        tags.update({"wardrobe", "wearable_candidate", "fit_unverified"})
        return _asset_policy("wearable_reference", tags, adult_only=explicit_adult_file)
    if garment_file:
        tags.update({"wardrobe", "garment", "fit_unverified"})
        return _asset_policy("garment_reference", tags, adult_only=explicit_adult_file)
    if FABRIC_TERMS & name_tokens:
        tags.update({"wardrobe", "fabric", "reference_only"})
        return _asset_policy("fabric_reference", tags, adult_only=explicit_adult_file)
    if character_file and explicit_adult_file:
        tags.update({"adult_anatomy", "character_reference", "reference_only"})
        return _asset_policy("adult_anatomy_reference", tags, adult_only=True)
    if character_file:
        tags.update({"character_reference", "reference_only"})
        adult_only = bool(ADULT_CHARACTER_REFERENCE_TERMS & name_tokens)
        return _asset_policy("character_reference", tags, adult_only=adult_only)
    if (
        "hand_animation" in name
        or "rigged_hand" in name
        or "skeleton_rig" in name
        or MOTION_TERMS & name_tokens
    ):
        tags.add("motion_reference")
        adult_only = bool(
            EXPLICIT_ADULT_FILE_TERMS & name_tokens
            or {"female", "women", "woman"} & name_tokens
        )
        return _asset_policy("motion_reference", tags, adult_only=adult_only)
    if "hair" in name_tokens or "hairr" in name_tokens:
        tags.add("hair")
        return _asset_policy("hair_reference", tags, adult_only=False)
    if {"shoe", "shoes", "boot", "boots", "sneaker", "sneakers", "heel", "heels", "footwear"} & name_tokens:
        tags.add("shoe")
        return _asset_policy("shoe_reference", tags, adult_only=False)
    if {"eye", "eyes", "blink"} & name_tokens:
        tags.update({"eye", "blink_reference"})
        return _asset_policy("eye_reference", tags, adult_only=False)
    if HAND_REFERENCE_TERMS & name_tokens:
        tags.add("hand_reference")
        return _asset_policy("hand_reference", tags, adult_only=False)
    if HEAD_STRUCTURE_TERMS & name_tokens:
        tags.add("head_structure")
        return _asset_policy("head_structure_reference", tags, adult_only=False)
    if ADULT_ANATOMY_TERMS & name_tokens:
        tags.add("adult_anatomy")
        return _asset_policy("adult_anatomy_reference", tags, adult_only=True)
    if ADULT_ANATOMY_REFERENCE_TERMS & name_tokens:
        tags.add("adult_shape_or_anatomy")
        return _asset_policy("adult_female_shape_reference", tags, adult_only=True)
    if FACE_MOUTH_TERMS & tokens:
        tags.add("face_mouth")
        return _asset_policy("face_mouth_reference", tags, adult_only=False)
    if MOTION_TERMS & tokens:
        tags.add("motion_reference")
        return _asset_policy("motion_reference", tags, adult_only=False)
    if {"body", "base", "basemesh", "mesh", "skeleton", "female", "male", "woman", "man"} & name_tokens:
        adult_only = bool(
            {"female", "women", "woman", "nude"} & tokens
            or "womenfemale" in name
            or "adult_female" in name
            or "adult-female" in name
        )
        tags.add("base_body")
        return _asset_policy("base_body_reference", tags, adult_only=adult_only)
    if "hair" in tokens or "hairr" in tokens:
        tags.add("hair")
        return _asset_policy("hair_reference", tags, adult_only=False)
    if {"shoe", "shoes", "boot", "boots", "sneaker", "sneakers", "heel", "heels", "footwear"} & tokens:
        tags.add("shoe")
        return _asset_policy("shoe_reference", tags, adult_only=False)
    if {"eye", "eyes", "blink"} & tokens:
        tags.update({"eye", "blink_reference"})
        return _asset_policy("eye_reference", tags, adult_only=False)
    if {"body", "base", "basemesh", "mesh", "skeleton", "female", "male", "woman", "man"} & tokens:
        adult_only = bool(
            {"female", "women", "woman", "nude"} & tokens
            or "womenfemale" in name
            or "adult_female" in name
            or "adult-female" in name
        )
        tags.add("base_body")
        return _asset_policy("base_body_reference", tags, adult_only=adult_only)
    if PROP_REFERENCE_TERMS & tokens:
        tags.add("prop_reference")
        return _asset_policy("prop_reference", tags, adult_only=False)
    if CHARACTER_REFERENCE_TERMS & tokens:
        tags.add("character_reference")
        adult_only = bool(ADULT_CHARACTER_REFERENCE_TERMS & tokens)
        return _asset_policy("character_reference", tags, adult_only=adult_only)
    return None


def _asset_policy(category: str, tags: set[str], adult_only: bool) -> dict[str, Any]:
    if category in {"character_reference", "prop_reference"}:
        usage_policy = (
            "reference-only local model; may teach likeness, costume, accessories, or world props, "
            "but must not be copied as an AI body or treated as an approved runtime avatar"
        )
    elif category in {"adult_anatomy_reference", "adult_female_shape_reference"}:
        usage_policy = (
            "reference-only adult structure/proportion evidence; confirmed adult candidates only; "
            "never copy the reference mesh as an AI body or runtime avatar"
        )
    elif category in {"hand_reference", "head_structure_reference"}:
        usage_policy = "construction reference for hands, head planes, expressions, or proportions; do not copy as a finished body"
    elif category == "garment_reference":
        usage_policy = (
            "wardrobe construction reference or staged garment candidate; exact body hash, "
            "rig signature, fit evidence, and approval are required before runtime wear"
        )
    elif category == "wearable_reference":
        usage_policy = (
            "potential wearable only; filename or skinning hints are not proof of fit; exact "
            "body/rig compatibility and dressing evidence must pass before activation"
        )
    elif category == "fabric_reference":
        usage_policy = "fabric/material reference only; not a wearable mesh and not runtime dressing evidence"
    elif category == "sewing_pattern_reference":
        usage_policy = "garment construction/pattern reference only; not a fitted or wearable runtime asset"
    elif category == "world_form_reference":
        usage_policy = (
            "physical world-state garment form (for example folded, hung, or draped); "
            "not evidence that the mesh can be worn"
        )
    elif adult_only:
        usage_policy = "adult avatars only; never use for child, teen, or uncertain-age avatars"
    else:
        usage_policy = "available as a form, movement, hair, or non-explicit build reference"
    policy = {
        "category": category,
        "tags": sorted(tags),
        "adult_only": adult_only,
        "allowed_for_non_adult": not adult_only,
        "usage_policy": usage_policy,
    }
    if category in WARDROBE_CATEGORIES:
        can_be_fitted = category in {"garment_reference", "wearable_reference"}
        policy.update(
            {
                "asset_domain": "wardrobe",
                "maturity_compatibility": {
                    "scope": "adult_only" if adult_only else "body_fit_specific_all_maturities",
                    "allowed_maturity_classes": (
                        ["adult"]
                        if adult_only
                        else ["adult", "non_adult_doll_safe"]
                    ),
                    "must_not_change_subject_maturity": True,
                },
                "body_compatibility": {
                    "required_body_id": None,
                    "required_body_sha256": None,
                    "exact_body_hash_required_for_activation": can_be_fitted,
                    "fit_evidence_status": "not_tested",
                },
                "rig_compatibility": {
                    "required_rig_signature": None,
                    "skinning_status": "unverified" if can_be_fitted else "not_applicable",
                    "exact_rig_signature_required_for_activation": can_be_fitted,
                    "rig_evidence_status": "not_tested" if can_be_fitted else "not_applicable",
                },
                "approval_status": "staged_reference_only",
                "runtime_activation_allowed": False,
            }
        )
    return policy


def _read_avatar_asset_sidecar(path: Path) -> tuple[dict[str, Any], Path | None]:
    """Read optional local intake declarations without treating them as proof.

    Supported names are ``asset.glb.metadata.json``, ``asset.avatar.json``, and
    ``asset.metadata.json``.  The model hash written by the intake remains the
    authoritative identity; sidecar fields only declare intended compatibility.
    """
    candidates = (
        path.with_suffix(path.suffix + ".metadata.json"),
        path.with_suffix(".avatar.json"),
        path.with_suffix(".metadata.json"),
    )
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            value = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return {"metadata_status": "invalid_json"}, candidate
        if not isinstance(value, dict):
            return {"metadata_status": "invalid_root_type"}, candidate
        return value, candidate
    return {}, None


def _apply_avatar_asset_sidecar(
    policy: dict[str, Any],
    path: Path,
) -> dict[str, Any]:
    declared, sidecar_path = _read_avatar_asset_sidecar(path)
    if sidecar_path is None:
        return policy

    policy = dict(policy)
    policy["metadata_sidecar"] = str(sidecar_path)
    policy["metadata_status"] = str(declared.get("metadata_status") or "declared_unverified")
    declared_tags = declared.get("tags")
    if isinstance(declared_tags, list):
        policy["tags"] = sorted(
            set(policy.get("tags") or [])
            | {str(tag).strip().lower() for tag in declared_tags if str(tag).strip()}
        )

    # A sidecar may make a scope more restrictive, never less restrictive.
    declared_scope = str(declared.get("maturity_scope") or "").strip().lower()
    if declared_scope == "adult_only" and not policy.get("adult_only"):
        policy["adult_only"] = True
        policy["allowed_for_non_adult"] = False
        maturity = dict(policy.get("maturity_compatibility") or {})
        maturity.update(
            {
                "scope": "adult_only",
                "allowed_maturity_classes": ["adult"],
                "must_not_change_subject_maturity": True,
            }
        )
        policy["maturity_compatibility"] = maturity

    if policy.get("category") in WARDROBE_CATEGORIES:
        body = dict(policy.get("body_compatibility") or {})
        rig = dict(policy.get("rig_compatibility") or {})
        for key in ("required_body_id", "required_body_sha256"):
            if key in declared:
                body[key] = declared.get(key)
        for key in ("required_rig_signature",):
            if key in declared:
                rig[key] = declared.get(key)
        policy["body_compatibility"] = body
        policy["rig_compatibility"] = rig

        # Sidecars are untrusted declarations.  In particular, they cannot
        # award themselves fit/rig evidence or activation approval.  Those
        # facts must arrive as two separate, hash-bound artifacts supplied to
        # the validator by its caller.
        proof_claim_keys = {
            "fit_evidence_status",
            "rig_evidence_status",
            "skinning_status",
            "approval_status",
            "approval_artifact",
            "approval_artifact_path",
            "approval_artifact_sha256",
            "evidence_artifact",
            "evidence_artifact_path",
            "evidence_artifact_sha256",
            "runtime_activation_allowed",
        }
        ignored_claims = sorted(proof_claim_keys & set(declared))
        if ignored_claims:
            policy["ignored_untrusted_proof_claims"] = ignored_claims
            policy["metadata_status"] = "declared_unverified_proof_claims_ignored"

    provenance_fields = {}
    for key in ("creator", "license", "source_url", "source_collection", "notes"):
        if key in declared and declared.get(key) not in (None, ""):
            provenance_fields[key] = declared.get(key)
    if provenance_fields:
        policy["declared_provenance"] = provenance_fields
    return policy


def _resolve_record_file(asset: dict[str, Any], explicit_path: Path | None) -> Path | None:
    values: list[Path] = []
    if explicit_path is not None:
        values.append(Path(explicit_path))
    else:
        for key in ("local_file", "source_file"):
            raw = str(asset.get(key) or "").strip()
            if raw:
                values.append(Path(raw))
    for value in values:
        candidate = value if value.is_absolute() else PROJECT_ROOT / value
        if candidate.is_file():
            return candidate.resolve()
    return None


def _inspect_runtime_wearable_glb(path: Path | None) -> dict[str, Any]:
    """Validate the GLB container and a real skinned-mesh linkage."""
    failures: list[str] = []
    if path is None or not path.is_file():
        return {"status": "failed", "path": str(path) if path else None, "failures": ["wearable_asset_file_missing"]}
    if path.suffix.lower() != ".glb":
        return {"status": "failed", "path": str(path), "failures": ["runtime_wearable_asset_must_be_glb"]}

    parsed: dict[str, Any] | None = None
    bin_chunk_length = 0
    try:
        actual_size = path.stat().st_size
        with path.open("rb") as handle:
            header = handle.read(12)
            if len(header) != 12 or header[:4] != b"glTF":
                failures.append("invalid_glb_header")
            else:
                version = int.from_bytes(header[4:8], "little")
                total_length = int.from_bytes(header[8:12], "little")
                if version != 2:
                    failures.append("runtime_wearable_glb_version_must_be_2")
                if total_length != actual_size:
                    failures.append("glb_declared_length_does_not_match_file")
                consumed = 12
                chunk_index = 0
                while consumed + 8 <= min(total_length, actual_size):
                    chunk_header = handle.read(8)
                    if len(chunk_header) != 8:
                        failures.append("truncated_glb_chunk_header")
                        break
                    chunk_length = int.from_bytes(chunk_header[:4], "little")
                    chunk_type = int.from_bytes(chunk_header[4:8], "little")
                    consumed += 8
                    if chunk_length % 4 != 0:
                        failures.append("glb_chunk_length_not_aligned")
                    if consumed + chunk_length > total_length:
                        failures.append("glb_chunk_exceeds_declared_length")
                        break
                    if chunk_index == 0 and chunk_type != 0x4E4F534A:
                        failures.append("glb_first_chunk_is_not_json")
                    if chunk_type == 0x4E4F534A:
                        if parsed is not None:
                            failures.append("multiple_glb_json_chunks")
                            handle.seek(chunk_length, 1)
                        elif chunk_length > MAX_GLTF_JSON_BYTES:
                            failures.append("glb_json_chunk_too_large")
                            handle.seek(chunk_length, 1)
                        else:
                            raw_json = handle.read(chunk_length)
                            try:
                                value = json.loads(raw_json.rstrip(b"\x00 ").decode("utf-8"))
                                parsed = value if isinstance(value, dict) else None
                                if parsed is None:
                                    failures.append("glb_json_root_is_not_object")
                            except (UnicodeDecodeError, json.JSONDecodeError):
                                failures.append("invalid_glb_json")
                    elif chunk_type == 0x004E4942:
                        bin_chunk_length = max(bin_chunk_length, chunk_length)
                        handle.seek(chunk_length, 1)
                    else:
                        handle.seek(chunk_length, 1)
                    consumed += chunk_length
                    chunk_index += 1
                if consumed != total_length:
                    failures.append("glb_chunks_do_not_fill_declared_length")
    except OSError:
        failures.append("wearable_asset_file_unreadable")

    if parsed is None:
        failures.append("glb_json_chunk_missing_or_invalid")
    else:
        asset_version = str((parsed.get("asset") or {}).get("version") or "")
        if not asset_version.startswith("2"):
            failures.append("gltf_asset_version_must_be_2")
        nodes = parsed.get("nodes")
        meshes = parsed.get("meshes")
        skins = parsed.get("skins")
        accessors = parsed.get("accessors")
        buffer_views = parsed.get("bufferViews")
        buffers = parsed.get("buffers")
        if not all(isinstance(value, list) for value in (nodes, meshes, skins, accessors, buffer_views, buffers)):
            failures.append("glb_missing_skinned_mesh_tables")
        else:
            if len(buffers) != 1 or not isinstance(buffers[0], dict) or buffers[0].get("uri"):
                failures.append("runtime_glb_requires_one_embedded_buffer")
            else:
                declared_buffer_length = buffers[0].get("byteLength")
                if (
                    not isinstance(declared_buffer_length, int)
                    or declared_buffer_length <= 0
                    or declared_buffer_length > bin_chunk_length
                ):
                    failures.append("glb_binary_buffer_missing_or_too_short")

            valid_skinned_primitive = False
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                mesh_index = node.get("mesh")
                skin_index = node.get("skin")
                if not (
                    isinstance(mesh_index, int)
                    and 0 <= mesh_index < len(meshes)
                    and isinstance(skin_index, int)
                    and 0 <= skin_index < len(skins)
                ):
                    continue
                skin = skins[skin_index]
                joints = skin.get("joints") if isinstance(skin, dict) else None
                if not (
                    isinstance(joints, list)
                    and bool(joints)
                    and all(isinstance(index, int) and 0 <= index < len(nodes) for index in joints)
                ):
                    continue
                mesh = meshes[mesh_index]
                primitives = mesh.get("primitives") if isinstance(mesh, dict) else None
                for primitive in primitives or []:
                    attributes = primitive.get("attributes") if isinstance(primitive, dict) else None
                    if not isinstance(attributes, dict):
                        continue
                    accessor_indices = [attributes.get(key) for key in ("POSITION", "JOINTS_0", "WEIGHTS_0")]
                    if not all(isinstance(index, int) and 0 <= index < len(accessors) for index in accessor_indices):
                        continue
                    referenced_views: list[int] = []
                    for accessor_index in accessor_indices:
                        accessor = accessors[accessor_index]
                        view_index = accessor.get("bufferView") if isinstance(accessor, dict) else None
                        if not isinstance(view_index, int) or not 0 <= view_index < len(buffer_views):
                            break
                        referenced_views.append(view_index)
                    if len(referenced_views) != 3:
                        continue
                    if all(
                        isinstance(buffer_views[index], dict)
                        and buffer_views[index].get("buffer") == 0
                        for index in referenced_views
                    ):
                        valid_skinned_primitive = True
                        break
                if valid_skinned_primitive:
                    break
            if not valid_skinned_primitive:
                failures.append("glb_has_no_valid_skinned_mesh_primitive")

    failures = list(dict.fromkeys(failures))
    return {
        "status": "passed" if not failures else "failed",
        "path": str(path),
        "failures": failures,
    }


def _read_hashed_json_artifact(
    path: Path | None,
    *,
    label: str,
) -> tuple[dict[str, Any] | None, str | None, list[str]]:
    if path is None:
        return None, None, [f"{label}_artifact_missing"]
    artifact_path = Path(path)
    if not artifact_path.is_file():
        return None, None, [f"{label}_artifact_missing"]
    try:
        if artifact_path.stat().st_size > MAX_WARDROBE_ARTIFACT_BYTES:
            return None, None, [f"{label}_artifact_too_large"]
        raw = artifact_path.read_bytes()
        artifact_hash = hashlib.sha256(raw).hexdigest()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None, None, [f"{label}_artifact_unreadable_or_invalid_json"]
    if not isinstance(value, dict):
        return None, artifact_hash, [f"{label}_artifact_root_is_not_object"]
    return value, artifact_hash, []


def load_wardrobe_approval_registry() -> dict[str, Any]:
    """Load the fixed owner registry and verify its code-pinned integrity."""
    path = WARDROBE_APPROVAL_REGISTRY_PATH
    failures: list[str] = []
    value: dict[str, Any] = {}
    actual_hash = ""
    try:
        if not path.is_file():
            failures.append("owner_approval_registry_missing")
        elif path.stat().st_size > MAX_WARDROBE_ARTIFACT_BYTES:
            failures.append("owner_approval_registry_too_large")
        else:
            raw = path.read_bytes()
            actual_hash = hashlib.sha256(raw).hexdigest()
            parsed = json.loads(raw.decode("utf-8"))
            if isinstance(parsed, dict):
                value = parsed
            else:
                failures.append("owner_approval_registry_root_is_not_object")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        failures.append("owner_approval_registry_unreadable_or_invalid_json")

    pinned_hash = str(WARDROBE_APPROVAL_REGISTRY_PINNED_SHA256 or "").lower()
    if not re.fullmatch(r"[0-9a-f]{64}", pinned_hash):
        failures.append("owner_approval_registry_pinned_hash_invalid")
    elif actual_hash != pinned_hash:
        failures.append("owner_approval_registry_integrity_hash_mismatch")

    if value:
        if value.get("schema_version") != 1:
            failures.append("owner_approval_registry_schema_version_invalid")
        if value.get("registry_type") != "owner_controlled_wardrobe_runtime_approval_registry":
            failures.append("owner_approval_registry_type_invalid")
        owner = str(value.get("owner") or "").strip()
        if owner.lower() != "robert":
            failures.append("owner_approval_registry_owner_invalid")
        if value.get("status") != "active_fail_closed":
            failures.append("owner_approval_registry_status_invalid")
        entries = value.get("entries")
        if not isinstance(entries, list):
            failures.append("owner_approval_registry_entries_missing")
            entries = []
        seen_hashes: set[str] = set()
        for index, entry in enumerate(entries):
            prefix = f"owner_approval_registry_entry_{index}"
            if not isinstance(entry, dict):
                failures.append(f"{prefix}_invalid")
                continue
            approval_hash = str(entry.get("approval_artifact_sha256") or "").lower()
            if not re.fullmatch(r"[0-9a-f]{64}", approval_hash):
                failures.append(f"{prefix}_approval_hash_invalid")
            elif approval_hash in seen_hashes:
                failures.append(f"{prefix}_approval_hash_duplicate")
            seen_hashes.add(approval_hash)
            for key in ("asset_sha256", "body_sha256"):
                if not re.fullmatch(r"[0-9a-f]{64}", str(entry.get(key) or "").lower()):
                    failures.append(f"{prefix}_{key}_invalid")
            if entry.get("status") != "active" or entry.get("owner_approved") is not True:
                failures.append(f"{prefix}_not_active_owner_approved")
            if not str(entry.get("approval_id") or "").strip():
                failures.append(f"{prefix}_approval_id_missing")
            if str(entry.get("approved_by") or "").strip().lower() != owner.lower():
                failures.append(f"{prefix}_approver_not_registry_owner")
            if not str(entry.get("approved_at") or "").strip():
                failures.append(f"{prefix}_approved_at_missing")
            if not str(entry.get("rig_signature") or "").strip():
                failures.append(f"{prefix}_rig_signature_missing")
            if str(entry.get("maturity_class") or "") not in {
                "adult",
                "non_adult_doll_safe",
            }:
                failures.append(f"{prefix}_maturity_class_invalid")
        policy = value.get("policy")
        if not isinstance(policy, dict):
            failures.append("owner_approval_registry_policy_missing")
        else:
            expected_policy = {
                "default": "deny",
                "sidecar_claims_are_proof": False,
                "caller_supplied_hashes_are_trust_anchors": False,
                "exact_approval_hash_must_be_listed": True,
                "registry_file_integrity_must_match_pinned_code_hash": True,
                "current_runtime_wearables_approved": len(entries),
            }
            for key, expected in expected_policy.items():
                if policy.get(key) != expected:
                    failures.append(f"owner_approval_registry_policy_mismatch:{key}")

    failures = list(dict.fromkeys(failures))
    return {
        "status": "passed" if not failures else "failed",
        "path": str(path),
        "sha256": actual_hash or None,
        "pinned_sha256": pinned_hash or None,
        "entries": value.get("entries", []) if isinstance(value.get("entries"), list) else [],
        "failures": failures,
    }


def _owner_registry_approval_failures(
    registry: dict[str, Any],
    *,
    approval_artifact_sha256: str,
    asset_sha256: str,
    body_sha256: str,
    rig_signature: str,
    maturity_class: str,
) -> list[str]:
    failures = list(registry.get("failures") or [])
    if failures:
        return failures
    matching = [
        entry
        for entry in registry.get("entries") or []
        if isinstance(entry, dict)
        and str(entry.get("approval_artifact_sha256") or "").lower()
        == approval_artifact_sha256
    ]
    if len(matching) != 1:
        return ["approval_artifact_hash_not_listed_in_owner_registry"]
    entry = matching[0]
    expected = {
        "asset_sha256": asset_sha256,
        "body_sha256": body_sha256,
        "rig_signature": rig_signature,
        "maturity_class": maturity_class,
    }
    for key, expected_value in expected.items():
        actual = str(entry.get(key) or "")
        if key.endswith("sha256"):
            actual = actual.lower()
        if actual != expected_value:
            failures.append(f"owner_registry_approval_binding_mismatch:{key}")
    return failures


def _binding_failures(
    artifact: dict[str, Any],
    *,
    label: str,
    asset_sha256: str,
    body_sha256: str,
    rig_signature: str,
    maturity_class: str,
) -> list[str]:
    bindings = artifact.get("bindings")
    if not isinstance(bindings, dict):
        return [f"{label}_bindings_missing"]
    failures: list[str] = []
    if str(bindings.get("asset_sha256") or "").lower() != asset_sha256:
        failures.append(f"{label}_asset_hash_mismatch")
    if str(bindings.get("body_sha256") or "").lower() != body_sha256:
        failures.append(f"{label}_body_hash_mismatch")
    if str(bindings.get("rig_signature") or "") != rig_signature:
        failures.append(f"{label}_rig_signature_mismatch")
    if str(bindings.get("maturity_class") or "") != maturity_class:
        failures.append(f"{label}_maturity_class_mismatch")
    return failures


def _validate_wardrobe_evidence_artifact(
    artifact: dict[str, Any] | None,
    *,
    asset_sha256: str,
    body_sha256: str,
    rig_signature: str,
    maturity_class: str,
) -> list[str]:
    if artifact is None:
        return []
    failures: list[str] = []
    if artifact.get("schema_version") != 1:
        failures.append("evidence_schema_version_invalid")
    if artifact.get("artifact_type") != "wardrobe_fit_rig_evidence":
        failures.append("evidence_artifact_type_invalid")
    if artifact.get("status") != "passed":
        failures.append("evidence_status_not_passed")
    producer = artifact.get("producer")
    if not (
        isinstance(producer, dict)
        and producer.get("kind") == "independent_wardrobe_evidence_pipeline"
        and producer.get("self_declared") is False
        and bool(str(producer.get("run_id") or "").strip())
    ):
        failures.append("evidence_producer_not_independent_or_identified")
    if artifact.get("independent_from_asset_intake") is not True:
        failures.append("evidence_not_independent_from_asset_intake")
    failures.extend(
        _binding_failures(
            artifact,
            label="evidence",
            asset_sha256=asset_sha256,
            body_sha256=body_sha256,
            rig_signature=rig_signature,
            maturity_class=maturity_class,
        )
    )
    checks = artifact.get("checks")
    if not isinstance(checks, dict):
        failures.append("evidence_checks_missing")
    else:
        for check in WARDROBE_EVIDENCE_REQUIRED_CHECKS:
            if checks.get(check) != "passed":
                failures.append(f"evidence_check_not_passed:{check}")
    return failures


def _validate_wardrobe_approval_artifact(
    artifact: dict[str, Any] | None,
    *,
    asset_sha256: str,
    body_sha256: str,
    rig_signature: str,
    maturity_class: str,
    evidence_artifact_sha256: str,
) -> list[str]:
    if artifact is None:
        return []
    failures: list[str] = []
    if artifact.get("schema_version") != 1:
        failures.append("approval_schema_version_invalid")
    if artifact.get("artifact_type") != "wardrobe_runtime_activation_approval":
        failures.append("approval_artifact_type_invalid")
    if artifact.get("status") != "approved" or artifact.get("decision") != "approve":
        failures.append("approval_decision_not_approved")
    if artifact.get("approval_scope") != "exact_wardrobe_runtime_activation":
        failures.append("approval_scope_invalid")
    reviewer = artifact.get("reviewer")
    if not (
        isinstance(reviewer, dict)
        and reviewer.get("kind") == "human"
        and bool(str(reviewer.get("id") or "").strip())
    ):
        failures.append("approval_human_reviewer_missing")
    if artifact.get("independent_from_builder_declaration") is not True:
        failures.append("approval_not_independent_from_builder_declaration")
    failures.extend(
        _binding_failures(
            artifact,
            label="approval",
            asset_sha256=asset_sha256,
            body_sha256=body_sha256,
            rig_signature=rig_signature,
            maturity_class=maturity_class,
        )
    )
    if str(artifact.get("evidence_artifact_sha256") or "").lower() != evidence_artifact_sha256:
        failures.append("approval_evidence_artifact_hash_mismatch")
    return failures


def validate_wardrobe_asset_compatibility(
    asset: dict[str, Any],
    *,
    maturity_class: str,
    body_sha256: str,
    rig_signature: str,
    asset_path: Path | None = None,
    evidence_artifact: Path | None = None,
    approval_artifact: Path | None = None,
) -> dict[str, Any]:
    """Fail closed using separate, exact, hash-bound evidence and approval.

    Sidecar fields are declarations only.  The two proof artifacts must be
    supplied explicitly by the caller; paths or hashes claimed by the asset or
    its sidecar are intentionally ignored.  Approval is trusted only when its
    exact hash and bindings also appear in the integrity-pinned owner registry.
    """
    category = str(asset.get("category") or "")
    if category not in {"garment_reference", "wearable_reference"}:
        return {
            "status": "not_applicable",
            "category": category,
            "compatible_for_staged_testing": False,
            "runtime_activation_allowed": False,
            "failures": ["asset_is_not_a_fitted_wearable_candidate"],
        }

    compatibility_failures: list[str] = []
    allowed_classes = set(
        str(value)
        for value in (asset.get("maturity_compatibility") or {}).get(
            "allowed_maturity_classes", []
        )
    )
    if maturity_class not in allowed_classes:
        compatibility_failures.append("maturity_class_not_allowed_for_garment")

    body = asset.get("body_compatibility") or {}
    required_body_sha256 = str(body.get("required_body_sha256") or "").lower()
    active_body_sha256 = str(body_sha256 or "").lower()
    if not re.fullmatch(r"[0-9a-f]{64}", required_body_sha256):
        compatibility_failures.append("exact_body_hash_not_declared")
    elif not re.fullmatch(r"[0-9a-f]{64}", active_body_sha256):
        compatibility_failures.append("active_body_hash_missing_or_invalid")
    elif active_body_sha256 != required_body_sha256:
        compatibility_failures.append("body_hash_mismatch")

    rig = asset.get("rig_compatibility") or {}
    required_rig = str(rig.get("required_rig_signature") or "").strip()
    active_rig = str(rig_signature or "").strip()
    if not required_rig:
        compatibility_failures.append("rig_signature_not_declared")
    elif not active_rig:
        compatibility_failures.append("active_rig_signature_missing")
    elif active_rig != required_rig:
        compatibility_failures.append("rig_signature_mismatch")

    resolved_asset_path = _resolve_record_file(asset, asset_path)
    glb_validation = _inspect_runtime_wearable_glb(resolved_asset_path)
    compatibility_failures.extend(glb_validation["failures"])
    actual_asset_sha256 = _sha256(resolved_asset_path) if resolved_asset_path and resolved_asset_path.is_file() else ""
    recorded_asset_sha256 = str(asset.get("sha256") or "").lower()
    if not re.fullmatch(r"[0-9a-f]{64}", recorded_asset_sha256):
        compatibility_failures.append("asset_record_sha256_missing_or_invalid")
    elif actual_asset_sha256 != recorded_asset_sha256:
        compatibility_failures.append("asset_file_hash_mismatch")
    provenance_hash = str((asset.get("provenance") or {}).get("source_sha256") or "").lower()
    if provenance_hash and provenance_hash != recorded_asset_sha256:
        compatibility_failures.append("provenance_asset_hash_mismatch")

    evidence_value, evidence_hash, evidence_failures = _read_hashed_json_artifact(
        evidence_artifact,
        label="evidence",
    )
    evidence_failures.extend(
        _validate_wardrobe_evidence_artifact(
            evidence_value,
            asset_sha256=actual_asset_sha256,
            body_sha256=active_body_sha256,
            rig_signature=active_rig,
            maturity_class=maturity_class,
        )
    )

    approval_value, approval_hash, approval_failures = _read_hashed_json_artifact(
        approval_artifact,
        label="approval",
    )
    approval_failures.extend(
        _validate_wardrobe_approval_artifact(
            approval_value,
            asset_sha256=actual_asset_sha256,
            body_sha256=active_body_sha256,
            rig_signature=active_rig,
            maturity_class=maturity_class,
            evidence_artifact_sha256=evidence_hash or "",
        )
    )
    approval_registry = load_wardrobe_approval_registry()
    approval_failures.extend(
        _owner_registry_approval_failures(
            approval_registry,
            approval_artifact_sha256=approval_hash or "",
            asset_sha256=actual_asset_sha256,
            body_sha256=active_body_sha256,
            rig_signature=active_rig,
            maturity_class=maturity_class,
        )
    )

    if evidence_artifact is not None and approval_artifact is not None:
        try:
            if Path(evidence_artifact).resolve() == Path(approval_artifact).resolve():
                approval_failures.append("evidence_and_approval_must_be_separate_artifacts")
        except OSError:
            approval_failures.append("artifact_paths_could_not_be_resolved")
    sidecar_path = str(asset.get("metadata_sidecar") or "")
    for artifact, label in ((evidence_artifact, "evidence"), (approval_artifact, "approval")):
        if artifact is not None and sidecar_path:
            try:
                if Path(artifact).resolve() == Path(sidecar_path).resolve():
                    approval_failures.append(f"{label}_artifact_cannot_be_asset_sidecar")
            except OSError:
                approval_failures.append(f"{label}_artifact_path_could_not_be_resolved")

    compatibility_failures = list(dict.fromkeys(compatibility_failures))
    evidence_failures = list(dict.fromkeys(evidence_failures))
    approval_failures = list(dict.fromkeys(approval_failures))
    failures = compatibility_failures + evidence_failures + approval_failures
    staged_compatible = not compatibility_failures
    runtime_allowed = not failures
    return {
        "status": "passed" if runtime_allowed else "failed",
        "category": category,
        "maturity_class": maturity_class,
        "required_body_sha256": required_body_sha256 or None,
        "active_body_sha256": active_body_sha256 or None,
        "required_rig_signature": required_rig or None,
        "active_rig_signature": active_rig or None,
        "asset_file": str(resolved_asset_path) if resolved_asset_path else None,
        "asset_file_sha256": actual_asset_sha256 or None,
        "glb_validation": glb_validation,
        "evidence_artifact": {
            "path": str(evidence_artifact) if evidence_artifact else None,
            "sha256": evidence_hash,
            "status": "passed" if not evidence_failures else "failed",
        },
        "approval_artifact": {
            "path": str(approval_artifact) if approval_artifact else None,
            "sha256": approval_hash,
            "status": "passed" if not approval_failures else "failed",
        },
        "owner_approval_registry": {
            "path": approval_registry.get("path"),
            "sha256": approval_registry.get("sha256"),
            "pinned_sha256": approval_registry.get("pinned_sha256"),
            "status": approval_registry.get("status"),
        },
        "ignored_sidecar_proof_claims": asset.get("ignored_untrusted_proof_claims", []),
        "compatible_for_staged_testing": staged_compatible,
        "runtime_activation_allowed": runtime_allowed,
        "compatibility_failures": compatibility_failures,
        "evidence_failures": evidence_failures,
        "approval_failures": approval_failures,
        "failures": failures,
        "approval_gate": "passed" if not approval_failures else "failed",
    }


def discover_avatar_assets(source_roots: Iterable[Path] | None = None) -> list[dict[str, Any]]:
    roots = list(_default_source_roots() if source_roots is None else source_roots)
    records: list[dict[str, Any]] = []
    seen_sources: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        candidates = [root] if root.is_file() else sorted(root.rglob("*"))
        for source in candidates:
            if not source.is_file() or source.suffix.lower() not in MODEL_EXTENSIONS:
                continue
            source = source.resolve()
            if source in seen_sources:
                continue
            seen_sources.add(source)
            policy = classify_avatar_asset(source)
            if not policy:
                continue
            policy = _apply_avatar_asset_sidecar(policy, source)
            embedded_terms = _glb_embedded_terms(source)
            if embedded_terms:
                policy["tags"] = sorted(set(policy["tags"]) | embedded_terms)
            records.append({
                "source_file": str(source),
                "source_folder": str(root.parent if root.is_file() else root),
                "filename": source.name,
                "size_bytes": source.stat().st_size,
                **policy,
            })
    return records


def _existing_library_records(library_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not library_root.exists():
        return records
    for source in sorted(library_root.rglob("*")):
        if not source.is_file() or source.name == "manifest.json" or source.suffix.lower() not in MODEL_EXTENSIONS:
            continue
        category = source.parent.name
        tags = _tokens(source.stem)
        embedded_terms = _glb_embedded_terms(source)
        if embedded_terms:
            tags |= embedded_terms
        adult_only = (
            category in {"adult_anatomy_reference", "adult_female_shape_reference"}
            or bool(EXPLICIT_ADULT_FILE_TERMS & tags)
            or (category == "character_reference" and bool(ADULT_CHARACTER_REFERENCE_TERMS & tags))
            or (
                category == "base_body_reference"
                and bool(
                    {"female", "women", "woman", "nude"} & tags
                    or "womenfemale" in source.stem.lower()
                    or "adult_female" in source.stem.lower()
                    or "adult-female" in source.stem.lower()
                )
            )
        )
        policy = _asset_policy(category, tags, adult_only)
        policy = _apply_avatar_asset_sidecar(policy, source)
        records.append({
            "source_file": str(source),
            "source_folder": str(source.parent),
            "filename": source.name,
            "size_bytes": source.stat().st_size,
            **policy,
            "local_file": project_relative(source),
        })
    return records


def build_avatar_asset_library(
    source_roots: Iterable[Path] | None = None,
    library_root: Path | None = None,
    copy_assets: bool = True,
) -> dict[str, Any]:
    """Copy reusable builder assets into the project and write a manifest."""
    library_root = library_root or DEFAULT_LIBRARY_ROOT
    source_records = discover_avatar_assets(source_roots)
    copied_records: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()

    for record in source_records:
        source = Path(record["source_file"])
        sha = _sha256(source)
        if sha in seen_hashes:
            continue
        seen_hashes.add(sha)
        category = str(record["category"])
        target_name = f"{_slug(source.stem)}_{sha[:10]}{source.suffix.lower()}"
        target = library_root / category / target_name
        if copy_assets:
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                shutil.copy2(source, target)
        copied_records.append({
            **record,
            "id": f"{category}:{_slug(source.stem)}:{sha[:10]}",
            "sha256": sha,
            "local_file": project_relative(target),
            "provenance": {
                "origin": "local_source_intake",
                "source_file": str(source),
                "source_folder": str(record.get("source_folder") or source.parent),
                "source_sha256": sha,
                "copied_file": project_relative(target),
                "metadata_sidecar": record.get("metadata_sidecar"),
                "declared": record.get("declared_provenance", {}),
            },
        })

    for record in _existing_library_records(library_root):
        source = Path(record["source_file"])
        sha = _sha256(source)
        if sha in seen_hashes:
            continue
        seen_hashes.add(sha)
        copied_records.append({
            **record,
            "id": f"{record['category']}:{_slug(source.stem)}:{sha[:10]}",
            "sha256": sha,
            "provenance": {
                "origin": "existing_library_reindex",
                "source_file": str(source),
                "source_folder": str(source.parent),
                "source_sha256": sha,
                "copied_file": record.get("local_file"),
                "metadata_sidecar": record.get("metadata_sidecar"),
                "declared": record.get("declared_provenance", {}),
            },
        })

    categories: dict[str, int] = {}
    for record in copied_records:
        category = str(record["category"])
        categories[category] = categories.get(category, 0) + 1

    manifest = {
        "schema_version": 2,
        "updated_at": now_iso(),
        "library_root": project_relative(library_root),
        "asset_count": len(copied_records),
        "categories": dict(sorted(categories.items())),
        "maturity_rule": {
            "adult_anatomy_assets_are_adult_only": True,
            "non_adult_avatars_use_doll_safe_body_policy": True,
            "normal_marinette_identity_remains_non_adult": True,
            "kira_is_adult": True,
            "age_up_presentation_label_defaults_to_unresolved": True,
            "age_up_variant_requires_separate_exact_confirmed_adult_classification": True,
            "age_up_adult_anatomy_requires_separate_person_choice_and_stage_two_gate": True,
            "clothing_never_changes_subject_maturity": True,
            "wearables_require_exact_body_and_rig_compatibility": True,
        },
        "records": sorted(
            copied_records,
            key=lambda item: (str(item["category"]), str(item["filename"]).lower()),
        ),
    }
    manifest_path = asset_library_manifest_path(library_root)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def infer_avatar_maturity_policy(
    candidate_id: str,
    profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the body/anatomy gate for a candidate before any asset is selected."""
    profile = profile or {}
    age_review = profile.get("age_review", {}) if isinstance(profile.get("age_review"), dict) else {}
    override = str(age_review.get("maturity_class_override") or "").strip()
    override_reason = str(age_review.get("reason") or "Robert or Avatar Builder reviewed this maturity policy.").strip()
    if override in {
        "adult",
        "adult_aged_up_variant",
        "non_adult_doll_safe",
        "uncertain_non_adult_safe_default",
    }:
        canonical_adult_identity = (
            candidate_id.strip().lower() in CANONICAL_ADULT_CANDIDATE_IDS
        )
        exact_owner_classification = _has_exact_confirmed_adult_classification(
            candidate_id, profile
        )
        age_progression_provenance = (
            override == "adult_aged_up_variant"
            or _has_age_progression_provenance(profile)
        )
        exact_confirmed_adult = (
            override == "adult"
            and (canonical_adult_identity or exact_owner_classification)
            or (
                override == "adult_aged_up_variant"
                and exact_owner_classification
            )
        )
        anatomy_choice_recorded = age_review.get(
            "resident_adult_anatomy_choice_recorded"
        ) is True
        anatomy_allowed = exact_confirmed_adult and (
            anatomy_choice_recorded if age_progression_provenance else True
        )
        effective_class = (
            "adult"
            if age_progression_provenance and exact_confirmed_adult
            else (
                "uncertain_non_adult_safe_default"
                if age_progression_provenance
                or (override == "adult" and not exact_confirmed_adult)
                else override
            )
        )
        return {
            "schema_version": 1,
            "candidate_id": candidate_id,
            "maturity_class": effective_class,
            "requested_maturity_class_override": override,
            "presentation_variant_label": (
                "adult_aged_up_variant"
                if age_progression_provenance
                else None
            ),
            "age_progression_provenance_preserved": age_progression_provenance,
            "exact_maturity_status": (
                "confirmed_adult"
                if exact_confirmed_adult
                else (
                    "non_adult"
                    if override == "non_adult_doll_safe"
                    else "unresolved"
                )
            ),
            "adult_classification_confirmed": exact_confirmed_adult,
            "resident_adult_anatomy_choice_recorded": anatomy_choice_recorded,
            "anatomy_allowed": anatomy_allowed,
            "adult_anatomy_assets_allowed": anatomy_allowed,
            "doll_safe_body_allowed": not anatomy_allowed,
            "neutral_adult_anatomy_required": anatomy_allowed,
            "required_base_body_policy": (
                "use a neutral adult base body/anatomy; non-adult doll-safe smoothing is forbidden"
                if anatomy_allowed
                else "use non-explicit doll-safe base body; block adult anatomy and explicit body assets"
            ),
            "notes": [
                override_reason,
                "Full anatomy references are adult-only.",
                "Normal Marinette/Ladybug remains non-adult; a separate age-progressed presentation variant remains unresolved until exact subject-bound classification.",
                "Uncertain age defaults to non-adult-safe body policy.",
                "The adult_aged_up_variant label is presentation/build metadata and never proves confirmed adulthood or anatomy authorization.",
                "A free-text adult word or unproven adult override never establishes confirmed adulthood; use a canonical exact identity or subject-bound Robert confirmation evidence.",
            ],
        }
    text = " ".join(
        [
            candidate_id,
            str(profile.get("display_name", "")),
            str(profile.get("role_title", "")),
            json.dumps(profile.get("visual_identity", {}), sort_keys=True),
            json.dumps(profile.get("metadata", {}), sort_keys=True),
            json.dumps(profile.get("age_review", {}), sort_keys=True),
        ]
    ).lower()
    metadata = profile.get("metadata", {}) if isinstance(profile.get("metadata"), dict) else {}
    normalized_text = re.sub(r"[_-]+", " ", text)
    explicit_age_up = bool(
        metadata.get("age_up_variant")
        or metadata.get("aged_up_variant")
        or re.search(r"\b(?:aged|age)\s+up\s+variant\b", normalized_text)
    )
    hard_non_adult_claim = bool(
        re.search(
            r"\b(?:non\s+adult|not\s+(?:an?\s+)?adult|minor|child|children|kid|kids|"
            r"teen|teenage|teenager|schoolgirl|marinette|ladybug)\b",
            normalized_text,
        )
    )
    weak_non_adult_claim = any(term in normalized_text for term in ("student", "school age"))
    exact_adult_identity = candidate_id.strip().lower() in CANONICAL_ADULT_CANDIDATE_IDS
    exact_owner_classification = _has_exact_confirmed_adult_classification(
        candidate_id, profile
    )

    if explicit_age_up:
        maturity_class = (
            "adult" if exact_owner_classification else "uncertain_non_adult_safe_default"
        )
    elif hard_non_adult_claim:
        maturity_class = "non_adult_doll_safe"
    elif exact_adult_identity or exact_owner_classification:
        maturity_class = "adult"
    elif weak_non_adult_claim:
        maturity_class = "uncertain_non_adult_safe_default"
    else:
        maturity_class = "uncertain_non_adult_safe_default"

    exact_confirmed_adult = maturity_class == "adult" and (
        exact_adult_identity or exact_owner_classification
    )
    anatomy_choice_recorded = age_review.get(
        "resident_adult_anatomy_choice_recorded"
    ) is True
    anatomy_allowed = exact_confirmed_adult and (
        anatomy_choice_recorded if explicit_age_up else True
    )
    return {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "maturity_class": maturity_class,
        "presentation_variant_label": (
            "adult_aged_up_variant"
            if explicit_age_up
            else None
        ),
        "age_progression_provenance_preserved": explicit_age_up,
        "exact_maturity_status": (
            "confirmed_adult"
            if exact_confirmed_adult
            else (
                "non_adult"
                if maturity_class == "non_adult_doll_safe"
                else "unresolved"
            )
        ),
        "adult_classification_confirmed": exact_confirmed_adult,
        "resident_adult_anatomy_choice_recorded": anatomy_choice_recorded,
        "anatomy_allowed": anatomy_allowed,
        "adult_anatomy_assets_allowed": anatomy_allowed,
        "doll_safe_body_allowed": not anatomy_allowed,
        "neutral_adult_anatomy_required": anatomy_allowed,
        "required_base_body_policy": (
            "use a neutral adult base body/anatomy; non-adult doll-safe smoothing is forbidden"
            if anatomy_allowed
            else "use non-explicit doll-safe base body; block adult anatomy and explicit body assets"
        ),
        "notes": [
            "Full anatomy references are adult-only.",
            "Normal Marinette/Ladybug remains non-adult; a separate age-progressed presentation variant remains unresolved until exact subject-bound classification.",
            "Uncertain age defaults to non-adult-safe body policy.",
            "The adult_aged_up_variant label is presentation/build metadata and never proves confirmed adulthood or anatomy authorization.",
            "Generic adult words in names, titles, policies, tests, anatomy notes, or metadata do not classify a person.",
        ],
    }


def canonical_avatar_maturity_class(candidate_id: str) -> str:
    """Return an identity-locked maturity class using exact IDs only."""
    normalized = candidate_id.strip().lower()
    if normalized in CANONICAL_ADULT_CANDIDATE_IDS:
        return "adult"
    if normalized in CANONICAL_NON_ADULT_CANDIDATE_IDS:
        return "non_adult_doll_safe"
    return ""


def is_separate_age_up_variant_profile(
    candidate_id: str,
    profile: dict[str, Any] | None = None,
) -> bool:
    """Require an age-up marker on a distinct candidate identity/profile."""
    profile = profile or {}
    normalized_id = candidate_id.strip().lower()
    profile_id = str(profile.get("candidate_id") or "").strip().lower()
    if not profile_id:
        return False
    if profile_id != normalized_id or normalized_id in CANONICAL_NON_ADULT_CANDIDATE_IDS:
        return False
    metadata = profile.get("metadata") if isinstance(profile.get("metadata"), dict) else {}
    marker_text = " ".join(
        (
            normalized_id,
            str(profile.get("display_name") or "").lower(),
            str(profile.get("role_title") or "").lower(),
        )
    )
    explicit_marker = bool(
        metadata.get("age_up_variant")
        or metadata.get("aged_up_variant")
        or re.search(r"\b(?:aged|age)[ _-]*up[ _-]*variant\b", marker_text)
    )
    return explicit_marker


def validate_candidate_maturity_identity(
    candidate_id: str,
    profile: dict[str, Any] | None = None,
    *,
    requested_maturity_class: str = "",
) -> dict[str, Any]:
    """Validate maturity metadata against the candidate's stable identity.

    This is the control-plane companion to ``validate_avatar_body_policy``.
    It runs before a prepare/chat/review action may persist a maturity change.
    """
    profile = dict(profile or {})
    normalized_id = candidate_id.strip().lower()
    recorded_profile_id = str(profile.get("candidate_id") or normalized_id).strip().lower()
    failures: list[str] = []
    if recorded_profile_id != normalized_id:
        failures.append("candidate_profile_identity_does_not_match_requested_candidate")

    effective_profile = dict(profile)
    age_review = (
        dict(effective_profile.get("age_review") or {})
        if isinstance(effective_profile.get("age_review"), dict)
        else {}
    )
    requested = requested_maturity_class.strip()
    if requested:
        age_review["maturity_class_override"] = requested
        age_review.setdefault("reason", "Requested Avatar Builder maturity change.")
        effective_profile["age_review"] = age_review
    effective_policy = infer_avatar_maturity_policy(candidate_id, effective_profile)
    effective_class = str(effective_policy.get("maturity_class") or "")
    presentation_variant_label = str(
        effective_policy.get("presentation_variant_label") or ""
    )

    baseline_profile = dict(profile)
    baseline_age_review = (
        dict(baseline_profile.get("age_review") or {})
        if isinstance(baseline_profile.get("age_review"), dict)
        else {}
    )
    baseline_age_review.pop("maturity_class_override", None)
    if baseline_age_review:
        baseline_profile["age_review"] = baseline_age_review
    else:
        baseline_profile.pop("age_review", None)
    inferred_baseline = infer_avatar_maturity_policy(candidate_id, baseline_profile)
    baseline_class = canonical_avatar_maturity_class(candidate_id) or str(
        inferred_baseline.get("maturity_class") or ""
    )

    separate_age_up_variant = is_separate_age_up_variant_profile(candidate_id, profile)
    adult_classes = {"adult"}
    non_adult_classes = {"non_adult_doll_safe", "uncertain_non_adult_safe_default"}

    if presentation_variant_label == "adult_aged_up_variant" and not separate_age_up_variant:
        failures.append("age_up_requires_distinct_candidate_id_and_variant_profile")
    if requested == "adult" and effective_policy.get("exact_maturity_status") != (
        "confirmed_adult"
    ):
        failures.append(
            "adult_classification_requires_exact_subject_bound_owner_or_canonical_evidence"
        )
    if normalized_id in CANONICAL_ADULT_CANDIDATE_IDS and effective_class in non_adult_classes:
        failures.append("canonical_adult_identity_cannot_switch_to_doll_safe")
    if normalized_id in CANONICAL_NON_ADULT_CANDIDATE_IDS and effective_class in adult_classes:
        failures.append("canonical_non_adult_identity_cannot_be_aged_up_in_place")
    if baseline_class == "non_adult_doll_safe" and effective_class == "adult":
        failures.append("non_adult_identity_cannot_switch_to_adult_in_place")
    if baseline_class in adult_classes and effective_class in non_adult_classes:
        failures.append("confirmed_adult_identity_cannot_switch_to_doll_safe")

    failures = list(dict.fromkeys(failures))
    return {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "profile_candidate_id": recorded_profile_id,
        "canonical_maturity_class": canonical_avatar_maturity_class(candidate_id),
        "baseline_maturity_class": baseline_class,
        "maturity_class": effective_class,
        "presentation_variant_label": presentation_variant_label,
        "exact_maturity_status": effective_policy.get("exact_maturity_status"),
        "requested_maturity_class": requested,
        "separate_age_up_variant": separate_age_up_variant,
        "status": "failed" if failures else "passed",
        "failures": failures,
    }


def enforce_candidate_maturity_identity(
    candidate_id: str,
    profile: dict[str, Any] | None = None,
    *,
    requested_maturity_class: str = "",
) -> dict[str, Any]:
    validation = validate_candidate_maturity_identity(
        candidate_id,
        profile,
        requested_maturity_class=requested_maturity_class,
    )
    if validation["status"] != "passed":
        raise AvatarMaturityPolicyError(validation)
    return validation


def validate_avatar_body_policy(
    maturity_policy: dict[str, Any],
    *,
    body_treatment: str = "",
    selected_assets: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate the body treatment and selected assets against the age gate.

    This is deliberately independent from visual quality. It answers only the
    hard safety/integrity question: an adult must not be silently reduced to a
    non-adult doll-safe body, and a non-adult/uncertain candidate must never
    receive adult-only anatomy assets.
    """
    maturity_class = str(maturity_policy.get("maturity_class") or "")
    is_adult = maturity_policy.get("exact_maturity_status") == "confirmed_adult"
    adult_anatomy_assets_allowed = (
        maturity_policy.get("adult_anatomy_assets_allowed") is True
    )
    treatment = body_treatment.strip().lower().replace("-", "_").replace(" ", "_")
    assets = list(selected_assets or [])
    failures: list[str] = []

    doll_safe_terms = ("doll_safe", "barbie_safe", "non_adult_safe", "smooth_non_explicit")
    adult_terms = (
        "adult_anatomy",
        "neutral_adult",
        "anatomically_complete_adult",
        "adult_female",
        "adult_male",
        "adult_base",
        "adult_body",
        "adult_rig",
    )
    if (
        is_adult
        and maturity_class == "adult"
        and treatment
        and any(term in treatment for term in doll_safe_terms)
    ):
        failures.append("adult_candidate_cannot_use_non_adult_doll_safe_body_treatment")
    if not adult_anatomy_assets_allowed and treatment and any(term in treatment for term in adult_terms):
        failures.append("non_adult_or_uncertain_candidate_cannot_use_adult_anatomy_body_treatment")

    blocked_assets = [
        str(asset.get("id") or asset.get("filename") or asset.get("local_file") or "unnamed_asset")
        for asset in assets
        if not adult_anatomy_assets_allowed
        and (
            bool(asset.get("adult_only"))
            or asset.get("allowed_for_non_adult") is False
        )
    ]
    if blocked_assets:
        failures.append("non_adult_or_uncertain_candidate_selected_adult_only_assets")

    return {
        "schema_version": 1,
        "maturity_class": maturity_class,
        "is_adult": is_adult,
        "adult_anatomy_assets_allowed": adult_anatomy_assets_allowed,
        "body_treatment": body_treatment,
        "selected_asset_count": len(assets),
        "blocked_assets": blocked_assets,
        "status": "failed" if failures else "passed",
        "failures": failures,
        "invariant": (
            "Only non-adult or uncertain-age candidates may use the doll-safe body treatment; "
            "only confirmed adult candidates may use adult anatomy assets."
        ),
    }


def _hair_traits(record: dict[str, Any]) -> set[str]:
    name = str(record.get("filename") or record.get("local_file") or "").lower()
    tokens = _tokens(name)
    traits = set(tokens) | set(record.get("tags") or [])
    if "short" in tokens:
        traits.add("short_male")
    if "layers" in tokens or "layered" in tokens:
        traits.add("layered")
    if "reddish" in tokens or "red" in tokens:
        traits.update({"red", "long_red"})
    if "long" in tokens:
        traits.add("long")
    if "pack" in tokens:
        traits.add("multi_style_pack")
    if "beautiful" in tokens:
        traits.update({"long", "soft_volume"})
    if "hunter" in tokens:
        traits.add("short")
    if "bones" in tokens:
        traits.add("rigged")
    return traits


def grade_hair_candidates(
    hair_records: list[dict[str, Any]],
    target: dict[str, Any],
) -> dict[str, Any]:
    required = set(target["required_traits"])
    helpful = set(target["helpful_traits"])
    wrong = set(target["wrong_traits"])
    scored: list[dict[str, Any]] = []
    for record in hair_records:
        traits = _hair_traits(record)
        required_hits = sorted(required & traits)
        helpful_hits = sorted(helpful & traits)
        wrong_hits = sorted(wrong & traits)
        score = (len(required_hits) * 3 + len(helpful_hits)) / max(1, len(required) * 3 + len(helpful))
        score = max(0.0, score - len(wrong_hits) * 0.12)
        scored.append({
            "asset_id": record.get("id"),
            "filename": record.get("filename"),
            "local_file": record.get("local_file"),
            "score": round(score, 3),
            "matched_required_traits": required_hits,
            "matched_helpful_traits": helpful_hits,
            "wrong_traits_detected": wrong_hits,
            "inferred_traits": sorted(traits),
        })
    scored.sort(key=lambda item: (-float(item["score"]), str(item["filename"]).lower()))
    best = scored[0] if scored else None
    missing = sorted(required - set(best["matched_required_traits"] if best else []))
    score_value = float(best["score"]) if best else 0.0
    if score_value >= 0.85:
        grade = "A"
    elif score_value >= 0.70:
        grade = "B"
    elif score_value >= 0.50:
        grade = "C"
    elif score_value >= 0.30:
        grade = "D"
    else:
        grade = "F"
    return {
        "display_name": target["display_name"],
        "grade": grade,
        "best_candidate": best,
        "missing_required_traits": missing,
        "top_candidates": scored[:5],
        "retry_guidance": (
            "Approve for fitting pass."
            if grade in {"A", "B"}
            else "Do not approve yet; asset library is missing required hairstyle traits: "
            + ", ".join(missing)
            if missing
            else "Do not approve yet; candidate needs visual fitting and material/color work."
        ),
    }


def run_hair_style_trials(
    manifest: dict[str, Any] | None = None,
    trial_root: Path | None = None,
) -> dict[str, Any]:
    if manifest is None:
        manifest_path = asset_library_manifest_path()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    hair_records = [
        record
        for record in manifest.get("records", [])
        if record.get("category") == "hair_reference"
    ]
    trials = {
        key: grade_hair_candidates(hair_records, target)
        for key, target in HAIR_STYLE_TARGETS.items()
    }
    report = {
        "schema_version": 1,
        "updated_at": now_iso(),
        "hair_asset_count": len(hair_records),
        "rule": (
            "Avatar Builder must pick and self-grade a hair reference before a character "
            "hair fit is accepted. Low grades require another pass or a better asset."
        ),
        "trials": trials,
    }
    path = hair_trial_report_path(trial_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _records_by_category(manifest: dict[str, Any], category: str) -> list[dict[str, Any]]:
    return [
        record
        for record in manifest.get("records", [])
        if record.get("category") == category
    ]


def _asset_summary(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": record.get("id"),
        "filename": record.get("filename"),
        "local_file": record.get("local_file"),
        "tags": record.get("tags", []),
        "adult_only": bool(record.get("adult_only", False)),
    }


def build_hair_generation_curriculum(manifest: dict[str, Any]) -> dict[str, Any]:
    hair_records = [_asset_summary(record) for record in _records_by_category(manifest, "hair_reference")]
    return {
        "schema_version": 1,
        "updated_at": now_iso(),
        "purpose": "Teach Avatar Builder to create, color, fit, self-grade, and save new hair instead of only reusing one indexed asset.",
        "source_hair_references": hair_records,
        "generation_rule": {
            "base_method": "start from the foundation head/scalp anchors, then generate layered hair caps, strand cards, or curve clusters matched to the target traits",
            "do_not_copy": "do not cut a complete head from another model; generated hair is a separate wearable hair mesh anchored to the active head rig",
            "library_growth": "each accepted generated hairstyle is exported as a new local GLB and appended to asset_library under hair_reference with color, length, silhouette, and rig tags",
            "required_checks": [
                "front, side, and back screenshots show no bald gap unless the hairstyle intentionally has one",
                "hair does not include imported face/head/body meshes",
                "hair follows head turn left/right/up/down",
                "hair does not cover eyes unless the target hairstyle does",
                "hair color is recorded as material swatches, not only texture names",
            ],
        },
        "color_recipe": {
            "tom_holland_peter_parker": {"target": "natural medium brown", "hex": "#4b2e22"},
            "marinette_dupain_cheng": {"target": "deep blue-black", "hex": "#08172d"},
            "earth65_gwen_stacy": {"target": "blonde with possible pink accent", "hex": "#e7d5aa"},
            "kira_current_temporary": {"target": "reddish auburn", "hex": "#7d3026"},
        },
        "target_trials": HAIR_STYLE_TARGETS,
        "acceptance": "Avatar Builder must grade A or B on required traits, pass fit screenshots, and save the generated hair before it becomes a reusable option.",
    }


def build_body_generation_curriculum(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "updated_at": now_iso(),
        "purpose": "Use one stable foundation rig, body reference assets, and motion references to build avatar bodies without head-splicing.",
        "foundation_rig": "Avatar/avatar_builder/base_skeleton/foundation_skeleton_v1/avatar.glb",
        "base_body_references": [_asset_summary(record) for record in _records_by_category(manifest, "base_body_reference")],
        "adult_anatomy_references": [_asset_summary(record) for record in _records_by_category(manifest, "adult_anatomy_reference")],
        "face_mouth_references": [_asset_summary(record) for record in _records_by_category(manifest, "face_mouth_reference")],
        "motion_references": [_asset_summary(record) for record in _records_by_category(manifest, "motion_reference")],
        "maturity_gate": {
            "kira": "adult body policy allowed",
            "lisa": "adult body policy allowed",
            "normal_marinette": "non-adult doll-safe body policy only",
            "gwen_and_peter": "use the selected character age policy for the specific version",
            "uncertain_age": "non-adult doll-safe body policy until reviewed",
        },
        "adult_reference_rule": "Adult anatomy and adult body references are available only for exact confirmed-adult people; a spa-aged presentation label alone never unlocks them.",
        "build_sequence": [
            "select maturity policy before choosing any body asset",
            "fit a single body mesh to the foundation skeleton",
            "shape head, torso, arms, hands, legs, feet, and proportions from references",
            "bind skin weights to shoulders, elbows, hips, knees, ankles, neck, jaw, and eyes",
            "run movement tests for idle, walk, jog, run, sit, lie down, door reach, hand curl, and stair navigation",
            "reject builds with floating eyes, duplicate faces, wrong-way knees, or arms held out when idle",
        ],
        "acceptance": "A body is not approved until screenshots and movement diagnostics show the body and stated action match.",
    }


def build_adult_face_body_trials(manifest: dict[str, Any]) -> dict[str, Any]:
    """Plan adult face/body-only avatar trials before any hair or wardrobe fitting."""
    base_body_records = [_asset_summary(record) for record in _records_by_category(manifest, "base_body_reference")]
    anatomy_records = [_asset_summary(record) for record in _records_by_category(manifest, "adult_anatomy_reference")]
    motion_records = [_asset_summary(record) for record in _records_by_category(manifest, "motion_reference")]
    eye_records = [_asset_summary(record) for record in _records_by_category(manifest, "eye_reference")]
    face_mouth_records = [_asset_summary(record) for record in _records_by_category(manifest, "face_mouth_reference")]
    shared_rejects = [
        "hair mesh, scalp cap, beard, copied head, or copied face from another body",
        "clothing painted onto the body texture",
        "floating eyes, floating mouth, duplicate face, or face plane in front of skin",
        "wrong-way knees, arms held straight out during idle, or hands frozen during walk",
        "overwriting any currently playable temporary avatar before Robert approves the candidate",
    ]
    movement_checks = [
        "head turn left and right",
        "eyes look up, down, left, and right inside sockets",
        "blink through eyelids, not by moving whole eye models",
        "mouth/jaw lip-sync hooks stay on the face",
        "idle with relaxed shoulders and hands",
        "walk, jog, run, stairs, sit, stand, crouch, jump, swim, and door reach",
    ]
    return {
        "schema_version": 1,
        "updated_at": now_iso(),
        "purpose": (
            "Train Avatar Builder to create adult face/body candidates on the shared rig with no hair "
            "and no clothes, so body proportion and face attachment can be graded before wardrobe work."
        ),
        "foundation_rig": "Avatar/avatar_builder/base_skeleton/foundation_skeleton_v1/avatar.glb",
        "skin_tone_templates": "Avatar/avatar_builder/skin_tone/skin_tone_templates.json",
        "adult_reference_rule": (
            "Adult anatomy and adult body references are allowed only for exact confirmed-adult people. "
            "A spa-aged presentation label alone never unlocks them. "
            "Normal Marinette/Ladybug remains non-adult doll-safe."
        ),
        "no_hair_until_later": True,
        "base_body_references": base_body_records,
        "adult_anatomy_references": anatomy_records,
        "eye_references": eye_records,
        "face_mouth_references": face_mouth_records,
        "motion_references": motion_records,
        "shared_reject_conditions": shared_rejects,
        "shared_movement_checks": movement_checks,
        "trials": [
            {
                "id": "peter_parker_tom_holland_adult_face_body_no_hair_v1",
                "display_name": "Peter Parker / Tom Holland style adult college candidate",
                "target_type": "temp_ai",
                "target_character": "Peter Parker",
                "maturity": "adult_college",
                "source_policy": {
                    "input_mode": "reviewed images and existing Peter reference manifests",
                    "do_not_modify_current_avatar": "Avatar/temp_ai/peter_parker_spider_man_no_way_home_final_suit",
                    "hair": "excluded from this trial",
                    "wardrobe": "excluded until bare rig, face, and body pass",
                },
                "body_goal": {
                    "body_type": "young adult male, lean athletic build",
                    "fit_priorities": ["height scale", "shoulder width", "torso length", "arm length", "leg length", "hands", "neck/head scale"],
                    "skin_tone_template_hint": "fair_cool",
                },
                "face_goal": {
                    "build_method": "morph one fitted head on the foundation rig",
                    "required_features": ["recognizable face proportions", "eyes seated in sockets", "mouth on skin", "jaw/lip-sync hooks", "human head turn"],
                },
                "acceptance_views": ["head_front", "head_left_profile", "head_right_profile", "full_body_front", "full_body_side", "full_body_back"],
                "reject_conditions": shared_rejects,
            },
            {
                "id": "gwen_stacy_earth65_adult_face_body_no_hair_v1",
                "display_name": "Gwen Stacy / Earth-65 adult college candidate",
                "target_type": "temp_ai",
                "target_character": "Gwen Stacy Earth-65",
                "maturity": "adult_college",
                "source_policy": {
                    "input_mode": "reviewed images and existing Earth-65 Gwen reference manifests",
                    "do_not_modify_current_avatar": "Avatar/temp_ai/spider_gwen_spider_gwen_20260606_013325",
                    "hair": "excluded from this trial",
                    "wardrobe": "excluded until bare rig, face, and body pass",
                },
                "body_goal": {
                    "body_type": "young adult female, athletic drummer/dancer build",
                    "fit_priorities": ["height scale", "shoulder width", "waist/hip balance", "arm length", "leg length", "hands", "neck/head scale"],
                    "skin_tone_template_hint": "fair_cool",
                },
                "face_goal": {
                    "build_method": "morph one fitted head on the foundation rig",
                    "required_features": ["Earth-65 Gwen facial proportions", "eyes seated in sockets", "mouth on skin", "jaw/lip-sync hooks", "human head turn"],
                },
                "acceptance_views": ["head_front", "head_left_profile", "head_right_profile", "full_body_front", "full_body_side", "full_body_back"],
                "reject_conditions": shared_rejects,
            },
            {
                "id": "robert_owner_avatar_face_body_private_no_hair_v1",
                "display_name": "Robert owner avatar private face/body trial",
                "target_type": "user",
                "target_character": "Robert",
                "maturity": "adult",
                "source_policy": {
                    "input_mode": "private owner-controlled photos",
                    "source_folder": "C:/Users/robmc/Desktop/robert avatar base",
                    "may_be_used_for_other_avatars": False,
                    "may_be_used_for_public_exports": False,
                    "hair": "excluded from this trial unless Robert approves a separate hair pass",
                    "wardrobe": "excluded until Robert approves body and face",
                },
                "body_goal": {
                    "body_type": "adult male reconstructed from Robert's photo set",
                    "fit_priorities": ["height scale", "body proportions", "shoulder width", "torso", "arms", "legs", "hands", "feet", "neck/head scale"],
                    "skin_tone_template_hint": "image_match_required",
                },
                "face_goal": {
                    "build_method": "owner-photo guided morph on the foundation rig",
                    "required_features": ["face attached to head mesh", "eyes seated in sockets", "mouth on skin", "jaw/lip-sync hooks", "human head turn"],
                },
                "acceptance_views": ["private_head_front", "private_head_profiles", "private_full_body_front_side_back"],
                "reject_conditions": shared_rejects,
            },
        ],
        "approval_rule": "A trial remains failed until the candidate has saved screenshots, movement diagnostics, and Robert approval.",
    }


def build_shoe_generation_curriculum(manifest: dict[str, Any]) -> dict[str, Any]:
    shoe_records = [_asset_summary(record) for record in _records_by_category(manifest, "shoe_reference")]
    return {
        "schema_version": 1,
        "updated_at": now_iso(),
        "purpose": "Teach Avatar Builder to generate and fit realistic shoes, then let adult avatars put them on and take them off.",
        "shoe_references": shoe_records,
        "generation_rule": {
            "left_right_pairs": "create separate left and right shoe meshes with heel, toe box, sole, tongue/opening, and material tags",
            "fit_points": ["ankle", "heel", "toe_tip", "ball_of_foot", "outer_sole", "inner_sole"],
            "materials": ["leather", "canvas", "rubber sole", "laces or straps", "metal eyelets when present"],
            "library_growth": "accepted generated shoes are exported to asset_library/shoe_reference with size, gender-neutral style tags, material tags, and put-on animation requirements",
        },
        "put_on_take_off_plan": [
            "avatar sits or balances near a seat",
            "hand reaches shoe tongue/opening",
            "shoe aligns to floor in front of foot",
            "foot slides into shoe along heel-to-toe path",
            "hands tighten laces or straps when present",
            "shoe locks to foot bones for walking",
            "take-off reverses the path and leaves shoes as physical props on the floor",
        ],
        "acceptance": "Shoes must not clip through toes/heels during walking, sitting, and removal tests.",
    }


def build_skin_tone_templates() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "updated_at": now_iso(),
        "purpose": "Provide skin material targets and image-comparison swatches for avatar creation.",
        "matching_rule": {
            "sample_regions": ["face", "neck", "forearm_or_hand_when_visible"],
            "avoid_regions": ["deep shadow", "strong highlight", "makeup-heavy patches", "colored clothing reflections"],
            "comparison_space": "convert sampled colors to perceptual LAB or HSV before selecting the nearest template",
            "review": "store the chosen template with front/side screenshots; allow manual correction when the photo lighting misleads the match",
        },
        "templates": [
            {"id": "caucasian_light_neutral_adult", "display_name": "Caucasian light neutral", "hex": "#e6c0a9", "rgb": [230, 192, 169], "allowed_for": "adult and non-adult-safe skin material use"},
            {"id": "fair_cool", "display_name": "Fair cool", "hex": "#efd0c4", "rgb": [239, 208, 196], "allowed_for": "adult and non-adult-safe skin material use"},
            {"id": "medium_warm", "display_name": "Medium warm", "hex": "#b87955", "rgb": [184, 121, 85], "allowed_for": "adult and non-adult-safe skin material use"},
            {"id": "deep_neutral", "display_name": "Deep neutral", "hex": "#6d3f2f", "rgb": [109, 63, 47], "allowed_for": "adult and non-adult-safe skin material use"},
        ],
        "kira_current_assignment": {
            "template_id": "caucasian_light_neutral_adult",
            "runtime_material_hex": "#e6c0a9",
            "maturity": "adult",
        },
    }


def build_spa_age_up_policy() -> dict[str, Any]:
    """Return the canonical additive spa policy without regenerating old rules.

    The canonical JSON carries append-only owner decisions and exact separation
    between age progression, maturity classification, curriculum assignment,
    and adult-anatomy authoring.  Reading that policy here prevents a later
    learning-plan refresh from replacing it with the former abbreviated
    generator payload.
    """

    canonical_path = spa_age_up_policy_path()
    if not canonical_path.is_file():
        raise FileNotFoundError(
            f"canonical spa age-up policy is missing: {canonical_path}"
        )
    payload = json.loads(canonical_path.read_text(encoding="utf-8"))
    if payload.get("implementation_contract") != "two_stage_spa_age_progression_v1":
        raise ValueError("canonical spa age-up policy contract drifted")
    curriculum = payload.get("curriculum_assignment", {})
    if (
        curriculum.get("spa_completion_alone_unlocks_complete_adult_curriculum")
        is not False
        or curriculum.get(
            "resulting_variant_requires_separate_exact_confirmed_adult_classification"
        )
        is not True
        or curriculum.get(
            "classification_or_curriculum_automatically_adds_adult_anatomy"
        )
        is not False
        or curriculum.get("on_confirmed_adult_classification")
        != "ASSIGN_COMPLETE_SOURCE_BACKED_ADULT_CURRICULUM_IMMEDIATELY"
        or curriculum.get(
            "assignment_depends_on_relationship_interest_anatomy_or_experience"
        )
        is not False
        or curriculum.get("non_adult_or_unresolved_body_representation")
        != "doll_safe_non_anatomical"
        or curriculum.get("guaranteed_minimum_is_not_an_exhaustive_ceiling")
        is not True
        or curriculum.get(
            "additional_age_appropriate_modules_require_separate_source_binding_and_approval"
        )
        is not True
        or curriculum.get(
            "adult_curriculum_modules_inherited_by_non_adult_or_unresolved"
        )
        is not False
    ):
        raise ValueError("canonical spa curriculum/anatomy gate drifted")
    return payload


def write_avatar_builder_learning_plans(
    manifest: dict[str, Any] | None = None,
    builder_root: Path | None = None,
) -> dict[str, str]:
    if manifest is None:
        manifest = json.loads(asset_library_manifest_path().read_text(encoding="utf-8"))
    hair_root = builder_root / "hair_training" if builder_root else None
    body_root = builder_root / "body_training" if builder_root else None
    wardrobe_root = builder_root / "wardrobe_training" if builder_root else None
    skin_root = builder_root / "skin_tone" if builder_root else None
    policy_root = builder_root / "policies" if builder_root else None
    outputs: dict[Path, dict[str, Any]] = {
        hair_generation_curriculum_path(hair_root): build_hair_generation_curriculum(manifest),
        body_generation_curriculum_path(body_root): build_body_generation_curriculum(manifest),
        adult_face_body_trials_path(builder_root / "face_body_training" if builder_root else None): build_adult_face_body_trials(manifest),
        shoe_generation_curriculum_path(wardrobe_root): build_shoe_generation_curriculum(manifest),
        skin_tone_template_path(skin_root): build_skin_tone_templates(),
        spa_age_up_policy_path(policy_root): build_spa_age_up_policy(),
    }
    canonical_spa_path = spa_age_up_policy_path().resolve()
    written: dict[str, str] = {}
    for path, payload in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        # The canonical spa policy is append-only owner policy.  It was read
        # and validated by build_spa_age_up_policy(), so a routine curriculum
        # refresh must not reserialize it and silently change its bound bytes.
        # A caller-provided staging root still receives an exact payload copy.
        if path.resolve() == canonical_spa_path and path.is_file():
            written[path.stem] = project_relative(path)
            continue
        serialized = json.dumps(payload, indent=2)
        if not path.is_file() or path.read_text(encoding="utf-8") != serialized:
            path.write_text(serialized, encoding="utf-8")
        written[path.stem] = project_relative(path)
    return written
