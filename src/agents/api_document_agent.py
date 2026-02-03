"""API Document Agent - Processes and stores external API documentation.

This agent is responsible for:
1. Ingesting API documents (OpenAPI, Markdown, text, etc.)
2. Parsing and extracting structured information
3. Extracting policies (rate limits, auth, error handling)
4. Storing endpoints and policies in long-term memory
5. Providing context for development work
"""
from __future__ import annotations


import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import AgentContext, AgentResult, AgentTask, BaseAgent
from ..api_docs.parser import APIDocumentParser
from ..api_docs.policy_extractor import PolicyExtractor
from ..api_docs.schema import (
    APIMemoryPatternType,
    DocumentFormat,
    ProcessedAPIDocument,
)
from ..memory.chroma_store import ChromaDBStore
from ..config import settings


class APIDocumentAgent(BaseAgent):
    """Agent specialized in processing and storing external API documentation.

    This agent processes API documentation from various formats (OpenAPI, Markdown,
    plain text, etc.) and stores the extracted information as long-term memory
    patterns for use in development work.

    Memory Storage Strategy:
    - API_OVERVIEW: High-level summary of the entire API
    - API_ENDPOINT: Individual endpoint documentation
    - API_POLICY: Rate limits, authentication, error handling
    - API_SCHEMA: Data models and schemas
    - API_EXAMPLE: Code examples and snippets
    """

    def __init__(self, context: AgentContext):
        """Initialize the API Document Agent.

        Args:
            context: Agent context with shared resources
        """
        # Initialize ChromaDB store for API documents
        self.memory_store = ChromaDBStore(
            collection_name="api_documents",
            persist_directory=settings.chroma_persist_directory,
            auto_embed=True,
        )

        # Initialize parser and policy extractor
        self.parser = APIDocumentParser()
        self.policy_extractor = PolicyExtractor(
            anthropic_client=context.anthropic_client if hasattr(context, 'anthropic_client') else None,
        )

        super().__init__(context)

    def get_agent_id(self) -> str:
        return "api_document_agent"

    def define_capabilities(self) -> Dict[str, Any]:
        return {
            "can_process_api_docs": True,
            "can_extract_policies": True,
            "can_query_endpoints": True,
            "can_suggest_integrations": True,
            "supported_formats": [
                "openapi_3",
                "openapi_2",
                "markdown",
                "text",
                "html",
            ],
            "memory_backend": "chromadb_vector",
        }

    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute API document processing operation.

        Supported actions:
        - process_document: Parse and store an API document
        - query_endpoints: Search for relevant endpoints
        - get_policies: Retrieve policies for an API
        - suggest_integration: Get suggestions for integrating with an API
        - list_apis: List all stored API documents
        """
        try:
            await self.log_event("info", f"Starting API document operation: {task.task_type}")

            action = str(task.input_data.get("action", "process_document")).lower()
            output: Dict[str, Any] = {}
            artifacts: List[str] = []

            if action in {"process", "process_document", "ingest"}:
                output, artifacts = await self._process_document(task.input_data)

            elif action in {"query", "query_endpoints", "search_endpoints"}:
                output = await self._query_endpoints(task.input_data)

            elif action in {"policies", "get_policies"}:
                output = await self._get_policies(task.input_data)

            elif action in {"suggest", "suggest_integration"}:
                output = await self._suggest_integration(task.input_data)

            elif action in {"list", "list_apis"}:
                output = await self._list_apis(task.input_data)

            elif action in {"get_context", "development_context"}:
                output = await self._get_development_context(task.input_data)

            elif action in {"health", "status"}:
                output = await self.memory_store.health()

            else:
                raise ValueError(f"Unknown action: {action}")

            result = AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output=output,
                artifacts=artifacts,
                metadata={"action": action},
            )

            await self.notify_completion(result)
            return result

        except Exception as exc:
            await self.log_event("error", f"API document operation failed: {exc}")
            result = AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=False,
                output={"error": str(exc)},
                artifacts=[],
                error=str(exc),
            )
            await self.notify_completion(result)
            return result

    async def _process_document(
        self, input_data: Dict[str, Any]
    ) -> tuple[Dict[str, Any], List[str]]:
        """Process and store an API document.

        Args:
            input_data: Must contain:
                - content: Raw document content
                - name: API name
                - doc_id (optional): Document ID
                - format (optional): Document format hint
                - source_url (optional): Original URL
                - version (optional): API version
                - use_llm_extraction (optional): Use LLM for policy extraction

        Returns:
            Tuple of (output dict, list of artifact IDs)
        """
        content = input_data.get("content")
        if not content:
            raise ValueError("Document processing requires 'content' field")

        name = input_data.get("name", "Unnamed API")
        doc_id = input_data.get("doc_id") or f"api_{uuid.uuid4().hex[:12]}"
        format_hint = input_data.get("format")
        source_url = input_data.get("source_url")
        version = input_data.get("version")
        use_llm = input_data.get("use_llm_extraction", True)
        metadata = input_data.get("metadata", {})

        # Parse document format if provided
        doc_format = None
        if format_hint:
            try:
                doc_format = DocumentFormat(format_hint)
            except ValueError:
                pass

        # Parse the document
        await self.log_event("info", f"Parsing API document: {name}")
        processed_doc = self.parser.parse(
            doc_id=doc_id,
            name=name,
            content=content,
            format_hint=doc_format,
            source_url=source_url,
            version=version,
            metadata=metadata,
        )

        # Optionally enhance with LLM extraction
        if use_llm and settings.llm_mode != "mock":
            await self.log_event("info", "Enhancing document with LLM policy extraction")
            try:
                processed_doc = await self.policy_extractor.enhance_processed_document(
                    processed_doc, content
                )
            except Exception as e:
                await self.log_event("warning", f"LLM enhancement failed: {e}")

        # Store in memory
        artifacts = await self._store_document_in_memory(processed_doc, content)

        # Save main artifact
        main_artifact_id = await self.save_artifact(
            artifact_type="api_document",
            content=json.dumps(processed_doc.model_dump(), indent=2, default=str),
            metadata={
                "api_name": processed_doc.name,
                "api_version": processed_doc.version,
                "endpoint_count": len(processed_doc.endpoints),
                "format": processed_doc.format.value,
            },
        )
        artifacts.insert(0, main_artifact_id)

        await self.log_event(
            "info",
            f"Processed API document: {name} with {len(processed_doc.endpoints)} endpoints",
        )

        return {
            "action": "process_document",
            "doc_id": doc_id,
            "api_name": processed_doc.name,
            "api_version": processed_doc.version,
            "format": processed_doc.format.value,
            "endpoints_count": len(processed_doc.endpoints),
            "has_rate_limit": processed_doc.policies.rate_limit is not None,
            "has_authentication": processed_doc.policies.authentication is not None,
            "memory_patterns_created": len(artifacts),
            "base_url": processed_doc.base_url,
        }, artifacts

    async def _store_document_in_memory(
        self, doc: ProcessedAPIDocument, raw_content: str
    ) -> List[str]:
        """Store processed document as memory patterns.

        Creates multiple memory patterns:
        1. Overview pattern with API summary
        2. Individual endpoint patterns
        3. Policy patterns (rate limit, auth, error handling)
        """
        artifacts = []
        base_metadata = {
            "api_name": doc.name,
            "api_version": doc.version or "unspecified",
            "doc_id": doc.doc_id,
            "source_url": doc.source_url or "",
            "processed_at": datetime.utcnow().isoformat(),
        }

        # 1. Store API overview
        overview_id = f"{doc.doc_id}_overview"
        overview_text = doc.get_summary_text()

        await self.memory_store.upsert_document(
            doc_id=overview_id,
            text=overview_text,
            metadata={
                **base_metadata,
                "pattern_type": APIMemoryPatternType.API_OVERVIEW.value,
                "endpoint_count": str(len(doc.endpoints)),
                "success_score": "0.8",  # Default high score for API docs
            },
        )
        artifacts.append(overview_id)

        # 2. Store policy patterns
        if doc.policies.rate_limit:
            policy_id = f"{doc.doc_id}_rate_limit"
            policy_text = self._format_rate_limit_text(doc.policies.rate_limit, doc.name)
            await self.memory_store.upsert_document(
                doc_id=policy_id,
                text=policy_text,
                metadata={
                    **base_metadata,
                    "pattern_type": APIMemoryPatternType.API_POLICY.value,
                    "policy_type": "rate_limit",
                    "success_score": "0.9",
                },
            )
            artifacts.append(policy_id)

        if doc.policies.authentication:
            auth_id = f"{doc.doc_id}_authentication"
            auth_text = self._format_auth_text(doc.policies.authentication, doc.name)
            await self.memory_store.upsert_document(
                doc_id=auth_id,
                text=auth_text,
                metadata={
                    **base_metadata,
                    "pattern_type": APIMemoryPatternType.API_POLICY.value,
                    "policy_type": "authentication",
                    "auth_type": doc.policies.authentication.auth_type.value,
                    "success_score": "0.9",
                },
            )
            artifacts.append(auth_id)

        if doc.policies.error_handling:
            error_id = f"{doc.doc_id}_error_handling"
            error_text = self._format_error_handling_text(
                doc.policies.error_handling, doc.name
            )
            await self.memory_store.upsert_document(
                doc_id=error_id,
                text=error_text,
                metadata={
                    **base_metadata,
                    "pattern_type": APIMemoryPatternType.API_POLICY.value,
                    "policy_type": "error_handling",
                    "success_score": "0.9",
                },
            )
            artifacts.append(error_id)

        # 3. Store individual endpoints
        for i, endpoint in enumerate(doc.endpoints):
            endpoint_id = f"{doc.doc_id}_endpoint_{i}"
            endpoint_text = endpoint.get_memory_text()

            await self.memory_store.upsert_document(
                doc_id=endpoint_id,
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
            artifacts.append(endpoint_id)

        # 4. Store usage guidelines if present
        if doc.policies.usage_guidelines:
            guidelines_id = f"{doc.doc_id}_guidelines"
            await self.memory_store.upsert_document(
                doc_id=guidelines_id,
                text=f"Usage Guidelines for {doc.name}:\n\n{doc.policies.usage_guidelines}",
                metadata={
                    **base_metadata,
                    "pattern_type": APIMemoryPatternType.API_INTEGRATION.value,
                    "success_score": "0.85",
                },
            )
            artifacts.append(guidelines_id)

        return artifacts

    def _format_rate_limit_text(self, rate_limit, api_name: str) -> str:
        """Format rate limit policy as searchable text."""
        parts = [f"Rate Limit Policy for {api_name}:"]

        if rate_limit.requests_per_minute:
            parts.append(f"- Requests per minute: {rate_limit.requests_per_minute}")
        if rate_limit.requests_per_hour:
            parts.append(f"- Requests per hour: {rate_limit.requests_per_hour}")
        if rate_limit.requests_per_day:
            parts.append(f"- Requests per day: {rate_limit.requests_per_day}")
        if rate_limit.burst_limit:
            parts.append(f"- Burst limit: {rate_limit.burst_limit}")
        if rate_limit.concurrent_limit:
            parts.append(f"- Concurrent connections: {rate_limit.concurrent_limit}")
        if rate_limit.retry_after_header:
            parts.append("- API returns Retry-After header on rate limit")
        if rate_limit.notes:
            parts.append(f"- Notes: {rate_limit.notes}")

        return "\n".join(parts)

    def _format_auth_text(self, auth, api_name: str) -> str:
        """Format authentication policy as searchable text."""
        parts = [f"Authentication Policy for {api_name}:"]
        parts.append(f"- Type: {auth.auth_type.value}")

        if auth.header_name:
            parts.append(f"- Header: {auth.header_name}")
        if auth.header_prefix:
            parts.append(f"- Header prefix: {auth.header_prefix}")
        if auth.api_key_name:
            parts.append(f"- API key parameter: {auth.api_key_name}")
        if auth.api_key_location:
            parts.append(f"- API key location: {auth.api_key_location.value}")
        if auth.scopes:
            parts.append(f"- Available scopes: {', '.join(auth.scopes.keys())}")
        if auth.token_url:
            parts.append(f"- Token URL: {auth.token_url}")
        if auth.notes:
            parts.append(f"- Notes: {auth.notes}")

        return "\n".join(parts)

    def _format_error_handling_text(self, error_handling, api_name: str) -> str:
        """Format error handling policy as searchable text."""
        parts = [f"Error Handling Policy for {api_name}:"]

        if error_handling.retry_codes:
            parts.append(f"- Retry on HTTP codes: {error_handling.retry_codes}")
        if error_handling.non_retry_codes:
            parts.append(f"- Do not retry on: {error_handling.non_retry_codes}")
        parts.append(f"- Max retries: {error_handling.max_retries}")
        parts.append(f"- Backoff strategy: {error_handling.backoff_strategy}")
        if error_handling.idempotency_key_header:
            parts.append(f"- Idempotency header: {error_handling.idempotency_key_header}")
        if error_handling.error_codes:
            parts.append("- Error codes:")
            for code, meaning in error_handling.error_codes.items():
                parts.append(f"  - {code}: {meaning}")
        if error_handling.notes:
            parts.append(f"- Notes: {error_handling.notes}")

        return "\n".join(parts)

    async def _query_endpoints(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Query for relevant API endpoints.

        Args:
            input_data:
                - query: Search query (e.g., "user authentication")
                - api_name (optional): Filter by API name
                - method (optional): Filter by HTTP method
                - top_k (optional): Number of results

        Returns:
            Query results with matching endpoints
        """
        query = input_data.get("query")
        if not query:
            raise ValueError("Endpoint query requires 'query' field")

        top_k = int(input_data.get("top_k", 10))
        api_name = input_data.get("api_name")
        method = input_data.get("method")

        # Build filter conditions
        pattern_type = APIMemoryPatternType.API_ENDPOINT.value

        # Query the memory store
        results = await self.memory_store.query_similar(
            query=query,
            top_k=top_k,
            pattern_type=pattern_type,
        )

        # Filter by API name and method if specified
        filtered_results = []
        for result in results:
            metadata = result.get("metadata", {})

            if api_name and metadata.get("api_name") != api_name:
                continue
            if method and metadata.get("http_method") != method.upper():
                continue

            filtered_results.append(result)

        await self.log_event(
            "info", f"Found {len(filtered_results)} endpoints matching query: {query}"
        )

        return {
            "action": "query_endpoints",
            "query": query,
            "results": filtered_results,
            "count": len(filtered_results),
            "filters": {
                "api_name": api_name,
                "method": method,
            },
        }

    async def _get_policies(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get policies for a specific API.

        Args:
            input_data:
                - api_name: Name of the API
                - policy_type (optional): rate_limit, authentication, error_handling

        Returns:
            Policy information for the API
        """
        api_name = input_data.get("api_name")
        if not api_name:
            raise ValueError("Policy lookup requires 'api_name' field")

        policy_type = input_data.get("policy_type")

        # Query for policy patterns
        results = await self.memory_store.query_similar(
            query=f"Policy for {api_name}",
            top_k=10,
            pattern_type=APIMemoryPatternType.API_POLICY.value,
        )

        # Filter by API name and policy type
        policies = []
        for result in results:
            metadata = result.get("metadata", {})
            if metadata.get("api_name") == api_name:
                if policy_type and metadata.get("policy_type") != policy_type:
                    continue
                policies.append({
                    "policy_type": metadata.get("policy_type"),
                    "content": result.get("text"),
                    "metadata": metadata,
                })

        return {
            "action": "get_policies",
            "api_name": api_name,
            "policies": policies,
            "count": len(policies),
        }

    async def _suggest_integration(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest how to integrate with an API based on requirements.

        Args:
            input_data:
                - requirements: What the integration needs to do
                - api_name (optional): Specific API to integrate with
                - top_k (optional): Number of suggestions

        Returns:
            Integration suggestions with relevant endpoints and policies
        """
        requirements = input_data.get("requirements")
        if not requirements:
            raise ValueError("Integration suggestion requires 'requirements' field")

        api_name = input_data.get("api_name")
        top_k = int(input_data.get("top_k", 5))

        # Find relevant endpoints
        endpoint_results = await self.memory_store.query_similar(
            query=requirements,
            top_k=top_k,
            pattern_type=APIMemoryPatternType.API_ENDPOINT.value,
        )

        if api_name:
            endpoint_results = [
                r for r in endpoint_results
                if r.get("metadata", {}).get("api_name") == api_name
            ]

        # Get unique APIs from results
        api_names = set()
        for r in endpoint_results:
            api_names.add(r.get("metadata", {}).get("api_name"))

        # Get relevant policies for each API
        api_policies = {}
        for name in api_names:
            if name:
                policies_result = await self._get_policies({"api_name": name})
                api_policies[name] = policies_result.get("policies", [])

        # Build suggestion
        suggestions = []
        for endpoint in endpoint_results:
            metadata = endpoint.get("metadata", {})
            api = metadata.get("api_name")

            suggestion = {
                "endpoint": {
                    "method": metadata.get("http_method"),
                    "path": metadata.get("path"),
                    "description": endpoint.get("text"),
                    "relevance_score": endpoint.get("score", 0),
                },
                "api_name": api,
                "policies": api_policies.get(api, []),
            }
            suggestions.append(suggestion)

        await self.log_event(
            "info",
            f"Generated {len(suggestions)} integration suggestions for: {requirements[:50]}...",
        )

        return {
            "action": "suggest_integration",
            "requirements": requirements,
            "suggestions": suggestions,
            "apis_involved": list(api_names),
        }

    async def _list_apis(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """List all stored API documents.

        Args:
            input_data:
                - limit (optional): Maximum number to return

        Returns:
            List of stored API documents
        """
        limit = int(input_data.get("limit", 50))

        # Query for overview patterns (one per API)
        results = await self.memory_store.query_similar(
            query="API documentation overview",
            top_k=limit,
            pattern_type=APIMemoryPatternType.API_OVERVIEW.value,
        )

        apis = []
        for result in results:
            metadata = result.get("metadata", {})
            apis.append({
                "api_name": metadata.get("api_name"),
                "api_version": metadata.get("api_version"),
                "doc_id": metadata.get("doc_id"),
                "endpoint_count": metadata.get("endpoint_count"),
                "source_url": metadata.get("source_url"),
                "processed_at": metadata.get("processed_at"),
            })

        return {
            "action": "list_apis",
            "apis": apis,
            "count": len(apis),
        }

    async def _get_development_context(
        self, input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get comprehensive context for development work.

        This method retrieves all relevant API documentation context
        for a specific development task, including:
        - Relevant endpoints
        - Authentication requirements
        - Rate limiting policies
        - Error handling guidelines

        Args:
            input_data:
                - task_description: What the developer needs to build
                - api_names (optional): List of APIs to focus on
                - top_k (optional): Number of results per category

        Returns:
            Comprehensive development context
        """
        task_description = input_data.get("task_description")
        if not task_description:
            raise ValueError("Development context requires 'task_description' field")

        api_names = input_data.get("api_names", [])
        top_k = int(input_data.get("top_k", 5))

        # Get relevant endpoints
        endpoints = await self._query_endpoints({
            "query": task_description,
            "top_k": top_k,
        })

        # Identify relevant APIs
        relevant_apis = set(api_names)
        for ep in endpoints.get("results", []):
            api = ep.get("metadata", {}).get("api_name")
            if api:
                relevant_apis.add(api)

        # Get policies for relevant APIs
        all_policies = {}
        for api in relevant_apis:
            policies = await self._get_policies({"api_name": api})
            all_policies[api] = policies.get("policies", [])

        # Format as development context
        context = {
            "action": "get_development_context",
            "task_description": task_description,
            "relevant_apis": list(relevant_apis),
            "endpoints": endpoints.get("results", []),
            "policies_by_api": all_policies,
            "summary": self._format_context_summary(
                endpoints.get("results", []),
                all_policies,
            ),
        }

        await self.log_event(
            "info",
            f"Generated development context for: {task_description[:50]}...",
        )

        return context

    def _format_context_summary(
        self,
        endpoints: List[Dict],
        policies: Dict[str, List[Dict]],
    ) -> str:
        """Format a human-readable context summary."""
        parts = ["## API Integration Context\n"]

        # Endpoints summary
        if endpoints:
            parts.append("### Relevant Endpoints")
            for ep in endpoints[:5]:  # Top 5
                metadata = ep.get("metadata", {})
                parts.append(
                    f"- {metadata.get('http_method', '?')} {metadata.get('path', '?')} "
                    f"({metadata.get('api_name', 'Unknown API')})"
                )
            parts.append("")

        # Policies summary
        for api_name, api_policies in policies.items():
            if api_policies:
                parts.append(f"### {api_name} Policies")
                for policy in api_policies:
                    policy_type = policy.get("policy_type", "unknown")
                    parts.append(f"- {policy_type.replace('_', ' ').title()}")
                parts.append("")

        return "\n".join(parts)
