"""Policy extractor using LLM for nuanced API policy extraction.

Uses Claude to extract detailed policies, usage guidelines, and best practices
from API documentation that may be difficult to parse with regex alone.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from anthropic import AsyncAnthropic

from ..config import settings
from .schema import (
    APIPolicy,
    AuthenticationPolicy,
    AuthenticationType,
    ErrorHandlingPolicy,
    ParameterLocation,
    ProcessedAPIDocument,
    RateLimitPolicy,
)


POLICY_EXTRACTION_SYSTEM_PROMPT = """You are an expert at analyzing API documentation and extracting structured policy information.

Your task is to analyze API documentation and extract:
1. Rate limiting policies (requests per minute/hour/day, burst limits)
2. Authentication requirements (API keys, OAuth, Bearer tokens)
3. Error handling guidelines (retry strategies, error codes)
4. Usage guidelines and best practices
5. Deprecation policies
6. Versioning strategies

Return your analysis as a JSON object. Be precise and only include information that is explicitly stated or clearly implied in the documentation.

If a field cannot be determined from the documentation, use null for that field."""

POLICY_EXTRACTION_USER_PROMPT = """Analyze the following API documentation and extract policy information.

API Name: {api_name}
API Version: {api_version}

Documentation Content:
---
{content}
---

Extract and return a JSON object with the following structure:
{{
    "rate_limit": {{
        "requests_per_minute": <int or null>,
        "requests_per_hour": <int or null>,
        "requests_per_day": <int or null>,
        "burst_limit": <int or null>,
        "concurrent_limit": <int or null>,
        "notes": "<any additional rate limit info>"
    }},
    "authentication": {{
        "auth_type": "<api_key|bearer_token|oauth2|basic|none>",
        "header_name": "<header name if applicable>",
        "header_prefix": "<prefix like 'Bearer' if applicable>",
        "api_key_name": "<parameter name if API key>",
        "api_key_location": "<header|query|body>",
        "scopes": {{"scope_name": "description"}},
        "notes": "<any additional auth info>"
    }},
    "error_handling": {{
        "error_format": {{"field": "description"}},
        "error_codes": {{"code": "meaning"}},
        "retry_codes": [<list of HTTP codes to retry>],
        "max_retries": <recommended retries>,
        "backoff_strategy": "<exponential|linear|fixed>",
        "idempotency_key_header": "<header name if applicable>",
        "notes": "<any additional error handling info>"
    }},
    "usage_guidelines": "<general usage guidelines and best practices>",
    "deprecation_policy": "<how the API handles deprecation>",
    "versioning_strategy": "<url_path|header|query_param|none>",
    "terms_summary": "<brief summary of terms of service if mentioned>"
}}

Return ONLY the JSON object, no additional text."""


ENDPOINT_EXTRACTION_SYSTEM_PROMPT = """You are an expert at analyzing API documentation and extracting endpoint information.

Your task is to identify all API endpoints mentioned in the documentation and extract their details including:
- HTTP method and path
- Description and purpose
- Parameters (path, query, header, body)
- Request body structure
- Response structure and status codes
- Rate limits specific to the endpoint

Return your analysis as a JSON array of endpoint objects."""

ENDPOINT_EXTRACTION_USER_PROMPT = """Analyze the following API documentation and extract all API endpoints.

API Name: {api_name}
Base URL: {base_url}

Documentation Content:
---
{content}
---

Extract and return a JSON array of endpoints with this structure:
[
    {{
        "path": "/endpoint/path",
        "method": "GET|POST|PUT|PATCH|DELETE",
        "summary": "Brief description",
        "description": "Detailed description",
        "tags": ["category"],
        "parameters": [
            {{
                "name": "param_name",
                "location": "path|query|header|body",
                "required": true|false,
                "type": "string|integer|boolean|array|object",
                "description": "What this param does",
                "default": null,
                "enum_values": null
            }}
        ],
        "request_body": {{
            "content_type": "application/json",
            "required": true|false,
            "schema": {{}}
        }},
        "responses": [
            {{
                "status_code": 200,
                "description": "Success response",
                "content_type": "application/json",
                "schema": {{}}
            }}
        ],
        "rate_limit": "specific rate limit if mentioned"
    }}
]

