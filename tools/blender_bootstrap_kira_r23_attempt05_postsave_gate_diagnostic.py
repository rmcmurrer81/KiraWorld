#!/usr/bin/env python3
"""Exact-root bootstrap for the bound read-only R23 gate diagnostic."""

from __future__ import annotations

import hashlib
from pathlib import Path
import runpy
import sys


EXPECTED_PROJECT_ROOT = Path(r"C:\Users\robmc\Kira")
WORKER_RELATIVE_PATH = Path("tools/blender_diagnose_kira_r23_attempt05_postsave_gates.py")
WORKER_BYTES = 26042
WORKER_SHA256 = "1ff006eef75b64d472e249a5711bb4c4e07fe5e94d10ec08dcbeedcb627c2ca2"


class DiagnosticBootstrapError(RuntimeError):
    """Fail-closed exact-root or worker-binding error."""


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
        raise DiagnosticBootstrapError(
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
        raise DiagnosticBootstrapError("bound diagnostic worker is absent or linked")
    if worker.stat().st_size != WORKER_BYTES:
        raise DiagnosticBootstrapError("bound diagnostic worker byte size drifted")
    if sha256_file(worker) != WORKER_SHA256:
        raise DiagnosticBootstrapError("bound diagnostic worker SHA-256 drifted")
    return worker


def main() -> None:
    root = exact_project_root()
    install_exact_project_root(root)
    worker = verified_worker(root)
    runpy.run_path(str(worker), run_name="__main__")


if __name__ == "__main__":
    main()
