# Skills System Documentation

## Quick Start: Example Skill

See `skills/weather-toolkit/` for a complete reference implementation demonstrating:
- ✅ Complete skill.json metadata with all fields
- ✅ Comprehensive documentation (skill.md)
- ✅ Capability definitions and tool requirements
- ✅ Python dependency specifications
- ✅ Integration tests with allowlist and capability mapping
- ✅ Best practices and patterns

**New to skills?** Start by reviewing the weather-toolkit example:
```bash
cat skills/weather-toolkit/skill.json
cat skills/weather-toolkit/README.md
pytest tests/test_example_skill_integration.py -v
```

## Overview

The Agent Bus Skills System provides a robust, pluggable framework for managing and executing Claude Skills. It includes:

- **JSON Schema-based registry format** for skill metadata validation
- **Automatic skill discovery** from the `skills/` directory
- **Hardened loader** with comprehensive error handling
- **Version compatibility checks** using semver
- **Git-based installation** for easy skill distribution

## Architecture

```
skills/
├── skill-name/
│   ├── skill.json          # Metadata (validated against schema)
│   ├── skill.md            # Main prompt (default entry point)
│   └── ...                 # Additional files
├── another-skill/
│   ├── skill.json
│   └── README.md           # Alternative entry point
└── skills.json             # Generated registry snapshot
```

### Components

1. **SkillMetadataSchema** (`src/skills/schema.py`)
   - Pydantic model for `skill.json` validation
   - Enforces semver versions, lowercase names, etc.

2. **SkillRegistry** (`src/skills/registry.py`)
   - Discovers and validates skills
   - Maintains in-memory registry
   - Provides filtering by capability/tag

3. **SkillsManager** (`src/skills/manager.py`)
   - Loads skill content on demand
   - Caches loaded skills
   - Handles git-based installation/updates

## Skill Metadata Format

### skill.json Schema

```json
{
  "name": "skill-name",
  "version": "1.0.0",
  "description": "Brief description of the skill",
  "author": "Author Name",
  "capabilities": [
    {
      "name": "capability-id",
      "description": "Human-readable description"
    }
  ],
  "required_tools": [
    {
      "name": "tool-name",
      "required": true
    }
  ],
  "dependencies": [
    {
      "name": "package-name",
      "version": ">=1.0.0",
      "optional": false
    }
  ],
  "entry_point": "skill.md",
  "min_python_version": "3.10",
  "repository": "https://github.com/user/skill",
  "license": "MIT",
  "tags": ["tag1", "tag2"],
  "metadata": {}
}
```

### Required Fields

- `name`: Lowercase, hyphenated skill identifier
- `version`: Semver version string (e.g., `1.2.3`)
- `description`: Brief description
- `author`: Author name or organization

### Optional Fields

- `capabilities`: List of capabilities provided by the skill
- `required_tools`: OpenClaw tools required (e.g., `browser`, `shell`)
- `dependencies`: Python package dependencies
- `entry_point`: Main prompt file (default: `skill.md`, `README.md`, `prompt.md`)
- `min_python_version`: Minimum Python version required
- `repository`: Git repository URL
- `license`: License identifier (e.g., `MIT`, `Apache-2.0`)
- `tags`: Tags for categorization and search
- `metadata`: Custom metadata dictionary

### Validation Rules

1. **Name**: Must be lowercase, alphanumeric with hyphens/underscores
2. **Version**: Must be valid semver (validated with `packaging` library)
3. **Python Version**: If specified, must be valid version string
4. **No Extra Fields**: Schema forbids additional fields not in spec

## CLI Commands

The Agent Bus Skills Manager provides a command-line interface for managing skills:

### Installation

```bash
# Install the CLI
poetry install

# Or use directly
python -m src.cli --help
```

### Commands

#### `install` - Install a skill from git

