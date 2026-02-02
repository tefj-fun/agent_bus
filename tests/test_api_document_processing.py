"""Tests for API document processing system.

Tests for:
- APIDocumentParser (multi-format parsing)
- Schema models
- Policy extraction
- Memory storage patterns
"""

import json
import pytest
from datetime import datetime

from src.api_docs.parser import APIDocumentParser
from src.api_docs.schema import (
    APIDocument,
    APIEndpoint,
    APIParameter,
    APIPolicy,
    APIResponse,
    AuthenticationPolicy,
    AuthenticationType,
    DocumentFormat,
    ErrorHandlingPolicy,
    HTTPMethod,
    ParameterLocation,
    ProcessedAPIDocument,
    RateLimitPolicy,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def parser():
    """Create an API document parser instance."""
    return APIDocumentParser()


@pytest.fixture
def sample_openapi_3_spec():
    """Sample OpenAPI 3.0 specification."""
    return json.dumps({
        "openapi": "3.0.0",
        "info": {
            "title": "Test API",
            "description": "A test API for unit testing",
            "version": "1.0.0"
        },
        "servers": [
            {"url": "https://api.example.com/v1", "description": "Production"}
        ],
        "paths": {
            "/users": {
                "get": {
                    "summary": "List users",
                    "description": "Get a paginated list of users",
                    "operationId": "listUsers",
                    "tags": ["users"],
                    "parameters": [
                        {
                            "name": "page",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 1}
                        },
                        {
                            "name": "limit",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 10, "maximum": 100}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "array"}
                                }
                            }
                        },
                        "401": {"description": "Unauthorized"}
                    }
                },
                "post": {
                    "summary": "Create user",
                    "operationId": "createUser",
                    "tags": ["users"],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "email": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {"description": "Created"},
                        "400": {"description": "Bad request"}
                    }
                }
            },
            "/users/{id}": {
                "get": {
                    "summary": "Get user by ID",
                    "operationId": "getUser",
                    "tags": ["users"],
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"}
                        }
                    ],
                    "responses": {
                        "200": {"description": "Success"},
                        "404": {"description": "Not found"}
                    }
                }
            }
        },
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer"
                }
            }
        }
    })


@pytest.fixture
def sample_openapi_2_spec():
    """Sample OpenAPI 2.0 (Swagger) specification."""
    return json.dumps({
        "swagger": "2.0",
        "info": {
            "title": "Legacy API",
            "version": "1.0.0"
        },
        "host": "api.legacy.com",
        "basePath": "/v1",
        "schemes": ["https"],
        "paths": {
            "/products": {
                "get": {
                    "summary": "List products",
                    "operationId": "listProducts",
                    "produces": ["application/json"],
                    "parameters": [
                        {
                            "name": "category",
                            "in": "query",
                            "type": "string"
                        }
                    ],
                    "responses": {
                        "200": {"description": "OK"}
                    }
                }
            }
        },
        "securityDefinitions": {
            "api_key": {
                "type": "apiKey",
                "name": "X-API-Key",
                "in": "header"
            }
        }
    })


@pytest.fixture
def sample_markdown_doc():
    """Sample Markdown API documentation."""
    return """
# Payment API

A simple API for processing payments.

Base URL: https://payments.example.com/api/v1

## Authentication

This API uses Bearer token authentication.
Include your API key in the Authorization header.

## Rate Limits

- 100 requests per minute
- 1000 requests per hour

## Endpoints

### POST /payments

Create a new payment.

Parameters:
- `amount` (integer, required): Payment amount in cents
- `currency` (string, required): ISO currency code
- `description` (string, optional): Payment description

### GET /payments/{id}

Get payment details by ID.

Parameters:
- `id` (path, required): Payment ID

### GET /payments

List all payments with pagination.

Parameters:
- `page` (query, optional): Page number
- `limit` (query, optional): Items per page

## Error Handling

Retry on 429, 500, 502, 503 status codes.
Use exponential backoff with max 3 retries.
"""


@pytest.fixture
def sample_text_doc():
    """Sample plain text API documentation."""
    return """
User Service API v2.0

Endpoints:
GET /users - List all users
POST /users - Create a user
GET /users/{id} - Get user by ID
PUT /users/{id} - Update user
DELETE /users/{id} - Delete user

Authentication: API Key in X-API-Key header

Rate limit: 60 requests per minute
"""


# =============================================================================
# Format Detection Tests
# =============================================================================


