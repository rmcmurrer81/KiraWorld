# Exact five-file deployment and recovery

Prepared for root review. No installation is authorized or performed by this
document. The existing frozen `INSTALL-PLAN.json` remains unchanged, SHA256:

`8d5160f30205936e015cf5938cbaa69e0caa68552553e1735b5db2f339a3ae71`

`install_exact.py` defaults to a read-only preflight. It verifies the plan hash,
the exact five allowed target paths, all current before hashes, candidate and
preimage bytes, 116 protected originals and the other 37 installed source files.
The explicit apply command may run only after root approves that exact plan:

```text
python -B install_exact.py --apply 8d5160f30205936e015cf5938cbaa69e0caa68552553e1735b5db2f339a3ae71
```

Each file replacement uses a flushed temporary file in the target directory and
an atomic rename. This is atomic per file, not an atomic five-file transaction;
perform it when no World source update/export is running. Any failed write
triggers rollback of completed replacements if their bytes still equal this
candidate. Unexpected concurrent edits are preserved and recorded for review.
The installer does not change saved worlds or preview directories and refuses
to overwrite an existing execution receipt.

After installation, root may authorize `verify_installed.py`. That helper uses
the actual installed saved-job API to create/reuse a new immutable preview and
write a fresh export under `installed-mars-001`, with a one-GiB process-family
cap and 180-second timeout. It preserves the saved-job pointer, checks the old
042 preview and older previews, verifies exact package/importer checks, and
confirms a repeat refresh reuses the same build. It starts no model, GPU job,
server or UI. It has been prepared from the already-used042 workflow but has
not yet been executed for installed045.

If root directs reverting all five files, the inverse command requires every
installed target to still match this candidate and all preimages to match the
original plan:

```text
python -B install_exact.py --rollback 8d5160f30205936e015cf5938cbaa69e0caa68552553e1735b5db2f339a3ae71
```

It restores preimage bytes and keeps all immutable preview directories. It does
not silently erase a later code update. A hardware/process failure during the
five-file transaction may require checking the hashes and manually restoring
the affected preimages; complete transaction durability is not claimed.

Eight temporary-fixture tests validate success/reversal, partial-write failure,
concurrent-change preservation and altered source/target/path/protected-input
rejection. These tests never write canonical files or owner data. Root accepted
the CPU artifact as a limited static geometric improvement; that acceptance is
separate from installation approval, native-view testing and owner realism.

The public backup currently maps only to `experimental/world-galley-detail-045`.
Five exact canonical mappings are prepared separately with before hashes from
public main `4d59e8272af89d43d5c1966cba1a464b010a093e`. Add them to the publication
manifest only after the corresponding installation/verification decision, along
with the new execution receipts. No Git mutation is part of these helpers.
