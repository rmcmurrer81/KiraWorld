# V3r16 independent compile and PE inspection

Date: 2026-08-11

The current source was compiled strictly into this audit evidence directory;
the sealed candidate object and executable were not overwritten or executed.

Compile policy: MSVC x64 `/W4 /WX /O2 /MT /guard:cf /std:c17`, Unicode,
`bcrypt.lib`.

Result: PASS, exit 0, no warnings.

| Audit compile artifact | Bytes | SHA-256 |
|---|---:|---|
| `compile_probe/rebuilt_v3r16.obj` | 48812 | `954b59ab5121d505e9c9a83bcd0289bab3de1ef40b16bb6f61526ce47aa85182` |
| `compile_probe/rebuilt_v3r16.exe` | 164864 | `3d11c1d4b1dfb264d8c564fb5a4230a295c8f31e596c8ba3c6b2effa0ef926af` |

Read-only `dumpbin` inspection of both the current candidate PE and the audit
rebuild found:

- x64 machine, PE32+;
- high-entropy VA, dynamic base, NX compatible, Control Flow Guard;
- zero delay-import directory;
- dependent DLLs exactly `bcrypt.dll` and `KERNEL32.dll`;
- no Python or Blender image/name and no `CreateProcess` or `ShellExecute`
  import.

The statically linked CRT imports generic `GetProcAddress` and
`LoadLibraryExW` from KERNEL32, but the audited source contains no call to
them and the PE contains no Python/Blender target name. This inspection does
not establish execution safety and does not overcome the exact-byte rejection.
