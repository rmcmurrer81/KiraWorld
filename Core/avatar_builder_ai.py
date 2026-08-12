"""Lightweight Avatar Builder agent memory and correction loop."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from Core.avatar_asset_library import (
    CANONICAL_ADULT_CANDIDATE_IDS,
    NORMAL_MARINETTE_CANDIDATE_ID,
    validate_candidate_maturity_identity,
)
from Core.avatar_builder_correction_memory import (
    append_correction_event,
    derive_correction_directives,
    evaluate_age_progression_stage_one_eligibility,
    evaluate_age_progression_stage_two_gate,
    route_next_private_build,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AVATAR_TEMP_DIR = PROJECT_ROOT / "Avatar" / "temp_ai"
AVATAR_STATE_DIR = PROJECT_ROOT / "Avatar" / "state" / "temp_ai"
BUILDER_ROOT = PROJECT_ROOT / "Avatar" / "avatar_builder"
GLOBAL_MEMORY_PATH = BUILDER_ROOT / "builder_memory.json"
HAIR_TRAINING_ROOT = BUILDER_ROOT / "hair_training"
BODY_TRAINING_ROOT = BUILDER_ROOT / "body_training"

ADULT_CLASSES = {"adult"}
NON_ADULT_CLASSES = {"non_adult_doll_safe", "uncertain_non_adult_safe_default"}
CANONICAL_GWEN_ID = "spider_gwen_spider_gwen_20260606_013325"
CANONICAL_PETER_ID = "peter_parker_spider_man_no_way_home_final_suit"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _owner_confirmed_adult_classification_evidence(
    candidate_id: str,
    correction_text: str,
    *,
    recorded_at: str | None = None,
) -> dict[str, Any]:
    """Bind Robert's exact-person correction without using keyword guesses."""

    subject_id = candidate_id.strip()
    source_text = correction_text.strip()
    digest = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    return {
        "classification_id": f"robert_confirmed_adult_{digest[:20]}",
        "subject_id": subject_id,
        "maturity_status": "confirmed_adult",
        "authority": "Robert_explicit_owner_confirmation",
        "offline_confirmation_allowed": True,
        "network_lookup_required": False,
        "recorded_at_utc": recorded_at or now_iso(),
        "source_text_sha256": digest,
        "source_text": source_text,
    }


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default.copy() if isinstance(default, dict) else default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def project_relative(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def adjustment_path(candidate_id: str) -> Path:
    return AVATAR_TEMP_DIR / candidate_id / "avatar_builder_adjustments.json"


def load_adjustments(candidate_id: str) -> dict[str, Any]:
    path = adjustment_path(candidate_id)
    data = read_json(path, {})
    data.setdefault("schema_version", 1)
    data.setdefault("candidate_id", candidate_id)
    data.setdefault("builder", "avatar_builder")
    data.setdefault("activation_policy", "inactive until Robert opens builder chat, runs a builder pass, or enters the spa builder station")
    data.setdefault("updated_at", now_iso())
    data.setdefault("maturity_override", "")
    data.setdefault("preview_adjustments", {})
    data.setdefault("build_targets", [])
    data.setdefault("learning_notes", [])
    data.setdefault("conversation", [])
    data.setdefault("correction_memory_events", [])
    data.setdefault("next_private_build_route", {})
    data.setdefault("approval_status", "unreviewed")
    return data


def save_adjustments(candidate_id: str, data: dict[str, Any]) -> Path:
    data["candidate_id"] = candidate_id
    data["updated_at"] = now_iso()
    path = adjustment_path(candidate_id)
    write_json(path, data)
    return path


def load_global_memory() -> dict[str, Any]:
    data = read_json(GLOBAL_MEMORY_PATH, {})
    data.setdefault("schema_version", 1)
    data.setdefault("updated_at", now_iso())
    data.setdefault("builder_rules", {
        "reference_model_use": (
            "3D character/reference models are evidence only. The Avatar Builder must not copy "
            "a reference model mesh into an AI/avatar body. A copied reference body is a "
            "disqualified cheating draft. Build from the approved base body, then use reference "
            "models, pictures, and measurements to adjust proportions, hair, eyes, mouth, and clothing."
        ),
        "accessory_exception": (
            "Small props/accessories may be copied only when Robert explicitly asks for that exact "
            "item, and they must be stored as accessories, never as avatar body source."
        ),
    })
    data.setdefault("builder_roles", {
        "avatar_builder": {
            "activation": "only while building, reviewing, or correcting avatars; spa station inside 3D world; Avatar Builder Workspace outside 3D world",
            "scope": "bodies, heads, eyes, hair, rigging, movement, maturity policy, references, and wardrobe later",
        },
        "world_builder": {
            "activation": "only while building, reviewing, or correcting worlds; TARDIS station inside 3D world",
            "scope": "notebook worlds, homes, rooms, portals, maps, props, collisions, and performance budgets",
        },
    })
    data.setdefault("lessons", [])
    data.setdefault("activation_log", [])
    return data


def append_global_lesson(candidate_id: str, tags: list[str], lesson: str, source: str = "avatar_builder") -> None:
    memory = load_global_memory()
    memory["lessons"].append({
        "created_at": now_iso(),
        "candidate_id": candidate_id,
        "source": source,
        "tags": sorted(set(tags)),
        "lesson": lesson,
    })
    memory["updated_at"] = now_iso()
    write_json(GLOBAL_MEMORY_PATH, memory)


def log_activation(candidate_id: str, action: str) -> None:
    memory = load_global_memory()
    memory["activation_log"].append({
        "created_at": now_iso(),
        "builder": "avatar_builder",
        "candidate_id": candidate_id,
        "action": action,
    })
    memory["updated_at"] = now_iso()
    write_json(GLOBAL_MEMORY_PATH, memory)


def candidate_state(candidate_id: str) -> dict[str, Any]:
    return read_json(AVATAR_STATE_DIR / f"{candidate_id}.json", {})


def model_path_for_candidate(candidate_id: str) -> Path | None:
    state = candidate_state(candidate_id)
    url = str(state.get("model_url") or "")
    if not url.startswith("/"):
        fallback = PROJECT_ROOT / "Avatar" / "models" / "temp_ai" / candidate_id / "avatar.glb"
        return fallback if fallback.exists() else None
    target = (PROJECT_ROOT / url.lstrip("/")).resolve()
    try:
        target.relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        return None
    return target if target.exists() else None


def _read_glb_json(path: Path) -> dict[str, Any] | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if data[:4] != b"glTF":
        return None
    offset = 12
    while offset + 8 <= len(data):
        chunk_len = int.from_bytes(data[offset:offset + 4], "little")
        chunk_type = int.from_bytes(data[offset + 4:offset + 8], "little")
        offset += 8
        chunk = data[offset:offset + chunk_len]
        offset += chunk_len
        if chunk_type == 0x4E4F534A:
            try:
                return json.loads(chunk.decode("utf-8").rstrip("\x00 "))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return None
    return None


def inspect_candidate_model(candidate_id: str) -> dict[str, Any]:
    path = model_path_for_candidate(candidate_id)
    if not path:
        return {"model_path": "", "model_ready": False, "issues": ["no local GLB model linked"]}
    doc = _read_glb_json(path)
    if not doc:
        return {"model_path": project_relative(path), "model_ready": False, "issues": ["linked model is not a readable GLB"]}
    names: dict[str, list[str]] = {}
    for key in ("nodes", "meshes", "materials", "skins", "animations"):
        names[key] = [
            str(item.get("name") or "")
            for item in doc.get(key, []) or []
            if isinstance(item, dict) and item.get("name")
        ]
    all_names = " ".join(name.lower() for values in names.values() for name in values)
    head_names = [name for name in names["nodes"] if re.search(r"\bhead\b|mixamorig:head", name, re.I)]
    eye_names = [
        name
        for values in (names["nodes"], names["meshes"], names["materials"])
        for name in values
        if re.search(r"eye|iris|pupil|sclera|eyelid", name, re.I)
    ]
    hair_names = [
        name
        for values in (names["nodes"], names["meshes"], names["materials"])
        for name in values
        if re.search(r"hair|bang|pigtail|ponytail|scalp", name, re.I)
    ]
    generic_spheres = [
        name for name in names["meshes"] + names["nodes"]
        if re.fullmatch(r"Sphere(?:\.\d+)?", name)
    ]
    issues: list[str] = []
    if not head_names:
        issues.append("no recognizable head node")
    if not eye_names:
        issues.append("no named eye/iris/pupil meshes; landmark-driven eye construction is required")
    if "marinette" in candidate_id.lower() and "pigtail" not in all_names:
        issues.append("Marinette hair target needs low twin pigtails named/fitted")
    return {
        "model_path": project_relative(path),
        "model_ready": True,
        "node_count": len(doc.get("nodes", []) or []),
        "mesh_count": len(doc.get("meshes", []) or []),
        "material_count": len(doc.get("materials", []) or []),
        "skin_count": len(doc.get("skins", []) or []),
        "animation_count": len(doc.get("animations", []) or []),
        "head_names": head_names[:12],
        "eye_names": eye_names[:12],
        "hair_names": hair_names[:16],
        "generic_sphere_candidates": generic_spheres[:12],
        "issues": issues,
    }


def hair_reference_assets() -> list[dict[str, Any]]:
    manifest_path = BUILDER_ROOT / "asset_library" / "manifest.json"
    manifest = read_json(manifest_path, {})
    return [
        {
            "id": record.get("id"),
            "filename": record.get("filename"),
            "local_file": record.get("local_file"),
            "tags": record.get("tags", []),
            "adult_only": bool(record.get("adult_only", False)),
        }
        for record in manifest.get("records", []) or []
        if isinstance(record, dict) and record.get("category") == "hair_reference"
    ]


def eye_reference_assets() -> list[dict[str, Any]]:
    manifest_path = BUILDER_ROOT / "asset_library" / "manifest.json"
    manifest = read_json(manifest_path, {})
    return [
        {
            "id": record.get("id"),
            "filename": record.get("filename"),
            "local_file": record.get("local_file"),
            "tags": record.get("tags", []),
            "adult_only": bool(record.get("adult_only", False)),
        }
        for record in manifest.get("records", []) or []
        if isinstance(record, dict) and record.get("category") == "eye_reference"
    ]


def write_hair_rebuild_plan(candidate_id: str, target: str, failure_reason: str) -> Path:
    plan = {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "updated_at": now_iso(),
        "target": target,
        "failure_reason": failure_reason,
        "source_hair_models": hair_reference_assets(),
        "required_method": [
            "do not copy/import a reference model mesh as the candidate's body or final hair",
            "do not accept current hair if the silhouette is wrong",
            "study the supplied hair model GLBs as construction references",
            "generate or fit hair as a separate wearable mesh, not as part of the body mesh",
            "anchor hair to scalp/head bones",
            "save named parts for cap, bangs, side locks, pigtails or ponytails, ties, and collision bounds",
            "review front, side, and back screenshots before approval",
        ],
        "marinette_required_traits": [
            "deep blue-black color",
            "side-swept bangs",
            "rounded youthful silhouette",
            "low twin pigtails",
            "red pigtail ties when in civilian Marinette look",
            "hair should frame the face without hiding the eyes",
        ],
        "reject_if": [
            "hair silhouette does not match the reference pictures",
            "hair is generic or copied from the wrong character",
            "hair floats away from the scalp",
            "hair clips through the face or eyes",
            "hair is not saved as named reusable parts",
        ],
    }
    path = HAIR_TRAINING_ROOT / f"{candidate_id}_hair_rebuild_plan.json"
    write_json(path, plan)
    return path


def write_eye_rebuild_plan(candidate_id: str, target_eye_color: str, failure_reason: str) -> Path:
    plan = {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "updated_at": now_iso(),
        "target_eye_color": target_eye_color,
        "target_eye_color_status": "requested_draft_pending_avatar_owner_review",
        "failure_reason": failure_reason,
        "source_eye_models": eye_reference_assets(),
        "required_method": [
            "use the Avatar Builder eye-reference GLBs as construction references",
            "place eyes from head landmarks and eye_socket bones, not by visual guessing",
            "keep separate named meshes for sclera, iris, pupil, eyelids, and highlights",
            "change iris color through material/texture settings while preserving realistic sclera, pupil, cornea, and highlight proportions",
            "fit both eyes symmetrically inside the head sockets before hair, wardrobe, or expression approval",
            "save front and three-quarter close-up screenshots for review",
        ],
        "reject_if": [
            "eyes float on the forehead, cheeks, side of face, or outside the head",
            "eyes are flat colored rectangles or cyan placeholders",
            "iris color is changed by tinting the whole eye white/sclera",
            "left and right eyes use different scale, height, or depth without an expression reason",
            "eye parts are unnamed or merged into a generic head mesh so socket checks cannot run",
        ],
    }
    path = BUILDER_ROOT / "eye_training" / f"{candidate_id}_eye_rebuild_plan.json"
    write_json(path, plan)
    return path


def write_adult_body_fit_plan(
    candidate_id: str,
    failure_reason: str,
    target_height: dict[str, Any] | None = None,
) -> Path:
    plan = {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "updated_at": now_iso(),
        "failure_reason": failure_reason,
        "target_measurements": {
            "height": target_height or {},
        },
        "diagnosis": [
            "A maturity/adult flag only controls which reference sets are allowed; it does not reshape the mesh by itself.",
            "The current failed Gwen proof still reads as a smooth generic base because it used small band deltas instead of a true landmark/lattice/sculpt body fit.",
            "Adult candidates must not pass review while using non-adult doll-safe body treatment or while only claiming adult policy in metadata.",
        ],
        "required_pipeline": [
            "Start from the approved adult base body for the candidate's sex/body class; do not copy a reference character mesh.",
            "Scale the base body to Robert-provided height before likeness fitting when a height is known.",
            "Select approved front, side, back, and three-quarter references and mark weak/inferred areas honestly.",
            "Measure target landmarks: top of head, chin, eye line, jaw width, shoulder width, chest/bust band, waist, hips, knees, ankles, arms, hands, and feet.",
            "Fit the base body with lattice/sculpt/proportional-edit deltas driven by those landmarks, not by a few hard-coded z bands.",
            "For adult candidates only, preserve neutral adult anatomy/proportions in a non-sexual modeling context; do not apply non-adult doll-safe simplification.",
            "Write a body-fit report with actual measurement deltas, before/after silhouettes, and rejection reasons.",
        ],
        "acceptance_checks": [
            "front/side/back renders match the target silhouette closely enough for Robert review",
            "adult body fitting report shows real landmark measurements and mesh deltas",
            "eyes, mouth, hair, and clothing remain separate systems and are not baked into a copied reference body",
            "non-adult doll-safe preview rules are off for adult candidates and on for non-adult candidates",
            "builder status stays failed until a real GLB and visual proof pass the body-fit gate",
        ],
        "reject_if": [
            "the body looks like the same smooth generic base with only metadata changed",
            "the proof says adult but non-adult doll-safe treatment is still applied",
            "the body is copied from a model instead of fitted from the approved base",
            "the body report has only JSON intent and no generated GLB/rendered proof",
            "the body has strange bumps caused by uncontrolled deformation",
        ],
    }
    path = BODY_TRAINING_ROOT / "body_fit_plans" / f"{candidate_id}_adult_body_fit_plan.json"
    write_json(path, plan)
    return path


def gwen_reference_paths() -> dict[str, str]:
    return {
        "rigged_spandex_costume_model": "Assets/third_party/intake/3d_models_kira_world/characters/spider_gwen/spider-_gwen.glb",
        "unmasked_head_hair_model": "Assets/third_party/intake/3d_models_kira_world/characters/spider_gwen/spider_gwen_low_poly_unmasked_reference.glb",
        "runtime_temp_model": "Avatar/models/temp_ai/spider_gwen_spider_gwen_20260606_013325/avatar.glb",
        "female_body_library": "Avatar/library/female/body",
        "female_proportions_library": "Avatar/library/female/proportions",
        "female_face_structure_library": "Avatar/library/female/face_structure",
        "shared_eye_library": "Avatar/library/shared_features/eyes",
        "shared_hair_library": "Avatar/library/shared_features/hair",
        "adult_anatomy_reference_library": "Avatar/avatar_builder/asset_library/adult_anatomy_reference",
        "base_body_reference_library": "Avatar/avatar_builder/asset_library/base_body_reference",
    }


def write_gwen_spandex_wardrobe_plan(candidate_id: str) -> Path:
    refs = gwen_reference_paths()
    plan = {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "updated_at": now_iso(),
        "purpose": "Use Gwen's spandex Ghost-Spider suit as a body-silhouette reference and convert the suit into removable clothing, not a baked-in body.",
        "source_models": refs,
        "chat_reference_batch": {
            "source": "Robert uploaded newer Gwen reference images in chat on 2026-07-12.",
            "available_to_codex_as_visual_context": True,
            "notes": [
                "unmasked stylized Gwen face with blonde side-part hair and blue eyes",
                "full spandex suit shows slim athletic adult build and shoulder/torso/hip proportions",
                "front, three-quarter, side, hoodie/civilian, and drummer references help face, hair, posture, and wardrobe",
                "costume should inform clothing fit and body silhouette, not remain fused to the base body",
            ],
        },
        "base_body_rule": [
            "build or fit a neutral adult female base body first",
            "do not copy the unmasked model or spandex model into the candidate base body",
            "use the rigged spandex suit only as a tight outer-clothing and body-proportion reference",
            "use adult anatomy references only for the adult Gwen variant and only in neutral modeling context",
            "do not bake web pattern, hood, gloves, mask, shoes, or suit colors into the base body mesh",
        ],
        "removable_clothing_layers": [
            {
                "id": "ghost_spider_spandex_suit",
                "type": "full_body_stretch_suit",
                "parts": ["torso", "legs", "sleeves", "neck seal"],
                "fit": "skinned close to base body with small cloth offset and body collision shrinkwrap",
            },
            {
                "id": "ghost_spider_hood",
                "type": "hood_layer",
                "parts": ["hood shell", "inner pink web lining", "mask attachment points"],
                "fit": "head/neck anchored; removable without deleting hair or head mesh",
            },
            {
                "id": "ghost_spider_gloves",
                "type": "gloves",
                "parts": ["left glove", "right glove", "web pattern material"],
                "fit": "hand/finger skinned clothing, not hand mesh replacement",
            },
            {
                "id": "ghost_spider_shoes",
                "type": "shoes",
                "parts": ["left shoe", "right shoe", "sole", "toe cap"],
                "fit": "foot bone attachments; removable like normal shoes",
            },
        ],
        "acceptance_checks": [
            "base body remains visible and neutral when costume layers are hidden",
            "turning costume off does not remove eyes, face, hair, hands, feet, or body",
            "costume follows pose/animation without clipping through shoulders, hips, elbows, or knees",
            "hood can be off while hair remains visible",
            "eyes use named realistic sclera, iris, pupil, cornea/highlight, and eyelids",
        ],
    }
    path = BUILDER_ROOT / "wardrobe_training" / f"{candidate_id}_spandex_removable_clothing_plan.json"
    write_json(path, plan)
    return path


def redo_job_path(candidate_id: str) -> Path:
    return BUILDER_ROOT / "redo_jobs" / f"{candidate_id}_redo_job.json"


def reference_summary(candidate_id: str) -> dict[str, Any]:
    avatar_root = AVATAR_TEMP_DIR / candidate_id
    pipeline = read_json(avatar_root / "avatar_pipeline_status.json", {})
    references_root = avatar_root / "references"
    image_suffixes = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".avif"}
    on_disk = 0
    if references_root.exists():
        on_disk = sum(
            1
            for item in references_root.rglob("*")
            if item.is_file() and item.suffix.lower() in image_suffixes
        )
    return {
        "references_folder": project_relative(references_root),
        "pipeline_reference_count": int(pipeline.get("reference_count") or 0),
        "desktop_reference_count": int(pipeline.get("desktop_reference_count") or 0),
        "on_disk_reference_count": on_disk,
        "pipeline_status": str(pipeline.get("status") or "not prepared"),
    }


