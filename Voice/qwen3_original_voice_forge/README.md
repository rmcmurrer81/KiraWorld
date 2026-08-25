# Qwen3 original voice forge

Status: **technical feasibility proven; no voice approved, assigned, routed, or active**.

This lane creates genuinely new, trait-described audition voices. It does not
clone a public figure, actor, character performer, or unrelated person. Kira's
accepted Chatterbox GPU route and sealed CPU fallback are unchanged.

## Proven pilot

The first bounded pilot used the Apache-2.0
`Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign` snapshot at exact revision
`5ecdb67327fd37bb2e042aab12ff7391903235d3`.

- Python 3.12.10
- Torch/Torchaudio 2.11.0 + CUDA 13.0
- RTX 5060 Ti, compute capability 12.0, `sm_120`
- eager SDPA and BF16; no FlashAttention or Triton
- 2.99-second model load and 18.55-second generation
- 4.53 GB peak allocated VRAM
- canonical mono PCM16 24 kHz output, 10.96 seconds
- pinned automated ASR word error rate: 0.0

ASR is an intelligibility proxy, not a listening, naturalness, identity,
distinctness, or approval decision. The candidate remains unassigned.

## Worker boundary

`feasibility_worker.py` accepts one strict generated-original request, verifies
the exact 13-file model payload before loading, rejects every unexpected file,
directory, link, or junction, generates one private audition, writes a
canonical WAV and hash-bound receipt, and exits. It never plays, routes,
binds, publishes, or replaces a voice. Named-person imitation language is
rejected.

## Read-only profile audition planner

`profile_audition_planner.py` is a separate planning boundary. It reads only
the trusted current Temporary Creator integration plan at
`Voice/local_voice_studio/evidence/avatar_temporary_creator_voice_integration.json`,
binds that file's byte count and SHA-256, and prepares request JSON without
loading a model or generating audio.

The planner is intentionally narrow:

- only the six current `prepare_nonbinding_*audition_brief` records with all
  three source records present are eligible;
- missing-source identities and `preserve_*` records are excluded;
- an existing voice is never copied into a request bundle, including the
  preserved legacy H. H. Holmes baseline;
- authored `female` and `male` values map exactly to Qwen's `adult_woman` and
  `adult_man` presentations;
- every eligible identity receives the same three generic audition palettes;
  no body, personality, era, or confirmed-locale traits are invented;
- `en-US` is retained only as the plan's explicit application audition default,
  while `source_locale_confirmation_required_before_binding` remains a blocker;
- all 18 deterministic request IDs are at most 64 characters, and every request
  conforms to `feasibility_worker.load_request`;
- the H. H. Holmes bundle and test text retain the exact disclosure:
  `Speculative historical reconstruction; not an authentic recording, verified
  voice match, or identity clone.` No authenticity or identity-clone claim is
  made.

Input JSON is size-bounded, duplicate-key rejecting, non-finite-number
rejecting, exact-schema checked, and recursively checked for unsafe attestation
paths and hashes. The output root must be a new absolute directory outside the
KiraWorld repository. Immediately before writing, the planner rebuilds the
entire plan from the trusted source and requires exact equality, preventing a
caller from injecting a request or traversal path.

Example planning command (no synthesis occurs):

```powershell
python profile_audition_planner.py `
  --output-root C:\new-private-audition-request-bundles
