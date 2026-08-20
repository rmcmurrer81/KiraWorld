#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
LIBRARY_PATH = ROOT / "item_prefab_library" / "item_prefab_library.json"
PROJECT_ROOT = ROOT / "projects" / "neighbor_three_bed_house_blueprint_20260707"


def load_library() -> dict[str, Any]:
    return json.loads(LIBRARY_PATH.read_text(encoding="utf-8"))


def prefabs_with(lib: dict[str, Any], tag: str) -> list[dict[str, Any]]:
    return [prefab for prefab in lib.get("prefabs", []) if tag in prefab.get("tags", [])]


def choose(lib: dict[str, Any], tag: str, keywords: list[str]) -> dict[str, Any] | None:
    candidates = prefabs_with(lib, tag)
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


def asset_ref(prefab: dict[str, Any] | None, role: str) -> dict[str, Any]:
    if not prefab:
        return {"role": role, "status": "missing"}
    return {
        "role": role,
        "status": "selected",
        "prefabId": prefab.get("id"),
        "source": prefab.get("source"),
        "sourceFile": prefab.get("sourceFile"),
        "nodeName": prefab.get("nodeName"),
        "tags": prefab.get("tags", []),
        "confidence": prefab.get("confidence"),
    }


def room(name: str, kind: str, x1: float, x2: float, z1: float, z2: float) -> dict[str, Any]:
    return {
        "name": name,
        "kind": kind,
        "xMin": x1,
        "xMax": x2,
        "zMin": z1,
        "zMax": z2,
        "center": {"x": round((x1 + x2) / 2, 2), "z": round((z1 + z2) / 2, 2)},
        "size": {"width": round(x2 - x1, 2), "depth": round(z2 - z1, 2)},
    }


