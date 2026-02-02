# API Documentation Skill

You are an expert technical writer specializing in API documentation, OpenAPI specifications, and developer experience.

## OpenAPI 3.1 Specification Guide

### Basic Structure

```yaml
openapi: 3.1.0
info:
  title: API Name
  description: |
    Comprehensive API description with:
    - Key features
    - Authentication overview
    - Rate limiting info
  version: 1.0.0
  contact:
    name: API Support
    email: api-support@example.com
    url: https://example.com/support
  license:
    name: MIT
    url: https://opensource.org/licenses/MIT

servers:
  - url: https://api.example.com/v1
    description: Production
  - url: https://staging-api.example.com/v1
    description: Staging
  - url: http://localhost:8000/v1
    description: Local development

tags:
  - name: Users
    description: User management operations
  - name: Projects
    description: Project CRUD operations

paths:
  /users:
    # ... endpoints

components:
  schemas:
    # ... data models
  securitySchemes:
    # ... auth methods
```

### Path Operations

```yaml
paths:
  /users:
    get:
      operationId: listUsers
      summary: List all users
      description: |
        Returns a paginated list of users.

        **Permissions required**: `users:read`
      tags:
        - Users
      parameters:
        - $ref: '#/components/parameters/PageParam'
        - $ref: '#/components/parameters/LimitParam'
        - name: status
          in: query
          description: Filter by user status
          schema:
            type: string
            enum: [active, inactive, pending]
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserList'
              examples:
                default:
                  $ref: '#/components/examples/UserListExample'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '403':
          $ref: '#/components/responses/Forbidden'
      security:
        - bearerAuth: []
        - apiKey: []

    post:
      operationId: createUser
      summary: Create a new user
      description: |
        Creates a new user account.

        **Permissions required**: `users:write`
      tags:
        - Users
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UserCreate'
            examples:
              basic:
                summary: Basic user creation
                value:
                  email: user@example.com
                  name: John Doe
              withMetadata:
                summary: User with metadata
                value:
                  email: user@example.com
                  name: John Doe
                  metadata:
                    department: Engineering
      responses:
        '201':
          description: User created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
        '400':
          $ref: '#/components/responses/BadRequest'
        '409':
          description: User already exists
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'
```

### Components

#### Schemas (Data Models)

```yaml
components:
  schemas:
    User:
      type: object
      required:
        - id
        - email
        - created_at
      properties:
        id:
          type: string
          format: uuid
          description: Unique user identifier
          example: "550e8400-e29b-41d4-a716-446655440000"
        email:
          type: string
          format: email
          description: User's email address
          example: "user@example.com"
        name:
          type: string
          description: User's display name
          example: "John Doe"
          minLength: 1
          maxLength: 100
        status:
          type: string
          enum: [active, inactive, pending]
          default: pending
          description: Account status
        created_at:
          type: string
          format: date-time
          description: Account creation timestamp
        metadata:
          type: object
          additionalProperties: true
          description: Custom metadata

    UserCreate:
      type: object
      required:
        - email
      properties:
        email:
          type: string
          format: email
        name:
          type: string
        metadata:
          type: object

    UserList:
      type: object
      properties:
        data:
          type: array
          items:
            $ref: '#/components/schemas/User'
        pagination:
          $ref: '#/components/schemas/Pagination'

    Pagination:
      type: object
      properties:
        page:
          type: integer
          minimum: 1
        limit:
          type: integer
          minimum: 1
          maximum: 100
        total:
          type: integer
        has_more:
          type: boolean

    Error:
      type: object
      required:
        - code
        - message
      properties:
        code:
          type: string
          description: Error code for programmatic handling
          example: "VALIDATION_ERROR"
        message:
          type: string
          description: Human-readable error message
        details:
          type: array
          items:
            type: object
            properties:
              field:
                type: string
              message:
                type: string
```

#### Security Schemes

```yaml
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
      description: |
        JWT token authentication.

        Include in header: `Authorization: Bearer <token>`

        Obtain tokens via `/auth/login` endpoint.

    apiKey:
      type: apiKey
      in: header
      name: X-API-Key
      description: |
        API key authentication for server-to-server communication.

        Generate keys in the dashboard under Settings > API Keys.

    oauth2:
      type: oauth2
      flows:
        authorizationCode:
          authorizationUrl: https://auth.example.com/authorize
          tokenUrl: https://auth.example.com/token
          refreshUrl: https://auth.example.com/refresh
          scopes:
            users:read: Read user information
            users:write: Create and modify users
            projects:read: Read project information
            projects:write: Create and modify projects
```

#### Reusable Components

