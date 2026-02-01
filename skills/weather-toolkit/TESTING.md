# Testing the Weather Toolkit Example Skill

This document describes how to test and validate the weather-toolkit example skill.

## Quick Validation

### 1. Structure Check
```bash
cd /home/bot/clawd/agent_bus
ls -la skills/weather-toolkit/
# Should show: skill.json, skill.md, README.md, TESTING.md
```

### 2. JSON Validation
```bash
python3 -c "import json; json.load(open('skills/weather-toolkit/skill.json')); print('✓ Valid JSON')"
```

### 3. Schema Validation
```bash
# With dependencies installed:
python3 << 'EOF'
import json
from pathlib import Path
from src.skills.schema import SkillMetadataSchema

data = json.load(open('skills/weather-toolkit/skill.json'))
skill = SkillMetadataSchema(**data)
print(f'✓ Valid schema: {skill.name} v{skill.version}')
EOF
```

## Integration Tests

### Run All Example Skill Tests
```bash
pytest tests/test_example_skill_integration.py -v
```

### Run Specific Test Classes
```bash
# Test skill loading
pytest tests/test_example_skill_integration.py::TestExampleSkillLoading -v

# Test capability mapping
pytest tests/test_example_skill_integration.py::TestCapabilityMapping -v

# Test permissions
pytest tests/test_example_skill_integration.py::TestPermissionEnforcement -v

# End-to-end workflow
pytest tests/test_example_skill_integration.py::TestEndToEndWorkflow -v
```

## What the Tests Verify

### TestExampleSkillLoading (6 tests)
- ✅ Skill loads successfully
- ✅ All capabilities are properly defined
- ✅ Tool requirements are correct (required vs optional)
- ✅ Python dependencies are specified
- ✅ Metadata is complete (version, license, tags, etc.)
- ✅ Prompt content loads from skill.md

### TestCapabilityMapping (3 tests)
- ✅ Weather capabilities map to weather-toolkit
- ✅ Capability priority ordering works
- ✅ Multiple skills can provide same capability

### TestPermissionEnforcement (4 tests)
- ✅ Agent can be allowed to use skill
- ✅ Agent can be denied access to skill
- ✅ Wildcard (*) grants access to all skills
- ✅ Specific deny overrides wildcard allow

### TestSkillsManagerIntegration (3 tests)
- ✅ Skills load with permission checks
- ✅ Loading fails without permission (SkillPermissionError)
- ✅ Backward compatibility (no allowlist = allow all)

### TestEndToEndWorkflow (1 test)
- ✅ Complete workflow:
  1. Load example skill
  2. Configure capability mappings
  3. Set up agent permissions
  4. Agent discovers skill via capability
  5. Agent loads and uses skill

### TestDocumentationQuality (3 tests)
- ✅ All important metadata fields present
- ✅ Capabilities have meaningful descriptions
- ✅ Prompt includes usage examples

## Expected Test Results

```
tests/test_example_skill_integration.py::TestExampleSkillLoading::test_load_weather_toolkit PASSED
tests/test_example_skill_integration.py::TestExampleSkillLoading::test_example_skill_capabilities PASSED
tests/test_example_skill_integration.py::TestExampleSkillLoading::test_example_skill_tools PASSED
tests/test_example_skill_integration.py::TestExampleSkillLoading::test_example_skill_dependencies PASSED
tests/test_example_skill_integration.py::TestExampleSkillLoading::test_example_skill_metadata PASSED
tests/test_example_skill_integration.py::TestExampleSkillLoading::test_example_skill_prompt PASSED
tests/test_example_skill_integration.py::TestCapabilityMapping::test_map_weather_capabilities PASSED
tests/test_example_skill_integration.py::TestCapabilityMapping::test_capability_priority_ordering PASSED
tests/test_example_skill_integration.py::TestCapabilityMapping::test_multiple_skills_per_capability PASSED
tests/test_example_skill_integration.py::TestPermissionEnforcement::test_allow_agent_weather_skill PASSED
tests/test_example_skill_integration.py::TestPermissionEnforcement::test_deny_agent_weather_skill PASSED
tests/test_example_skill_integration.py::TestPermissionEnforcement::test_wildcard_skill_access PASSED
tests/test_example_skill_integration.py::TestPermissionEnforcement::test_specific_override_wildcard PASSED
tests/test_example_skill_integration.py::TestSkillsManagerIntegration::test_load_skill_with_permission PASSED
tests/test_example_skill_integration.py::TestSkillsManagerIntegration::test_load_skill_without_permission PASSED
tests/test_example_skill_integration.py::TestSkillsManagerIntegration::test_load_skill_no_allowlist PASSED
tests/test_example_skill_integration.py::TestEndToEndWorkflow::test_complete_weather_skill_workflow PASSED
tests/test_example_skill_integration.py::TestDocumentationQuality::test_skill_has_complete_metadata PASSED
tests/test_example_skill_integration.py::TestDocumentationQuality::test_capabilities_have_descriptions PASSED
tests/test_example_skill_integration.py::TestDocumentationQuality::test_prompt_has_usage_examples PASSED

======================== 20 passed in X.XXs ========================
```

