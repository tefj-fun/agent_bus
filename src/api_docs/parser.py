"""Multi-format API document parser.

Parses various API documentation formats (OpenAPI, Markdown, HTML, text)
into a unified ProcessedAPIDocument structure.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import yaml

from .schema import (
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


class APIDocumentParser:
    """Parser for multiple API documentation formats.

    Supports:
    - OpenAPI 3.x (JSON/YAML)
    - OpenAPI 2.x / Swagger (JSON/YAML)
    - Markdown documentation
    - Plain text documentation
    """

    def __init__(self):
        self._format_parsers = {
            DocumentFormat.OPENAPI_3: self._parse_openapi_3,
            DocumentFormat.OPENAPI_2: self._parse_openapi_2,
            DocumentFormat.MARKDOWN: self._parse_markdown,
            DocumentFormat.TEXT: self._parse_text,
            DocumentFormat.HTML: self._parse_html,
        }

    def detect_format(self, content: str) -> DocumentFormat:
        """Detect the format of the API document.

        Args:
            content: Raw document content

        Returns:
            Detected DocumentFormat
        """
        content_stripped = content.strip()

        # Try to parse as JSON first
        if content_stripped.startswith("{"):
            try:
                data = json.loads(content)
                if "openapi" in data:
                    version = data.get("openapi", "")
                    if version.startswith("3"):
                        return DocumentFormat.OPENAPI_3
                if "swagger" in data:
                    return DocumentFormat.OPENAPI_2
            except json.JSONDecodeError:
                pass

        # Try YAML
        if "openapi:" in content or "swagger:" in content:
            try:
                data = yaml.safe_load(content)
                if isinstance(data, dict):
                    if "openapi" in data:
                        version = str(data.get("openapi", ""))
                        if version.startswith("3"):
                            return DocumentFormat.OPENAPI_3
                    if "swagger" in data:
                        return DocumentFormat.OPENAPI_2
            except yaml.YAMLError:
                pass

        # Check for HTML
        if content_stripped.startswith("<!DOCTYPE") or content_stripped.startswith("<html"):
            return DocumentFormat.HTML

        # Check for Markdown patterns
        markdown_patterns = [
            r"^#{1,6}\s",  # Headers
            r"^\*\*.*\*\*",  # Bold
            r"^```",  # Code blocks
            r"^\[.*\]\(.*\)",  # Links
            r"^-\s",  # Unordered lists
            r"^\d+\.\s",  # Ordered lists
        ]
        for pattern in markdown_patterns:
            if re.search(pattern, content, re.MULTILINE):
                return DocumentFormat.MARKDOWN

        return DocumentFormat.TEXT

    def parse(
        self,
        doc_id: str,
        name: str,
        content: str,
        format_hint: Optional[DocumentFormat] = None,
        source_url: Optional[str] = None,
        version: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProcessedAPIDocument:
        """Parse an API document into structured format.

        Args:
            doc_id: Unique document identifier
            name: API name
            content: Raw document content
            format_hint: Optional format hint (auto-detected if not provided)
            source_url: Original document URL
            version: API version
            metadata: Additional metadata

        Returns:
            ProcessedAPIDocument with extracted structure
        """
        # Detect format if not provided
        doc_format = format_hint or self.detect_format(content)

        # Create raw document record
        raw_doc = APIDocument(
            doc_id=doc_id,
            name=name,
            version=version,
            format=doc_format,
            source_url=source_url,
            content=content,
            content_hash=hashlib.sha256(content.encode()).hexdigest(),
            metadata=metadata or {},
        )

        # Get the appropriate parser
        parser_func = self._format_parsers.get(doc_format, self._parse_text)

        # Parse and return
        return parser_func(raw_doc)

    # =========================================================================
    # OpenAPI 3.x Parser
    # =========================================================================

    def _parse_openapi_3(self, doc: APIDocument) -> ProcessedAPIDocument:
        """Parse OpenAPI 3.x specification."""
        try:
            if doc.content.strip().startswith("{"):
                spec = json.loads(doc.content)
            else:
                spec = yaml.safe_load(doc.content)
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            # Fall back to text parsing if spec is invalid
            return self._parse_text(doc.model_copy(update={"format": DocumentFormat.TEXT}))

        info = spec.get("info", {})
        servers = spec.get("servers", [])

        # Extract base URL
        base_url = None
        if servers:
            base_url = servers[0].get("url", "")

        # Parse endpoints
        endpoints = self._parse_openapi_3_paths(spec.get("paths", {}), spec)

        # Extract policies
        policies = self._extract_openapi_policies(spec)

        # Extract tags
        tags = [tag.get("name", "") for tag in spec.get("tags", [])]

        return ProcessedAPIDocument(
            doc_id=doc.doc_id,
            name=doc.name or info.get("title", "Untitled API"),
            version=doc.version or info.get("version"),
            base_url=base_url,
            description=info.get("description"),
            format=doc.format,
            endpoints=endpoints,
            policies=policies,
            tags=tags,
            servers=[{"url": s.get("url"), "description": s.get("description", "")} for s in servers],
            source_url=doc.source_url,
            metadata=doc.metadata,
        )

    def _parse_openapi_3_paths(
        self, paths: Dict[str, Any], spec: Dict[str, Any]
    ) -> List[APIEndpoint]:
        """Parse OpenAPI 3.x paths into endpoints."""
        endpoints = []

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            # Common parameters for all methods in this path
            common_params = path_item.get("parameters", [])

            for method in ["get", "post", "put", "patch", "delete", "head", "options"]:
                if method not in path_item:
                    continue

                operation = path_item[method]
                if not isinstance(operation, dict):
                    continue

                # Parse parameters
                params = self._parse_openapi_3_parameters(
                    common_params + operation.get("parameters", []), spec
                )

                # Parse request body
                request_body = self._parse_openapi_3_request_body(
                    operation.get("requestBody"), spec
                )

                # Parse responses
                responses = self._parse_openapi_3_responses(
                    operation.get("responses", {}), spec
                )

                endpoint = APIEndpoint(
                    path=path,
                    method=HTTPMethod(method.upper()),
                    summary=operation.get("summary"),
                    description=operation.get("description"),
                    operation_id=operation.get("operationId"),
                    tags=operation.get("tags", []),
                    parameters=params,
                    request_body=request_body,
                    responses=responses,
                    deprecated=operation.get("deprecated", False),
                    security=[
                        list(s.keys())[0] for s in operation.get("security", []) if s
                    ] or None,
                )
                endpoints.append(endpoint)

        return endpoints

    def _parse_openapi_3_parameters(
        self, params: List[Dict], spec: Dict[str, Any]
    ) -> List[APIParameter]:
        """Parse OpenAPI 3.x parameters."""
        result = []

        for param in params:
            # Handle $ref
            if "$ref" in param:
                param = self._resolve_ref(param["$ref"], spec)
                if not param:
                    continue

            location_map = {
                "path": ParameterLocation.PATH,
                "query": ParameterLocation.QUERY,
                "header": ParameterLocation.HEADER,
                "cookie": ParameterLocation.COOKIE,
            }

            schema = param.get("schema", {})

            result.append(
                APIParameter(
                    name=param.get("name", "unknown"),
                    location=location_map.get(param.get("in", "query"), ParameterLocation.QUERY),
                    required=param.get("required", False),
                    param_type=schema.get("type", "string"),
                    description=param.get("description"),
                    default=schema.get("default"),
                    enum_values=schema.get("enum"),
                    example=param.get("example") or schema.get("example"),
                    constraints=self._extract_constraints(schema),
                )
            )

        return result

    def _parse_openapi_3_request_body(
        self, request_body: Optional[Dict], spec: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Parse OpenAPI 3.x request body."""
        if not request_body:
            return None

        # Handle $ref
        if "$ref" in request_body:
            request_body = self._resolve_ref(request_body["$ref"], spec)
            if not request_body:
                return None

        content = request_body.get("content", {})
        json_content = content.get("application/json", {})

        return {
            "required": request_body.get("required", False),
            "description": request_body.get("description"),
            "content_type": "application/json" if json_content else list(content.keys())[0] if content else None,
            "schema": json_content.get("schema") if json_content else None,
        }

    def _parse_openapi_3_responses(
        self, responses: Dict[str, Any], spec: Dict[str, Any]
    ) -> List[APIResponse]:
        """Parse OpenAPI 3.x responses."""
        result = []

        for status_code, response in responses.items():
            if status_code == "default":
                status_code = "0"

            # Handle $ref
            if "$ref" in response:
                response = self._resolve_ref(response["$ref"], spec)
                if not response:
                    continue

            content = response.get("content", {})
            json_content = content.get("application/json", {})

            result.append(
                APIResponse(
                    status_code=int(status_code) if status_code.isdigit() else 0,
                    description=response.get("description"),
                    content_type="application/json" if json_content else (
                        list(content.keys())[0] if content else "application/json"
                    ),
                    schema=json_content.get("schema") if json_content else None,
                    example=json_content.get("example") if json_content else None,
                )
            )

        return result

    def _resolve_ref(self, ref: str, spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Resolve a $ref pointer in OpenAPI spec."""
        if not ref.startswith("#/"):
            return None

        parts = ref[2:].split("/")
        current = spec

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current if isinstance(current, dict) else None

    def _extract_constraints(self, schema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract validation constraints from schema."""
        constraints = {}
        constraint_keys = [
            "minimum", "maximum", "minLength", "maxLength",
            "pattern", "minItems", "maxItems", "uniqueItems",
            "format",
        ]

        for key in constraint_keys:
            if key in schema:
                constraints[key] = schema[key]

        return constraints if constraints else None

    def _extract_openapi_policies(self, spec: Dict[str, Any]) -> APIPolicy:
        """Extract policies from OpenAPI specification."""
        # Extract authentication
        auth_policy = self._extract_openapi_auth(spec)

        # Extract rate limits from extensions or info
        rate_limit = self._extract_openapi_rate_limits(spec)

        # Extract error handling info
        error_handling = self._extract_openapi_error_handling(spec)

        return APIPolicy(
            rate_limit=rate_limit,
            authentication=auth_policy,
            error_handling=error_handling,
            versioning_strategy=self._detect_versioning_strategy(spec),
        )

    def _extract_openapi_auth(self, spec: Dict[str, Any]) -> Optional[AuthenticationPolicy]:
        """Extract authentication policy from OpenAPI security schemes."""
        security_schemes = spec.get("components", {}).get("securitySchemes", {})
        if not security_schemes:
            # Check OpenAPI 2.x location
            security_schemes = spec.get("securityDefinitions", {})

        if not security_schemes:
            return None

        # Get the first/primary security scheme
        for name, scheme in security_schemes.items():
            scheme_type = scheme.get("type", "")

            if scheme_type == "apiKey":
                return AuthenticationPolicy(
                    auth_type=AuthenticationType.API_KEY,
                    api_key_location=ParameterLocation(scheme.get("in", "header")),
                    api_key_name=scheme.get("name"),
                    header_name=scheme.get("name") if scheme.get("in") == "header" else None,
                )

            elif scheme_type == "http":
                scheme_name = scheme.get("scheme", "").lower()
                if scheme_name == "bearer":
                    return AuthenticationPolicy(
                        auth_type=AuthenticationType.BEARER_TOKEN,
                        header_name="Authorization",
                        header_prefix="Bearer",
                    )
                elif scheme_name == "basic":
                    return AuthenticationPolicy(
                        auth_type=AuthenticationType.BASIC,
                        header_name="Authorization",
                    )

            elif scheme_type == "oauth2":
                flows = scheme.get("flows", {})
                return AuthenticationPolicy(
                    auth_type=AuthenticationType.OAUTH2,
                    oauth_flows=flows,
                    scopes=self._extract_oauth_scopes(flows),
                    token_url=self._extract_token_url(flows),
                )

        return None

    def _extract_oauth_scopes(self, flows: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Extract OAuth scopes from flows."""
        for flow_name, flow_config in flows.items():
            if isinstance(flow_config, dict) and "scopes" in flow_config:
                return flow_config["scopes"]
        return None

    def _extract_token_url(self, flows: Dict[str, Any]) -> Optional[str]:
        """Extract token URL from OAuth flows."""
        for flow_name in ["clientCredentials", "password", "authorizationCode"]:
            if flow_name in flows:
                return flows[flow_name].get("tokenUrl")
        return None

    def _extract_openapi_rate_limits(self, spec: Dict[str, Any]) -> Optional[RateLimitPolicy]:
        """Extract rate limits from OpenAPI extensions or description."""
        # Check for x-rate-limit extension
        info = spec.get("info", {})
        extensions = {k: v for k, v in info.items() if k.startswith("x-")}

        rate_limit = extensions.get("x-rateLimit") or extensions.get("x-rate-limit")
        if rate_limit:
            return RateLimitPolicy(
                requests_per_minute=rate_limit.get("requestsPerMinute"),
                requests_per_hour=rate_limit.get("requestsPerHour"),
                requests_per_day=rate_limit.get("requestsPerDay"),
            )

        # Try to extract from description
        description = info.get("description", "")
        return self._parse_rate_limits_from_text(description)

    def _extract_openapi_error_handling(self, spec: Dict[str, Any]) -> ErrorHandlingPolicy:
        """Extract error handling info from OpenAPI spec."""
        # Look for common error response schemas
        error_codes = {}

        # Scan responses for error patterns
        paths = spec.get("paths", {})
        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
            for method in ["get", "post", "put", "patch", "delete"]:
                if method not in path_item:
                    continue
                responses = path_item[method].get("responses", {})
                for code, response in responses.items():
                    if code.startswith("4") or code.startswith("5"):
                        desc = response.get("description", "")
                        if code not in error_codes:
                            error_codes[code] = desc

        return ErrorHandlingPolicy(error_codes=error_codes)

    def _detect_versioning_strategy(self, spec: Dict[str, Any]) -> Optional[str]:
        """Detect API versioning strategy."""
        servers = spec.get("servers", [])
        paths = list(spec.get("paths", {}).keys())

        # Check URL path versioning
        for path in paths:
            if re.match(r"^/v\d+", path):
                return "url_path"

        # Check server URL for version
        for server in servers:
            url = server.get("url", "")
            if re.search(r"/v\d+", url):
                return "url_path"

        # Check for version header mentions in description
        info = spec.get("info", {})
        description = info.get("description", "").lower()
        if "api-version" in description or "x-api-version" in description:
            return "header"

        return None

    # =========================================================================
    # OpenAPI 2.x (Swagger) Parser
    # =========================================================================

    def _parse_openapi_2(self, doc: APIDocument) -> ProcessedAPIDocument:
        """Parse OpenAPI 2.x (Swagger) specification."""
        try:
            if doc.content.strip().startswith("{"):
                spec = json.loads(doc.content)
            else:
                spec = yaml.safe_load(doc.content)
        except (json.JSONDecodeError, yaml.YAMLError):
            return self._parse_text(doc.model_copy(update={"format": DocumentFormat.TEXT}))

        info = spec.get("info", {})

        # Build base URL from host, basePath, schemes
        host = spec.get("host", "")
        base_path = spec.get("basePath", "")
        schemes = spec.get("schemes", ["https"])
        base_url = f"{schemes[0]}://{host}{base_path}" if host else None

        # Parse endpoints (similar to OpenAPI 3 but with different structure)
        endpoints = self._parse_openapi_2_paths(spec.get("paths", {}), spec)

        # Extract policies
        policies = self._extract_openapi_policies(spec)

        tags = [tag.get("name", "") for tag in spec.get("tags", [])]

        return ProcessedAPIDocument(
            doc_id=doc.doc_id,
            name=doc.name or info.get("title", "Untitled API"),
            version=doc.version or info.get("version"),
            base_url=base_url,
            description=info.get("description"),
            format=doc.format,
            endpoints=endpoints,
            policies=policies,
            tags=tags,
            servers=[{"url": base_url, "description": "Primary"}] if base_url else [],
            source_url=doc.source_url,
            metadata=doc.metadata,
        )

    def _parse_openapi_2_paths(
        self, paths: Dict[str, Any], spec: Dict[str, Any]
    ) -> List[APIEndpoint]:
        """Parse OpenAPI 2.x paths."""
        endpoints = []

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            common_params = path_item.get("parameters", [])

            for method in ["get", "post", "put", "patch", "delete", "head", "options"]:
                if method not in path_item:
                    continue

                operation = path_item[method]
                if not isinstance(operation, dict):
                    continue

                # Parse parameters (OpenAPI 2.x includes body as parameter)
                all_params = common_params + operation.get("parameters", [])
                params, request_body = self._parse_openapi_2_parameters(all_params, spec)

                # Parse responses
                responses = self._parse_openapi_2_responses(
                    operation.get("responses", {}), spec
                )

                endpoint = APIEndpoint(
                    path=path,
                    method=HTTPMethod(method.upper()),
                    summary=operation.get("summary"),
                    description=operation.get("description"),
                    operation_id=operation.get("operationId"),
                    tags=operation.get("tags", []),
                    parameters=params,
                    request_body=request_body,
                    responses=responses,
                    deprecated=operation.get("deprecated", False),
                )
                endpoints.append(endpoint)

        return endpoints

    def _parse_openapi_2_parameters(
        self, params: List[Dict], spec: Dict[str, Any]
    ) -> Tuple[List[APIParameter], Optional[Dict[str, Any]]]:
        """Parse OpenAPI 2.x parameters, separating body from others."""
        result = []
        request_body = None

        for param in params:
            # Handle $ref
            if "$ref" in param:
                param = self._resolve_ref(param["$ref"], spec)
                if not param:
                    continue

            param_in = param.get("in", "query")

            # Body parameter becomes request_body
            if param_in == "body":
                request_body = {
                    "required": param.get("required", False),
                    "description": param.get("description"),
                    "schema": param.get("schema"),
                }
                continue

            location_map = {
                "path": ParameterLocation.PATH,
                "query": ParameterLocation.QUERY,
                "header": ParameterLocation.HEADER,
                "formData": ParameterLocation.BODY,
            }

            result.append(
                APIParameter(
                    name=param.get("name", "unknown"),
                    location=location_map.get(param_in, ParameterLocation.QUERY),
                    required=param.get("required", False),
                    param_type=param.get("type", "string"),
                    description=param.get("description"),
                    default=param.get("default"),
                    enum_values=param.get("enum"),
                    example=param.get("x-example"),
                    constraints=self._extract_constraints(param),
                )
            )

        return result, request_body

    def _parse_openapi_2_responses(
        self, responses: Dict[str, Any], spec: Dict[str, Any]
    ) -> List[APIResponse]:
        """Parse OpenAPI 2.x responses."""
        result = []

        for status_code, response in responses.items():
            if status_code == "default":
                status_code = "0"

            # Handle $ref
            if "$ref" in response:
                response = self._resolve_ref(response["$ref"], spec)
                if not response:
                    continue

            result.append(
                APIResponse(
                    status_code=int(status_code) if status_code.isdigit() else 0,
                    description=response.get("description"),
                    schema=response.get("schema"),
                )
            )

        return result

    # =========================================================================
    # Markdown Parser
    # =========================================================================

    def _parse_markdown(self, doc: APIDocument) -> ProcessedAPIDocument:
        """Parse Markdown API documentation."""
        content = doc.content

        # Extract title from first header
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        title = title_match.group(1) if title_match else doc.name

        # Extract description (first paragraph after title)
        desc_match = re.search(
            r"^#\s+.+\n\n(.+?)(?=\n\n|\n#)", content, re.MULTILINE | re.DOTALL
        )
        description = desc_match.group(1).strip() if desc_match else None

        # Extract endpoints from code blocks and headers
        endpoints = self._extract_endpoints_from_markdown(content)

        # Extract policies from text
        policies = self._extract_policies_from_text(content)

        # Extract base URL
        base_url = self._extract_base_url_from_text(content)

        return ProcessedAPIDocument(
            doc_id=doc.doc_id,
            name=doc.name or title,
            version=doc.version or self._extract_version_from_text(content),
            base_url=base_url,
            description=description,
            format=doc.format,
            endpoints=endpoints,
            policies=policies,
            source_url=doc.source_url,
            metadata=doc.metadata,
        )

    def _extract_endpoints_from_markdown(self, content: str) -> List[APIEndpoint]:
        """Extract endpoints from Markdown content."""
        endpoints = []

        # Pattern for endpoint headers like "### GET /users/{id}"
        endpoint_pattern = r"#{2,4}\s+(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(/[^\s\n]+)"
        matches = re.finditer(endpoint_pattern, content, re.IGNORECASE)

        for match in matches:
            method = match.group(1).upper()
            path = match.group(2)

            # Get section content until next header
            start = match.end()
            next_header = re.search(r"\n#{2,4}\s+", content[start:])
            end = start + next_header.start() if next_header else len(content)
            section = content[start:end]

            # Extract description
            desc_match = re.search(r"\n\n(.+?)(?=\n\n|\n```)", section, re.DOTALL)
            description = desc_match.group(1).strip() if desc_match else None

            # Extract parameters from tables or lists
            params = self._extract_params_from_markdown_section(section)

            endpoints.append(
                APIEndpoint(
                    path=path,
                    method=HTTPMethod(method),
                    description=description,
                    parameters=params,
                )
            )

        return endpoints

    def _extract_params_from_markdown_section(self, section: str) -> List[APIParameter]:
        """Extract parameters from a Markdown section."""
        params = []

        # Pattern for parameter lists: "- `param_name` (type, required): description"
        param_pattern = r"-\s+`(\w+)`\s*\(([^)]+)\)(?::\s*(.+))?"
        matches = re.finditer(param_pattern, section)

        for match in matches:
            name = match.group(1)
            type_info = match.group(2).lower()
            description = match.group(3)

            # Parse type info
            required = "required" in type_info
            param_type = "string"
            for t in ["integer", "number", "boolean", "array", "object"]:
                if t in type_info:
                    param_type = t
                    break

            # Determine location
            location = ParameterLocation.QUERY
            if "path" in type_info:
                location = ParameterLocation.PATH
            elif "header" in type_info:
                location = ParameterLocation.HEADER
            elif "body" in type_info:
                location = ParameterLocation.BODY

            params.append(
                APIParameter(
                    name=name,
                    location=location,
                    required=required,
                    param_type=param_type,
                    description=description,
                )
            )

        return params

    # =========================================================================
    # Text Parser
    # =========================================================================

    def _parse_text(self, doc: APIDocument) -> ProcessedAPIDocument:
        """Parse plain text API documentation."""
        content = doc.content

        # Try to extract structure from text
        endpoints = self._extract_endpoints_from_text(content)
        policies = self._extract_policies_from_text(content)
        base_url = self._extract_base_url_from_text(content)
        version = self._extract_version_from_text(content)

        # Extract title (first line or doc name)
        lines = content.strip().split("\n")
        title = lines[0].strip() if lines else doc.name

        return ProcessedAPIDocument(
            doc_id=doc.doc_id,
            name=doc.name or title,
            version=doc.version or version,
            base_url=base_url,
            description=content[:500] if len(content) > 500 else content,
            format=doc.format,
            endpoints=endpoints,
            policies=policies,
            source_url=doc.source_url,
            metadata=doc.metadata,
        )

    def _extract_endpoints_from_text(self, content: str) -> List[APIEndpoint]:
        """Extract endpoints from plain text."""
        endpoints = []

        # Pattern for HTTP method + path
        pattern = r"\b(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(/[^\s\n]+)"
        matches = re.finditer(pattern, content, re.IGNORECASE)

        seen = set()
        for match in matches:
            method = match.group(1).upper()
            path = match.group(2)
            key = f"{method} {path}"

            if key not in seen:
                seen.add(key)
                endpoints.append(
                    APIEndpoint(
                        path=path,
                        method=HTTPMethod(method),
                    )
                )

        return endpoints

    def _parse_html(self, doc: APIDocument) -> ProcessedAPIDocument:
        """Parse HTML API documentation (basic extraction)."""
        # Simple HTML to text conversion
        content = doc.content

        # Remove script and style tags
        content = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r"<style[^>]*>.*?</style>", "", content, flags=re.DOTALL | re.IGNORECASE)

        # Remove HTML tags but keep content
        content = re.sub(r"<[^>]+>", " ", content)

        # Clean up whitespace
        content = re.sub(r"\s+", " ", content).strip()

        # Create a text document and parse it
        text_doc = APIDocument(
            doc_id=doc.doc_id,
            name=doc.name,
            version=doc.version,
            format=DocumentFormat.TEXT,
            source_url=doc.source_url,
            content=content,
            metadata=doc.metadata,
        )

        result = self._parse_text(text_doc)
        result.format = DocumentFormat.HTML
        return result

    # =========================================================================
    # Common Extraction Helpers
    # =========================================================================

    def _extract_policies_from_text(self, content: str) -> APIPolicy:
        """Extract policies from free-form text."""
        rate_limit = self._parse_rate_limits_from_text(content)
        auth = self._parse_auth_from_text(content)
        error_handling = ErrorHandlingPolicy()

        return APIPolicy(
            rate_limit=rate_limit,
            authentication=auth,
            error_handling=error_handling,
        )

    def _parse_rate_limits_from_text(self, content: str) -> Optional[RateLimitPolicy]:
        """Parse rate limits from text content."""
        content_lower = content.lower()

        # Look for rate limit patterns
        rpm_match = re.search(r"(\d+)\s*(?:requests?|calls?)\s*per\s*minute", content_lower)
        rph_match = re.search(r"(\d+)\s*(?:requests?|calls?)\s*per\s*hour", content_lower)
        rpd_match = re.search(r"(\d+)\s*(?:requests?|calls?)\s*per\s*day", content_lower)

        if not any([rpm_match, rph_match, rpd_match]):
            # Alternative patterns
            rpm_match = re.search(r"rate\s*limit[:\s]+(\d+)\s*/\s*min", content_lower)
            rph_match = re.search(r"rate\s*limit[:\s]+(\d+)\s*/\s*hour", content_lower)

        if not any([rpm_match, rph_match, rpd_match]):
            return None

        return RateLimitPolicy(
            requests_per_minute=int(rpm_match.group(1)) if rpm_match else None,
            requests_per_hour=int(rph_match.group(1)) if rph_match else None,
            requests_per_day=int(rpd_match.group(1)) if rpd_match else None,
        )

    def _parse_auth_from_text(self, content: str) -> Optional[AuthenticationPolicy]:
        """Parse authentication info from text."""
        content_lower = content.lower()

        if "api key" in content_lower or "api_key" in content_lower:
            # Try to find header name
            header_match = re.search(
                r"(?:header|key)[:\s]+[\"']?([A-Za-z-_]+)[\"']?",
                content,
                re.IGNORECASE,
            )
            return AuthenticationPolicy(
                auth_type=AuthenticationType.API_KEY,
                api_key_location=ParameterLocation.HEADER,
                api_key_name=header_match.group(1) if header_match else "X-API-Key",
            )

        if "bearer" in content_lower:
            return AuthenticationPolicy(
                auth_type=AuthenticationType.BEARER_TOKEN,
                header_name="Authorization",
                header_prefix="Bearer",
            )

        if "oauth" in content_lower:
            return AuthenticationPolicy(auth_type=AuthenticationType.OAUTH2)

        if "basic auth" in content_lower:
            return AuthenticationPolicy(
                auth_type=AuthenticationType.BASIC,
                header_name="Authorization",
            )

        return None

    def _extract_base_url_from_text(self, content: str) -> Optional[str]:
        """Extract base URL from text content."""
        # Look for URL patterns
        url_pattern = r"(?:base\s*url|endpoint|server)[:\s]+[\"']?(https?://[^\s\"']+)[\"']?"
        match = re.search(url_pattern, content, re.IGNORECASE)
        if match:
            return match.group(1).rstrip("/")

        # Look for any https URL that looks like an API
        api_url_pattern = r"(https?://[^\s\"']+(?:api|v\d)[^\s\"']*)"
        match = re.search(api_url_pattern, content, re.IGNORECASE)
        if match:
            url = match.group(1).rstrip("/")
            # Remove path after version
            parsed = urlparse(url)
            return f"{parsed.scheme}://{parsed.netloc}"

        return None

    def _extract_version_from_text(self, content: str) -> Optional[str]:
        """Extract API version from text."""
        # Common version patterns
        patterns = [
            r"(?:api\s*)?version[:\s]+[\"']?v?(\d+(?:\.\d+)*)[\"']?",
            r"v(\d+(?:\.\d+)*)",
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)

        return None
