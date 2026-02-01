# Weather Toolkit - Example Skill

This is a **reference implementation** demonstrating best practices for creating Agent Bus skills.

## Quick Start

```bash
# Install the skill
agent-bus-skills install https://github.com/example/weather-toolkit weather-toolkit

# Or manually
cd skills/
git clone https://github.com/example/weather-toolkit weather-toolkit

# Verify installation
agent-bus-skills list
agent-bus-skills info weather-toolkit
```

## What This Example Demonstrates

### 1. Complete skill.json Metadata
- All required fields (name, version, description, author)
- Capability definitions with descriptions
- Tool requirements (required vs optional)
- Python dependencies with version constraints
- Entry point specification
- Repository and license info
- Custom metadata for API details

### 2. Comprehensive Documentation
- Clear overview and capabilities
- Implementation examples with code
- API integration details
- Best practices and limitations
- Testing instructions

### 3. Capability Mapping
This skill provides three capabilities that can be mapped to agent roles:
- `weather-query` → Support agents, QA agents (environmental testing)
- `weather-forecast` → Planning agents, PM agents
- `weather-analysis` → Data analysis agents, QA agents

### 4. Tool Requirements
Demonstrates both required and optional tool dependencies:
- `web_fetch` is **required** for core functionality
- `exec` is **optional** for advanced features

### 5. Dependency Management
Shows proper Python dependency specification:
```json
"dependencies": [
  {
    "name": "requests",
    "version": ">=2.28.0",
    "optional": false
  }
]
```

## File Structure

```
weather-toolkit/
├── skill.json          # Metadata (validated against schema)
├── skill.md            # Main prompt/documentation (entry point)
├── README.md           # This file
├── examples/           # Usage examples (optional)
├── tests/              # Test suite (optional)
└── assets/             # Additional resources (optional)
```

## Integration with Agent Bus

### Loading the Skill

```python
from src.skills import SkillsManager

manager = SkillsManager("./skills")
weather_skill = await manager.load_skill("weather-toolkit")

# Get the prompt
prompt = weather_skill.get_prompt()

# Access metadata
print(f"Capabilities: {weather_skill.capabilities}")
print(f"Tools needed: {weather_skill.required_tools}")
```

### Permission Control

```python
from src.skills import SkillAllowlistManager

# Allow QA agent to use weather capabilities
await allowlist_manager.add_allowlist_entry(
    agent_id="qa_agent",
    skill_name="weather-toolkit",
    allowed=True,
    notes="For environmental testing scenarios"
)

# Map capability to skill
await allowlist_manager.add_capability_mapping(
    capability="weather-query",
    skill_name="weather-toolkit",
    priority=10
)
```

### Agent Usage

```python
from src.agents.base import BaseAgent

class QAAgent(BaseAgent):
    def define_capabilities(self) -> dict:
        return {
            "testing": True,
            "weather-query": True  # Request weather capability
        }
    
    async def execute(self, task):
        # Load weather skill if allowed
        weather_skill = await self.load_skill("weather-toolkit")
        
        if weather_skill:
            # Use skill prompt in context
            prompt = f"{weather_skill.get_prompt()}\n\nTask: {task.input}"
            # ... execute with LLM
```

## Testing

This example includes comprehensive tests demonstrating:
- Skill loading and validation
- Capability mapping
- Permission enforcement
- Integration with agents

Run tests:
```bash
pytest tests/test_example_skill_integration.py -v
```

## Best Practices Illustrated

### ✅ DO
- Use semantic versioning (MAJOR.MINOR.PATCH)
- Provide clear capability descriptions
- Document all API integrations
- Specify minimum Python version
- Include implementation examples
- Add error handling guidance
- List known limitations

### ❌ DON'T
- Use generic capability names (be specific)
- Omit tool requirements (declare all dependencies)
- Skip version constraints (pin dependencies)
- Forget rate limits (document API constraints)
- Ignore error cases (handle failures gracefully)

## Creating Your Own Skill

Use this example as a template:

1. **Copy the structure**:
   ```bash
   cp -r skills/weather-toolkit skills/my-new-skill
   ```

2. **Update skill.json**:
   - Change name, description, author
   - Define your capabilities
   - List required tools
   - Specify dependencies

3. **Write skill.md**:
   - Explain what your skill does
   - Provide implementation examples
   - Document API usage
   - Include best practices

4. **Add tests**:
   - Test skill loading
   - Test capability mapping
   - Test agent integration

5. **Register the skill**:
   ```bash
   agent-bus-skills list  # Auto-discovers new skill
   ```

## Learning Resources

- [Skills System Documentation](../../docs/SKILLS_SYSTEM.md)
- [Skill Allowlist Guide](../../docs/SKILL_ALLOWLIST.md)
- [Agent Bus Architecture](../../README.md)

## License

MIT - Free to use as a template for your own skills