## Manual Testing

### 1. Load Skill with SkillsManager
```python
from src.skills import SkillsManager

manager = SkillsManager("./skills")
skill = await manager.load_skill("weather-toolkit")

print(f"Loaded: {skill.name} v{skill.version}")
print(f"Capabilities: {[c.name for c in skill.capabilities]}")
print(f"Prompt length: {len(skill.get_prompt())} chars")
```

### 2. Test Capability Mapping
```python
from src.skills import SkillAllowlistManager
import asyncpg

pool = await asyncpg.create_pool(...)  # Your DB config
manager = SkillAllowlistManager(pool)

# Map capability
await manager.add_capability_mapping(
    capability="weather-query",
    skill_name="weather-toolkit",
    priority=10
)

# Query
skills = await manager.get_skills_for_capability("weather-query")
print(f"Skills with weather-query: {skills}")
```

### 3. Test Permission System
```python
# Allow agent
await manager.add_allowlist_entry(
    agent_id="qa_agent",
    skill_name="weather-toolkit",
    allowed=True
)

# Check permission
allowed = await manager.check_permission("qa_agent", "weather-toolkit")
print(f"qa_agent allowed: {allowed}")

# Deny agent
await manager.add_allowlist_entry(
    agent_id="restricted_agent",
    skill_name="weather-toolkit",
    allowed=False
)

allowed = await manager.check_permission("restricted_agent", "weather-toolkit")
print(f"restricted_agent allowed: {allowed}")
```

## CI/CD Integration

### GitHub Actions
```yaml
- name: Test Example Skill
  run: |
    pytest tests/test_example_skill_integration.py -v --cov=src/skills
```

### Pre-commit Hook
```bash
#!/bin/bash
# Validate all skills before commit
python3 -c "
import json
from pathlib import Path
for skill_json in Path('skills').glob('*/skill.json'):
    data = json.load(open(skill_json))
    print(f'✓ {data[\"name\"]} v{data[\"version\"]}')
"
```

## Troubleshooting

### Test Failures

**DatabaseError: connection refused**
- Solution: Ensure PostgreSQL is running (`docker compose up postgres`)

**SkillLoadError: skill.md not found**
- Solution: Check entry_point in skill.json matches actual file

**ValidationError: Invalid semver**
- Solution: Use semantic versioning (MAJOR.MINOR.PATCH)

### Common Issues

**ImportError: No module named 'src.skills'**
- Solution: Run tests from repo root: `cd /home/bot/clawd/agent_bus && pytest`

**Permission denied on skills directory**
- Solution: Check file permissions: `chmod -R u+w skills/`

## Best Practices Demonstrated

1. **Comprehensive Metadata**: All fields populated in skill.json
2. **Clear Capabilities**: Descriptive capability names and descriptions
3. **Tool Declaration**: Both required and optional tools specified
4. **Dependency Management**: Exact version constraints for dependencies
5. **Documentation**: README.md explains structure and integration
6. **Testing**: 20 tests covering all aspects of skills system
7. **Examples**: Real-world usage examples in skill.md

## Next Steps

After testing this example:
1. Use as template for new skills (`cp -r skills/weather-toolkit skills/my-skill`)
2. Update skill.json with your metadata
3. Write your skill.md prompt
4. Add tests in tests/test_my_skill.py
5. Submit PR with new skill

## Resources

- [Skills System Docs](../../docs/SKILLS_SYSTEM.md)
- [Allowlist Guide](../../docs/SKILL_ALLOWLIST.md)
- [Example Skill README](./README.md)
