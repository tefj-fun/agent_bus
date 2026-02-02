"""Pydantic models for API document representation and policies.

These models define the structure for storing external API documentation
in long-term memory, including endpoints, parameters, responses, and policies.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, HttpUrl


class HTTPMethod(str, Enum):
    """HTTP methods for API endpoints."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class ParameterLocation(str, Enum):
    """Location of API parameters."""

    PATH = "path"
    QUERY = "query"
    HEADER = "header"
    BODY = "body"
    COOKIE = "cookie"


class AuthenticationType(str, Enum):
    """Types of API authentication."""

    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    OAUTH2 = "oauth2"
    BASIC = "basic"
    CUSTOM = "custom"
    NONE = "none"


class DocumentFormat(str, Enum):
    """Supported API document formats."""

    OPENAPI_3 = "openapi_3"
    OPENAPI_2 = "openapi_2"  # Swagger
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    TEXT = "text"
    UNKNOWN = "unknown"


# ============================================================================
# Core API Structure Models
# ============================================================================


class APIParameter(BaseModel):
    """Represents a single API parameter."""

    name: str = Field(..., description="Parameter name")
    location: ParameterLocation = Field(..., description="Where the parameter is sent")
    required: bool = Field(default=False, description="Whether the parameter is required")
    param_type: str = Field(default="string", description="Data type (string, integer, etc.)")
    description: Optional[str] = Field(default=None, description="Parameter description")
    default: Optional[Any] = Field(default=None, description="Default value if not provided")
    enum_values: Optional[List[str]] = Field(
        default=None, description="Allowed values for enum types"
    )
    example: Optional[Any] = Field(default=None, description="Example value")
    constraints: Optional[Dict[str, Any]] = Field(
        default=None, description="Validation constraints (min, max, pattern, etc.)"
    )


class APIResponse(BaseModel):
    """Represents an API response."""

    status_code: int = Field(..., description="HTTP status code")
    description: Optional[str] = Field(default=None, description="Response description")
    content_type: str = Field(default="application/json", description="Response content type")
    schema: Optional[Dict[str, Any]] = Field(default=None, description="Response schema/structure")
    example: Optional[Any] = Field(default=None, description="Example response")
    headers: Optional[Dict[str, str]] = Field(default=None, description="Response headers")


class APIEndpoint(BaseModel):
    """Represents a single API endpoint."""

    path: str = Field(..., description="Endpoint path (e.g., /users/{id})")
    method: HTTPMethod = Field(..., description="HTTP method")
    summary: Optional[str] = Field(default=None, description="Short summary")
    description: Optional[str] = Field(default=None, description="Detailed description")
    operation_id: Optional[str] = Field(default=None, description="Unique operation identifier")
    tags: List[str] = Field(default_factory=list, description="Categorization tags")
    parameters: List[APIParameter] = Field(
        default_factory=list, description="Input parameters"
    )
    request_body: Optional[Dict[str, Any]] = Field(
        default=None, description="Request body schema"
    )
    responses: List[APIResponse] = Field(default_factory=list, description="Possible responses")
    deprecated: bool = Field(default=False, description="Whether endpoint is deprecated")
    security: Optional[List[str]] = Field(
        default=None, description="Security requirements"
    )
    rate_limit: Optional[str] = Field(
        default=None, description="Specific rate limit for this endpoint"
    )
    examples: Optional[Dict[str, Any]] = Field(
        default=None, description="Request/response examples"
    )

    def get_full_path(self, base_url: str = "") -> str:
        """Get the full URL for this endpoint."""
        return f"{base_url.rstrip('/')}/{self.path.lstrip('/')}"

    def get_memory_text(self) -> str:
        """Generate text representation for memory storage and search."""
        parts = [
            f"Endpoint: {self.method.value} {self.path}",
            f"Summary: {self.summary or 'No summary'}",
        ]
        if self.description:
            parts.append(f"Description: {self.description}")
        if self.parameters:
            param_text = ", ".join(
                f"{p.name} ({p.location.value}, {'required' if p.required else 'optional'})"
                for p in self.parameters
            )
            parts.append(f"Parameters: {param_text}")
        if self.responses:
            response_text = ", ".join(f"{r.status_code}" for r in self.responses)
            parts.append(f"Responses: {response_text}")
        return "\n".join(parts)


