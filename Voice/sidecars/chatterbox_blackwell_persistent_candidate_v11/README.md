# Blackwell typed-memory integration candidate v11

This append-only, default-off candidate integrates the independently accepted
v10 pointer-width Windows memory probe into the exact sealed v8 live adapter
while retaining the v9 dual-process Job topology.

It is **not production routing** and it authorizes no live run. Static-fixture
mode delegates to the exact v8 fixture without importing the live adapter.
The current worker and parent refuse live mode unconditionally. The exact
adapter-install helper exists only for later harness authoring and static
verification. A successor needs its own exact audit and new one-shot capability
before it may call that helper; consumed V8/V9 live authority is not reused.

No Qwen model, Chatterbox model, voice profile, reference audio, playback
policy, person state, body, media route, or Blender path is changed here.
Successful static tests are not owner hearing and do not prove a latency
improvement. A later separately sealed and audited bounded harness would be
required to measure that.
