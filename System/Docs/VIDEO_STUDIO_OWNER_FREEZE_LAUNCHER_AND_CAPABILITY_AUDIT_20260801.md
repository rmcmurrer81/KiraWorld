# Video Studio Owner Freeze, Launcher, and Capability Audit

Date: 2026-08-01  
Method: read-only filesystem, source, launcher, manifest, and log inspection  
Status: **COMPLETE — NO VIDEO OR STUDIO OPERATION RUN**

Current owner authority:

- `VIDEO_STUDIO_DARK_ALPHA_UI_REJECTED_AS_TOO_COMPLICATED`
- `VIDEO_STUDIO_GREY_CHAT_FIRST_UI_REJECTED_AS_WORSE`
- `VIDEO_STUDIO_PRODUCTION_AND_UI_DEVELOPMENT_FROZEN_BY_OWNER`

No project, research, fact sheet, script, visual acquisition, restoration,
upscale, face search, voice synthesis, render, approval, publication, or upload
was run for this audit. No Studio directory, launcher, project, output, or
evidence file was moved, renamed, merged, overwritten, or deleted.

## Owner decision on deletion

Do **not** delete the old Studio. Deletion is neither authorized nor advisable
now. The three trees are not redundant copies: v1.9 contains the complete
older backend and its integrity manifest; the dark alpha contains a separate
v2 backend and private project/output history; and the grey chat-first tree
contains the later isolated prototype and its diagnostic evidence. Removing
any one now would destroy rollback or forensic evidence before a single stable
replacement has been owner-approved.

## The three installations

| Location | Exact purpose and ownership | Read-only integrity observation |
|---|---|---|
| `C:\KiraVideos\VideoStudio` | Self-contained **v1.9** installation. `app.py` owns its form UI and `studio_core.py` owns its older research, outline/script, slides, thumbnail, narration, packaging, and rendering workflow. Its configured project/output root is `C:\Users\robmc\KiraVideos\StudioOutputs`. It does not use the later v2 or chat-first backend. | 118 files, 21,953,950 bytes. All 51 files named by `FILE_HASHES.json` exist and match exactly: 51 matched, 0 missing, 0 mismatched. |
| `C:\KiraVideos\KiraLabsVideoStudio_v2_staging\2.0.0-alpha.1` | Isolated **dark v2 alpha**, explicitly not a v1.9 replacement. `kira_video_studio/ui.py` owns the dark six-tab/nine-stage UI; `kira_video_studio/project_service.py` owns its v2 research, claims/fact sheet, script, visual/review, voice, and build operations. Its configured output root is `C:\Users\robmc\KiraVideos\StudioOutputs\V2_PrivateTests`; legacy v1.9 output is read-only to it. | 18,250 files, 426,918,231 bytes, including its local media environment and evidence. VERSION, README, both launchers, app, UI, backend, and settings match the 2026-07-31 pre-sprint backup byte-for-byte. Five files differ from the earlier 2026-07-28 validation ledger because documented later alpha work enlarged them; those current files also match the later pre-sprint backup. |
| `VideoStudioDevelopment\chat_first_production` | Isolated **grey chat-first prototype**. It deliberately does not runtime-import v1.9 or v2. `chat_first_studio/store.py` owns projects under this tree's `runtime/projects`; `service.py`, factuality modules, and `production_renderer.py` form a third independent backend. Its UI exposes deterministic chat intake plus internal state and build controls. | 285 files, 26,128,942 bytes. Existing Jean Grey, diagnostic, and auto-created untitled project evidence remains present and inactive. |

This is the central architecture problem: there is no single shared “real
backend.” There are three independent programs with three project stores and
partly overlapping capabilities. The current normal source route selects the
third one, so it understandably looked like a different program.

## Current normal launcher chain

The source currently on disk has one unambiguous chain:

1. `Start_Kira_Text_Voice_Chat.bat` starts
   `tools/kira_world_shell_server.py` on port 8768 and opens
   `tools/kira_world_shell_viewer.py`.
2. The visible **Open Video Studio** button sends
   `POST /api/open-video-studio` at
   `tools/kira_world_shell_server.py:4838-4840`.
3. The POST handler at lines 6797-6825 calls
   `Core/shared_person_workbench.py:13-39`.
4. That policy resolves only
   `VideoStudioDevelopment/chat_first_production/START_CHAT_FIRST_STUDIO.bat`
   (`Core/shared_person_workbench.py:6-10`).
5. The handler runs the batch file with `cmd.exe` and the chat-first directory
   as its working directory (`tools/kira_world_shell_server.py:6806-6811`).
6. The batch file runs `py -m chat_first_studio ui`, which reaches the grey
   Tkinter interface.

That exact current chain can produce the grey **Kira Labs Video Studio — Chat
First (Protected)** window. It cannot produce the dark
**2.0.0-alpha.1 STAGING** window shown in the earlier screenshot.

## Why both different windows appeared

The dark screenshot is conclusively the installed alpha: its title, six tabs,
and nine-stage workflow are defined in
`C:\KiraVideos\KiraLabsVideoStudio_v2_staging\2.0.0-alpha.1\kira_video_studio\ui.py`.
Its direct launch chain is:

`START_KIRA_LABS_VIDEO_STUDIO.bat` → a Python 3.11+ windowed interpreter →
`START_KIRA_LABS_VIDEO_STUDIO.pyw` → `app.py` →
`kira_video_studio.ui.launch()`.

The grey screenshots conclusively match the current chat-first chain above.
The exact initiating event for the earlier dark window was not persisted:

- `Data/runtime/video_studio_access_log.jsonl`, which the current POST handler
  would append, does not exist;
