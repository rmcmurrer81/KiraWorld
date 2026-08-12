# Kira R25 AFES Python/controller V3r19 different fresh static audit

Decision: `ACCEPT_STATIC_ONLY_FOR_ONE_BOUNDED_V3R19_VALIDATION`

Execution scope: one no-argument V3r19 contract-and-isolated-Python-controller
validation only. No `_build_execution_plan`, process, AFES, Blender, body,
save, render, model, voice, media, or network authority is granted.

## Independent result

The different reviewer `/root/resident_media_v13` rehashed the exact 61-row
seal with zero mismatch and independently rebuilt the C source under strict
x64 MSVC `/W4 /WX /O2 /MT /guard:cf /std:c17`. The independent build passed;
its executable differed from the sealed image only at duplicated link-timestamp
bytes. Both images are x64 PE32+ with high-entropy VA, ASLR, NX, CFG, and only
`bcrypt.dll` plus `KERNEL32.dll` direct imports.

The existing read-only post-seal suite returned
`V3R19_HOSTILE_STATIC_TESTS_PASS`. Independent source inspection accepted the
successful-path invariants:

- the exact V3r19 contract handle is acquired and checked before audit parsing,
  bound into reservation/terminal records, retained, and rechecked before a
  successful completion;
- the 39-field audit grammar rejects embedded NUL/CR, suffixes, extra lines,
  noncanonical auditor IDs, and non-exact lowercase digests using raw lengths;
- Python finalization and `FreeLibrary` must succeed, a Toolhelp inventory must
  prove the old module base and exact Python path absent, all retained handles
  are rechecked, and only then may `E_FINALIZED` be written;
- the exact closure is `8 + 4 + 13 + 17 + 14 + 5 = 61` unique subjects.

Reviewer ordered-row aggregate SHA-256:
`ea8df504b8c98cabbcfb3f524ce896879c110c14a34bf8716a45f36b909574f2`.

## Exact audit authorization

`INDEPENDENT_AUDIT.tsv` is 3,507 bytes, LF-only with 40 lines and no CR/NUL,
SHA-256
`927dc02ef49091dfff64909308fc244fa22e55a41f4844a17b8021ca5c1cbea7`.
Its sidecar is exactly that 64-byte lowercase digest plus LF.

The auditor ID records the different review; root transcribed the review into
the exact sealed V3r19 grammar. Transcription does not make root the reviewer.

## Scope notes

The terminal authority-contract recheck gates successful completion; a consumed
failure record may still be written after an earlier failure without that final
recheck. The module inventory proves point-in-time process-module absence under
the bounded candidate's ordinary single-run model; it is not a general
cryptographic statement about every concurrent loader or filesystem alias.

At this checkpoint the candidate executable, Python stage, AFES, Blender, body,
save, and render were not run, and runtime evidence/receipt were absent. The
one exact validation authority is unconsumed until the later root invocation.
