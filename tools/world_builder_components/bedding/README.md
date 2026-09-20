# Experimental bedding contact components

These four modules are the installed engineering implementation, published as a self-contained CPU component subset. They provide a procedural cloth grid, a fixed-bottom mattress height field, top-surface contact, and discrete triangle-versus-convex bed-frame contact. They do not require model weights, personal data, a browser, or a GPU for the regression checks below.

From the repository root, with Node.js installed:

```text
node Testing/test_bedding_frame_contacts.mjs
```

The 13 small regression cases check chamfer geometry, triangle-interior intersection, prior-side selection, pinned points, finite contact boundaries, and velocity/friction bookkeeping. The fixture is procedural geometry. A passing result establishes those isolated cases only.

The full bedding simulation remains experimental. These checks do not establish continuous collision detection, cloth self-collision, arbitrary initial-overlap recovery, calibrated foam behavior, two-way cloth/mattress coupling, full-body behavior, visual realism, or a finished World Builder. Later coupled release tests still have unresolved frame-overlap and stability problems. The unpublished diagnostic response prototypes are not installed here.

The workstation's native preview wrapper depends on additional local services and vendor setup and is deliberately outside this portable component release. No native-preview launch or full-world acceptance is implied. Original source files are preserved unchanged; only the public smoke-test imports and result reporting use repository-relative paths.
