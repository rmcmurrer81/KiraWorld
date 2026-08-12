# GPU Media First-Look Bridge v1

## Purpose

Kira and Lisa now have a GPU bridge stage, so the system can begin moving beyond title/metadata-only media previews.

This bridge creates reviewed first-look notes for images and limited video-frame samples. It is not the same as full watching/listening.

## Current Capability

Added tool:

```text
tools/create_gpu_media_first_look_note.py
Start_Kira_GPU_Media_First_Look.bat
```

The tool can:

```text
- create a timestamped first-look JSON note
- create a readable monitor Markdown note
- record image metadata
- use an image itself as a visual sample
- sample video frames if ffmpeg is installed later
- call an optional Ollama vision model if configured
```

Current local model list only includes:

```text
llama3.1:8b
```

That is not a vision model. Until a vision model is installed and selected, first-look notes are metadata/sample notes only.

## Usage

Clickable:

```text
Start_Kira_GPU_Media_First_Look.bat
```

Command line:

```powershell
py tools\create_gpu_media_first_look_note.py "Avatar/library/female/face_structure/female_face_structure_reference_001.jpg" --viewer kira
py tools\create_gpu_media_first_look_note.py "Data/library/movies/example.mp4" --viewer kira --vision-model llava:7b
```

Outputs:

```text
Data/media/gpu_first_look_notes/<note_id>/<note_id>.json
Data/media/gpu_first_look_notes/<note_id>/<note_id>.monitor.md
```

## Important Distinctions

Preview card:

```text
This sounds interesting based on title/metadata/summary.
```

First-look visual note:

```text
I have a reviewed visual sample or frame description.
```

Watching/listening note:

```text
Kira or Lisa actually watched/listened/read a session and reacted.
```

Memory:

```text
Only promoted after review. Media experience is not lived personal history.
```

## Policy

First-look notes must not create:

```text
- lived memory
- canon claims
- TemporaryAI profiles
- relationship claims
- proof that Kira/Lisa watched a full movie/video
```

First-look notes may support:

```text
- curiosity
- visual reference
- avatar/body/style discussion
- media preview browsing
- later watched/listened session planning
- TemporaryAI source review after human/Codex approval
```

## Next Improvements

Recommended next steps:

```text
1. Install or choose a local vision model for Ollama.
2. Install ffmpeg so video frame sampling works.
3. Add audio transcription/listening notes.
4. Add a review panel for first-look notes.
5. Feed approved first-look summaries into the future video-store/media room UI.
```
