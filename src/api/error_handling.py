"""Standardized API error handling for agent_bus.

This module provides:
1. Consistent error response format across all endpoints
2. Exception handlers for mapping exceptions to HTTP responses
3. Pydantic models for error responses (for OpenAPI documentation)
4. Utility functions for creating error responses
"""

from __future__ import annotations

import logging
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..exceptions import (
    AgentBusError,
    ErrorCode,
    ERROR_CODE_TO_STATUS,
)
from ..infrastructure.circuit_breaker import CircuitBreakerError


logger = logging.getLogger(__name__)


# Pydantic models for API documentation


class ErrorDetail(BaseModel):
    """Detailed error information."""

    code: str = Field(..., description="Error code for programmatic handling")
    message: str = Field(..., description="Human-readable error message")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    request_id: Optional[str] = Field(None, description="Request identifier for tracing")
    job_id: Optional[str] = Field(None, description="Job ID if applicable")
    task_id: Optional[str] = Field(None, description="Task ID if applicable")
    agent_id: Optional[str] = Field(None, description="Agent ID if applicable")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error: ErrorDetail

    class Config:
        json_schema_extra = {
            "example": {
                "error": {
                    "code": "JOB_NOT_FOUND",
                    "message": "Job 'job_abc123' not found",
                    "timestamp": "2024-01-15T10:30:00Z",
                    "request_id": "req_xyz789",
                }
            }
        }


class ValidationErrorItem(BaseModel):
    """Single validation error."""

    field: str = Field(..., description="Field that failed validation")
    message: str = Field(..., description="Validation error message")
    type: str = Field(..., description="Error type")


class ValidationErrorResponse(BaseModel):
    """Validation error response with field-level details."""

    error: ErrorDetail
    validation_errors: List[ValidationErrorItem] = Field(
        ..., description="List of validation errors"
    )


# Utility functions


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return f"req_{uuid.uuid4().hex[:12]}"


