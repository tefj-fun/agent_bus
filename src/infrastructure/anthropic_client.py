"""Anthropic Claude client wrapper."""

from anthropic import AsyncAnthropic
from ..config import settings


def get_anthropic_client() -> AsyncAnthropic:
    """Get AsyncAnthropic client instance."""
    # In mock mode, return None - agents should check settings.llm_mode
    if settings.llm_mode == "mock":
        return None
    return AsyncAnthropic(api_key=settings.anthropic_api_key)


# Global Anthropic client instance (None in mock mode)
anthropic_client = get_anthropic_client()
