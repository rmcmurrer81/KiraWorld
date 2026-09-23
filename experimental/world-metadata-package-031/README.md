# Verified metadata package prototype031

This uninstalled CLI verifies actual bytes of explicitly selected saved geometry,
blueprint, research packet and referenced local research caches. It then uses the
exact pinned030 core to produce a portable three-file metadata package:
`scene.json`, `manifest.json` and `README.txt`. It performs CPU work only.

The source geometry must match the raw research-packet digest and the canonical
blueprint digest; the blueprint must bind the same research packet. Cache bindings
are checked inside the packet folder. Producer/source bytes are checked again
after projection and before creating output. The package records role/digest/size
proof without copying source documents, research text, personal memory fields,
media or absolute source paths. Source labels containing absolute paths are held.
Byte verification is not factual, visual, physics or owner approval.

Inputs can be an existing `isolated_world_layout_preview_v1` manifest or a small
`world_scene_export_input_bindings_v1` JSON object with an `inputs` map containing
`geometry_source`, `blueprint` and `research_packet`. Each row needs `path`, `bytes`
and `sha256`; paths in this local input file are explicit absolute file paths.
The existing-preview route verifies its seal and selected source chain. It does
not render, reopen or certify that preview's runtime assets. Both routes require
the caller's exact SHA256 of the input manifest.

Example commands from this directory, with reviewed input/output values:

```text
python -B package_writer.py build --bindings SOURCE_BINDINGS_JSON --bindings-sha256 EXACT_SHA256 --scene-id scene_name --output NEW_FOLDER
python -B package_writer.py verify --package NEW_FOLDER
python -B test_package.py
python -B make_example.py --destination NEW_SYNTHETIC_EXAMPLE_FOLDER
```

The default core is sibling `../world-scene-metadata-030`; `--core-root` can select
another copy only when all four030 code hashes match `CORE-PINS.json`. Node is
found on PATH, or selected with `--node`. No installed Kira path is assumed.
The writer refuses every existing output folder, including empty ones and source
folders. Output writes are exclusive, and the manifest is written last. An I/O
failure may retain a partial new folder; a retry will not overwrite it.

Fifteen tests cover actual byte/semantic digest checks, source and manifest
tampering, missing/malformed bindings, cache traversal, missing/tampered output,
producer changes, concurrent source changes, two byte-identical output packages,
source-free verification after relocation, and real CLI build/verify. All test
inputs are synthetic. Tests require only Python/Node plus the sibling030 closure;
there is no network, GPU, visual tool or model job.

This remains a metadata prototype. It exports no equipment meshes, materials,
engine adapter or VR runtime and adds no native export control. Sources and owner
worlds remain unchanged. The self-contained package can verify its own integrity
without original files, but it does not embed those files or prove source truth.

Root also exercised the writer on actual saved Mars bindings. `actual-mars-001/` is the reviewed derived metadata package:7 rooms,141 nodes,134 colliders,6 doors. All116 protected original source bindings stayed unchanged. Its labels were checked as habitat-room names; local paths, original research documents, raw geometry files and personal memory/media are absent. This is derived layout metadata, not a rendered/mesh world or visual approval. `evidence/ROOT-ACTUAL-PACKAGE-REVIEW.json` records that review.