# ============================================================================
# Policy Models
# ============================================================================


class RateLimitPolicy(BaseModel):
    """Rate limiting policy extracted from API documentation."""

    requests_per_minute: Optional[int] = Field(
        default=None, description="Max requests per minute"
    )
    requests_per_hour: Optional[int] = Field(
        default=None, description="Max requests per hour"
    )
    requests_per_day: Optional[int] = Field(
        default=None, description="Max requests per day"
    )
    burst_limit: Optional[int] = Field(
        default=None, description="Max burst requests"
    )
    concurrent_limit: Optional[int] = Field(
        default=None, description="Max concurrent requests"
    )
    retry_after_header: bool = Field(
        default=True, description="Whether API returns Retry-After header"
    )
    rate_limit_headers: List[str] = Field(
        default_factory=lambda: ["X-RateLimit-Limit", "X-RateLimit-Remaining"],
        description="Headers used for rate limit info",
    )
    endpoint_specific: Optional[Dict[str, Dict[str, int]]] = Field(
        default=None, description="Per-endpoint rate limits"
    )
    notes: Optional[str] = Field(default=None, description="Additional rate limit notes")


class AuthenticationPolicy(BaseModel):
    """Authentication policy extracted from API documentation."""

    auth_type: AuthenticationType = Field(..., description="Primary authentication type")
    header_name: Optional[str] = Field(
        default=None, description="Header name for auth (e.g., Authorization)"
    )
    header_prefix: Optional[str] = Field(
        default=None, description="Header value prefix (e.g., Bearer)"
    )
    api_key_location: Optional[ParameterLocation] = Field(
        default=None, description="Where API key is sent"
    )
    api_key_name: Optional[str] = Field(
        default=None, description="Name of API key parameter"
    )
    oauth_flows: Optional[Dict[str, Any]] = Field(
        default=None, description="OAuth2 flow configurations"
    )
    scopes: Optional[Dict[str, str]] = Field(
        default=None, description="Available OAuth scopes and descriptions"
    )
    token_url: Optional[str] = Field(
        default=None, description="Token endpoint for OAuth"
    )
    refresh_url: Optional[str] = Field(
        default=None, description="Token refresh endpoint"
    )
    expiration_seconds: Optional[int] = Field(
        default=None, description="Token expiration time"
    )
    notes: Optional[str] = Field(default=None, description="Additional auth notes")


class ErrorHandlingPolicy(BaseModel):
    """Error handling policy extracted from API documentation."""

    error_format: Optional[Dict[str, Any]] = Field(
        default=None, description="Standard error response structure"
    )
    error_codes: Dict[str, str] = Field(
        default_factory=dict, description="Error codes and their meanings"
    )
    retry_codes: List[int] = Field(
        default_factory=lambda: [429, 500, 502, 503, 504],
        description="HTTP codes that should trigger retry",
    )
    non_retry_codes: List[int] = Field(
        default_factory=lambda: [400, 401, 403, 404],
        description="HTTP codes that should not retry",
    )
    max_retries: int = Field(default=3, description="Recommended max retries")
    backoff_strategy: str = Field(
        default="exponential", description="Retry backoff strategy"
    )
    idempotency_key_header: Optional[str] = Field(
        default=None, description="Header for idempotency key"
    )
    notes: Optional[str] = Field(default=None, description="Additional error handling notes")


