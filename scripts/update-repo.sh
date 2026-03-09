#!/bin/bash
# Sparse checkout script for shallow cloning specific subdirectories
# Usage: ./update-repo.sh OWNER REPO PATH
# Output structure: repos/OWNER/REPO/

set -euo pipefail  # Exit on error, undefined vars, pipe failures

OWNER=$1
REPO=$2
SPARSE_PATH=$3

# Build target directory: repos/owner/repo
TARGET_DIR="repos/$OWNER/$REPO"

echo "📥 Updating $OWNER/$REPO - path: $SPARSE_PATH"
echo "📂 Target directory: $TARGET_DIR"

# Create temp directory for sparse checkout
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT  # Cleanup on exit

cd "$TEMP_DIR"

# Initialize git with sparse checkout
git init --quiet
git config core.sparseCheckout true

# Add remote
git remote add origin "https://github.com/$OWNER/$REPO.git"

# Configure sparse checkout patterns
echo "$SPARSE_PATH/*" >> .git/info/sparse-checkout

# Detect default branch (main or master)
echo "🔍 Detecting default branch..."
DEFAULT_BRANCH=$(git ls-remote --symref origin HEAD | awk '/^ref:/ {sub(/refs\/heads\//, "", $2); print $2}')

if [ -z "$DEFAULT_BRANCH" ]; then
  echo "❌ Error: Could not detect default branch for $OWNER/$REPO"
  exit 1
fi

echo "📦 Cloning branch: $DEFAULT_BRANCH (shallow, sparse)"

# Shallow clone only the sparse path
git pull --depth 1 --quiet origin "$DEFAULT_BRANCH" || {
  echo "❌ Error: Failed to clone $OWNER/$REPO"
  exit 1
}

# Verify path exists
if [ ! -d "$SPARSE_PATH" ]; then
  echo "❌ Error: Path '$SPARSE_PATH' not found in $OWNER/$REPO"
  echo "Available paths:"
  find . -maxdepth 3 -type d | grep -v "^./.git" | head -20
  exit 1
fi

# Return to original directory
cd "$OLDPWD"

# Create target directory structure
mkdir -p "$(dirname "$TARGET_DIR")"

# Sync to target directory (delete removed files)
rsync -a --delete "$TEMP_DIR/$SPARSE_PATH/" "$TARGET_DIR/"

echo "✅ Updated $TARGET_DIR"
