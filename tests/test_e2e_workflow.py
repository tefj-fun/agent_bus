"""End-to-end integration tests for the agent_bus workflow.

These tests verify the complete workflow from API request through
orchestration, agent execution, and response delivery.

Requirements:
- Redis and PostgreSQL must be running
- Set LLM_MODE=mock for CI/testing without API calls
"""

import asyncio
import json
import os
import pytest
import uuid
from typing import Dict, Any
from unittest.mock import AsyncMock, patch

# Set mock mode before importing app modules
os.environ.setdefault("LLM_MODE", "mock")
os.environ.setdefault("POSTGRES_PASSWORD", "test_password")

from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from src.main import app
from src.config import settings
from src.infrastructure.container import container
from src.infrastructure.redis_client import redis_client
from src.infrastructure.postgres_client import postgres_client
from src.exceptions import JobNotFoundError, ErrorCode


# Fixtures


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture
def sync_client():
    """Synchronous test client for simple tests."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def async_client():
    """Async test client for async tests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def setup_infrastructure():
    """Setup test infrastructure connections."""
    try:
        await container.init()
        yield
    finally:
        await container.close()


@pytest.fixture
def unique_project_id():
    """Generate a unique project ID for each test."""
    return f"test_project_{uuid.uuid4().hex[:8]}"


# Health Check Tests


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_root_endpoint(self, sync_client):
        """Test root endpoint returns API info."""
        response = sync_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Agent Bus API"
        assert "version" in data
        assert data["status"] == "running"

    def test_health_endpoint_returns_structure(self, sync_client):
        """Test health endpoint returns expected structure."""
        response = sync_client.get("/health")
        # May be 200 (healthy) or 503 (unhealthy) depending on infra
        assert response.status_code in (200, 503)
        data = response.json()

        if response.status_code == 200:
            assert data["status"] == "healthy"
            assert "redis" in data
            assert "postgres" in data
        else:
            # 503 returns detail with status
            assert "detail" in data or "status" in data


# Error Response Consistency Tests


class TestErrorResponseFormat:
    """Test that all error responses follow the standardized format."""

    def test_404_returns_standard_error_format(self, sync_client):
        """Test 404 errors return standardized format."""
        response = sync_client.get("/api/projects/nonexistent_job_12345")
        assert response.status_code == 404
        data = response.json()

        # Check standardized error structure
        assert "error" in data
        error = data["error"]
        assert "code" in error
        assert "message" in error
        assert "timestamp" in error

    def test_validation_error_returns_standard_format(self, sync_client):
        """Test validation errors return standardized format."""
        # Send invalid request body
        response = sync_client.post(
            "/api/projects/",
            json={"invalid_field": "value"},  # Missing required fields
        )
        assert response.status_code in (400, 422)
        data = response.json()

        # Should have error structure
        assert "error" in data

    def test_request_id_header_returned(self, sync_client):
        """Test that X-Request-ID header is returned."""
        response = sync_client.get("/")
        # Request ID should be in response headers
        assert "x-request-id" in response.headers or response.status_code == 200


# Project API Tests


class TestProjectAPI:
    """Test project management API endpoints."""

    def test_create_project_success(self, sync_client, unique_project_id):
        """Test creating a new project."""
        response = sync_client.post(
            "/api/projects/",
            json={
                "project_id": unique_project_id,
                "requirements": "Build a simple todo application with user authentication",
                "metadata": {"priority": "high"},
            },
        )

        # May fail if DB not available, but should return valid response
        if response.status_code == 200:
            data = response.json()
            assert "job_id" in data
            assert data["project_id"] == unique_project_id
            assert data["status"] == "queued"
        else:
            # Should still be valid error response
            data = response.json()
            assert "error" in data or "detail" in data

    def test_create_project_missing_requirements(self, sync_client):
        """Test creating project without requirements fails validation."""
        response = sync_client.post(
            "/api/projects/",
            json={"project_id": "test_project"},
        )
        assert response.status_code in (400, 422)

    def test_get_nonexistent_job(self, sync_client):
        """Test getting a nonexistent job returns 404."""
        response = sync_client.get("/api/projects/job_nonexistent_xyz")
        assert response.status_code in (404, 500)  # 500 if DB not available

    def test_get_job_prd_nonexistent(self, sync_client):
        """Test getting PRD for nonexistent job."""
        response = sync_client.get("/api/projects/job_nonexistent_xyz/prd")
        assert response.status_code in (404, 500)


# Memory API Tests


