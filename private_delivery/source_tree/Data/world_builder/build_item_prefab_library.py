#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import struct
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
STAGED_ROOT = ROOT / "staged_assets_for_world_builder"
OUT_ROOT = ROOT / "item_prefab_library"
PREFAB_ROOT = OUT_ROOT / "prefabs"


TAG_RULES: list[tuple[str, list[str]]] = [
    ("hook", ["robe hook", "coat hook", "wall hook", "wall hooks", "clothes hook", "garment hook", "hook", "hooks", "peg"]),
    ("towel_rack", ["towel rack", "towel bar", "towel rail", "towel holder"]),
    ("robe", ["bathrobe", "bath robe", "dressing gown", "robe"]),
    ("clothing", ["clothing", "clothes", "garment", "apparel", "outfit"]),
    ("laundry", ["laundry", "hamper", "clothes basket", "washing machine", "washer", "dryer"]),
    ("closet", ["walk in closet", "walk-in closet", "closet", "wardrobe", "clothes cabinet"]),
    ("shelf", ["wall shelf", "linen shelf", "closet shelf", "shelf", "shelving"]),
    ("placement_surface", ["placement surface", "putdown surface", "put down surface"]),
    ("bookshelf", ["bookshelf", "book shelf", "book_shelf", "bookcase", "book case", "rak buku", "shelf", "shelving"]),
    ("book", ["book", "books", "notebook", "journal", "magazine", "pages", "paperback"]),
    ("couch", ["couch", "sofa", "loveseat", "sectional", "settee"]),
    ("stool", ["stool", "bar stool", "counter stool"]),
    ("dining_chair", ["dining chair", "diningchair"]),
    ("chair", ["chair", "stool", "armchair", "seat", "seating", "bench"]),
    ("bed_frame", ["bed frame", "bedframe", "headboard", "footboard", "bed post", "bed_post"]),
    ("bed", ["bed", "mattress", "pillow", "blanket", "duvet", "headboard", "bedding"]),
    ("mattress", ["mattress", "matress", "duvet", "blanket", "bedding"]),
    ("pillow", ["pillow", "bed pillow"]),
    ("coffee_table", ["coffee table", "coffeetable"]),
    ("dining_table", ["dining table", "diningtable"]),
    ("table", ["table", "coffee table", "dining table", "dining", "countertop", "counter"]),
    ("desk", ["desk", "computer table", "writing table", "workstation"]),
    ("door", ["door", "entry door", "sidelight", "sliding door", "simplydoor", "door panel", "door_panel"]),
    ("window", ["window", "glass pane", "sash", "mullion", "transom"]),
    ("cabinet", ["cabinet", "wardrobe", "drawer", "dresser", "closet", "cupboard"]),
    ("refrigerator", ["fridge", "refrigerator", "freezer"]),
    ("stove", ["stove", "oven", "cooktop", "burner", "range"]),
    ("microwave", ["microwave"]),
    ("appliance", ["fridge", "refrigerator", "stove", "oven", "microwave", "washer", "dryer"]),
    ("sink", ["sink", "faucet", "washbasin", "basin"]),
    ("toilet", ["toilet", "wc"]),
    ("bathtub", ["bathtub", "bath tub", "tub"]),
    ("shower", ["shower"]),
    ("bathroom_fixture", ["toilet", "sink", "bathtub", "bath", "shower", "vanity", "faucet"]),
    ("tv", ["tv", "television", "screen", "monitor"]),
    ("computer", ["computer", "laptop", "keyboard", "mouse", "monitor", "pc"]),
    ("phone", ["phone", "cell phone", "mobile phone", "smartphone"]),
    ("light", ["lamp", "light", "sconce", "chandelier", "pendant"]),
    ("stairs", ["stair", "stairs", "railing", "banister"]),
    ("wall", ["wall", "brick", "stone wall", "panel", "partition"]),
    ("floor", ["floor", "tile", "carpet", "rug", "wood floor"]),
    ("roof", ["roof", "ceiling", "gable"]),
    ("house_shell", ["house", "home", "apartment", "building", "room", "layout", "terrace"]),
    ("corridor", ["corridor", "hallway", "hall", "passage"]),
    ("bridge", ["bridge", "enterprise", "voyager", "runabout", "delta flyer", "star trek"]),
    ("vehicle", ["car", "shuttle", "runabout", "flyer", "vehicle", "tardis"]),
    ("plant", ["plant", "tree", "grass", "shrub", "bush", "flower"]),
]

TAG_PRIORITY = [
    "hook",
    "towel_rack",
    "robe",
    "clothing",
    "laundry",
    "closet",
    "door",
    "pillow",
    "mattress",
    "bed_frame",
    "bed",
    "couch",
    "stool",
    "dining_chair",
    "chair",
    "bookshelf",
    "shelf",
    "book",
    "coffee_table",
    "dining_table",
    "table",
    "desk",
    "cabinet",
    "refrigerator",
    "stove",
    "microwave",
    "appliance",
    "sink",
    "toilet",
    "bathtub",
    "shower",
    "bathroom_fixture",
    "tv",
    "computer",
    "phone",
    "window",
    "light",
    "stairs",
    "wall",
    "floor",
    "roof",
    "house_shell",
    "corridor",
    "bridge",
    "vehicle",
    "plant",
    "placement_surface",
]

