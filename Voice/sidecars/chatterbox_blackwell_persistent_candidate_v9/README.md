# Blackwell v9 venv-launcher descendant identity repair

Status: **inactive, static-only, default-off, pending a different-agent audit**.

V8 live attempt 01 proved that the configured Windows virtual-environment
`python.exe` is a PSF `venvlauncher` root. It starts the exact base-Python
interpreter as its child, and that child owns the JSONL worker protocol. The v7
boundary bound the root correctly but rejected the child's otherwise valid
readiness because it required one PID to be both processes.

V9 changes only that boundary:

- the exact venvlauncher is created suspended, assigned to the retained Job,
  identified from its process handle, and then resumed;
- readiness must name a distinct PID whose Toolhelp parent is exactly that
  launcher root—not an arbitrary descendant;
- that exact PID is opened and its OS creation token, resolved executable path,
  SHA-256, size, volume serial, and file index must match both readiness and the
  sealed base-Python identity;
- the exact child handle must prove membership in the same retained Job;
- every response remains bound to the retained child PID, process-identity
  digest, and worker-instance ID;
- cleanup retains separate root/child truth and closes the child handle only
  after the Job-owned tree has exited.

The v8 worker is reused byte-for-byte. V2-v8, the consumed live attempt 01,
its audits, its postmortem, approved routing, and production fallback remain
unchanged.

Static tests may run the sealed v8 `--static-fixture` branch through the exact
launcher topology. They do not import or run Ollama, Qwen, Torch, CUDA,
Chatterbox, audio synthesis, playback, a person, or Blender. Hostile tests must
prove rejection of a grandchild protocol owner, a changed launcher identity,
and a changed worker identity, with Job cleanup evidence for every case.

No v9 live attempt is authorized by these files. A different agent must first
audit the exact v9 seal and create the configured append-only authorization for
one bounded live `attempt_02`. The v9 author must not create that authorization.
