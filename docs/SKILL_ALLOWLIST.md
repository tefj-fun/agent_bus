# Skill Allowlist and Capability Mapping

## Overview

The skill allowlist system provides fine-grained control over which agents can use which skills, along with capability-based skill discovery.

### Key Features

- **Per-agent skill permissions**: Control which skills each agent can access
- **Capability-based discovery**: Agents request capabilities, system returns matching permitted skills
- **Wildcard support**: Use `*` to allow/deny all skills by default
- **Priority-based skill selection**: Multiple skills can provide the same capability with priority ordering
- **Backward compatibility**: Agents without allowlist entries have full access (default allow-all)
- **Database-backed configuration**: All settings persisted in PostgreSQL
- **YAML configuration**: Import/export allowlists via YAML files

## Architecture

### Database Schema

```sql
-- Agent skill allowlist
CREATE TABLE agent_skill_allowlist (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(100) NOT NULL,
    skill_name VARCHAR(255) NOT NULL,  -- skill name or '*' for wildcard
    allowed BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(255),
    notes TEXT,
    UNIQUE(agent_id, skill_name)
);

-- Capability to skill mapping
CREATE TABLE capability_skill_mapping (
    id SERIAL PRIMARY KEY,
    capability_name VARCHAR(255) NOT NULL,
    skill_name VARCHAR(255) NOT NULL,
    priority INTEGER DEFAULT 10,  -- Lower = higher priority
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(capability_name, skill_name)
);
```

### Components

1. **SkillAllowlistManager** (`src/skills/allowlist.py`)
   - Permission checking and enforcement
   - Capability-to-skill mapping
   - Caching for performance

2. **SkillsManager** (updated)
   - Integrates permission checks when loading skills
   - Capability-based skill discovery
   - Agent-aware skill loading

3. **BaseAgent** (updated)
   - Permission-aware skill loading
   - Capability-based skill discovery methods
   - Graceful permission enforcement

4. **AllowlistConfigLoader** (`src/skills/config_loader.py`)
   - YAML import/export
   - Bulk configuration updates

## Usage

### Agent Code

```python
from src.agents.base import BaseAgent
from src.skills import SkillPermissionError

class MyAgent(BaseAgent):
    def get_agent_id(self) -> str:
        return "my_agent"
    
    async def my_task(self):
        # Load skill with permission check
        try:
            skill = await self.load_skill("code-analyzer")
            # Use skill...
        except SkillPermissionError as e:
            self.log_event("error", f"Permission denied: {e}")
            return
        
        # Find skills by capability
        testing_skills = await self.find_skills_by_capability("testing")
        if testing_skills:
            # Use highest priority skill
            skill = await self.load_skill(testing_skills[0])
        
        # Get all allowed skills
        allowed = await self.get_allowed_skills()
        print(f"I can use: {allowed}")
```

### Direct Allowlist Management

```python
from src.skills.allowlist import SkillAllowlistManager

manager = SkillAllowlistManager(db_pool)

# Add permission entry
await manager.add_allowlist_entry(
    agent_id="security_agent",
    skill_name="security-audit",
    allowed=True,
    notes="Primary security tool"
)

# Deny a skill
await manager.add_allowlist_entry(
    agent_id="qa_agent",
    skill_name="dangerous-tool",
    allowed=False,
    notes="Security restriction"
)

# Wildcard: deny all by default
await manager.add_allowlist_entry(
    agent_id="restricted_agent",
    skill_name="*",
    allowed=False
)

# Check permission
if await manager.check_permission("my_agent", "some-skill"):
    print("Allowed!")

# Enforce (raises exception if denied)
await manager.enforce_permission("my_agent", "some-skill")
```

### Capability Mapping

```python
# Add capability mapping
await manager.add_capability_mapping(
    capability_name="ui-design",
    skill_name="figma-pro",
    priority=1,  # Highest priority
    metadata={"version": "2.0", "framework": "figma"}
)

await manager.add_capability_mapping(
    capability_name="ui-design",
    skill_name="simple-ui",
    priority=10,  # Lower priority fallback
    metadata={"framework": "basic"}
)

# Find skills for capability
skills = await manager.get_skills_by_capability("ui-design")
# Returns: ["figma-pro", "simple-ui"] (ordered by priority)

# Find skills filtered by agent permissions
skills = await manager.get_skills_by_capability(
    "ui-design",
    agent_id="uiux_agent"
)
# Returns only skills that uiux_agent is allowed to use
```

### YAML Configuration

Create `config/skill_allowlist.yaml`:

```yaml
agent_allowlists:
  developer_agent:
    - skill: "*"
      allowed: true
      notes: "Full access for developers"
  
  security_agent:
    - skill: "security-audit"
      allowed: true
    - skill: "vulnerability-scan"
      allowed: true
    - skill: "*"
      allowed: false
      notes: "Restricted to security tools only"
  
  qa_agent:
    - skill: "pytest-gen"
      allowed: true
    - skill: "coverage-tool"
      allowed: true
    - skill: "*"
      allowed: false

capability_mappings:
  testing:
    - skill: "pytest-gen"
      priority: 1
      metadata:
        framework: "pytest"
    - skill: "jest-gen"
      priority: 5
      metadata:
        framework: "jest"
  
  security:
    - skill: "security-audit"
      priority: 1
    - skill: "vulnerability-scan"
      priority: 2
  
  ui-design:
    - skill: "figma-pro"
      priority: 1
    - skill: "sketch-tool"
      priority: 5
```

