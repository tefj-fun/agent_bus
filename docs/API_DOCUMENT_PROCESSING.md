# API Document Processing System

This document describes the API Document Processing system in Agent Bus, which allows you to ingest external API documentation into long-term memory for use during development work.

## Overview

When building integrations with external APIs, agents need context about:
- Available endpoints and their parameters
- Authentication requirements
- Rate limiting policies
- Error handling guidelines

The API Document Processing system solves this by:
1. **Parsing** API documentation in multiple formats (OpenAPI, Markdown, plain text)
2. **Extracting** structured information (endpoints, policies, schemas)
3. **Storing** the information as searchable memory patterns in ChromaDB
4. **Providing** context to agents during development tasks

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    API Document Processing                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│   │   Parser     │───▶│   Policy     │───▶│   Memory     │     │
│   │  (Multi-fmt) │    │  Extractor   │    │   Store      │     │
│   └──────────────┘    │   (LLM)      │    │  (ChromaDB)  │     │
│                       └──────────────┘    └──────────────┘     │
│                                                                  │
│   Supported Formats:                    Memory Pattern Types:   │
│   • OpenAPI 3.x (JSON/YAML)            • api_overview           │
│   • OpenAPI 2.x / Swagger              • api_endpoint           │
│   • Markdown                           • api_policy             │
│   • HTML                               • api_integration        │
│   • Plain text                                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. API Document Parser (`src/api_docs/parser.py`)

Multi-format parser that handles:

| Format | Detection | Features |
|--------|-----------|----------|
| **OpenAPI 3.x** | `openapi: "3.x.x"` | Full parsing of paths, parameters, responses, security schemes |
| **OpenAPI 2.x** | `swagger: "2.0"` | Full parsing with automatic conversion to unified format |
| **Markdown** | Headers, code blocks | Endpoint extraction from headers, parameter tables |
| **HTML** | `<!DOCTYPE html>` | Text extraction with HTML tag stripping |
| **Plain Text** | Default | Pattern-based endpoint detection |

### 2. Policy Extractor (`src/api_docs/policy_extractor.py`)

Uses Claude LLM to extract nuanced policy information:

- Rate limiting (requests per minute/hour/day, burst limits)
- Authentication (API keys, OAuth, Bearer tokens)
- Error handling (retry strategies, error codes)
- Usage guidelines and best practices

### 3. API Document Agent (`src/agents/api_document_agent.py`)

Orchestrates the processing pipeline:

```python
# Actions supported:
- process_document    # Parse and store an API document
- query_endpoints     # Search for relevant endpoints
- get_policies        # Retrieve policies for an API
- suggest_integration # Get integration suggestions
- get_development_context # Comprehensive context for a task
- list_apis           # List all stored API documents
```

### 4. Memory Storage Patterns

Documents are stored as multiple memory patterns:

| Pattern Type | Description | Use Case |
|--------------|-------------|----------|
| `api_overview` | High-level API summary | Finding relevant APIs |
| `api_endpoint` | Individual endpoint details | Finding specific operations |
| `api_policy` | Rate limits, auth, errors | Understanding constraints |
| `api_integration` | Usage guidelines | Implementation guidance |

## API Reference

### Process a Document

```bash
POST /api/api-documents/process
```

**Request:**
```json
{
  "content": "<raw API document content>",
  "name": "Stripe API",
  "doc_id": "stripe_api_v1",       // Optional
  "format": "openapi_3",           // Optional, auto-detected
  "source_url": "https://...",     // Optional
  "version": "2024-01",            // Optional
  "use_llm_extraction": true,      // Use LLM for enhanced extraction
  "metadata": {}                   // Custom metadata
}
```

**Response:**
```json
{
  "status": "success",
  "doc_id": "stripe_api_v1",
  "api_name": "Stripe API",
  "api_version": "2024-01",
  "format": "openapi_3",
  "endpoints_count": 150,
  "has_rate_limit": true,
  "has_authentication": true,
  "memory_patterns_created": 156,
  "base_url": "https://api.stripe.com/v1"
}
```

### Upload a File

