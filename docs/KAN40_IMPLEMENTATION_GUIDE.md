# KAN-40 CI/CD Hardening - Implementation Guide

**Epic:** KAN-40 - Production-grade CI/CD pipeline  
**Status:** In Progress (1/5 complete, 1 in review)  
**Last Updated:** 2026-02-01

## Overview

KAN-40 aims to transform the agent_bus CI/CD pipeline from basic Docker build + pytest to a production-ready system with linting, caching, security scanning, and automated releases.

## Subtask Breakdown

### ✅ KAN-80: Mock smoke test required + nightly real-Claude
**Status:** Done (pre-existing)

**Implementation:**
- `smoke-test.yml`: Runs mock-mode smoke test manually + nightly
- `nightly-real-smoke.yml`: Runs real Claude API test nightly at 09:17 UTC
- Prevents regressions without burning API credits on every PR

**No action needed.**

---

### 🔄 KAN-76: Lint/format checks (ruff + black)
**Status:** In review (PR #38)

**What was done:**
1. Added `lint` job to `.github/workflows/ci.yml`:
   - Runs in parallel with `test` job
   - Installs ruff + black
   - Runs `ruff check` and `black --check` on src/, tests/, scripts/
   - Fails CI if code doesn't pass checks

2. Fixed codebase:
   - Auto-fixed 45 lint issues with `ruff check --fix`
   - Reformatted 73 files with `black`
   - Configured ruff to ignore E402 in test files (imports after path manipulation)

3. Fixed critical bug in Dockerfile:
   - Added missing dependencies: chromadb, sentence-transformers, kubernetes, prometheus-client, opentelemetry-api, opentelemetry-sdk, packaging, pyyaml
   - These were in pyproject.toml but missing from Dockerfile

**Current status:**
- PR #38 created: https://github.com/tefj-fun/agent_bus/pull/38
- CI running (2nd attempt after dependency fix)
- Lint job: ✅ Passed in 10s
- Test job: Still running (Docker build + tests)

**Next steps:**
1. Wait for CI to pass
2. Merge PR #38
3. Transition KAN-76 to Done in Jira

**Verification:**
```bash
# After merge, verify lint checks work:
git checkout main && git pull
ruff check src/ tests/ scripts/  # Should pass
black --check src/ tests/ scripts/  # Should pass
```

---

### ⏳ KAN-77: Container build cache improvements
**Status:** Ready to implement

**Branch:** `kan-77-build-cache` (changes stashed - contains draft implementation)

**Goal:** Reduce Docker build time from ~3min to ~30s on cache hits

**Implementation plan:**

1. **Restore stashed changes:**
   ```bash
   git checkout kan-77-build-cache
   git stash pop
   ```

2. **Review changes:**
   - `.github/workflows/ci.yml`: Added GitHub Actions cache for Docker layers
   - Uses `actions/cache@v4` with path `/tmp/.buildx-cache`
   - Cache key: `${{ runner.os }}-docker-${{ hashFiles('Dockerfile', 'pyproject.toml') }}`
   - Uses `docker/build-push-action@v5` for layer caching

3. **Test locally:**
   ```bash
   # First build (no cache)
   docker buildx build --load -t agent_bus:latest .
   
   # Second build (with cache) - should be much faster
   docker buildx build --load -t agent_bus:latest .
   ```

4. **Create PR:**
   ```bash
   git add .github/workflows/ci.yml docker-compose.yml
   git commit -m "KAN-77: Add Docker build cache to CI

   - Use GitHub Actions cache for Docker layers
   - Cache key based on Dockerfile + pyproject.toml hash
   - Expected ~2-3min savings on cache hits
   - Uses docker/build-push-action@v5 with layer caching"
   
   git push -u origin kan-77-build-cache
   gh pr create --title "KAN-77: Add Docker build cache to CI" --base main
   ```

5. **Verify:**
   - First CI run: ~3-4min (cache miss)
   - Second CI run (after merge): ~1-2min (cache hit)

**Estimated time:** 30-45 minutes

**Jira transition:**
```bash
# Move to In Progress, then Done after merge
```

---

### ⏳ KAN-78: Branch protection rules
**Status:** Not started

**Goal:** Protect main branch from direct pushes and ensure code quality

**Implementation:**

1. **Configure GitHub branch protection** (via UI or API):

   **Via GitHub UI:**
   - Go to: https://github.com/tefj-fun/agent_bus/settings/branches
   - Click "Add rule" for `main` branch
   - Configure:
     - ✅ Require a pull request before merging
     - ✅ Require approvals (1 minimum)
     - ✅ Dismiss stale pull request approvals when new commits are pushed
     - ✅ Require status checks to pass before merging
       - Required checks: `lint`, `test`
     - ✅ Require branches to be up to date before merging
     - ✅ Do not allow bypassing the above settings
     - ✅ Restrict who can push to matching branches (admin only)
   - Save changes

   **Via GitHub API:**
   ```bash
   gh api repos/tefj-fun/agent_bus/branches/main/protection -X PUT \
     -f required_pull_request_reviews[required_approving_review_count]=1 \
     -f required_status_checks[strict]=true \
     -f required_status_checks[contexts][]=lint \
     -f required_status_checks[contexts][]=test \
     -f enforce_admins=true \
     -f restrictions=null
   ```

2. **Test:**
   - Try to push directly to main (should fail)
   - Create a PR with failing tests (should block merge)
   - Create a PR with passing tests (should allow merge)

3. **Document in README:**
   Add to README.md under "Contributing":
   ```markdown
   ## Branch Protection
   
   The `main` branch is protected:
   - All changes must go through pull requests
   - PRs require 1 approval
   - All CI checks (lint + test) must pass
   - Branches must be up-to-date before merge
   ```

**Estimated time:** 15-20 minutes

**Jira transition:** Create ticket → In Progress → Done

---

### ⏳ KAN-79: Release tagging + deployment stub
**Status:** Not started

**Goal:** Automated releases with semantic versioning and deployment automation

**Implementation plan:**

1. **Create release workflow** (`.github/workflows/release.yml`):

```yaml
name: Release

on:
  push:
    tags:
      - 'v*.*.*'  # Trigger on version tags (v1.0.0, v1.2.3, etc.)

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      packages: write
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Fetch all history for changelog
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Extract version from tag
        id: version
        run: echo "VERSION=${GITHUB_REF#refs/tags/v}" >> $GITHUB_OUTPUT
      
      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ghcr.io/tefj-fun/agent_bus:${{ steps.version.outputs.VERSION }}
            ghcr.io/tefj-fun/agent_bus:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
      
      - name: Generate changelog
        id: changelog
        uses: metcalfc/changelog-generator@v4.1.0
        with:
          myToken: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Create GitHub Release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: ${{ github.ref }}
          release_name: Release ${{ steps.version.outputs.VERSION }}
          body: ${{ steps.changelog.outputs.changelog }}
          draft: false
          prerelease: false
      
      - name: Deployment stub (placeholder)
        run: |
          echo "🚀 Deployment would happen here"
          echo "Version: ${{ steps.version.outputs.VERSION }}"
          echo "Image: ghcr.io/tefj-fun/agent_bus:${{ steps.version.outputs.VERSION }}"
          echo ""
          echo "Future: kubectl apply -f k8s/ (once KAN-36 is complete)"
```

2. **Add release script** (`scripts/release.sh`):

```bash
#!/bin/bash
# Create a new release tag
set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <version>"
    echo "Example: $0 1.0.0"
    exit 1
fi

VERSION=$1
TAG="v${VERSION}"

echo "Creating release ${TAG}..."

# Verify we're on main and up-to-date
git checkout main
git pull

# Create and push tag
git tag -a "${TAG}" -m "Release ${VERSION}"
git push origin "${TAG}"

echo "✅ Release ${TAG} created and pushed"
echo "GitHub Actions will now:"
echo "  1. Build and push Docker image"
echo "  2. Generate changelog"
echo "  3. Create GitHub release"
echo ""
echo "View progress: https://github.com/tefj-fun/agent_bus/actions"
```

3. **Make script executable:**
   ```bash
   chmod +x scripts/release.sh
   ```

4. **Update version in pyproject.toml:**
   - Add version bumping automation (optional, can use `poetry version`)

5. **Test the workflow:**
   ```bash
   # Create a test release
   ./scripts/release.sh 0.1.0
   
   # Verify:
   # - GitHub Actions runs release workflow
   # - Docker image pushed to ghcr.io/tefj-fun/agent_bus:0.1.0
   # - GitHub release created with changelog
   ```

6. **Document release process:**
   Add to `docs/RELEASING.md`:
   ```markdown
   # Release Process
   
   1. Ensure all PRs for the release are merged to `main`
   2. Run the release script:
      ```bash
      ./scripts/release.sh <version>
      ```
   3. GitHub Actions will automatically:
      - Build and push Docker image to ghcr.io
      - Generate changelog
      - Create GitHub release
   
   ## Versioning
   
   We follow [Semantic Versioning](https://semver.org/):
   - MAJOR: Breaking changes
   - MINOR: New features (backward compatible)
   - PATCH: Bug fixes
   
   Example: `1.2.3` → Major=1, Minor=2, Patch=3
   ```

**Estimated time:** 1-2 hours

**Jira transition:** Create ticket → In Progress → Done

---

### 💡 KAN-86: Security scanning (RECOMMENDED)
**Status:** Not created in Jira (recommended addition)

**Goal:** Add automated security scanning for production-readiness

**Implementation plan:**

1. **Create Jira ticket:**
   ```
   Summary: CI: add security scanning (bandit, safety, trivy)
   Description:
   Add security scanning to CI pipeline for production-grade security:
   - bandit: Python code security issues (SQL injection, hardcoded secrets, etc.)
   - safety: Dependency vulnerability scanning (CVEs)
   - trivy: Container image vulnerability scanning
   
   Keep CI fast - run in parallel with lint/test jobs.
   ```

2. **Add security workflow** (`.github/workflows/security.yml`):

```yaml
name: Security

on:
  push:
    branches: ["main"]
  pull_request:
  schedule:
    - cron: '0 6 * * 1'  # Weekly Monday 6am UTC

jobs:
  bandit:
    name: Python Security (Bandit)
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      
      - name: Install Bandit
        run: pip install bandit[toml]
      
      - name: Run Bandit
        run: |
          bandit -r src/ -f json -o bandit-report.json || true
          bandit -r src/ -ll  # Fail on medium/high severity
      
      - name: Upload Bandit report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: bandit-report
          path: bandit-report.json
  
  safety:
    name: Dependency Vulnerabilities (Safety)
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      
      - name: Install Safety
        run: pip install safety
      
      - name: Check dependencies
        run: |
          # Extract dependencies from Dockerfile
          grep "pip install" Dockerfile | sed 's/.*pip install --no-cache-dir //' | tr ' ' '\n' > requirements.txt
          safety check --file=requirements.txt --json --output safety-report.json || true
          safety check --file=requirements.txt  # Fail on vulnerabilities
      
      - name: Upload Safety report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: safety-report
          path: safety-report.json
  
  trivy:
    name: Container Security (Trivy)
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      
      - name: Build Docker image
        run: docker build -t agent_bus:scan .
      
      - name: Run Trivy scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'agent_bus:scan'
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
      
      - name: Upload Trivy results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-results.sarif'
```

3. **Configure Bandit** (`pyproject.toml`):
```toml
[tool.bandit]
exclude_dirs = ["tests", "scripts"]
skips = ["B101"]  # Skip assert warnings in test-like code
```

4. **Test locally:**
```bash
# Install tools
pip install bandit[toml] safety

# Run bandit
bandit -r src/ -ll

# Run safety
grep "pip install" Dockerfile | sed 's/.*pip install --no-cache-dir //' | tr ' ' '\n' > requirements.txt
safety check --file=requirements.txt

# Run trivy
docker build -t agent_bus:scan .
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image --severity HIGH,CRITICAL agent_bus:scan
```

5. **Update CI badge in README:**
```markdown
[![Security](https://github.com/tefj-fun/agent_bus/workflows/Security/badge.svg)](https://github.com/tefj-fun/agent_bus/actions/workflows/security.yml)
```

**Expected results:**
- Bandit: Catches common Python security issues
- Safety: Alerts on vulnerable dependencies (CVEs)
- Trivy: Scans Docker image for OS/library vulnerabilities

**Estimated time:** 45-60 minutes

**Jira:** Create KAN-86 → Implement → Done

---

## Summary Checklist

- [x] KAN-80: Smoke tests ✅
- [ ] KAN-76: Lint/format (waiting for CI to pass, then merge)
- [ ] KAN-77: Build cache (~30-45 min)
- [ ] KAN-78: Branch protection (~15-20 min)
- [ ] KAN-79: Release automation (~1-2 hours)
- [ ] KAN-86: Security scanning (~45-60 min) - Optional but recommended

**Total remaining effort:** ~3-4 hours for complete implementation

---

## Testing Checklist

After all tasks complete, verify:

- [ ] CI runs lint + test in parallel (total time <5 min)
- [ ] Build cache works (2nd run ~1-2 min faster)
- [ ] Cannot push directly to main
- [ ] PR with failing tests blocks merge
- [ ] Release workflow creates GitHub release + Docker image
- [ ] Security scans run weekly and on PRs
- [ ] All CI badges green in README

---

## Rollback Plan

If issues arise:

**KAN-76 (Lint):**
```bash
# Disable lint job temporarily
git revert <commit-sha>
```

**KAN-77 (Cache):**
```bash
# Remove cache configuration
# CI will work without cache, just slower
```

**KAN-78 (Branch protection):**
- Disable in GitHub settings temporarily

**KAN-79 (Release):**
```bash
# Delete problematic tag
git tag -d v<version>
git push origin :refs/tags/v<version>
```

---

## Metrics

Target metrics after full implementation:

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| CI time (cache hit) | 3-4 min | 1-2 min | ~50% faster |
| Lint coverage | 0% | 100% | ✅ |
| Security scanning | None | 3 tools | ✅ |
| Branch protection | None | Full | ✅ |
| Release automation | Manual | Automated | ✅ |
| Code formatting | Inconsistent | Enforced | ✅ |

---

## Notes

- **Dependencies:** KAN-77 depends on KAN-76 (merged Dockerfile fixes)
- **Order:** Recommend completing in ticket order for logical progression
- **Time budget:** Full KAN-40 completion: ~4-5 hours total
- **Integration:** Works with KAN-36 (deployment) once K8s configs exist
