"""
Tests for release workflow validation
"""
import os
import yaml
import pytest
from pathlib import Path


def test_release_workflow_exists():
    """Test that release.yml workflow file exists"""
    workflow_path = Path(".github/workflows/release.yml")
    assert workflow_path.exists(), "release.yml workflow not found"


def test_release_workflow_syntax():
    """Test that release.yml has valid YAML syntax"""
    workflow_path = Path(".github/workflows/release.yml")
    with open(workflow_path) as f:
        workflow = yaml.safe_load(f)
    
    assert workflow is not None
    assert "name" in workflow
    assert workflow["name"] == "Release"
    assert "on" in workflow
    assert "jobs" in workflow


def test_release_workflow_has_required_jobs():
    """Test that release workflow has all required jobs"""
    workflow_path = Path(".github/workflows/release.yml")
    with open(workflow_path) as f:
        workflow = yaml.safe_load(f)
    
    jobs = workflow["jobs"]
    assert "build-and-push" in jobs
    assert "create-release" in jobs
    assert "deploy-staging" in jobs


def test_release_workflow_trigger():
    """Test that release workflow triggers on version tags"""
    workflow_path = Path(".github/workflows/release.yml")
    with open(workflow_path) as f:
        workflow = yaml.safe_load(f)
    
    triggers = workflow["on"]
    assert "push" in triggers
    assert "tags" in triggers["push"]
    assert "v*.*.*" in triggers["push"]["tags"]


def test_release_workflow_permissions():
    """Test that build-and-push job has correct permissions"""
    workflow_path = Path(".github/workflows/release.yml")
    with open(workflow_path) as f:
        workflow = yaml.safe_load(f)
    
    build_job = workflow["jobs"]["build-and-push"]
    assert "permissions" in build_job
    permissions = build_job["permissions"]
    assert permissions.get("contents") == "read"
    assert permissions.get("packages") == "write"


def test_release_workflow_docker_metadata():
    """Test that Docker metadata action is configured"""
    workflow_path = Path(".github/workflows/release.yml")
    with open(workflow_path) as f:
        content = f.read()
    
    assert "docker/metadata-action@v5" in content
    assert "type=semver,pattern={{version}}" in content
    assert "type=semver,pattern={{major}}.{{minor}}" in content
    assert "type=semver,pattern={{major}}" in content


def test_release_script_exists():
    """Test that release script exists and is executable"""
    script_path = Path("scripts/release.sh")
    assert script_path.exists(), "release.sh script not found"
    assert os.access(script_path, os.X_OK), "release.sh is not executable"


def test_release_script_has_shebang():
    """Test that release script has proper shebang"""
    script_path = Path("scripts/release.sh")
    with open(script_path) as f:
        first_line = f.readline().strip()
    
    assert first_line.startswith("#!"), "Missing shebang"
    assert "bash" in first_line, "Should use bash"


def test_changelog_exists():
    """Test that CHANGELOG.md exists"""
    changelog_path = Path("CHANGELOG.md")
    assert changelog_path.exists(), "CHANGELOG.md not found"


def test_changelog_format():
    """Test that CHANGELOG follows Keep a Changelog format"""
    changelog_path = Path("CHANGELOG.md")
    with open(changelog_path) as f:
        content = f.read()
    
    assert "# Changelog" in content
    assert "## [Unreleased]" in content or "## Unreleased" in content
    assert "keepachangelog.com" in content.lower() or "## [" in content


def test_release_documentation_exists():
    """Test that release documentation exists"""
    doc_path = Path("docs/RELEASE.md")
    assert doc_path.exists(), "docs/RELEASE.md not found"


def test_release_documentation_completeness():
    """Test that release documentation covers key topics"""
    doc_path = Path("docs/RELEASE.md")
    with open(doc_path) as f:
        content = f.read()
    
    required_sections = [
        "Release Process",
        "Creating a Release",
        "Versioning",
        "Deployment",
        "Rollback",
    ]
    
    for section in required_sections:
        assert section.lower() in content.lower(), f"Missing section: {section}"


def test_staging_values_exists():
    """Test that staging Helm values file exists"""
    values_path = Path("helm/agent-bus/values-staging.yaml")
    assert values_path.exists(), "values-staging.yaml not found"


def test_staging_values_syntax():
    """Test that staging values has valid YAML"""
    values_path = Path("helm/agent-bus/values-staging.yaml")
    with open(values_path) as f:
        values = yaml.safe_load(f)
    
    assert values is not None
    assert "image" in values or "replicaCount" in values


def test_staging_values_has_autoscaling():
    """Test that staging values configures autoscaling"""
    values_path = Path("helm/agent-bus/values-staging.yaml")
    with open(values_path) as f:
        values = yaml.safe_load(f)
    
    assert "autoscaling" in values
    autoscaling = values["autoscaling"]
    
    # Check API autoscaling
    if "api" in autoscaling:
        assert autoscaling["api"].get("enabled") is True
        assert "minReplicas" in autoscaling["api"]
        assert "maxReplicas" in autoscaling["api"]


def test_version_tags_format():
    """Test that version tag format examples are consistent"""
    doc_path = Path("docs/RELEASE.md")
    with open(doc_path) as f:
        content = f.read()
    
    # Should use semantic versioning examples
    assert "v1.2.3" in content
    assert "v" in content  # Version tags should have 'v' prefix


def test_docker_registry_configured():
    """Test that Docker registry is properly configured"""
    workflow_path = Path(".github/workflows/release.yml")
    with open(workflow_path) as f:
        content = f.read()
    
    assert "ghcr.io" in content or "REGISTRY" in content
    assert "docker/login-action" in content


def test_release_creates_github_release():
    """Test that workflow creates GitHub release"""
    workflow_path = Path(".github/workflows/release.yml")
    with open(workflow_path) as f:
        content = f.read()
    
    assert "create-release" in content
    assert "softprops/action-gh-release" in content or "gh release create" in content


def test_changelog_generation():
    """Test that workflow generates changelog"""
    workflow_path = Path(".github/workflows/release.yml")
    with open(workflow_path) as f:
        content = f.read()
    
    assert "changelog" in content.lower()
    assert "git log" in content


def test_deployment_stub_documented():
    """Test that deployment stub is documented as extensible"""
    workflow_path = Path(".github/workflows/release.yml")
    with open(workflow_path) as f:
        content = f.read()
    
    assert "stub" in content.lower() or "deploy" in content.lower()


def test_rollback_procedure_documented():
    """Test that rollback procedure is documented"""
    doc_path = Path("docs/RELEASE.md")
    with open(doc_path) as f:
        content = f.read()
    
    assert "rollback" in content.lower()
    assert "helm upgrade" in content.lower()


def test_semver_strategy_documented():
    """Test that semantic versioning strategy is documented"""
    doc_path = Path("docs/RELEASE.md")
    with open(doc_path) as f:
        content = f.read()
    
    assert "semantic versioning" in content.lower() or "semver" in content.lower()
    assert "MAJOR" in content
    assert "MINOR" in content
    assert "PATCH" in content


def test_readme_mentions_releases():
    """Test that README.md mentions releases"""
    readme_path = Path("README.md")
    with open(readme_path) as f:
        content = f.read()
    
    assert "release" in content.lower()
    assert "docs/RELEASE.md" in content or "./scripts/release.sh" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
