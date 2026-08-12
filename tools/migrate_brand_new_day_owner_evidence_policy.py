"""Migrate the existing private Brand New Day intake to owner-evidence v2.

This is a bounded migration for an unrendered, unpublished intake. It adds no
owner claim and invents no spoiler. The original project status remains
AWAITING_ROBERT_OWNER_NOTES.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


EXPECTED_STATUS = "AWAITING_ROBERT_OWNER_NOTES"


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} does not contain a JSON object")
    return value


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def migrate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    project_path = root / "project.v2.json"
    manifest_path = root / "manifests" / "INTAKE_PACKAGE_MANIFEST.json"
    intake_path = root / "review" / "OWNER_SPOILER_REVIEW_INTAKE.md"
    readiness_path = root / "review" / "PROJECT_READINESS.json"
    source_seed_path = root / "research" / "OFFICIAL_SOURCE_SEED.json"

    project = read_json(project_path)
    status = project.get("status", {})
    readiness = status.get("project_readiness")
    if readiness != EXPECTED_STATUS:
        raise RuntimeError(
            f"Refusing migration: project readiness is {readiness!r}, "
            f"expected {EXPECTED_STATUS!r}."
        )
    if project.get("publication_enabled") is not False:
        raise RuntimeError("Refusing migration: publication is not disabled.")
    artifacts = project.get("artifacts", {})
    render_fields = (
        "clean_final_builder",
        "full_narration",
        "private_review_mp4",
        "owner_review_mp4",
    )
    if any(artifacts.get(name) for name in render_fields):
        raise RuntimeError("Refusing migration: a render or narration artifact exists.")

    preset = project.setdefault("preset", {})
    options = preset.setdefault("options", {})
    options.pop("owner_claims_are_not_external_fact_sources", None)
    options.update(
        {
            "owner_screening_evidence_supported": True,
            "owner_evidence_provenance_is_private_metadata": True,
            "owner_confirmed_screening_facts_may_be_narrated_directly": True,
            "official_confirmation_language_requires_official_public_source": True,
        }
    )

    intake = project.setdefault("owner_review_intake", {})
    intake["classification_rule"] = {
        "PUBLIC_VERIFIED_SOURCE": (
            "Information supported by an official source or reliable publication."
        ),
        "OWNER_FIRSTHAND_SCREENING_NOTE": (
            "What Robert personally reports seeing or hearing; valid private "
            "evidence that remains unconfirmed until Robert explicitly confirms "
            "the fact status."
        ),
        "OWNER_CONFIRMED_SCREENING_FACT": (
            "A firsthand fact Robert explicitly confirms was clearly shown, "
            "stated, named in dialogue, or identified in credits."
        ),
        "OWNER_INTERPRETATION": (
            "Robert's conclusion or theory when the movie implies something "
            "without explicitly establishing it."
        ),
        "UNVERIFIED_PUBLIC_RUMOR": (
            "An online claim that lacks sufficient confirmation and is not "
            "eligible as a factual script source."
        ),
    }
    intake["spoken_script_rule"] = (
        "Provenance stays in private metadata. A confirmed screening fact may "
        "be stated directly without saying 'according to Robert'; interpretations "
        "must remain hedged. Do not claim official Marvel/Sony/etc. confirmation "
        "without a linked official public source."
    )

    sources = project.setdefault("sources", {})
    sources.setdefault("owner_evidence", [])
    if sources["owner_evidence"]:
        raise RuntimeError(
            "Refusing migration: owner evidence is unexpectedly nonempty; "
            "this migration must not rewrite real owner notes."
        )
    sources["owner_evidence_policy"] = {
        "schema_version": 1,
        "evidence_classes": [
            "PUBLIC_VERIFIED_SOURCE",
            "OWNER_FIRSTHAND_SCREENING_NOTE",
            "OWNER_CONFIRMED_SCREENING_FACT",
            "OWNER_INTERPRETATION",
            "UNVERIFIED_PUBLIC_RUMOR",
        ],
        "raw_firsthand_requires_owner_attestation": True,
        "confirmed_fact_requires_explicit_shown_stated_named_or_credited_confirmation": True,
        "internal_provenance_requires_spoken_attribution": False,
        "confirmed_screening_fact_direct_narration_allowed": True,
        "interpretation_requires_hedged_wording": True,
        "official_confirmation_language_requires_linked_official_source": True,
        "later_corroboration_preserves_original_note_hash_and_timestamp": True,
    }

    atomic_json(project_path, project)

    intake_text = intake_path.read_text(encoding="utf-8")
    old = (
        "The Studio must preserve your words as owner\n"
        "observations/opinions, then independently verify external factual claims."
    )
    new = (
        "The Studio must preserve your exact meaning and classify each item as a\n"
        "firsthand note, an explicitly confirmed screening fact, or an interpretation.\n"
        "Public background claims still require public sources. Internal provenance\n"
        "does not have to be repeated in the narration."
    )
    if old in intake_text:
        intake_text = intake_text.replace(old, new)
        temporary = intake_path.with_name(intake_path.name + ".tmp")
        temporary.write_text(intake_text, encoding="utf-8", newline="\n")
        temporary.replace(intake_path)

    rows = []
    for path in (project_path, intake_path, readiness_path, source_seed_path):
        rows.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    manifest = {
        "schema_version": 1,
        "status": EXPECTED_STATUS,
        "publication_performed": False,
        "files": rows,
    }
    atomic_json(manifest_path, manifest)
    return {
        "status": "PASSED",
        "project_root": str(root),
        "project_status": readiness,
        "owner_evidence_count": len(sources["owner_evidence"]),
        "publication_enabled": project["publication_enabled"],
        "manifest": str(manifest_path),
        "project_sha256": sha256(project_path),
        "manifest_sha256": sha256(manifest_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(migrate(args.project_root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
