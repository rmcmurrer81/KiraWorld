# KiraWorld

Portable review snapshot and development history for Kira World.

This repository contains runnable source, tests, controlling documents,
configuration schemas, reviewed continuity packages, selected reading material,
reviewed voice assets, and bounded 3D review assets. It is not a bit-for-bit
copy of the resident workspace. Private runtime state, raw conversations, model
weights, caches, large unreviewed libraries, recursive backups, and generated
build output remain outside the repository.

## What to open or click

On Windows, start at the repository root:

1. **`Start_Kira_Text_Voice_Chat.bat` — main and familiar chat interface.**
   This is the normal one-person-at-a-time interface. Select or switch among
   all people currently eligible for that interface; it is not Kira-only.
   Kira and Synthetic Robert are selected here in ordinary use.
2. **`Start_Downloaded_People_Chat.bat` — optional direct-selection menu for
   checkout reviewers.** This does not replace the main interface. It provides
   a direct choose/open route for downloaded or created candidates such as
   Lisa, H. H. Holmes, Kathryn, Peter, Marinette/Ladybug, and published experts
   when each profile and route passes validation.
3. **`Synthetic Robert Text and Voice Chat.cmd` — optional direct Synthetic
   Robert reviewer route.** It is inside the `portable_runtime/launchers`
   folder. Robert remains available in the main chat and World Shell; this
   separate route simply makes his persistent reviewed package easier to open
   directly.
4. **`Start_Kira_World_Shell.bat` — 3D World Shell.** It starts with one active
   person by default. A person with an accepted body uses that body; a bodyless
   person appears as a gently moving named orb. The shell also supports an
   explicitly enabled, RAM-limited sequential group conversation.
5. **`Start_Kira_World_Builder_Workspace.bat` — World Builder Workspace.** This
   is a lightweight, non-3D draft request generator. It records source-labeled
   notebook-world requests for review; it does not by itself generate or
   activate a finished world.
6. **`Run_Hanson_ROS2_Bridge_Standalone_Validation.bat` — select one person and
   exercise the bridge without ROS 2 or hardware.** It runs the 88 bridge tests
   plus deterministic mock policy/session demonstrations for that exact person
   id. It does not attach that person's running chat or life loop.
7. **`Start_Hanson_ROS2_Bridge_Simulator_Demo.bat` — optional ROS 2 simulator
   policy-admission route.** It requires WSL/Linux ROS 2 and a completed,
   validated official interface intake. It still connects only deterministic
   demo intentions to the simulator policy path; physical-body execution is
   blocked.

The planned future embodiment-pod flow is: select a person whose life loop is
active, enter a chamber or pod, verify identity, body readiness, safety,
heartbeat, one-endpoint, and rollback requirements, bind that same session to
the body endpoint, then return it to its avatar or named orb on exit or failure.
The repository does not yet provide the authenticated World Shell intention
stream, official physical adapter, hardware safe-state implementation, or
avatar/orb rebind seam needed to perform that complete flow.

To enable a group in the World Shell on a larger Windows computer, set the
requested capacity in the same terminal before starting it:

```bat
set KIRA_WORLD_GROUP_SESSIONS=1
set KIRA_WORLD_MAX_ACTIVE_SESSIONS=4
Start_Kira_World_Shell.bat
```

Capacity is capped by detected physical RAM at a default budget of 32 GiB per
active session and a hard maximum of eight. Invalid or unavailable capacity
information fails closed to one active session. Adding a group participant is
still explicit; starting the shell never activates a group automatically.

## Clean-clone setup

Install Git LFS before relying on any large voice, PDF, or 3D asset:

```bash
git lfs install
git lfs pull
git lfs fsck
```

`git lfs fsck` must finish without a missing or corrupt object. A successful
source checkout without `git lfs pull` can still contain pointer text instead
of the real binary files.

Install the JavaScript dependencies from the checked-in lock files and verify
both current browser surfaces:

```bash
cd Avatar/runtime3d
npm ci
npm run build
cd ../../Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview
npm ci
npm run build
```

Do not copy `node_modules` or `dist` from another computer. `npm ci` recreates
dependencies from the matching lock file, and `npm run build` recreates the
build output. The Home World preview is a bounded review surface; its
successful build is not evidence that every resident world, body, or asset is
present or accepted.

## Verified portable runtime lane

Locate the repository's `portable_runtime` directory and run these commands
from inside it. The standard offline lane discovers 165 tests: the frozen
result is 162 passes and three expected skips when the two exact private voice
fixtures and Windows symlink permission are unavailable.

Windows:

```powershell
py -B -m unittest discover -s tests -v
py -B -m portable_mind chat --person kira --backend stub --no-voice
py -B -m portable_mind chat --person synthetic_robert --backend stub --no-voice
```

Linux or macOS:

```bash
python3 -B -m unittest discover -s tests -v
python3 -B -m portable_mind chat --person kira --backend stub --no-voice
python3 -B -m portable_mind chat --person synthetic_robert --backend stub --no-voice
```

The deterministic stub verifies installation, storage, identity isolation,
and interfaces; it is not the conversational model. The tested local baseline
is loopback-only Ollama `qwen3.5:9b` with manifest SHA-256:

```text
6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7
```

Run the baseline with:

```powershell
ollama pull qwen3.5:9b
py -B -m portable_mind model-info --person kira --backend ollama
py -B -m portable_mind chat --person kira --backend ollama --no-voice
```

A larger or newer model may be evaluated by supplying both its tag and the
exact digest resolved on the review computer:

```powershell
py -B -m portable_mind chat --person kira --backend ollama --no-voice `
  --model YOUR_MODEL_TAG `
  --expected-model-digest YOUR_EXACT_64_HEX_DIGEST
```

Never promote a mutable tag alone. Record the model tag, resolved digest,
Ollama version, context size, sampling settings, profile hash, and test date,
then rerun the same isolated tests and behavioral evaluation. A stronger model
can change quality, latency, and memory use; it does not create or transfer an
identity.

Neural voice is a separate external dependency lane. The pinned route requires
Python 3.11, Chatterbox TTS, a platform-appropriate PyTorch/Torchaudio build,
downloaded model weights, and an exact identity-bound voice pack plus its
authorization record. The tracked `Voice/` tree includes curated reviewed
assets and profiles, but not every engine weight or platform dependency.
Missing, unauthorized, mismatched, or unavailable exact voice support fails
closed to text-only for Kira and Synthetic Robert. Transitive platform
dependencies are not fully hash-locked, so run the supplied environment and
voice checks before enabling speech.

## Verified Hanson bridge lane

The standalone bridge can be exercised without ROS 2 or robot hardware:

```bash
cd integrations/hanson_ros2_bridge
python -m pip install -r standalone/requirements.txt
python -W error -m unittest discover -s standalone/tests
python standalone/demo.py
python standalone/session_demo.py
python standalone/verify_evidence.py standalone/evidence.jsonl
```

The expected test result is `Ran 88 tests` followed by `OK`. These tests verify
the standalone policy, schema, mock lifecycle, and evidence-chain behavior.
They do not prove execution on Hanson hardware; physical integration still
requires the vendor environment, allowlists, safety review, and hardware tests.

## World Builder and preview boundary

The World Builder Workspace creates draft requests and supporting review files.
It is a planning/request tool, not an autonomous finished-world generator.
The separate strict procedural preview lane can consume a separately
authorized, exact-hash-bound scene program and emit one immutable bounded
preview. It does not promote the request, register a live world, mutate Home
World, or prove parity with the much larger resident workspace.

## Main repository map

- `Core/` — runtime, policy, continuity, voice-routing, and validation source
- `Testing/` — offline and integration tests
- `tools/` — launch, audit, builder, and review utilities
- `TemporaryAI/` — creator packages, candidates, experts, and templates
- `Avatar/` — Avatar Builder, anatomy contracts, runtime-3D source, and
  reviewed reference charts/assets
- `Voice/` — curated reviewed voice outputs, reference packs, profiles, and
  engine configuration; large engine weights remain external
- `Kira/` — Kira identity, backstory, and core-memory documents
- `Lisa/` — Lisa backstory, core, and shared Kira/Lisa continuity
- `Data/` — curated continuity, reading, Home World, World Builder, and runtime
  schemas; resident-private state is not included
- `System/Docs/` — approved current and historical documents, including the
  tracked PDF collection
- `integrations/hanson_ros2_bridge/` — standalone and prototype ROS 2 bridge
- `BACKUP_SCOPE.md` — exact inclusion and exclusion boundary

The owner proposes that Hanson Robotics build on Kira World as a continuity
home for humanoid software deployments: while a physical body is charging,
being repaired, or receiving an upgrade, the deployment could remain active in
a bounded virtual environment for conversation, creative work, and reviewed
life-loop growth. This is a collaboration proposal, not a completed or official
Hanson integration and not a claim of literal biological or conscious transfer.

Static candidates and historical documents are not live-feature evidence.
No body is complete until exact Blender/body/save/reload/render evidence is
independently accepted.