def create_error_response(
    code: Union[ErrorCode, str],
    message: str,
    status_code: Optional[int] = None,
    request_id: Optional[str] = None,
    job_id: Optional[str] = None,
    task_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    """
    Create a standardized error response.

    Args:
        code: Error code (ErrorCode enum or string)
        message: Human-readable error message
        status_code: HTTP status code (derived from error code if not provided)
        request_id: Request identifier for tracing
        job_id: Job ID if applicable
        task_id: Task ID if applicable
        agent_id: Agent ID if applicable
        details: Additional error details

    Returns:
        JSONResponse with standardized error format
    """
    # Convert string code to ErrorCode if possible
    if isinstance(code, str):
        try:
            code = ErrorCode(code)
        except ValueError:
            pass  # Keep as string if not a valid ErrorCode

    # Determine status code
    if status_code is None:
        if isinstance(code, ErrorCode):
            status_code = ERROR_CODE_TO_STATUS.get(code, 500)
        else:
            status_code = 500

    # Build error detail
    error_detail: Dict[str, Any] = {
        "code": code.value if isinstance(code, ErrorCode) else code,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if request_id:
        error_detail["request_id"] = request_id
    if job_id:
        error_detail["job_id"] = job_id
    if task_id:
        error_detail["task_id"] = task_id
    if agent_id:
        error_detail["agent_id"] = agent_id
    if details:
        error_detail["details"] = details

    return JSONResponse(
        status_code=status_code,
        content={"error": error_detail},
    )


# Exception handlers


async def agent_bus_exception_handler(
    request: Request, exc: AgentBusError
) -> JSONResponse:
    """Handle AgentBusError exceptions."""
    request_id = getattr(request.state, "request_id", None)

    # Log the error
    logger.error(
        f"AgentBusError: {exc.code.value} - {exc.message}",
        extra={
            "error_code": exc.code.value,
            "request_id": request_id,
            "job_id": exc.context.job_id,
            "task_id": exc.context.task_id,
            "agent_id": exc.context.agent_id,
        },
    )

    return create_error_response(
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        request_id=request_id,
        job_id=exc.context.job_id,
        task_id=exc.context.task_id,
        agent_id=exc.context.agent_id,
        details=exc.context.additional if exc.context.additional else None,
    )


async def circuit_breaker_exception_handler(
    request: Request, exc: CircuitBreakerError
) -> JSONResponse:
    """Handle CircuitBreakerError exceptions."""
    request_id = getattr(request.state, "request_id", None)

    logger.warning(
        f"Circuit breaker open: {exc.circuit_name}",
        extra={"circuit_name": exc.circuit_name, "request_id": request_id},
    )

    return create_error_response(
        code=ErrorCode.CIRCUIT_OPEN,
        message=str(exc),
        status_code=503,
        request_id=request_id,
        details={"circuit_name": exc.circuit_name, "retry_after": exc.recovery_time},
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTPException with standardized format."""
    request_id = getattr(request.state, "request_id", None)

    # Map common HTTP status codes to error codes
    status_to_code = {
        400: ErrorCode.VALIDATION_ERROR,
        401: ErrorCode.SKILL_PERMISSION_DENIED,  # Reusing for auth
        403: ErrorCode.SKILL_PERMISSION_DENIED,
        404: ErrorCode.NOT_FOUND,
        409: ErrorCode.CONFLICT,
        429: ErrorCode.LLM_RATE_LIMIT,
        500: ErrorCode.INTERNAL_ERROR,
        502: ErrorCode.LLM_API_ERROR,
        503: ErrorCode.DATABASE_ERROR,
        504: ErrorCode.TIMEOUT,
    }

    code = status_to_code.get(exc.status_code, ErrorCode.INTERNAL_ERROR)

    # Handle detail as string or dict
    if isinstance(exc.detail, dict):
        message = exc.detail.get("message", str(exc.detail))
        details = exc.detail if "message" not in exc.detail else None
    else:
        message = str(exc.detail)
        details = None

    return create_error_response(
        code=code,
        message=message,
        status_code=exc.status_code,
        request_id=request_id,
        details=details,
    )


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle Pydantic validation errors."""
    from pydantic import ValidationError as PydanticValidationError

    request_id = getattr(request.state, "request_id", None)

    if isinstance(exc, PydanticValidationError):
        validation_errors = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            validation_errors.append(
                {
                    "field": field,
                    "message": error["msg"],
                    "type": error["type"],
                }
            )

        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": ErrorCode.VALIDATION_ERROR.value,
                    "message": "Request validation failed",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "request_id": request_id,
                },
                "validation_errors": validation_errors,
            },
        )

    # Fallback for other validation-like errors
    return create_error_response(
        code=ErrorCode.VALIDATION_ERROR,
        message=str(exc),
        status_code=400,
        request_id=request_id,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    request_id = getattr(request.state, "request_id", None)

    # Log full traceback for debugging
    logger.error(
        f"Unhandled exception: {exc}",
        extra={"request_id": request_id},
        exc_info=True,
    )

    # Don't expose internal details in production
    from ..config import settings

    if settings.debug:
        message = str(exc)
        details = {"traceback": traceback.format_exc()}
    else:
        message = "An internal error occurred"
        details = None

    return create_error_response(
        code=ErrorCode.INTERNAL_ERROR,
        message=message,
        status_code=500,
        request_id=request_id,
        details=details,
    )


# Middleware for request ID


async def request_id_middleware(request: Request, call_next):
    """Add request ID to all requests."""
    request_id = request.headers.get("X-Request-ID") or generate_request_id()
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Setup function


def setup_error_handlers(app: FastAPI) -> None:
    """
    Configure all error handlers for the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    from pydantic import ValidationError as PydanticValidationError
    from fastapi.exceptions import RequestValidationError

    # Add request ID middleware
    app.middleware("http")(request_id_middleware)

    # Register exception handlers
    app.add_exception_handler(AgentBusError, agent_bus_exception_handler)
    app.add_exception_handler(CircuitBreakerError, circuit_breaker_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(PydanticValidationError, validation_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)


# Response models for OpenAPI documentation


# Common response models for use in route decorators
COMMON_ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "Bad Request"},
    404: {"model": ErrorResponse, "description": "Not Found"},
    500: {"model": ErrorResponse, "description": "Internal Server Error"},
    503: {"model": ErrorResponse, "description": "Service Unavailable"},
}
