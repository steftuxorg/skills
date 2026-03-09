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

# Check if repository already exists
if [ -d "$TARGET_DIR/.git" ]; then
    echo "📥 Repository exists - pulling updates..."
    cd "$TARGET_DIR"
    
    # Detect current branch
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
    
    # Pull latest changes
    if git pull --depth 1 --quiet origin "$CURRENT_BRANCH" 2>/dev/null; then
        echo "✅ Updated $TARGET_DIR"
        exit 0
    else
        echo "⚠️  Pull failed, attempting fresh clone..."
        cd "$OLDPWD"
        rm -rf "$TARGET_DIR"
        # Continue to clone logic below
    fi
fi

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
# Check if path contains wildcard
if [[ "$SPARSE_PATH" == *"/*/"* ]]; then
    # For wildcard paths like "plugins/*/skills", extract parent directory
    # and include all subdirectories
    PARENT_DIR=$(echo "$SPARSE_PATH" | sed 's|/\*/.*||')
    echo "$PARENT_DIR/*" >> .git/info/sparse-checkout
else
    echo "$SPARSE_PATH/*" >> .git/info/sparse-checkout
fi

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

# Verify path exists (skip for wildcard paths)
if [[ "$SPARSE_PATH" != *"/*/"* ]]; then
  if [ ! -d "$SPARSE_PATH" ]; then
    echo "❌ Error: Path '$SPARSE_PATH' not found in $OWNER/$REPO"
    echo "Available paths:"
    find . -maxdepth 3 -type d | grep -v "^./.git" | head -20
    exit 1
  fi
else
  # For wildcard paths, verify parent directory exists
  PARENT_DIR=$(echo "$SPARSE_PATH" | sed 's|/\*/.*||')
  if [ ! -d "$PARENT_DIR" ]; then
    echo "❌ Error: Parent path '$PARENT_DIR' not found in $OWNER/$REPO"
    exit 1
  fi
fi

# Return to original directory
cd "$OLDPWD"

# Create target directory structure
mkdir -p "$(dirname "$TARGET_DIR")"

# Sync to target directory (delete removed files)
if [[ "$SPARSE_PATH" == *"/*/"* ]]; then
  # For wildcard paths, sync the parent directory
  PARENT_DIR=$(echo "$SPARSE_PATH" | sed 's|/\*/.*||')
  rsync -a --delete "$TEMP_DIR/$PARENT_DIR/" "$TARGET_DIR/"
else
  rsync -a --delete "$TEMP_DIR/$SPARSE_PATH/" "$TARGET_DIR/"
fi

echo "✅ Updated $TARGET_DIR"
