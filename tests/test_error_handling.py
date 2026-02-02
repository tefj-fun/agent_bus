"""Tests for standardized API error handling."""

import os
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock

# Set test environment
os.environ.setdefault("LLM_MODE", "mock")
os.environ.setdefault("POSTGRES_PASSWORD", "test_password")

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from src.exceptions import (
    AgentBusError,
    ErrorCode,
    ErrorContext,
    JobNotFoundError,
    TaskExecutionError,
    ValidationError,
    LLMTimeoutError,
    DatabaseConnectionError,
)
from src.api.error_handling import (
    ErrorResponse,
    ErrorDetail,
    create_error_response,
    setup_error_handlers,
    generate_request_id,
)


class TestErrorResponseFormat:
    """Test error response formatting."""

    def test_create_error_response_basic(self):
        """Test basic error response creation."""
        response = create_error_response(
            code=ErrorCode.NOT_FOUND,
            message="Resource not found",
        )

        assert response.status_code == 404
        data = response.body.decode()
        import json
        body = json.loads(data)

        assert "error" in body
        assert body["error"]["code"] == "NOT_FOUND"
        assert body["error"]["message"] == "Resource not found"
        assert "timestamp" in body["error"]

    def test_create_error_response_with_context(self):
        """Test error response with full context."""
        response = create_error_response(
            code=ErrorCode.TASK_EXECUTION_ERROR,
            message="Task failed",
            request_id="req_123",
            job_id="job_456",
            task_id="task_789",
            agent_id="prd_agent",
            details={"reason": "missing input"},
        )

        import json
        body = json.loads(response.body.decode())

        error = body["error"]
        assert error["request_id"] == "req_123"
        assert error["job_id"] == "job_456"
        assert error["task_id"] == "task_789"
        assert error["agent_id"] == "prd_agent"
        assert error["details"]["reason"] == "missing input"

    def test_create_error_response_string_code(self):
        """Test error response with string error code."""
        response = create_error_response(
            code="CUSTOM_ERROR",
            message="Custom error occurred",
        )

        import json
        body = json.loads(response.body.decode())

        assert body["error"]["code"] == "CUSTOM_ERROR"
        assert response.status_code == 500  # Default for unknown codes

    def test_generate_request_id_format(self):
        """Test request ID generation format."""
        req_id = generate_request_id()

        assert req_id.startswith("req_")
        assert len(req_id) == 16  # "req_" + 12 hex chars


class TestExceptionHandlers:
    """Test exception handlers with a test app."""

    @pytest.fixture
    def test_app(self):
        """Create a test FastAPI app with error handlers."""
        app = FastAPI()
        setup_error_handlers(app)

        @app.get("/agent-bus-error")
        async def raise_agent_bus_error():
            raise JobNotFoundError("job_123")

        @app.get("/http-exception")
        async def raise_http_exception():
            raise HTTPException(status_code=404, detail="Not found")

        @app.get("/generic-error")
        async def raise_generic_error():
            raise RuntimeError("Unexpected error")

        @app.get("/validation-error")
        async def raise_validation_error():
            raise ValidationError("Invalid field", field="email")

        return app

    @pytest.fixture
    def client(self, test_app):
        """Create test client."""
        return TestClient(test_app, raise_server_exceptions=False)

    def test_agent_bus_error_handler(self, client):
        """Test AgentBusError is handled correctly."""
        response = client.get("/agent-bus-error")

        assert response.status_code == 404
        data = response.json()

        assert "error" in data
        assert data["error"]["code"] == "JOB_NOT_FOUND"
        assert "job_123" in data["error"]["message"]

    def test_http_exception_handler(self, client):
        """Test HTTPException is converted to standard format."""
        response = client.get("/http-exception")

        assert response.status_code == 404
        data = response.json()

        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"

    def test_generic_error_handler(self, client):
        """Test generic exceptions are handled."""
        response = client.get("/generic-error")

        assert response.status_code == 500
        data = response.json()

        assert "error" in data
        assert data["error"]["code"] == "INTERNAL_ERROR"

    def test_request_id_in_response(self, client):
        """Test request ID is added to response."""
        response = client.get("/agent-bus-error")

        # Check header
        assert "x-request-id" in response.headers

    def test_request_id_passthrough(self, client):
        """Test request ID from header is preserved."""
        response = client.get(
            "/agent-bus-error",
            headers={"X-Request-ID": "custom_req_123"},
        )

        assert response.headers.get("x-request-id") == "custom_req_123"


class TestExceptionModels:
    """Test Pydantic error response models."""

    def test_error_detail_model(self):
        """Test ErrorDetail model."""
        detail = ErrorDetail(
            code="TEST_ERROR",
            message="Test message",
            timestamp="2024-01-15T10:00:00Z",
            request_id="req_123",
        )

        assert detail.code == "TEST_ERROR"
        assert detail.message == "Test message"
        assert detail.request_id == "req_123"

    def test_error_response_model(self):
        """Test ErrorResponse model."""
        response = ErrorResponse(
            error=ErrorDetail(
                code="NOT_FOUND",
                message="Resource not found",
                timestamp="2024-01-15T10:00:00Z",
            )
        )

        data = response.model_dump()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"