```

The new directory contains `audition-request-plan.json` and 18 individual
request files. It remains nonbinding planning material: no profile, route,
binding, activation, pilot evidence, or audio is changed.

Planner regression tests, including validation of every emitted request through
the current feasibility worker, run with:

```powershell
python -B -m unittest tests.test_profile_audition_planner -v
```

## Read-only profile audition evidence packager

`profile_audition_packager.py` is the next, still nonbinding boundary. It does
not generate, play, approve, bind, activate, or route audio. It consumes four
already-completed **external** inputs: the original request plan, its 18 run
directories, the exact two-entry Emily retry plan, and those two retry run
directories. It writes only to one caller-supplied, brand-new absolute output
root outside KiraWorld, and creates nothing until every input has validated in
memory.

The packager fails closed unless all of these statements are true:

- the original plan exactly rebuilds from the current trusted Temporary Creator
  integration source, including its source SHA-256, six eligible bundles, and
  three palettes per bundle;
- the retry plan byte count and SHA-256 bind that exact original plan and its
  source-integration SHA-256, and contain only the two declared Emily retry1
  candidates;
- every original and retry request passes the current
  `feasibility_worker.load_request`; retry traits are unchanged, the seed is
  exactly original plus one, and retry text is the exact reviewed plain-language
  clarity sentence;
- input directories have exact contents and every path is absolute, contained,
  regular, and free of links, junctions, reparse points, traversal, duplicate
  JSON keys, non-finite values, and over-limit data;
- every receipt binds its exact request and canonical WAV plus the current
  worker's exact revision and 13-file model manifest;
- every selected ASR report binds the request, WAV, and pinned checkpoint, has
  status `PASS`, and has word error rate at or below `0.25`;
- the final selection contains exactly 18 unique subject/palette slots: Emily
  calm-clear from the original run, Emily warm-rounded and grounded-assured from
  their two retry1 runs, and all 15 other slots from their original runs.

The external package preserves each selected request under its original
filename alongside `receipt.json`, `asr-audit.json`, and `candidate.wav`. It
also copies the original and retry plans as provenance. The two failed original
Emily request/receipt/ASR triplets are retained under `negative-evidence`, but
their failed WAVs are deliberately **not** copied. The machine manifest records
each omitted WAV's byte count and SHA-256 and states that it remains a private
local negative artifact. Its artifact inventory records the byte count and
SHA-256 of every one of the 80 copied payload files; the manifest cannot include
its own digest without recursive self-reference and states that limitation
explicitly.

Example packaging command, run only after the four external roots exist:

```powershell
python -B profile_audition_packager.py `
  --original-plan C:\absolute\external\original\audition-request-plan.json `
  --original-runs-root C:\absolute\external\original-runs `
  --retry-plan C:\absolute\external\retry\retry-plan.json `
  --retry-runs-root C:\absolute\external\retry-runs `
  --output-root C:\absolute\external\new-audition-evidence-package
```

The output is evidence for later human listening and collision review, not an
approval or runtime configuration. A failed write may leave a manifest-less
partial directory; such a directory is invalid and must never be treated as a
package. Retry only with another brand-new output root.

Packager tests use generated, tiny PCM fixtures and never load the Qwen model or
play audio:

```powershell
python -B -m unittest tests.test_profile_audition_packager -v
```

## Published candidate evidence

The first complete six-profile evidence set is published at
`auditions/profile_candidates_20260825_v1`. It contains 18 generated-original
WAV candidates, three per source-complete profile, plus their exact requests,
receipts, ASR audits, plan provenance, and two failed-attempt evidence triplets
without the failed WAVs. Its manifest SHA-256 is
`052cadaa45bbbd9fcd7dd626451aa03c3eb94a5db675285d208a7a2d6eb890b9`.

Commit `a3f9aa0db0a34fb477ba3051fd27ee1621aa5944` uploaded all 18 WAVs through
Git LFS. Package-specific Git attributes preserve the original JSON bytes so
the manifest's recorded sizes and SHA-256 values remain valid after cloning.
This publication is still audition evidence only: no voice was approved,
assigned, activated, or routed by that commit.

The worker sets Hugging Face and Transformers offline flags and was exercised
inside the development tool's restricted-network sandbox. That is useful
feasibility evidence, but it is not the reviewed OS-enforced production
isolation required by Kira World's voice authority. Production remains
fail-closed until a sealed parent/worker authority, containment canary,
collision evaluation, human listening review, and exact activation approval
all pass.

## Reproducing the bounded feasibility run

Create a separate Python 3.12 environment. Do not reuse or modify either of
Kira's accepted Chatterbox environments. Install the versions in
`requirements-feasibility.lock.txt`, download the exact model revision into a
local model directory, and run:

```powershell
python feasibility_worker.py `
  --request auditions/calm_female_pilot_20260825_01/qwen3_voice_design_feasibility_request.json `
  --model-dir <exact-local-model-directory> `
  --output-root <new-private-output-root>
```

The model weights, Python environment, caches, and private review material do
not belong in Git. Only generated-original auditions that contain no private
source recording may be considered for later publication, and only with their
request, receipt, provenance, and review evidence.

## Next gates

1. independent source and containment audit;
2. at least three candidates per new person;
3. pronunciation, long-text, emotional-range, clipping, silence, and unwanted-
   speech probes;
4. collision comparison against every approved resident voice;
5. owner or exact subject listening selection;
6. sealed 0.6B Base rendition and clean process/VRAM return;
7. append-only approval, activation, revocation, and rollback evidence.
