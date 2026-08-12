"""Explicitly cache the bounded TemporaryAI speaker-consistency model."""
from __future__ import annotations

import json

from huggingface_hub import HfApi, snapshot_download


MODEL_ID = "microsoft/wavlm-base-plus-sv"


def main() -> int:
    info = HfApi().model_info(MODEL_ID)
    revision = str(info.sha or "main")
    # Resolve through the public ``main`` ref so Hugging Face also writes the
    # local refs/main pointer used by the ordinary cache-only analyzer.  The
    # resolved commit is still recorded below for reproducibility.
    path = snapshot_download(
        repo_id=MODEL_ID,
        revision="main",
        allow_patterns=[
            "README.md",
            "config.json",
            "preprocessor_config.json",
            "pytorch_model.bin",
        ],
    )
    print(
        json.dumps(
            {
                "status": "speaker_consistency_model_cached",
                "model_id": MODEL_ID,
                "resolved_revision": revision,
                "cache_path": path,
                "purpose": "cross-source speaker consistency evidence only",
                "identity_proof": False,
                "voice_training_or_cloning": False,
                "voice_assignment": False,
                "activation": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