class TestFormatDetection:
    """Tests for API document format detection."""

    def test_detect_openapi_3_json(self, parser):
        """Test detection of OpenAPI 3.x JSON."""
        content = '{"openapi": "3.0.0", "info": {"title": "Test"}}'
        assert parser.detect_format(content) == DocumentFormat.OPENAPI_3

    def test_detect_openapi_3_yaml(self, parser):
        """Test detection of OpenAPI 3.x YAML."""
        content = "openapi: '3.0.0'\ninfo:\n  title: Test"
        assert parser.detect_format(content) == DocumentFormat.OPENAPI_3

    def test_detect_swagger_json(self, parser):
        """Test detection of Swagger/OpenAPI 2.x JSON."""
        content = '{"swagger": "2.0", "info": {"title": "Test"}}'
        assert parser.detect_format(content) == DocumentFormat.OPENAPI_2

    def test_detect_swagger_yaml(self, parser):
        """Test detection of Swagger/OpenAPI 2.x YAML."""
        content = "swagger: '2.0'\ninfo:\n  title: Test"
        assert parser.detect_format(content) == DocumentFormat.OPENAPI_2

    def test_detect_markdown(self, parser):
        """Test detection of Markdown documentation."""
        content = "# API Documentation\n\nThis is the **API** description.\n\n## Endpoints"
        assert parser.detect_format(content) == DocumentFormat.MARKDOWN

    def test_detect_html(self, parser):
        """Test detection of HTML documentation."""
        content = "<!DOCTYPE html><html><body>API docs</body></html>"
        assert parser.detect_format(content) == DocumentFormat.HTML

    def test_detect_text(self, parser):
        """Test detection of plain text documentation."""
        content = "API Documentation\n\nGET /users - List users"
        assert parser.detect_format(content) == DocumentFormat.TEXT


# =============================================================================
# OpenAPI 3.x Parsing Tests
# =============================================================================


class TestOpenAPI3Parsing:
    """Tests for OpenAPI 3.x specification parsing."""

    def test_parse_basic_info(self, parser, sample_openapi_3_spec):
        """Test parsing of basic API information."""
        result = parser.parse(
            doc_id="test_api",
            name="Test API",
            content=sample_openapi_3_spec,
        )

        assert result.name == "Test API"
        assert result.version == "1.0.0"
        assert result.description == "A test API for unit testing"
        assert result.format == DocumentFormat.OPENAPI_3

    def test_parse_base_url(self, parser, sample_openapi_3_spec):
        """Test parsing of base URL from servers."""
        result = parser.parse(
            doc_id="test_api",
            name="Test API",
            content=sample_openapi_3_spec,
        )

        assert result.base_url == "https://api.example.com/v1"
        assert len(result.servers) == 1
        assert result.servers[0]["description"] == "Production"

    def test_parse_endpoints(self, parser, sample_openapi_3_spec):
        """Test parsing of API endpoints."""
        result = parser.parse(
            doc_id="test_api",
            name="Test API",
            content=sample_openapi_3_spec,
        )

        assert len(result.endpoints) == 3

        # Check GET /users
        get_users = next(e for e in result.endpoints if e.path == "/users" and e.method == HTTPMethod.GET)
        assert get_users.summary == "List users"
        assert get_users.operation_id == "listUsers"
        assert "users" in get_users.tags

    def test_parse_parameters(self, parser, sample_openapi_3_spec):
        """Test parsing of endpoint parameters."""
        result = parser.parse(
            doc_id="test_api",
            name="Test API",
            content=sample_openapi_3_spec,
        )

        get_users = next(e for e in result.endpoints if e.path == "/users" and e.method == HTTPMethod.GET)
        assert len(get_users.parameters) == 2

        page_param = next(p for p in get_users.parameters if p.name == "page")
        assert page_param.location == ParameterLocation.QUERY
        assert page_param.required is False
        assert page_param.param_type == "integer"

    def test_parse_responses(self, parser, sample_openapi_3_spec):
        """Test parsing of endpoint responses."""
        result = parser.parse(
            doc_id="test_api",
            name="Test API",
            content=sample_openapi_3_spec,
        )

        get_users = next(e for e in result.endpoints if e.path == "/users" and e.method == HTTPMethod.GET)
        assert len(get_users.responses) == 2

        success_response = next(r for r in get_users.responses if r.status_code == 200)
        assert success_response.description == "Successful response"

    def test_parse_bearer_auth(self, parser, sample_openapi_3_spec):
        """Test parsing of Bearer token authentication."""
        result = parser.parse(
            doc_id="test_api",
            name="Test API",
            content=sample_openapi_3_spec,
        )

        assert result.policies.authentication is not None
        assert result.policies.authentication.auth_type == AuthenticationType.BEARER_TOKEN
        assert result.policies.authentication.header_name == "Authorization"
        assert result.policies.authentication.header_prefix == "Bearer"