def create_avatar_redo_job(
    candidate_id: str,
    adult_test_candidate_id: str = "",
    reason: str = "Robert rejected the current preview and requested a redo.",
) -> dict[str, Any]:
    data = load_adjustments(candidate_id)
    candidate_key = candidate_id.strip().lower()
    inspection = inspect_candidate_model(candidate_id)
    adult_test = {}
    hair_plan = ""
    log_activation(candidate_id, "create_redo_job")

    if candidate_key == NORMAL_MARINETTE_CANDIDATE_ID:
        data["maturity_override"] = "non_adult_doll_safe"
        data["maturity_reason"] = "Normal Marinette/Ladybug remains non-adult and must use a smooth doll-safe non-explicit body."
        data.setdefault("preview_adjustments", {})["non_adult_review_garment"] = False
        hair_path = write_hair_rebuild_plan(
            candidate_id,
            "Marinette deep blue-black low twin pigtails, side-swept bangs, and close face-framing silhouette",
            "Robert rejected the current Marinette hair, head shape, and body shape as nowhere close.",
        )
        hair_plan = project_relative(hair_path)
        _add_target(data, "redo", "Reject the current Marinette preview as failed; rebuild head, body, eyes, and hair against references.", "Robert F-grade correction")
        _add_target(data, "body", "Use a smooth non-adult doll-safe body with no adult anatomy assets and no blue-box overlay.", "Robert F-grade correction")
        _add_target(data, "head", "Rebuild Marinette head shape from references; do not keep the current head silhouette if it fails likeness checks.", "Robert F-grade correction")
        _add_target(data, "hair", f"Rebuild Marinette hair from supplied hair models and references; plan: {hair_plan}.", "Robert F-grade correction")
        _add_target(data, "eyes", "Create named eye, iris, pupil, eyelid, and socket anchors so eyes cannot float outside the face.", "Robert F-grade correction")

    if adult_test_candidate_id:
        adult_data = load_adjustments(adult_test_candidate_id)
        adult_inspection = inspect_candidate_model(adult_test_candidate_id)
        adult_test = {
            "candidate_id": adult_test_candidate_id,
            "adjustments_path": project_relative(adjustment_path(adult_test_candidate_id)),
            "maturity_override": adult_data.get("maturity_override") or "",
            "test_role": adult_data.get("test_role") or "",
            "reference_summary": reference_summary(adult_test_candidate_id),
            "inspection": adult_inspection,
            "purpose": "adult reference/body-shape comparison test kept separate from non-adult Marinette policy",
        }

    job = {
        "schema_version": 1,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "status": "queued_redo_not_completed",
        "candidate_id": candidate_id,
        "reason": reason,
        "current_model_is_approved": False,
        "current_model": inspection,
        "reference_summary": reference_summary(candidate_id),
        "hair_rebuild_plan": hair_plan,
        "paired_adult_test": adult_test,
        "rebuild_rules": [
            "reference models are evidence only; copying a reference GLB as the candidate body is disqualifying",
            "treat the current preview as a failed draft, not as the body to polish",
            "compare front, side, and back views against approved references before approval",
            "save generated hair as a separate wearable mesh anchored to scalp/head bones",
            "save named head, eye socket, eye, iris, pupil, eyelid, hair, hand, and foot parts",
            "reject any body where eyes float outside sockets or hair/head/body silhouette is not close",
            "do not mix adult anatomy assets into non-adult or uncertain-age avatars",
        ],
        "required_outputs": [
            "new avatar.glb or staged GLB candidate",
            "front, side, back, and head close-up screenshots",
            "updated avatar_builder_adjustments.json with passed/failed checks",
            "reference comparison notes naming what still does not match",
        ],
    }
    path = redo_job_path(candidate_id)
    write_json(path, job)

    data["approval_status"] = "failed_redo_required"
    data["redo_job_path"] = project_relative(path)
    data["redo_requested_at"] = now_iso()
    data["paired_adult_test_candidate"] = adult_test_candidate_id
    _note(data, reason, ["redo", "robert_f_grade"])
    saved_path = save_adjustments(candidate_id, data)
    append_global_lesson(
        candidate_id,
        ["avatar_builder", "redo", "quality_gate"],
        "A preview Robert grades F must be marked failed and rebuilt from references; do not quietly approve or polish the failed body.",
        source="Robert correction",
    )
    return {
        "ok": True,
        "candidate_id": candidate_id,
        "redo_job_path": project_relative(path),
        "adjustments_path": project_relative(saved_path),
        "paired_adult_test_candidate": adult_test_candidate_id,
        "job": job,
    }


