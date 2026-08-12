#!/usr/bin/env python3
"""Exact-root bootstrap for the unchanged R23 fresh-reopen verifier.

Blender does not necessarily place the project root on its embedded Python
``sys.path``.  This bootstrap adds only the hash-bound project's exact root,
verifies the unchanged worker, and executes that exact file.  It neither reads
nor depends on ``PYTHONPATH`` and performs no Blend, render, or output work of
its own.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import runpy
import sys


EXPECTED_PROJECT_ROOT = Path(r"C:\Users\robmc\Kira")
WORKER_RELATIVE_PATH = Path("tools/blender_verify_kira_r23_postsave_fresh_reopen.py")
WORKER_BYTES = 55260
WORKER_SHA256 = "5dbf4faaef09a82717989f5e7bc17312d5182b0042e39475aa5b47f131f3a1b5"


class ExactRootBootstrapError(RuntimeError):
    """Fail-closed bootstrap binding error."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def exact_project_root() -> Path:
    derived = Path(__file__).resolve().parents[1]
    expected = EXPECTED_PROJECT_ROOT.resolve()
    if derived != expected:
        raise ExactRootBootstrapError(
            f"bootstrap project root mismatch: {derived} != {expected}"
        )
    return derived


def install_exact_project_root(root: Path) -> None:
    exact_text = str(root)
    equivalent_indices: list[int] = []
    for index, value in enumerate(sys.path):
        try:
            if Path(value).resolve() == root:
                equivalent_indices.append(index)
        except (OSError, RuntimeError, TypeError, ValueError):
            continue
    for index in reversed(equivalent_indices):
        del sys.path[index]
    sys.path.insert(0, exact_text)


def verified_worker(root: Path) -> Path:
    worker = root / WORKER_RELATIVE_PATH
    if not worker.is_file() or worker.is_symlink():
        raise ExactRootBootstrapError("bound fresh-reopen worker is absent or linked")
    if worker.stat().st_size != WORKER_BYTES:
        raise ExactRootBootstrapError("bound fresh-reopen worker byte size drifted")
    if sha256_file(worker) != WORKER_SHA256:
        raise ExactRootBootstrapError("bound fresh-reopen worker SHA-256 drifted")
    return worker


def main() -> None:
    root = exact_project_root()
    install_exact_project_root(root)
    worker = verified_worker(root)
    runpy.run_path(str(worker), run_name="__main__")


if __name__ == "__main__":
    main()
