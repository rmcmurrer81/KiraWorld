#!/usr/bin/env python3
"""Non-destructively add functional interaction metadata to the prefab index."""
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Data.world_builder.build_item_prefab_library import (  # noqa: E402
    write_supplemental_interaction_manifest,
)


def main() -> int:
    report = write_supplemental_interaction_manifest()
    print(
        json.dumps(
            {
                "status": "completed",
                "generationMode": report["generationMode"],
                "prefabCount": report["prefabCount"],
                "runtimeReadyCount": report["runtimeReadyCount"],
                "sourceReadErrorCount": report["sourceReadErrorCount"],
                "output": report["output"],
                "prefabPayloadsCopied": report["prefabPayloadsCopied"],
                "prefabDescriptorsRewritten": report["prefabDescriptorsRewritten"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
