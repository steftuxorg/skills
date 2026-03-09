#!/usr/bin/env python3
"""
Populate repos.json with metadata (stars) from GitHub API.
This is a one-time/periodic utility script that uses PyGithub.

Usage:
    GITHUB_TOKEN=your_token python scripts/populate_metadata.py

Or with .env file:
    python scripts/populate_metadata.py
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
from github import Github, GithubException, Auth

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    print("❌ Error: GITHUB_TOKEN not found in environment or .env file")
    print("   Create a GitHub personal access token with 'public_repo' access")
    print("   Then run: GITHUB_TOKEN=your_token python scripts/populate_metadata.py")
    sys.exit(1)

# Initialize GitHub client
auth = Auth.Token(GITHUB_TOKEN)
g = Github(auth=auth)


def fetch_repo_metadata(owner: str, repo: str) -> Optional[Dict]:
    """Fetch stars from GitHub API."""
    try:
        print(f"  Fetching {owner}/{repo}...", end=" ")
        repo_obj = g.get_repo(f"{owner}/{repo}")

        stars = repo_obj.stargazers_count

        print(f"⭐ {stars} stars")

        return {"stars": stars}

    except GithubException as e:
        print(f"❌ Error: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None


def main():
    """Main function to populate metadata in repos.json."""
    print("=" * 60)
    print("Populate repos.json with GitHub Metadata")
    print("=" * 60)

    # Load repos.json
    repos_file = Path(__file__).parent.parent / "repos.json"

    if not repos_file.exists():
        print(f"❌ Error: {repos_file} not found")
        sys.exit(1)

    with open(repos_file, "r", encoding="utf-8") as f:
        repos = json.load(f)

    print(f"\n📋 Found {len(repos)} repositories in repos.json")

    # Fetch metadata for each repo
    updated_count = 0
    skipped_count = 0
    error_count = 0

    for repo_config in repos:
        owner = repo_config["owner"]
        repo_name = repo_config["repo"]

        # Skip if metadata already exists and user doesn't want to override
        if "stars" in repo_config:
            print(f"  ⏭️  {owner}/{repo_name} - metadata already exists (skipping)")
            skipped_count += 1
            continue

        # Fetch metadata
        metadata = fetch_repo_metadata(owner, repo_name)

        if metadata:
            repo_config["stars"] = metadata["stars"]
            updated_count += 1
        else:
            error_count += 1

    # Save updated repos.json
    if updated_count > 0:
        with open(repos_file, "w", encoding="utf-8") as f:
            json.dump(repos, f, indent=2, ensure_ascii=False)
            f.write("\n")  # Add trailing newline

        print(f"\n✅ Updated {repos_file}")

    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  ✅ Updated: {updated_count}")
    print(f"  ⏭️  Skipped: {skipped_count}")
    print(f"  ❌ Errors: {error_count}")
    print("=" * 60)

    if updated_count > 0:
        print("\n💡 Next steps:")
        print("   1. Review the updated repos.json")
        print("   2. Run main.py to process skills")

    # Check rate limit
    try:
        rate_limit = g.get_rate_limit()
        core = rate_limit.core if hasattr(rate_limit, "core") else rate_limit
        print(f"\n📊 GitHub API Rate Limit: {core.remaining}/{core.limit}")
    except Exception:
        print("\n📊 GitHub API Rate Limit: (unable to fetch)")


if __name__ == "__main__":
    main()
