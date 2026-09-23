# World026 immutable preview compatibility recovery

This isolated, uninstalled candidate allows the four immutable renderer copies in a saved v1 preview to outlive updates to their original engine files. It explicitly recognizes the previously installed creator hash; unknown creator revisions fail closed. Geometry, source research, blueprint/cache files, Node, navigation/preflight and live Three integrity remain enforced. It does not upgrade the old preview's appearance or grant visual approval.

Candidate and baseline backend bytes are exact. Historical23-test results, diff and the read-only saved-Mars compatibility simulation are under evidence/. No owner geometry, original media, model data, current project state or generated preview is included. Setup/check source in evidence/ has historical local paths redacted and is not a ready-to-run owner-project operation.

Run `python -B test_compatibility.py` from this directory with Python3.10+ and Node.js available on PATH, or set WORLD_PREVIEW_NODE to the Node executable. It uses included synthetic geometry and the exact published-base dependencies in support/engine, creates uniquely named disposable test-only directories under the OS temporary directory (to avoid deep Windows checkout path limits), and records a new PORTABLE-TEST-RESULT-N.json. One unchanged real Node preflight runs; all other preflight responses/Node/Three contents are explicit inert integrity fixtures. No model, GPU, browser, live owner state or canonical file is required. Portable changes only relocate fixture/dependency paths, discover Node and separate fresh receipts; historical tests remain distinct.

Installation still requires root review and preserved canonical preimages. This backup adds only experimental repository paths and installs nothing.

The first packaged run hit Windows path-length limits during setup, before any behavioral assertion or real Node preflight ran. The portable runner now uses a checked, uniquely named OS temporary directory. The failed receipt is preserved beside the corrected run; this was a packaging-path failure, not a backend behavior result.
