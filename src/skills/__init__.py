"""Skills module for Claude Skills management."""

from .manager import SkillsManager, Skill, SkillLoadError
from .registry import (
    SkillRegistry,
    SkillMetadata,
    SkillRegistryError,
    SkillValidationError,
    SkillNotFoundError,
)
from .schema import (
    SkillMetadataSchema,
    SkillsRegistrySchema,
    SkillCapability,
    SkillTool,
    SkillDependency,
    EXAMPLE_SKILL_METADATA,
)
from .allowlist import (
    SkillAllowlistManager,
    SkillPermissionError,
    AllowlistEntry,
    CapabilityMapping,
)
from .config_loader import AllowlistConfigLoader

__all__ = [
    # Manager
    "SkillsManager",
    "Skill",
    "SkillLoadError",
    # Registry
    "SkillRegistry",
    "SkillMetadata",
    "SkillRegistryError",
    "SkillValidationError",
    "SkillNotFoundError",
    # Schema
    "SkillMetadataSchema",
    "SkillsRegistrySchema",
    "SkillCapability",
    "SkillTool",
    "SkillDependency",
    "EXAMPLE_SKILL_METADATA",
    # Allowlist
    "SkillAllowlistManager",
    "SkillPermissionError",
    "AllowlistEntry",
    "CapabilityMapping",
    "AllowlistConfigLoader",
]
