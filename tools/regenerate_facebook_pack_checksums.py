"""Regenerate the deterministic SHA-256 manifest for the desktop Facebook pack."""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path


PACK = Path.home() / "Desktop" / "facebook"
MANIFEST = PACK / "06_provenance" / "checksums_sha256.txt"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    paths = sorted(
        (path for path in PACK.rglob("*") if path.is_file() and path != MANIFEST),
        key=lambda path: path.relative_to(PACK).as_posix().lower(),
    )
    lines = [
        f"# SHA-256 manifest regenerated {date.today().strftime('%B %d, %Y')} after clean video finalization. This manifest intentionally excludes itself."
    ]
    for path in paths:
        lines.append(f"{sha256(path)}  {path.relative_to(PACK).as_posix()}")
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(paths)} hashes to {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