def _add_target(data: dict[str, Any], area: str, instruction: str, source: str) -> None:
    targets = data.setdefault("build_targets", [])
    normalized = instruction.strip()
    if not normalized:
        return
    for item in targets:
        if item.get("area") == area and item.get("instruction") == normalized:
            item["updated_at"] = now_iso()
            return
    targets.append({
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "area": area,
        "source": source,
        "instruction": normalized,
        "status": "queued_for_builder_review",
    })


def _note(data: dict[str, Any], text: str, tags: list[str]) -> None:
    notes = data.setdefault("learning_notes", [])
    notes.append({
        "created_at": now_iso(),
        "tags": sorted(set(tags)),
        "text": text,
    })


def _maturity_from_message(message: str) -> tuple[str, str] | None:
    lowered = message.lower()
    policy_only_non_adult_rule = bool(
        re.search(
            r"\bonly\s+(?:the\s+)?non[- ]adults?\b.{0,100}\b(?:barbie|doll[- ]?safe|safe bod(?:y|ies))\b",
            lowered,
        )
        or re.search(
            r"\b(?:barbie|doll[- ]?safe)\b.{0,100}\bonly\s+(?:for\s+)?(?:the\s+)?non[- ]adults?\b",
            lowered,
        )
    )
    negated_non_adult_hit = any(term in lowered for term in (
        "do not use non adult",
        "do not use non-adult",
        "don't use non adult",
        "don't use non-adult",
        "must not use non adult",
        "must not use non-adult",
        "not use non adult",
        "not use non-adult",
        "not the non adult",
        "not the non-adult",
        "not a non adult",
        "not a non-adult",
        "no non adult",
        "no non-adult",
        "never use non adult",
        "never use non-adult",
        "without non adult",
        "without non-adult",
        "reject non adult",
        "reject non-adult",
        "rejected non adult",
        "rejected non-adult",
        "failed non adult",
        "failed non-adult",
    ))
    non_adult_hit = any(term in lowered for term in (
        "non adult", "non-adult", "not adult", "not an adult", "isn't an adult",
        "is not an adult", "minor", "child", "kid", "teen",
        "teenager", "student body", "doll safe", "doll-safe",
    ))
    explicit_subject_adult_hit = bool(
        re.search(
            r"\b(?:this\s+(?:(?:requested|current|fictional)\s+){0,2}(?:version|person|candidate|avatar|body)|"
            r"the\s+current\s+version|current\s+version|requested\s+version|"
            r"she|he|they|gwen|peter|kira|lisa|robert)\s+"
            r"(?:is|are)\s+(?:an?\s+)?adult\b",
            lowered,
        )
        or re.search(
            r"\b(?:classify|mark|record|set)\s+(?:this|the\s+(?:person|candidate|avatar|version)|"
            r"her|him|them)\b.{0,45}\b(?:as\s+)?adult\b",
            lowered,
        )
        or re.search(
            r"\b(?:i\s+confirm|trust\s+my\s+owner\s+correction)\b.{0,100}"
            r"\b(?:this|the\s+requested)\b.{0,35}\b(?:is|as)\s+(?:an?\s+)?adult\b",
            lowered,
        )
    )
    policy_only_adult_rule = bool(
        re.search(
            r"\badult(?:\s+body)?\s+(?:policy|test|document|reference|folder|rule|gate)\b",
            lowered,
        )
        or "not a person classification" in lowered
        or "not person classification" in lowered
    )
    negated_non_adult_regex = bool(
        re.search(r"\bnon[- ]adult\b.{0,40}\b(?:not allowed|failed|rejected|unusable|wrong)\b", lowered)
        or re.search(
            r"\b(?:do not|don't|must not|should not|cannot|can't|never)\b.{0,70}"
            r"\b(?:use|receive|apply|force|forced|give|given|assign|assigned)\b.{0,50}\bnon[- ]adult\b",
            lowered,
        )
    )
    negated_adult_hit = bool(
        re.search(r"\b(?:is|are|this is|she is|he is)\s+not\s+(?:an?\s+)?adult\b", lowered)
        or re.search(
            r"\b(?:do not|don't|must not|should not|cannot|can't|never)\b.{0,70}"
            r"\b(?:use|receive|apply|give|given|assign|assigned)\b.{0,50}"
            r"\b(?<!non-)(?<!non )adult\b",
            lowered,
        )
    )
    age_up_hit = bool(
        re.search(r"\b(?:age[ -]?up|aged[ -]?up|spa age|age progression)\b", lowered)
    )
    age_up_negated = bool(
        re.search(
            r"\b(?:do not|don't|must not|should not|cannot|can't|never|no)\b"
            r".{0,55}\b(?:age[ -]?up|aged[ -]?up|spa age|age progression)\b",
            lowered,
        )
    )
    explicit_age_up_request = age_up_hit and not age_up_negated and bool(
        re.search(
            r"(?:^|[.!?]\s*)(?:please\s+)?(?:age[ -]?up|start\s+(?:the\s+)?age progression|"
            r"create\s+(?:a\s+)?(?:separate\s+)?aged[ -]?up)",
            lowered,
        )
        or re.search(
            r"\b(?:i|they|she|he|the resident|this person|marinette|ladybug|peter|gwen|kira|lisa|robert)\s+"
            r"(?:want|wants|wanted|choose|chooses|chose|request|requests|requested)\b.{0,60}"
            r"\b(?:age[ -]?up|age progression|spa)\b",
            lowered,
        )
        or re.search(
            r"\b(?:go|goes|went)\s+to\s+(?:the\s+)?spa\b.{0,60}\bage[ -]?up\b",
            lowered,
        )
    )
    explicit_later_adult_version_hit = bool(
        re.search(r"\b(?:no[, ]+)?(?:this|the current|current|requested) version is (?:an )?adult\b", lowered)
        or re.search(r"\b(?:use|choose|build) (?:the )?(?:adult|adult-era|post-college|post-graduation) version\b", lowered)
        or (
            any(
                term in lowered
                for term in ("after graduation", "post-college", "adult-era", "adult era")
            )
            and explicit_subject_adult_hit
        )
    )
    if explicit_age_up_request:
        return (
            "adult_aged_up_variant",
            "Robert requested a separate spa age-progression presentation/build variant; this label is not confirmed adulthood.",
        )
    if policy_only_non_adult_rule:
        # This is a global policy statement, not an instruction to change the
        # selected candidate's age. The anatomy-policy path records it below.
        return None
    if explicit_later_adult_version_hit and not negated_adult_hit:
        return "adult", "Robert explicitly selected this later adult continuity/version."
    if non_adult_hit and not (negated_non_adult_hit or negated_non_adult_regex):
        return "non_adult_doll_safe", "Robert corrected this avatar to non-adult-safe."
    if policy_only_adult_rule and not explicit_subject_adult_hit:
        return None
    if explicit_subject_adult_hit and not negated_adult_hit:
        return "adult", "Robert corrected this avatar to adult."
    return None


