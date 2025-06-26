"""Utility functions for the workflow module."""

from .state import GraphState


def get_last_user_message_content(state: GraphState) -> str:
    """Extracts the content of the most recent user message from the state."""
    messages = state.get("messages", [])
    for msg in reversed(messages):
        if msg.get("role") == "user":
            # Return stripped content. Caller can decide to .lower() if needed.
            return msg.get("content", "").strip()
    return ""


def is_api_key_error(error: Exception) -> bool:
    """
    Check if an exception is related to API key authentication issues.

    Args:
        error: The exception to check

    Returns:
        bool: True if the error appears to be related to API key issues
    """
    error_str = str(error).lower()
    error_type = type(error).__name__.lower()

    # Check for common API key error indicators
    api_key_indicators = [
        "api key",
        "openrouter",
        "unauthorized",
        "authentication",
        "401",
        "403",
        "invalid api key",
        "missing api key",
        "authenticationerror",
        "permission denied",
    ]

    return any(
        indicator in error_str or indicator in error_type
        for indicator in api_key_indicators
    )


def get_api_key_error_message() -> str:
    """
    Get a standardized error message for API key issues.

    Returns:
        str: Formatted error message for API key problems
    """
    return (
        "❌ **API Configuration Error**: The OpenRouter API key is missing or invalid. "
        "Please check your API key configuration and try again."
    )