```bash
POST /api/api-documents/upload
Content-Type: multipart/form-data
```

**Form Fields:**
- `file`: API document file (JSON, YAML, MD, TXT)
- `name`: API name (required)
- `version`: API version (optional)
- `source_url`: Original URL (optional)
- `use_llm_extraction`: Use LLM extraction (default: true)

### Query Endpoints

```bash
POST /api/api-documents/query/endpoints
```

**Request:**
```json
{
  "query": "create a payment intent",
  "api_name": "Stripe API",     // Optional filter
  "method": "POST",             // Optional filter
  "top_k": 10
}
```

**Response:**
```json
{
  "status": "success",
  "query": "create a payment intent",
  "results": [
    {
      "id": "stripe_api_v1_endpoint_42",
      "text": "Endpoint: POST /v1/payment_intents\nSummary: Create a PaymentIntent...",
      "metadata": {
        "api_name": "Stripe API",
        "http_method": "POST",
        "path": "/v1/payment_intents"
      },
      "score": 0.89
    }
  ],
  "count": 5
}
```

### Get Policies

```bash
POST /api/api-documents/query/policies
```

**Request:**
```json
{
  "api_name": "Stripe API",
  "policy_type": "rate_limit"   // Optional: rate_limit, authentication, error_handling
}
```

**Response:**
```json
{
  "status": "success",
  "api_name": "Stripe API",
  "policies": [
    {
      "policy_type": "rate_limit",
      "content": "Rate Limit Policy for Stripe API:\n- Requests per second: 100\n...",
      "metadata": {...}
    },
    {
      "policy_type": "authentication",
      "content": "Authentication Policy for Stripe API:\n- Type: bearer_token\n...",
      "metadata": {...}
    }
  ],
  "count": 2
}
```

### Get Development Context

```bash
POST /api/api-documents/context/development
```

**Request:**
```json
{
  "task_description": "Implement payment processing with Stripe including subscriptions",
  "api_names": ["Stripe API"],   // Optional: focus on specific APIs
  "top_k": 5
}
```

**Response:**
```json
{
  "status": "success",
  "task_description": "Implement payment processing...",
  "relevant_apis": ["Stripe API"],
  "endpoints": [...],
  "policies_by_api": {
    "Stripe API": [...]
  },
  "summary": "## API Integration Context\n\n### Relevant Endpoints\n- POST /v1/payment_intents..."
}
```

### List All APIs

```bash
GET /api/api-documents/list?limit=50
```

**Response:**
```json
{
  "status": "success",
  "apis": [
    {
      "api_name": "Stripe API",
      "api_version": "2024-01",
      "doc_id": "stripe_api_v1",
      "endpoint_count": "150",
      "source_url": "https://...",
      "processed_at": "2024-01-15T10:30:00Z"
    }
  ],
  "count": 5
}
```

### Get Specific API Document

```bash
GET /api/api-documents/{doc_id}
```

### Delete API Document

```bash
DELETE /api/api-documents/{doc_id}
```

## Usage Examples

### Example 1: Process an OpenAPI Spec

```python
import httpx
import json

# Read OpenAPI spec
with open("stripe_openapi.json") as f:
    spec_content = f.read()

# Process the document
response = httpx.post(
    "http://localhost:8000/api/api-documents/process",
    json={
        "name": "Stripe API",
        "content": spec_content,
        "version": "2024-01",
        "use_llm_extraction": True
    }
)

result = response.json()
print(f"Processed {result['endpoints_count']} endpoints")
print(f"Created {result['memory_patterns_created']} memory patterns")
```

### Example 2: Query During Development

```python
# Get context for a development task
response = httpx.post(
    "http://localhost:8000/api/api-documents/context/development",
    json={
        "task_description": "Build a checkout flow with Stripe that handles card payments and subscriptions",
    }
)

context = response.json()

# Use in agent prompt
prompt = f"""
Task: Build a checkout flow with Stripe

API Context:
{context['summary']}

Relevant Endpoints:
{json.dumps(context['endpoints'], indent=2)}

Policies:
{json.dumps(context['policies_by_api'], indent=2)}
"""
```