def _requests_age_progression_stage_two_body(message: str) -> bool:
    """Recognize adult-body/anatomy requests that must not bypass spa Stage 2."""

    lowered = message.lower()
    return bool(
        re.search(r"\b(?:adult\s+)?anatom(?:y|ical)\b", lowered)
        or re.search(
            r"\b(?:use|give|build|make|add|author|fit|switch\s+to)\b.{0,50}"
            r"\b(?:full\s+)?adult(?:\s+(?:female|male))?\s+body\b",
            lowered,
        )
        or re.search(
            r"\badult(?:\s+(?:female|male))?\s+body\b.{0,50}"
            r"\b(?:use|build|fit|revision|variant|shape|base)\b",
            lowered,
        )
    )


def _requested_eye_color(message: str) -> str:
    lowered = message.lower()
    color_patterns = [
        ("blue-gray", ("blue gray", "blue-gray", "grey blue", "gray blue", "blue grey")),
        ("brown", ("brown eyes", "brown iris", "brown irises", "make the eyes brown")),
        ("blue", ("blue eyes", "blue iris", "blue irises", "make the eyes blue")),
        ("green", ("green eyes", "green iris", "green irises", "make the eyes green")),
        ("hazel", ("hazel eyes", "hazel iris", "hazel irises")),
        ("gray", ("gray eyes", "grey eyes", "gray iris", "grey iris")),
    ]
    for color, phrases in color_patterns:
        if any(phrase in lowered for phrase in phrases):
            return color
    explicit = re.search(r"\b(?:give|make|set|change)\b.{0,40}\b(?:eyes?|iris|irises)\b.{0,20}\b(?:to|as)\s+([a-z -]{3,20})", lowered)
    if explicit:
        return explicit.group(1).strip(" .,!?:;")
    return ""


