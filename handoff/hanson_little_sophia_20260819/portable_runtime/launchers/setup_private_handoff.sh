#!/usr/bin/env sh
set -eu
if [ "$#" -ne 1 ]; then
  echo "Usage: $0 /full/path/to/hanson_little_sophia_20260819" >&2
  exit 2
fi
runtime_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$runtime_root"
python_exe=python3
if [ -x "$runtime_root/.venv-voice/bin/python" ]; then
  python_exe="$runtime_root/.venv-voice/bin/python"
fi
"$python_exe" -m portable_mind bootstrap-handoff --person kira --backend stub --handoff-root "$1" --approve-private-bootstrap
"$python_exe" -m portable_mind bootstrap-handoff --person synthetic_robert --backend stub --handoff-root "$1" --approve-private-bootstrap
echo "Private Kira/Robert handoff bootstrap verified; re-running is idempotent."
