"""Bounded engineering probe for the bundled CC0 MakeHuman female foundation.

This deliberately reuses only the generic parser/topology/boolean methodology
from the male engineering probe.  It replaces every identity/proportion target
with official MakeHuman female macro targets and does not read any Robert
candidate, photograph, measurement, morph, or private-review directory.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools" / "blender_build_makehuman_parametric_male_foundation.py"

spec = importlib.util.spec_from_file_location("makehuman_generic_foundation", SOURCE)
if spec is None or spec.loader is None:
    raise RuntimeError(f"could not load generic MakeHuman methodology: {SOURCE}")
generic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generic)

generic.TARGETS = (
    (
        generic.MAKEHUMAN_DATA
        / "targets"
        / "macrodetails"
        / "universal-female-young-averagemuscle-averageweight.target",
        1.0,
    ),
    (
        generic.MAKEHUMAN_DATA
        / "targets"
        / "macrodetails"
        / "caucasian-female-young.target",
        1.0,
    ),
)
# The bundled ``helper-genital`` component is an explicitly male attachment.
# The official female macro target already shapes the closed body surface; do
# not import the male helper into a female candidate.
generic.RENDER_GROUPS = {"body"}

generic.main()
