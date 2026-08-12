"""Build Robert's opaque private-reference intake manifest."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.private_owner_avatar_intake import (  # noqa: E402
    build_private_owner_manifest,
    write_private_owner_manifest,
)


def main() -> int:
    source = Path(r"C:\Users\robmc\Desktop\robert avatar base")
    outputs = []
    for subject_id, filename in (
        ("BIOLOGICAL_ROBERT_AVATAR", "BIOLOGICAL_ROBERT_AVATAR_REFERENCE_MANIFEST.json"),
        ("SYNTHETIC_ROBERT_TWIN_BODY", "SYNTHETIC_ROBERT_TWIN_BODY_REFERENCE_MANIFEST.json"),
    ):
        manifest = build_private_owner_manifest(
            source,
            subject_id=subject_id,
            owner_authorization=(
                "Robert explicit consolidated authority 2026-07-28: same protected "
                "reference set may be registered for exactly these two targets"
            ),
        )
        manifest["authorized_target_allowlist"] = [
            "BIOLOGICAL_ROBERT_AVATAR",
            "SYNTHETIC_ROBERT_TWIN_BODY",
        ]
        manifest["avatar_builder_construction_frozen"] = True
        output = ROOT / "Avatar" / "outputs" / "user" / filename
        write_private_owner_manifest(manifest, output)
        outputs.append(output)
        print(output)
        print(manifest["status"])
        print(f"references={manifest['reference_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
