"""Anthropic Claude client wrapper."""

from anthropic import Anthropic
from ..config import settings


def get_anthropic_client() -> Anthropic:
    """
    Get Anthropic client instance.

    Returns:
        Configured Anthropic client
    """
    return Anthropic(api_key=settings.anthropic_api_key)


# Global Anthropic client instance
anthropic_client = get_anthropic_client()
