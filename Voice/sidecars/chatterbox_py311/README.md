# Isolated Kira Chatterbox Python 3.11 sidecar

This one-shot sidecar preserves the approved Kira Chatterbox 0.1.7 voice while
leaving the global Python 3.14 environment unchanged.

- Python: 3.11.9, side-by-side user installation.
- Environment: `.venv` under this directory; excluded from checkpoints.
- Chatterbox: exactly 0.1.7.
- Torch/Torchaudio: exactly 2.6.0+cu124.
- Compute: CPU. The pinned supported stack exposes kernels only through
  `sm_90`, while the RTX 5060 Ti reports `sm_120`; the sidecar does not pretend
  that unsupported CUDA execution passed.
- Input: one bounded JSON request on stdin, channel
  `public_spoken_only`; private/factual channel markers are rejected.
- Output: one bounded JSON result on stdout plus a PCM16 WAV under an approved
  project output root. Playback is always false.
- Network: Hugging Face and Transformers offline/cache-only mode is mandatory.
- Voice: only the hash-sealed approved Kira profile/reference is accepted. No
  SAPI or generic voice can satisfy the contract.
- Lifetime: one synthesis request per process; model and resources are released
  by cleanup and process exit.

`requirements.lock.txt` pins every installed distribution. The raw pip install
reports preserve archive URLs and SHA-256 values, while
`evidence/dependency_manifest.json` binds those archives to installed versions,
METADATA/RECORD hashes, Python, the voice profile, and the approved reference.

Rebuild the environment only through a new reviewed changed-file checkpoint.
Never copy `.venv` into a checkpoint or replace the global Python environment.
