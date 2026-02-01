# Skills Installation Guide

This guide covers installing and managing skills in the Agent Bus system.

## Quick Start

```bash
# Install a skill
agent-bus-skills install https://github.com/user/awesome-skill

# List installed skills
agent-bus-skills list

# Get skill details
agent-bus-skills info awesome-skill

# Update a skill
agent-bus-skills update awesome-skill
```

## Installation Methods

### 1. CLI (Recommended)

The CLI provides the easiest way to install skills:

```bash
# Basic installation
agent-bus-skills install https://github.com/ComposioHQ/awesome-claude-skills

# With custom name
agent-bus-skills install https://github.com/user/skill --name my-custom-name

# Custom skills directory
agent-bus-skills --skills-dir /path/to/skills install https://github.com/user/skill
```

**Features:**
- ✓ Auto-extracts skill name from repository URL
- ✓ Validates skill structure before registration
- ✓ Shows detailed install progress and errors
- ✓ Displays installed skill information

### 2. REST API

For programmatic installation:

```bash
curl -X POST http://localhost:8000/api/skills/install \
  -H "Content-Type: application/json" \
  -d '{
    "git_url": "https://github.com/user/skill-repo",
    "skill_name": "my-skill"
  }'
```

**Response:**
```json
{
  "name": "my-skill",
  "version": "1.0.0",
  "description": "Skill description",
  "author": "Author Name",
  "capabilities": ["capability1", "capability2"],
  "required_tools": ["browser"],
  "path": "/path/to/skills/my-skill",
  "repository": "https://github.com/user/skill-repo",
  "license": "MIT",
  "tags": ["tag1", "tag2"]
}
```

### 3. Python API

For integration in Python code:

```python
from src.skills import SkillsManager

manager = SkillsManager("./skills")

# Install skill
await manager.install_skill(
    git_url="https://github.com/user/skill-repo",
    skill_name="my-skill"
)

# Get info about installed skill
info = manager.get_skill_info("my-skill")
print(f"Installed: {info.name} v{info.version}")
```

## Installation Process

When you install a skill, the system:

1. **Validates the URL** - Ensures it's a valid git repository
2. **Clones the repository** - Uses `git clone` to download the skill
3. **Validates skill structure** - Checks for:
   - Valid `skill.json` (if present)
   - At least one entry point file (`skill.md`, `README.md`, or `prompt.md`)
   - Correct directory structure
4. **Registers the skill** - Adds it to the registry
5. **Saves registry** - Persists to `skills/skills.json`

If any step fails, the installation is rolled back (cloned directory is removed).

## Validation Rules

### Directory Structure

A valid skill must have:
```
skill-name/
├── skill.json          # Metadata (optional but recommended)
└── skill.md            # Prompt content (or README.md/prompt.md)
```

### skill.json Format

If present, `skill.json` must be valid JSON matching the schema:

```json
{
  "name": "skill-name",           // Required: lowercase, hyphenated
  "version": "1.0.0",             // Required: semver format
  "description": "Description",   // Required
  "author": "Author Name",        // Required
  "capabilities": [               // Optional
    {"name": "capability-id", "description": "..."}
  ],
  "required_tools": [             // Optional
    {"name": "browser", "required": true}
  ],
  "tags": ["tag1", "tag2"]        // Optional
}
```

## Error Handling

### Common Errors

#### Skill Already Exists
```bash
$ agent-bus-skills install https://github.com/user/skill
✗ Installation failed: Skill directory 'skill' already exists
```

**Solution:** Use a different name or remove the existing skill first.

#### Invalid Git URL
```bash
$ agent-bus-skills install https://invalid-url
✗ Installation failed: Git clone failed: repository not found
```

**Solution:** Verify the repository URL is correct and accessible.

#### Invalid Skill Format
```bash
$ agent-bus-skills install https://github.com/user/bad-skill
✗ Installation failed: Invalid skill: No entry point file found
```

**Solution:** Ensure the repository contains `skill.md`, `README.md`, or `prompt.md`.

#### Invalid skill.json
```bash
✗ Installation failed: Invalid skill: Invalid JSON in skill.json: ...
```

**Solution:** Fix the JSON syntax in `skill.json`.

#### Git Clone Timeout
```bash
✗ Installation failed: Git clone operation timed out
```

**Solution:** Check network connection or try again later.

## Managing Installed Skills

### List Skills

```bash
# Basic list
agent-bus-skills list

# Verbose output with all metadata
agent-bus-skills list --verbose
```

### Get Skill Info

```bash
agent-bus-skills info skill-name
```

Shows:
- Name, version, description
- Author and license
- Capabilities and required tools
- Tags and dependencies
- Repository URL
- Local path

### Update Skills