BAD_SINGLETON_TAGS = {"wall", "floor", "roof", "house_shell", "corridor", "bridge"}
COMPONENT_TAGS = [
    "hook",
    "towel_rack",
    "robe",
    "clothing",
    "laundry",
    "closet",
    "shelf",
    "placement_surface",
    "door",
    "window",
    "bed",
    "bed_frame",
    "mattress",
    "pillow",
    "couch",
    "chair",
    "stool",
    "dining_chair",
    "table",
    "coffee_table",
    "dining_table",
    "desk",
    "bookshelf",
    "book",
    "cabinet",
    "refrigerator",
    "stove",
    "microwave",
    "sink",
    "toilet",
    "bathtub",
    "shower",
    "tv",
    "computer",
    "phone",
    "light",
    "stairs",
    "wall",
    "floor",
    "roof",
    "house_shell",
    "corridor",
    "bridge",
    "vehicle",
    "plant",
]
STRUCTURE_TAGS = {"house_shell", "wall", "floor", "roof", "door", "window", "stairs", "corridor", "bridge"}
FINISHED_HOME_REQUIRED_TAGS = [
    "door",
    "window",
    "couch",
    "chair",
    "table",
    "bed",
    "mattress",
    "pillow",
    "refrigerator",
    "stove",
    "sink",
    "toilet",
]

FUNCTIONAL_TAGS = frozenset(
    {
        "hook",
        "towel_rack",
        "clothing",
        "robe",
        "laundry",
        "closet",
        "shelf",
        "placement_surface",
    }
)
PLACEMENT_SURFACE_SOURCE_TAGS = frozenset(
    {
        "bed",
        "coffee_table",
        "desk",
        "dining_table",
        "floor",
        "mattress",
        "shelf",
        "table",
    }
)
ANCHOR_NAME_RULES: dict[str, tuple[str, ...]] = {
    "hang_point": ("hang_point", "hangpoint", "hook_anchor", "garment_anchor"),
    "hook_loop": ("hook_loop", "robe_hook_loop", "hanger_loop"),
    "towel_drape_line": ("towel_drape_line", "drape_line", "towel_bar_anchor", "rack_contact_band"),
    "placement_surface": ("placement_surface", "putdown_surface", "place_surface"),
    "container_drop_zone": ("container_drop_zone", "basket_anchor", "laundry_basket_anchor"),
    "grip_point": ("grip_point", "grippoint", "grab_point", "handle_anchor", "collar_grip"),
    "left_sleeve_portal": ("left_sleeve_portal", "sleeve_portal_l", "left_arm_hole", "left_sleeve_opening"),
    "right_sleeve_portal": ("right_sleeve_portal", "sleeve_portal_r", "right_arm_hole", "right_sleeve_opening"),
    "left_belt_end": ("left_belt_end", "belt_left_end", "belt_end_l"),
    "right_belt_end": ("right_belt_end", "belt_right_end", "belt_end_r"),
}
FUNCTIONAL_CONTRACTS: dict[str, dict[str, list[str]]] = {
    "hook": {
        "capabilities": ["hang_garment", "remove_hung_garment"],
        "requiredAnchors": ["hang_point"],
        "states": ["empty", "occupied"],
        "evidence": ["same_object_continuity", "hand_contact", "source_removal_after_pickup"],
    },
    "towel_rack": {
        "capabilities": ["hang_towel", "remove_towel"],
        "requiredAnchors": ["towel_drape_line"],
        "states": ["empty", "occupied"],
        "evidence": ["same_object_continuity", "support_contact", "source_removal_after_pickup"],
    },
    "clothing": {
        "capabilities": ["pick_up", "put_down", "store", "retrieve"],
        "requiredAnchors": ["grip_point"],
        "states": ["stored", "world", "held", "worn"],
        "evidence": ["same_object_continuity", "hand_contact", "no_duplicate_instances"],
    },
    "robe": {
        "capabilities": ["pick_up", "put_down", "hang", "dress", "remove"],
        "requiredAnchors": [
            "grip_point",
            "hook_loop",
            "left_sleeve_portal",
            "right_sleeve_portal",
            "left_belt_end",
            "right_belt_end",
        ],
        "states": ["stored", "world", "held", "worn_open", "worn_tied"],
        "evidence": [
            "same_object_continuity",
            "both_sleeve_passages",
            "belt_end_hand_contact",
            "body_and_rig_compatibility",
            "no_duplicate_instances",
        ],
    },
    "laundry": {
        "capabilities": ["store_dirty_clothing", "retrieve_clothing"],
        "requiredAnchors": ["container_drop_zone"],
        "states": ["empty", "contains_items"],
        "evidence": ["same_object_continuity", "container_or_surface_contact"],
    },
    "closet": {
        "capabilities": ["store_clothing", "retrieve_clothing", "hang_clothing"],
        "requiredAnchors": ["placement_surface"],
        "states": ["open", "closed"],
        "evidence": ["reachable_approach", "hand_contact", "same_object_continuity"],
    },
    "shelf": {
        "capabilities": ["place_object", "retrieve_object"],
        "requiredAnchors": ["placement_surface"],
        "states": ["available", "occupied"],
        "evidence": ["support_contact", "same_object_continuity"],
    },
    "placement_surface": {
        "capabilities": ["place_object", "retrieve_object"],
        "requiredAnchors": ["placement_surface"],
        "states": ["available", "occupied"],
        "evidence": ["support_contact", "release_before_settle", "same_object_continuity"],
    },
}


def slugify(value: str, fallback: str = "item") -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return text[:96] or fallback


