# World chat dispatcher 047 — isolated candidate

The installed chat submitted almost every message as new research. In 53 actual callback fixtures, 39 commands that were not creation or resume created unwanted jobs; two polite resume requests also created new jobs. This candidate routes those requests before research submission. All 53 fixtures pass through the actual workspace callback with real disposable saved-job services. Research/model execution, preview opening, destination selection and export generation are inert boundaries, so this is routing and state verification rather than a new generated-world or native-window review.

Only two canonical files are proposed: the existing workspace and a small pure command classifier. The installed 046 selection fix remains intact. No canonical file, owner world, saved preview or original source was changed during candidate preparation.

## Supported actions

- Direct Build, Create, Make, Design, Invent and Research requests, including “Can you build a Mars base?” and “Please make a habitat,” retain the full original owner prompt for the existing research parser.
- Resume/retry/continue the selected research normalizes to the existing resume action. Same-selection previews and reference views remain open.
- Show status reads the selected job's saved research stage and explicitly does not declare a complete or visually approved world.
- Open latest saved world/project/layout/research uses the existing catalog and selector. It selects the newest record, without silently substituting an older record when the newest is damaged. It does not automatically open a graphical preview.
- Open current preview and Export this world call their existing selection-aware callbacks. Their existing source validation, immutable-preview and export eligibility rules remain in effect.
- Explicit negatives, plans, questions, deferred requests, quoted source instructions and unsupported edits create no research job. Unsupported edits say they are unsupported and preserve the selected world. Stop/Cancel explicitly does not claim to stop an already-running worker.

## Evidence

`BASELINE-CAPTURES.json` and `CANDIDATE-CAPTURES.json` preserve all 53 before/after command captures: 11 creation/research, 29 no-job cases, three status, two latest-selection, two preview, three export and three resume. Unwanted new research drops from 39 to zero; unwanted new jobs for polite resume drop from two to zero. The 11 direct creation/research prompts remain byte-for-byte identical in saved briefs.

Five test groups cover those fixtures plus newest-record selection, damaged newest-record handling, missing selection and honest stop behavior. Ten additional context regressions reuse the frozen 046 tests: current selection reaches preview/export, new-job selection closes stale views, same-job resume retains views, running workers are not replaced, saved selection does not research, and an invalid explicit creation request preserves prior context. Tests do not instantiate Tk, launch a browser, invoke a model or create a real export.

The first test run exposed that “Export the selected world” needed two determiners; its failure is retained under `history/first-test`. Current results include that correction and existing-world room/door creation held as unsupported edits. Final source/preimage and 116 protected-input hashes are checked by `finalize.py`.

## Limits and recovery

This is a bounded English command dispatcher, not general conversational planning or room editing. Ambiguous text and unsupported combinations request a clearer single action. Informational questions receive brief capability guidance; no model is invoked. “Reopen my last saved habitat” is deliberately not treated as an arbitrary latest saved project: type/name lookup is not implemented. The existing parser still classifies “Build an original crew habitat” as real-place reconstruction; this is captured as a remaining grammar limitation, not silently promoted to original generation.

Negative room constraints within an otherwise direct creation request remain part of the original brief. A later generic stop message only prevents a new job and does not implement research cancellation. Approval must still happen through a new direct request; no deferred background job is scheduled.

`REVIEW-PLAN.json` identifies one existing-file replacement and one new file, with the exact preimage, final hashes and protected inputs. Installation requires root review; no installer was executed here. To recover the prior state after a later installation, restore `baseline/world_builder_workspace.py` and remove only the newly added helper after verifying it still has this candidate's hash. The old saved worlds and previews require no migration.

The tests depend on a complete Kira checkout and the pinned 046 `test_context.py`. Local harness paths are recorded honestly; a portable publication wrapper can rebind the checkout and output directory without changing the frozen source. No native UI or owner acceptance is claimed.
