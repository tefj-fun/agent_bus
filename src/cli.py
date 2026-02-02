#!/usr/bin/env python3
"""CLI for agent_bus skills management."""

import asyncio
import sys
from typing import Optional
import argparse
import logging

from .skills import SkillsManager, SkillRegistryError, SkillNotFoundError


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SkillsCLI:
    """CLI interface for skills management."""

    def __init__(self, skills_dir: str = "./skills"):
        self.skills_dir = skills_dir
        self.manager = SkillsManager(skills_dir)

    async def install(self, git_url: str, skill_name: Optional[str] = None) -> int:
        """
        Install a skill from a git repository.

        Args:
            git_url: GitHub repository URL
            skill_name: Optional name for the skill directory
                       (defaults to last part of repo URL)

        Returns:
            Exit code (0 for success, 1 for error)
        """
        # Extract skill name from URL if not provided
        if not skill_name:
            skill_name = self._extract_skill_name(git_url)
            logger.info(f"Using skill name: {skill_name}")

        try:
            logger.info(f"Installing skill '{skill_name}' from {git_url}")
            success = await self.manager.install_skill(git_url, skill_name)

            if success:
                logger.info(f"✓ Successfully installed skill '{skill_name}'")

                # Show skill info
                info = self.manager.get_skill_info(skill_name)
                if info:
                    print(f"\nSkill: {info.name}")
                    print(f"Version: {info.version}")
                    print(f"Description: {info.description}")
                    print(f"Author: {info.author}")
                    if info.capabilities:
                        print(f"Capabilities: {', '.join(info.capabilities)}")
                    if info.tags:
                        print(f"Tags: {', '.join(info.tags)}")

                return 0
            else:
                logger.error(f"✗ Failed to install skill '{skill_name}'")
                return 1

        except SkillRegistryError as e:
            logger.error(f"✗ Installation failed: {e}")
            return 1
        except Exception as e:
            logger.error(f"✗ Unexpected error: {e}")
            return 1

    async def update(self, skill_name: str) -> int:
        """
        Update a skill from its git repository.

        Args:
            skill_name: Name of the skill to update

        Returns:
            Exit code (0 for success, 1 for error)
        """
        try:
            logger.info(f"Updating skill '{skill_name}'")
            success = await self.manager.update_skill(skill_name)

            if success:
                logger.info(f"✓ Successfully updated skill '{skill_name}'")
                return 0
            else:
                logger.error(f"✗ Failed to update skill '{skill_name}'")
                return 1

        except SkillNotFoundError as e:
            logger.error(f"✗ Skill not found: {e}")
            return 1
        except SkillRegistryError as e:
            logger.error(f"✗ Update failed: {e}")
            return 1
        except Exception as e:
            logger.error(f"✗ Unexpected error: {e}")
            return 1

    def list(self, verbose: bool = False) -> int:
        """
        List all installed skills.

        Args:
            verbose: Show detailed information

        Returns:
            Exit code (always 0)
        """
        skills = self.manager.list_skills()

        if not skills:
            print("No skills installed.")
            return 0

        print(f"Installed skills ({len(skills)}):\n")

        for skill in sorted(skills, key=lambda s: s.name):
            if verbose:
                print(f"  • {skill.name} (v{skill.version})")
                print(f"    Description: {skill.description}")
                print(f"    Author: {skill.author}")
                if skill.capabilities:
                    print(f"    Capabilities: {', '.join(skill.capabilities)}")
                if skill.tags:
                    print(f"    Tags: {', '.join(skill.tags)}")
                print()
            else:
                print(f"  • {skill.name} (v{skill.version}) - {skill.description}")

        return 0

    def info(self, skill_name: str) -> int:
        """
        Show detailed information about a skill.

        Args:
            skill_name: Name of the skill

        Returns:
            Exit code (0 for success, 1 if not found)
        """
        info = self.manager.get_skill_info(skill_name)

        if not info:
            logger.error(f"✗ Skill '{skill_name}' not found")
            return 1

        print(f"Skill: {info.name}")
        print(f"Version: {info.version}")
        print(f"Description: {info.description}")
        print(f"Author: {info.author}")
        print(f"Path: {info.path}")

        if info.entry_point:
            print(f"Entry Point: {info.entry_point}")

        if info.repository:
            print(f"Repository: {info.repository}")

        if info.license:
            print(f"License: {info.license}")

        if info.capabilities:
            print(f"Capabilities: {', '.join(info.capabilities)}")

        if info.required_tools:
            print(f"Required Tools: {', '.join(info.required_tools)}")

        if info.tags:
            print(f"Tags: {', '.join(info.tags)}")

        if info.dependencies:
            print("Dependencies:")
            for dep in info.dependencies:
                version_str = f" ({dep.get('version')})" if dep.get("version") else ""
                optional_str = " [optional]" if dep.get("optional") else ""
                print(f"  - {dep.get('name')}{version_str}{optional_str}")

        if info.min_python_version:
            print(f"Min Python Version: {info.min_python_version}")

        return 0

    def _extract_skill_name(self, git_url: str) -> str:
        """
        Extract skill name from git URL.

        Args:
            git_url: Git repository URL

        Returns:
            Skill name (last part of URL without .git)
        """
        # Remove trailing .git if present
        url = git_url.rstrip("/")
        if url.endswith(".git"):
            url = url[:-4]

        # Get last part of path
        name = url.split("/")[-1]

        # Clean up name
        name = name.lower().replace("_", "-")

        return name


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Agent Bus Skills Manager", formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--skills-dir", default="./skills", help="Skills directory path (default: ./skills)"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Install command
    install_parser = subparsers.add_parser("install", help="Install a skill from a git repository")
    install_parser.add_argument(
        "git_url", help="Git repository URL (e.g., https://github.com/user/skill)"
    )
    install_parser.add_argument("--name", help="Custom name for the skill (defaults to repo name)")

    # Update command
    update_parser = subparsers.add_parser("update", help="Update a skill from its git repository")
    update_parser.add_argument("skill_name", help="Name of the skill to update")

    # List command
    list_parser = subparsers.add_parser("list", help="List all installed skills")
    list_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show detailed information"
    )

    # Info command
    info_parser = subparsers.add_parser("info", help="Show detailed information about a skill")
    info_parser.add_argument("skill_name", help="Name of the skill")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    cli = SkillsCLI(args.skills_dir)

    # Execute command
    if args.command == "install":
        exit_code = asyncio.run(cli.install(args.git_url, args.name))
    elif args.command == "update":
        exit_code = asyncio.run(cli.update(args.skill_name))
    elif args.command == "list":
        exit_code = cli.list(args.verbose)
    elif args.command == "info":
        exit_code = cli.info(args.skill_name)
    else:
        parser.print_help()
        exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
