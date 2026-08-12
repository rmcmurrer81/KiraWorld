"""Model-specific fields for ordinary local-model requests."""

from __future__ import annotations

import os
from typing import Any


QWEN_TEXT_VOICE_MODEL = "qwen3.5:9b"
QWEN_TEXT_VOICE_DIGEST = (
    "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
)


def pin_exact_qwen35_environment() -> tuple[str, str]:
    """Pin and validate the only currently authorized person-model route.

    A caller may inherit the approved values or start without model variables;
    in the latter case the approved constants are installed.  An inherited
    conflicting or blank value fails closed.  This prevents a stale shell from
    silently selecting an older local model.
    """

    os.environ.setdefault("KIRA_MODEL_NAME", QWEN_TEXT_VOICE_MODEL)
    os.environ.setdefault("KIRA_MODEL_DIGEST", QWEN_TEXT_VOICE_DIGEST)
    return require_exact_qwen35_selection(
        os.environ.get("KIRA_MODEL_NAME"),
        os.environ.get("KIRA_MODEL_DIGEST"),
    )


def require_exact_qwen35_selection(
    model_name: Any,
    model_digest: Any,
) -> tuple[str, str]:
    """Return the exact approved identity or raise before model execution."""

    normalized_model = str(model_name or "").strip().casefold()
    normalized_digest = str(model_digest or "").strip().casefold()
    if normalized_model != QWEN_TEXT_VOICE_MODEL:
        raise RuntimeError(
            "current person routes require exact qwen3.5:9b; alternate-model "
            "selection is disabled"
        )
    if normalized_digest != QWEN_TEXT_VOICE_DIGEST:
        raise RuntimeError(
            "current person routes require the approved qwen3.5:9b digest; "
            "a missing or mismatched digest fails closed"
        )
    return QWEN_TEXT_VOICE_MODEL, QWEN_TEXT_VOICE_DIGEST


def ordinary_model_request_fields(
    model_name: Any,
    *,
    keep_alive: Any = 0,
    release_residency: bool = False,
) -> dict[str, Any]:
    """Return top-level request fields required by an ordinary model turn.

    Qwen 3.5 supports a thinking mode, but current person routes are
    intentionally non-thinking and release Ollama residency after the response
    so the approved GPU voice can own the GPU next. Bounded lifecycle probes
    may explicitly pass ``keep_alive="10m"``. Unknown models receive no Qwen
    fields; current person routes reject them through
    :func:`require_exact_qwen35_selection` before execution.
    """

    normalized = str(model_name or "").strip().casefold()
    if normalized == QWEN_TEXT_VOICE_MODEL:
        return {"think": False, "keep_alive": keep_alive}
    return {}
