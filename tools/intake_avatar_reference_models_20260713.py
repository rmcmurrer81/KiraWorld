from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_ROOT = ROOT / "Avatar" / "avatar_builder" / "reference_models"
AVATAR_TEMP = ROOT / "Avatar" / "temp_ai"
TEMP_CANDIDATES = ROOT / "TemporaryAI" / "candidates"
MODEL_SUFFIXES = {".glb", ".gltf", ".fbx", ".obj", ".usdz"}
ARCHIVE_SUFFIXES = {".zip"}


SUBJECT_RULES = [
    ("beth_smith_reference", "Beth Smith (Adult Reference)", ["beth_smith", "beth-smith"]),
    ("elsa_frozen_reference", "Elsa / Frozen Reference", ["elsa", "frozen"]),
    ("vincent_van_gogh_reference", "Vincent van Gogh Reference", ["vincent_van_gogh", "van-gogh", "van_gogh"]),
    (
        "sarah_michelle_gellar_reference",
        "Sarah Michelle Gellar (Adult Actor Reference)",
        ["sarah_michelle_gellar", "sarah-michelle-gellar", "sarah_michelle_geller", "sarah-michelle-geller"],
    ),
    ("spider_gwen_spider_gwen_20260606_013325", "Gwen Stacy / Spider-Gwen", ["gwen", "stacy"]),
    ("peter_parker_spider_man_no_way_home_final_suit", "Peter Parker / Spider-Man", ["peter", "parker", "spiderman", "spider_man", "raimi"]),
    ("harley_quinn_reference", "Harley Quinn", ["harley", "quinn"]),
    ("batgirl_reference", "Batgirl", ["batgirl"]),
    ("miles_morales_reference", "Miles Morales", ["miles", "morales"]),
    ("tony_stark_reference", "Tony Stark", ["tony", "stark"]),
    ("lucifer_morningstar_reference", "Lucifer Morningstar", ["lucifer", "morningstar"]),
    ("adult_anatomy_reference", "Adult Anatomy Reference", ["anatomy", "muscle", "muscles", "bones", "skeleton"]),
    ("adult_female_shape_reference", "Adult Female Shape Reference", ["sexy_women", "sexy", "women", "woman", "female"]),
    ("power_rangers_reference", "Power Rangers Props And Characters", ["power", "ranger", "rangers", "morpher", "powermorpher", "dagger", "dulcea", "zedd", "alpha"]),
    ("hand_reference", "Hand And Gesture Reference", ["hand", "gesture"]),
    ("head_expression_reference", "Head Planes And Expression Reference", ["head", "expression", "loomis", "planes"]),
]

SUBJECT_MATURITY = {
    "beth_smith_reference": {
        "maturity_class": "adult",
        "source": "Robert correction 2026-07-15: Beth is an adult and the supplied model has a full adult body.",
        "adult_anatomy_assets_allowed": True,
    },
    "elsa_frozen_reference": {
        "maturity_class": "adult",
        "source": (
            "Robert correction 2026-07-15: both supported movie versions are adult. "
            "Elsa is 21 in Frozen (2013), and Disney/D23 places Frozen II three years later (about 24)."
        ),
        "adult_anatomy_assets_allowed": True,
        "supported_versions": {
            "frozen_2013": {"age": 21, "adult": True},
            "frozen_ii_2019": {"age": 24, "adult": True},
        },
        "source_urls": [
            "https://frozen.disney.com/elsa",
            "https://d23.com/meet-the-enchanting-new-characters-of-frozen-2/",
        ],
    },
    "vincent_van_gogh_reference": {
        "maturity_class": "adult",
        "source": "Historical adult subject reference; reference-only model, not an AI body.",
        "adult_anatomy_assets_allowed": True,
    },
    "sarah_michelle_gellar_reference": {
        "maturity_class": "adult",
        "source": (
            "Robert correction 2026-07-15: adult actor likeness reference for Kathryn Merteuil; "
            "the actor reference does not determine the character candidate's age or body policy."
        ),
        "adult_anatomy_assets_allowed": True,
    },
}


SUBJECT_CANDIDATE_LINKS = {
    "sarah_michelle_gellar_reference": [
        "kathryn_merteuil_kathryn_merteuil_20260605_213017",
    ],
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path | str) -> str:
    path = Path(path)
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "reference"


def tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.lower()) if token}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def subject_for_file(path: Path) -> tuple[str, str]:
    text = path.stem.lower().replace("-", "_").replace(" ", "_")
    file_tokens = tokens(text)
    for subject_id, display_name, hints in SUBJECT_RULES:
        if any(hint in text or hint in file_tokens for hint in hints):
            return subject_id, display_name
    subject_id = f"{slug(path.stem)}_reference"
    return subject_id, " ".join(part.capitalize() for part in subject_id.split("_") if part) or subject_id


def target_kind(path: Path) -> str:
    lowered = path.name.lower()
    if path.suffix.lower() in ARCHIVE_SUFFIXES:
        return "archive_recorded_not_copied"
    if any(term in lowered for term in ("anatomy", "muscle", "bones", "skeleton", "nsfw", "nude", "naked")):
        return "adult_anatomy_reference"
    if any(term in lowered for term in ("sexy", "female", "woman", "women")):
        return "adult_female_shape_reference"
    if "mask" in lowered:
        return "mask_reference"
    if "morpher" in lowered or "dagger" in lowered:
        return "prop_reference"
    if "hand" in lowered or "gesture" in lowered:
        return "hand_reference"
    if "head" in lowered or "loomis" in lowered or "expression" in lowered:
        return "head_expression_reference"
    return "character_model_reference"


def copy_reference(source: Path, subject_dir: Path, digest: str, *, copy_models: bool) -> Path | None:
    if not copy_models or source.suffix.lower() not in MODEL_SUFFIXES:
        return None
    target = subject_dir / "source_models" / f"{slug(source.stem)}_{digest[:10]}{source.suffix.lower()}"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        shutil.copy2(source, target)
    return target


def candidate_dirs_for_subject(subject_id: str) -> list[Path]:
    matches: list[Path] = []
    candidate_ids = [subject_id, *SUBJECT_CANDIDATE_LINKS.get(subject_id, [])]
    for root in (AVATAR_TEMP, TEMP_CANDIDATES):
        for candidate_id in candidate_ids:
            candidate = root / candidate_id
            if candidate.exists():
                matches.append(candidate)
    return matches


def write_candidate_link(subject_id: str, display_name: str, subject_manifest: Path) -> None:
    for candidate_dir in candidate_dirs_for_subject(subject_id):
        out_dir = candidate_dir / "references" / "model_references"
        out_dir.mkdir(parents=True, exist_ok=True)
        target_candidate_id = candidate_dir.name
        link_path = out_dir / (
            "local_model_reference_manifest.json"
            if target_candidate_id == subject_id
            else f"{subject_id}_manifest.json"
        )
        is_actor_likeness_bridge = (
            subject_id == "sarah_michelle_gellar_reference"
            and target_candidate_id == "kathryn_merteuil_kathryn_merteuil_20260605_213017"
        )
        link = {
            "schema_version": 1,
            "updated_at": now_iso(),
            "candidate_id": target_candidate_id,
            "reference_subject_id": subject_id,
            "display_name": display_name,
            "reference_model_manifest": rel(subject_manifest),
            "usage_policy": (
                "These local models are references only. The Avatar Builder may measure, compare, "
                "and learn from them, but may not copy them as the candidate body."
            ),
            "actor_character_bridge": is_actor_likeness_bridge,
            "allowed_reference_uses": (
                ["face_likeness", "head_proportions", "hairline", "expression_comparison"]
                if is_actor_likeness_bridge
                else ["measurement", "visual_comparison", "reference_study"]
            ),
            "forbidden_inferences": (
                [
                    "do_not_copy_actor_mesh_as_kathryn_body",
                    "do_not_infer_kathryn_maturity_from_actor_age",
                    "do_not_use_adult_actor_anatomy_for_a_non_adult_or_uncertain_candidate",
                ]
                if is_actor_likeness_bridge
                else ["do_not_copy_reference_mesh_as_candidate_body"]
            ),
        }
        link_path.write_text(json.dumps(link, indent=2), encoding="utf-8")