- the life-loop log contains no Studio-open event for the supervised session;
- no matching Studio process remained when the read-only process check was
  performed;
- a preserved pre-sprint shell route did explicitly target the external dark
  alpha, while direct installed launchers and an already-open alpha window also
  remained possible.

Therefore the defensible conclusion is **route/version skew**: the dark window
came from the older alpha chain (an older already-running shell/server, direct
alpha launcher, alternate shortcut, or existing window), while the later grey
window came from the current chat-first route. The evidence cannot distinguish
which of those older-alpha entry points Robert used, and this report does not
invent an access event that was never logged.

## Backend and project ownership

| Concern | v1.9 | Dark v2 alpha | Grey chat-first |
|---|---|---|---|
| Owner UI | `app.py` | `kira_video_studio/ui.py` | `chat_first_studio/ui.py` |
| Core service | `studio_core.py` | `kira_video_studio/project_service.py` and related v2 modules | `chat_first_studio/service.py`, `store.py`, and graph/journal modules |
| Projects/outputs | `KiraVideos/StudioOutputs` | `KiraVideos/StudioOutputs/V2_PrivateTests` | `VideoStudioDevelopment/chat_first_production/runtime/projects` and per-project outputs |
| Research/facts | v1.9 search/source workflow | v2 four-pass claims/fact-sheet workflow | factuality executor requiring supplied/injected sources; no automatic handoff reader |
| Scripts | v1.9 outline/chapter generator | v2 evidence-bound script stages | persistent script schema/service; normal chat does not generate a natural finished script |
| Visual planning | slides and approved image-folder intake | v2 storyboard/review plus labeled concept-card/motion tools | attached/sourced media production plan; no connected image/video generator |
| Voice/render | v1.9 Robert voice/package builder | v2 approved voice and FFmpeg build pipeline | separate protected approved-voice adapter and local visual-first renderer |

Existing projects and outputs remain owned by the program that created them.
The current grey program does not transparently become the UI for v1.9 or v2
projects, which is why moving the normal button to it did not feel like a
simplification of the same Studio.

## Promised-feature truth table

| Promised feature | Classification | Evidence-based truth |
|---|---|---|
| Conversational video planner | **Implemented and connected, but only as a limited deterministic intake; the promised natural planner is absent** | The grey UI sends ordinary text to `interpret_chat`, but `intake.py` uses phrase/pattern matching and canned administrative replies. It has no Studio-bound Llama/Qwen conversation model. Raw JSON and technical state remain exposed. |
| Topic-dependent fact-sheet skipping | **Implemented and connected in chat-first** | `factuality.py` supports NONE/LIGHT/STANDARD/STRICT and AUTO. Future concepts can resolve to NONE; a Kira World update resolves to local-records-first STANDARD. This does not make handoff ingestion automatic. |
| Automatic handoff/document intake | **Documented promise only** | Chat-first has a local-first policy but no code that discovers, reads, ranks, or summarizes the main handoff and `System/Docs` from a natural request. Its factuality command expects claims/source JSON or an injected provider. v1.9 exposes a manual handoff-pack setting, not the promised automatic chat behavior. |
| Private concept-video planning | **Implemented but disconnected for labeled alpha concept cards/motion; requested generator integration absent** | The dark alpha can create clearly labeled offline concept cards and simple still-motion previews. The current chat-first route does not connect an image or video generator and cannot produce the requested generated concept video from the conversation. |
| Animated Robert selection | **Prototype/documented intent only; working feature absent** | Preserved Animated Robert hosts are rejected/deferred, and no accepted animated Robert performance is connected to chat-first. |
| Old-video restoration/upscaling | **Prototype/schema only** | The grey button and `archive_restoration_lab.py` record a bounded project foundation but perform no decode, restoration, enhancement, derivative creation, or upscale. Real-ESRGAN remains an unverified future candidate, not a connected tool. |
| Public personal-media finder | **Prototype/schema only** | The grey button can record owner-supplied local files, folders, archives, or catalog metadata. It performs no public-web search, login, retrieval, or download. |
| Face-match candidate search | **Absent** | `personal_media_finder.py` explicitly disables face search and biometric matching. No PimEyes-like candidate engine is implemented or connected. |

## Preserved future owner requirements

These are notes only, not authorization to resume development:

- one stable owner-facing program and one normal launcher;
- dark navy Kira Labs appearance, cyan/white text, restrained orange accents;
- one large natural conversation, one attachment control, and a readable plan
  or preview;
- technical state, hashes, factuality modes, and raw JSON hidden behind one
  optional **Advanced Details** control;
- incomplete restoration and media-finder functions hidden until real;
- one useful follow-up question at a time, without administrative phrases such
  as “project brief updated while preserving unmentioned work.”

## Integrity anchors

- v1.9 `FILE_HASHES.json` SHA-256:
  `5597e4e4030a36c53f3a2927734539644e0669ad5ca865326ab93927444a412c`
- dark alpha current UI SHA-256:
  `b36959f7c10ac7011fb13c7812cfa58abe870e1edbab050ac67d1bf6af19dce5`
- dark alpha current backend SHA-256:
  `51f5a0b7250d70a1ced99f8aa478e6de74da86bbb83e1f776a46b53b6df0da8f`
- chat-first launcher SHA-256:
  `f6c43cb22cb415bc28600cc9f38b538e378f73a5d4025820936e99ebdab53158`
- chat-first README SHA-256:
  `c1b76d6b48f18b7a7b15f1ddbd903aa294f669b5182bd22bf7fc0fef0876cf51`

All three installations and their existing evidence remain frozen and intact.
No repair or replacement is authorized by this audit.