def read_gltf_json(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".gltf":
        return json.loads(path.read_text(encoding="utf-8"))
    # GLB binary buffers may be hundreds of megabytes.  Stream past them so a
    # metadata refresh does not temporarily duplicate every model in RAM.
    with path.open("rb") as handle:
        header = handle.read(12)
        if len(header) != 12 or header[:4] != b"glTF":
            raise ValueError("not a GLB file")
        _magic, _version, total_length = struct.unpack("<4sII", header)
        consumed = 12
        while consumed + 8 <= total_length:
            chunk_header = handle.read(8)
            if len(chunk_header) != 8:
                break
            chunk_len, chunk_type = struct.unpack("<II", chunk_header)
            consumed += 8
            if chunk_type == 0x4E4F534A:
                chunk = handle.read(chunk_len)
                if len(chunk) != chunk_len:
                    raise ValueError("truncated GLB JSON chunk")
                return json.loads(chunk.rstrip(b"\x00 ").decode("utf-8"))
            handle.seek(chunk_len, 1)
            consumed += chunk_len
    raise ValueError("GLB JSON chunk was not found")


def source_id_for(path: Path) -> str:
    # Identity follows bytes, not path+size.  A same-size replacement must not
    # silently retain a prefab/source ID.  Stream so multi-gigabyte model packs
    # do not compete with Kira for RAM during indexing.
    return _content_bound_source_id(path, source_sha256(path))


def _content_bound_source_id(path: Path, content_sha256: str) -> str:
    try:
        identity_path = path.resolve().relative_to(ROOT.resolve()).as_posix().lower()
    except ValueError:
        identity_path = path.resolve().as_posix().lower()
    seed = f"{identity_path}|sha256:{content_sha256}".encode("utf-8")
    return hashlib.sha256(seed).hexdigest()[:16]


def source_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tag_text(text: str) -> dict[str, int]:
    lower = text.lower().replace("-", " ").replace("_", " ")
    scores: dict[str, int] = {}
    for tag, needles in TAG_RULES:
        score = 0
        for needle in needles:
            normalized = needle.lower().replace("_", " ")
            if " " in normalized:
                pattern = r"(?<![a-z0-9])" + r"\s+".join(re.escape(part) for part in normalized.split()) + r"(?![a-z0-9])"
            else:
                pattern = r"(?<![a-z0-9])" + re.escape(normalized) + r"(?![a-z0-9])"
            if re.search(pattern, lower):
                score += 3 if " " in normalized else 2
        if score:
            scores[tag] = score
    return scores


def material_names_for_mesh(gltf: dict[str, Any], mesh_index: int | None) -> list[str]:
    if mesh_index is None:
        return []
    meshes = gltf.get("meshes") or []
    materials = gltf.get("materials") or []
    if mesh_index < 0 or mesh_index >= len(meshes):
        return []
    names: list[str] = []
    for primitive in meshes[mesh_index].get("primitives") or []:
        mat_index = primitive.get("material")
        if isinstance(mat_index, int) and 0 <= mat_index < len(materials):
            names.append(str(materials[mat_index].get("name") or f"material_{mat_index}"))
    return sorted(set(names))


def mesh_bounds(gltf: dict[str, Any], mesh_index: int | None) -> dict[str, float] | None:
    if mesh_index is None:
        return None
    meshes = gltf.get("meshes") or []
    accessors = gltf.get("accessors") or []
    if mesh_index < 0 or mesh_index >= len(meshes):
        return None
    mins: list[list[float]] = []
    maxs: list[list[float]] = []
    for primitive in meshes[mesh_index].get("primitives") or []:
        accessor_index = (primitive.get("attributes") or {}).get("POSITION")
        if not isinstance(accessor_index, int) or accessor_index < 0 or accessor_index >= len(accessors):
            continue
        accessor = accessors[accessor_index]
        if isinstance(accessor.get("min"), list) and isinstance(accessor.get("max"), list):
            mins.append([float(v) for v in accessor["min"][:3]])
            maxs.append([float(v) for v in accessor["max"][:3]])
    if not mins:
        return None
    low = [min(values[i] for values in mins) for i in range(3)]
    high = [max(values[i] for values in maxs) for i in range(3)]
    return {
        "x": round(high[0] - low[0], 4),
        "y": round(high[1] - low[1], 4),
        "z": round(high[2] - low[2], 4),
    }


def build_parent_map(nodes: list[dict[str, Any]]) -> dict[int, int]:
    parents: dict[int, int] = {}
    for index, node in enumerate(nodes):
        for child in node.get("children") or []:
            if isinstance(child, int):
                parents[child] = index
    return parents


def ancestor_names(nodes: list[dict[str, Any]], parents: dict[int, int], index: int) -> list[str]:
    names: list[str] = []
    current = parents.get(index)
    while current is not None:
        names.append(str(nodes[current].get("name") or f"node_{current}"))
        current = parents.get(current)
    return list(reversed(names))


def descendant_mesh_count(nodes: list[dict[str, Any]], index: int) -> int:
    node = nodes[index]
    count = 1 if isinstance(node.get("mesh"), int) else 0
    for child in node.get("children") or []:
        if isinstance(child, int) and 0 <= child < len(nodes):
            count += descendant_mesh_count(nodes, child)
    return count


def source_text(path: Path, gltf: dict[str, Any]) -> str:
    scene_names = " ".join(str(scene.get("name") or "") for scene in gltf.get("scenes") or [])
    return f"{path.name} {path.parent.as_posix()} {scene_names}"


def confidence_for(node_scores: dict[str, int], source_scores: dict[str, int], direct_named: bool, mesh_count: int) -> str:
    best = max([0, *node_scores.values()])
    source_best = max([0, *source_scores.values()])
    if direct_named and best >= 3:
        return "high"
    if direct_named or best >= 2 or (source_best and mesh_count > 1):
        return "medium"
    return "low"


def primary_tag(tags: list[str]) -> str:
    return tags[0] if tags else "misc"


def add_derived_functional_tags(tags: list[str]) -> list[str]:
    """Add semantic capabilities without claiming that behavior is proved."""
    expanded = set(tags)
    if "robe" in expanded:
        expanded.add("clothing")
    if expanded & PLACEMENT_SURFACE_SOURCE_TAGS:
        expanded.add("placement_surface")
    return sorted(
        expanded,
        key=lambda tag: (TAG_PRIORITY.index(tag) if tag in TAG_PRIORITY else 999, tag),
    )


def _subtree_indices(nodes: list[dict[str, Any]], root_index: int | None) -> list[int]:
    if root_index is None:
        return list(range(len(nodes)))
    pending = [root_index]
    seen: set[int] = set()
    while pending:
        index = pending.pop()
        if index in seen or index < 0 or index >= len(nodes):
            continue
        seen.add(index)
        pending.extend(
            child
            for child in nodes[index].get("children") or []
            if isinstance(child, int)
        )
    return sorted(seen)


def detect_interaction_anchors(
    nodes: list[dict[str, Any]],
    root_index: int | None,
) -> list[dict[str, Any]]:
    detected: list[dict[str, Any]] = []
    for index in _subtree_indices(nodes, root_index):
        node_name = str(nodes[index].get("name") or f"node_{index}")
        normalized = slugify(node_name)
        for role, aliases in ANCHOR_NAME_RULES.items():
            if normalized == role or any(alias in normalized for alias in aliases):
                detected.append(
                    {
                        "role": role,
                        "nodeIndex": index,
                        "nodeName": node_name,
                        "status": "named_anchor_detected_geometry_unverified",
                    }
                )
                break
    return detected


def build_functional_prefab_metadata(
    tags: list[str],
    nodes: list[dict[str, Any]],
    root_index: int | None,
) -> dict[str, Any]:
    """Build a fail-closed interaction contract for clothing-related prefabs."""
    enriched_tags = add_derived_functional_tags(tags)
    functional_tags = [tag for tag in enriched_tags if tag in FUNCTIONAL_TAGS]
    if not functional_tags:
        return {
            "functionalTags": [],
            "functionalMetadata": None,
            "interactionManifest": None,
        }

    capabilities: list[str] = []
    required_anchors: list[str] = []
    states: list[str] = []
    evidence: list[str] = []
    for tag in functional_tags:
        contract = FUNCTIONAL_CONTRACTS[tag]
        capabilities.extend(contract["capabilities"])
        required_anchors.extend(contract["requiredAnchors"])
        states.extend(contract["states"])
        evidence.extend(contract["evidence"])

    capabilities = list(dict.fromkeys(capabilities))
    required_anchors = list(dict.fromkeys(required_anchors))
    states = list(dict.fromkeys(states))
    evidence = list(dict.fromkeys(evidence))
    detected = detect_interaction_anchors(nodes, root_index)
    detected_roles = {anchor["role"] for anchor in detected}
    missing = [role for role in required_anchors if role not in detected_roles]

    interaction_manifest = {
        "schemaVersion": 1,
        "status": (
            "anchors_named_behavior_evidence_required"
            if not missing
            else "missing_required_named_anchors"
        ),
        "capabilities": [
            {"id": capability, "status": "declared_unverified"}
            for capability in capabilities
        ],
        "requiredAnchors": required_anchors,
        "detectedAnchors": detected,
        "missingRequiredAnchors": missing,
        "stateModel": {
            "states": states,
            "persistentObjectIdRequired": True,
            "sameObjectContinuityRequired": True,
            "duplicationAllowed": False,
        },
        "evidenceRequirements": evidence,
        "runtimeReady": False,
        "runtimeReadyReason": "metadata_and_named_anchors_are_not_physical_interaction_evidence",
    }
    return {
        "functionalTags": functional_tags,
        "functionalMetadata": {
            "schemaVersion": 1,
            "primaryFunctionalTag": functional_tags[0],
            "isPlacementSurface": "placement_surface" in functional_tags,
            "isWearableWorldObject": bool({"clothing", "robe"} & set(functional_tags)),
            "persistentObjectIdRequired": True,
            "authoringStatus": interaction_manifest["status"],
        },
        "interactionManifest": interaction_manifest,
    }


def component_quality_score(prefab: dict[str, Any], desired_tag: str | None = None) -> tuple[int, int, int, int, str]:
    confidence = {"high": 0, "medium": 1, "low": 2}.get(str(prefab.get("confidence")), 3)
    kind_penalty = 0 if prefab.get("kind") == "node_prefab" else 2
    tag_penalty = 0 if desired_tag and primary_tag(prefab.get("tags") or []) == desired_tag else 1
    mesh_count = int(prefab.get("meshCount") or 0)
    mesh_penalty = 0 if 1 <= mesh_count <= 24 else 1 if mesh_count <= 80 else 2
    name = str(prefab.get("nodeName") or prefab.get("sourceFile") or "").lower()
    vague_name_penalty = 1 if re.fullmatch(r"(object|cube|mesh|node)[_\-\s]?\d*", name) else 0
    return (confidence, kind_penalty, tag_penalty, mesh_penalty + vague_name_penalty, name)


def component_summary(prefab: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": prefab.get("id"),
        "kind": prefab.get("kind"),
        "source": prefab.get("source"),
        "sourceFile": prefab.get("sourceFile"),
        "nodeIndex": prefab.get("nodeIndex"),
        "nodeName": prefab.get("nodeName"),
        "meshCount": prefab.get("meshCount"),
        "tags": prefab.get("tags"),
        "confidence": prefab.get("confidence"),
        "approxMeshBounds": prefab.get("approxMeshBounds"),
        "materialNames": prefab.get("materialNames", [])[:12],
        "functionalTags": prefab.get("functionalTags", []),
        "functionalMetadata": prefab.get("functionalMetadata"),
        "interactionManifest": prefab.get("interactionManifest"),
        "selection": prefab.get("selection"),
    }


def build_prefabs_for_source(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    gltf = read_gltf_json(path)
    nodes = gltf.get("nodes") or []
    meshes = gltf.get("meshes") or []
    source_scores = tag_text(source_text(path, gltf))
    parents = build_parent_map(nodes)
    source_digest = source_sha256(path)
    sid = _content_bound_source_id(path, source_digest)
    rel = path.relative_to(ROOT).as_posix()

    prefabs: list[dict[str, Any]] = []

    if source_scores and meshes:
        source_tags = add_derived_functional_tags(
            sorted(source_scores, key=lambda tag: (TAG_PRIORITY.index(tag) if tag in TAG_PRIORITY else 999, tag))
        )
        functional = build_functional_prefab_metadata(source_tags, nodes, None)
        prefabs.append(
            {
                "id": f"{sid}_source_bundle",
                "kind": "source_bundle",
                "source": rel,
                "sourceFile": path.name,
                "nodeIndex": None,
                "nodeName": None,
                "nodePath": [],
                "meshIndex": None,
                "meshCount": len(meshes),
                "tags": source_tags,
                "primaryTag": primary_tag(source_tags),
                "reuseMode": "whole_source_bundle",
                "componentRole": "source_bundle_fallback",
                "confidence": "medium",
                "selection": "Load the source model and use as a whole asset bundle only when no better node-level prefab exists.",
                "notes": "Whole-model bundle inferred from filename/path tags.",
                **functional,
            }
        )

    for index, node in enumerate(nodes):
        mesh_index = node.get("mesh") if isinstance(node.get("mesh"), int) else None
        mesh_count = descendant_mesh_count(nodes, index)
        if mesh_count == 0:
            continue
        node_name = str(node.get("name") or f"node_{index}")
        mesh_name = ""
        if isinstance(mesh_index, int) and 0 <= mesh_index < len(meshes):
            mesh_name = str(meshes[mesh_index].get("name") or "")
        mats = material_names_for_mesh(gltf, mesh_index)
        path_names = ancestor_names(nodes, parents, index) + [node_name]
        direct_text = " ".join([node_name, mesh_name, *mats])
        context_text = " ".join([path.name, str(path.parent), *path_names, mesh_name, *mats])
        node_scores = tag_text(direct_text)
        context_scores = tag_text(context_text)
        combined_scores = dict(source_scores)
        combined_scores.update({tag: combined_scores.get(tag, 0) + score for tag, score in context_scores.items()})

        direct_named = bool(node_scores)
        if not combined_scores:
            continue
        if not direct_named and mesh_count == 1 and set(combined_scores).issubset(BAD_SINGLETON_TAGS):
            continue

        tags = add_derived_functional_tags(
            sorted(combined_scores, key=lambda tag: (TAG_PRIORITY.index(tag) if tag in TAG_PRIORITY else 999, tag))
        )
        label = node_name if node_name and not node_name.startswith("node_") else path.stem
        confidence = confidence_for(node_scores, source_scores, direct_named, mesh_count)
        prefab_id = f"{sid}_{index:04d}_{slugify(label)}"
        functional = build_functional_prefab_metadata(tags, nodes, index)
        prefabs.append(
            {
                "id": prefab_id,
                "kind": "node_prefab",
                "source": rel,
                "sourceFile": path.name,
                "nodeIndex": index,
                "nodeName": node_name,
                "nodePath": path_names,
                "meshIndex": mesh_index,
                "meshName": mesh_name or None,
                "meshCount": mesh_count,
                "materialNames": mats,
                "approxMeshBounds": mesh_bounds(gltf, mesh_index),
                "tags": tags,
                "primaryTag": primary_tag(tags),
                "reuseMode": "clone_node_subtree",
                "componentRole": "structure_part" if any(tag in STRUCTURE_TAGS for tag in tags) else "reusable_prop",
                "confidence": confidence,
                "selection": "Load source GLB/GLTF, clone this node subtree, then fit to the target world placement.",
                **functional,
            }
        )

    source_info = {
        "source": rel,
        "sourceFile": path.name,
        "sourceId": sid,
        "sourceSha256": source_digest,
        "sizeMB": round(path.stat().st_size / (1024 * 1024), 3),
        "nodeCount": len(nodes),
        "meshCount": len(meshes),
        "sourceTags": add_derived_functional_tags(sorted(source_scores)),
        "prefabCount": len(prefabs),
        "functionalPrefabCount": sum(1 for prefab in prefabs if prefab.get("functionalTags")),
    }
    return prefabs, source_info


def write_prefab_files(prefabs: list[dict[str, Any]]) -> None:
    if PREFAB_ROOT.exists():
        shutil.rmtree(PREFAB_ROOT)
    PREFAB_ROOT.mkdir(parents=True, exist_ok=True)
    for prefab in prefabs:
        primary = prefab["tags"][0] if prefab.get("tags") else "misc"
        folder = PREFAB_ROOT / primary
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"{prefab['id']}.json"
        target.write_text(json.dumps(prefab, indent=2), encoding="utf-8")


def write_supplemental_interaction_manifest(
    *,
    library_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Refresh interaction metadata without replacing any prefab descriptors.

    This reads the existing item library, enriches records in memory, and
    atomically writes only ``interaction_manifest_library.json``.  It never
    calls ``write_prefab_files`` and never copies, deletes, or rewrites model
    payloads or the source/component libraries.
    """
    library_path = library_path or OUT_ROOT / "item_prefab_library.json"
    output_path = output_path or OUT_ROOT / "interaction_manifest_library.json"
    library_path = Path(library_path)
    output_path = Path(output_path)
    same_resolved_path = library_path.resolve() == output_path.resolve()
    same_existing_file = False
    if library_path.exists() and output_path.exists():
        try:
            same_existing_file = os.path.samefile(library_path, output_path)
        except OSError:
            # The resolved-path check remains authoritative when platform
            # metadata races or does not support same-file checks.
            pass
    if same_resolved_path or same_existing_file:
        raise ValueError("source library and interaction-manifest output must be different files")

    library = json.loads(library_path.read_text(encoding="utf-8"))
    prefabs = library.get("prefabs") if isinstance(library, dict) else None
    if not isinstance(prefabs, list):
        raise ValueError("item prefab library is missing a prefabs list")

    source_cache: dict[str, dict[str, Any]] = {}
    records: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for prefab in prefabs:
        if not isinstance(prefab, dict):
            continue
        text_parts = [
            str(prefab.get("sourceFile") or ""),
            str(prefab.get("nodeName") or ""),
            " ".join(str(value) for value in prefab.get("nodePath") or []),
            " ".join(str(value) for value in prefab.get("materialNames") or []),
        ]
        inferred = tag_text(" ".join(text_parts))
        tags = add_derived_functional_tags(
            list(dict.fromkeys([*(prefab.get("tags") or []), *inferred.keys()]))
        )
        if not any(tag in FUNCTIONAL_TAGS for tag in tags):
            continue

        source_value = str(prefab.get("source") or "")
        cached = source_cache.get(source_value)
        if cached is None:
            source_path = Path(source_value)
            if not source_path.is_absolute():
                source_path = ROOT / source_path
            try:
                gltf = read_gltf_json(source_path)
                cached = {
                    "path": source_path,
                    "nodes": gltf.get("nodes") or [],
                    "sha256": source_sha256(source_path),
                    "error": None,
                }
            except Exception as exc:  # noqa: BLE001 - supplemental audit records every unreadable source.
                cached = {
                    "path": source_path,
                    "nodes": [],
                    "sha256": None,
                    "error": str(exc),
                }
                errors.append({"source": source_value, "error": str(exc)})
            source_cache[source_value] = cached

        node_index = prefab.get("nodeIndex")
        if not isinstance(node_index, int):
            node_index = None
        functional = build_functional_prefab_metadata(tags, cached["nodes"], node_index)
        records.append(
            {
                "prefabId": prefab.get("id"),
                "prefabIdSchema": "legacy_preserved_supplemental_only",
                "kind": prefab.get("kind"),
                "source": source_value,
                "sourceFile": prefab.get("sourceFile"),
                "sourceSha256": cached["sha256"],
                "contentSourceId": (
                    _content_bound_source_id(cached["path"], cached["sha256"])
                    if cached["sha256"]
                    else None
                ),
                "nodeIndex": prefab.get("nodeIndex"),
                "nodeName": prefab.get("nodeName"),
                "tags": tags,
                **functional,
                "sourceReadStatus": "passed" if cached["error"] is None else "failed",
                "runtimePayloadModified": False,
            }
        )

    generated_at = datetime.now(timezone.utc).isoformat()
    report = {
        "schemaVersion": 1,
        "generatedAt": generated_at,
        "generationMode": "non_destructive_supplemental_metadata_refresh",
        "sourceLibrary": str(library_path),
        "sourceLibrarySha256": source_sha256(library_path),
        "output": str(output_path),
        "prefabPayloadsCopied": False,
        "prefabDescriptorsRewritten": False,
        "itemPrefabLibraryRewritten": False,
        "componentLibraryRewritten": False,
        "prefabCount": len(records),
        "runtimeReadyCount": sum(
            1
            for record in records
            if (record.get("interactionManifest") or {}).get("runtimeReady") is True
        ),
        "sourceReadErrorCount": len(errors),
        "errors": errors,
        "hardRules": [
            "This file supplements legacy prefab IDs; it does not approve or mutate their runtime payloads.",
            "Named anchors are authoring hints, not physical interaction evidence.",
            "Persistent item identity and no-duplication rules apply across stored, held, worn, and placed states.",
            "runtimeReady stays false until separate physical evidence and Avatar Builder body/rig gates pass.",
        ],
        "prefabs": records,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        # A unique, exclusively created temporary file prevents concurrent
        # refreshes from sharing or deleting one another's staging payload.
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            dir=output_path.parent,
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            json.dump(report, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, output_path)
        temp_path = None
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass
    return report


def write_reports(prefabs: list[dict[str, Any]], sources: list[dict[str, Any]], errors: list[dict[str, str]]) -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).isoformat()
    by_tag: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for prefab in prefabs:
        for tag in prefab.get("tags") or ["untagged"]:
            by_tag[tag].append(prefab)

    library = {
        "generatedAt": generated_at,
        "stagedRoot": STAGED_ROOT.as_posix(),
        "prefabRoot": PREFAB_ROOT.as_posix(),
        "sourceCount": len(sources),
        "prefabCount": len(prefabs),
        "errorCount": len(errors),
        "tagCounts": dict(sorted(Counter(tag for prefab in prefabs for tag in prefab.get("tags", [])).items())),
        "sources": sources,
        "prefabs": prefabs,
        "errors": errors,
    }
    (OUT_ROOT / "item_prefab_library.json").write_text(json.dumps(library, indent=2), encoding="utf-8")

    functional_prefabs = [prefab for prefab in prefabs if prefab.get("functionalTags")]
    interaction_library = {
        "schemaVersion": 1,
        "generatedAt": generated_at,
        "purpose": (
            "Fail-closed interaction authoring contracts for clothing, robe, storage, "
            "hook, towel-rack, laundry, shelf, and placement-surface prefabs."
        ),
        "prefabCount": len(functional_prefabs),
        "runtimeReadyCount": sum(
            1
            for prefab in functional_prefabs
            if (prefab.get("interactionManifest") or {}).get("runtimeReady") is True
        ),
        "hardRules": [
            "Named anchors are authoring hints, not proof of hand contact, support, dressing, or collision.",
            "Every moved garment keeps one persistent object ID across stored, world, held, and worn states.",
            "A garment source instance is removed when picked up; duplicate robe or clothing instances fail the gate.",
            "World Builder owns placement/storage anchors; Avatar Builder owns body hash, rig fit, and worn deformation.",
            "runtimeReady remains false until physical evidence and exact wearable compatibility pass outside this indexer.",
        ],
        "prefabs": [
            {
                "id": prefab.get("id"),
                "source": prefab.get("source"),
                "nodeIndex": prefab.get("nodeIndex"),
                "nodeName": prefab.get("nodeName"),
                "functionalTags": prefab.get("functionalTags"),
                "functionalMetadata": prefab.get("functionalMetadata"),
                "interactionManifest": prefab.get("interactionManifest"),
            }
            for prefab in functional_prefabs
        ],
    }
    (OUT_ROOT / "interaction_manifest_library.json").write_text(
        json.dumps(interaction_library, indent=2),
        encoding="utf-8",
    )

    component_groups: dict[str, dict[str, Any]] = {}
    for tag in COMPONENT_TAGS:
        tagged = [prefab for prefab in by_tag.get(tag, []) if prefab.get("kind") == "node_prefab"]
        primary_matches = [prefab for prefab in tagged if primary_tag(prefab.get("tags") or []) == tag]
        secondary_matches = [prefab for prefab in tagged if primary_tag(prefab.get("tags") or []) != tag]
        recommended = sorted(primary_matches, key=lambda prefab: component_quality_score(prefab, tag))[:40]
        if len(recommended) < 40:
            recommended.extend(
                sorted(secondary_matches, key=lambda prefab: component_quality_score(prefab, tag))[: 40 - len(recommended)]
            )
        component_groups[tag] = {
            "count": len(tagged),
            "primaryCount": len(primary_matches),
            "highConfidenceCount": sum(1 for prefab in tagged if prefab.get("confidence") == "high"),
            "recommended": [component_summary(prefab) for prefab in recommended],
        }
    missing_finished_home_tags = [
        tag for tag in FINISHED_HOME_REQUIRED_TAGS if component_groups.get(tag, {}).get("count", 0) == 0
    ]
    available_finished_home_tags = [
        tag for tag in FINISHED_HOME_REQUIRED_TAGS if component_groups.get(tag, {}).get("count", 0) > 0
    ]

    component_library = {
        "generatedAt": generated_at,
        "purpose": "Reusable node-level parts for the world generator. Use these before any generated block geometry.",
        "sourceCount": len(sources),
        "prefabCount": len(prefabs),
        "componentTags": COMPONENT_TAGS,
        "finishedHomeRequiredTags": FINISHED_HOME_REQUIRED_TAGS,
        "availableFinishedHomeTags": available_finished_home_tags,
        "missingFinishedHomeTags": missing_finished_home_tags,
        "hardRules": [
            "Blueprint first, then select tagged components for each room and doorway.",
            "Prefer node_prefab records with reuseMode=clone_node_subtree. Whole source bundles are fallback only.",
            "Never generate block furniture when a matching component tag has a recommended prefab.",
            "A finished bedroom bed must use a bed or bed_frame plus mattress plus pillow/blanket component evidence.",
            "Doors and windows must use imported components and a separate runtime collider/swing/opening test.",
            "If missingFinishedHomeTags is non-empty, finished-home generation must fail or request assets; do not fill missing tags with blocks.",
            "If a required component is missing or fails validation, leave a gap and report the missing tag instead of faking it.",
            "Functional clothing/storage prefabs must carry interactionManifest metadata and remain runtimeReady=false until physical evidence passes.",
            "World Builder placement metadata never proves Avatar Builder body-hash or rig compatibility.",
        ],
        "groups": component_groups,
    }
    (OUT_ROOT / "component_library.json").write_text(json.dumps(component_library, indent=2), encoding="utf-8")

    lines = [
        "# World Generator Item Prefab Library",
        "",
        f"Generated: {generated_at}",
        f"Scanned source models: {len(sources)}",
        f"Tagged prefab records: {len(prefabs)}",
        f"Parse errors: {len(errors)}",
        "",
        "## Generator Rules",
        "",
        "- Use tagged node/source prefabs before making procedural boxes.",
        "- Break house/apartment/hallway/bridge packs into node-level component prefabs; do not place a whole bundled model when a tagged door, window, chair, table, TV, appliance, wall, or floor node can be cloned.",
        "- Doors must come from `door` prefabs unless a real imported door fails collision/swing testing; do not place decorative bars over walkable entries.",
        "- Beds must come from `bed` or `bed_frame` prefabs paired with `mattress` and `pillow`/`blanket` evidence when available; otherwise reject them for finished homes.",
        "- Bookshelves must come from `bookshelf` prefabs; books/notebooks use `book` prefabs or separate book props.",
        "- Kitchen objects must use specific tags (`refrigerator`, `stove`, `microwave`, `sink`, `cabinet`) before falling back to the broad `appliance` tag.",
        "- Room layouts must keep bedrooms out of front living/dining rooms, preserve a clear entry path, and pass a walk-in collision probe.",
        "- Hooks, towel racks, robes, clothing, laundry, closets, shelves, and placement surfaces must use fail-closed interaction manifests with named anchors and persistent object identity.",
        "- Named anchors do not make a prefab runtime-ready; hand/support/collision evidence and Avatar Builder body/rig compatibility remain separate gates.",
        f"- The generator should read `component_library.json` for recommended reusable parts before scanning the full prefab list.",
        "",
        "## Tag Counts",
        "",
    ]
    for tag, count in sorted(Counter(tag for prefab in prefabs for tag in prefab.get("tags", [])).items()):
        lines.append(f"- {tag}: {count}")

    for tag in TAG_PRIORITY:
        items = by_tag.get(tag, [])
        if not items:
            continue
        lines.extend(["", f"## {tag}", ""])
        for prefab in sorted(items, key=lambda p: (p.get("confidence") != "high", p.get("sourceFile", ""), p.get("nodeIndex") or -1))[:60]:
            node = prefab.get("nodeName") or "whole source"
            conf = prefab.get("confidence")
            src = prefab.get("source")
            bounds = prefab.get("approxMeshBounds")
            bounds_text = f", bounds={bounds}" if bounds else ""
            lines.append(f"- `{prefab['id']}` ({conf}) {node} from `{src}`{bounds_text}")
        if len(items) > 60:
            lines.append(f"- ... {len(items) - 60} more `{tag}` prefabs in JSON.")

    if errors:
        lines.extend(["", "## Parse Errors", ""])
        for error in errors[:40]:
            lines.append(f"- `{error['source']}`: {error['error']}")

    (OUT_ROOT / "item_prefab_library.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    rules = [
        "# World Generator Asset Selection Rules",
        "",
        "This file is the hard rule layer for generated homes and notebook worlds.",
        "",
        "1. Query `Data/world_builder/item_prefab_library/item_prefab_library.json` by tag before creating a block placeholder.",
        "2. Query `Data/world_builder/item_prefab_library/component_library.json` first for recommended reusable parts from house/apartment/hallway/bridge packs.",
        "3. For residential interiors, prefer these tags: `door`, `window`, `couch`, `chair`, `stool`, `dining_table`, `dining_chair`, `table`, `bookshelf`, `book`, `bed`, `bed_frame`, `mattress`, `pillow`, `cabinet`, `refrigerator`, `stove`, `microwave`, `sink`, `toilet`, `tv`, `computer`, `phone`, `light`.",
        "4. A generated house must fail validation if it has a bedroom bed in the front living/dining area, an unwalkable front entry, or a door/window covered by decorative wall strips.",
        "5. A generated bed is not acceptable unless the selected prefab or companion prefab includes mattress plus pillow/blanket evidence.",
        "6. Imported decorative doors are not enough: the runtime must add a matching open/close collider and prove the threshold is walkable when open.",
        "7. If `component_library.json` has `missingFinishedHomeTags`, do not build a finished home; report the missing tags or leave the objects out for review.",
        "8. If no acceptable real prefab exists for a required object, leave the room empty and report the missing asset instead of inventing a block object.",
        "9. Query `interaction_manifest_library.json` for hook/towel-rack/clothing/robe/laundry/closet/shelf/placement behavior contracts; do not infer successful interaction from a mesh name.",
        "10. Preserve one persistent object ID across storage, pickup, wearing, removal, throwing, and replacement; duplicate instances fail validation.",
        "",
        "Current library paths:",
        f"- Machine JSON: `{(OUT_ROOT / 'item_prefab_library.json').as_posix()}`",
        f"- Component JSON: `{(OUT_ROOT / 'component_library.json').as_posix()}`",
        f"- Interaction JSON: `{(OUT_ROOT / 'interaction_manifest_library.json').as_posix()}`",
        f"- Human report: `{(OUT_ROOT / 'item_prefab_library.md').as_posix()}`",
        f"- Per-prefab descriptors: `{PREFAB_ROOT.as_posix()}`",
    ]
    (OUT_ROOT / "world_generator_asset_rules.md").write_text("\n".join(rules) + "\n", encoding="utf-8")


def main() -> int:
    if not STAGED_ROOT.exists():
        raise SystemExit(f"Missing staged model root: {STAGED_ROOT}")
    paths = sorted([*STAGED_ROOT.rglob("*.glb"), *STAGED_ROOT.rglob("*.gltf")])
    all_prefabs: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for path in paths:
        try:
            prefabs, source_info = build_prefabs_for_source(path)
            all_prefabs.extend(prefabs)
            sources.append(source_info)
        except Exception as exc:  # noqa: BLE001 - report all bad model files for generator audits.
            errors.append({"source": path.relative_to(ROOT).as_posix(), "error": str(exc)})

    write_prefab_files(all_prefabs)
    write_reports(all_prefabs, sources, errors)
    print(
        json.dumps(
            {
                "sources": len(sources),
                "prefabs": len(all_prefabs),
                "errors": len(errors),
                "out": OUT_ROOT.as_posix(),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
