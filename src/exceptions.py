"""Custom exception hierarchy for agent_bus.

This module provides a structured exception hierarchy that:
1. Enables precise error handling at different layers
2. Provides consistent error messages and codes
3. Maps cleanly to HTTP status codes for API responses
4. Includes context for debugging and logging
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class ErrorCode(str, Enum):
    """Standard error codes for categorizing errors."""

    # General errors (1xxx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    TIMEOUT = "TIMEOUT"

    # Infrastructure errors (2xxx)
    DATABASE_ERROR = "DATABASE_ERROR"
    DATABASE_CONNECTION_ERROR = "DATABASE_CONNECTION_ERROR"
    DATABASE_QUERY_ERROR = "DATABASE_QUERY_ERROR"
    REDIS_ERROR = "REDIS_ERROR"
    REDIS_CONNECTION_ERROR = "REDIS_CONNECTION_ERROR"

    # Agent errors (3xxx)
    AGENT_ERROR = "AGENT_ERROR"
    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"
    AGENT_EXECUTION_ERROR = "AGENT_EXECUTION_ERROR"
    AGENT_TIMEOUT = "AGENT_TIMEOUT"

    # Task errors (4xxx)
    TASK_ERROR = "TASK_ERROR"
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    TASK_EXECUTION_ERROR = "TASK_EXECUTION_ERROR"
    TASK_TIMEOUT = "TASK_TIMEOUT"
    TASK_DEPENDENCY_ERROR = "TASK_DEPENDENCY_ERROR"

    # Job/Workflow errors (5xxx)
    JOB_ERROR = "JOB_ERROR"
    JOB_NOT_FOUND = "JOB_NOT_FOUND"
    WORKFLOW_ERROR = "WORKFLOW_ERROR"
    WORKFLOW_TRANSITION_ERROR = "WORKFLOW_TRANSITION_ERROR"

    # LLM errors (6xxx)
    LLM_ERROR = "LLM_ERROR"
    LLM_API_ERROR = "LLM_API_ERROR"
    LLM_RATE_LIMIT = "LLM_RATE_LIMIT"
    LLM_TIMEOUT = "LLM_TIMEOUT"

    # Memory/Pattern errors (7xxx)
    MEMORY_ERROR = "MEMORY_ERROR"
    PATTERN_NOT_FOUND = "PATTERN_NOT_FOUND"
    EMBEDDING_ERROR = "EMBEDDING_ERROR"

    # Skills errors (8xxx)
    SKILL_ERROR = "SKILL_ERROR"
    SKILL_NOT_FOUND = "SKILL_NOT_FOUND"
    SKILL_PERMISSION_DENIED = "SKILL_PERMISSION_DENIED"

    # Circuit breaker errors (9xxx)
    CIRCUIT_OPEN = "CIRCUIT_OPEN"


# HTTP status code mapping
ERROR_CODE_TO_STATUS: Dict[ErrorCode, int] = {
    ErrorCode.INTERNAL_ERROR: 500,
    ErrorCode.VALIDATION_ERROR: 400,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.CONFLICT: 409,
    ErrorCode.TIMEOUT: 504,
    ErrorCode.DATABASE_ERROR: 503,
    ErrorCode.DATABASE_CONNECTION_ERROR: 503,
    ErrorCode.DATABASE_QUERY_ERROR: 500,
    ErrorCode.REDIS_ERROR: 503,
    ErrorCode.REDIS_CONNECTION_ERROR: 503,
    ErrorCode.AGENT_ERROR: 500,
    ErrorCode.AGENT_NOT_FOUND: 404,
    ErrorCode.AGENT_EXECUTION_ERROR: 500,
    ErrorCode.AGENT_TIMEOUT: 504,
    ErrorCode.TASK_ERROR: 500,
    ErrorCode.TASK_NOT_FOUND: 404,
    ErrorCode.TASK_EXECUTION_ERROR: 500,
    ErrorCode.TASK_TIMEOUT: 504,
    ErrorCode.TASK_DEPENDENCY_ERROR: 400,
    ErrorCode.JOB_ERROR: 500,
    ErrorCode.JOB_NOT_FOUND: 404,
    ErrorCode.WORKFLOW_ERROR: 500,
    ErrorCode.WORKFLOW_TRANSITION_ERROR: 400,
    ErrorCode.LLM_ERROR: 502,
    ErrorCode.LLM_API_ERROR: 502,
    ErrorCode.LLM_RATE_LIMIT: 429,
    ErrorCode.LLM_TIMEOUT: 504,
    ErrorCode.MEMORY_ERROR: 500,
    ErrorCode.PATTERN_NOT_FOUND: 404,
    ErrorCode.EMBEDDING_ERROR: 500,
    ErrorCode.SKILL_ERROR: 500,
    ErrorCode.SKILL_NOT_FOUND: 404,
    ErrorCode.SKILL_PERMISSION_DENIED: 403,
    ErrorCode.CIRCUIT_OPEN: 503,
}


@dataclass
class ErrorContext:
    """Additional context for debugging errors."""

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    request_id: Optional[str] = None
    job_id: Optional[str] = None
    task_id: Optional[str] = None
    agent_id: Optional[str] = None
    additional: Dict[str, Any] = field(default_factory=dict)


class AgentBusError(Exception):
    """
    Base exception for all agent_bus errors.

    All custom exceptions should inherit from this class to ensure
    consistent error handling and reporting.
    """

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.context = context or ErrorContext()
        self.cause = cause

    @property
    def status_code(self) -> int:
        """Get HTTP status code for this error."""
        return ERROR_CODE_TO_STATUS.get(self.code, 500)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for API response."""
        result = {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "timestamp": self.context.timestamp.isoformat(),
            }
        }

        # Add optional context
        if self.context.request_id:
            result["error"]["request_id"] = self.context.request_id
        if self.context.job_id:
            result["error"]["job_id"] = self.context.job_id
        if self.context.task_id:
            result["error"]["task_id"] = self.context.task_id
        if self.context.agent_id:
            result["error"]["agent_id"] = self.context.agent_id

        return result

    def __str__(self) -> str:
        return f"[{self.code.value}] {self.message}"


