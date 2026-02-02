# System Architecture Skill

A comprehensive skill for designing cloud-native, scalable system architectures.

## Overview

This skill enhances the Architect Agent with:
- Cloud platform expertise (AWS, GCP, Azure)
- Microservices design patterns
- Scalability and resilience patterns
- Data architecture guidance

## Capabilities

| Capability | Description |
|------------|-------------|
| `cloud-architecture` | Design cloud-native architectures for major providers |
| `microservices-design` | Service decomposition and communication patterns |
| `scalability-patterns` | Horizontal scaling, caching, load balancing |
| `data-architecture` | Database selection, data pipelines, storage strategies |

## Usage

```python
from src.skills import SkillsManager

manager = SkillsManager("./skills")
skill = await manager.load_skill("system-architecture")

# Use with architect agent
prompt = skill.get_prompt()
```

## Integration with Architect Agent

```python
# In architect_agent.py
class ArchitectAgent(BaseAgent):
    async def execute(self, task):
        arch_skill = await self.load_skill("system-architecture")

        prompt = f"""
        {arch_skill.get_prompt()}

        Design the system architecture for:
        {task.input['requirements']}
        """

        response = await self.query_llm(prompt=prompt)
        return AgentResult(...)
```

## Topics Covered

- AWS/GCP/Azure reference architectures
- 3-tier web applications
- Event-driven architectures
- Microservices patterns (DDD, Saga, CQRS)
- Resilience patterns (Circuit Breaker, Bulkhead)
- Caching strategies
- Database selection guide
- Architecture Decision Records (ADR)

## License

MIT
