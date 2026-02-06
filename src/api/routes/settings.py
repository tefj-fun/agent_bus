"""API routes for runtime settings."""

from typing import Optional
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...config import settings

router = APIRouter()


def _mask_secret(value: str | None) -> Optional[str]:
    if not value:
        return None
    suffix = value[-4:] if len(value) >= 4 else value
    return f"****{suffix}"


def _apply_setting(field: str, value: object, env_key: Optional[str] = None) -> None:
    setattr(settings, field, value)
    if env_key:
        os.environ[env_key] = str(value)


class SettingsResponse(BaseModel):
    llm_mode: str
    llm_provider: str
    anthropic_model: str
    openai_model: str
    anthropic_max_tokens: int
    prd_max_tokens: int
    timeout_llm_call: int
    timeout_task_completion: int
    timeout_db_query: int
    timeout_redis_operation: int
    anthropic_api_key_masked: Optional[str] = None
    openai_api_key_masked: Optional[str] = None


class SettingsUpdateRequest(BaseModel):
    llm_mode: Optional[str] = None
    llm_provider: Optional[str] = None
    anthropic_model: Optional[str] = None
    openai_model: Optional[str] = None
    anthropic_max_tokens: Optional[int] = Field(default=None, ge=1)
    prd_max_tokens: Optional[int] = Field(default=None, ge=1)
    timeout_llm_call: Optional[int] = Field(default=None, ge=1)
    timeout_task_completion: Optional[int] = Field(default=None, ge=1)
    timeout_db_query: Optional[int] = Field(default=None, ge=1)
    timeout_redis_operation: Optional[int] = Field(default=None, ge=1)
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None


def _current_settings() -> SettingsResponse:
    return SettingsResponse(
        llm_mode=settings.llm_mode,
        llm_provider=settings.llm_provider,
        anthropic_model=settings.anthropic_model,
        openai_model=settings.openai_model,
        anthropic_max_tokens=settings.anthropic_max_tokens,
        prd_max_tokens=settings.prd_max_tokens,
        timeout_llm_call=settings.timeout_llm_call,
        timeout_task_completion=settings.timeout_task_completion,
        timeout_db_query=settings.timeout_db_query,
        timeout_redis_operation=settings.timeout_redis_operation,
        anthropic_api_key_masked=_mask_secret(settings.anthropic_api_key),
        openai_api_key_masked=_mask_secret(settings.openai_api_key),
    )


@router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    """Return tunable runtime settings (secrets masked)."""
    return _current_settings()


@router.post("/settings", response_model=SettingsResponse)
async def update_settings(request: SettingsUpdateRequest):
    """Update tunable runtime settings (in-memory)."""
    try:
        if request.llm_mode is not None:
            _apply_setting("llm_mode", request.llm_mode, "LLM_MODE")
        if request.llm_provider is not None:
            _apply_setting("llm_provider", request.llm_provider, "LLM_PROVIDER")
        if request.anthropic_model is not None:
            _apply_setting("anthropic_model", request.anthropic_model, "ANTHROPIC_MODEL")
        if request.openai_model is not None:
            _apply_setting("openai_model", request.openai_model, "OPENAI_MODEL")
        if request.anthropic_max_tokens is not None:
            _apply_setting(
                "anthropic_max_tokens", request.anthropic_max_tokens, "ANTHROPIC_MAX_TOKENS"
            )
        if request.prd_max_tokens is not None:
            _apply_setting("prd_max_tokens", request.prd_max_tokens, "PRD_MAX_TOKENS")
        if request.timeout_llm_call is not None:
            _apply_setting("timeout_llm_call", request.timeout_llm_call, "TIMEOUT_LLM_CALL")
        if request.timeout_task_completion is not None:
            _apply_setting(
                "timeout_task_completion",
                request.timeout_task_completion,
                "TIMEOUT_TASK_COMPLETION",
            )
        if request.timeout_db_query is not None:
            _apply_setting("timeout_db_query", request.timeout_db_query, "TIMEOUT_DB_QUERY")
        if request.timeout_redis_operation is not None:
            _apply_setting(
                "timeout_redis_operation",
                request.timeout_redis_operation,
                "TIMEOUT_REDIS_OPERATION",
            )
        if request.anthropic_api_key is not None:
            _apply_setting("anthropic_api_key", request.anthropic_api_key, "ANTHROPIC_API_KEY")
        if request.openai_api_key is not None:
            _apply_setting("openai_api_key", request.openai_api_key, "OPENAI_API_KEY")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _current_settings()
