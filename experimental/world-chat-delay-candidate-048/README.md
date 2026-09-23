# World chat delay correction 048

This isolated successor preserves frozen 047. Root found that four explicit delays still queued research: “Build a Mars base but wait before starting,” “Build a Mars base, but do not build a new world yet,” “Build a Mars base after I get home,” and “Build a Mars base later, not now.” The new helper holds all four before job submission. `ROOT-REGRESSIONS.json` reproduces each failure with the frozen 047 helper through the actual workspace callback, then captures the corrected callback and unchanged saved state.

The narrow addition recognizes a post-command wait/hold-off clause, a negated creation/research clause with yet/now/until, a first-person or addressed return-home condition, and a trailing “not [right] now.” Quoted text is masked before this check. Ordinary content constraints, including “with no weapons” and “but do not build a laboratory,” remain valid creation requests; quoted delay text remains data. A request that negates building a particular room **yet** is conservatively held as a timing constraint. This bounded grammar does not claim to understand every possible English condition.

The workspace file is byte-identical to candidate 047. Its dispatcher uses the existing saved selection, preview and export callbacks, preserves the installed 046 stale-view fix, and leaves room editing and general conversational planning explicitly unsupported. No model, research, preview UI or export was executed in the routing tests. A stop request honestly does not claim to cancel an already-running worker. Named/type-filtered world reopening and the existing “original crew habitat” parser gap remain as documented in 047.

## Validation

- 69 command fixtures through the actual workspace callback, real disposable job creation and saved catalogs, with inert model/research/preview/export boundaries. These include all 53 prior cases and 16 new delay/content/quotation cases.
- Six routing test groups include newest saved selection, damaged latest record, missing selection, stop messaging and the four independently reported 047 regressions.
- Ten retained 046 context tests preserve selected preview/export bindings, same-job resume, existing workers and failed-submission state.
- Ten installer tests use temporary fixtures only: exact install/rollback, new-file collision, candidate/preimage/protected-file tampering, target escape, failures before and after replacement, and concurrent-change preservation.
- The exact candidate preflight checks 116 protected inputs and the installed 046 preimage. No canonical writes or owner-file changes occurred.

`SOURCE.diff` compares the full proposed two-file change against installed 046. `FROM047.diff` contains only the delay correction. `prior047/world_chat_requests.py` is the exact frozen helper used to reproduce root's findings. `baseline/world_builder_workspace.py` is the actual installed preimage. `SOURCE-PINS.json` records the canonical dependencies used by the tests. The retained context suite depends on `../world-chat-usability-audit-046/test_context.py`; the frozen path and hash are recorded in `TEST-DEPENDENCIES.json`.

## Exact installation and recovery

`INSTALL-PLAN.json` SHA-256 is `3fedb5237a74155411c93453df700ecfeaca358bedd9b5dcdc2594409d713906`. Root review and explicit authorization are required before applying it. Running `install_exact.py` without arguments is a read-only preflight. The installer adds the helper first, then atomically replaces the workspace. It validates exact targets, new-file absence, source hashes, preimage, syntax, dependencies and protected inputs. An installation failure attempts to restore only verified candidate bytes; a concurrent edit is held for review. If the workspace cannot be restored, its helper is retained in case the concurrent workspace still imports it.

After root authorization, `--apply` with the exact plan hash applies the two files and writes `INSTALLED.json`. `--rollback` with that hash first verifies both installed hashes, restores the old workspace and removes only the exact new helper, then writes `ROLLED-BACK.json`. No recursive deletion or saved-world migration is involved. Historical receipts are never overwritten. Tests write exclusive result files; rerun in a fresh disposable copy or preserve previous receipts under a new history directory first.

Root reviewed and installed this exact plan at 2026-09-23 12:16:58 UTC; `INSTALLED.json` records the two replacements and 116 protected inputs unchanged. Final verification checks the actual installed hashes. The first freeze attempt raced with that authorized installation and correctly rejected the changed before-state; `FINALIZE-TIMING.json` records that event. Native UI and owner approval are pending. The earlier 047 source and receipts were not changed.
