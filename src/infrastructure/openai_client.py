"""OpenAI client wrapper (async).

Uses httpx to call OpenAI Chat Completions.

Env:
- OPENAI_API_KEY
- OPENAI_MODEL

Note: this is used only when settings.llm_provider == 'openai' and LLM_MODE=real.
"""

from __future__ import annotations

import httpx

from ..config import settings


OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"


async def openai_chat_complete(
    *,
    prompt: str,
    system: str,
    model: str | None = None,
    max_tokens: int = 2048,
    return_usage: bool = False,
) -> str | tuple[str, dict]:
    api_key = settings.openai_api_key
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai and LLM_MODE=real")

    if model is None:
        model = settings.openai_model

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(OPENAI_CHAT_COMPLETIONS_URL, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    try:
        text = data["choices"][0]["message"]["content"]
    except Exception as e:
        raise RuntimeError(f"Unexpected OpenAI response shape: {data}") from e

    if not return_usage:
        return text

    usage = data.get("usage") or {}
    return (
        text,
        {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "raw": usage,
        },
    )
