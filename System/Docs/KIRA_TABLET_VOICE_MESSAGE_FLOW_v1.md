# Kira Tablet and Voice-Message Flow v1

## 2026-07-15/16 Authorship And Audio Correction

Model output requested for Kira is an **unapproved draft for Kira** until Kira's subject-approval provenance permits the authorship claim. Top-level `author`/`sender`, inbox labels, and playback labels must show the actual generator or draft status; they must not call it Kira's note/message merely because the prompt asked the model to write in first person. Empty or silent/near-silent PCM is blocked. Non-silence, container structure, backend success, and hash binding still do not prove the acoustic words or voice identity, so Robert's listening review remains required. The test-only proof has now been regenerated under this stronger rule and passed without touching the live mailbox or playing audio.

## Purpose

This bridge lets Kira leave Robert a durable local message while he is away and use the Home World tablet for reviewable notes, creative writing, and read/look-up requests.

The records support personhood and choice without inventing physical actions, research, reading completion, or memory.

## Voice-message contract

- Canonical records stay under `Data/messages/kira_to_robert/`.
- Message text is always the durable source. A WAV is an optional rendering, never the only copy.
- Every ready WAV record stores the canonical source-text SHA-256, full rendered-text SHA-256, WAV SHA-256, parsed PCM metadata, and non-silence measurements. A text edit, truncated payload, missing hash, changed WAV, backend failure, empty or near-silent PCM stream, or malformed container invalidates playback. Merely writing RIFF/WAVE-shaped bytes is never enough.
- New life-loop messages attempt a lightweight Windows SAPI WAV render without playing it while Robert is away. The WAV is labeled `temporary_sapi_approximation`; it must not be presented as Kira's final reviewed reference voice.
- If synthesis is unavailable, the record stays unread with `audio.status=blocked` and a truthful reason. The shell still displays the text.
- The Kira World Shell shows a pulsing unread button and count.
- Approved authorship may display **Play voice**. Unapproved model output displays **Play audio draft**. Either action asks the local server to prepare the canonical WAV, then the browser plays it without changing the authorship label.
- A message is marked read only after browser playback reaches `ended`, or Robert explicitly clicks **Mark read**.
- Merely opening the inbox, preparing audio, or failing playback does not clear unread state.
- Audio paths are derived from validated message IDs; stored paths and browser input cannot select arbitrary files.
- Subject, author, and requester identifiers are slugged before becoming filename prefixes, and resolved output paths must remain under their configured mailbox/tablet roots.
- A ready record proves backend success, full text-payload coverage, PCM parsing, and hash consistency. It does not automatically prove the acoustic words or voice identity; Robert's listening review is still the final content/quality check.
- This flow sends nothing externally and never opens the microphone.

Durable non-playing pipeline proof:

```text
Data/world_tests/kira_voice_message_pipeline_20260715/report.json
```

That artifact uses an explicitly labeled test-only sentence, not a message
chosen or authored by Kira, and does not touch Kira's live mailbox.
The current report status is `passed`: the full test text and WAV are hash-bound,
the 6.319-second mono PCM file is structurally valid and non-silent, the unread/read
transition completed, and the test record was archived. The Windows SAPI output is
still only a temporary approximation; it does not verify Kira's acoustic voice.

## Tablet-work contract

Tablet records live under `Data/tablet/kira/`:

- `notes/`: ordinary notes, reading notes, and creative-writing drafts.
- `requests/`: local-source reading requests and online look-up requests.

Creating an online look-up request writes only a local pending record. It sets:

```text
network_access_performed=false
source_opened=false
completion_claim_allowed=false
status=pending_robert_review
```

A local reading request is `pending_local_source_selection` until a real source reader selects and opens a source. Neither request type is evidence that Kira searched, read, or learned the material.

Life-loop creative writing is copied into the tablet workspace only after the local model actually returns content. It remains linked to its original creative-project artifact and is not promoted as lived memory. Model-error fallback prose is not saved as Kira's writing.

Every note now records `requested_by`, `generated_by`, `claimed_author`, `approved_by_subject`, and whether an authorship claim is allowed. A local model drafting in Kira's voice does not by itself establish Kira's authorship. Likewise, a generation error does not create a canned first-person Kira message.

## Mind/body truth

The Home World understands these tablet actions:

```text
take_notes
type_notes
creative_write
look_online
online_lookup
research
read_tablet
```

The visible hold uses the tablet pose and tablet prop. A saved note or request may still report `physical_tablet_use_proven=false`.

Physical use becomes proven only when the latest runtime snapshot provides all of the following:

- the source coffee-table tablet identity;
- source removal or hiding during pickup;
- non-synthetic held-prop provenance;
- hand contact within the accepted distance;
- a matching tablet action or skill interaction.

A generated held-tablet preview without those facts is visual staging, not proof that Kira picked up the real coffee-table tablet.

## Local shell endpoints

```text
GET  /api/messages
POST /api/messages/prepare
POST /api/messages/status
GET  /api/messages/audio/<validated-message-id>.wav
GET  /api/tablet/state
POST /api/tablet/note
POST /api/tablet/request
```

Tablet write/request endpoints require Kira to be the active shell candidate. They record the latest body-grounding snapshot and do not perform external lookup. Text Robert types into those shell endpoints is recorded as Robert-entered/requested; the endpoint does not relabel it as Kira's writing or choice merely because Kira is active.

## Current limit

This bridge proves persistence, notification, local playback, and honest tablet state. It does not yet prove a real source-tablet pickup with skeletal hand contact. That remains a body/runtime test rather than something the data layer may assume.