```yaml
components:
  parameters:
    PageParam:
      name: page
      in: query
      description: Page number (1-indexed)
      schema:
        type: integer
        minimum: 1
        default: 1

    LimitParam:
      name: limit
      in: query
      description: Items per page
      schema:
        type: integer
        minimum: 1
        maximum: 100
        default: 20

    IdPath:
      name: id
      in: path
      required: true
      description: Resource ID
      schema:
        type: string
        format: uuid

  responses:
    Unauthorized:
      description: Authentication required
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
          example:
            code: UNAUTHORIZED
            message: Authentication required

    Forbidden:
      description: Insufficient permissions
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
          example:
            code: FORBIDDEN
            message: You don't have permission to access this resource

    BadRequest:
      description: Invalid request
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'

    NotFound:
      description: Resource not found
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
          example:
            code: NOT_FOUND
            message: Resource not found
```

---

## SDK Code Examples

### Python (requests)

```python
import requests

class APIClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        })

    def list_users(self, page: int = 1, limit: int = 20) -> dict:
        """List all users with pagination."""
        response = self.session.get(
            f'{self.base_url}/users',
            params={'page': page, 'limit': limit}
        )
        response.raise_for_status()
        return response.json()

    def create_user(self, email: str, name: str = None) -> dict:
        """Create a new user."""
        response = self.session.post(
            f'{self.base_url}/users',
            json={'email': email, 'name': name}
        )
        response.raise_for_status()
        return response.json()

    def get_user(self, user_id: str) -> dict:
        """Get a user by ID."""
        response = self.session.get(f'{self.base_url}/users/{user_id}')
        response.raise_for_status()
        return response.json()


# Usage
client = APIClient('https://api.example.com/v1', 'your-api-key')
users = client.list_users(page=1, limit=10)
new_user = client.create_user('user@example.com', 'John Doe')
```

### Python (httpx async)

```python
import httpx
from typing import Optional

class AsyncAPIClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            timeout=30.0
        )

    async def list_users(self, page: int = 1, limit: int = 20) -> dict:
        response = await self.client.get(
            f'{self.base_url}/users',
            params={'page': page, 'limit': limit}
        )
        response.raise_for_status()
        return response.json()

    async def create_user(self, email: str, name: Optional[str] = None) -> dict:
        response = await self.client.post(
            f'{self.base_url}/users',
            json={'email': email, 'name': name}
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        await self.client.aclose()


# Usage
async def main():
    client = AsyncAPIClient('https://api.example.com/v1', 'your-api-key')
    try:
        users = await client.list_users()
        print(users)
    finally:
        await client.close()
```

### JavaScript (fetch)

```javascript
class APIClient {
  constructor(baseUrl, apiKey) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.apiKey = apiKey;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'API request failed');
    }

    return response.json();
  }

  async listUsers(page = 1, limit = 20) {
    const params = new URLSearchParams({ page, limit });
    return this.request(`/users?${params}`);
  }

  async createUser(email, name = null) {
    return this.request('/users', {
      method: 'POST',
      body: JSON.stringify({ email, name }),
    });
  }

  async getUser(userId) {
    return this.request(`/users/${userId}`);
  }
}

// Usage
const client = new APIClient('https://api.example.com/v1', 'your-api-key');
const users = await client.listUsers(1, 10);
const newUser = await client.createUser('user@example.com', 'John Doe');
```

### TypeScript (axios)

```typescript
import axios, { AxiosInstance } from 'axios';

interface User {
  id: string;
  email: string;
  name?: string;
  status: 'active' | 'inactive' | 'pending';
  created_at: string;
}

interface UserList {
  data: User[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    has_more: boolean;
  };
}

interface CreateUserRequest {
  email: string;
  name?: string;
  metadata?: Record<string, unknown>;
}

class APIClient {
  private client: AxiosInstance;

  constructor(baseUrl: string, apiKey: string) {
    this.client = axios.create({
      baseURL: baseUrl,
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
    });
  }

  async listUsers(page = 1, limit = 20): Promise<UserList> {
    const { data } = await this.client.get<UserList>('/users', {
      params: { page, limit },
    });
    return data;
  }

  async createUser(request: CreateUserRequest): Promise<User> {
    const { data } = await this.client.post<User>('/users', request);
    return data;
  }

  async getUser(userId: string): Promise<User> {
    const { data } = await this.client.get<User>(`/users/${userId}`);
    return data;
  }
}
```

### cURL

```bash
# List users
curl -X GET "https://api.example.com/v1/users?page=1&limit=20" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json"

# Create user
curl -X POST "https://api.example.com/v1/users" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "name": "John Doe"
  }'

# Get user by ID
curl -X GET "https://api.example.com/v1/users/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer YOUR_API_KEY"

# Update user
curl -X PATCH "https://api.example.com/v1/users/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jane Doe"
  }'

# Delete user
curl -X DELETE "https://api.example.com/v1/users/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Go

```go
package api

import (
    "bytes"
    "encoding/json"
    "fmt"
    "net/http"
    "net/url"
)

type Client struct {
    BaseURL    string
    APIKey     string
    HTTPClient *http.Client
}

