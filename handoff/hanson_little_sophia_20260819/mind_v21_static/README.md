# Mind V21 static archive and portable author-test runner

This directory preserves the recorded Mind V21 static design and audit material.
It is requirements and historical static evidence, not the executable portable
Kira or Synthetic Robert resident. The runnable prototype is in
[`../portable_runtime/`](../portable_runtime/).

## Portable author test

The sealed author test retains its original long, sibling-relative V19/V20
workspace paths. Editing that test would invalidate its identity in
`author/AUTHOR_SOURCE_MANIFEST.json`, and placing the legacy directory names
directly below a deeply nested Windows checkout can exceed the reliable legacy
path-length boundary.

Run the unsealed transport wrapper from this directory instead:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONWARNINGS = 'error'
py -B -W error .\run_author_tests_portable.py
```

The wrapper:

1. rejects symlinks and generated Python bytecode in the sealed author tree;
2. verifies the exact byte count and SHA-256 of both packaged predecessor
   schemas;
3. copies the unchanged `author/` tree and dependencies into a short directory
   below the operating system's temporary folder;
4. recreates the historical sibling names only inside that disposable folder;
5. runs the unchanged `author/test_mind_v21_author.py` with warnings treated as
   errors and bytecode disabled;
6. requires two successful 64-test rounds (128/128 total), proves neither the
   packaged nor disposable author tree changed, and verifies temporary cleanup.

Pinned dependencies:

| Package path | Bytes | SHA-256 |
| --- | ---: | --- |
| `deps/v19_schema.json` | 33,788 | `ed2e2367a5a942b65a9a6107114e7c5a93b323b37e981c35a5d94e5359601dba` |
| `deps/v20_schema.json` | 42,299 | `82417f2634e14b6f49dfc6414364ede41f23c053d4b55fee1723fb168c27e53b` |

This wrapper and the short-path dependency copies are current handoff transport
files. They are not retroactively members of the historical sealed author or
independent-audit manifests and do not change those recorded roots.

## Historical independent-audit bytecode gap

The archived `independent_audit/EVIDENCE_MANIFEST.json` and
`independent_audit/POST_SEAL_REHASH.json` record a CPython 3.14 cache file as an
original audit subject:

```text
__pycache__/independent_v21_immutable_audit.cpython-314.pyc
```

That platform-specific cache file is deliberately not shipped. Reintroducing
it would conflict with the current handoff's no-generated-bytecode rule and
would not be a portable source dependency. Consequently, the archived inner
audit root is a historical record rather than a standalone reproducible seal in
this handoff. The current outer handoff manifest must hash the files that are
actually delivered. Do not silently rewrite the historical evidence manifest,
claim that the omitted cache is present, or describe the portable author test
as a new independent audit.

The recorded historical result remains bounded to static requirements. Neither
the archive nor the portable test proves a live mind, consciousness, personhood,
executed forgetting, robot safety, physical embodiment, deployment, or GO.
