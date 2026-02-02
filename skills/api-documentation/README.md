# API Documentation Skill

A comprehensive skill for generating API documentation, OpenAPI specifications, and SDK examples.

## Overview

This skill enhances the API Document Agent and Technical Writer with:
- OpenAPI 3.1 specification generation
- Multi-language SDK code examples
- Integration guide templates
- Developer-friendly documentation patterns

## Capabilities

| Capability | Description |
|------------|-------------|
| `openapi-generation` | Generate OpenAPI 3.0+ specifications |
| `api-reference` | Create comprehensive API reference docs |
| `sdk-examples` | Generate code examples in multiple languages |
| `integration-guide` | Create step-by-step integration guides |

## Usage

```python
from src.skills import SkillsManager

manager = SkillsManager("./skills")
skill = await manager.load_skill("api-documentation")

# Use with API document agent
prompt = skill.get_prompt()
```

## Integration

```python
# In api_document_agent.py or technical_writer.py
class APIDocumentAgent(BaseAgent):
    async def execute(self, task):
        api_skill = await self.load_skill("api-documentation")

        prompt = f"""
        {api_skill.get_prompt()}

        Generate API documentation for:
        {task.input['api_spec']}
        """

        response = await self.query_llm(prompt=prompt)
        return AgentResult(...)
```

## Topics Covered

### OpenAPI Specification
- Complete 3.1 structure
- Path operations
- Components (schemas, security, parameters)
- Reusable response definitions

### SDK Examples
- Python (requests, httpx)
- JavaScript (fetch)
- TypeScript (axios)
- Go
- cURL

### Documentation Patterns
- Authentication guides
- Error handling
- Pagination
- Rate limiting

## Supported Languages

| Language | Library | Style |
|----------|---------|-------|
| Python | requests, httpx | Sync & async |
| JavaScript | fetch | Native ES6+ |
| TypeScript | axios | Typed client |
| Go | net/http | Idiomatic Go |
| cURL | - | Command line |

## License

MIT