Return ONLY the JSON array, no additional text. If no endpoints are found, return an empty array []."""


class PolicyExtractor:
    """Extract policies from API documentation using LLM analysis.

    This class uses Claude to analyze API documentation and extract
    structured policy information that may be difficult to parse
    with traditional regex-based approaches.
    """

    def __init__(
        self,
        anthropic_client: Optional[AsyncAnthropic] = None,
        model: Optional[str] = None,
    ):
        """Initialize the policy extractor.

        Args:
            anthropic_client: Anthropic client (created if not provided)
            model: Model to use (defaults to config)
        """
        self.client = anthropic_client
        self.model = model or settings.anthropic_model

    async def _get_client(self) -> AsyncAnthropic:
        """Get or create the Anthropic client."""
        if self.client is None:
            self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        return self.client

    async def extract_policies(
        self,
        content: str,
        api_name: str,
        api_version: Optional[str] = None,
        max_content_length: int = 50000,
    ) -> APIPolicy:
        """Extract policies from API documentation using LLM.

        Args:
            content: Raw API documentation content
            api_name: Name of the API
            api_version: Version of the API
            max_content_length: Maximum content length to send to LLM

        Returns:
            Extracted APIPolicy object
        """
        # Truncate content if too long
        if len(content) > max_content_length:
            content = content[:max_content_length] + "\n\n[Content truncated...]"

        client = await self._get_client()

        prompt = POLICY_EXTRACTION_USER_PROMPT.format(
            api_name=api_name,
            api_version=api_version or "unspecified",
            content=content,
        )

        try:
            response = await client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=POLICY_EXTRACTION_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract text from response
            response_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    response_text += block.text

            # Parse JSON response
            policy_data = self._parse_json_response(response_text)

            return self._build_policy_from_data(policy_data)

        except Exception as e:
            # Return empty policy on error
            return APIPolicy(
                usage_guidelines=f"Policy extraction failed: {str(e)}"
            )

    async def extract_endpoints(
        self,
        content: str,
        api_name: str,
        base_url: Optional[str] = None,
        max_content_length: int = 50000,
    ) -> List[Dict[str, Any]]:
        """Extract endpoints from API documentation using LLM.

        Args:
            content: Raw API documentation content
            api_name: Name of the API
            base_url: Base URL of the API
            max_content_length: Maximum content length to send to LLM

        Returns:
            List of endpoint dictionaries
        """
        # Truncate content if too long
        if len(content) > max_content_length:
            content = content[:max_content_length] + "\n\n[Content truncated...]"

        client = await self._get_client()

        prompt = ENDPOINT_EXTRACTION_USER_PROMPT.format(
            api_name=api_name,
            base_url=base_url or "Not specified",
            content=content,
        )

        try:
            response = await client.messages.create(
                model=self.model,
                max_tokens=8192,
                system=ENDPOINT_EXTRACTION_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract text from response
            response_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    response_text += block.text

            # Parse JSON response
            endpoints = self._parse_json_response(response_text)

            if isinstance(endpoints, list):
                return endpoints
            return []

        except Exception as e:
            # Return empty list on error
            return []

    async def enhance_processed_document(
        self,
        doc: ProcessedAPIDocument,
        raw_content: str,
    ) -> ProcessedAPIDocument:
        """Enhance a processed document with LLM-extracted policies.

        This method takes a document that was parsed with regex-based
        methods and enhances it with LLM-extracted policies for
        more accurate and complete information.

        Args:
            doc: ProcessedAPIDocument from parser
            raw_content: Original raw content

        Returns:
            Enhanced ProcessedAPIDocument
        """
        # Extract policies using LLM
        llm_policies = await self.extract_policies(
            content=raw_content,
            api_name=doc.name,
            api_version=doc.version,
        )

        # Merge policies (LLM takes precedence for missing fields)
        merged_policies = self._merge_policies(doc.policies, llm_policies)

        # If we have few endpoints, try to extract more with LLM
        if len(doc.endpoints) < 3:
            llm_endpoints = await self.extract_endpoints(
                content=raw_content,
                api_name=doc.name,
                base_url=doc.base_url,
            )

            # Add any new endpoints not already present
            existing_paths = {(e.path, e.method.value) for e in doc.endpoints}
            for ep_data in llm_endpoints:
                key = (ep_data.get("path"), ep_data.get("method"))
                if key not in existing_paths:
                    # Convert to APIEndpoint (simplified)
                    from .schema import APIEndpoint, HTTPMethod, APIParameter

                    try:
                        params = []
                        for p in ep_data.get("parameters", []):
                            params.append(
                                APIParameter(
                                    name=p.get("name", "unknown"),
                                    location=ParameterLocation(p.get("location", "query")),
                                    required=p.get("required", False),
                                    param_type=p.get("type", "string"),
                                    description=p.get("description"),
                                )
                            )

                        endpoint = APIEndpoint(
                            path=ep_data.get("path", "/"),
                            method=HTTPMethod(ep_data.get("method", "GET")),
                            summary=ep_data.get("summary"),
                            description=ep_data.get("description"),
                            tags=ep_data.get("tags", []),
                            parameters=params,
                        )
                        doc.endpoints.append(endpoint)
                    except (ValueError, KeyError):
                        continue

        # Update the document
        doc.policies = merged_policies

        return doc

    def _parse_json_response(self, response_text: str) -> Any:
        """Parse JSON from LLM response, handling markdown code blocks."""
        text = response_text.strip()

        # Remove markdown code blocks if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json or ```)
            lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)

        return json.loads(text)

    def _build_policy_from_data(self, data: Dict[str, Any]) -> APIPolicy:
        """Build APIPolicy from extracted data dictionary."""
        rate_limit = None
        auth = None
        error_handling = None

        # Build rate limit policy
        rl_data = data.get("rate_limit", {})
        if rl_data and any(v for v in rl_data.values() if v is not None):
            rate_limit = RateLimitPolicy(
                requests_per_minute=rl_data.get("requests_per_minute"),
                requests_per_hour=rl_data.get("requests_per_hour"),
                requests_per_day=rl_data.get("requests_per_day"),
                burst_limit=rl_data.get("burst_limit"),
                concurrent_limit=rl_data.get("concurrent_limit"),
                notes=rl_data.get("notes"),
            )

        # Build authentication policy
        auth_data = data.get("authentication", {})
        if auth_data and auth_data.get("auth_type"):
            auth_type_str = auth_data.get("auth_type", "none").lower()
            auth_type_map = {
                "api_key": AuthenticationType.API_KEY,
                "bearer_token": AuthenticationType.BEARER_TOKEN,
                "bearer": AuthenticationType.BEARER_TOKEN,
                "oauth2": AuthenticationType.OAUTH2,
                "oauth": AuthenticationType.OAUTH2,
                "basic": AuthenticationType.BASIC,
                "none": AuthenticationType.NONE,
            }
            auth_type = auth_type_map.get(auth_type_str, AuthenticationType.CUSTOM)

            api_key_loc = auth_data.get("api_key_location")
            if api_key_loc:
                try:
                    api_key_loc = ParameterLocation(api_key_loc)
                except ValueError:
                    api_key_loc = ParameterLocation.HEADER

            auth = AuthenticationPolicy(
                auth_type=auth_type,
                header_name=auth_data.get("header_name"),
                header_prefix=auth_data.get("header_prefix"),
                api_key_name=auth_data.get("api_key_name"),
                api_key_location=api_key_loc,
                scopes=auth_data.get("scopes"),
                notes=auth_data.get("notes"),
            )

        # Build error handling policy
        eh_data = data.get("error_handling", {})
        if eh_data:
            error_handling = ErrorHandlingPolicy(
                error_format=eh_data.get("error_format"),
                error_codes=eh_data.get("error_codes", {}),
                retry_codes=eh_data.get("retry_codes", [429, 500, 502, 503, 504]),
                max_retries=eh_data.get("max_retries", 3),
                backoff_strategy=eh_data.get("backoff_strategy", "exponential"),
                idempotency_key_header=eh_data.get("idempotency_key_header"),
                notes=eh_data.get("notes"),
            )

        return APIPolicy(
            rate_limit=rate_limit,
            authentication=auth,
            error_handling=error_handling,
            usage_guidelines=data.get("usage_guidelines"),
            deprecation_policy=data.get("deprecation_policy"),
            versioning_strategy=data.get("versioning_strategy"),
            terms_of_service=data.get("terms_summary"),
        )

    def _merge_policies(
        self, parser_policy: APIPolicy, llm_policy: APIPolicy
    ) -> APIPolicy:
        """Merge policies from parser and LLM, preferring LLM for missing fields."""
        # Start with parser policy as base
        merged = APIPolicy(
            rate_limit=parser_policy.rate_limit,
            authentication=parser_policy.authentication,
            error_handling=parser_policy.error_handling,
            usage_guidelines=parser_policy.usage_guidelines,
            terms_of_service=parser_policy.terms_of_service,
            deprecation_policy=parser_policy.deprecation_policy,
            versioning_strategy=parser_policy.versioning_strategy,
        )

        # Override with LLM policy if parser fields are empty
        if llm_policy.rate_limit and not merged.rate_limit:
            merged.rate_limit = llm_policy.rate_limit
        elif llm_policy.rate_limit and merged.rate_limit:
            # Merge rate limit fields
            rl = merged.rate_limit
            llm_rl = llm_policy.rate_limit
            merged.rate_limit = RateLimitPolicy(
                requests_per_minute=rl.requests_per_minute or llm_rl.requests_per_minute,
                requests_per_hour=rl.requests_per_hour or llm_rl.requests_per_hour,
                requests_per_day=rl.requests_per_day or llm_rl.requests_per_day,
                burst_limit=rl.burst_limit or llm_rl.burst_limit,
                concurrent_limit=rl.concurrent_limit or llm_rl.concurrent_limit,
                notes=llm_rl.notes or rl.notes,
            )

        if llm_policy.authentication and not merged.authentication:
            merged.authentication = llm_policy.authentication

        if llm_policy.error_handling and not merged.error_handling:
            merged.error_handling = llm_policy.error_handling

        if llm_policy.usage_guidelines and not merged.usage_guidelines:
            merged.usage_guidelines = llm_policy.usage_guidelines

        if llm_policy.deprecation_policy and not merged.deprecation_policy:
            merged.deprecation_policy = llm_policy.deprecation_policy

        if llm_policy.versioning_strategy and not merged.versioning_strategy:
            merged.versioning_strategy = llm_policy.versioning_strategy

        if llm_policy.terms_of_service and not merged.terms_of_service:
            merged.terms_of_service = llm_policy.terms_of_service

        return merged
