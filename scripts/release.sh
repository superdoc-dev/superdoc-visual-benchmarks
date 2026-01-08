#!/bin/bash
set -e

# Release script for superdoc-benchmark
# Usage: ./scripts/release.sh 0.2.0

VERSION=$1

if [ -z "$VERSION" ]; then
    echo "Usage: ./scripts/release.sh <version>"
    echo "Example: ./scripts/release.sh 0.2.0"
    exit 1
fi

# Ensure we're on main branch
BRANCH=$(git branch --show-current)
if [ "$BRANCH" != "main" ]; then
    echo "Error: Must be on main branch (currently on $BRANCH)"
    exit 1
fi

echo "Releasing v$VERSION..."

# Update version in pyproject.toml
sed -i '' "s/^version = \".*\"/version = \"$VERSION\"/" pyproject.toml
echo "Updated pyproject.toml to version $VERSION"

# Commit version bump
git add pyproject.toml
git commit -m "chore: bump version to $VERSION"

# Create and push tag
git tag "v$VERSION"
git push origin main
git push origin "v$VERSION"
echo "Pushed tag v$VERSION"

# Build binary
echo "Building binary..."
uv run pyinstaller superdoc-benchmark.spec --noconfirm
echo "Binary built at dist/superdoc-benchmark"

# Create GitHub release with binary
echo "Creating GitHub release..."
gh release create "v$VERSION" \
    --title "v$VERSION" \
    --generate-notes \
    dist/superdoc-benchmark

echo ""
echo "Release v$VERSION complete!"
echo "Download at: $(gh browse -n)/releases/tag/v$VERSION"