def _extract_height_measurement(message: str) -> dict[str, Any] | None:
    lowered = message.lower()
    patterns = [
        re.search(r"\b([4-7])\s*(?:feet|foot|ft|')\s*(?:and\s*)?(\d{1,2})?\s*(?:inches|inch|in|\")?\b", lowered),
        re.search(r"\b([4-7])\s*-\s*(\d{1,2})\b", lowered),
    ]
    match = next((item for item in patterns if item), None)
    if match:
        feet = int(match.group(1))
        inches = int(match.group(2) or 0)
        if 0 <= inches < 12:
            total_inches = feet * 12 + inches
            return {
                "source": "Robert chat",
                "raw": match.group(0),
                "feet": feet,
                "inches": inches,
                "total_inches": total_inches,
                "height_m": round(total_inches * 0.0254, 3),
                "height_cm": round(total_inches * 2.54, 1),
            }

    cm_match = re.search(r"\b(1[2-9]\d|20\d|21\d)\s*(?:cm|centimeters|centimetres)\b", lowered)
    if cm_match:
        cm = float(cm_match.group(1))
        total_inches = cm / 2.54
        return {
            "source": "Robert chat",
            "raw": cm_match.group(0),
            "feet": int(total_inches // 12),
            "inches": round(total_inches % 12, 1),
            "total_inches": round(total_inches, 1),
            "height_m": round(cm / 100.0, 3),
            "height_cm": round(cm, 1),
        }

    meters_match = re.search(r"\b(1\.\d{2}|2\.\d{2})\s*(?:m|meter|meters|metre|metres)\b", lowered)
    if meters_match:
        meters = float(meters_match.group(1))
        total_inches = meters / 0.0254
        return {
            "source": "Robert chat",
            "raw": meters_match.group(0),
            "feet": int(total_inches // 12),
            "inches": round(total_inches % 12, 1),
            "total_inches": round(total_inches, 1),
            "height_m": round(meters, 3),
            "height_cm": round(meters * 100.0, 1),
        }
    return None


def _research_request_from_message(message: str) -> str:
    lowered = message.lower()
    if not any(term in lowered for term in ("go online", "search online", "look online", "research online", "search the web", "web search")):
        return ""
    cleaned = re.sub(r"\b(?:can you|please|avatar builder|go online|search online|look online|research online|search the web|web search|for|about)\b", " ", message, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,!?:;")
    return cleaned or message.strip()


def _record_design_conversation(data: dict[str, Any], message: str, facts: dict[str, Any], intents: list[str]) -> None:
    if len(message.strip()) < 12 and not facts:
        return
    durable_design_intents = {
        "body_shape",
        "head_shape_or_size",
        "hair",
        "detachable_hair",
        "hair_fullness",
        "hairline_fit",
        "skin_tone",
        "anatomy_policy",
        "online_learning",
        "eyes",
        "eye_socket_fit",
        "face_likeness",
        "continuity_timepoint",
        "age_progression_stage_1",
    }
    if not facts and not durable_design_intents.intersection(intents):
        return
    data.setdefault("design_conversation", []).append({
        "created_at": now_iso(),
        "speaker": "Robert",
        "message": message.strip(),
        "extracted_facts": facts,
        "understood_intents": sorted(set(intents)),
    })


def _maturity_validation_profile(
    candidate_id: str,
    profile: dict[str, Any] | None,
    adjustments: dict[str, Any],
    requested_maturity: tuple[str, str] | None,
    requested_classification_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    effective = dict(profile or {})
    effective.setdefault("candidate_id", candidate_id)
    age_review = (
        dict(effective.get("age_review") or {})
        if isinstance(effective.get("age_review"), dict)
        else {}
    )
    persisted = str(adjustments.get("maturity_override") or "").strip()
    if persisted:
        age_review["maturity_class_override"] = persisted
        age_review["reason"] = adjustments.get("maturity_reason") or "Persisted Avatar Builder policy."
    persisted_classification = adjustments.get(
        "confirmed_adult_classification_evidence"
    )
    if isinstance(persisted_classification, dict):
        age_review["confirmed_adult_classification_evidence"] = dict(
            persisted_classification
        )
    stage_one_evidence = adjustments.get("age_progression_stage_one_evidence")
    if isinstance(stage_one_evidence, dict):
        stage_one_classification = stage_one_evidence.get(
            "confirmed_adult_classification_evidence"
        )
        if isinstance(stage_one_classification, dict):
            age_review["confirmed_adult_classification_evidence"] = dict(
                stage_one_classification
            )
        if stage_one_evidence.get("resident_adult_anatomy_choice_recorded") is True:
            age_review["resident_adult_anatomy_choice_recorded"] = True
    if adjustments.get("age_progression_presentation_label") == (
        "adult_aged_up_variant"
    ):
        age_review["age_progression_presentation_label"] = (
            "adult_aged_up_variant"
        )
    if isinstance(adjustments.get("age_progression_contract"), dict):
        age_review["age_progression_contract"] = dict(
            adjustments["age_progression_contract"]
        )
    if requested_maturity:
        age_review["maturity_class_override"] = requested_maturity[0]
        age_review["reason"] = requested_maturity[1]
    if isinstance(requested_classification_evidence, dict):
        age_review["confirmed_adult_classification_evidence"] = dict(
            requested_classification_evidence
        )
    if age_review:
        effective["age_review"] = age_review
    return effective


def _apply_message_adjustments(
    candidate_id: str,
    message: str,
    data: dict[str, Any],
    requested_classification_evidence: dict[str, Any] | None = None,
) -> list[str]:
    lowered = message.lower()
    previous_maturity = str(data.get("maturity_override") or "").strip()
    changes: list[str] = []
    preview = data.setdefault("preview_adjustments", {})
    understood_intents: list[str] = []
    extracted_facts: dict[str, Any] = {}

    maturity = _maturity_from_message(message)
    stage_two_gate: dict[str, Any] = {}
    requests_adult_anatomy = _requests_age_progression_stage_two_body(message)
    has_age_progression_provenance = (
        previous_maturity == "adult_aged_up_variant"
        or data.get("age_progression_presentation_label")
        == "adult_aged_up_variant"
        or (
            isinstance(data.get("age_progression_contract"), dict)
            and data["age_progression_contract"].get("contract")
            == "two_stage_spa_age_progression_v1"
        )
    )
    if (
        has_age_progression_provenance
        and requests_adult_anatomy
    ):
        stage_two_gate = evaluate_age_progression_stage_two_gate(
            {"age_progression": data.get("age_progression_contract") or {}},
            data.get("age_progression_stage_one_evidence")
            if isinstance(data.get("age_progression_stage_one_evidence"), dict)
            else {},
        )
        if stage_two_gate.get("status") == "passed":
            maturity = (
                "adult_aged_up_variant",
                "Exact Stage 1 age-progression evidence passed; Robert requested the separate Stage 2 anatomy build.",
            )
    if maturity:
        maturity_class, reason = maturity
        preserve_age_progression_label = (
            has_age_progression_provenance and maturity_class == "adult"
        )
        data["maturity_override"] = (
            "adult_aged_up_variant"
            if preserve_age_progression_label
            else maturity_class
        )
        data["maturity_reason"] = reason
        data["maturity_corrected_at"] = now_iso()
        if maturity_class == "adult" and isinstance(
            requested_classification_evidence, dict
        ):
            data["confirmed_adult_classification_evidence"] = dict(
                requested_classification_evidence
            )
            data["exact_maturity_status"] = "confirmed_adult"
            data["complete_adult_curriculum_assignment"] = "IMMEDIATE"
            if preserve_age_progression_label:
                stage_one_evidence = data.get(
                    "age_progression_stage_one_evidence"
                )
                if isinstance(stage_one_evidence, dict):
                    stage_one_evidence[
                        "confirmed_adult_classification_evidence"
                    ] = dict(requested_classification_evidence)
                    stage_one_evidence["adult_classification_confirmed"] = True
        if maturity_class == "adult_aged_up_variant":
            data["age_progression_presentation_label"] = "adult_aged_up_variant"
            if stage_two_gate.get("status") == "passed":
                stage_one_evidence = data.get("age_progression_stage_one_evidence")
                if isinstance(stage_one_evidence, dict):
                    exact_classification = stage_one_evidence.get(
                        "confirmed_adult_classification_evidence"
                    )
                    if isinstance(exact_classification, dict):
                        data["confirmed_adult_classification_evidence"] = dict(
                            exact_classification
                        )
                    data["resident_adult_anatomy_choice_recorded"] = (
                        stage_one_evidence.get(
                            "resident_adult_anatomy_choice_recorded"
                        )
                        is True
                    )
                data["exact_maturity_status"] = "confirmed_adult"
                data["confirmed_adult_classification_id"] = stage_two_gate.get(
                    "confirmed_adult_classification_id"
                )
                data["complete_adult_curriculum_assignment"] = "IMMEDIATE"
            else:
                data["exact_maturity_status"] = "unresolved"
                data["complete_adult_curriculum_assignment"] = (
                    "ADULT_CURRICULUM_BLOCKED_GUARANTEED_MINIMUM_WITH_SEPARATELY_APPROVED_AGE_APPROPRIATE_MODULES_ALLOWED"
                )
                data["adult_anatomy_auto_added"] = False
        changes.append(
            "Recorded the exact confirmed-adult classification while preserving the separate age-progression presentation label."
            if preserve_age_progression_label
            else f"Set maturity override to {maturity_class}."
        )
        understood_intents.append(f"maturity:{maturity_class}")
        _add_target(data, "maturity", reason, "Robert correction")

    if "head" in lowered:
        _add_target(data, "head", message, "Robert correction")
        understood_intents.append("head_shape_or_size")
        current = float(preview.get("head_scale") or 1.0)
        if any(term in lowered for term in ("too big", "smaller", "large", "oversized")):
            preview["head_scale"] = round(max(0.82, current - 0.04), 3)
            changes.append(f"Adjusted preview head scale to {preview['head_scale']}.")
        elif any(term in lowered for term in ("too small", "bigger", "larger", "tiny")):
            preview["head_scale"] = round(min(1.22, current + 0.04), 3)
            changes.append(f"Adjusted preview head scale to {preview['head_scale']}.")
        else:
            preview.setdefault("head_scale", current)
            changes.append("Queued head shape/size review.")

    if any(term in lowered for term in ("eye", "eyes", "socket", "sclera", "iris", "pupil")):
        requested_color = _requested_eye_color(message)
        candidate_key = candidate_id.strip().lower()
        persisted_requested_color = str(data.get("requested_eye_color") or "").strip()
        effective_requested_color = requested_color or persisted_requested_color
        if candidate_key == "kira":
            target_eye_color = (
                f"realistic {effective_requested_color} adult Kira iris color "
                "(Robert-requested provisional target; Kira owner review remains required)"
                if effective_requested_color
                else "Kira's adult eye color after Kira owner review of a visual target"
            )
        elif candidate_key == CANONICAL_GWEN_ID:
            target_eye_color = f"realistic {effective_requested_color} Gwen iris color" if effective_requested_color else "realistic blue-gray Gwen iris color from Spider-Verse references"
        elif candidate_key == NORMAL_MARINETTE_CANDIDATE_ID:
            target_eye_color = f"realistic {effective_requested_color} Marinette iris color" if effective_requested_color else "realistic blue Marinette iris color from references"
        else:
            target_eye_color = f"candidate-specific realistic {effective_requested_color} iris color from approved references" if effective_requested_color else "candidate-specific realistic iris color from approved references"
        if requested_color:
            data["requested_eye_color"] = requested_color
            understood_intents.append(f"eye_color:{requested_color}")
        else:
            understood_intents.append("eyes")
        eye_plan = write_eye_rebuild_plan(
            candidate_id,
            target_eye_color,
            "Robert asked for eyes to be added/fixed; missing named eyes is treated as a construction task, not a blocker excuse.",
        )
        data["eye_rebuild_plan"] = project_relative(eye_plan)
        _add_target(
            data,
            "eyes",
            (
                "Run landmark-driven eye construction: measure head and socket landmarks first, then create named "
                f"sclera/iris/pupil/eyelid/look-target parts seated in the sockets; plan: {project_relative(eye_plan)}."
            ),
            "Robert correction",
        )
        preview["eye_guide_y"] = 0.835
        preview["eye_guide_width"] = 0.30
        changes.append(f"Queued landmark-driven eye construction for {target_eye_color} and tightened preview eye guides.")

    if any(term in lowered for term in ("hair", "hairline", "bald", "pigtail", "bang", "groom")):
        _add_target(data, "hair", message, "Robert correction")
        preview["show_hair_priority"] = candidate_id.strip().lower() != "kira"
        preview["detachable_hair_component_only"] = True
        if candidate_id.strip().lower() == "kira":
            preview["runtime_scalp_hair_enabled"] = False
        understood_intents.append("hair")
        changes.append("Queued a detachable hair-component fitting/generation lesson without regenerating the body.")

    if any(term in lowered for term in ("face does not look", "face doesn't look", "does not look like", "doesn't look like", "face likeness", "likeness", "generic face")):
        _add_target(data, "face", message, "Robert correction")
        understood_intents.append("face_likeness")
        changes.append("Queued a candidate-specific face-likeness correction from approved references.")

    if any(term in lowered for term in ("body", "torso", "shoulder", "arm", "leg", "hand", "feet", "proportion", "shape")):
        _add_target(data, "body", message, "Robert correction")
        understood_intents.append("body_shape")
        changes.append("Queued body proportion review.")

    height = _extract_height_measurement(message)
    if height:
        data.setdefault("physical_measurements", {})["height"] = height
        data["target_height_m"] = height["height_m"]
        data["target_height_source"] = "Robert chat"
        extracted_facts["height"] = height
        _add_target(
            data,
            "measurements",
            (
                f"Use Robert-provided target height {height['height_m']}m "
                f"({height['feet']} ft {height['inches']} in) to scale the base body before likeness sculpting."
            ),
            "Robert measurement",
        )
        understood_intents.append("measurement:height")
        changes.append(f"Recorded target height {height['height_m']}m ({height['feet']} ft {height['inches']} in).")

    age_progression_stage_two = bool(
        maturity
        and maturity[0] == "adult_aged_up_variant"
        and stage_two_gate.get("status") == "passed"
    )
    age_progression_stage_one = bool(
        maturity
        and maturity[0] == "adult_aged_up_variant"
        and not age_progression_stage_two
    )
    if any(term in lowered for term in ("barbie", "doll treatment", "doll-safe", "doll safe", "anatomy")):
        _add_target(
            data,
            "anatomy_policy",
            (
                "For a spa age-progression request, complete Stage 1 only as an unresolved doll-safe older/taller "
                "presentation/build label. Adult curriculum waits for separate exact confirmed-adult evidence, "
                "and adult anatomy waits for the later Stage 2 choice and build gate."
                if age_progression_stage_one
                else (
                    "The exact Stage 1 age-progression and spa-eligibility evidence passed. Queue Stage 2 adult "
                    "anatomy only on the separate inactive adult-aged variant; do not alter the original non-adult body."
                    if age_progression_stage_two
                    else "Re-check maturity policy before the next build. Adult candidates must not use non-adult doll-safe "
                    "body treatment; non-adult candidates must remain smooth/non-explicit."
                )
            ),
            "Robert correction",
        )
        understood_intents.append("anatomy_policy")
        changes.append("Queued anatomy/maturity policy review.")

    adult_body_fit_terms = any(
        term in lowered
        for term in (
            "adult body",
            "barbie",
            "doll treatment",
            "doll-safe",
            "doll safe",
            "anatomy",
            "body shape",
            "body fit",
            "proportion",
            "shoulder",
            "waist",
            "hips",
            "torso",
            "height",
        )
    ) or height is not None
    adult_body_candidate = (
        data.get("maturity_override") in ADULT_CLASSES
        or bool(maturity and maturity[0] in ADULT_CLASSES)
        or data.get("exact_maturity_status") == "confirmed_adult"
        or candidate_id.strip().lower() in CANONICAL_ADULT_CANDIDATE_IDS
    )
    if adult_body_candidate and adult_body_fit_terms and not age_progression_stage_one:
        body_fit_plan = write_adult_body_fit_plan(
            candidate_id,
            "Robert rejected the adult body as generic/doll-like; maturity metadata is not enough without real landmark-driven body fitting.",
            data.get("physical_measurements", {}).get("height") if isinstance(data.get("physical_measurements"), dict) else None,
        )
        data["adult_body_fit_plan"] = project_relative(body_fit_plan)
        data["adult_body_fit_status"] = "failed_requires_landmark_lattice_sculpt_fit"
        data["adult_body_fit_reason"] = (
            "Adult policy is allowed, but the actual mesh must be fitted from measurements and references before approval."
        )
        preview["non_adult_review_garment"] = False
        _add_target(
            data,
            "adult_body_fit",
            (
                "Do not treat the adult maturity flag as body approval. Scale to known measurements, fit the adult base "
                "with front/side/back landmarks and a lattice/sculpt pass, preserve neutral adult anatomy/proportions, "
                f"and write proof artifacts; plan: {project_relative(body_fit_plan)}."
            ),
            "Robert correction",
        )
        understood_intents.append("adult_body_fit")
        changes.append("Queued adult body-fit contract; the current generic/doll-like body remains failed until a real fitting pass produces proof.")

    if any(term in lowered for term in ("skin", "skin tone", "complexion", "too pale", "too white", "warmer")):
        _add_target(data, "skin_tone", message, "Robert correction")
        understood_intents.append("skin_tone")
        changes.append("Queued skin tone/material review.")

    research_query = _research_request_from_message(message)
    if research_query:
        request = {
            "created_at": now_iso(),
            "status": "queued_requires_robert_or_tool_approval",
            "query": research_query,
            "source": "Robert chat",
            "rule": "Search only when explicitly requested; save source links and do not claim a result until sources are recorded.",
        }
        data.setdefault("online_research_requests", []).append(request)
        _add_target(data, "online_learning", f"Research online for: {research_query}", "Robert correction")
        understood_intents.append("online_learning")
        extracted_facts["online_research_request"] = request
        changes.append("Queued online-learning research task with source-recording rules.")

    if candidate_id.strip().lower() == NORMAL_MARINETTE_CANDIDATE_ID:
        preview["non_adult_review_garment"] = False

    directives = derive_correction_directives(
        candidate_id,
        message,
        requested_maturity_class=maturity[0] if maturity else "",
        previous_maturity_class=previous_maturity,
        age_progression_stage_one_eligibility_gate=(
            data.get("age_progression_stage_one_eligibility_gate")
            if isinstance(data.get("age_progression_stage_one_eligibility_gate"), dict)
            else {}
        ),
        age_progression_stage_two_gate=stage_two_gate,
    )
    event = append_correction_event(
        data,
        candidate_id=candidate_id,
        message=message,
        directives=directives,
        recorded_at=now_iso(),
    )
    if event:
        route = route_next_private_build(data, event)
        for instruction in directives.get("instructions") or []:
            _add_target(
                data,
                str(instruction.get("area") or "general"),
                str(instruction.get("instruction") or ""),
                "Robert correction memory",
            )
        understood_intents.extend(directives.get("intents") or [])
        extracted_facts["correction_memory_event_id"] = event["event_id"]
        extracted_facts["next_private_build_route"] = {
            "components_to_rebuild": route["components_to_rebuild"],
            "body_lane": route["body_lane"],
            "status": route["status"],
        }
        changes.append(
            f"Recorded append-only correction {event['event_id']} and rerouted the next private, inactive, unapproved build."
        )
    data["last_understood_intents"] = sorted(set(understood_intents))
    _record_design_conversation(data, message, extracted_facts, understood_intents)
    return changes


def run_builder_review(candidate_id: str, profile: dict[str, Any] | None = None, focus: str = "auto") -> dict[str, Any]:
    data = load_adjustments(candidate_id)
    candidate_key = candidate_id.strip().lower()
    review_corrects_maturity = candidate_key in {
        NORMAL_MARINETTE_CANDIDATE_ID,
        "kira",
        CANONICAL_PETER_ID,
        CANONICAL_GWEN_ID,
    }
    if not review_corrects_maturity:
        current_validation = validate_candidate_maturity_identity(
            candidate_id,
            _maturity_validation_profile(candidate_id, profile, data, None),
        )
        if current_validation["status"] != "passed":
            return {
                "ok": False,
                "status": "blocked_maturity_identity_policy",
                "candidate_id": candidate_id,
                "message": "Avatar Builder review was blocked before writes by incompatible maturity metadata.",
                "changes": [],
                "adjustments_saved": False,
                "maturity_identity_validation": current_validation,
            }
    inspection = inspect_candidate_model(candidate_id)
    preview = data.setdefault("preview_adjustments", {})
    changes: list[str] = []
    log_activation(candidate_id, f"run_builder_review:{focus}")

    if candidate_key == NORMAL_MARINETTE_CANDIDATE_ID:
        data["maturity_override"] = "non_adult_doll_safe"
        data["maturity_reason"] = "Normal Marinette/Ladybug remains non-adult. A separate spa age-progressed presentation variant remains unresolved until exact subject-bound classification."
        preview.update({
            "head_scale": 1.04,
            "eye_guide_y": 0.835,
            "eye_guide_width": 0.30,
            "non_adult_review_garment": False,
        })
        _add_target(data, "identity", "Current model is not approved as a Marinette likeness; rebuild against the 59 reviewed references.", "builder review")
        hair_plan = write_hair_rebuild_plan(
            candidate_id,
            "Marinette deep blue-black low twin pigtails and side-swept bangs",
            "Robert graded the current hair F because it does not look close enough to Marinette.",
        )
        eye_plan = write_eye_rebuild_plan(
            candidate_id,
            "realistic blue Marinette eyes matched from references",
            "Robert rejected placeholder/floating eyes and wants realistic color changes using the eye model library.",
        )
        _add_target(data, "hair", f"Current Marinette hair is failed. Rebuild from hair model references using {project_relative(hair_plan)}.", "builder review")
        _add_target(data, "hair", "Generate or fit deep blue-black side-swept bangs and low twin pigtails; save as separate hair mesh with scalp anchors.", "builder review")
        _add_target(data, "eyes", f"Replace placeholder eyes with realistic named sclera/iris/pupil/eyelid meshes seated inside sockets; plan: {project_relative(eye_plan)}.", "builder review")
        _add_target(data, "body", "Start from the usable female-base body branch, then keep the normal Marinette result smooth non-adult-safe; block explicit adult anatomy and do not use the primitive procedural redo as the active body.", "Robert correction")
        changes.append("Locked normal Marinette/Ladybug to smooth non-adult-safe review and queued likeness/hair/eye rebuild targets.")
    elif candidate_key == "kira":
        data["maturity_override"] = "adult"
        data["maturity_reason"] = "Kira is an adult synthetic person and may use adult body/anatomy references in neutral avatar-building contexts."
        data["test_role"] = "not_valid_adult_reference_test_until_robert_adds_visual_references"
        preview.update({
            "head_scale": 1.0,
            "eye_guide_y": 0.835,
            "eye_guide_width": 0.30,
            "non_adult_review_garment": False,
        })
        _add_target(data, "references", "Do not use Kira as the adult likeness/body-reference test until Robert provides or approves visual references. Use Peter, Gwen, or Robert for adult tests now.", "Robert correction")
        _add_target(data, "eyes", "Kira needs separate named eye, iris, pupil, eyelid, and head socket anchors; reject floating or side-face eyes.", "builder review")
        _add_target(data, "body", "Keep Kira on the clean shared adult base body; do not copy Marinette hair, face, or body edits.", "builder review")
        _add_target(data, "hair", "Kira hair is separate wearable hair fitted to scalp/head anchors, not part of the body mesh.", "builder review")
        changes.append("Recorded Kira as adult but not a valid adult reference test until visual references exist.")
    elif candidate_key == CANONICAL_PETER_ID:
        data["maturity_override"] = "adult"
        data["maturity_reason"] = "Robert selected Peter as an adult avatar-builder test pick."
        data["test_role"] = "adult_reference_test_pick"
        preview.setdefault("non_adult_review_garment", False)
        _add_target(data, "body", "Use adult male base-body/anatomy references for a neutral face/body trial before hair and wardrobe.", "builder review")
        _add_target(data, "eyes", "Use named eyes and sockets; reject mask/face planes that hide bad eye placement.", "builder review")
        changes.append("Locked Peter to adult body test policy.")
    elif candidate_key == CANONICAL_GWEN_ID:
        refs = gwen_reference_paths()
        unmasked_reference = PROJECT_ROOT / refs["unmasked_head_hair_model"]
        spandex_reference = PROJECT_ROOT / refs["rigged_spandex_costume_model"]
        data["maturity_override"] = "adult"
        data["maturity_reason"] = "Robert selected Gwen as an adult avatar-builder test pick."
        data["test_role"] = "adult_reference_test_pick_sources_ready"
        data["current_body_rejected_reason"] = "The active costume runtime body is not the base body, but it is useful as a spandex silhouette and removable wardrobe reference."
        data["approval_status"] = "adult_rebuild_sources_ready"
        data["gwen_reference_sources"] = refs
        preview.setdefault("non_adult_review_garment", False)
        eye_plan = write_eye_rebuild_plan(
            candidate_id,
            "realistic blue Gwen eyes from unmasked model and new chat-uploaded references",
            "Robert wants the Avatar Builder to learn realistic eye color/material changes while placing eyes in the correct sockets.",
        )
        wardrobe_plan = write_gwen_spandex_wardrobe_plan(candidate_id)
        body_fit_plan = write_adult_body_fit_plan(
            candidate_id,
            "Robert rejected Gwen's current body as a generic/barbie-like adult proof; rebuild with real adult landmark fitting.",
            data.get("physical_measurements", {}).get("height") if isinstance(data.get("physical_measurements"), dict) else None,
        )
        data["adult_body_fit_plan"] = project_relative(body_fit_plan)
        data["adult_body_fit_status"] = "failed_requires_landmark_lattice_sculpt_fit"
        _add_target(data, "body", "Build an adult neutral Gwen base body from the female base body, adult anatomy/reference models, Avatar/library female body/proportions, and the spandex costume silhouette; do not use the costume mesh as the naked/base body.", "Robert correction")
        _add_target(data, "adult_body_fit", f"Run a true adult body-fit pass before approval; plan: {project_relative(body_fit_plan)}.", "Robert correction")
        _add_target(data, "head_hair", f"Use the saved unmasked Gwen model for head/hair reference: {refs['unmasked_head_hair_model']}.", "Robert correction")
        _add_target(data, "wardrobe", f"Convert the Ghost-Spider spandex suit into removable clothing layers instead of baking it into the body; plan: {project_relative(wardrobe_plan)}.", "Robert correction")
        _add_target(data, "eyes", f"Use eye-reference models to place realistic Gwen eyes in sockets and recolor only the iris/material; plan: {project_relative(eye_plan)}.", "Robert F-grade correction")
        _add_target(data, "hair", "Use Gwen's blonde asymmetric side-part hair from the unmasked model and new image references; hair is separate from head and hood.", "builder review")
        if not unmasked_reference.exists():
            data["approval_status"] = "failed_waiting_for_unmasked_gwen_model"
            _add_target(data, "references", f"Missing unmasked Gwen reference model: {refs['unmasked_head_hair_model']}.", "model inspection")
        if not spandex_reference.exists():
            data["approval_status"] = "failed_waiting_for_spandex_costume_model"
            _add_target(data, "references", f"Missing rigged spandex costume reference model: {refs['rigged_spandex_costume_model']}.", "model inspection")
        changes.append("Queued Gwen adult rebuild with unmasked head/hair reference, spandex body silhouette, realistic eye plan, and removable costume wardrobe plan.")
    else:
        _add_target(data, "review", "Run visual reference, maturity, head, eyes, hair, body, and movement review before accepting this avatar.", "builder review")
        changes.append("Queued generic avatar review.")

    if inspection.get("issues"):
        for issue in inspection["issues"]:
            _add_target(data, "model_diagnostics", str(issue), "model inspection")
        changes.append("Stored model diagnostics from the linked GLB.")

    _note(data, "Builder review ran and updated correction targets.", ["builder_review", focus])
    if data.get("approval_status") not in {
        "failed_redo_required",
        "redo_draft_ready_for_robert_review",
        "female_base_restored_eye_training_required",
        "failed_waiting_for_out_of_costume_refs",
        "adult_rebuild_sources_ready",
        "failed_disqualified_reference_copy",
        "base_body_pass_ready_for_robert_review",
        "round_eye_mechanics_preview_ready_overlay_required",
        "failed_robert_big_f_overlay_required",
        "silhouette_overlay_calibration_ready_failed_likeness",
        "avatar_builder_school_required_failed_preview",
        "builder_reference_pass_ready_for_robert_review",
        "failed_waiting_for_unmasked_gwen_model",
        "failed_waiting_for_spandex_costume_model",
    }:
        data["approval_status"] = "failed_needs_rebuild_or_review" if data.get("build_targets") else "unreviewed"
    maturity_validation = validate_candidate_maturity_identity(
        candidate_id,
        _maturity_validation_profile(candidate_id, profile, data, None),
    )
    if maturity_validation["status"] != "passed":
        return {
            "ok": False,
            "status": "blocked_maturity_identity_policy",
            "candidate_id": candidate_id,
            "message": "Avatar Builder review produced incompatible maturity metadata and was not saved.",
            "changes": [],
            "adjustments_saved": False,
            "maturity_identity_validation": maturity_validation,
        }
    path = save_adjustments(candidate_id, data)
    append_global_lesson(
        candidate_id,
        ["avatar_builder", "review", "head", "eyes", "hair", "body"],
        "Avatar Builder must compare the linked GLB, reference images, and Robert corrections before approving a body.",
    )
    return {
        "ok": True,
        "candidate_id": candidate_id,
        "message": "Avatar Builder review complete.",
        "changes": changes,
        "adjustments_path": project_relative(path),
        "inspection": inspection,
        "adjustments": data,
        "maturity_identity_validation": maturity_validation,
    }


def avatar_builder_chat(candidate_id: str, message: str, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    data = load_adjustments(candidate_id)
    message = message.strip()
    requested_maturity = _maturity_from_message(message)
    requested_classification_evidence = (
        _owner_confirmed_adult_classification_evidence(candidate_id, message)
        if requested_maturity and requested_maturity[0] == "adult"
        else None
    )
    persisted_maturity = str(data.get("maturity_override") or "").strip()
    has_age_progression_provenance = (
        persisted_maturity == "adult_aged_up_variant"
        or data.get("age_progression_presentation_label")
        == "adult_aged_up_variant"
        or (
            isinstance(data.get("age_progression_contract"), dict)
            and data["age_progression_contract"].get("contract")
            == "two_stage_spa_age_progression_v1"
        )
    )
    requests_age_progression_anatomy = (
        has_age_progression_provenance
        and _requests_age_progression_stage_two_body(message)
    )
    requests_age_progression_stage_one = bool(
        requested_maturity
        and requested_maturity[0] == "adult_aged_up_variant"
        and not requests_age_progression_anatomy
    )
    stage_one_eligibility_gate: dict[str, Any] = {}
    if requests_age_progression_stage_one:
        profile_eligibility = (
            profile.get("age_progression_eligibility_evidence")
            if isinstance(profile, dict)
            and isinstance(profile.get("age_progression_eligibility_evidence"), dict)
            else {}
        )
        stored_eligibility = (
            data.get("age_progression_eligibility_evidence")
            if isinstance(data.get("age_progression_eligibility_evidence"), dict)
            else {}
        )
        stage_one_eligibility_gate = evaluate_age_progression_stage_one_eligibility(
            stored_eligibility or profile_eligibility
        )
    if requests_age_progression_anatomy:
        stage_two_gate = evaluate_age_progression_stage_two_gate(
            {"age_progression": data.get("age_progression_contract") or {}},
            data.get("age_progression_stage_one_evidence")
            if isinstance(data.get("age_progression_stage_one_evidence"), dict)
            else {},
        )
        if stage_two_gate["status"] != "passed":
            return {
                "ok": False,
                "status": "blocked_age_progression_stage_one_evidence_required",
                "candidate_id": candidate_id,
                "reply": (
                    "I did not add or queue adult anatomy. The older/taller presentation/build label, "
                    "separate exact confirmed-adult classification, spa eligibility, and the resident's "
                    "Stage 2 adult-anatomy choice must pass exact evidence first."
                ),
                "changes": [],
                "adjustments_saved": False,
                "age_progression_stage_two_gate": stage_two_gate,
            }
        requested_maturity = (
            "adult_aged_up_variant",
            "Exact Stage 1 age-progression evidence passed; Robert requested the separate Stage 2 anatomy build.",
        )
    explicitly_non_adult_in_place_change = (
        persisted_maturity == "non_adult_doll_safe"
        and bool(requested_maturity and requested_maturity[0] == "adult")
        and candidate_id.strip().lower() not in CANONICAL_ADULT_CANDIDATE_IDS
    )
    if explicitly_non_adult_in_place_change:
        return {
            "ok": False,
            "status": "blocked_separate_age_up_variant_required",
            "candidate_id": candidate_id,
            "reply": (
                "I did not age up or overwrite the explicitly non-adult body. Create a distinct spa age-up "
                "candidate/version first; Stage 1 establishes only the older/taller presentation/build label "
                "without adult anatomy. The separate exact adult classification remains a later gate."
            ),
            "changes": [],
            "adjustments_saved": False,
            "maturity_identity_validation": {
                "schema_version": 1,
                "candidate_id": candidate_id,
                "status": "failed",
                "failures": ["explicit_non_adult_body_cannot_be_aged_up_in_place"],
            },
        }
    maturity_profile = _maturity_validation_profile(
        candidate_id,
        profile,
        data,
        requested_maturity,
        requested_classification_evidence,
    )
    maturity_validation = validate_candidate_maturity_identity(candidate_id, maturity_profile)
    if maturity_validation["status"] != "passed":
        separate_variant_required = (
            "age_up_requires_distinct_candidate_id_and_variant_profile"
            in maturity_validation["failures"]
            or "canonical_non_adult_identity_cannot_be_aged_up_in_place"
            in maturity_validation["failures"]
        )
        status = (
            "blocked_separate_age_up_variant_required"
            if separate_variant_required
            else "blocked_maturity_identity_policy"
        )
        reply = (
            "I did not change this candidate. Age-up must use a distinct aged-up candidate "
            "ID and variant profile; the normal identity remains unchanged."
            if separate_variant_required
            else "I did not change this candidate because the requested body policy conflicts "
            "with its confirmed maturity identity."
        )
        return {
            "ok": False,
            "status": status,
            "candidate_id": candidate_id,
            "reply": reply,
            "changes": [],
            "adjustments_saved": False,
            "maturity_identity_validation": maturity_validation,
        }
    if (
        requests_age_progression_stage_one
        and stage_one_eligibility_gate.get("status") != "passed"
    ):
        return {
            "ok": False,
            "status": "blocked_spa_age_progression_eligibility_required",
            "candidate_id": candidate_id,
            "reply": (
                "I did not queue an age-up body. Stage 1 first requires exact evidence of temporary origin, "
                "permanent promotion, at least two prior activations, the resident's recorded choice, and "
                "the spa flow."
            ),
            "changes": [],
            "adjustments_saved": False,
            "age_progression_stage_one_eligibility_gate": stage_one_eligibility_gate,
        }
    if requests_age_progression_stage_one:
        data["age_progression_stage_one_eligibility_gate"] = stage_one_eligibility_gate
    inspection = inspect_candidate_model(candidate_id)
    log_activation(candidate_id, "chat")
    changes = _apply_message_adjustments(
        candidate_id,
        message,
        data,
        requested_classification_evidence,
    )

    if any(term in message.lower() for term in ("review", "run", "inspect", "look at", "check")):
        review = run_builder_review(candidate_id, profile, focus="chat_request")
        data = review["adjustments"]
        changes.extend(review["changes"])

    data.setdefault("conversation", []).append({
        "created_at": now_iso(),
        "from": "Robert",
        "message": message,
    })

    if not changes:
        _add_target(data, "general", message, "Robert correction")
        changes.append("I saved that as a builder correction target.")

    understood = data.get("last_understood_intents") or []
    reply_parts = [
        "Avatar Builder is active for this build task only.",
        (
            "I understood: " + ", ".join(str(item) for item in understood) + "."
            if understood
            else "I saved the correction as a general build target."
        ),
        "I updated candidate build memory; a builder pass is still required to change the actual GLB.",
    ]
    if inspection.get("model_ready"):
        reply_parts.append(
            f"I inspected {inspection.get('model_path')} with {inspection.get('node_count')} nodes and {inspection.get('mesh_count')} meshes."
        )
    if inspection.get("issues"):
        reply_parts.append("Problems I see: " + "; ".join(str(item) for item in inspection["issues"][:3]) + ".")
    reply_parts.append("Changes: " + " ".join(changes))
    reply = " ".join(reply_parts)

    data["conversation"].append({
        "created_at": now_iso(),
        "from": "Avatar Builder",
        "message": reply,
    })
    data["last_reply"] = reply
    path = save_adjustments(candidate_id, data)
    append_global_lesson(candidate_id, ["avatar_builder", "robert_correction"], message, source="Robert correction")

    return {
        "ok": True,
        "candidate_id": candidate_id,
        "reply": reply,
        "changes": changes,
        "adjustments_path": project_relative(path),
        "inspection": inspection,
        "adjustments": data,
        "maturity_identity_validation": maturity_validation,
    }
