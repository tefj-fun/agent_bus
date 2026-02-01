"""JSON schema definitions for skills registry format."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
from packaging import version as pkg_version


class SkillDependency(BaseModel):
    """External dependency required by a skill."""
    
    name: str = Field(..., description="Dependency name (e.g., 'requests', 'opencv-python')")
    version: Optional[str] = Field(None, description="Version constraint (e.g., '>=2.0.0')")
    optional: bool = Field(False, description="Whether dependency is optional")


class SkillCapability(BaseModel):
    """Capability that a skill provides."""
    
    name: str = Field(..., description="Capability identifier (e.g., 'ui-design', 'testing')")
    description: Optional[str] = Field(None, description="Human-readable capability description")


class SkillTool(BaseModel):
    """Tool required by the skill."""
    
    name: str = Field(..., description="Tool identifier (e.g., 'browser', 'shell')")
    required: bool = Field(True, description="Whether tool is strictly required")


class SkillMetadataSchema(BaseModel):
    """
    JSON schema for skill.json metadata file.
    
    This defines the canonical format for skill registry entries.
    """
    
    model_config = ConfigDict(extra='forbid')
    
    # Core metadata
    name: str = Field(..., description="Skill identifier (lowercase, hyphenated)")
    version: str = Field(..., description="Semver version string (e.g., '1.2.3')")
    description: str = Field(..., description="Brief description of the skill")
    author: str = Field(..., description="Author name or organization")
    
    # Skill capabilities
    capabilities: List[SkillCapability] = Field(
        default_factory=list,
        description="Capabilities provided by this skill"
    )
    
    # Tool requirements
    required_tools: List[SkillTool] = Field(
        default_factory=list,
        description="OpenClaw tools required by this skill"
    )
    
    # Dependencies
    dependencies: List[SkillDependency] = Field(
        default_factory=list,
        description="Python package dependencies"
    )
    
    # Entry points
    entry_point: Optional[str] = Field(
        None,
        description="Main prompt file (default: skill.md, README.md, or prompt.md)"
    )
    
    # Compatibility
    min_python_version: Optional[str] = Field(
        None,
        description="Minimum Python version required (e.g., '3.10')"
    )
    
    # Repository info
    repository: Optional[str] = Field(
        None,
        description="Git repository URL"
    )
    
    license: Optional[str] = Field(
        None,
        description="License identifier (e.g., 'MIT', 'Apache-2.0')"
    )
    
    # Tags for discovery
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for categorization and search"
    )
    
    # Custom metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional custom metadata"
    )
    
    @field_validator('version')
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate semver version format."""
        try:
            pkg_version.Version(v)
        except Exception as e:
            raise ValueError(f"Invalid semver version '{v}': {e}")
        return v
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate skill name format (lowercase, hyphenated)."""
        if not v:
            raise ValueError("Skill name cannot be empty")
        
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError(
                f"Skill name '{v}' must contain only alphanumeric characters, "
                "hyphens, and underscores"
            )
        
        if v.lower() != v:
            raise ValueError(f"Skill name '{v}' must be lowercase")
        
        return v
    
    @field_validator('min_python_version')
    @classmethod
    def validate_min_python_version(cls, v: Optional[str]) -> Optional[str]:
        """Validate Python version format."""
        if v is None:
            return v
        
        try:
            pkg_version.Version(v)
        except Exception as e:
            raise ValueError(f"Invalid Python version '{v}': {e}")
        
        return v


class SkillsRegistrySchema(BaseModel):
    """
    Root schema for skills registry file (skills.json).
    
    This file tracks all installed skills in the workspace.
    """
    
    model_config = ConfigDict(extra='forbid')
    
    version: str = Field(
        default="1.0.0",
        description="Registry format version"
    )
    
    skills: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Map of skill name to metadata"
    )
    
    updated_at: Optional[str] = Field(
        None,
        description="ISO 8601 timestamp of last update"
    )


# Example skill.json for reference
EXAMPLE_SKILL_METADATA = {
    "name": "ui-ux-pro-max",
    "version": "1.0.0",
    "description": "Professional UI/UX design system generator",
    "author": "ComposioHQ",
    "capabilities": [
        {
            "name": "ui-design",
            "description": "Generate comprehensive UI/UX designs"
        },
        {
            "name": "design-systems",
            "description": "Create design systems and component libraries"
        }
    ],
    "required_tools": [
        {
            "name": "browser",
            "required": True
        }
    ],
    "dependencies": [],
    "entry_point": "skill.md",
    "min_python_version": "3.10",
    "repository": "https://github.com/ComposioHQ/awesome-claude-skills",
    "license": "MIT",
    "tags": ["design", "ui", "ux", "frontend"],
    "metadata": {}
}