def intake_folder(
    source_root: Path,
    *,
    copy_models: bool = True,
    include_subject_ids: set[str] | None = None,
) -> dict:
    source_root = source_root.resolve()
    if not source_root.exists():
        raise FileNotFoundError(source_root)
    grouped: dict[str, dict] = {}
    seen_hashes: set[str] = set()
    sources = [source_root] if source_root.is_file() else sorted(source_root.rglob("*"))
    for source in sources:
        if not source.is_file() or source.suffix.lower() not in (MODEL_SUFFIXES | ARCHIVE_SUFFIXES):
            continue
        subject_id, display_name = subject_for_file(source)
        if include_subject_ids and subject_id not in include_subject_ids:
            continue
        digest = sha256(source)
        if digest in seen_hashes:
            continue
        seen_hashes.add(digest)
        subject_dir = REFERENCE_ROOT / subject_id
        copied = copy_reference(source, subject_dir, digest, copy_models=copy_models)
        maturity = SUBJECT_MATURITY.get(
            subject_id,
            {
                "maturity_class": "uncertain_non_adult_safe_default",
                "source": "No per-subject maturity review was recorded during intake.",
                "adult_anatomy_assets_allowed": False,
            },
        )
        kind = target_kind(source)
        adult_only = (
            maturity["maturity_class"] == "adult"
            or
            kind in {"adult_anatomy_reference", "adult_female_shape_reference"}
            or any(term in source.name.lower() for term in ("nsfw", "nude", "naked"))
        )
        record = {
            "source_file": str(source),
            "filename": source.name,
            "size_bytes": source.stat().st_size,
            "sha256": digest,
            "kind": kind,
            "copied_file": rel(copied) if copied else "",
            "reference_only": True,
            "copy_as_avatar_body_allowed": False,
            "maturity_class": maturity["maturity_class"],
            "adult_only": adult_only,
            "allowed_for_non_adult": not adult_only,
        }
        entry = grouped.setdefault(
            subject_id,
            {
                "schema_version": 1,
                "updated_at": now_iso(),
                "subject_id": subject_id,
                "display_name": display_name,
                "source_root": str(source_root),
                "reference_only_rule": (
                    "Use these models for measuring, visual comparison, proportions, costumes, props, "
                    "hair/face/body study, and world-builder objects. Do not copy a character model as an AI body. "
                    "Adult anatomy or adult-shape references are only for adult candidates."
                ),
                "maturity_policy": maturity,
                "models": [],
            },
        )
        entry["models"].append(record)

    index = {
        "schema_version": 1,
        "updated_at": now_iso(),
        "source_root": str(source_root),
        "reference_root": rel(REFERENCE_ROOT),
        "copy_mode": "copied_reference_models" if copy_models else "metadata_only_source_links",
        "subjects": [],
    }
    for subject_id, manifest in sorted(grouped.items()):
        subject_dir = REFERENCE_ROOT / subject_id
        manifest["updated_at"] = now_iso()
        manifest["model_count"] = len(manifest["models"])
        subject_manifest = subject_dir / "reference_model_manifest.json"
        subject_manifest.parent.mkdir(parents=True, exist_ok=True)
        subject_manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        write_candidate_link(subject_id, str(manifest["display_name"]), subject_manifest)
        index["subjects"].append(
            {
                "subject_id": subject_id,
                "display_name": manifest["display_name"],
                "model_count": manifest["model_count"],
                "manifest": rel(subject_manifest),
            }
        )

    index_slug = slug(source_root.name or source_root.stem or "reference_folder")
    subject_suffix = ""
    if include_subject_ids:
        subject_suffix = "_" + "_".join(sorted(include_subject_ids))
    index_path = REFERENCE_ROOT / f"{index_slug}{subject_suffix}_reference_intake_20260713.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
    return index


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Intake a local folder as Avatar Builder reference-only models.")
    parser.add_argument("--source-root", default=str(Path.home() / "Desktop" / "45"))
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Write reference manifests without copying model files into the workspace.",
    )
    parser.add_argument(
        "--subject-id",
        action="append",
        default=[],
        help="Only intake files classified to this subject ID. Repeat for more than one subject.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    index = intake_folder(
        Path(args.source_root),
        copy_models=not args.metadata_only,
        include_subject_ids=set(args.subject_id) or None,
    )
    print(json.dumps(index, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
