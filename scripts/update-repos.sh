#!/bin/bash
# Batch update all repositories from repos.json
# Usage: ./scripts/update-repos.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
REPOS_JSON="$PROJECT_DIR/repos.json"

echo "🔄 Updating all enabled repositories from repos.json"
echo "=================================================="

# Check if repos.json exists
if [ ! -f "$REPOS_JSON" ]; then
    echo "❌ Error: $REPOS_JSON not found"
    exit 1
fi

# Check if jq is available
if ! command -v jq &> /dev/null; then
    echo "⚠️  jq not found, falling back to Python parser"
    USE_JQ=false
else
    USE_JQ=true
fi

# Counters
SUCCESS_COUNT=0
ERROR_COUNT=0
SKIPPED_COUNT=0

# Parse repos.json and process each enabled repo
if [ "$USE_JQ" = true ]; then
    # Use jq to parse JSON
    mapfile -t REPOS < <(jq -c '.[] | select(.enabled == true)' "$REPOS_JSON")
    
    for repo_json in "${REPOS[@]}"; do
        owner=$(echo "$repo_json" | jq -r '.owner')
        repo=$(echo "$repo_json" | jq -r '.repo')
        path=$(echo "$repo_json" | jq -r '.path')
        
        echo ""
        echo "📦 Processing: $owner/$repo"
        
        if "$SCRIPT_DIR/update-repo.sh" "$owner" "$repo" "$path"; then
            ((SUCCESS_COUNT++))
        else
            echo "❌ Failed to update $owner/$repo"
            ((ERROR_COUNT++))
        fi
    done
else
    # Fallback: Use Python to parse JSON
    python3 <<'EOF'
import json
import sys
import subprocess

with open(sys.argv[1], 'r') as f:
    repos = json.load(f)

success = 0
errors = 0

for repo in repos:
    if not repo.get('enabled', True):
        continue
    
    owner = repo['owner']
    repo_name = repo['repo']
    path = repo['path']
    
    print(f"\n📦 Processing: {owner}/{repo_name}")
    
    result = subprocess.run(
        [f"{sys.argv[2]}/update-repo.sh", owner, repo_name, path],
        capture_output=False
    )
    
    if result.returncode == 0:
        success += 1
    else:
        print(f"❌ Failed to update {owner}/{repo_name}")
        errors += 1

print(f"\n{'='*50}")
print(f"✅ Success: {success}")
print(f"❌ Errors: {errors}")
print(f"{'='*50}")
EOF
    exit 0
fi

# Summary
echo ""
echo "=================================================="
echo "Summary:"
echo "  ✅ Success: $SUCCESS_COUNT"
echo "  ❌ Errors: $ERROR_COUNT"
echo "=================================================="

if [ $ERROR_COUNT -gt 0 ]; then
    echo ""
    echo "⚠️  Some repositories failed to update."
    echo "   Check the error messages above for details."
    exit 1
fi

echo ""
echo "✅ All repositories updated successfully!"
