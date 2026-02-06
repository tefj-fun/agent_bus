"""Best-effort LLM pricing fetcher for current provider/model."""

from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Any, Dict, Optional, Tuple

import httpx

from ..config import settings


_cached_pricing: Dict[str, Any] = {}
_last_refresh: float = 0.0
_refresh_lock = asyncio.Lock()


def _load_env_pricing() -> Dict[str, Any]:
    raw = (settings.llm_pricing_json or "").strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def get_pricing() -> Dict[str, Any]:
    if _cached_pricing:
        return _cached_pricing
    return _load_env_pricing()


def _extract_prices_near(
    text: str, model: str
) -> Optional[Tuple[float, float]]:
    """Extract input/output prices near a model mention.

    Returns (input_per_1k, output_per_1k) or None.
    """
    idx = text.lower().find(model.lower())
    if idx == -1:
        return None

    window = text[idx : idx + 1200]
    prices = re.findall(r"\$([0-9]+(?:\.[0-9]+)?)", window)
    if len(prices) < 2:
        return None

    unit_match = re.search(r"per\s*1\s*(m|k)", window, re.IGNORECASE)
    unit = unit_match.group(1).lower() if unit_match else "m"
    factor = 1000.0 if unit == "m" else 1.0

    try:
        input_price = float(prices[0]) / factor
        output_price = float(prices[1]) / factor
        return (input_price, output_price)
    except Exception:
        return None


async def _fetch_openai_pricing(model: str) -> Optional[Dict[str, Any]]:
    url = "https://openai.com/api/pricing/"
    async with httpx.AsyncClient(timeout=settings.pricing_request_timeout) as client:
        resp = await client.get(
            url,
            headers={"User-Agent": settings.pricing_user_agent},
            follow_redirects=True,
        )
        resp.raise_for_status()
        text = resp.text

    prices = _extract_prices_near(text, model)
    if not prices:
        return None
    input_per_1k, output_per_1k = prices
    return {
        "openai": {
            model: {
                "input_per_1k": input_per_1k,
                "output_per_1k": output_per_1k,
                "source": url,
                "fetched_at": time.time(),
            }
        }
    }


async def _fetch_anthropic_pricing(model: str) -> Optional[Dict[str, Any]]:
    url = "https://www.anthropic.com/pricing"
    async with httpx.AsyncClient(timeout=settings.pricing_request_timeout) as client:
        resp = await client.get(
            url,
            headers={"User-Agent": settings.pricing_user_agent},
            follow_redirects=True,
        )
        resp.raise_for_status()
        text = resp.text

    prices = _extract_prices_near(text, model)
    if not prices:
        return None
    input_per_1k, output_per_1k = prices
    return {
        "anthropic": {
            model: {
                "input_per_1k": input_per_1k,
                "output_per_1k": output_per_1k,
                "source": url,
                "fetched_at": time.time(),
            }
        }
    }


def _merge_pricing(base: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base or {})
    for provider, provider_data in incoming.items():
        if provider not in merged or not isinstance(merged[provider], dict):
            merged[provider] = {}
        for model, model_data in (provider_data or {}).items():
            merged[provider][model] = model_data
    return merged


async def refresh_pricing(force: bool = False) -> Dict[str, Any]:
    """Refresh pricing for the current provider/model (best-effort)."""
    global _cached_pricing, _last_refresh

    ttl = settings.pricing_refresh_seconds
    if not force and _cached_pricing and (time.time() - _last_refresh) < ttl:
        return _cached_pricing

    async with _refresh_lock:
        if not force and _cached_pricing and (time.time() - _last_refresh) < ttl:
            return _cached_pricing

        provider = settings.llm_provider
        model = (
            settings.openai_model if provider == "openai" else settings.anthropic_model
        )

        pricing_payload: Optional[Dict[str, Any]] = None
        try:
            if provider == "openai":
                pricing_payload = await _fetch_openai_pricing(model)
            elif provider == "anthropic":
                pricing_payload = await _fetch_anthropic_pricing(model)
        except Exception:
            pricing_payload = None

        env_pricing = _load_env_pricing()
        if pricing_payload:
            _cached_pricing = _merge_pricing(env_pricing, pricing_payload)
            _last_refresh = time.time()
            return _cached_pricing

        # Fallback to env if fetch failed
        _cached_pricing = env_pricing
        _last_refresh = time.time()
        return _cached_pricing


async def pricing_refresh_loop() -> None:
    """Background loop to refresh pricing periodically."""
    while True:
        try:
            await refresh_pricing()
        except Exception:
            pass
        await asyncio.sleep(settings.pricing_refresh_seconds)
