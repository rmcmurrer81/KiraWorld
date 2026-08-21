# Optional High-Resource Media and Group Experiment v1

## Status

This optional path is disabled by default.

It has **not been run or accepted on this machine** because the available RAM and GPU are not sufficient for a responsible multi-person, richer-media hardware test. The recommended hardware below is planning guidance, not proof that the feature will work on another computer.

The normal Kira World and text/voice launchers remain unchanged.

## What the launcher does

`Start_Kira_High_Resource_Media_Group_Experimental.bat` calls the existing Kira text and voice surface after an explicit command-line opt-in:

```text
Start_Kira_High_Resource_Media_Group_Experimental.bat --enable-experimental-high-resource
```

The wrapper requests up to four active text/voice sessions, budgets 32 GB of physical RAM per active session, and lets the existing hardware-aware policy reduce the actual capacity. It does not bypass person activation checks, source checks, identity boundaries, the ordered speech queue, or media-access controls.

This surface can select Kira, Robert, Lisa, and downloaded TemporaryAI candidates that are already eligible for the existing bounded chat path. The wrapper does not make an ineligible candidate eligible.

## Capability truth

| Capability | Classification | Exact boundary |
|---|---|---|
| Multiple-person text and voice group routing | Implemented | The existing group router keeps separate candidate sessions and uses the ordered voice queue. Physical RAM still caps capacity. |
| Portable book, script, and non-adult magazine reading | Implemented | Uses the separate portable index and paced reading records. Reading does not create lived memory or instant completion. |
| Indexed PDF/image presentation and indexed audio/video playback | Implemented | Only indexed local files can open. Presentation or playback does not prove attention, understanding, enjoyment, or completion. |
| Local speech recognition | Hardware-dependent | Uses the existing loopback ASR sidecar. Microphone capture starts off and requires an owner action. |
| One transient camera still | Hardware-dependent | Uses the existing bounded, non-identifying single-still path. This is not continuous visual understanding. |
| Local model and custom voice acceleration | Hardware-dependent | Requires compatible models, voice packs, drivers, GPU/VRAM, and free resources. Configuration alone does not provide them. |
| Continuous semantic video understanding | Not yet connected | No continuous interpretation or identity recognition is enabled. |
| Simultaneous animated 3D group bodies | Not yet connected | This experimental wrapper uses the existing text/voice surface. It grants no body and proves no multi-body render. |
| Automatic media enjoyment and completion claims | Not yet connected | The long-session route remains paced and reviewable; reactions and completion require grounded records. |

## Hardware guidance

- 64 GB RAM is a cautious planning target for trying two concurrent sessions.
- 128 GB RAM is the planning target for requesting the four-session ceiling used by the wrapper.
- A discrete GPU with approximately 16 GB VRAM is a reasonable planning target for richer local model, media, speech, and one-still vision experiments.
- Storage bandwidth, drivers, decoder support, local model installation, and free GPU memory still matter.

These numbers are not certification. The runtime measures physical RAM and can reduce the effective number of sessions. GPU presence does not prove that speech recognition, a custom voice, video decoding, or the one-still vision model is installed and ready.

## Portable library and resident library

The portable index is:

```text
Data/indexes/portable_media_library_index.json
```

The resident private index remains:

```text
Data/indexes/media_library_index.json
```

When both exist, the resident index remains primary and portable entries are added in memory only when their exact paths are not already present. The private index is never overwritten by the portable builder.

Reading recommendations use the same resident-first pattern. The resident preference file stays primary when present. A clean checkout uses `Data/reading/portable_reading_interest_profiles.json`, which contains neutral starting themes and no claimed active reading, favorites, or durable personal preference history.

The portable collection contains a small set of reviewed U.S. public-domain/no-known-restrictions books, a project-original short script, and a project-original non-adult magazine. Modern resident magazines and private-reference scripts are not copied into the portable set. No real-person avatar-reference photographs or Robert photographs are included.

## Reading boundary

The long-session reading route may choose a small source unit, pause, and save a reviewable reaction. It must not:

- claim a whole work was read instantly;
- convert fiction or source material into lived memory;
- create or activate a TemporaryAI automatically;
- claim media enjoyment without a grounded reaction;
- claim that displayed media provides a body, perception, or skill;
- use a camera or microphone unless the owner starts that exact temporary path.
