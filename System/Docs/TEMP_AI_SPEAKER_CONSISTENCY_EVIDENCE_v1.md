# TemporaryAI Speaker-Consistency Evidence v1

## Purpose

`Core/temp_ai_speaker_consistency.py` compares an owner-confirmed, bounded
target-only WAV with bounded WAVs from other recordings. It is a screening
aid for source review. It is not speaker identification and it is never voice
authorization.

The analyzer fails closed when:

- the anchor is not explicitly owner-confirmed as target-only;
- an input is too short, too quiet, excessively clipped, or lacks enough
  active audio;
- anchor and candidate use the same source ID;
- bounded WAV hashes match, or supplied underlying-media hashes match;
- the WavLM model is unavailable or returns invalid embeddings.

Every evidence manifest records source and segment SHA-256 hashes, requested
and resolved model revisions, all cross-source cosine scores, quality
measurements, and explicit false values for identity proof, automatic speaker
approval, voice assignment, cloning/training, and TemporaryAI activation.

## Model and downloads

The production backend is Transformers `WavLMForXVector` with
`microsoft/wavlm-base-plus-sv`. Loading is lazy. The default is local-cache
only, so an ordinary check cannot silently download a large model. A caller
must explicitly pass `--allow-model-download` to permit acquisition into the
Hugging Face cache.

On 2026-07-17, the model was explicitly cached at resolved revision
`feb593a6c23c1cc3d9510425c29b0a14d2b07b1e`. A real cache-only CPU smoke test
loaded that revision and produced a 512-dimensional x-vector from a bounded
Kathryn candidate WAV. This proves that the analysis backend runs locally; it
does not prove the speaker's identity or approve the source.

The first production comparison used Kathryn's owner-confirmed 1999 source as
the anchor and three owner-shown 2016 pilot clips as candidates. All supported
same-speaker consistency: clip 0345 median 0.887174, clip 0346 median 0.946274,
and clip 0350 median 0.936888. This ranking replaces the need to inspect those
rows manually, while background cleanup/QC and final source approval remain
separate.

Check dependencies and cache without loading a model:

```powershell
py tools/check_temp_ai_speaker_consistency.py --capability
```

## Explicit bounded-WAV analysis

The WAVs must already contain only the intended time ranges. The anchor source
and every candidate source need stable, different recording IDs.

```powershell
py tools/check_temp_ai_speaker_consistency.py `
  --anchor-wav C:\path\anchor.wav `
  --anchor-source-id source_scene_a `
  --owner-confirmed-anchor `
  --candidate source_scene_b=C:\path\candidate.wav `
  --output C:\path\speaker_consistency_evidence.json
```

By default, energy-bounded regions are split on silence. Use `--presegmented`
only when each supplied WAV is already one clean speech segment.

## Interpretation

The default operational bands are median cross-source cosine similarity of
`>= 0.80` for consistency support, `< 0.60` for lack of support, and the
middle band for manual source review. These thresholds are not calibrated as
identity probabilities. Even a high result cannot prove who spoke, approve a
clip, grant rights, build a clone, assign a voice, or activate a person.
