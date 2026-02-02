# Release Process

This document describes the release and deployment automation for agent_bus.

## Overview

The project uses semantic versioning (semver) and automated CI/CD pipelines to:
1. Build and publish Docker images
2. Create GitHub releases with changelogs
3. Deploy to staging environment (configurable)

## Quick Start

### Creating a Release

```bash
# Ensure you're on main branch with latest changes
git checkout main
git pull origin main

# Run the release script (defaults to patch bump)
./scripts/release.sh patch

# Or specify bump type
./scripts/release.sh minor  # for feature releases
./scripts/release.sh major  # for breaking changes
```

The script will:
- Check you're on main branch with clean working directory
- Calculate the next version based on bump type
- Generate a changelog from commits since last tag
- Create an annotated git tag
- Push the tag to trigger the release workflow

### Manual Tagging (Alternative)

If you prefer manual control:

```bash
# Create and push a tag
git tag -a v1.2.3 -m "Release v1.2.3

- Feature: Add new capability
- Fix: Resolve issue with...
"
git push origin v1.2.3
```

## Release Workflow

When a tag matching `v*.*.*` is pushed, the GitHub Actions workflow automatically:

### 1. Build and Push Docker Image

- Builds optimized Docker image with multi-stage build
- Publishes to GitHub Container Registry (ghcr.io)
- Tags with multiple variants:
  - `v1.2.3` (exact version)
  - `v1.2` (minor version)
  - `v1` (major version)
  - `main-<sha>` (commit SHA)

**Registry**: `ghcr.io/tefj-fun/agent_bus`

### 2. Create GitHub Release

- Generates changelog from commits since previous tag
- Creates GitHub release with:
  - Changelog of commits
  - Docker pull command
  - Helm installation command
- Release is public (not draft)

### 3. Deploy to Staging (Stub)

The workflow includes a deployment stub that:
- Logs the deployment intent
- Shows example Helm upgrade command
- Can be extended to perform actual deployment

**To enable real deployment**, configure:
1. Kubernetes cluster access (kubeconfig)
2. GitHub secrets: `KUBECONFIG`, `STAGING_NAMESPACE`
3. Replace stub with actual deployment commands

## Versioning Strategy