def build_blueprint(lib: dict[str, Any]) -> dict[str, Any]:
    cx = 31.0
    cz = 1.0
    width = 16.8
    depth = 16.2
    left = round(cx - width / 2, 2)
    right = round(cx + width / 2, 2)
    back = round(cz - depth / 2, 2)
    front = round(cz + depth / 2, 2)
    hall_left = round(cx - 1.05, 2)
    hall_right = round(cx + 1.05, 2)
    service_left = round(cx + 1.2, 2)
    service_mid = round(cx + 4.2, 2)

    rooms = [
        room("front living room", "living_room", left + 0.35, hall_left, cz + 2.75, front - 0.35),
        room("entry foyer and central hall", "hall", hall_left, hall_right, cz + 0.8, front - 0.35),
        room("rear bedroom hall", "hall", hall_left, right - 0.35, cz - 1.85, cz + 0.8),
        room("front dining room", "dining_room", service_left, right - 0.35, cz + 4.55, front - 0.35),
        room("right side kitchen", "kitchen", service_left, right - 0.35, cz + 1.75, cz + 4.45),
        room("hall bathroom", "bathroom", service_left, service_mid, cz - 0.95, cz + 0.75),
        room("rear left bedroom", "bedroom", left + 0.35, hall_left, back + 0.45, cz + 0.25),
        room("rear middle bedroom", "bedroom", hall_right, service_mid, back + 0.45, cz - 1.95),
        room("rear right bedroom", "bedroom", service_mid + 0.25, right - 0.35, back + 0.45, cz - 1.95),
    ]

    assets = [
        asset_ref(choose(lib, "couch", ["modern_sofa", "sofa", "living_room"]), "living room couch"),
        asset_ref(choose(lib, "bookshelf", ["book_shelf", "bookshelf"]), "living room bookshelf"),
        asset_ref(choose(lib, "book", ["book (1)", "notebook", "book"]), "readable book"),
        asset_ref(choose(lib, "table", ["outdoor_table_and_chairs", "dining"]), "dining table and chairs"),
        asset_ref(choose(lib, "bed", ["bed.glb", "simple_bed", "victorian_bed"]), "bed frame"),
        asset_ref(choose(lib, "mattress", ["bed_mattress", "mattress"]), "mattress"),
        asset_ref(choose(lib, "pillow", ["bed_pillow", "pillow"]), "pillow"),
        asset_ref(choose(lib, "bathroom_fixture", ["toilet_002", "toilet"]), "bathroom toilet"),
        asset_ref(choose(lib, "wall", ["moit_modular_assets", "wall_plain", "brick"]), "wall reference"),
        asset_ref(choose(lib, "window", ["wall_window", "window_frame", "window"]), "window reference"),
        asset_ref(choose(lib, "door", ["entry-door", "door.glb", "5_doors"]), "door reference"),
    ]

    doors = [
        {"name": "front entry door", "connects": ["porch", "entry foyer and central hall"], "x": cx - 0.35, "z": front, "width": 1.35, "wallAxis": "x"},
        {"name": "living to hall opening", "connects": ["front living room", "entry foyer and central hall"], "x": hall_left, "z": cz + 3.55, "width": 1.2, "wallAxis": "z"},
        {"name": "kitchen to hall opening", "connects": ["right side kitchen", "entry foyer and central hall"], "x": hall_right, "z": cz + 2.85, "width": 1.15, "wallAxis": "z"},
        {"name": "bathroom door", "connects": ["hall bathroom", "rear bedroom hall"], "x": hall_right, "z": cz + 0.1, "width": 0.95, "wallAxis": "z"},
        {"name": "rear left bedroom door", "connects": ["rear left bedroom", "rear bedroom hall"], "x": hall_left, "z": cz - 0.45, "width": 0.95, "wallAxis": "z"},
        {"name": "rear middle bedroom door", "connects": ["rear middle bedroom", "rear bedroom hall"], "x": cx + 2.85, "z": cz - 1.85, "width": 0.95, "wallAxis": "x"},
        {"name": "rear right bedroom door", "connects": ["rear right bedroom", "rear bedroom hall"], "x": cx + 6.25, "z": cz - 1.85, "width": 0.95, "wallAxis": "x"},
    ]

    furniture = [
        {"room": "front living room", "role": "real sofa", "assetRole": "living room couch"},
        {"room": "front living room", "role": "real bookshelf", "assetRole": "living room bookshelf"},
        {"room": "front dining room", "role": "real dining table and chairs", "assetRole": "dining table and chairs"},
        {"room": "right side kitchen", "role": "kitchen counters and appliances", "assetRole": "generated kitchen until a tagged kitchen prefab exists"},
        {"room": "hall bathroom", "role": "real toilet plus vanity and tub", "assetRole": "bathroom toilet"},
        {"room": "rear left bedroom", "role": "bed frame, mattress, pillow", "assetRole": "bed frame + mattress + pillow"},
        {"room": "rear middle bedroom", "role": "bed frame, mattress, pillow", "assetRole": "bed frame + mattress + pillow"},
        {"room": "rear right bedroom", "role": "bed frame, mattress, pillow", "assetRole": "bed frame + mattress + pillow"},
    ]

    failures: list[str] = []
    bedrooms = [item for item in rooms if item["kind"] == "bedroom"]
    if len(bedrooms) != 3:
        failures.append(f"Expected exactly 3 bedrooms, found {len(bedrooms)}.")
    required_kinds = {"living_room", "dining_room", "kitchen", "bathroom", "hall"}
    missing_kinds = sorted(required_kinds.difference({item["kind"] for item in rooms}))
    if missing_kinds:
        failures.append(f"Missing required room kinds: {', '.join(missing_kinds)}.")
    front_private = [item["name"] for item in bedrooms if item["zMax"] > cz + 1.7]
    if front_private:
        failures.append(f"Bedroom is in the front public zone: {', '.join(front_private)}.")
    missing_assets = [item["role"] for item in assets if item["status"] != "selected" and item["role"] not in {"wall reference", "window reference"}]
    if missing_assets:
        failures.append(f"Missing required real assets: {', '.join(missing_assets)}.")
    if not any(item["name"] == "front entry door" and "entry foyer and central hall" in item["connects"] for item in doors):
        failures.append("Front door does not connect to foyer/hall.")
    if any(item["room"].startswith("front") and "bed" in item["role"].lower() for item in furniture):
        failures.append("A bed was placed in a front public room.")

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "status": "ready_for_runtime_spawn" if not failures else "blocked_before_spawn",
        "spawnAllowed": not failures,
        "sourceLibrary": str(LIBRARY_PATH),
        "objective": "Blueprint first: create a coherent 3-bedroom neighbor house with public rooms in front, bedrooms in back, bathroom off the hall, real bed parts, real couch, real bookshelf, real dining set, and a clear walkable front door.",
        "shell": {
            "type": "single-story brick ranch",
            "center": {"x": cx, "z": cz},
            "width": width,
            "depth": depth,
            "frontZ": front,
            "backZ": back,
            "leftX": left,
            "rightX": right,
            "largeGapFromMainHouseEastWallMeters": round(left - 8.0, 2),
        },
        "rooms": rooms,
        "doors": doors,
        "windows": [
            {"room": "front living room", "wall": "front", "count": 1},
            {"room": "front dining room", "wall": "front", "count": 1},
            {"room": "right side kitchen", "wall": "right", "count": 1},
            {"room": "hall bathroom", "wall": "right", "count": 1},
            {"room": "rear left bedroom", "wall": "rear", "count": 1},
            {"room": "rear middle bedroom", "wall": "rear", "count": 1},
            {"room": "rear right bedroom", "wall": "rear", "count": 1},
        ],
        "furniture": furniture,
        "selectedAssets": assets,
        "validationFailures": failures,
        "rules": [
            "Do not place any bed, bedframe, mattress, or pillow in the front living/dining/kitchen zone.",
            "Do not paste a door panel over a doorway; every doorway must have an actual wall gap.",
            "The front door must open to foyer/hall, not directly into a bedroom.",
            "Every bedroom must include a real downloaded bed frame, mattress, and pillow asset.",
            "The bathroom must be a separate room reachable from the hall.",
            "If a tagged prefab is missing, report it instead of replacing it with a block prop.",
        ],
    }