Load configuration:

```python
from src.skills.config_loader import AllowlistConfigLoader

loader = AllowlistConfigLoader(db_pool)

# Load from YAML (merge with existing)
stats = await loader.load_from_yaml("config/skill_allowlist.yaml")
print(f"Loaded {stats['allowlist_entries']} entries")

# Load and replace all existing entries
stats = await loader.load_from_yaml(
    "config/skill_allowlist.yaml",
    clear_existing=True
)

# Export current config to YAML
await loader.export_to_yaml("config/exported_allowlist.yaml")
```

## Permission Logic

### Resolution Order

When checking if agent `A` can use skill `S`:

1. Check for explicit entry: `(agent_id=A, skill_name=S)`
   - If found: return `allowed` value
   
2. Check for wildcard entry: `(agent_id=A, skill_name='*')`
   - If found: return `allowed` value
   
3. Default: return `True` (backward compatibility)

### Examples

**Example 1: Wildcard deny with specific allows**
```
agent_skill_allowlist:
  agent_id: "security_agent"
  skill_name: "*"
  allowed: false

  agent_id: "security_agent"
  skill_name: "security-audit"
  allowed: true

  agent_id: "security_agent"
  skill_name: "vulnerability-scan"
  allowed: true

Result:
- security-audit: ALLOWED (explicit)
- vulnerability-scan: ALLOWED (explicit)
- any-other-skill: DENIED (wildcard)
```

**Example 2: No entries (default allow-all)**
```
agent_skill_allowlist:
  (empty)

Result:
- any-skill: ALLOWED (default)
```

**Example 3: Wildcard allow**
```
agent_skill_allowlist:
  agent_id: "developer_agent"
  skill_name: "*"
  allowed: true

Result:
- any-skill: ALLOWED (wildcard)
```

## Capability-Based Discovery

### Flow

1. Agent requests a capability (e.g., "testing")
2. System queries `capability_skill_mapping` for matching skills
3. Results are filtered by agent's allowlist
4. Skills returned in priority order (lower priority number = higher precedence)

### Example

```python
# Setup: capability_skill_mapping
"testing" -> ["pytest-gen" (priority=1), "jest-gen" (priority=5), "mocha" (priority=10)]

# Setup: qa_agent allowlist
qa_agent can use: ["pytest-gen", "jest-gen"]
qa_agent cannot use: ["mocha"]

# Query
skills = await manager.get_skills_by_capability("testing", agent_id="qa_agent")

# Result
["pytest-gen", "jest-gen"]  # mocha filtered out, ordered by priority
```

## Caching

The allowlist manager uses in-memory caching for performance:

- Permission checks are cached per agent+skill
- Capability mappings are cached per capability
- Cache is automatically invalidated on updates

Manual cache control:

```python
# Clear all caches
manager.clear_cache()
```

## Migration

Run the migration to create tables:

```bash
psql -U agent_bus -d agent_bus -f scripts/migrations/001_add_skill_allowlists.sql
```

Or via Python:

```python
async with db_pool.acquire() as conn:
    with open('scripts/migrations/001_add_skill_allowlists.sql', 'r') as f:
        await conn.execute(f.read())
```

## Security Considerations

1. **Principle of least privilege**: Use wildcard deny (`*: false`) and explicit allows
2. **Audit trail**: Allowlist entries include `created_by` and `notes` fields
3. **Isolation**: Each agent has independent allowlist
4. **Bypass protection**: Permission checks are enforced in SkillsManager, not just BaseAgent

## Performance

- Allowlist checks: O(1) with caching, single DB query without cache
- Capability lookup: O(1) for cache hit, single DB query for miss
- Cache invalidation: Automatic on updates, manual via `clear_cache()`

## Testing

Run tests:

```bash
# Allowlist tests
pytest tests/test_skill_allowlist.py -v

# Config loader tests
pytest tests/test_allowlist_config_loader.py -v

# Agent integration tests
pytest tests/test_agent_skill_permissions.py -v

# All skill-related tests
pytest tests/test_skill*.py tests/test_allowlist*.py tests/test_agent_skill*.py -v
```

## Troubleshooting

### Agent can't load skill despite allowlist entry

1. Check cache: `manager.clear_cache()`
2. Verify entry: `SELECT * FROM agent_skill_allowlist WHERE agent_id = '...'`
3. Check agent_id matches: Ensure `agent.get_agent_id()` returns expected value

### Capability returns no skills

1. Check mapping exists: `SELECT * FROM capability_skill_mapping WHERE capability_name = '...'`
2. Check agent permissions: `await manager.get_skills_by_capability(capability, agent_id=None)` to see unfiltered results
3. Verify skill names match registry

### YAML import fails

1. Validate YAML syntax: `python -c "import yaml; yaml.safe_load(open('config.yaml'))"`
2. Check field names: `skill`, `allowed`, `notes`, `priority`, `metadata`
3. Review logs for specific error messages

## Future Enhancements

- [ ] Time-based permissions (expire after date)
- [ ] Request/approval workflow for skill access
- [ ] Usage auditing and analytics
- [ ] Role-based permissions (agent groups)
- [ ] Dynamic permission updates via API
- [ ] Permission inheritance hierarchies
