"""Run a long Avatar Builder School session.

This is the Avatar Builder equivalent of Kira's school loop. It does not
generate or promote a body. It indexes Robert's model references, runs the
measurement lab, then cycles through lessons and assignments so the builder has
recorded evidence before the next preview attempt.

Run:
  py tools/run_avatar_builder_school_loop_20260712.py --duration-hours 4 --cycle-minutes 15
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHOOL_ROOT = PROJECT_ROOT / "Avatar" / "avatar_builder" / "school"
ASSIGNMENT_ROOT = SCHOOL_ROOT / "assignments"
SESSION_ROOT = SCHOOL_ROOT / "session_runs"
PROGRESS_PATH = SCHOOL_ROOT / "progress" / "avatar_builder_school_progress_20260712.json"
MANIFEST_PATH = PROJECT_ROOT / "Avatar" / "avatar_builder" / "asset_library" / "manifest.json"
PRESENCE_DIR = PROJECT_ROOT / "Data" / "presence"
CURRENT_RUN_PATH = PRESENCE_DIR / "current_avatar_builder_school_run.json"
STOP_PATH = PRESENCE_DIR / "avatar_builder_school_stop.json"
PAUSE_PATH = PRESENCE_DIR / "avatar_builder_school_pause.json"
DEFAULT_SOURCE_ROOTS = [
    Path.home() / "Desktop" / "1model",
    Path.home() / "Desktop" / "21",
]
DEFAULT_BLENDER = Path(r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe")


LESSON_PLAN: list[dict[str, Any]] = [
    {
        "lesson_id": "eye_asset_lab",
        "class_id": "eye_model_lab_001",
        "title": "Eye Model Structure And Materials",
        "categories": ["eye_reference"],
        "assignments": [
            "identify sclera, iris, pupil, cornea/catchlight, eyelid, and socket anchor",
            "record which meshes are geometry eyes and which are decorative surfaces",
            "learn iris recolor by material change without changing eyeball size",
        ],
        "critical_asset_terms": ["4_eyes_compatible", "human_eye", "green_eye", "eye_blend"],
        "required_evidence": [
            "asset list includes at least one 4-eyes compatible model",
            "assignment records which eye assets can teach socket placement and which are only material/color examples",
        ],
        "gates": [
            "no flat cyan plates",
            "no eye mesh larger than the fitted socket permits",
            "left/right eyes remain separate and named",
        ],
    },
    {
        "lesson_id": "eye_socket_placement",
        "class_id": "eye_model_lab_001",
        "title": "Eye Socket Placement And Scale",
        "categories": ["eye_reference", "base_body_reference"],
        "assignments": [
            "place eyeball centers behind the face plane, not on top of it",
            "fit eye diameter from head width and eye spacing instead of hard-coded size",
            "verify front and side screenshots before a preview can pass",
        ],
        "critical_asset_terms": ["4_eyes_compatible"],
        "required_evidence": [
            "socket-placement assignment explicitly references the 4-eyes compatible model",
            "assignment repeats that side view must prove the eye is seated, not stuck on the face",
        ],
        "gates": [
            "eyes sit inside the head",
            "iris and pupil sit on the round eye surface",
            "side view shows no protruding goggles",
        ],
    },
    {
        "lesson_id": "photo_head_reconstruction",
        "class_id": "head_photo_reconstruction_001",
        "title": "Photo-Based Head Reconstruction On A Generic Body",
        "categories": ["eye_reference", "face_mouth_reference", "base_body_reference", "motion_reference"],
        "assignments": [
            "use head photos from front, left profile, right profile, three-quarter, and back/top where available",
            "build a new head mesh over a generic body instead of copying a reference model head",
            "place round movable eyes inside sockets and connect eyelids/brows to expression controls",
            "build a real mouth opening with lips, teeth, and tongue controls for voice lip-sync",
            "attach the head to a neck/head rig so it can bend, turn, look up/down, and look around",
            "save front, side, three-quarter, top, and mouth-open proof renders before any character approval",
        ],
        "critical_asset_terms": ["4_eyes_compatible", "mouth", "tongue", "skeleton_rig"],
        "required_evidence": [
            "photo references are treated as the head-shape source, not model meshes",
            "generic body is used only as a scale and neck attachment base",
            "eyes, mouth, eyelids, brows, jaw, tongue, neck, and head controls are named separately",
            "proof renders show the recreated head from multiple angles on the generic body",
        ],
        "photo_reference_views": [
            "front neutral face",
            "left profile",
            "right profile",
            "three-quarter front",
            "back of head or hair silhouette",
            "mouth open / smile if available",
        ],
        "output_requirements": [
            "candidate_head_mesh.glb",
            "candidate_head_on_generic_body.glb",
            "front_head_overlay.png",
            "left_profile_overlay.png",
            "right_profile_overlay.png",
            "three_quarter_overlay.png",
            "eyes_inside_socket_side_proof.png",
            "mouth_open_lip_sync_proof.png",
            "head_neck_rig_controls.json",
            "likeness_measurement_report.json",
        ],
        "reference_photo_policy": [
            "Photos may drive silhouette, proportions, color, asymmetry, and facial landmark placement.",
            "Reference models may teach topology, anatomy, rigging, and motion only.",
            "Do not paste a photo plane as a face card.",
            "Do not copy a full model head or body as the candidate.",
            "Non-adult avatars remain doll-safe below the neck; adult anatomy references are adult-only.",
        ],
        "gates": [
            "head silhouette matches front and profile photos before hair is judged",
            "eyes are two round movable eyes seated inside sockets",
            "mouth opens from the head mesh and has lip-sync controls",
            "head bends on a neck/head rig without detaching from generic body",
            "photos and generated head overlays are saved from multiple angles",
            "Robert review is required before the head can be used by any AI",
        ],
    },
    {
        "lesson_id": "body_shape_overlay",
        "class_id": "body_anatomy_and_maturity_001",
        "title": "Base Body Reshaping From Pictures And Reference Models",
        "categories": ["base_body_reference"],
        "assignments": [
            "start from the approved base body or foundation rig",
            "use front and side image planes as overlays",
            "reshape head, torso, arms, hips, legs, hands, and feet with morph targets",
            "never copy a full reference model as the candidate body",
        ],
        "critical_asset_terms": ["womenfemale_body_base", "low_poly_female_textured", "base_female"],
        "required_evidence": [
            "base body references are listed separately from anatomy references",
            "assignment says reference models are for silhouette/proportion only and cannot be copied",
        ],
        "gates": [
            "one continuous candidate body on the shared rig",
            "front/side/back measurements saved",
            "no pasted head, face card, or copied model body",
        ],
    },
    {
        "lesson_id": "adult_anatomy_gate",
        "class_id": "body_anatomy_and_maturity_001",
        "title": "Adult Anatomy Class And Non-Adult Safety Gate",
        "categories": ["adult_anatomy_reference", "base_body_reference"],
        "assignments": [
            "use adult anatomy only for adult avatars or explicit adult variants",
            "keep normal Marinette non-adult doll-safe",
            "keep Gwen, Peter, Robert, Kira, and Lisa in adult-capable policy when their records say adult",
            "study skeleton, muscle, pelvis, body proportion, and motion references separately",
        ],
        "critical_asset_terms": ["ashley", "nude", "pelvis", "muscle", "topless", "sexy"],
        "required_evidence": [
            "adult-only count is nonzero when adult anatomy class runs",
            "assignment includes the Marinette/Gwen adult-vs-non-adult policy difference",
        ],
        "gates": [
            "adult-only assets never appear in non-adult builds",
            "Gwen does not receive Barbie/non-adult treatment",
            "maturity policy is written before any body reference is used",
        ],
    },
    {
        "lesson_id": "head_face_expression",
        "class_id": "head_face_topology_001",
        "title": "Head Shape, Mouth, Eyes, And Expression Topology",
        "categories": ["eye_reference", "face_mouth_reference", "base_body_reference"],
        "assignments": [
            "map jaw, mouth corners, lips, cheeks, brow, eyelids, and eye anchors",
            "prepare blink, look, phoneme, smile, frown, and neutral expression controls",
            "reject egg heads and face cards before likeness review",
        ],
        "critical_asset_terms": ["mouth", "tongue", "teeth", "4_eyes_compatible"],
        "required_evidence": [
            "mouth/tongue/teeth references are available before lip-sync approval",
            "eye and mouth controls are listed as separate moving systems",
        ],
        "gates": [
            "mouth is attached to the face",
            "eyes can look around without leaving sockets",
            "lip-sync controls are named before voice approval",
        ],
    },
    {
        "lesson_id": "hair_construction",
        "class_id": "hair_construction_001",
        "title": "Hair Construction From References",
        "categories": ["hair_reference", "base_body_reference"],
        "assignments": [
            "build hair as separate wearable mesh or strand/card groups",
            "anchor hair to scalp/head bones",
            "support multiple styles for one person, such as Marinette pigtails and hair-down variants",
            "record front, side, and back hair silhouettes",
        ],
        "critical_asset_terms": ["hair", "scalp", "bones"],
        "required_evidence": [
            "hair reference assets are listed and current Marinette/Gwen hair grades remain visible",
            "assignment rejects copied heads and face meshes",
        ],
        "gates": [
            "no blob hair",
            "hair follows head movement",
            "hair does not import a copied head or face",
        ],
    },
    {
        "lesson_id": "motion_rig_lab",
        "class_id": "body_anatomy_and_maturity_001",
        "title": "Movement, Rigging, Hands, And Animation References",
        "categories": ["motion_reference", "base_body_reference"],
        "assignments": [
            "study animated and rigged models for joint orientation and weights",
            "test idle, walk, run, sit, stair, reach, hand curl, blink, and mouth movement",
            "record motion failure before runtime promotion",
        ],
        "critical_asset_terms": ["walking", "animated", "hand_animation", "skeleton_rig"],
        "required_evidence": [
            "walking animated reference is listed when available",
            "movement assignment includes walking, hands, head, eyes, and mouth",
        ],
        "gates": [
            "arms do not freeze in T-pose during idle",
            "hands can grab clothes/doors/cups",
            "head, eyes, and mouth move independently",
        ],
    },
    {
        "lesson_id": "wardrobe_fabric_lab",
        "class_id": "real_clothes_and_fabric_001",
        "title": "Real Clothes And Fabric State Machine",
        "categories": ["shoe_reference", "base_body_reference", "motion_reference"],
        "assignments": [
            "separate stored, carried, dressing, worn, fastened, and removed garment states",
            "use cloth simulation or baked morphs only during the dressing action",
            "swap to a stable skinned garment after clothing is worn",
            "make shirts use sleeve openings, collar, buttons, and hand grab points",
        ],
        "critical_asset_terms": ["shoe", "hand_animation", "walking"],
        "required_evidence": [
            "assignment preserves the garment state machine",
            "assignment rejects hanging-state clothes floating after a worn transition",
        ],
        "gates": [
            "no hanging-state shirt floating in front of body after dressing",
            "worn clothes follow the avatar rig",
            "clothes remain removable objects, not painted-on body textures",
        ],
    },
    {
        "lesson_id": "review_quiz",
        "class_id": "avatar_builder_review_001",
        "title": "Review Quiz And Next-Preview Blockers",
        "categories": [
            "eye_reference",
            "base_body_reference",
            "adult_anatomy_reference",
            "hair_reference",
            "motion_reference",
            "face_mouth_reference",
        ],
        "assignments": [
            "list why the current Marinette and Gwen previews are still failed",
            "name the next measurements needed before a fresh preview",
            "write which assets are references only and which are allowed for each maturity policy",
        ],
        "critical_asset_terms": ["4_eyes_compatible", "mouth", "tongue", "walking", "animated"],
        "required_evidence": [
            "review names the 4-eyes, mouth/tongue, and walking references if present",
            "review says current bodies remain failed until Robert approves a new preview",
        ],
        "gates": [
            "current previews remain failed",
            "new preview requires front/head/profile screenshots",
            "Robert approval is required before runtime promotion",
        ],
    },
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        if isinstance(fallback, dict):
            return dict(fallback)
        if isinstance(fallback, list):
            return list(fallback)
        return fallback


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_jsonl(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def tail_text(text: str, limit: int = 2400) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[-limit:]


def run_command(args: list[str], log_path: Path, label: str, timeout: int = 300) -> dict[str, Any]:
    event = {
        "time": now_iso(),
        "type": "command_start",
        "label": label,
        "args": args,
    }
    append_jsonl(log_path, event)
    try:
        result = subprocess.run(
            args,
            cwd=str(PROJECT_ROOT),
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        payload = {
            "time": now_iso(),
            "type": "command_finish",
            "label": label,
            "returncode": result.returncode,
            "stdout_tail": tail_text(result.stdout),
            "stderr_tail": tail_text(result.stderr),
        }
    except Exception as exc:
        payload = {
            "time": now_iso(),
            "type": "command_error",
            "label": label,
            "error": repr(exc),
        }
    append_jsonl(log_path, payload)
    return payload


def load_manifest() -> dict[str, Any]:
    return read_json(MANIFEST_PATH, {"records": [], "categories": {}, "asset_count": 0})


def records_for_categories(manifest: dict[str, Any], categories: list[str]) -> list[dict[str, Any]]:
    allowed = set(categories)
    records = [
        record
        for record in manifest.get("records", []) or []
        if record.get("category") in allowed
    ]
    records.sort(key=lambda item: (str(item.get("category")), str(item.get("filename")).lower()))
    return [
        {
            "id": record.get("id"),
            "category": record.get("category"),
            "filename": record.get("filename"),
            "local_file": record.get("local_file"),
            "tags": record.get("tags", []),
            "adult_only": bool(record.get("adult_only")),
            "usage_policy": record.get("usage_policy"),
        }
        for record in records
    ]


def asset_matches_terms(record: dict[str, Any], terms: list[str]) -> bool:
    haystack = " ".join(
        [
            str(record.get("filename", "")),
            str(record.get("local_file", "")),
            " ".join(str(tag) for tag in record.get("tags", []) or []),
        ]
    ).lower()
    return any(term.lower() in haystack for term in terms)


def grade_assignment(lesson: dict[str, Any], lesson_assets: list[dict[str, Any]], adult_only_count: int) -> dict[str, Any]:
    critical_terms = lesson.get("critical_asset_terms", []) or []
    hits = [
        {
            "term": term,
            "matched_assets": [
                record.get("filename")
                for record in lesson_assets
                if asset_matches_terms(record, [term])
            ][:8],
        }
        for term in critical_terms
    ]
    missing = [item["term"] for item in hits if not item["matched_assets"]]
    pass_gate_checks = [
        {
            "gate": gate,
            "status": "unverified_needs_constructed_visual_proof",
        }
        for gate in lesson["gates"]
    ]
    evidence_checks = [
        {
            "evidence": item,
            "status": "recorded_as_requirement_not_passing_proof",
        }
        for item in lesson.get("required_evidence", []) or []
    ]
    if not lesson_assets:
        grade = "F_no_source_assets"
    elif missing and len(missing) == len(critical_terms):
        grade = "D_missing_all_critical_references"
    elif missing:
        grade = "C_missing_some_critical_references"
    else:
        grade = "F_reference_coverage_only_needs_constructed_visual_proof"
    if lesson["lesson_id"] == "adult_anatomy_gate" and adult_only_count <= 0:
        grade = "F_no_adult_anatomy_sources"
    return {
        "grade": grade,
        "critical_reference_hits": hits,
        "missing_critical_terms": missing,
        "pass_gate_checks": pass_gate_checks,
        "evidence_checks": evidence_checks,
        "reference_coverage_is_not_a_pass": True,
        "learning_proof": (
            "This is reference coverage and assignment setup only. It is not a passing lesson until the builder "
            "produces constructed, inspectable evidence such as front/side renders, measurements, or a GLB proof "
            "that satisfies the pass gates."
        ),
    }


def progress_class_entry(progress: dict[str, Any], class_id: str, title: str) -> dict[str, Any]:
    classes = progress.setdefault("classes", {})
    entry = classes.setdefault(class_id, {"title": title, "assignments": [], "pass_gate": []})
    entry.setdefault("title", title)
    entry["status"] = "studying_in_long_run"
    entry["times_seen"] = int(entry.get("times_seen") or 0) + 1
    entry["grade"] = "in_progress"
    entry["last_seen_at"] = now_iso()
    return entry


def write_lesson_artifact(
    run_id: str,
    cycle_index: int,
    lesson: dict[str, Any],
    manifest: dict[str, Any],
) -> Path:
    lesson_assets = records_for_categories(manifest, lesson["categories"])
    adult_only_count = sum(1 for record in lesson_assets if record.get("adult_only"))
    grade_card = grade_assignment(lesson, lesson_assets, adult_only_count)
    assignment_root = ASSIGNMENT_ROOT / "lesson_runs" / run_id
    assignment_path = assignment_root / f"{cycle_index:03d}_{lesson['lesson_id']}_assignment.json"
    grade_path = assignment_root / f"{cycle_index:03d}_{lesson['lesson_id']}_grade_card.json"
    assignment = {
        "schema_version": 1,
        "run_id": run_id,
        "cycle_index": cycle_index,
        "created_at": now_iso(),
        "lesson_id": lesson["lesson_id"],
        "class_id": lesson["class_id"],
        "title": lesson["title"],
        "assignment_status": "submitted_for_later_review",
        "instructions": lesson["assignments"],
        "required_evidence": lesson.get("required_evidence", []),
        "critical_asset_terms": lesson.get("critical_asset_terms", []),
        "photo_reference_views": lesson.get("photo_reference_views", []),
        "output_requirements": lesson.get("output_requirements", []),
        "reference_photo_policy": lesson.get("reference_photo_policy", []),
        "source_asset_count": len(lesson_assets),
        "adult_only_source_asset_count": adult_only_count,
        "source_assets": lesson_assets[:120],
        "reference_policy": [
            "Use these models as references only.",
            "Do not copy a full reference model as an AI body.",
            "Adult-only anatomy/body references are blocked for non-adult avatars.",
            "The 4-eyes compatible model should teach eye socket/movement/shape, not be pasted oversized onto a head.",
        ],
    }
    write_json(assignment_path, assignment)
    write_json(grade_path, {
        "schema_version": 1,
        "run_id": run_id,
        "cycle_index": cycle_index,
        "created_at": now_iso(),
        "lesson_id": lesson["lesson_id"],
        "class_id": lesson["class_id"],
        "title": lesson["title"],
        **grade_card,
        "assignment": rel(assignment_path),
    })
    artifact = {
        "schema_version": 1,
        "run_id": run_id,
        "cycle_index": cycle_index,
        "created_at": now_iso(),
        "lesson_id": lesson["lesson_id"],
        "class_id": lesson["class_id"],
        "title": lesson["title"],
        "status": "completed_lesson_cycle_not_graduated",
        "source_asset_count": len(lesson_assets),
        "adult_only_source_asset_count": adult_only_count,
        "source_assets": lesson_assets[:80],
        "assignments": lesson["assignments"],
        "photo_reference_views": lesson.get("photo_reference_views", []),
        "output_requirements": lesson.get("output_requirements", []),
        "reference_photo_policy": lesson.get("reference_photo_policy", []),
        "assignment_file": rel(assignment_path),
        "grade_card": rel(grade_path),
        "assignment_grade": grade_card["grade"],
        "missing_critical_terms": grade_card["missing_critical_terms"],
        "pass_gates": lesson["gates"],
        "non_negotiable_rules": [
            "Current Marinette and Gwen previews remain failed until Robert approves a future rebuild.",
            "Reference models teach shape, topology, movement, and materials; they are not bodies to copy.",
            "Adult-only anatomy references are blocked for normal Marinette and any non-adult or uncertain-age avatar.",
            "Gwen is adult and must not receive the non-adult doll-safe/Barbie treatment.",
        ],
        "next_teacher_action": (
            "Use this lesson artifact as input for the next measured preview attempt, "
            "then produce front/head/profile screenshots before claiming improvement."
        ),
    }
    path = SESSION_ROOT / run_id / f"{cycle_index:03d}_{lesson['lesson_id']}.json"
    write_json(path, artifact)
    update_assignment_index(run_id, artifact, assignment_path, grade_path)
    return path


def update_assignment_index(run_id: str, artifact: dict[str, Any], assignment_path: Path, grade_path: Path) -> None:
    index_path = ASSIGNMENT_ROOT / "lesson_runs" / run_id / "assignment_index.json"
    index = read_json(index_path, {"schema_version": 1, "run_id": run_id, "assignments": []})
    index["updated_at"] = now_iso()
    index["assignment_folder"] = rel(index_path.parent)
    index["assignments"].append({
        "cycle_index": artifact["cycle_index"],
        "lesson_id": artifact["lesson_id"],
        "title": artifact["title"],
        "assignment_grade": artifact["assignment_grade"],
        "assignment": rel(assignment_path),
        "grade_card": rel(grade_path),
        "session_artifact": rel(SESSION_ROOT / run_id / f"{artifact['cycle_index']:03d}_{artifact['lesson_id']}.json"),
        "missing_critical_terms": artifact["missing_critical_terms"],
    })
    write_json(index_path, index)


def update_progress(run_id: str, lesson: dict[str, Any], cycle_index: int, artifact_path: Path, summary_path: Path) -> None:
    progress = read_json(PROGRESS_PATH, {})
    progress["updated_at"] = now_iso()
    progress["status"] = "school_loop_running"
    progress["latest_school_loop"] = {
        "run_id": run_id,
        "cycle_index": cycle_index,
        "lesson_id": lesson["lesson_id"],
        "class_id": lesson["class_id"],
        "title": lesson["title"],
        "lesson_artifact": rel(artifact_path),
        "assignment_folder": rel(ASSIGNMENT_ROOT / "lesson_runs" / run_id),
        "assignment_index": rel(ASSIGNMENT_ROOT / "lesson_runs" / run_id / "assignment_index.json"),
        "summary": rel(summary_path),
    }
    progress_class_entry(progress, lesson["class_id"], lesson["title"])
    blocked = progress.setdefault("blocked_preview_claims", [])
    message = "Avatar Builder School long run is active; no current failed preview may be promoted."
    if message not in blocked:
        blocked.append(message)
    write_json(PROGRESS_PATH, progress)


def write_presence(status: str, data: dict[str, Any]) -> None:
    payload = {
        "schema_version": 1,
        "status": status,
        "updated_at": now_iso(),
        "pid": os.getpid(),
        **data,
    }
    write_json(CURRENT_RUN_PATH, payload)


def blender_path_from_arg(value: str | None) -> Path | None:
    if value:
        path = Path(value)
        return path if path.exists() else None
    if DEFAULT_BLENDER.exists():
        return DEFAULT_BLENDER
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a long Avatar Builder School session.")
    parser.add_argument("--duration-hours", type=float, default=4.0)
    parser.add_argument("--cycle-minutes", type=float, default=15.0)
    parser.add_argument("--source-root", action="append", type=Path, default=[])
    parser.add_argument("--blender", type=str, default=None)
    parser.add_argument("--start-cycle-index", type=int, default=0)
    args = parser.parse_args()

    run_id = f"avatar_builder_school_loop_{now_id()}"
    run_dir = SESSION_ROOT / run_id
    log_path = run_dir / f"{run_id}.jsonl"
    summary_path = run_dir / f"{run_id}_summary.json"
    source_roots = args.source_root or [path for path in DEFAULT_SOURCE_ROOTS if path.exists()]
    blender = blender_path_from_arg(args.blender)
    stop_started_at = STOP_PATH.stat().st_mtime if STOP_PATH.exists() else None

    write_presence("starting", {
        "run_id": run_id,
        "started_at": now_iso(),
        "duration_hours": args.duration_hours,
        "cycle_minutes": args.cycle_minutes,
        "start_cycle_index": args.start_cycle_index,
        "source_roots": [str(path) for path in source_roots],
        "log_path": rel(log_path),
        "summary_path": rel(summary_path),
        "stop_file": rel(STOP_PATH),
        "pause_file": rel(PAUSE_PATH),
    })
    append_jsonl(log_path, {"time": now_iso(), "type": "run_start", "run_id": run_id})

    update_args = [sys.executable, "tools/update_avatar_builder_asset_library.py"]
    for source_root in source_roots:
        update_args.extend(["--source-root", str(source_root)])
    run_command(update_args, log_path, "refresh_asset_library", timeout=900)
    run_command([sys.executable, "tools/run_avatar_builder_school_20260712.py"], log_path, "assign_school", timeout=300)
    if blender:
        run_command(
            [str(blender), "--background", "--python", "tools/run_avatar_builder_school_measurement_lab_20260712.py"],
            log_path,
            "measurement_lab",
            timeout=900,
        )
    else:
        append_jsonl(log_path, {
            "time": now_iso(),
            "type": "warning",
            "message": "Blender executable not found; measurement lab skipped.",
        })

    start = time.monotonic()
    end_at = start + max(0.05, args.duration_hours) * 3600.0
    cycle_seconds = max(60.0, args.cycle_minutes * 60.0)
    cycle_index = max(0, args.start_cycle_index)
    completed_count = 0
    completed_lessons: list[str] = []
    write_presence("running", {"run_id": run_id, "log_path": rel(log_path), "summary_path": rel(summary_path)})

    while time.monotonic() < end_at:
        if STOP_PATH.exists() and (stop_started_at is None or STOP_PATH.stat().st_mtime > stop_started_at):
            append_jsonl(log_path, {"time": now_iso(), "type": "stop_requested", "stop_file": rel(STOP_PATH)})
            break
        if PAUSE_PATH.exists():
            write_presence("paused", {"run_id": run_id, "log_path": rel(log_path), "summary_path": rel(summary_path)})
            append_jsonl(log_path, {"time": now_iso(), "type": "paused", "pause_file": rel(PAUSE_PATH)})
            time.sleep(min(60.0, cycle_seconds))
            continue

        manifest = load_manifest()
        lesson = LESSON_PLAN[cycle_index % len(LESSON_PLAN)]
        artifact_path = write_lesson_artifact(run_id, cycle_index, lesson, manifest)
        completed_lessons.append(lesson["lesson_id"])
        update_progress(run_id, lesson, cycle_index, artifact_path, summary_path)
        write_presence("running", {
            "run_id": run_id,
            "cycle_index": cycle_index,
            "current_lesson": lesson["lesson_id"],
            "current_lesson_title": lesson["title"],
            "log_path": rel(log_path),
            "summary_path": rel(summary_path),
            "latest_artifact": rel(artifact_path),
            "assignment_folder": rel(ASSIGNMENT_ROOT / "lesson_runs" / run_id),
            "assignment_index": rel(ASSIGNMENT_ROOT / "lesson_runs" / run_id / "assignment_index.json"),
        })
        append_jsonl(log_path, {
            "time": now_iso(),
            "type": "lesson_completed",
            "cycle_index": cycle_index,
            "lesson_id": lesson["lesson_id"],
            "artifact": rel(artifact_path),
        })
        cycle_index += 1
        completed_count += 1
        remaining = end_at - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(cycle_seconds, remaining))

    summary = {
        "schema_version": 1,
        "run_id": run_id,
        "finished_at": now_iso(),
        "status": "completed" if time.monotonic() >= end_at else "stopped",
        "duration_hours_requested": args.duration_hours,
        "cycle_minutes": args.cycle_minutes,
        "start_cycle_index": max(0, args.start_cycle_index),
        "cycles_completed": completed_count,
        "last_cycle_index": cycle_index - 1 if completed_count else None,
        "completed_lessons": completed_lessons,
        "source_roots": [str(path) for path in source_roots],
        "manifest": rel(MANIFEST_PATH),
        "progress": rel(PROGRESS_PATH),
        "log_path": rel(log_path),
        "rule": "This run teaches and records assignments only; it does not approve or promote any avatar body.",
    }
    write_json(summary_path, summary)

    progress = read_json(PROGRESS_PATH, {})
    progress["updated_at"] = now_iso()
    progress["status"] = "school_loop_completed" if summary["status"] == "completed" else "school_loop_stopped"
    progress["latest_school_loop_summary"] = rel(summary_path)
    write_json(PROGRESS_PATH, progress)

    write_presence(summary["status"], {
        "run_id": run_id,
        "cycles_completed": cycle_index,
        "summary_path": rel(summary_path),
        "log_path": rel(log_path),
    })
    append_jsonl(log_path, {"time": now_iso(), "type": "run_finish", **summary})
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