```bash
# Basic usage (auto-extracts name from URL)
agent-bus-skills install https://github.com/user/awesome-skill

# With custom name
agent-bus-skills install https://github.com/user/skill --name my-skill

# With custom skills directory
agent-bus-skills --skills-dir ./my-skills install https://github.com/user/skill
```

Features:
- Clones git repository to skills directory
- Validates skill structure (skill.json, entry point files)
- Registers skill in registry
- Shows installed skill info

#### `update` - Update an installed skill

```bash
# Update skill from its git repository
agent-bus-skills update my-skill

# Output:
# ✓ Successfully updated skill 'my-skill'
```

Features:
- Pulls latest changes from git
- Validates updated skill
- Clears cache for updated skill
- Reloads registry

#### `list` - List installed skills

```bash
# Basic list
agent-bus-skills list

# Output:
# Installed skills (2):
#   • ui-ux-pro-max (v1.0.0) - Professional UI/UX design system generator
#   • test-skill (v1.2.3) - Testing automation skill

# Verbose output
agent-bus-skills list --verbose

# Output includes:
# - Description
# - Author
# - Capabilities
# - Tags
```

#### `info` - Show detailed skill information

```bash
# Show all metadata for a skill
agent-bus-skills info ui-ux-pro-max

# Output:
# Skill: ui-ux-pro-max
# Version: 1.0.0
# Description: Professional UI/UX design system generator
# Author: ComposioHQ
# Path: /path/to/skills/ui-ux-pro-max
# Entry Point: skill.md
# Repository: https://github.com/ComposioHQ/awesome-claude-skills
# License: MIT
# Capabilities: ui-design, design-systems
# Required Tools: browser
# Tags: design, ui, ux, frontend
```

### Error Handling

The CLI provides clear error messages:

```bash
# Skill already exists
$ agent-bus-skills install https://github.com/user/skill
✗ Installation failed: Skill directory 'skill' already exists

# Invalid git URL
$ agent-bus-skills install https://invalid-url
✗ Installation failed: Git clone failed: ...

# Skill not found
$ agent-bus-skills update nonexistent
✗ Skill not found: Skill 'nonexistent' not found in registry

# Invalid skill format
$ agent-bus-skills install https://github.com/user/bad-skill
✗ Installation failed: Invalid skill: No entry point file found
```

## API Endpoints

The skills system provides REST API endpoints for programmatic access:

### `POST /api/skills/install` - Install a skill

Request:
```json
{
  "git_url": "https://github.com/user/skill-repo",
  "skill_name": "my-skill"  // optional, auto-extracted from URL
}
```

Response (201 Created):
```json
{
  "name": "my-skill",
  "version": "1.0.0",
  "description": "Skill description",
  "author": "Author Name",
  "capabilities": ["capability1"],
  "required_tools": ["browser"],
  "path": "/path/to/skills/my-skill",
  "repository": "https://github.com/user/skill-repo",
  "license": "MIT",
  "tags": ["tag1", "tag2"]
}
```

### `POST /api/skills/{skill_name}/update` - Update a skill

Response (200 OK):
```json
{
  "success": true,
  "message": "Skill 'my-skill' updated successfully"
}
```

### `GET /api/skills` - List all skills

Query parameters:
- `capability`: Filter by capability
- `tag`: Filter by tag

Response (200 OK):
```json
{
  "skills": [
    {
      "name": "skill1",
      "version": "1.0.0",
      ...
    }
  ],
  "total": 1
}
```

### `GET /api/skills/{skill_name}` - Get skill info

Response (200 OK):
```json
{
  "name": "my-skill",
  "version": "1.0.0",
  "description": "Skill description",
  ...
}
```

### `POST /api/skills/reload` - Reload registry

Response (200 OK):
```json
{
  "success": true,
  "message": "Registry reloaded. 5 skills found."
}
```

## Usage

### Discovery and Loading

