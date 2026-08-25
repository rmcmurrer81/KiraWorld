# Qwen3-TTS original voice forge feasibility — 2026-08-25

Status: `TECHNICAL_FEASIBILITY_SAMPLE_NOT_APPROVED_NOT_ACTIVE`

The first local Qwen3-TTS VoiceDesign feasibility run completed on the RTX
5060 Ti without changing Kira's accepted Chatterbox GPU route, sealed CPU
fallback, reference, profile, or voice routing. No source recording, actor
recording, named-person imitation request, playback, assignment, activation,
or publication occurred.

## Exact result

- model: `Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign`;
- revision: `5ecdb67327fd37bb2e042aab12ff7391903235d3`;
- license: Apache-2.0;
- sanitized local payload: exactly 13 files, 4,520,163,832 bytes, zero
  incomplete or download-metadata files;
- Python 3.12.10, Torch/Torchaudio 2.11.0+cu130, Transformers 4.57.3;
- GPU: RTX 5060 Ti, compute capability 12.0, `sm_120` present;
- model load: 2.9948 seconds;
- generation: 18.5491 seconds;
- peak allocated/reserved VRAM: 4,526,731,264 / 4,697,620,480 bytes;
- output: mono PCM16 24 kHz, 10.96 seconds, 526,124 bytes;
- WAV SHA-256:
  `6f92cdf4ee7d2409c08550d6b75553c944ca9180c3f056a462c437177e04a672`;
- pinned greedy Wav2Vec2 ASR WER: 0.0, technical intelligibility `PASS`.

The ASR result does not prove naturalness, identity fit, distinctness, emotional
range, or owner approval. The generated voice is only an audition candidate.

## Isolation truth

The run used local model paths, Hugging Face/Transformers offline flags, and
the development tool's restricted-network sandbox. A requested exact-program
Windows Firewall rule could not be created because the current process lacks
administrator authority. Therefore this run is feasibility evidence, not
reviewed OS-enforced production isolation.

The generated worker verifies exact file-set equality, sizes, and hashes,
rejects extra files/directories/links/junctions, and refuses named-person
imitation language, but it does not itself constitute the sealed one-use
parent/worker authority required by the current voice-forge documents.

## Current decision

Keep the candidate unassigned. Human listening, multi-candidate comparison,
collision checking against existing resident voices, pronunciation and stress
tests, a sealed runtime rendition, reviewed process containment, and exact
approval/rollback evidence remain required before any person can use it.

Uploadable source and evidence live below
`Voice/qwen3_original_voice_forge/`. Model weights, environments, caches, and
private review material remain outside Git.
