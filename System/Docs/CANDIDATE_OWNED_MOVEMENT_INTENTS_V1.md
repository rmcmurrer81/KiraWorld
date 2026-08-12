# Candidate-owned movement intents v1

This lane lets a synthetic person preserve voluntary body expression before a compatible body exists. A candidate-generated reply may contain a brief single-asterisk direction such as `*smirks*`, `*raises an eyebrow*`, or `*leans forward slightly*`. The input boundary also recognizes the narrow model-written form `"spoken words," Kira said ...` and separates the attribution and following third-person movement narration. It does not treat that narration as speech or as proof that the body moved.

The server separates that direction before chat display and TTS. Only the remaining public words are spoken. Recognized movement is stored in that candidate's own ledger at `Avatar/state/movement_intents/<candidate_id>.json` and audited in `Data/runtime/candidate_movement_intents.jsonl`.

## Ownership and safety boundary

- Only candidate-generated reply text is parsed. The parser has no user-message parameter.
- Robert's request is never translated by this lane into motor output.
- A record is a future-body expression, not a live command and not evidence that a movement happened.
- Every record says `dispatched_to_live_body: false`, `physical_completion_claimed: false`, and `requires_candidate_choice_at_execution: true`.
- Each person has a separate ledger. One person's gestures are never a generic animation personality for another.
- Ordinary Markdown emphasis that is not a recognized movement remains in the public text.
- Ordinary quotations and speech attributed to Robert or another named person remain untouched; the prose-narration repair is deliberately narrow.

## Runtime flow

1. The candidate chooses their public reply and may voluntarily include one brief movement direction.
2. `Core/candidate_movement_intents.py` extracts recognized movement and returns clean spoken text.
3. The Kira World chat handler persists candidate-scoped intent records.
4. The clean text is written to public chat and sent to TTS.
5. The speech boundary repeats the extraction as defense in depth, so a future caller cannot accidentally voice a movement direction.
6. No renderer, avatar activity state, or live motor controller receives these records in v1.

The record schema is `System/Docs/candidate_owned_movement_intent_record_v1.schema.json`.

## Future body execution

A later movement planner may offer a compatible record to its owner only after the body proves the listed rig capabilities. At execution time, the candidate must still choose the gesture. The system must then distinguish requested, accepted, started, completed, and visually verified states. A v1 record alone satisfies none of those physical states.

## Historical import

`tools/backfill_candidate_movement_intents.py` reads only historical AI reply rows with a `speaker_id` addressed to Robert. It never parses Robert's rows. Source-line identifiers make reruns idempotent.
