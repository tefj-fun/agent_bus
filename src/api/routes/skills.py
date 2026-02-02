"""API routes for skills management."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging

from ...skills import (
    SkillsManager,
    SkillRegistryError,
    SkillNotFoundError,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize skills manager
skills_manager = SkillsManager("./skills")


# Request/Response Models
class InstallSkillRequest(BaseModel):
    """Request to install a skill."""

    git_url: str = Field(..., description="Git repository URL")
    skill_name: Optional[str] = Field(None, description="Custom skill name (defaults to repo name)")


class SkillResponse(BaseModel):
    """Skill metadata response."""

    name: str
    version: str
    description: str
    author: str
    capabilities: List[str] = Field(default_factory=list)
    required_tools: List[str] = Field(default_factory=list)
    path: str
    entry_point: Optional[str] = None
    repository: Optional[str] = None
    license: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    dependencies: List[Dict[str, Any]] = Field(default_factory=list)
    min_python_version: Optional[str] = None


class SkillListResponse(BaseModel):
    """List of skills response."""

    skills: List[SkillResponse]
    total: int


class SuccessResponse(BaseModel):
    """Generic success response."""

    success: bool
    message: str


# Routes
@router.post(
    "/skills/install",
    response_model=SkillResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Install a skill from git repository",
    tags=["skills"],
)
async def install_skill(request: InstallSkillRequest):
    """
    Install a skill from a git repository.

    This endpoint:
    1. Clones the git repository
    2. Validates the skill structure
    3. Registers the skill in the registry
    4. Returns the installed skill metadata

    Args:
        request: Installation request with git_url and optional skill_name

    Returns:
        Installed skill metadata

    Raises:
        400: Invalid request or skill already exists
        500: Installation failed
    """
    try:
        # Extract skill name from URL if not provided
        skill_name = request.skill_name
        if not skill_name:
            skill_name = _extract_skill_name(request.git_url)
            logger.info(f"Using extracted skill name: {skill_name}")

        # Install skill
        logger.info(f"Installing skill '{skill_name}' from {request.git_url}")
        success = await skills_manager.install_skill(request.git_url, skill_name)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Skill installation failed",
            )

        # Get installed skill info
        skill_info = skills_manager.get_skill_info(skill_name)
        if not skill_info:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Skill installed but not found in registry",
            )

        return _skill_to_response(skill_info)

    except SkillRegistryError as e:
        logger.error(f"Skill installation failed: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during skill installation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Installation failed: {str(e)}",
        )


@router.post(
    "/skills/{skill_name}/update",
    response_model=SuccessResponse,
    summary="Update a skill from its git repository",
    tags=["skills"],
)
async def update_skill(skill_name: str):
    """
    Update a skill by pulling latest changes from git.

    Args:
        skill_name: Name of the skill to update

    Returns:
        Success message

    Raises:
        404: Skill not found
        500: Update failed
    """
    try:
        success = await skills_manager.update_skill(skill_name)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Skill update failed"
            )

        return SuccessResponse(success=True, message=f"Skill '{skill_name}' updated successfully")

    except SkillNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SkillRegistryError as e:
        logger.error(f"Skill update failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during skill update: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Update failed: {str(e)}"
        )


@router.get(
    "/skills",
    response_model=SkillListResponse,
    summary="List all installed skills",
    tags=["skills"],
)
def list_skills(capability: Optional[str] = None, tag: Optional[str] = None):
    """
    List all installed skills.

    Optionally filter by capability or tag.

    Args:
        capability: Filter by capability
        tag: Filter by tag

    Returns:
        List of skills with metadata
    """
    try:
        if capability:
            skills = skills_manager.get_skills_by_capability(capability)
        elif tag:
            skills = skills_manager.get_skills_by_tag(tag)
        else:
            skills = skills_manager.list_skills()

        return SkillListResponse(
            skills=[_skill_to_response(skill) for skill in skills], total=len(skills)
        )

    except Exception as e:
        logger.error(f"Error listing skills: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list skills: {str(e)}",
        )


@router.get(
    "/skills/{skill_name}",
    response_model=SkillResponse,
    summary="Get skill information",
    tags=["skills"],
)
def get_skill(skill_name: str):
    """
    Get detailed information about a specific skill.

    Args:
        skill_name: Name of the skill

    Returns:
        Skill metadata

    Raises:
        404: Skill not found
    """
    skill_info = skills_manager.get_skill_info(skill_name)

    if not skill_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Skill '{skill_name}' not found"
        )

    return _skill_to_response(skill_info)


@router.post(
    "/skills/reload",
    response_model=SuccessResponse,
    summary="Reload skills registry",
    tags=["skills"],
)
def reload_skills():
    """
    Reload the skills registry from disk.

    This re-scans the skills directory and updates the registry.

    Returns:
        Success message
    """
    try:
        skills_manager.reload_registry()

        skills = skills_manager.list_skills()

        return SuccessResponse(
            success=True, message=f"Registry reloaded. {len(skills)} skills found."
        )

    except Exception as e:
        logger.error(f"Error reloading registry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reload registry: {str(e)}",
        )


# Helper functions
def _skill_to_response(skill) -> SkillResponse:
    """Convert SkillMetadata to SkillResponse."""
    return SkillResponse(
        name=skill.name,
        version=skill.version,
        description=skill.description,
        author=skill.author,
        capabilities=skill.capabilities,
        required_tools=skill.required_tools,
        path=skill.path,
        entry_point=skill.entry_point,
        repository=skill.repository,
        license=skill.license,
        tags=skill.tags,
        dependencies=skill.dependencies,
        min_python_version=skill.min_python_version,
    )


def _extract_skill_name(git_url: str) -> str:
    """
    Extract skill name from git URL.

    Args:
        git_url: Git repository URL

    Returns:
        Skill name
    """
    url = git_url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]

    name = url.split("/")[-1]
    name = name.lower().replace("_", "-")

    return name