### Example 3: Process Markdown Documentation

```bash
# Upload markdown docs
curl -X POST http://localhost:8000/api/api-documents/upload \
  -F "file=@twilio_api_docs.md" \
  -F "name=Twilio API" \
  -F "version=2024"
```

## Schema Models

### APIEndpoint

```python
class APIEndpoint:
    path: str              # e.g., "/users/{id}"
    method: HTTPMethod     # GET, POST, PUT, etc.
    summary: str           # Short description
    description: str       # Detailed description
    parameters: List[APIParameter]
    request_body: Dict     # Request body schema
    responses: List[APIResponse]
    tags: List[str]        # Categorization
    deprecated: bool
    rate_limit: str        # Endpoint-specific rate limit
```

### APIPolicy

```python
class APIPolicy:
    rate_limit: RateLimitPolicy
    authentication: AuthenticationPolicy
    error_handling: ErrorHandlingPolicy
    usage_guidelines: str
    deprecation_policy: str
    versioning_strategy: str
```

### RateLimitPolicy

```python
class RateLimitPolicy:
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    burst_limit: int
    concurrent_limit: int
    retry_after_header: bool
```

### AuthenticationPolicy

```python
class AuthenticationPolicy:
    auth_type: AuthenticationType  # api_key, bearer_token, oauth2, basic
    header_name: str               # e.g., "Authorization"
    header_prefix: str             # e.g., "Bearer"
    api_key_name: str              # Parameter name
    api_key_location: str          # header, query, body
    scopes: Dict[str, str]         # OAuth scopes
    token_url: str                 # OAuth token endpoint
```

## Integration with Agents

Agents can access API document context through the `APIDocumentAgent`:

```python
from src.agents.api_document_agent import APIDocumentAgent
from src.agents.base import AgentTask

# Create agent
api_doc_agent = APIDocumentAgent(context)

# Get development context
task = AgentTask(
    task_id="ctx_001",
    task_type="get_context",
    input_data={
        "action": "get_development_context",
        "task_description": "Implement OAuth login with GitHub"
    },
    dependencies=[],
    priority=5,
    metadata={}
)

result = await api_doc_agent.execute(task)
# result.output contains endpoints, policies, summary
```

## Best Practices

### 1. Use Specific API Names

When processing multiple APIs, use unique, descriptive names:

```json
{
  "name": "Stripe Payments API v2024",
  "name": "GitHub REST API v2022",
  "name": "Twilio Messaging API"
}
```

### 2. Enable LLM Extraction for Complex Docs

For markdown or text documentation, enable LLM extraction:

```json
{
  "use_llm_extraction": true
}
```

### 3. Query with Specific Terms

Use domain-specific terms in queries:

```json
{
  "query": "create subscription with metered billing"
}
```

Not:
```json
{
  "query": "make a thing"
}
```

### 4. Filter by API Name for Large Collections

When you have many APIs stored, filter queries:

```json
{
  "query": "authenticate user",
  "api_name": "Auth0 Management API"
}
```

## Troubleshooting

### Document Not Parsing Correctly

1. Check the format is being detected correctly:
   ```bash
   curl -X POST .../process -d '{"content": "...", "format": "openapi_3"}'
   ```

2. For complex documents, ensure JSON/YAML is valid

3. Enable LLM extraction for better results

### No Endpoints Found

1. Verify the document contains endpoint definitions
2. For text/markdown, ensure endpoints follow patterns like:
   - `GET /users/{id}`
   - `### POST /payments`

### Policies Not Extracted

1. Check if the documentation mentions rate limits, auth, etc.
2. Enable `use_llm_extraction: true` for nuanced extraction

## File Locations

| File | Purpose |
|------|---------|
| `src/api_docs/schema.py` | Pydantic models for API documents |
| `src/api_docs/parser.py` | Multi-format document parser |
| `src/api_docs/policy_extractor.py` | LLM-based policy extraction |
| `src/agents/api_document_agent.py` | Agent for document processing |
| `src/api/routes/api_documents.py` | REST API endpoints |
| `tests/test_api_document_processing.py` | Test suite |
