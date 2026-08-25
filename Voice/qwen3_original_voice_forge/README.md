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