# Infrastructure Exceptions


class DatabaseError(AgentBusError):
    """Base exception for database errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code=ErrorCode.DATABASE_ERROR, **kwargs)


class DatabaseConnectionError(DatabaseError):
    """Database connection failed."""

    def __init__(self, message: str = "Failed to connect to database", **kwargs):
        kwargs["code"] = ErrorCode.DATABASE_CONNECTION_ERROR
        AgentBusError.__init__(self, message, **kwargs)


class DatabaseQueryError(DatabaseError):
    """Database query failed."""

    def __init__(self, message: str, query: Optional[str] = None, **kwargs):
        kwargs["code"] = ErrorCode.DATABASE_QUERY_ERROR
        if query:
            kwargs.setdefault("context", ErrorContext()).additional["query"] = query
        AgentBusError.__init__(self, message, **kwargs)


class RedisError(AgentBusError):
    """Base exception for Redis errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code=ErrorCode.REDIS_ERROR, **kwargs)


class RedisConnectionError(RedisError):
    """Redis connection failed."""

    def __init__(self, message: str = "Failed to connect to Redis", **kwargs):
        kwargs["code"] = ErrorCode.REDIS_CONNECTION_ERROR
        AgentBusError.__init__(self, message, **kwargs)


# Agent Exceptions


class AgentError(AgentBusError):
    """Base exception for agent errors."""

    def __init__(self, message: str, agent_id: Optional[str] = None, **kwargs):
        context = kwargs.pop("context", None) or ErrorContext()
        context.agent_id = agent_id
        super().__init__(message, code=ErrorCode.AGENT_ERROR, context=context, **kwargs)


class AgentNotFoundError(AgentError):
    """Agent type not found."""

    def __init__(self, agent_type: str, **kwargs):
        kwargs["code"] = ErrorCode.AGENT_NOT_FOUND
        AgentBusError.__init__(self, f"Agent type '{agent_type}' not found", **kwargs)


class AgentExecutionError(AgentError):
    """Agent execution failed."""

    def __init__(self, message: str, agent_id: Optional[str] = None, **kwargs):
        kwargs["code"] = ErrorCode.AGENT_EXECUTION_ERROR
        context = kwargs.pop("context", None) or ErrorContext()
        context.agent_id = agent_id
        AgentBusError.__init__(self, message, context=context, **kwargs)


class AgentTimeoutError(AgentError):
    """Agent execution timed out."""

    def __init__(
        self, agent_id: str, timeout_seconds: int, **kwargs
    ):
        kwargs["code"] = ErrorCode.AGENT_TIMEOUT
        context = kwargs.pop("context", None) or ErrorContext()
        context.agent_id = agent_id
        context.additional["timeout_seconds"] = timeout_seconds
        AgentBusError.__init__(
            self,
            f"Agent '{agent_id}' timed out after {timeout_seconds} seconds",
            context=context,
            **kwargs,
        )


# Task Exceptions