def write_project(blueprint: dict[str, Any]) -> None:
    PROJECT_ROOT.mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "blueprint.json").write_text(json.dumps(blueprint, indent=2), encoding="utf-8")

    lines = [
        "# Neighbor 3-Bed House Blueprint",
        "",
        f"Generated: {blueprint['generatedAt']}",
        f"Status: {blueprint['status']}",
        f"Spawn allowed: {blueprint['spawnAllowed']}",
        "",
        "## Rooms",
        "",
    ]
    for item in blueprint["rooms"]:
        lines.append(
            f"- {item['name']} ({item['kind']}): x {item['xMin']}..{item['xMax']}, z {item['zMin']}..{item['zMax']}, size {item['size']['width']} x {item['size']['depth']}"
        )
    lines.extend(["", "## Doors", ""])
    for item in blueprint["doors"]:
        lines.append(f"- {item['name']}: connects {' / '.join(item['connects'])} at x {item['x']}, z {item['z']}")
    lines.extend(["", "## Selected Assets", ""])
    for item in blueprint["selectedAssets"]:
        if item["status"] == "selected":
            lines.append(f"- {item['role']}: `{item['sourceFile']}` node `{item.get('nodeName')}`")
        else:
            lines.append(f"- {item['role']}: MISSING")
    lines.extend(["", "## Validation", ""])
    if blueprint["validationFailures"]:
        lines.extend(f"- FAIL: {failure}" for failure in blueprint["validationFailures"])
    else:
        lines.append("- PASS: blueprint has coherent public/private zones, exactly three rear bedrooms, a separate hall bathroom, a front living room, a front dining room, a kitchen, and required real bed/couch/bookshelf/dining/toilet assets.")
    lines.extend(["", "## Rules", ""])
    lines.extend(f"- {rule}" for rule in blueprint["rules"])
    (PROJECT_ROOT / "blueprint.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    lib = load_library()
    blueprint = build_blueprint(lib)
    write_project(blueprint)
    print(json.dumps({"project": str(PROJECT_ROOT), "status": blueprint["status"], "spawnAllowed": blueprint["spawnAllowed"]}, indent=2))
    return 0 if blueprint["spawnAllowed"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
