#!/bin/bash
set -e

# Release script for superdoc-benchmark
# Usage: ./scripts/release.sh 0.2.0
#
# For signed releases, set these environment variables:
#   APPLE_SIGNING_IDENTITY           - e.g., "Developer ID Application: Your Name (TEAM_ID)"
#   APPLE_INSTALLER_SIGNING_IDENTITY - e.g., "Developer ID Installer: Your Name (TEAM_ID)"
#
# Notarization credentials should be stored in Keychain (one-time setup):
#   xcrun notarytool store-credentials "notary-profile" \
#     --apple-id "your@email.com" \
#     --team-id "XXXXXXXXXX" \
#     --password "app-specific-password"
#
# If signing identities are not set, the binary will be unsigned.

VERSION=$1
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENTITLEMENTS="$SCRIPT_DIR/entitlements.plist"

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
if [ -n "$APPLE_SIGNING_IDENTITY" ] && [ -n "$APPLE_INSTALLER_SIGNING_IDENTITY" ]; then
    SIGNING_ENABLED=true
    echo "Code signing: $APPLE_SIGNING_IDENTITY"
    echo "Installer signing: $APPLE_INSTALLER_SIGNING_IDENTITY"
elif [ -n "$APPLE_SIGNING_IDENTITY" ]; then
    echo "Warning: APPLE_SIGNING_IDENTITY set but APPLE_INSTALLER_SIGNING_IDENTITY missing"
    echo "Signing: disabled (need both identities for .pkg distribution)"
else
    echo "Signing: disabled (set APPLE_SIGNING_IDENTITY and APPLE_INSTALLER_SIGNING_IDENTITY to enable)"
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
    echo "Signing binary with entitlements..."
    codesign --sign "$APPLE_SIGNING_IDENTITY" \
        --options runtime \
        --timestamp \
        --force \
        --entitlements "$ENTITLEMENTS" \
        dist/superdoc-benchmark

    echo "Verifying signature..."
    codesign --verify --verbose dist/superdoc-benchmark

    echo "Signature details:"
    codesign -dvv dist/superdoc-benchmark 2>&1 | grep -E "(Identifier|Authority|Timestamp)"

    # Create .pkg installer (Apple's recommended format for CLI tools)
    echo "Creating .pkg installer..."

    # Create a temporary directory structure for pkgbuild
    PKG_ROOT=$(mktemp -d)
    mkdir -p "$PKG_ROOT/usr/local/bin"
    cp dist/superdoc-benchmark "$PKG_ROOT/usr/local/bin/"

    # Build the package
    pkgbuild \
        --root "$PKG_ROOT" \
        --identifier "dev.superdoc.benchmark" \
        --version "$VERSION" \
        --install-location "/" \
        --sign "$APPLE_INSTALLER_SIGNING_IDENTITY" \
        dist/superdoc-benchmark-$VERSION.pkg

    rm -rf "$PKG_ROOT"
    echo "Created dist/superdoc-benchmark-$VERSION.pkg"

    # Notarize the .pkg
    echo "Submitting .pkg for notarization (this may take a few minutes)..."
    xcrun notarytool submit dist/superdoc-benchmark-$VERSION.pkg \
        --keychain-profile "notary-profile" \
        --wait

    # Staple the notarization ticket to the .pkg
    echo "Stapling notarization ticket..."
    xcrun stapler staple dist/superdoc-benchmark-$VERSION.pkg

    echo "Package signed, notarized, and stapled!"

    # Create GitHub release with .pkg
    echo "Creating GitHub release..."
    gh release create "v$VERSION" \
        --title "v$VERSION" \
        --generate-notes \
        dist/superdoc-benchmark-$VERSION.pkg
else
    # Unsigned release: create zip for distribution
    echo "Creating unsigned release zip..."
    ditto -c -k --keepParent dist/superdoc-benchmark dist/superdoc-benchmark-macos.zip
    echo "Created dist/superdoc-benchmark-macos.zip"

    echo "Creating GitHub release (unsigned)..."
    gh release create "v$VERSION" \
        --title "v$VERSION" \
        --generate-notes \
        dist/superdoc-benchmark-macos.zip
fi

echo ""
echo "Release v$VERSION complete!"
echo "Download at: $(gh browse -n)/releases/tag/v$VERSION"
