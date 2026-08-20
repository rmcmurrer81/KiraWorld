#!/usr/bin/env sh
set -eu
runtime_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$runtime_root"
exec python3 -m portable_mind chat --person synthetic_robert --backend ollama --no-voice "$@"