type User struct {
    ID        string            `json:"id"`
    Email     string            `json:"email"`
    Name      string            `json:"name,omitempty"`
    Status    string            `json:"status"`
    CreatedAt string            `json:"created_at"`
    Metadata  map[string]any    `json:"metadata,omitempty"`
}

type UserList struct {
    Data       []User     `json:"data"`
    Pagination Pagination `json:"pagination"`
}

type Pagination struct {
    Page    int  `json:"page"`
    Limit   int  `json:"limit"`
    Total   int  `json:"total"`
    HasMore bool `json:"has_more"`
}

func NewClient(baseURL, apiKey string) *Client {
    return &Client{
        BaseURL:    baseURL,
        APIKey:     apiKey,
        HTTPClient: &http.Client{},
    }
}

func (c *Client) ListUsers(page, limit int) (*UserList, error) {
    params := url.Values{}
    params.Set("page", fmt.Sprintf("%d", page))
    params.Set("limit", fmt.Sprintf("%d", limit))

    req, _ := http.NewRequest("GET", c.BaseURL+"/users?"+params.Encode(), nil)
    req.Header.Set("Authorization", "Bearer "+c.APIKey)

    resp, err := c.HTTPClient.Do(req)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()

    var result UserList
    json.NewDecoder(resp.Body).Decode(&result)
    return &result, nil
}

func (c *Client) CreateUser(email, name string) (*User, error) {
    body, _ := json.Marshal(map[string]string{
        "email": email,
        "name":  name,
    })

    req, _ := http.NewRequest("POST", c.BaseURL+"/users", bytes.NewBuffer(body))
    req.Header.Set("Authorization", "Bearer "+c.APIKey)
    req.Header.Set("Content-Type", "application/json")

    resp, err := c.HTTPClient.Do(req)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()

    var user User
    json.NewDecoder(resp.Body).Decode(&user)
    return &user, nil
}
```

---

## Integration Guide Template

### Getting Started

#### 1. Authentication

```markdown
## Authentication

This API uses **Bearer token authentication**. Include your API key in the
`Authorization` header of all requests:

\`\`\`
Authorization: Bearer YOUR_API_KEY
\`\`\`

### Obtaining API Keys

1. Log in to the [Dashboard](https://dashboard.example.com)
2. Navigate to **Settings** > **API Keys**
3. Click **Create New Key**
4. Copy and securely store your key (it won't be shown again)

### Key Types

| Type | Use Case | Rate Limit |
|------|----------|------------|
| Test | Development & testing | 100 req/min |
| Production | Live applications | 1000 req/min |
```

#### 2. Making Your First Request

```markdown
## Quick Start

### 1. Install the SDK

\`\`\`bash
# Python
pip install example-api

# JavaScript
npm install @example/api-client
\`\`\`

### 2. Initialize the Client

\`\`\`python
from example_api import Client

client = Client(api_key="your-api-key")
\`\`\`

### 3. Make a Request

\`\`\`python
# List all users
users = client.users.list()
print(f"Found {len(users.data)} users")

# Create a user
new_user = client.users.create(
    email="user@example.com",
    name="John Doe"
)
print(f"Created user: {new_user.id}")
\`\`\`
```

#### 3. Error Handling

```markdown
## Error Handling

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Invalid or missing API key |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Server Error - Contact support |

### Error Response Format

\`\`\`json
{
  "code": "VALIDATION_ERROR",
  "message": "Invalid email format",
  "details": [
    {
      "field": "email",
      "message": "Must be a valid email address"
    }
  ]
}
\`\`\`

### Handling Errors

\`\`\`python
from example_api import Client, APIError, RateLimitError

client = Client(api_key="your-api-key")

try:
    user = client.users.get("invalid-id")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")
except APIError as e:
    print(f"API error: {e.code} - {e.message}")
\`\`\`
```

#### 4. Pagination

```markdown
## Pagination

List endpoints return paginated results. Use `page` and `limit` parameters:

\`\`\`python
# Get first page
page1 = client.users.list(page=1, limit=20)

# Check for more pages
if page1.pagination.has_more:
    page2 = client.users.list(page=2, limit=20)
\`\`\`

### Response Format

\`\`\`json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 150,
    "has_more": true
  }
}
\`\`\`
```

---

## Documentation Output Format

When generating API documentation, include:

1. **Overview**
   - API description and purpose
   - Base URL and versioning
   - Authentication methods

2. **OpenAPI Specification**
   - Complete YAML/JSON spec
   - All endpoints with examples
   - Schema definitions

3. **SDK Examples**
   - Python, JavaScript, cURL at minimum
   - Copy-paste ready code
   - Error handling examples

4. **Integration Guide**
   - Quick start tutorial
   - Authentication setup
   - Common use cases

5. **Reference**
   - All endpoints documented
   - Request/response examples
   - Error codes and handling
