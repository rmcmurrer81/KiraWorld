#!/usr/bin/env sh
set -eu
runtime_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$runtime_root"
if [ -x "$runtime_root/.venv-voice/bin/python" ]; then
  exec "$runtime_root/.venv-voice/bin/python" -m portable_mind chat --person synthetic_robert --backend ollama "$@"
fi
exec python3.11 -m portable_mind chat --person synthetic_robert --backend ollama "$@"
