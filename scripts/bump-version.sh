#!/bin/bash
set -e

VERSION=$1
if [ -z "$VERSION" ]; then
  echo "Usage: ./scripts/bump-version.sh <version>"
  exit 1
fi

# Update pyproject.toml
sed -i '' "s/^version = .*/version = \"${VERSION}\"/" pyproject.toml

# Update npm/package.json
sed -i '' "s/\"version\": .*/\"version\": \"${VERSION}\",/" npm/package.json

# Update __init__.py version
sed -i '' "s/__version__ = .*/__version__ = \"${VERSION}\"/" src/superdoc_benchmark/__init__.py

echo "Version bumped to ${VERSION}"
echo ""
echo "Next steps:"
echo "  git add -A"
echo "  git commit -m 'chore: bump version to ${VERSION}'"
echo "  git tag v${VERSION}"
echo "  git push && git push --tags"
