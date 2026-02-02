# Security & OWASP Skill

A comprehensive security skill based on OWASP guidelines for vulnerability assessment and secure development.

## Overview

This skill enhances the Security Agent with:
- OWASP Top 10 (2021) vulnerability detection
- STRIDE threat modeling methodology
- Secure coding practices and patterns
- Structured security review output

## Capabilities

| Capability | Description |
|------------|-------------|
| `vulnerability-assessment` | Identify vulnerabilities using OWASP Top 10 |
| `threat-modeling` | STRIDE-based threat analysis |
| `secure-coding` | Apply secure coding practices |
| `security-review` | Conduct reviews with remediation guidance |

## Usage

```python
from src.skills import SkillsManager

manager = SkillsManager("./skills")
skill = await manager.load_skill("security-owasp")

# Use with security agent
prompt = skill.get_prompt()
```

## Integration with Security Agent

```python
# In security_agent.py
class SecurityAgent(BaseAgent):
    async def execute(self, task):
        security_skill = await self.load_skill("security-owasp")

        prompt = f"""
        {security_skill.get_prompt()}

        Review the following for security vulnerabilities:
        {task.input['code_or_architecture']}
        """

        response = await self.query_llm(prompt=prompt)
        return AgentResult(...)
```

## Topics Covered

### OWASP Top 10 (2021)
- A01: Broken Access Control
- A02: Cryptographic Failures
- A03: Injection
- A04: Insecure Design
- A05: Security Misconfiguration
- A06: Vulnerable Components
- A07: Authentication Failures
- A08: Integrity Failures
- A09: Logging Failures
- A10: SSRF

### Additional Coverage
- STRIDE threat modeling
- Secure coding checklists
- Security headers
- Password policies
- Session management

## License

MIT
