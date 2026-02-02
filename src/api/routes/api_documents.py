"""API endpoints for external API document management.

These endpoints allow uploading, processing, and querying external API
documentation that gets stored as long-term memory for development work.
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel, Field, HttpUrl
from typing import Any, Dict, List, Optional
import uuid

from ...api_docs.parser import APIDocumentParser
from ...api_docs.policy_extractor import PolicyExtractor
from ...api_docs.schema import (
    APIMemoryPatternType,
    DocumentFormat,
    ProcessedAPIDocument,
)
from ...memory.chroma_store import ChromaDBStore
from ...config import settings


router = APIRouter(prefix="/api/api-documents", tags=["api-documents"])


# ============================================================================
# Request/Response Models
# ============================================================================


class ProcessDocumentRequest(BaseModel):
    """Request to process an API document."""

    content: str = Field(..., description="Raw API document content")
    name: str = Field(..., description="API name")
    doc_id: Optional[str] = Field(None, description="Optional document ID")
    format: Optional[str] = Field(
        None, description="Document format (openapi_3, openapi_2, markdown, text)"
    )
    source_url: Optional[str] = Field(None, description="Original document URL")
    version: Optional[str] = Field(None, description="API version")
    use_llm_extraction: bool = Field(
        True, description="Use LLM for enhanced policy extraction"
    )
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ProcessDocumentResponse(BaseModel):
    """Response after processing an API document."""

    status: str
    doc_id: str
    api_name: str
    api_version: Optional[str]
    format: str
    endpoints_count: int
    has_rate_limit: bool
    has_authentication: bool
    memory_patterns_created: int
    base_url: Optional[str]


class QueryEndpointsRequest(BaseModel):
    """Request to query API endpoints."""

    query: str = Field(..., description="Search query (e.g., 'user authentication')")
    api_name: Optional[str] = Field(None, description="Filter by API name")
    method: Optional[str] = Field(None, description="Filter by HTTP method")
    top_k: int = Field(10, gt=0, le=50, description="Number of results")


class GetPoliciesRequest(BaseModel):
    """Request to get API policies."""

    api_name: str = Field(..., description="API name")
    policy_type: Optional[str] = Field(
        None, description="Policy type (rate_limit, authentication, error_handling)"
    )


class SuggestIntegrationRequest(BaseModel):
    """Request for integration suggestions."""

    requirements: str = Field(..., description="What the integration needs to do")
    api_name: Optional[str] = Field(None, description="Specific API to integrate with")
    top_k: int = Field(5, gt=0, le=20, description="Number of suggestions")


class DevelopmentContextRequest(BaseModel):
    """Request for development context."""

    task_description: str = Field(..., description="Development task description")
    api_names: List[str] = Field(default_factory=list, description="APIs to focus on")
    top_k: int = Field(5, gt=0, le=20, description="Results per category")


# ============================================================================
# Dependencies
# ============================================================================


def get_api_docs_store() -> ChromaDBStore:
    """Get ChromaDB store for API documents."""
    return ChromaDBStore(
        collection_name="api_documents",
        persist_directory=settings.chroma_persist_directory,
        auto_embed=True,
    )


def get_parser() -> APIDocumentParser:
    """Get API document parser."""
    return APIDocumentParser()


def get_policy_extractor() -> PolicyExtractor:
    """Get policy extractor."""
    return PolicyExtractor()


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/process", response_model=ProcessDocumentResponse)
async def process_document(
    request: ProcessDocumentRequest,
    store: ChromaDBStore = Depends(get_api_docs_store),
    parser: APIDocumentParser = Depends(get_parser),
    extractor: PolicyExtractor = Depends(get_policy_extractor),
):
    """
    Process and store an API document.

    This endpoint parses the API document, extracts endpoints and policies,
    and stores everything in long-term memory for development use.

    Supported formats:
    - OpenAPI 3.x (JSON/YAML)
    - OpenAPI 2.x / Swagger (JSON/YAML)
    - Markdown documentation
    - Plain text documentation
    """
    try:
        doc_id = request.doc_id or f"api_{uuid.uuid4().hex[:12]}"

        # Parse format if provided
        doc_format = None
        if request.format:
            try:
                doc_format = DocumentFormat(request.format)
            except ValueError:
                pass

        # Parse the document
        processed_doc = parser.parse(
            doc_id=doc_id,
            name=request.name,
            content=request.content,
            format_hint=doc_format,
            source_url=request.source_url,
            version=request.version,
            metadata=request.metadata or {},
        )

        # Optionally enhance with LLM
        if request.use_llm_extraction and settings.llm_mode != "mock":
            try:
                processed_doc = await extractor.enhance_processed_document(
                    processed_doc, request.content
                )
            except Exception:
                pass  # Continue without LLM enhancement

        # Store in memory
        patterns_created = await _store_document_in_memory(
            store, processed_doc, request.content
        )

        return ProcessDocumentResponse(
            status="success",
            doc_id=doc_id,
            api_name=processed_doc.name,
            api_version=processed_doc.version,
            format=processed_doc.format.value,
            endpoints_count=len(processed_doc.endpoints),
            has_rate_limit=processed_doc.policies.rate_limit is not None,
            has_authentication=processed_doc.policies.authentication is not None,
            memory_patterns_created=patterns_created,
            base_url=processed_doc.base_url,
        )

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    name: str = Form(...),
    version: Optional[str] = Form(None),
    source_url: Optional[str] = Form(None),
    use_llm_extraction: bool = Form(True),
    store: ChromaDBStore = Depends(get_api_docs_store),
    parser: APIDocumentParser = Depends(get_parser),
    extractor: PolicyExtractor = Depends(get_policy_extractor),
):
    """
    Upload an API document file for processing.

    Accepts JSON, YAML, Markdown, or text files containing API documentation.
    """
    try:
        # Read file content
        content = await file.read()
        content_str = content.decode("utf-8")

        doc_id = f"api_{uuid.uuid4().hex[:12]}"

        # Parse the document
        processed_doc = parser.parse(
            doc_id=doc_id,
            name=name,
            content=content_str,
            source_url=source_url,
            version=version,
        )

        # Optionally enhance with LLM
        if use_llm_extraction and settings.llm_mode != "mock":
            try:
                processed_doc = await extractor.enhance_processed_document(
                    processed_doc, content_str
                )
            except Exception:
                pass

        # Store in memory
        patterns_created = await _store_document_in_memory(
            store, processed_doc, content_str
        )

        return {
            "status": "success",
            "doc_id": doc_id,
            "api_name": processed_doc.name,
            "api_version": processed_doc.version,
            "format": processed_doc.format.value,
            "endpoints_count": len(processed_doc.endpoints),
            "has_rate_limit": processed_doc.policies.rate_limit is not None,
            "has_authentication": processed_doc.policies.authentication is not None,
            "memory_patterns_created": patterns_created,
            "filename": file.filename,
        }

    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400, detail="File must be a valid text file (UTF-8 encoded)"
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/query/endpoints")
async def query_endpoints(
    request: QueryEndpointsRequest,
    store: ChromaDBStore = Depends(get_api_docs_store),
):
    """
    Search for relevant API endpoints.

    Returns endpoints matching the query, optionally filtered by API name and HTTP method.
    """
    try:
        # Query the memory store
        results = await store.query_similar(
            query=request.query,
            top_k=request.top_k * 2,  # Get extra for filtering
            pattern_type=APIMemoryPatternType.API_ENDPOINT.value,
        )

        # Filter by API name and method if specified
        filtered_results = []
        for result in results:
            metadata = result.get("metadata", {})

            if request.api_name and metadata.get("api_name") != request.api_name:
                continue
            if request.method and metadata.get("http_method") != request.method.upper():
                continue

            filtered_results.append(result)

            if len(filtered_results) >= request.top_k:
                break

        return {
            "status": "success",
            "query": request.query,
            "results": filtered_results,
            "count": len(filtered_results),
            "filters": {
                "api_name": request.api_name,
                "method": request.method,
            },
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/query/policies")
async def get_policies(
    request: GetPoliciesRequest,
    store: ChromaDBStore = Depends(get_api_docs_store),
):
    """
    Get policies for a specific API.

    Returns rate limiting, authentication, and error handling policies.
    """
    try:
        # Query for policy patterns
        results = await store.query_similar(
            query=f"Policy for {request.api_name}",
            top_k=20,
            pattern_type=APIMemoryPatternType.API_POLICY.value,
        )

        # Filter by API name and policy type
        policies = []
        for result in results:
            metadata = result.get("metadata", {})
            if metadata.get("api_name") == request.api_name:
                if request.policy_type and metadata.get("policy_type") != request.policy_type:
                    continue
                policies.append({
                    "policy_type": metadata.get("policy_type"),
                    "content": result.get("text"),
                    "metadata": metadata,
                })

        return {
            "status": "success",
            "api_name": request.api_name,
            "policies": policies,
            "count": len(policies),
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/suggest/integration")
async def suggest_integration(
    request: SuggestIntegrationRequest,
    store: ChromaDBStore = Depends(get_api_docs_store),
):
    """
    Suggest how to integrate with an API based on requirements.

    Returns relevant endpoints and policies for the integration task.
    """
    try:
        # Find relevant endpoints
        endpoint_results = await store.query_similar(
            query=request.requirements,
            top_k=request.top_k * 2,
            pattern_type=APIMemoryPatternType.API_ENDPOINT.value,
        )

        if request.api_name:
            endpoint_results = [
                r for r in endpoint_results
                if r.get("metadata", {}).get("api_name") == request.api_name
            ]

        # Get unique APIs from results
        api_names = set()
        for r in endpoint_results:
            api_names.add(r.get("metadata", {}).get("api_name"))

        # Get relevant policies for each API
        api_policies = {}
        for name in api_names:
            if name:
                policy_results = await store.query_similar(
                    query=f"Policy for {name}",
                    top_k=10,
                    pattern_type=APIMemoryPatternType.API_POLICY.value,
                )
                api_policies[name] = [
                    {
                        "policy_type": r.get("metadata", {}).get("policy_type"),
                        "content": r.get("text"),
                    }
                    for r in policy_results
                    if r.get("metadata", {}).get("api_name") == name
                ]

        # Build suggestions
        suggestions = []
        for endpoint in endpoint_results[: request.top_k]:
            metadata = endpoint.get("metadata", {})
            api = metadata.get("api_name")

            suggestions.append({
                "endpoint": {
                    "method": metadata.get("http_method"),
                    "path": metadata.get("path"),
                    "description": endpoint.get("text"),
                    "relevance_score": endpoint.get("score", 0),
                },
                "api_name": api,
                "policies": api_policies.get(api, []),
            })

        return {
            "status": "success",
            "requirements": request.requirements,
            "suggestions": suggestions,
            "apis_involved": list(api_names),
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/context/development")
async def get_development_context(
    request: DevelopmentContextRequest,
    store: ChromaDBStore = Depends(get_api_docs_store),
):
    """
    Get comprehensive context for development work.

    Returns all relevant API documentation context for a specific
    development task, including endpoints, authentication, rate limits,
    and error handling guidelines.
    """
    try:
        # Get relevant endpoints
        endpoint_results = await store.query_similar(
            query=request.task_description,
            top_k=request.top_k,
            pattern_type=APIMemoryPatternType.API_ENDPOINT.value,
        )

        # Identify relevant APIs
        relevant_apis = set(request.api_names)
        for ep in endpoint_results:
            api = ep.get("metadata", {}).get("api_name")
            if api:
                relevant_apis.add(api)

        # Get policies for relevant APIs
        all_policies = {}
        for api in relevant_apis:
            policy_results = await store.query_similar(
                query=f"Policy for {api}",
                top_k=10,
                pattern_type=APIMemoryPatternType.API_POLICY.value,
            )
            all_policies[api] = [
                {
                    "policy_type": r.get("metadata", {}).get("policy_type"),
                    "content": r.get("text"),
                }
                for r in policy_results
                if r.get("metadata", {}).get("api_name") == api
            ]

        # Format summary
        summary_parts = ["## API Integration Context\n"]

        if endpoint_results:
            summary_parts.append("### Relevant Endpoints")
            for ep in endpoint_results[:5]:
                metadata = ep.get("metadata", {})
                summary_parts.append(
                    f"- {metadata.get('http_method', '?')} {metadata.get('path', '?')} "
                    f"({metadata.get('api_name', 'Unknown API')})"
                )
            summary_parts.append("")

        for api_name, policies in all_policies.items():
            if policies:
                summary_parts.append(f"### {api_name} Policies")
                for policy in policies:
                    policy_type = policy.get("policy_type", "unknown")
                    summary_parts.append(f"- {policy_type.replace('_', ' ').title()}")
                summary_parts.append("")

        return {
            "status": "success",
            "task_description": request.task_description,
            "relevant_apis": list(relevant_apis),
            "endpoints": endpoint_results,
            "policies_by_api": all_policies,
            "summary": "\n".join(summary_parts),
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/list")
async def list_apis(
    limit: int = 50,
    store: ChromaDBStore = Depends(get_api_docs_store),
):
    """
    List all stored API documents.

    Returns a summary of each API including name, version, and endpoint count.
    """
    try:
        # Query for overview patterns (one per API)
        results = await store.query_similar(
            query="API documentation overview",
            top_k=limit,
            pattern_type=APIMemoryPatternType.API_OVERVIEW.value,
        )

        apis = []
        seen_names = set()
        for result in results:
            metadata = result.get("metadata", {})
            api_name = metadata.get("api_name")

            # Deduplicate by name
            if api_name in seen_names:
                continue
            seen_names.add(api_name)

            apis.append({
                "api_name": api_name,
                "api_version": metadata.get("api_version"),
                "doc_id": metadata.get("doc_id"),
                "endpoint_count": metadata.get("endpoint_count"),
                "source_url": metadata.get("source_url"),
                "processed_at": metadata.get("processed_at"),
            })

        return {
            "status": "success",
            "apis": apis,
            "count": len(apis),
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{doc_id}")
async def get_api_document(
    doc_id: str,
    store: ChromaDBStore = Depends(get_api_docs_store),
):
    """
    Get details of a specific API document.

    Returns the overview and all related patterns for the API.
    """
    try:
        # Get overview
        overview = await store.get_document(f"{doc_id}_overview")
        if not overview:
            raise HTTPException(status_code=404, detail=f"API document {doc_id} not found")

        metadata = overview.get("metadata", {})
        api_name = metadata.get("api_name")

        # Get endpoints
        endpoints = await store.query_similar(
            query=f"Endpoints for {api_name}",
            top_k=100,
            pattern_type=APIMemoryPatternType.API_ENDPOINT.value,
        )
        endpoints = [
            e for e in endpoints
            if e.get("metadata", {}).get("doc_id") == doc_id
        ]

        # Get policies
        policies = await store.query_similar(
            query=f"Policy for {api_name}",
            top_k=10,
            pattern_type=APIMemoryPatternType.API_POLICY.value,
        )
        policies = [
            p for p in policies
            if p.get("metadata", {}).get("doc_id") == doc_id
        ]

        return {
            "status": "success",
            "doc_id": doc_id,
            "api_name": api_name,
            "overview": overview.get("text"),
            "metadata": metadata,
            "endpoints": endpoints,
            "policies": policies,
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/{doc_id}")
async def delete_api_document(
    doc_id: str,
    store: ChromaDBStore = Depends(get_api_docs_store),
):
    """
    Delete an API document and all its patterns.

    Removes the overview, all endpoints, and all policies for the API.
    """
    try:
        deleted_count = 0

        # Delete overview
        if await store.delete_document(f"{doc_id}_overview"):
            deleted_count += 1

        # Delete policies
        for policy_type in ["rate_limit", "authentication", "error_handling"]:
            if await store.delete_document(f"{doc_id}_{policy_type}"):
                deleted_count += 1

        # Delete guidelines
        if await store.delete_document(f"{doc_id}_guidelines"):
            deleted_count += 1

        # Delete endpoints (try up to 100)
        for i in range(100):
            if not await store.delete_document(f"{doc_id}_endpoint_{i}"):
                break
            deleted_count += 1

        if deleted_count == 0:
            raise HTTPException(status_code=404, detail=f"API document {doc_id} not found")

        return {
            "status": "success",
            "doc_id": doc_id,
            "patterns_deleted": deleted_count,
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/health")
async def api_documents_health(store: ChromaDBStore = Depends(get_api_docs_store)):
    """
    Get health status of API documents storage.
    """
    try:
        health = await store.health()
        return {
            "status": "success",
            **health,
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# Helper Functions
# ============================================================================


async def _store_document_in_memory(
    store: ChromaDBStore,
    doc: ProcessedAPIDocument,
    raw_content: str,
) -> int:
    """Store processed document as memory patterns."""
    from datetime import datetime

    patterns_created = 0
    base_metadata = {
        "api_name": doc.name,
        "api_version": doc.version or "unspecified",
        "doc_id": doc.doc_id,
        "source_url": doc.source_url or "",
        "processed_at": datetime.utcnow().isoformat(),
    }

    # 1. Store API overview
    overview_text = doc.get_summary_text()
    await store.upsert_document(
        doc_id=f"{doc.doc_id}_overview",
        text=overview_text,
        metadata={
            **base_metadata,
            "pattern_type": APIMemoryPatternType.API_OVERVIEW.value,
            "endpoint_count": str(len(doc.endpoints)),
            "success_score": "0.8",
        },
    )
    patterns_created += 1

    # 2. Store policy patterns
    if doc.policies.rate_limit:
        rl = doc.policies.rate_limit
        policy_text = f"Rate Limit Policy for {doc.name}:\n"
        if rl.requests_per_minute:
            policy_text += f"- Requests per minute: {rl.requests_per_minute}\n"
        if rl.requests_per_hour:
            policy_text += f"- Requests per hour: {rl.requests_per_hour}\n"
        if rl.requests_per_day:
            policy_text += f"- Requests per day: {rl.requests_per_day}\n"

        await store.upsert_document(
            doc_id=f"{doc.doc_id}_rate_limit",
            text=policy_text,
            metadata={
                **base_metadata,
                "pattern_type": APIMemoryPatternType.API_POLICY.value,
                "policy_type": "rate_limit",
                "success_score": "0.9",
            },
        )
        patterns_created += 1

    if doc.policies.authentication:
        auth = doc.policies.authentication
        auth_text = f"Authentication Policy for {doc.name}:\n"
        auth_text += f"- Type: {auth.auth_type.value}\n"
        if auth.header_name:
            auth_text += f"- Header: {auth.header_name}\n"
        if auth.api_key_name:
            auth_text += f"- API key: {auth.api_key_name}\n"

        await store.upsert_document(
            doc_id=f"{doc.doc_id}_authentication",
            text=auth_text,
            metadata={
                **base_metadata,
                "pattern_type": APIMemoryPatternType.API_POLICY.value,
                "policy_type": "authentication",
                "auth_type": auth.auth_type.value,
                "success_score": "0.9",
            },
        )
        patterns_created += 1

    if doc.policies.error_handling:
        eh = doc.policies.error_handling
        error_text = f"Error Handling Policy for {doc.name}:\n"
        error_text += f"- Retry on: {eh.retry_codes}\n"
        error_text += f"- Max retries: {eh.max_retries}\n"
        error_text += f"- Backoff: {eh.backoff_strategy}\n"

        await store.upsert_document(
            doc_id=f"{doc.doc_id}_error_handling",
            text=error_text,
            metadata={
                **base_metadata,
                "pattern_type": APIMemoryPatternType.API_POLICY.value,
                "policy_type": "error_handling",
                "success_score": "0.9",
            },
        )
        patterns_created += 1

    # 3. Store individual endpoints
    for i, endpoint in enumerate(doc.endpoints):
        endpoint_text = endpoint.get_memory_text()

        await store.upsert_document(
            doc_id=f"{doc.doc_id}_endpoint_{i}",
            text=endpoint_text,
            metadata={
                **base_metadata,
                "pattern_type": APIMemoryPatternType.API_ENDPOINT.value,
                "http_method": endpoint.method.value,
                "path": endpoint.path,
                "tags": ",".join(endpoint.tags) if endpoint.tags else "",
                "deprecated": str(endpoint.deprecated),
                "success_score": "0.7",
            },
        )
        patterns_created += 1

    # 4. Store usage guidelines if present
    if doc.policies.usage_guidelines:
        await store.upsert_document(
            doc_id=f"{doc.doc_id}_guidelines",
            text=f"Usage Guidelines for {doc.name}:\n\n{doc.policies.usage_guidelines}",
            metadata={
                **base_metadata,
                "pattern_type": APIMemoryPatternType.API_INTEGRATION.value,
                "success_score": "0.85",
            },
        )
        patterns_created += 1

    return patterns_created
