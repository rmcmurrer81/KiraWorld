#!/usr/bin/env sh
set -eu
runtime_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$runtime_root"
command -v python3.11 >/dev/null 2>&1 || {
  echo "Python 3.11 is required before voice setup." >&2
  exit 2
}
python3.11 -m venv .venv-voice
python_exe="$runtime_root/.venv-voice/bin/python"
"$python_exe" -m pip install --upgrade pip
# Platform dependencies are not fully hash-locked; voice-env-check verifies their versions.
"$python_exe" -m pip install chatterbox-tts==0.1.7
"$python_exe" -m pip uninstall -y chatterbox-tts
"$python_exe" -m pip install --no-deps --require-hashes -r voice-package-hash.lock
"$python_exe" -m portable_mind voice-env-check --person kira --backend stub --allow-download
echo "Direct Chatterbox wheel and pinned model files verified. Validate synthesis/listening separately."