```python
from src.skills import SkillsManager

# Initialize manager (automatically discovers skills)
manager = SkillsManager("./skills")

# Load a skill
skill = await manager.load_skill("ui-ux-pro-max")

# Get skill prompt
prompt = skill.get_prompt()

# Get capabilities
capabilities = skill.get_capabilities()
```

### Installation

#### Via CLI

```bash
# Install skill from GitHub
agent-bus-skills install https://github.com/user/skill-repo

# Install with custom name
agent-bus-skills install https://github.com/user/skill-repo --name my-skill

# Update installed skill
agent-bus-skills update my-skill

# List all installed skills
agent-bus-skills list

# Show detailed info
agent-bus-skills info my-skill
```

#### Via Python API

```python
# Install skill from GitHub
await manager.install_skill(
    git_url="https://github.com/user/skill-repo",
    skill_name="new-skill"
)

# Update existing skill
await manager.update_skill("ui-ux-pro-max")
```

#### Via REST API

```bash
# Install skill
curl -X POST http://localhost:8000/api/skills/install \
  -H "Content-Type: application/json" \
  -d '{"git_url": "https://github.com/user/skill-repo", "skill_name": "my-skill"}'

# Update skill
curl -X POST http://localhost:8000/api/skills/my-skill/update

# List skills
curl http://localhost:8000/api/skills

# Get skill info
curl http://localhost:8000/api/skills/my-skill

# Reload registry
curl -X POST http://localhost:8000/api/skills/reload
```

### Querying Skills

```python
# List all skills
skills = manager.list_skills()

# Get skill info
info = manager.get_skill_info("skill-name")

# Filter by capability
testing_skills = manager.get_skills_by_capability("testing")

# Filter by tag
automation_skills = manager.get_skills_by_tag("automation")
```

### Execution

```python
# Execute skill (returns prompt content)
prompt = await manager.execute_skill(
    skill_name="ui-ux-pro-max",
    context={"project": "dashboard"}
)

# Pass to LLM
response = await llm.generate(prompt, context)
```

## Error Handling

The skills system provides robust error handling:

### SkillRegistryError
Base exception for registry errors.

### SkillValidationError
Raised when skill.json validation fails:
- Invalid JSON syntax
- Schema validation errors
- Missing required fields

### SkillNotFoundError
Raised when requesting a non-existent skill.

### SkillLoadError
Raised when skill content cannot be loaded:
- No entry point files found
- Empty content files
- File read errors

### Example Error Handling

```python
from src.skills import (
    SkillsManager,
    SkillNotFoundError,
    SkillLoadError,
    SkillValidationError
)

try:
    skill = await manager.load_skill("my-skill")
except SkillNotFoundError:
    print("Skill not found in registry")
except SkillLoadError as e:
    print(f"Failed to load skill content: {e}")
except SkillValidationError as e:
    print(f"Skill validation failed: {e}")
```

## Hardening Features

### 1. Schema Validation
- All `skill.json` files validated against Pydantic schema
- Invalid skills logged but don't crash the system
- Fallback to basic metadata if validation fails

### 2. Entry Point Discovery
- Tries multiple entry point files in priority order:
  1. Custom `entry_point` from skill.json
  2. `skill.md`
  3. `README.md`
  4. `prompt.md`
- Skips empty files
- Logs warnings for empty content

### 3. Error Recovery
- Registry loading continues even if individual skills fail
- Detailed error logging for debugging
- Validation errors don't prevent other skills from loading

### 4. Cache Management
- Loaded skills cached in memory
- Cache invalidated on registry reload
- Cache cleared after skill updates

### 5. Directory Validation
- Validates skill directory structure before registration
- Checks for required entry point files
- Validates skill.json syntax and schema

### 6. Git Operations
- Timeouts on git clone/pull (60s/30s)
- Comprehensive error handling
- Automatic cleanup on failed installations

## Creating a Skill

### 1. Create Skill Directory

```bash
mkdir -p skills/my-skill
cd skills/my-skill
```

