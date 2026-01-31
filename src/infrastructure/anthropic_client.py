"""Anthropic Claude client wrapper."""

from anthropic import AsyncAnthropic
from ..config import settings


def get_anthropic_client() -> AsyncAnthropic:
    """Get AsyncAnthropic client instance."""
    return AsyncAnthropic(api_key=settings.anthropic_api_key)


# Global Anthropic client instance
anthropic_client = get_anthropic_client()