class TestExceptionHierarchy:
    """Test the custom exception hierarchy."""

    def test_base_exception_properties(self):
        """Test AgentBusError base class."""
        exc = AgentBusError(
            message="Test error",
            code=ErrorCode.INTERNAL_ERROR,
        )

        assert exc.message == "Test error"
        assert exc.code == ErrorCode.INTERNAL_ERROR
        assert exc.status_code == 500
        assert exc.context is not None

    def test_exception_with_context(self):
        """Test exception with ErrorContext."""
        context = ErrorContext(
            job_id="job_123",
            task_id="task_456",
            agent_id="test_agent",
            additional={"custom": "data"},
        )

        exc = TaskExecutionError(
            message="Task failed",
            task_id="task_456",
            context=context,
        )

        assert exc.context.job_id == "job_123"
        assert exc.context.task_id == "task_456"
        assert exc.context.agent_id == "test_agent"

    def test_exception_to_dict(self):
        """Test exception serialization."""
        context = ErrorContext(
            job_id="job_123",
            additional={"key": "value"},
        )

        exc = JobNotFoundError("job_123", context=context)
        data = exc.to_dict()

        assert data["error"]["code"] == "JOB_NOT_FOUND"
        assert data["error"]["job_id"] == "job_123"
        assert "timestamp" in data["error"]

    def test_exception_str(self):
        """Test exception string representation."""
        exc = JobNotFoundError("job_123")

        assert "[JOB_NOT_FOUND]" in str(exc)
        assert "job_123" in str(exc)

    def test_exception_cause_chain(self):
        """Test exception cause chaining."""
        original = ValueError("Original error")
        exc = DatabaseConnectionError(
            message="Failed to connect",
            cause=original,
        )

        assert exc.cause is original

    def test_all_exception_types_have_status_codes(self):
        """Test all exception types map to HTTP status codes."""
        exceptions = [
            JobNotFoundError("x"),
            TaskExecutionError("x"),
            ValidationError("x"),
            LLMTimeoutError("anthropic", 30),
            DatabaseConnectionError(),
        ]

        for exc in exceptions:
            assert isinstance(exc.status_code, int)
            assert 400 <= exc.status_code < 600


class TestErrorCodeMapping:
    """Test error code to HTTP status mapping."""

    def test_404_errors(self):
        """Test 404 error codes."""
        codes_404 = [
            ErrorCode.NOT_FOUND,
            ErrorCode.JOB_NOT_FOUND,
            ErrorCode.TASK_NOT_FOUND,
            ErrorCode.AGENT_NOT_FOUND,
            ErrorCode.PATTERN_NOT_FOUND,
            ErrorCode.SKILL_NOT_FOUND,
        ]

        from src.exceptions import ERROR_CODE_TO_STATUS

        for code in codes_404:
            assert ERROR_CODE_TO_STATUS[code] == 404

    def test_400_errors(self):
        """Test 400 error codes."""
        codes_400 = [
            ErrorCode.VALIDATION_ERROR,
            ErrorCode.TASK_DEPENDENCY_ERROR,
            ErrorCode.WORKFLOW_TRANSITION_ERROR,
        ]

        from src.exceptions import ERROR_CODE_TO_STATUS

        for code in codes_400:
            assert ERROR_CODE_TO_STATUS[code] == 400

    def test_503_errors(self):
        """Test 503 error codes."""
        codes_503 = [
            ErrorCode.DATABASE_ERROR,
            ErrorCode.DATABASE_CONNECTION_ERROR,
            ErrorCode.REDIS_ERROR,
            ErrorCode.REDIS_CONNECTION_ERROR,
            ErrorCode.CIRCUIT_OPEN,
        ]

        from src.exceptions import ERROR_CODE_TO_STATUS

        for code in codes_503:
            assert ERROR_CODE_TO_STATUS[code] == 503

    def test_504_errors(self):
        """Test 504 error codes."""
        codes_504 = [
            ErrorCode.TIMEOUT,
            ErrorCode.AGENT_TIMEOUT,
            ErrorCode.TASK_TIMEOUT,
            ErrorCode.LLM_TIMEOUT,
        ]

        from src.exceptions import ERROR_CODE_TO_STATUS

        for code in codes_504:
            assert ERROR_CODE_TO_STATUS[code] == 504


class TestSpecificExceptions:
    """Test specific exception types."""

    def test_job_not_found_error(self):
        """Test JobNotFoundError."""
        exc = JobNotFoundError("job_abc")

        assert exc.code == ErrorCode.JOB_NOT_FOUND
        assert exc.status_code == 404
        assert "job_abc" in exc.message
        assert exc.context.job_id == "job_abc"

    def test_task_timeout_error(self):
        """Test TaskTimeoutError."""
        from src.exceptions import TaskTimeoutError

        exc = TaskTimeoutError("task_123", 300)

        assert exc.code == ErrorCode.TASK_TIMEOUT
        assert exc.status_code == 504
        assert "task_123" in exc.message
        assert "300" in exc.message
        assert exc.context.additional["timeout_seconds"] == 300

    def test_workflow_transition_error(self):
        """Test WorkflowTransitionError."""
        from src.exceptions import WorkflowTransitionError

        exc = WorkflowTransitionError("prd_generation", "delivery")

        assert exc.code == ErrorCode.WORKFLOW_TRANSITION_ERROR
        assert exc.status_code == 400
        assert "prd_generation" in exc.message
        assert "delivery" in exc.message

    def test_skill_permission_denied_error(self):
        """Test SkillPermissionDeniedError."""
        from src.exceptions import SkillPermissionDeniedError

        exc = SkillPermissionDeniedError("weather-toolkit", "prd_agent")

        assert exc.code == ErrorCode.SKILL_PERMISSION_DENIED
        assert exc.status_code == 403
        assert "weather-toolkit" in exc.message
        assert "prd_agent" in exc.message

    def test_llm_rate_limit_error(self):
        """Test LLMRateLimitError."""
        from src.exceptions import LLMRateLimitError

        exc = LLMRateLimitError("anthropic", retry_after=60)

        assert exc.code == ErrorCode.LLM_RATE_LIMIT
        assert exc.status_code == 429
        assert exc.context.additional["retry_after"] == 60