We follow [Semantic Versioning 2.0.0](https://semver.org/):

- **MAJOR** (v2.0.0): Incompatible API changes
- **MINOR** (v1.3.0): New features, backward compatible
- **PATCH** (v1.2.4): Bug fixes, backward compatible

### When to Bump Each Version

| Change Type | Version | Example |
|-------------|---------|---------|
| Breaking API change | MAJOR | Remove endpoint, change response structure |
| New agent/feature | MINOR | Add new workflow stage, new API endpoint |
| Bug fix | PATCH | Fix crash, correct logic error |
| Documentation | PATCH | Update README, add docs |
| Performance | PATCH | Optimize query, reduce memory |

## CI/CD Architecture

```
┌─────────────────┐
│  Developer      │
│  pushes tag     │
│  v1.2.3         │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  GitHub Actions: release.yml            │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │  1. Build and Push Image         │  │
│  │     - Multi-stage Docker build   │  │
│  │     - Cache layers (GitHub)      │  │
│  │     - Push to ghcr.io            │  │
│  │     - Tag: v1.2.3, v1.2, v1      │  │
│  └──────────────────────────────────┘  │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │  2. Create GitHub Release        │  │
│  │     - Generate changelog         │  │
│  │     - Create release notes       │  │
│  │     - Include deployment guide   │  │
│  └──────────────────────────────────┘  │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │  3. Deploy to Staging (Stub)     │  │
│  │     - Log deployment intent      │  │
│  │     - (Extend for real deploy)   │  │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Artifacts                              │
│  - Docker image in ghcr.io              │
│  - GitHub release with changelog        │
│  - Ready for deployment                 │
└─────────────────────────────────────────┘
```

## Deployment Environments

### Development

**Purpose**: Local development and testing  
**Infrastructure**: Docker Compose  
**Deployment**: Manual (`docker-compose up`)

```bash
docker-compose up -d --build
```

### Staging

**Purpose**: Pre-production testing with production-like setup  
**Infrastructure**: Kubernetes cluster  
**Deployment**: Automated on release (configurable)

```bash
# Manual deployment to staging
helm upgrade --install agent-bus ./helm/agent-bus \
  --set image.tag=v1.2.3 \
  -f helm/agent-bus/values-staging.yaml \
  --namespace agent-bus-staging \
  --create-namespace
```

**Configuration**:
- Moderate resource limits (between dev and prod)
- Autoscaling enabled (2-5 API pods, 2-8 workers)
- Managed database and Redis recommended
- TLS with Let's Encrypt staging
- Monitoring enabled

### Production

**Purpose**: Live user-facing environment  
**Infrastructure**: Production Kubernetes cluster  
**Deployment**: Manual with approval gate

```bash
# Production deployment (manual, with caution)
helm upgrade --install agent-bus ./helm/agent-bus \
  --set image.tag=v1.2.3 \
  -f helm/agent-bus/values-prod.yaml \
  --namespace agent-bus-prod \
  --create-namespace
```

**Configuration**:
- High resource limits and replicas
- Autoscaling enabled (2-10 API pods, 3-20 workers)
- External managed database (RDS, Cloud SQL)
- External Redis (ElastiCache, Memorystore)
- External secrets (AWS Secrets Manager, etc.)
- TLS with Let's Encrypt production
- Comprehensive monitoring and alerting

## Docker Image Management

### Pulling Images

```bash
# Latest release
docker pull ghcr.io/tefj-fun/agent_bus:latest

# Specific version
docker pull ghcr.io/tefj-fun/agent_bus:v1.2.3

# Minor version (tracks latest patch)
docker pull ghcr.io/tefj-fun/agent_bus:v1.2

# Major version (tracks latest minor/patch)
docker pull ghcr.io/tefj-fun/agent_bus:v1
```

### Image Tags Strategy

Each release creates multiple tags:

| Tag Pattern | Example | Use Case |
|-------------|---------|----------|
| `v{major}.{minor}.{patch}` | `v1.2.3` | Pin to exact version |
| `v{major}.{minor}` | `v1.2` | Auto-update patches |
| `v{major}` | `v1` | Auto-update minor/patches |
| `{branch}-{sha}` | `main-abc1234` | Test specific commits |
| `latest` | `latest` | Always newest release |

### Best Practices

- **Production**: Pin to exact version (`v1.2.3`) for predictability
- **Staging**: Use minor version (`v1.2`) to test patches automatically
- **Development**: Use `latest` or specific commit SHA

## Release Checklist

Before creating a release:

- [ ] All tests passing in CI
- [ ] Code reviewed and merged to main
- [ ] Documentation updated (README, API docs, etc.)
- [ ] Breaking changes documented in CHANGELOG or migration guide
- [ ] Database migrations tested (if applicable)
- [ ] Performance regressions checked
- [ ] Security vulnerabilities addressed

## Rollback Procedure

If a release has issues:

### 1. Identify Previous Good Version

```bash
# List recent releases
gh release list

# Example output:
# v1.2.3  Latest   1 hour ago
# v1.2.2  v1.2.2   2 days ago   <- rollback target
# v1.2.1  v1.2.1   1 week ago
```

### 2. Rollback Deployment

```bash
# Staging
helm upgrade agent-bus ./helm/agent-bus \
  --set image.tag=v1.2.2 \
  -f helm/agent-bus/values-staging.yaml \
  --namespace agent-bus-staging

# Production
helm upgrade agent-bus ./helm/agent-bus \
  --set image.tag=v1.2.2 \
  -f helm/agent-bus/values-prod.yaml \
  --namespace agent-bus-prod
```

### 3. Document and Fix

- Create GitHub issue documenting the problem
- Fix the bug in a new branch
- Create patch release (v1.2.4) with the fix

## Extending Deployment Automation

To enable automatic staging deployment:

### 1. Set Up Kubernetes Access

Store kubeconfig as GitHub secret:

```bash
# Encode kubeconfig
cat ~/.kube/config | base64 | pbcopy

# Add to GitHub secrets:
# Settings > Secrets > Actions > New repository secret
# Name: KUBECONFIG
# Value: <paste base64 kubeconfig>
```

### 2. Update Workflow

Edit `.github/workflows/release.yml`, replace the `deploy-staging` job stub:

```yaml
- name: Deploy to staging
  env:
    KUBECONFIG_DATA: ${{ secrets.KUBECONFIG }}
  run: |
    echo "$KUBECONFIG_DATA" | base64 -d > /tmp/kubeconfig
    export KUBECONFIG=/tmp/kubeconfig
    
    helm upgrade --install agent-bus ./helm/agent-bus \
      --set image.tag=${{ github.ref_name }} \
      -f helm/agent-bus/values-staging.yaml \
      --namespace agent-bus-staging \
      --create-namespace \
      --wait
```

### 3. Add Production Deployment (Manual)

Create separate workflow for production with manual approval:

```yaml
# .github/workflows/deploy-production.yml
on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Version to deploy (e.g., v1.2.3)'
        required: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production  # Requires approval in GitHub settings
    steps:
      - name: Deploy to production
        run: |
          # Deployment commands
```

## Monitoring Releases

### GitHub Actions

Monitor workflow runs:
```
https://github.com/tefj-fun/agent_bus/actions
```

### Container Registry

View published images:
```
https://github.com/tefj-fun/agent_bus/pkgs/container/agent_bus
```

### Deployments

Check deployment status:

```bash
# Staging
kubectl get pods -n agent-bus-staging
helm status agent-bus -n agent-bus-staging

# Production
kubectl get pods -n agent-bus-prod
helm status agent-bus -n agent-bus-prod
```

## Troubleshooting

### Workflow Fails to Build Image

**Check**:
- Dockerfile syntax
- All dependencies in requirements.txt
- Docker build context includes all necessary files

**Fix**:
```bash
# Test build locally
docker build -t agent-bus:test .
```

### Tag Push Doesn't Trigger Workflow

**Check**:
- Tag matches pattern `v*.*.*`
- GitHub Actions enabled for repository
- Workflow file syntax is valid

**Verify**:
```bash
# Check tag format
git tag -l

# Verify workflow file
cat .github/workflows/release.yml | yamllint -
```

### Image Push Fails (Permission Denied)

**Fix**:
- Ensure `packages: write` permission in workflow
- Check `GITHUB_TOKEN` has necessary scopes

### Helm Deployment Fails

**Check**:
- Kubernetes cluster is reachable
- Namespace exists or `--create-namespace` flag is used
- Image pull secret configured (if using private registry)
- Resource quotas not exceeded

**Debug**:
```bash
# Check deployment logs
kubectl logs -n agent-bus-staging deployment/agent-bus-api --tail=100

# Describe pod for events
kubectl describe pod -n agent-bus-staging <pod-name>
```

## Future Enhancements

Potential improvements to the release process:

1. **Changelog Automation**: Use conventional commits for automatic changelog generation
2. **Automated Testing**: Run integration tests before deployment
3. **Canary Deployments**: Gradual rollout with traffic shifting
4. **Rollback Automation**: Automatic rollback on failure detection
5. **Multi-environment Promotion**: Dev → Staging → Production pipeline
6. **Release Notes Template**: Standardized format for release notes
7. **Version Bumping in Code**: Update version in `pyproject.toml` automatically
8. **Docker Image Scanning**: Security vulnerability scanning before push
9. **Slack/Email Notifications**: Alert team on releases and deployments
10. **GitOps Integration**: ArgoCD or Flux for declarative deployments

## Related Documentation

- [Docker Guide](DOCKER.md) - Container build and local development
- [Kubernetes Guide](../k8s/README.md) - Cluster deployment
- [Helm Chart](../helm/agent-bus/README.md) - Helm installation and configuration
- [Observability](OBSERVABILITY.md) - Monitoring and logging

## Support

For issues with the release process:
1. Check [GitHub Actions runs](https://github.com/tefj-fun/agent_bus/actions)
2. Review [existing issues](https://github.com/tefj-fun/agent_bus/issues)
3. Create new issue with `ci/cd` label
