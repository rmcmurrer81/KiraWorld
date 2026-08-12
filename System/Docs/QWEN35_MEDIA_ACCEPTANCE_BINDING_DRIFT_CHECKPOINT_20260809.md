# Qwen 3.5 resident-media acceptance binding drift — 2026-08-09

Status: `STATIC_MEDIA_CORE_PASS_QWEN_OVERLAY_FAILS_CLOSED_PENDING_V2`

No magazine, PDF, movie, television, music, speaker, model, camera,
microphone, or body operation was run for this check.

## Result

The source-bound media core remains internally healthy:

- exact rendered PDF page/crop and separate OCR evidence;
- real decoded video frames, timestamps, audio, pause/seek/resume truth;
- PCM-derived music evidence rather than filename/metadata substitution;
- mature-mainstream co-viewing and exact-item correction boundaries;
- person-scoped presentation, attention, reaction, and memory separation.

The combined static run passed all 22 core media/session/receipt checks. The
Qwen 3.5 non-body/media overlay then failed closed in four tests before any
live operation.

## Exact drift

`tools/run_qwen35_non_body_media_acceptance.py` still pins the resident-media
harness to historical SHA-256:

`d7b527397c8c630dfda01834191b8839c4fc4300c372c6517e5926cb03267773`

The current exact harness SHA-256 is:

`f56927167a92eadf88f2ea9b61ef5a6ece9d8e96bc53f3d696331188e2279e23`

The latter hash is separately recorded by
`System/Docs/QWEN35_REMAINING_CURRENT_PERSON_ROUTES_STATIC_CHECKPOINT_20260809.md`
after current owner routes were repinned to exact Qwen 3.5. The overlay is
therefore doing the safe thing by refusing to reinterpret changed bytes as
historically preserved.

## Next boundary

Do not overwrite the historic readiness evidence or silently update a hash.
Create an append-only v2 overlay that:

1. preserves the original historical harness hash as provenance;
2. binds the current exact Qwen-3.5 harness hash and semantics separately;
3. revalidates its exact prompts, source windows, model name/digest, media
   receipts, lifecycle/unload gates, and no-experience-overclaim rules;
4. receives an independent static audit; and
5. remains non-live until Robert is present for any owner-hearing or media
   presentation acceptance.

No watched, read, heard, enjoyed, learned, preferred, or remembered claim is
authorized by this checkpoint.

