# Pinned predecessor schemas

`v19_schema.json` and `v20_schema.json` are byte-exact predecessor inputs used
only by [`../run_author_tests_portable.py`](../run_author_tests_portable.py).
Their required sizes and SHA-256 identities are pinned in that wrapper and in
the parent [`README.md`](../README.md).

The short filenames avoid making the distributed Windows checkout depend on
legacy paths longer than 260 characters. The wrapper reconstructs the original
directory and filename layout only inside a short, disposable temporary root.