class TaskError(AgentBusError):
    """Base exception for task errors."""

    def __init__(self, message: str, task_id: Optional[str] = None, **kwargs):
        context = kwargs.pop("context", None) or ErrorContext()
        context.task_id = task_id
        super().__init__(message, code=ErrorCode.TASK_ERROR, context=context, **kwargs)


class TaskNotFoundError(TaskError):
    """Task not found."""

    def __init__(self, task_id: str, **kwargs):
        kwargs["code"] = ErrorCode.TASK_NOT_FOUND
        context = kwargs.pop("context", None) or ErrorContext()
        context.task_id = task_id
        AgentBusError.__init__(
            self, f"Task '{task_id}' not found", context=context, **kwargs
        )


class TaskExecutionError(TaskError):
    """Task execution failed."""

    def __init__(self, message: str, task_id: Optional[str] = None, **kwargs):
        kwargs["code"] = ErrorCode.TASK_EXECUTION_ERROR
        context = kwargs.pop("context", None) or ErrorContext()
        context.task_id = task_id
        AgentBusError.__init__(self, message, context=context, **kwargs)


class TaskTimeoutError(TaskError):
    """Task execution timed out."""

    def __init__(self, task_id: str, timeout_seconds: int, **kwargs):
        kwargs["code"] = ErrorCode.TASK_TIMEOUT
        context = kwargs.pop("context", None) or ErrorContext()
        context.task_id = task_id
        context.additional["timeout_seconds"] = timeout_seconds
        AgentBusError.__init__(
            self,
            f"Task '{task_id}' timed out after {timeout_seconds} seconds",
            context=context,
            **kwargs,
        )


class TaskDependencyError(TaskError):
    """Task dependency not satisfied."""

    def __init__(
        self, task_id: str, missing_dependencies: List[str], **kwargs
    ):
        kwargs["code"] = ErrorCode.TASK_DEPENDENCY_ERROR
        context = kwargs.pop("context", None) or ErrorContext()
        context.task_id = task_id
        context.additional["missing_dependencies"] = missing_dependencies
        AgentBusError.__init__(
            self,
            f"Task '{task_id}' has unmet dependencies: {missing_dependencies}",
            context=context,
            **kwargs,
        )


# Job/Workflow Exceptions


class JobError(AgentBusError):
    """Base exception for job errors."""

    def __init__(self, message: str, job_id: Optional[str] = None, **kwargs):
        context = kwargs.pop("context", None) or ErrorContext()
        context.job_id = job_id
        super().__init__(message, code=ErrorCode.JOB_ERROR, context=context, **kwargs)


class JobNotFoundError(JobError):
    """Job not found."""

    def __init__(self, job_id: str, **kwargs):
        kwargs["code"] = ErrorCode.JOB_NOT_FOUND
        context = kwargs.pop("context", None) or ErrorContext()
        context.job_id = job_id
        AgentBusError.__init__(
            self, f"Job '{job_id}' not found", context=context, **kwargs
        )


class WorkflowError(AgentBusError):
    """Base exception for workflow errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code=ErrorCode.WORKFLOW_ERROR, **kwargs)


class WorkflowTransitionError(WorkflowError):
    """Invalid workflow state transition."""

    def __init__(self, from_stage: str, to_stage: str, **kwargs):
        kwargs["code"] = ErrorCode.WORKFLOW_TRANSITION_ERROR
        context = kwargs.pop("context", None) or ErrorContext()
        context.additional["from_stage"] = from_stage
        context.additional["to_stage"] = to_stage
        AgentBusError.__init__(
            self,
            f"Invalid workflow transition from '{from_stage}' to '{to_stage}'",
            context=context,
            **kwargs,
        )


# LLM Exceptions


class LLMError(AgentBusError):
    """Base exception for LLM errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code=ErrorCode.LLM_ERROR, **kwargs)


class LLMAPIError(LLMError):
    """LLM API call failed."""

    def __init__(self, message: str, provider: str = "unknown", **kwargs):
        kwargs["code"] = ErrorCode.LLM_API_ERROR
        context = kwargs.pop("context", None) or ErrorContext()
        context.additional["provider"] = provider
        AgentBusError.__init__(self, message, context=context, **kwargs)


class LLMRateLimitError(LLMError):
    """LLM rate limit exceeded."""

    def __init__(
        self, provider: str, retry_after: Optional[int] = None, **kwargs
    ):
        kwargs["code"] = ErrorCode.LLM_RATE_LIMIT
        context = kwargs.pop("context", None) or ErrorContext()
        context.additional["provider"] = provider
        if retry_after:
            context.additional["retry_after"] = retry_after
        AgentBusError.__init__(
            self, f"Rate limit exceeded for {provider}", context=context, **kwargs
        )