# =============================================================================
# OpenAPI 2.x (Swagger) Parsing Tests
# =============================================================================


class TestOpenAPI2Parsing:
    """Tests for OpenAPI 2.x (Swagger) specification parsing."""

    def test_parse_swagger_basic(self, parser, sample_openapi_2_spec):
        """Test parsing of basic Swagger specification."""
        result = parser.parse(
            doc_id="legacy_api",
            name="Legacy API",
            content=sample_openapi_2_spec,
        )

        assert result.name == "Legacy API"
        assert result.version == "1.0.0"
        assert result.format == DocumentFormat.OPENAPI_2

    def test_parse_swagger_base_url(self, parser, sample_openapi_2_spec):
        """Test parsing of base URL from host and basePath."""
        result = parser.parse(
            doc_id="legacy_api",
            name="Legacy API",
            content=sample_openapi_2_spec,
        )

        assert result.base_url == "https://api.legacy.com/v1"

    def test_parse_swagger_api_key_auth(self, parser, sample_openapi_2_spec):
        """Test parsing of API key authentication."""
        result = parser.parse(
            doc_id="legacy_api",
            name="Legacy API",
            content=sample_openapi_2_spec,
        )

        assert result.policies.authentication is not None
        assert result.policies.authentication.auth_type == AuthenticationType.API_KEY
        assert result.policies.authentication.api_key_name == "X-API-Key"


# =============================================================================
# Markdown Parsing Tests
# =============================================================================


class TestMarkdownParsing:
    """Tests for Markdown documentation parsing."""

    def test_parse_markdown_endpoints(self, parser, sample_markdown_doc):
        """Test parsing of endpoints from Markdown."""
        result = parser.parse(
            doc_id="payment_api",
            name="Payment API",
            content=sample_markdown_doc,
        )

        assert result.format == DocumentFormat.MARKDOWN
        assert len(result.endpoints) >= 2  # POST /payments and GET /payments/{id}

    def test_parse_markdown_rate_limits(self, parser, sample_markdown_doc):
        """Test extraction of rate limits from Markdown."""
        result = parser.parse(
            doc_id="payment_api",
            name="Payment API",
            content=sample_markdown_doc,
        )

        assert result.policies.rate_limit is not None
        assert result.policies.rate_limit.requests_per_minute == 100
        assert result.policies.rate_limit.requests_per_hour == 1000


# =============================================================================
# Text Parsing Tests
# =============================================================================


class TestTextParsing:
    """Tests for plain text documentation parsing."""

    def test_parse_text_endpoints(self, parser, sample_text_doc):
        """Test parsing of endpoints from plain text."""
        result = parser.parse(
            doc_id="user_api",
            name="User API",
            content=sample_text_doc,
        )

        assert result.format == DocumentFormat.TEXT
        assert len(result.endpoints) >= 4  # Multiple endpoints

    def test_parse_text_rate_limit(self, parser, sample_text_doc):
        """Test extraction of rate limit from plain text."""
        result = parser.parse(
            doc_id="user_api",
            name="User API",
            content=sample_text_doc,
        )

        assert result.policies.rate_limit is not None
        assert result.policies.rate_limit.requests_per_minute == 60


# =============================================================================
# Schema Model Tests
# =============================================================================


