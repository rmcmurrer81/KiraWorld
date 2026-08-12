# Blackwell persistent voice candidate v4

Status: **inactive static repair candidate pending fresh independent audit and
bounded RAM/GPU owner-hearing acceptance**.

V4 is append-only.  It preserves sealed v2 and rejected v3 byte-for-byte and
repairs the ten blockers reproduced by the v3 fresh audit.  It is not wired to
production, cannot play audio, and contains no CPU synthesis, Llama, SAPI,
generic voice, substitute-reference, or internal fallback route.

The canonical on-disk config is compared to hard-coded immutable identity and
route invariants.  Injected config must be byte-equivalent in meaning.  Every
RAM/commit/VRAM value is finite, nonnegative, and internally consistent.
Park, resume, synthesis, and unload re-prove real owned-object device and
condition identity.  Synthesis accepts a closed request schema and supplies
the exact approved audio-prompt path internally.

The Qwen coordinator owns full load-only and streamed-call lifecycles.  Its
control lock permits cancellation to enter while the shared CUDA/Qwen lock is
held.  Cleanup cannot report success or clear ownership until exact unload,
fresh Qwen absence, CUDA cleanup, and measured resource return are proven.

All included tests are standard-library fakes.  They do not invoke a model,
GPU, CUDA, audio, playback, camera/microphone, person state, or Blender.
