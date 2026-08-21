# World Generator Asset Selection Rules

This file is the hard rule layer for generated homes and notebook worlds.

1. Query `Data/world_builder/item_prefab_library/item_prefab_library.json` by tag before creating a block placeholder.
2. Query `Data/world_builder/item_prefab_library/component_library.json` first for recommended reusable parts from house/apartment/hallway/bridge packs.
3. For residential interiors, prefer these tags: `door`, `window`, `couch`, `chair`, `stool`, `dining_table`, `dining_chair`, `table`, `bookshelf`, `book`, `bed`, `bed_frame`, `mattress`, `pillow`, `cabinet`, `refrigerator`, `stove`, `microwave`, `sink`, `toilet`, `tv`, `computer`, `phone`, `light`.
4. A generated house must fail validation if it has a bedroom bed in the front living/dining area, an unwalkable front entry, or a door/window covered by decorative wall strips.
5. A generated bed is not acceptable unless the selected prefab or companion prefab includes mattress plus pillow/blanket evidence.
6. Imported decorative doors are not enough: the runtime must add a matching open/close collider and prove the threshold is walkable when open.
7. If `component_library.json` has `missingFinishedHomeTags`, do not build a finished home; report the missing tags or leave the objects out for review.
8. If no acceptable real prefab exists for a required object, leave the room empty and report the missing asset instead of inventing a block object.
9. Prefer curated material references from `Data/world_builder/favorite_material_references.json` before using flat generated colors. Robert specifically liked the Starbucks red brick exterior and wants it saved for future houses or storefronts.

Current library paths:
- Machine JSON: `Data/world_builder/item_prefab_library/item_prefab_library.json`
- Component JSON: `Data/world_builder/item_prefab_library/component_library.json`
- Human report: `Data/world_builder/item_prefab_library/item_prefab_library.md`
- Per-prefab descriptors: `Data/world_builder/item_prefab_library/prefabs`
