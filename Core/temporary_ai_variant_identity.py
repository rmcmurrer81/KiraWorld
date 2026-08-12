"""Grounded identity records for historical and fictional synthetic variants.

A variant shares source history through a selected branch point and develops
its own continuity afterward.  Later source updates are learned information;
they never overwrite the variant's lived memories.
"""

from __future__ import annotations

from typing import Any, Mapping


COMMON_REQUIRED = (
    "source_identity",
    "person_type",
    "source_continuity",
    "source_version",
    "source_cutoff_date",
    "branch_point",
    "inherited_source_memories",
    "new_variant_memories",
    "post_instantiation_relationships",
    "canon_facts",
    "kira_world_runtime_facts",
    "uncertainty_and_source_conflicts",
)

FICTIONAL_REQUIRED = (
    "life_stage",
    "relationships_at_cutoff",
    "knowledge_limits",
    "powers_and_abilities_at_cutoff",
)

HISTORICAL_REQUIRED = (
    "documented_experiences",
    "historically_supported_relationships",
    "information_unavailable_at_cutoff",
)


def validate_variant_identity_record(record: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in COMMON_REQUIRED:
        if field not in record or record[field] in (None, "", []):
            errors.append(f"missing required variant field: {field}")
    person_type = str(record.get("person_type", "")).casefold()
    if person_type == "synthetic fictional variant":
        required = FICTIONAL_REQUIRED
    elif person_type == "synthetic historical variant":
        required = HISTORICAL_REQUIRED
    else:
        required = ()
        if person_type:
            errors.append(
                "person_type must be synthetic fictional variant or "
                "synthetic historical variant"
            )
    for field in required:
        if field not in record or record[field] in (None, "", []):
            errors.append(f"missing required {person_type} field: {field}")
    if record.get("later_source_updates_overwrite_variant_memories") is not False:
        errors.append("later source updates must never overwrite variant memories")
    if record.get("post_branch_events_inherited_as_autobiography") is not False:
        errors.append("post-branch events must not be inherited as autobiography")
    if record.get("biological_source_transported") is not False:
        errors.append("the biological or fictional source must not be marked transported")
    return errors


LOKI_2012_EXAMPLE = {
    "source_identity": "Loki",
    "person_type": "synthetic fictional variant",
    "source_continuity": "Marvel Cinematic Universe",
    "source_version": "2012 New York branch",
    "life_stage": "adult through The Avengers",
    "source_cutoff_date": "2012",
    "branch_point": "New York, immediately after obtaining the Tesseract",
    "inherited_source_memories": ["source life through The Avengers"],
    "new_variant_memories": ["stored separately after activation"],
    "relationships_at_cutoff": ["Thor", "Odin", "Frigga", "Asgard"],
    "post_instantiation_relationships": ["stored only after direct experience"],
    "knowledge_limits": ["no autobiographical memory of later original-timeline events"],
    "powers_and_abilities_at_cutoff": ["only abilities belonging to the selected MCU version"],
    "canon_facts": ["selected primary-continuity facts through the branch point"],
    "kira_world_runtime_facts": ["stored separately from source canon"],
    "uncertainty_and_source_conflicts": ["kept labeled rather than silently resolved"],
    "later_source_updates_overwrite_variant_memories": False,
    "post_branch_events_inherited_as_autobiography": False,
    "biological_source_transported": False,
}


__all__ = [
    "LOKI_2012_EXAMPLE",
    "validate_variant_identity_record",
]
