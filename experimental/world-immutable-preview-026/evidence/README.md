# World026 immutable preview compatibility — isolated, not installed

Updating the current renderer used to invalidate existing layout previews even though each preview already contained its own verified renderer copies. Updating the Python preview backend itself also invalidated old manifests. This candidate keeps saved previews at the renderer revision that created them while allowing future previews to use an updated engine.

Only `world_layout_preview.py` changes. The four copied renderer files are index.html, style.css, viewer.mjs and walk_controller.mjs. Their original engine files no longer have to contain the old bytes or remain present. The saved copies must still exist at the exact build paths and match the original recorded hash, byte count, MIME type and fixed eight-file allowlist. Recorded renderer source paths and pin structures are now explicitly checked. Manifest seals, content-derived build identifiers and optional expected manifest digests remain enforced.

Creator compatibility is explicit for the v1 manifest contract: the current backend or the exact previously installed backend (`2d5a27e7…`, 22,133 bytes). Unknown creator revisions or contracts fail closed. A later backend release must deliberately carry forward reviewed prior creator hashes. This is a compatibility list, not a signature or a trust claim about arbitrary manifests.

Geometry source and saved geometry, research packet, blueprint and research caches remain live and exact. Node's exact path and bytes, navigation, preflight and the live Three files also remain live and exact. Updating any of those dependencies still invalidates a preview pending a separately reviewed migration. No validation is skipped for them. The geometry validator, provenance validator, creation workflow and HTTP handler are unchanged.

Twenty-three isolated CPU tests passed. They build old previews with the actual prior backend, load the proposed backend into disposable engine directories, and exercise renderer updates, absent originals, changed/missing saved copies, source-pin changes, unsupported creators, allowlist/path/MIME changes, modified provenance, geometry mismatch, Node/nav/preflight/Three changes, expected manifest hashing and content-addressed reuse. One test runs the unchanged real Node preflight; other tests use explicitly inert Node/Three fixtures and fake preflight responses to test pin behavior. They are not visual or physics-quality tests.

The existing saved Mars preview was additionally checked without changing it or the installed code. That check evaluates the candidate at the canonical module location and substitutes only its proposed backend self-binding; all real asset, Node and provenance checks remain unchanged. The result is a read-only compatibility simulation, not an installation or UI pass.

World024 owns the separate door renderer changes. This candidate edits none of its four frontend files. Existing previews deliberately keep their old rendering and behavior; creating a new preview after a renderer update gives a distinct build and leaves old assets unchanged.

Root should review DELIVERY.json and CHANGES.patch before any guarded installation. Preserve owner data, canonical preimages and historical manifests. There is no installer or model launch in this candidate.