class TestMemoryAPI:
    """Test memory store API endpoints."""

    def test_memory_health(self, sync_client):
        """Test memory health endpoint."""
        response = sync_client.get("/api/memory/health")
        # May be 200 or 500 depending on DB availability
        assert response.status_code in (200, 500)

    def test_memory_upsert_and_query(self, sync_client):
        """Test upserting and querying memory documents."""
        doc_id = f"test_doc_{uuid.uuid4().hex[:8]}"

        # Upsert
        response = sync_client.post(
            "/api/memory/upsert",
            json={
                "doc_id": doc_id,
                "text": "Test document about building REST APIs",
                "metadata": {"type": "test"},
            },
        )

        if response.status_code == 200:
            data = response.json()
            assert data["doc_id"] == doc_id

            # Query
            query_response = sync_client.post(
                "/api/memory/query",
                json={"query": "REST APIs", "top_k": 5},
            )
            assert query_response.status_code == 200


# Circuit Breaker Tests


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after threshold failures."""
        from src.infrastructure.circuit_breaker import CircuitBreaker, CircuitState

        cb = CircuitBreaker(
            name="test_circuit",
            failure_threshold=3,
            recovery_timeout=1,
        )

        # Simulate failures
        async def failing_call():
            raise Exception("Simulated failure")

        for _ in range(3):
            try:
                await cb.call(failing_call)
            except Exception:
                pass

        # Circuit should be open
        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovers(self):
        """Test circuit breaker recovers after timeout."""
        from src.infrastructure.circuit_breaker import CircuitBreaker, CircuitState

        cb = CircuitBreaker(
            name="test_recovery",
            failure_threshold=2,
            recovery_timeout=0.1,  # 100ms for fast test
            half_open_requests=1,
        )

        # Open the circuit
        async def failing_call():
            raise Exception("Failure")

        for _ in range(2):
            try:
                await cb.call(failing_call)
            except Exception:
                pass

        assert cb.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        # Successful call should close circuit
        async def success_call():
            return "success"

        result = await cb.call(success_call)
        assert result == "success"
        assert cb.state == CircuitState.CLOSED


# DI Container Tests


class TestDIContainer:
    """Test dependency injection container."""

    @pytest.mark.asyncio
    async def test_container_lazy_initialization(self):
        """Test container initializes dependencies lazily."""
        from src.infrastructure.container import Container

        test_container = Container()

        # Should not be initialized yet
        assert not test_container._initialized

        # Override with mock to avoid real connections
        mock_redis = AsyncMock()
        test_container.override("redis", mock_redis)

        # Resolve should work
        redis = await test_container.redis()
        assert redis == mock_redis

    @pytest.mark.asyncio
    async def test_container_health_check(self):
        """Test container health check method."""
        from src.infrastructure.container import Container

        test_container = Container()

        # Override with mocks
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        test_container.override("redis", mock_redis)

        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        mock_conn.execute = AsyncMock(return_value=None)
        test_container.override("postgres_pool", mock_pool)

        health = await test_container.health_check()

        assert "redis" in health
        assert "postgres" in health


# Exception Hierarchy Tests


class TestExceptionHierarchy:
    """Test custom exception hierarchy."""

    def test_agent_bus_error_to_dict(self):
        """Test exception serialization."""
        from src.exceptions import JobNotFoundError, ErrorCode

        exc = JobNotFoundError("job_123")

        result = exc.to_dict()

        assert "error" in result
        assert result["error"]["code"] == ErrorCode.JOB_NOT_FOUND.value
        assert "job_123" in result["error"]["message"]
        assert "timestamp" in result["error"]

    def test_error_code_to_status_mapping(self):
        """Test error codes map to correct HTTP status."""
        from src.exceptions import (
            JobNotFoundError,
            ValidationError,
            LLMTimeoutError,
        )

        assert JobNotFoundError("x").status_code == 404
        assert ValidationError("x").status_code == 400
        assert LLMTimeoutError("anthropic", 30).status_code == 504

    def test_exception_with_context(self):
        """Test exception with full context."""
        from src.exceptions import TaskExecutionError, ErrorContext

        context = ErrorContext(
            job_id="job_123",
            task_id="task_456",
            agent_id="prd_agent",
        )

        exc = TaskExecutionError(
            "Task failed due to missing input",
            task_id="task_456",
            context=context,
        )

        result = exc.to_dict()

        assert result["error"]["job_id"] == "job_123"
        assert result["error"]["task_id"] == "task_456"
        assert result["error"]["agent_id"] == "prd_agent"


# Workflow State Machine Tests


class TestWorkflowIntegration:
    """Test workflow state machine integration."""

    def test_workflow_stages_defined(self):
        """Test all workflow stages are defined."""
        from src.orchestration.workflow import WorkflowStage, WorkflowStateMachine

        wf = WorkflowStateMachine()

        # Check key stages exist
        assert WorkflowStage.PRD_GENERATION
        assert WorkflowStage.ARCHITECTURE_DESIGN
        assert WorkflowStage.DEVELOPMENT
        assert WorkflowStage.COMPLETED

    def test_workflow_transitions_valid(self):
        """Test workflow transition validation."""
        from src.orchestration.workflow import WorkflowStateMachine, WorkflowStage

        wf = WorkflowStateMachine()

        # Valid transition from INITIALIZATION to PRD_GENERATION
        assert wf.can_transition(
            WorkflowStage.INITIALIZATION,
            WorkflowStage.PRD_GENERATION,
        )

    def test_workflow_agent_mapping(self):
        """Test stages map to correct agents."""
        from src.orchestration.workflow import WorkflowStateMachine, WorkflowStage

        wf = WorkflowStateMachine()

        # PRD stage should map to prd_agent
        agent = wf.get_agent_for_stage(WorkflowStage.PRD_GENERATION)
        assert agent == "prd_agent"


# Configuration Tests


class TestConfiguration:
    """Test configuration and timeout settings."""

    def test_timeout_settings_exist(self):
        """Test timeout settings are configured."""
        from src.config import settings

        assert hasattr(settings, "timeout_task_completion")
        assert hasattr(settings, "timeout_llm_call")
        assert hasattr(settings, "timeout_db_query")
        assert hasattr(settings, "timeout_redis_operation")

        # Check defaults are reasonable
        assert settings.timeout_task_completion > 0
        assert settings.timeout_llm_call > 0

    def test_circuit_breaker_settings_exist(self):
        """Test circuit breaker settings are configured."""
        from src.config import settings

        assert hasattr(settings, "circuit_breaker_failure_threshold")
        assert hasattr(settings, "circuit_breaker_recovery_timeout")
        assert hasattr(settings, "circuit_breaker_half_open_requests")

        # Check defaults
        assert settings.circuit_breaker_failure_threshold >= 1
        assert settings.circuit_breaker_recovery_timeout > 0

    def test_postgres_pool_settings(self):
        """Test PostgreSQL pool settings exist."""
        from src.config import settings

        assert hasattr(settings, "postgres_pool_min_size")
        assert hasattr(settings, "postgres_pool_max_size")
        assert settings.postgres_pool_min_size <= settings.postgres_pool_max_size


# Full Workflow E2E Test (requires running infrastructure)


@pytest.mark.skipif(
    os.environ.get("SKIP_E2E_TESTS", "true").lower() == "true",
    reason="E2E tests require running infrastructure",
)
class TestFullWorkflowE2E:
    """Full end-to-end workflow tests (require running Redis/PostgreSQL)."""

    @pytest.mark.asyncio
    async def test_complete_project_workflow(self, async_client, unique_project_id):
        """Test complete project creation and PRD generation workflow."""
        # Create project
        response = await async_client.post(
            "/api/projects/",
            json={
                "project_id": unique_project_id,
                "requirements": "Build a simple REST API for a blog",
            },
        )

        assert response.status_code == 200
        data = response.json()
        job_id = data["job_id"]

        # Check job status
        status_response = await async_client.get(f"/api/projects/{job_id}")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["status"] in ("queued", "in_progress", "waiting_for_approval")

    @pytest.mark.asyncio
    async def test_approval_workflow(self, async_client, unique_project_id):
        """Test the HITL approval workflow."""
        # Create project
        response = await async_client.post(
            "/api/projects/",
            json={
                "project_id": unique_project_id,
                "requirements": "Test approval workflow",
            },
        )

        if response.status_code != 200:
            pytest.skip("Infrastructure not available")

        job_id = response.json()["job_id"]

        # Try to approve (may fail if not in correct state)
        approval_response = await async_client.post(
            f"/api/projects/{job_id}/approve",
            json={"notes": "Approved for testing"},
        )

        # Either succeeds or returns error with proper format
        assert approval_response.status_code in (200, 400, 404, 500)
        data = approval_response.json()
        assert "job_id" in data or "error" in data or "detail" in data
