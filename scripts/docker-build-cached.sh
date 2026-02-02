#!/bin/bash
# Build Docker image with BuildKit cache

set -e

CACHE_FROM="${BUILDX_CACHE_FROM:-}"
CACHE_TO="${BUILDX_CACHE_TO:-}"

# Build the image with cache
if [ -n "$CACHE_FROM" ] && [ -n "$CACHE_TO" ]; then
    docker buildx build \
        --cache-from="$CACHE_FROM" \
        --cache-to="$CACHE_TO" \
        --load \
        -t agent_bus:latest \
        -f Dockerfile \
        .
else
    docker buildx build \
        --load \
        -t agent_bus:latest \
        -f Dockerfile \
        .
fi
