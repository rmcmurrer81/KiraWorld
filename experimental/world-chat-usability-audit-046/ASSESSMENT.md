# Ordinary World Builder chat audit046

Scope: installed045 routing and service code, with disposable saved-job state and
inert background workers. No native window, model, network research, preview
server, real export, GPU job or owner-file mutation was performed. This is a
measured usability audit and one isolated context fix, not a completed chat UI.

## What ordinary requests currently do

The actual `send_world_builder_chat` callback invokes
`submit_research_prompt` for every nonempty message. That adapter recognizes only
four complete resume phrases: `resume`, `resume research`, `continue research`
and `retry research`. Every other message creates/reuses a research brief/job.

Fifteen captured requests used the real brief parser, job creator and saved-job
catalog. The research/geometry worker boundary stayed inert, so these results
establish routing and saved state, not generated-world quality.

| Request type | Observed behavior | Meaning for ordinary use |
| --- | --- | --- |
| `Build a Mars base.` | New analog-to-original research, original generation eligible | Creation front door is connected; output quality still needs actual generation/review. |
| `Build a habitat with a galley, laboratory and two airlock doors.` | New analog-to-original research, original generation eligible | Requested functions enter the saved prompt; no claim each function has been built by this audit. |
| `Build an original crew habitat.` | New real-place reconstruction research, generation locked | A normal descriptive modifier falls outside the current originality grammar. This is a measured limitation, unchanged here. |
| Widen a current door; add dining furniture; change the lab into a galley | New real-place research on that sentence | No existing-room editing service is dispatched; the selected original geometry is not changed. |
| Open/reopen the latest saved world | New real-place research | Chat does not invoke the working saved-job selector. |
| Open current preview; export this world as a 3D package | New real-place research | Chat does not invoke the working preview/export buttons. |
| `resume` / `Resume research` | Existing selected research job queued | Exact supported phrases reuse the saved job; they are not read-only reopening commands. |
| `Continue my world.` | New real-place research | The phrasing is not recognized as resume. |
| `Do not build a new world.` / a question about a room | New real-place research | There is no conversational action/negation gate before job creation. No model was started by this audit. |

The tested messages report a queued research job and its subject/style. They do
not say that an existing door was widened, a room changed or an export completed.
The issue is incorrect action routing and unwanted research submission, not an
observed false completed-edit claim. “Photorealistic by default” is the stored
style preference; it does not establish rendered realism.

## One concrete bug fixed in isolation

Starting a different research job through chat directly assigned the selected
job/folder, leaving the previous world's preview, reference-photo window and
component view intact. This differs from the saved selector, which already calls
`set_saved_research_context` to close/rebind those views.

With a previous world open, the old chat callback retained its preview on all
13 job-changing cases. An export then captured the new selected job together
with the old preview binding. The actual `inspect_selected_layout` guard
correctly rejected this pair as belonging to different saved projects. It did
not silently export the wrong world, but ordinary creation could leave stale
visual context and a confusing export refusal.

Candidate046 uses the existing context-reset method when the chat result changes
the selected job. It keeps same-job resume views intact and preserves the prior
`latest_folder` update. No parser, generator, source policy, preview, collision,
geometry or exporter logic changes. All 13 job changes now clear the old preview,
close old reference photos and bind the component view to the new selection.
The actual export-selection guard reaches the correct selected source boundary.

This fixes the context mismatch only. Unsupported chat actions still require a
separately designed dispatcher or clear unsupported-command response. It does
not add room editing, natural-language export/reopen, conversation answers or a
larger originality grammar.

## Validation and preservation

Eleven focused tests exercise actual workspace methods with temporary state:
new job context switch, same-job resume, failed submission, already-running
research queue, preview/export after selection, no-selection behavior and saved
selector reopening. The real exporter selection gate reproduces the baseline
mismatch and accepts the candidate's selected source before an inert stop.
Saved selector reopening remains read-only and does not queue research.

Candidate and baseline captures preserve the same job-creation/research-mode
outcomes. No unsupported request was relabeled as successfully implemented.
All 116 protected original files and eight audited canonical source files remain
unchanged. No installation or Git mutation was performed.

Earlier audit captures used “original crew habitat” for the starting fixture,
which the current parser conservatively locks as a real-place request. That
history is preserved. Final captures use the supported “original habitat” as
the prior saved job and add “original crew habitat” as an explicit audit case.
The first candidate draft omitted the unconditional `latest_folder` assignment;
that omission was corrected before freezing, preserving same-job behavior.

Root review and native UI validation remain pending. `REVIEW-PLAN.json` contains
the exact one-file candidate/preimage mapping for any later installation.
