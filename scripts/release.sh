#!/bin/bash
set -euo pipefail

# Release script for agent_bus
# Usage: ./scripts/release.sh [patch|minor|major]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Check if we're on main branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "main" ]; then
    error "Must be on main branch to create a release. Current branch: $CURRENT_BRANCH"
fi

# Check if working directory is clean
if [ -n "$(git status --porcelain)" ]; then
    error "Working directory is not clean. Commit or stash changes first."
fi

# Pull latest changes
info "Pulling latest changes from origin/main..."
git pull origin main

# Get the latest tag
LATEST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
info "Latest tag: $LATEST_TAG"

# Parse version
VERSION=${LATEST_TAG#v}
IFS='.' read -r MAJOR MINOR PATCH <<< "$VERSION"

# Determine bump type
BUMP_TYPE=${1:-patch}

case $BUMP_TYPE in
    major)
        MAJOR=$((MAJOR + 1))
        MINOR=0
        PATCH=0
        ;;
    minor)
        MINOR=$((MINOR + 1))
        PATCH=0
        ;;
    patch)
        PATCH=$((PATCH + 1))
        ;;
    *)
        error "Invalid bump type: $BUMP_TYPE. Use: major, minor, or patch"
        ;;
esac

NEW_VERSION="v${MAJOR}.${MINOR}.${PATCH}"
info "New version: $NEW_VERSION"

# Confirm
read -p "Create and push tag $NEW_VERSION? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    warn "Aborted by user"
    exit 0
fi

# Generate changelog since last tag
info "Generating changelog..."
if [ "$LATEST_TAG" != "v0.0.0" ]; then
    CHANGELOG=$(git log ${LATEST_TAG}..HEAD --pretty=format:"- %s (%h)" --no-merges)
else
    CHANGELOG=$(git log --pretty=format:"- %s (%h)" --no-merges)
fi

echo ""
echo "Changelog:"
echo "$CHANGELOG"
echo ""

# Create annotated tag
info "Creating tag..."
git tag -a "$NEW_VERSION" -m "Release $NEW_VERSION

$CHANGELOG"

# Push tag
info "Pushing tag to origin..."
git push origin "$NEW_VERSION"

info "✅ Release $NEW_VERSION created and pushed!"
info "GitHub Actions will now:"
info "  1. Build and push Docker image"
info "  2. Create GitHub release with changelog"
info "  3. Deploy to staging environment (stub)"
info ""
info "Monitor the workflow at:"
info "  https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]\(.*\)\.git/\1/')/actions"
