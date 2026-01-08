#!/bin/bash
set -e

# Release script for superdoc-benchmark
# Usage: ./scripts/release.sh 0.2.0
#
# For signed releases, set these environment variables:
#   APPLE_SIGNING_IDENTITY  - e.g., "Developer ID Application: Your Name (TEAM_ID)"
#   APPLE_ID                - Your Apple ID email
#   APPLE_TEAM_ID           - Your Team ID
#   SUPERDOC_BENCHMARK_APP_PASSWORD      - App-specific password from appleid.apple.com
#
# If not set, the binary will be unsigned.

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

# Check if signing is configured
SIGNING_ENABLED=false
if [ -n "$APPLE_SIGNING_IDENTITY" ] && [ -n "$APPLE_ID" ] && [ -n "$APPLE_TEAM_ID" ] && [ -n "$SUPERDOC_BENCHMARK_APP_PASSWORD" ]; then
    SIGNING_ENABLED=true
    echo "Signing: enabled"
else
    echo "Signing: disabled (set APPLE_* env vars to enable)"
fi

echo "Releasing v$VERSION..."

# Update version in pyproject.toml
sed -i '' "s/^version = \".*\"/version = \"$VERSION\"/" pyproject.toml
echo "Updated pyproject.toml to version $VERSION"

# Commit version bump (if there are changes)
git add pyproject.toml
git diff --cached --quiet || git commit -m "chore: bump version to $VERSION"

# Create and push tag
if git rev-parse "v$VERSION" >/dev/null 2>&1; then
    echo "Tag v$VERSION already exists"
else
    git tag "v$VERSION"
fi
git push origin main
git push origin "v$VERSION"
echo "Pushed tag v$VERSION"

# Build binary
echo "Building binary..."
uv run pyinstaller superdoc-benchmark.spec --noconfirm
echo "Binary built at dist/superdoc-benchmark"

# Sign and notarize if configured
if [ "$SIGNING_ENABLED" = true ]; then
    echo "Signing binary..."
    codesign --sign "$APPLE_SIGNING_IDENTITY" \
        --options runtime \
        --timestamp \
        --force \
        dist/superdoc-benchmark

    echo "Verifying signature..."
    codesign --verify --verbose dist/superdoc-benchmark

    echo "Submitting for notarization (this may take a few minutes)..."
    ditto -c -k --keepParent dist/superdoc-benchmark dist/superdoc-benchmark-notarize.zip

    xcrun notarytool submit dist/superdoc-benchmark-notarize.zip \
        --apple-id "$APPLE_ID" \
        --team-id "$APPLE_TEAM_ID" \
        --password "$SUPERDOC_BENCHMARK_APP_PASSWORD" \
        --wait

    rm dist/superdoc-benchmark-notarize.zip
    echo "Binary signed and notarized!"
fi

# Create zip for release (preserves executable permission)
echo "Creating release zip..."
cd dist && zip -r superdoc-benchmark-macos.zip superdoc-benchmark && cd ..
echo "Created dist/superdoc-benchmark-macos.zip"

# Create GitHub release with zip
echo "Creating GitHub release..."
gh release create "v$VERSION" \
    --title "v$VERSION" \
    --generate-notes \
    dist/superdoc-benchmark-macos.zip

echo ""
echo "Release v$VERSION complete!"
echo "Download at: $(gh browse -n)/releases/tag/v$VERSION"