```bash
# Update a specific skill
agent-bus-skills update skill-name

# Update pulls latest changes from git
```

### Filter Skills

**By capability (API only):**
```bash
curl http://localhost:8000/api/skills?capability=ui-design
```

**By tag (API only):**
```bash
curl http://localhost:8000/api/skills?tag=automation
```

## Best Practices

### 1. Use Version Control

Always install skills from version-controlled repositories (GitHub, GitLab, etc.) for:
- Reproducibility
- Easy updates
- Version tracking

### 2. Review Before Installing

Before installing a skill:
- Check the repository contents
- Read the skill.json metadata
- Review capabilities and required tools
- Verify the author and license

### 3. Name Skills Consistently

Use lowercase, hyphenated names:
- ✓ `ui-ux-designer`
- ✓ `code-reviewer`
- ✗ `UI_UX_Designer`
- ✗ `CodeReviewer`

### 4. Keep Skills Updated

Periodically update installed skills:
```bash
agent-bus-skills list | grep "v" | cut -d' ' -f2 | xargs -I {} agent-bus-skills update {}
```

### 5. Document Custom Skills

If creating custom skills, include:
- Complete skill.json metadata
- Clear README.md with usage examples
- Required tools and dependencies
- Version history in CHANGELOG.md

## Advanced Usage

### Custom Skills Directory

```bash
# Use a different skills directory
agent-bus-skills --skills-dir /custom/path install https://github.com/user/skill
```

### Skill Name Extraction

The CLI auto-extracts skill names from URLs:

- `https://github.com/user/awesome-skill` → `awesome-skill`
- `https://github.com/user/my_skill.git` → `my-skill`
- `https://gitlab.com/org/Cool_Skill` → `cool-skill`

To override, use `--name`:
```bash
agent-bus-skills install https://github.com/user/skill --name custom-name
```

### Registry Management

```bash
# Reload registry from disk (API)
curl -X POST http://localhost:8000/api/skills/reload
```

This re-scans the skills directory and updates the in-memory registry.

## Troubleshooting

### Skill Not Loading

If a skill installs but doesn't load:

1. **Check logs:**
   ```bash
   # Enable debug logging
   export LOG_LEVEL=DEBUG
   agent-bus-skills info skill-name
   ```

2. **Validate manually:**
   ```python
   from src.skills import SkillRegistry
   registry = SkillRegistry("./skills")
   is_valid, error = registry.validate_skill_directory("./skills/skill-name")
   print(f"Valid: {is_valid}, Error: {error}")
   ```

3. **Reload registry:**
   ```python
   manager.reload_registry()
   ```

### Git Authentication Issues

For private repositories:

1. **Use SSH URLs:**
   ```bash
   agent-bus-skills install git@github.com:user/private-skill.git
   ```

2. **Set up SSH keys:**
   ```bash
   ssh-add ~/.ssh/id_rsa
   ```

3. **Or use HTTPS with credentials:**
   ```bash
   git config --global credential.helper store
   ```

### Skill Conflicts

If two skills have the same name:
- The CLI prevents installation
- Rename one skill using `--name`
- Or remove the existing skill first

## Examples

### Install from GitHub

```bash
agent-bus-skills install https://github.com/ComposioHQ/awesome-claude-skills
```

### Install with Custom Name

```bash
agent-bus-skills install https://github.com/karanb192/awesome-claude-skills --name ui-designer
```

### List All Skills

```bash
$ agent-bus-skills list
Installed skills (3):
  • ui-ux-pro-max (v1.0.0) - Professional UI/UX design system generator
  • code-reviewer (v2.1.0) - Automated code review skill
  • test-writer (v1.5.2) - Test generation and validation
```

### Get Detailed Info

```bash
$ agent-bus-skills info ui-ux-pro-max
Skill: ui-ux-pro-max
Version: 1.0.0
Description: Professional UI/UX design system generator
Author: ComposioHQ
Path: /home/user/agent_bus/skills/ui-ux-pro-max
Entry Point: skill.md
Repository: https://github.com/ComposioHQ/awesome-claude-skills
License: MIT
Capabilities: ui-design, design-systems
Required Tools: browser
Tags: design, ui, ux, frontend
```

### Update a Skill

```bash
$ agent-bus-skills update ui-ux-pro-max
✓ Successfully updated skill 'ui-ux-pro-max'
```

## API Reference

See [SKILLS_SYSTEM.md](./SKILLS_SYSTEM.md) for complete API documentation.

## Related Documentation

- [Skills System Overview](./SKILLS_SYSTEM.md)
- [Creating Custom Skills](./SKILLS_SYSTEM.md#creating-a-skill)
- [Skill Metadata Schema](./SKILLS_SYSTEM.md#skill-metadata-format)
