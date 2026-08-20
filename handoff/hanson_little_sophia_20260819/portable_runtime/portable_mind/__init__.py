"""Portable, public-safe persistent conversational runtime for Kira and Synthetic Robert."""

from .backends import DEFAULT_MODEL
from .runtime import ConversationRuntime, RuntimeResponse

__all__ = ["ConversationRuntime", "RuntimeResponse", "DEFAULT_MODEL"]
__version__ = "0.1.0"
