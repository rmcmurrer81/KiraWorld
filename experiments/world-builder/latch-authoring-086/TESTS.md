# Portable artificial geometry checks

From the repository root:

```sh
node --test experiments/world-builder/latch-authoring-086/tests/test_authoring.mjs
```

No download, browser, server, canvas, GPU, model or saved-world file is required. The tests reference the existing sibling `package-consumer-083/candidate/vendor/three` directory and its `door_metadata.mjs` validator. Retain those relative locations and the original vendor license when copying this experimental folder.

Eight checks cover exact part replacement; actual Three.js vertices within all-pose bounds across four orientations and17 visual samples; released hinge motion and analytic bounds; keeper channels and central passage; metadata ownership/tampering; old-contract rejection; pause/fault/disposal; and independent opposite hatches. Each observer is a synchronous double and every layout is explicitly artificial. They do not prove real walkthrough collision, occupied-swing admission, export/import parity, native appearance or pressure containment.

PORTABILITY.diff records only the relative test-import changes needed for this public repository layout. No test-body or production-source behavior was changed for publication.
