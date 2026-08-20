#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
LIBRARY_PATH = ROOT / "item_prefab_library" / "item_prefab_library.json"
PROJECT_ROOT = ROOT / "projects" / "neighbor_three_bed_house_retry_20260707"


def load_library() -> dict[str, Any]:
    return json.loads(LIBRARY_PATH.read_text(encoding="utf-8"))


def prefabs_with(lib: dict[str, Any], tag: str, *, min_confidence: str = "medium") -> list[dict[str, Any]]:
    confidence_rank = {"low": 0, "medium": 1, "high": 2}
    threshold = confidence_rank[min_confidence]
    return [
        prefab
        for prefab in lib["prefabs"]
        if tag in prefab.get("tags", [])
        and confidence_rank.get(prefab.get("confidence", "low"), 0) >= threshold
    ]


def choose_first(lib: dict[str, Any], tag: str, keywords: list[str], *, min_confidence: str = "medium") -> dict[str, Any] | None:
    candidates = prefabs_with(lib, tag, min_confidence=min_confidence)
    lowered = [keyword.lower() for keyword in keywords]
    for prefab in candidates:
        haystack = " ".join(
            str(value or "")
            for value in [
                prefab.get("id"),
                prefab.get("source"),
                prefab.get("sourceFile"),
                prefab.get("nodeName"),
                " ".join(prefab.get("nodePath") or []),
            ]
        ).lower()
        if any(keyword in haystack for keyword in lowered):
            return prefab
    return candidates[0] if candidates else None


def prefab_ref(prefab: dict[str, Any] | None, role: str, required: bool = True) -> dict[str, Any]:
    if not prefab:
        return {"role": role, "required": required, "status": "missing"}
    return {
        "role": role,
        "required": required,
        "status": "selected",
        "prefabId": prefab["id"],
        "source": prefab["source"],
        "nodeIndex": prefab.get("nodeIndex"),
        "nodeName": prefab.get("nodeName"),
        "confidence": prefab.get("confidence"),
        "tags": prefab.get("tags", []),
    }


def build_plan(lib: dict[str, Any]) -> dict[str, Any]:
    selections = {
        "frontDoor": choose_first(lib, "door", ["door_panel", "simplydoor", "5_doors", "door (1)", "door.glb"], min_confidence="medium"),
        "interiorDoor": choose_first(lib, "door", ["door_panel", "simplydoor", "5_doors", "door (1)", "door.glb"], min_confidence="medium"),
        "sofa": choose_first(lib, "couch", ["modern_sofa", "sofa"], min_confidence="medium"),
        "bookshelf": choose_first(lib, "bookshelf", ["book_shelf.glb", "book_shelf"], min_confidence="medium"),
        "book": choose_first(lib, "book", ["book (1)", "book (2)", "notebook", "object_38"], min_confidence="medium"),
        "diningSet": choose_first(lib, "table", ["outdoor_table_and_chairs", "dining"], min_confidence="medium"),
        "bedCandidate": choose_first(lib, "bed", ["simple_bed", "victorian_bed", "bed_mattress_20_mb", "bed.glb"], min_confidence="medium"),
        "mattress": choose_first(lib, "mattress", ["bed_mattress_20_mb", "matress", "mattress"], min_confidence="medium"),
        "pillow": choose_first(lib, "pillow", ["bed_pillow", "pillow"], min_confidence="medium"),
        "bathroomFixture": choose_first(lib, "bathroom_fixture", ["toilet", "toilet_"], min_confidence="medium"),
    }

    required_roles = [
        prefab_ref(selections["frontDoor"], "front door"),
        prefab_ref(selections["interiorDoor"], "interior bedroom doors"),
        prefab_ref(selections["sofa"], "living room couch"),
        prefab_ref(selections["bookshelf"], "real bookshelf"),
        prefab_ref(selections["book"], "books/notebooks"),
        prefab_ref(selections["diningSet"], "dining table and chairs"),
        prefab_ref(selections["bedCandidate"], "bed candidate"),
        prefab_ref(selections["mattress"], "mattress"),
        prefab_ref(selections["pillow"], "pillow"),
        prefab_ref(selections["bathroomFixture"], "bathroom fixture"),
    ]

    has_mattress_prefab = bool(prefabs_with(lib, "mattress", min_confidence="medium"))
    has_pillow_prefab = bool(prefabs_with(lib, "pillow", min_confidence="medium"))
    validation_failures: list[str] = []
    for role in required_roles:
        if role["required"] and role["status"] != "selected":
            validation_failures.append(f"Missing required prefab for {role['role']}.")
    if not has_mattress_prefab:
        validation_failures.append(
            "No confirmed mattress/blanket/pillow prefab exists in the downloaded/staged model library. Do not spawn a finished furnished bedroom yet."
        )
    if not has_pillow_prefab:
        validation_failures.append(
            "No confirmed pillow prefab exists in the downloaded/staged model library. Do not spawn a finished furnished bedroom yet."
        )

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceLibrary": str(LIBRARY_PATH),
        "objective": "Retry a realistic 3-bedroom house next to the main home only after the generator can use real tagged assets.",
        "status": "blocked_before_spawn" if validation_failures else "ready_for_runtime_spawn",
        "spawnAllowed": not validation_failures,
        "layout": {
            "houseType": "single-story 3-bedroom residential test house",
            "placement": "next to the main home with a large walk-around gap",
            "frontZone": ["porch", "entry foyer", "living room", "dining area"],
            "rearPrivateZone": ["bedroom 1", "bedroom 2", "bedroom 3", "bathroom"],
            "rules": [
                "No bed in the front room.",
                "Front door must be walkable when open.",
                "Every visible door must use an imported door prefab plus a matching runtime open/close collider.",
                "Do not generate block furniture.",
                "If a required real asset is missing, leave the room unfurnished and report the missing asset.",
            ],
        },
        "selectedPrefabs": required_roles,
        "validationFailures": validation_failures,
        "nextAssetNeeded": None if not validation_failures else "A real bed/mattress/pillow/blanket model or a confirmed downloaded bed prefab with visible soft bedding.",
    }


def write_project(plan: dict[str, Any]) -> None:
    PROJECT_ROOT.mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "asset_plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    lines = [
        "# Neighbor 3-Bed House Retry",
        "",
        f"Generated: {plan['generatedAt']}",
        f"Status: {plan['status']}",
        f"Spawn allowed: {plan['spawnAllowed']}",
        "",
        "## Selected Real Prefabs",
        "",
    ]
    for role in plan["selectedPrefabs"]:
        if role["status"] == "selected":
            lines.append(f"- {role['role']}: `{role['prefabId']}` from `{role['source']}` node `{role.get('nodeName')}`")
        else:
            lines.append(f"- {role['role']}: MISSING")
    lines.extend(["", "## Validation", ""])
    if plan["validationFailures"]:
        for failure in plan["validationFailures"]:
            lines.append(f"- FAIL: {failure}")
    else:
        lines.append("- PASS: real-asset plan is ready for runtime spawning and screenshot collision tests.")
    lines.extend(["", "## Layout Rules", ""])
    for rule in plan["layout"]["rules"]:
        lines.append(f"- {rule}")
    (PROJECT_ROOT / "validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    lib = load_library()
    plan = build_plan(lib)
    write_project(plan)
    print(json.dumps({"project": str(PROJECT_ROOT), "status": plan["status"], "spawnAllowed": plan["spawnAllowed"]}, indent=2))
    return 0 if plan["spawnAllowed"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
