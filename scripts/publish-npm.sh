#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
PACKAGE_JSON="$ROOT_DIR/npm/package.json"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required. Install from https://github.com/astral-sh/uv"
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required. Install Node.js first."
  exit 1
fi

ARCH="$(uname -m)"
if [ "$ARCH" != "arm64" ]; then
  echo "This script only supports Apple Silicon (arm64)."
  exit 1
fi
NPM_ARCH="arm64"

cd "$ROOT_DIR"

echo "Building $NPM_ARCH binary..."
uv run pyinstaller superdoc-benchmark.spec --noconfirm

LOCAL_TARBALL="$ROOT_DIR/dist/superdoc-benchmark-darwin-$NPM_ARCH.tar.gz"

echo "Packaging $NPM_ARCH tarball: $LOCAL_TARBALL"
tar -czf "$LOCAL_TARBALL" -C "$ROOT_DIR/dist" superdoc-benchmark

cd "$ROOT_DIR/npm"
npm run publish