### 2. Create skill.json

```json
{
  "name": "my-skill",
  "version": "1.0.0",
  "description": "My awesome skill",
  "author": "Your Name",
  "capabilities": [
    {
      "name": "my-capability",
      "description": "What this skill does"
    }
  ],
  "required_tools": [
    {
      "name": "browser",
      "required": true
    }
  ],
  "tags": ["category1", "category2"]
}
```

### 3. Create skill.md

```markdown
# My Skill

You are an expert at doing X, Y, and Z.

## Instructions

1. First step
2. Second step
3. Final step

## Examples

...
```

### 4. Test Locally

```python
from src.skills import SkillsManager

manager = SkillsManager("./skills")
skill = await manager.load_skill("my-skill")
print(skill.get_prompt())
```

### 5. Publish to Git

```bash
git init
git add .
git commit -m "Initial skill"
git remote add origin https://github.com/user/my-skill
git push -u origin main
```

### 6. Install from Git

```python
await manager.install_skill(
    "https://github.com/user/my-skill",
    "my-skill"
)
```

## Testing

The skills system includes comprehensive test coverage:

- **Schema validation tests** (`tests/test_skills_registry.py`)
  - Valid/invalid metadata
  - Version validation
  - Name validation
  - Extra fields handling

- **Registry tests**
  - Discovery and loading
  - Error handling
  - Fallback behavior
  - Filtering by capability/tag

- **Manager tests** (`tests/test_skills_manager.py`)
  - Loading and caching
  - Installation/updates
  - Error scenarios
  - Git operations

- **CLI tests** (`tests/test_cli.py`)
  - Install command (success, auto-name, errors)
  - Update command
  - List command (basic, verbose)
  - Info command
  - Name extraction
  - Error handling

- **API tests** (`tests/test_api_skills.py`)
  - Install endpoint
  - Update endpoint
  - List endpoint (with filters)
  - Get skill endpoint
  - Reload endpoint
  - Error responses

### Running Tests

```bash
# All skills tests
pytest tests/test_skills_*.py tests/test_cli.py tests/test_api_skills.py -v

# Specific test file
pytest tests/test_skills_registry.py -v

# CLI tests only
pytest tests/test_cli.py -v

# API tests only
pytest tests/test_api_skills.py -v

# Single test
pytest tests/test_skills_registry.py::TestSkillRegistry::test_load_skill_with_valid_metadata -v
```

## Registry Persistence

The registry can be persisted to `skills/skills.json`:

```python
# Save current registry state
manager.registry.save_registry()
```

This creates a snapshot with:
- Registry format version
- All registered skills with metadata
- Last update timestamp

Example `skills.json`:

```json
{
  "version": "1.0.0",
  "updated_at": "2026-02-01T20:00:00Z",
  "skills": {
    "ui-ux-pro-max": {
      "name": "ui-ux-pro-max",
      "version": "1.0.0",
      "description": "Professional UI/UX design system generator",
      "author": "ComposioHQ",
      ...
    }
  }
}
```

## Future Enhancements

1. **Per-agent allowlists** (KAN-57)
   - Restrict which skills each agent can use
   - Capability-based access control

2. **Hot reloading**
   - Watch skills directory for changes
   - Auto-reload on file modifications

3. **Skill versioning**
   - Support multiple versions simultaneously
   - Version constraints and compatibility checks

4. **Remote registries**
   - Fetch skills from remote registries
   - Version resolution and dependency management

5. **Context templating**
   - Template variables in skill prompts
   - Dynamic context injection

6. **Skill composition**
   - Combine multiple skills
   - Skill dependencies and chaining

## References

- [ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills)
- [karanb192/awesome-claude-skills](https://github.com/karanb192/awesome-claude-skills)
- Jira Epic: KAN-34 (Skills system)
- Related tasks: KAN-55, KAN-56, KAN-57, KAN-58