class TestSchemaModels:
    """Tests for Pydantic schema models."""

    def test_api_endpoint_memory_text(self):
        """Test endpoint memory text generation."""
        endpoint = APIEndpoint(
            path="/users/{id}",
            method=HTTPMethod.GET,
            summary="Get user by ID",
            description="Retrieves a user by their unique identifier",
            parameters=[
                APIParameter(
                    name="id",
                    location=ParameterLocation.PATH,
                    required=True,
                    param_type="string",
                )
            ],
            responses=[
                APIResponse(status_code=200, description="Success"),
                APIResponse(status_code=404, description="Not found"),
            ],
        )

        text = endpoint.get_memory_text()
        assert "GET /users/{id}" in text
        assert "Get user by ID" in text
        assert "id (path, required)" in text
        assert "200" in text

    def test_processed_document_summary(self):
        """Test processed document summary generation."""
        doc = ProcessedAPIDocument(
            doc_id="test",
            name="Test API",
            version="1.0.0",
            base_url="https://api.test.com",
            description="A test API",
            format=DocumentFormat.OPENAPI_3,
            endpoints=[
                APIEndpoint(path="/users", method=HTTPMethod.GET),
                APIEndpoint(path="/users", method=HTTPMethod.POST),
            ],
            policies=APIPolicy(
                authentication=AuthenticationPolicy(
                    auth_type=AuthenticationType.BEARER_TOKEN,
                ),
                rate_limit=RateLimitPolicy(requests_per_minute=100),
            ),
        )

        summary = doc.get_summary_text()
        assert "Test API" in summary
        assert "1.0.0" in summary
        assert "2 total" in summary  # 2 endpoints
        assert "bearer_token" in summary

    def test_endpoint_groups(self):
        """Test endpoint grouping by tags."""
        doc = ProcessedAPIDocument(
            doc_id="test",
            name="Test API",
            format=DocumentFormat.OPENAPI_3,
            endpoints=[
                APIEndpoint(path="/users", method=HTTPMethod.GET, tags=["users"]),
                APIEndpoint(path="/users", method=HTTPMethod.POST, tags=["users"]),
                APIEndpoint(path="/products", method=HTTPMethod.GET, tags=["products"]),
            ],
        )

        groups = doc.get_endpoint_groups()
        assert "users" in groups
        assert "products" in groups
        assert len(groups["users"]) == 2
        assert len(groups["products"]) == 1


# =============================================================================
# Policy Model Tests
# =============================================================================


class TestPolicyModels:
    """Tests for policy models."""

    def test_rate_limit_policy(self):
        """Test rate limit policy model."""
        policy = RateLimitPolicy(
            requests_per_minute=100,
            requests_per_hour=5000,
            burst_limit=20,
            retry_after_header=True,
        )

        assert policy.requests_per_minute == 100
        assert policy.requests_per_hour == 5000
        assert policy.burst_limit == 20
        assert policy.retry_after_header is True

    def test_authentication_policy(self):
        """Test authentication policy model."""
        policy = AuthenticationPolicy(
            auth_type=AuthenticationType.OAUTH2,
            token_url="https://auth.example.com/token",
            scopes={"read": "Read access", "write": "Write access"},
        )

        assert policy.auth_type == AuthenticationType.OAUTH2
        assert policy.token_url == "https://auth.example.com/token"
        assert "read" in policy.scopes

    def test_error_handling_policy(self):
        """Test error handling policy model."""
        policy = ErrorHandlingPolicy(
            retry_codes=[429, 500, 502, 503],
            max_retries=3,
            backoff_strategy="exponential",
            idempotency_key_header="Idempotency-Key",
        )

        assert 429 in policy.retry_codes
        assert policy.max_retries == 3
        assert policy.backoff_strategy == "exponential"


# =============================================================================
# Integration Tests
# =============================================================================


class TestParserIntegration:
    """Integration tests for the parser."""

    def test_full_parsing_workflow(self, parser, sample_openapi_3_spec):
        """Test complete parsing workflow."""
        result = parser.parse(
            doc_id="integration_test",
            name="Integration Test API",
            content=sample_openapi_3_spec,
            source_url="https://docs.example.com/api",
            version="2.0.0",  # Override version
            metadata={"environment": "test"},
        )

        # Basic info
        assert result.doc_id == "integration_test"
        assert result.name == "Integration Test API"
        assert result.version == "2.0.0"  # Overridden
        assert result.source_url == "https://docs.example.com/api"
        assert result.metadata["environment"] == "test"

        # Endpoints
        assert len(result.endpoints) > 0

        # Policies
        assert result.policies is not None

    def test_invalid_json_fallback(self, parser):
        """Test fallback to text parsing for invalid JSON."""
        invalid_json = '{"openapi": "3.0.0", invalid json here}'

        result = parser.parse(
            doc_id="invalid",
            name="Invalid API",
            content=invalid_json,
            format_hint=DocumentFormat.OPENAPI_3,
        )

        # Should fall back to text parsing
        assert result.format == DocumentFormat.TEXT

    def test_empty_content(self, parser):
        """Test parsing of empty content."""
        result = parser.parse(
            doc_id="empty",
            name="Empty API",
            content="",
        )

        assert result.name == "Empty API"
        assert len(result.endpoints) == 0
