"""Fail-closed identity checks for the approved local Qwen 3.5 route."""

from __future__ import annotations

from typing import Any

from Core.model_request_policy import (
    QWEN_TEXT_VOICE_DIGEST,
    QWEN_TEXT_VOICE_MODEL,
    require_exact_qwen35_selection,
)


def ollama_tags_endpoint(chat_endpoint: Any) -> str:
    """Return the sibling ``/api/tags`` URL for a supported Ollama endpoint."""

    endpoint = str(chat_endpoint or "").strip().rstrip("/")
    for suffix in ("/api/chat", "/api/generate"):
        if endpoint.endswith(suffix):
            return endpoint[: -len(suffix)] + "/api/tags"
    raise RuntimeError("exact Qwen identity check requires an Ollama /api/chat endpoint")


def require_installed_exact_qwen35(
    requests_client: Any,
    *,
    chat_endpoint: Any,
    model_name: Any,
    model_digest: Any,
    timeout: int,
) -> dict[str, str]:
    """Prove the exact installed name and digest without loading the model."""

    expected_model, expected_digest = require_exact_qwen35_selection(
        model_name,
        model_digest,
    )
    response = requests_client.get(
        ollama_tags_endpoint(chat_endpoint),
        timeout=max(1, min(int(timeout), 15)),
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
        raise RuntimeError("Ollama tags response did not contain a model list")

    matching: dict[str, Any] | None = None
    for item in payload["models"]:
        if not isinstance(item, dict):
            continue
        names = {
            str(item.get("name") or "").strip(),
            str(item.get("model") or "").strip(),
        }
        if expected_model in names:
            matching = item
            break
    if matching is None:
        raise RuntimeError("the exact approved qwen3.5:9b model is not installed")

    observed_digest = str(matching.get("digest") or "").strip().casefold()
    if observed_digest != expected_digest:
        raise RuntimeError("the installed qwen3.5:9b digest does not match the approved digest")
    return {"model": expected_model, "digest": expected_digest}


def require_exact_qwen35_response_model(
    payload: Any,
    *,
    expected_model: Any = QWEN_TEXT_VOICE_MODEL,
) -> str:
    """Reject a model response that is not attributed to exact Qwen 3.5."""

    require_exact_qwen35_selection(expected_model, QWEN_TEXT_VOICE_DIGEST)
    if not isinstance(payload, dict):
        raise RuntimeError("Ollama response was not a JSON object")
    observed_model = str(payload.get("model") or "").strip()
    if observed_model != QWEN_TEXT_VOICE_MODEL:
        raise RuntimeError("Ollama returned a response from an unapproved model")
    return observed_model