class APIPolicy(BaseModel):
    """Combined API policies."""

    rate_limit: Optional[RateLimitPolicy] = Field(
        default=None, description="Rate limiting policy"
    )
    authentication: Optional[AuthenticationPolicy] = Field(
        default=None, description="Authentication policy"
    )
    error_handling: Optional[ErrorHandlingPolicy] = Field(
        default=None, description="Error handling policy"
    )
    usage_guidelines: Optional[str] = Field(
        default=None, description="General usage guidelines"
    )
    terms_of_service: Optional[str] = Field(
        default=None, description="Terms of service summary"
    )
    deprecation_policy: Optional[str] = Field(
        default=None, description="API deprecation policy"
    )
    versioning_strategy: Optional[str] = Field(
        default=None, description="API versioning approach"
    )


# ============================================================================
# Document Models
# ============================================================================


class APIDocument(BaseModel):
    """Raw API document before processing."""

    doc_id: str = Field(..., description="Unique document identifier")
    name: str = Field(..., description="API name (e.g., 'Stripe API')")
    version: Optional[str] = Field(default=None, description="API version")
    format: DocumentFormat = Field(..., description="Document format")
    source_url: Optional[str] = Field(default=None, description="Original document URL")
    content: str = Field(..., description="Raw document content")
    content_hash: Optional[str] = Field(
        default=None, description="Hash of content for change detection"
    )
    uploaded_at: datetime = Field(
        default_factory=datetime.utcnow, description="Upload timestamp"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class ProcessedAPIDocument(BaseModel):
    """Fully processed API document ready for memory storage."""

    doc_id: str = Field(..., description="Unique document identifier")
    name: str = Field(..., description="API name")
    version: Optional[str] = Field(default=None, description="API version")
    base_url: Optional[str] = Field(default=None, description="API base URL")
    description: Optional[str] = Field(default=None, description="API description")
    format: DocumentFormat = Field(..., description="Original document format")

    # Extracted structure
    endpoints: List[APIEndpoint] = Field(
        default_factory=list, description="Parsed API endpoints"
    )
    policies: APIPolicy = Field(
        default_factory=APIPolicy, description="Extracted policies"
    )
    tags: List[str] = Field(default_factory=list, description="API tags/categories")
    servers: List[Dict[str, str]] = Field(
        default_factory=list, description="Available servers/environments"
    )

    # Memory metadata
    processed_at: datetime = Field(
        default_factory=datetime.utcnow, description="Processing timestamp"
    )
    chunk_count: int = Field(default=0, description="Number of memory chunks created")
    source_url: Optional[str] = Field(default=None, description="Original document URL")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    def get_summary_text(self) -> str:
        """Generate a summary for high-level memory storage."""
        parts = [
            f"API: {self.name}",
            f"Version: {self.version or 'unspecified'}",
            f"Description: {self.description or 'No description'}",
            f"Base URL: {self.base_url or 'Not specified'}",
            f"Endpoints: {len(self.endpoints)} total",
        ]
        if self.tags:
            parts.append(f"Tags: {', '.join(self.tags)}")
        if self.policies.authentication:
            parts.append(f"Auth: {self.policies.authentication.auth_type.value}")
        if self.policies.rate_limit:
            rl = self.policies.rate_limit
            if rl.requests_per_minute:
                parts.append(f"Rate Limit: {rl.requests_per_minute} req/min")
        return "\n".join(parts)

    def get_endpoint_groups(self) -> Dict[str, List[APIEndpoint]]:
        """Group endpoints by their first tag."""
        groups: Dict[str, List[APIEndpoint]] = {}
        for endpoint in self.endpoints:
            tag = endpoint.tags[0] if endpoint.tags else "default"
            if tag not in groups:
                groups[tag] = []
            groups[tag].append(endpoint)
        return groups


# ============================================================================
# Memory Pattern Types for API Documents
# ============================================================================


class APIMemoryPatternType(str, Enum):
    """Pattern types for API document memory storage."""

    API_OVERVIEW = "api_overview"  # High-level API summary
    API_ENDPOINT = "api_endpoint"  # Individual endpoint details
    API_POLICY = "api_policy"  # Rate limits, auth, error handling
    API_SCHEMA = "api_schema"  # Data models and schemas
    API_EXAMPLE = "api_example"  # Code examples and snippets
    API_INTEGRATION = "api_integration"  # Integration guidance