class LLMTimeoutError(LLMError):
    """LLM call timed out."""

    def __init__(self, provider: str, timeout_seconds: int, **kwargs):
        kwargs["code"] = ErrorCode.LLM_TIMEOUT
        context = kwargs.pop("context", None) or ErrorContext()
        context.additional["provider"] = provider
        context.additional["timeout_seconds"] = timeout_seconds
        AgentBusError.__init__(
            self,
            f"LLM call to {provider} timed out after {timeout_seconds}s",
            context=context,
            **kwargs,
        )


# Memory/Pattern Exceptions


class MemoryError(AgentBusError):
    """Base exception for memory system errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code=ErrorCode.MEMORY_ERROR, **kwargs)


class PatternNotFoundError(MemoryError):
    """Pattern not found in memory store."""

    def __init__(self, pattern_id: str, **kwargs):
        kwargs["code"] = ErrorCode.PATTERN_NOT_FOUND
        context = kwargs.pop("context", None) or ErrorContext()
        context.additional["pattern_id"] = pattern_id
        AgentBusError.__init__(
            self, f"Pattern '{pattern_id}' not found", context=context, **kwargs
        )


class EmbeddingError(MemoryError):
    """Failed to generate embeddings."""

    def __init__(self, message: str, **kwargs):
        kwargs["code"] = ErrorCode.EMBEDDING_ERROR
        AgentBusError.__init__(self, message, **kwargs)


# Skills Exceptions


class SkillError(AgentBusError):
    """Base exception for skills errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code=ErrorCode.SKILL_ERROR, **kwargs)


class SkillNotFoundError(SkillError):
    """Skill not found."""

    def __init__(self, skill_name: str, **kwargs):
        kwargs["code"] = ErrorCode.SKILL_NOT_FOUND
        context = kwargs.pop("context", None) or ErrorContext()
        context.additional["skill_name"] = skill_name
        AgentBusError.__init__(
            self, f"Skill '{skill_name}' not found", context=context, **kwargs
        )


class SkillPermissionDeniedError(SkillError):
    """Agent doesn't have permission to use skill."""

    def __init__(self, skill_name: str, agent_id: str, **kwargs):
        kwargs["code"] = ErrorCode.SKILL_PERMISSION_DENIED
        context = kwargs.pop("context", None) or ErrorContext()
        context.agent_id = agent_id
        context.additional["skill_name"] = skill_name
        AgentBusError.__init__(
            self,
            f"Agent '{agent_id}' is not allowed to use skill '{skill_name}'",
            context=context,
            **kwargs,
        )


# Validation Exceptions


class ValidationError(AgentBusError):
    """Validation error."""

    def __init__(
        self, message: str, field: Optional[str] = None, **kwargs
    ):
        context = kwargs.pop("context", None) or ErrorContext()
        if field:
            context.additional["field"] = field
        super().__init__(
            message, code=ErrorCode.VALIDATION_ERROR, context=context, **kwargs
        )


class NotFoundError(AgentBusError):
    """Generic not found error."""

    def __init__(self, resource_type: str, resource_id: str, **kwargs):
        context = kwargs.pop("context", None) or ErrorContext()
        context.additional["resource_type"] = resource_type
        context.additional["resource_id"] = resource_id
        super().__init__(
            f"{resource_type} '{resource_id}' not found",
            code=ErrorCode.NOT_FOUND,
            context=context,
            **kwargs,
        )


class TimeoutError(AgentBusError):
    """Generic timeout error."""

    def __init__(self, operation: str, timeout_seconds: int, **kwargs):
        context = kwargs.pop("context", None) or ErrorContext()
        context.additional["operation"] = operation
        context.additional["timeout_seconds"] = timeout_seconds
        super().__init__(
            f"Operation '{operation}' timed out after {timeout_seconds}s",
            code=ErrorCode.TIMEOUT,
            context=context,
            **kwargs,
        )


class CircuitOpenError(AgentBusError):
    """Circuit breaker is open."""

    def __init__(self, circuit_name: str, retry_after: float, **kwargs):
        context = kwargs.pop("context", None) or ErrorContext()
        context.additional["circuit_name"] = circuit_name
        context.additional["retry_after"] = retry_after
        super().__init__(
            f"Circuit '{circuit_name}' is open. Retry after {retry_after:.1f}s",
            code=ErrorCode.CIRCUIT_OPEN,
            context=context,
            **kwargs,
        )
