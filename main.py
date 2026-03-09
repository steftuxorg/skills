#!/usr/bin/env python3
"""
OpenSkills Agency - GitHub Skills Scraper
Scrapes SKILL.md files from multiple GitHub repositories
and generates a JSON data file.
"""

import os
import re
import json
import tempfile
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
from collections import Counter
from dotenv import load_dotenv
from github import Github, GithubException, Auth
import time
from skill_scanner import SkillScanner
from skill_scanner.core.analyzers import BehavioralAnalyzer

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN not found in .env file")

# Initialize GitHub client
auth = Auth.Token(GITHUB_TOKEN)
g = Github(auth=auth)


# Load repository configurations from repos.json
def load_repos() -> List[Dict]:
    """Load repository configurations from repos.json file."""
    repos_file = Path(__file__).parent / "repos.json"
    with open(repos_file, "r", encoding="utf-8") as f:
        return json.load(f)


# Load category keywords from categories.json
def load_categories() -> Dict[str, List[str]]:
    """Load category keywords from categories.json file."""
    categories_file = Path(__file__).parent / "categories.json"
    with open(categories_file, "r", encoding="utf-8") as f:
        return json.load(f)


REPOS = load_repos()
CATEGORY_KEYWORDS = load_categories()

# Common license patterns
LICENSE_PATTERNS = {
    r"\bMIT\b": "MIT",
    r"\bApache[- ](?:License[- ])?(?:Version[- ])?2\.0\b": "Apache-2.0",
    r"\bGPL[- ]?3\b": "GPL-3.0",
    r"\bGPL[- ]?2\b": "GPL-2.0",
    r"\bBSD[- ]3\b": "BSD-3-Clause",
    r"\bBSD[- ]2\b": "BSD-2-Clause",
    r"\bISC\b": "ISC",
    r"\bMPL[- ]2\.0\b": "MPL-2.0",
    r"\bCC0\b": "CC0-1.0",
    r"\bunlicense": "Unlicense",
}


def extract_license_from_frontmatter(content: str) -> Optional[str]:
    """Extract license from YAML frontmatter."""
    frontmatter_match = re.match(
        r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL
    )
    if frontmatter_match:
        frontmatter = frontmatter_match.group(1)
        # Look for license field in YAML frontmatter
        license_match = re.search(
            r"^license:\s*(.+?)$", frontmatter, re.MULTILINE
        )
        if license_match:
            license_info = license_match.group(1).strip()
            # Remove quotes if present
            license_info = license_info.strip("\"'")
            if license_info:
                # Normalize "MIT License" to "MIT"
                if license_info == "MIT License":
                    return "MIT"
                return license_info
    return None


def extract_license_from_file(repo, skill_dir_path: str) -> Optional[str]:
    """Extract license from LICENSE file in skill directory."""
    try:
        # Get contents of the skill directory
        dir_contents = repo.get_contents(skill_dir_path)

        # Look for LICENSE files
        for item in dir_contents:
            if item.type == "file" and item.name.upper().startswith("LICENSE"):
                # Read the LICENSE file
                license_content = item.decoded_content.decode("utf-8")

                # Extract first or second meaningful line (skip empty lines)
                lines = [
                    line.strip()
                    for line in license_content.split("\n")
                    if line.strip()
                ]

                if len(lines) >= 1:
                    # Return first line; use two if first is very short
                    first_line = lines[0]
                    if len(first_line) < 20 and len(lines) >= 2:
                        license_text = f"{first_line} {lines[1]}"
                    else:
                        license_text = first_line

                    # Normalize "MIT License" to "MIT"
                    if license_text == "MIT License":
                        return "MIT"
                    return license_text

    except Exception:
        pass

    return None


def extract_license_from_referenced_file(
    repo, skill_dir_path: str, content: str
) -> Optional[str]:
    """
    Check SKILL.md content for references to license files (e.g., LICENSE.txt).
    If found, fetch the file and extract the first or second meaningful line.
    This is used as a fallback when no direct license info is
    found in SKILL.md.
    """
    # Look for license file references in the content
    # Pattern: LICENSE.txt, LICENSE.md, etc. in the content
    license_file_pattern = r"\b(LICENSE(?:\.[a-zA-Z0-9]+)?)\b"
    matches = re.findall(license_file_pattern, content, re.IGNORECASE)

    if not matches:
        return None

    # Try to fetch each referenced license file
    for license_filename in set(matches):  # Use set to avoid duplicates
        try:
            # Construct the full path to the license file
            license_path = f"{skill_dir_path}/{license_filename}"

            # Get the license file from GitHub
            license_file = repo.get_contents(license_path)
            license_content = license_file.decoded_content.decode("utf-8")

            # Extract first or second meaningful line (skip empty lines)
            lines = [
                line.strip()
                for line in license_content.split("\n")
                if line.strip()
            ]

            if len(lines) >= 1:
                # Return first line; use two if first is very short
                first_line = lines[0]
                if len(first_line) < 20 and len(lines) >= 2:
                    license_text = f"{first_line} {lines[1]}"
                else:
                    license_text = first_line

                # Normalize "MIT License" to "MIT"
                if license_text == "MIT License":
                    return "MIT"
                return license_text

        except Exception:
            continue

    return None


def extract_license(
    content: str, repo, skill_dir_path: str, repo_license: Optional[str] = None
) -> str:
    """Extract license information from multiple sources."""
    # 1. Check YAML frontmatter first
    frontmatter_license = extract_license_from_frontmatter(content)
    if frontmatter_license:
        return frontmatter_license

    # 2. Check for LICENSE file in skill directory
    file_license = extract_license_from_file(repo, skill_dir_path)
    if file_license:
        return file_license

    # 3. Check content for license patterns
    for pattern, license_name in LICENSE_PATTERNS.items():
        if re.search(pattern, content, re.IGNORECASE):
            return license_name

    # 4. NEW: Check if SKILL.md references a license file and fetch it
    referenced_license = extract_license_from_referenced_file(
        repo, skill_dir_path, content
    )
    if referenced_license:
        return referenced_license

    # 5. Fall back to repository license
    if repo_license:
        return repo_license

    return "Unknown"


def generate_summary(content: str, max_length: int = 150) -> str:
    """Generate a summary from SKILL.md content."""
    # Check for YAML frontmatter with description field
    frontmatter_match = re.match(
        r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL
    )
    if frontmatter_match:
        frontmatter = frontmatter_match.group(1)
        # Look for description field in YAML frontmatter
        desc_match = re.search(
            r"^description:\s*(.+?)$", frontmatter, re.MULTILINE
        )
        if desc_match:
            description = desc_match.group(1).strip()
            # Remove quotes if present
            description = description.strip("\"'")
            if description and len(description) > 10:
                return description

    # Remove markdown headers and code blocks
    content = re.sub(r"^#+\s+", "", content, flags=re.MULTILINE)
    content = re.sub(r"```[\s\S]*?```", "", content)

    # Get first meaningful paragraph
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

    for para in paragraphs:
        # Skip very short paragraphs or those that look like metadata
        if len(para) > 30 and not para.startswith(("---", "<!--", "{")):
            # Clean up and truncate
            summary = " ".join(para.split())
            if len(summary) > max_length:
                summary = summary[:max_length].rsplit(" ", 1)[0] + "..."
            return summary

    # Fallback
    return "No description available"


def categorize_skill(name: str, content: str, max_tags: int = 5) -> List[str]:
    """Auto-generate tags based on skill name and content."""
    text = (name + " " + content).lower()

    # Count keyword matches
    tag_scores = Counter()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                tag_scores[category] += text.count(keyword)

    # Get top tags
    tags = [tag for tag, _ in tag_scores.most_common(max_tags)]

    # Ensure at least 2 tags
    if len(tags) < 2:
        tags.extend(["general", "utility"])

    return tags[:max_tags]


def extract_snyk_labels(snyk_result: Dict) -> Dict:
    """Extract only the 4 specific labels from Snyk scanner output."""
    try:
        # Navigate through the Snyk result structure to find labels
        # Structure:
        # {"<path>": {"servers": [...], "labels": [[{labels_dict}]]}}
        for path_key, path_data in snyk_result.items():
            if isinstance(path_data, dict) and "labels" in path_data:
                labels_list = path_data["labels"]
                if (
                    labels_list
                    and isinstance(labels_list, list)
                    and len(labels_list) > 0
                ):
                    # labels is a list of lists, get the first inner list
                    inner_labels = labels_list[0]
                    if (
                        inner_labels
                        and isinstance(inner_labels, list)
                        and len(inner_labels) > 0
                    ):
                        # Get the first label dict
                        labels_dict = inner_labels[0]
                        if isinstance(labels_dict, dict):
                            # Extract only the 4 required labels
                            return {
                                "is_public_sink": labels_dict.get(
                                    "is_public_sink", 0
                                ),
                                "destructive": labels_dict.get(
                                    "destructive", 0
                                ),
                                "untrusted_content": labels_dict.get(
                                    "untrusted_content", 0
                                ),
                                "private_data": labels_dict.get(
                                    "private_data", 0
                                ),
                            }

        # If we couldn't find labels in the expected structure, return defaults
        return {
            "is_public_sink": 0,
            "destructive": 0,
            "untrusted_content": 0,
            "private_data": 0,
            "note": "Labels not found in expected structure",
        }
    except Exception as e:
        return {
            "error": f"Failed to extract labels: {str(e)}",
            "is_public_sink": 0,
            "destructive": 0,
            "untrusted_content": 0,
            "private_data": 0,
        }


def find_skill_files(
    repo, base_path: str, is_wildcard: bool = False
) -> List[Dict]:
    """Find all SKILL.md files in a repository path."""
    skills = []

    try:
        if is_wildcard:
            # Handle wildcard paths like plugins/*/skills
            parts = base_path.split("/*/")
            if len(parts) == 2:
                parent_path, child_path = parts
                try:
                    contents = repo.get_contents(parent_path)
                    for item in contents:
                        if item.type == "dir":
                            skill_path = (
                                f"{parent_path}/{item.name}/{child_path}"
                            )
                            skills.extend(
                                find_skill_files(repo, skill_path, False)
                            )
                except GithubException:
                    pass
            return skills

        # Regular path handling
        try:
            contents = repo.get_contents(base_path)
        except GithubException:
            print(f"  ⚠️  Path not found: {base_path}")
            return skills

        # Process contents
        if not isinstance(contents, list):
            contents = [contents]

        for content in contents:
            if content.type == "dir":
                # Check if this directory contains SKILL.md
                try:
                    dir_contents = repo.get_contents(content.path)
                    for file in dir_contents:
                        if file.name.upper() == "SKILL.MD":
                            skills.append({
                                "name": content.name,
                                "path": file.path,
                                "file": file,
                            })
                            break
                except GithubException:
                    pass

    except Exception as e:
        print(f"  ❌ Error processing path {base_path}: {e}")

    return skills


# Spinner characters emitted by the Snyk CLI progress indicator.
_SNYK_SPINNER_CHARS = frozenset("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏")


def _is_snyk_spinner_line(line: str) -> bool:
    """Return True if *line* contains a Snyk CLI spinner character."""
    return bool(_SNYK_SPINNER_CHARS.intersection(line))


def _parse_snyk_stdout(stdout: str) -> Dict:
    """
    Extract and parse the JSON object embedded in Snyk CLI output.

    The CLI mixes spinner/progress lines with the JSON payload.  This
    function strips those lines and returns the parsed dict, or raises
    ``json.JSONDecodeError`` / ``ValueError`` on failure.
    """
    lines = stdout.strip().split("\n")
    json_lines: List[str] = []
    in_json = False
    brace_count = 0

    for line in lines:
        if _is_snyk_spinner_line(line):
            continue

        for char in line:
            if char == "{":
                if not in_json:
                    in_json = True
                    json_lines = []
                brace_count += 1
            elif char == "}":
                brace_count -= 1

        if in_json:
            json_lines.append(line)

        if in_json and brace_count == 0:
            break

    if json_lines:
        return json.loads("\n".join(json_lines))

    # Fallback: slice between first '{' and last '}'
    json_start = stdout.find("{")
    json_end = stdout.rfind("}")
    if json_start != -1 and json_end != -1:
        raw = stdout[json_start:json_end + 1]
        clean = "\n".join(
            ln for ln in raw.split("\n")
            if not _is_snyk_spinner_line(ln)
        )
        return json.loads(clean)

    raise ValueError("No valid JSON found in Snyk output")


def run_cisco_scan(skill_path: Path) -> Dict:
    """
    Run the Cisco AI Defense (SkillScanner) on *skill_path*.

    Returns a serialisable dict with keys:
    ``findings_count``, ``max_severity``, ``is_safe``, ``findings``.
    On failure the dict contains an ``error`` key instead of ``findings``.
    """
    try:
        scanner = SkillScanner(analyzers=[BehavioralAnalyzer()])
        scan_result = scanner.scan_skill(str(skill_path))
        return {
            "findings_count": len(scan_result.findings),
            "max_severity": str(scan_result.max_severity),
            "is_safe": scan_result.is_safe,
            "findings": [
                {
                    "severity": str(finding.severity),
                    "category": finding.category,
                    "title": finding.title,
                    "description": finding.description,
                    "file": finding.file_path,
                    "line": finding.line_number,
                }
                for finding in scan_result.findings
            ],
        }
    except Exception as exc:
        print(f"      ⚠️  Cisco scanner warning: {exc}")
        return {
            "error": str(exc),
            "findings_count": 0,
            "max_severity": "UNKNOWN",
            "is_safe": None,
        }


def run_snyk_scan(skill_md_path: Path) -> Dict:
    """
    Run the Snyk agent scanner on *skill_md_path*.

    Returns the four security labels extracted by :func:`extract_snyk_labels`,
    or a dict with an ``error`` key when the scan cannot be completed.
    """
    cmd = [
        "uvx",
        "snyk-agent-scan@latest",
        "inspect",
        "--json",
        "--skills",
        str(skill_md_path),
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if not result.stdout:
            return {"error": "No output from Snyk scanner"}

        try:
            snyk_result = _parse_snyk_stdout(result.stdout)
        except (json.JSONDecodeError, ValueError) as exc:
            return {
                "error": f"Failed to parse Snyk output: {exc}",
                "raw_output": result.stdout[:500],
            }

        return extract_snyk_labels(snyk_result)

    except subprocess.TimeoutExpired:
        return {"error": "Snyk scanner timeout"}
    except Exception as exc:
        return {"error": f"Snyk scanner error: {exc}"}


def _download_skill_directory(
    repo, skill_dir_path: str, skill_path: Path
) -> None:
    """
    Download all non-SKILL.md files from *skill_dir_path* into *skill_path*.

    Silently ignores errors so that processing continues with just SKILL.md
    when ancillary files are unavailable.
    """
    try:
        dir_contents = repo.get_contents(skill_dir_path)
        for item in dir_contents:
            if item.type == "file" and item.name.upper() != "SKILL.MD":
                dest = skill_path / item.name
                dest.write_bytes(item.decoded_content)
    except Exception:
        pass


def _run_scanners(
    repo,
    skill_dir_path: str,
    skill_name: str,
    content: str,
) -> tuple:
    """
    Prepare a temporary directory and run both security scanners.

    Returns ``(scan_data, snyk_data)`` — each is either a result dict or
    an error dict if the corresponding scanner failed.
    """
    scan_data: Optional[Dict] = None
    snyk_data: Optional[Dict] = None

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            skill_path = Path(temp_dir) / skill_name
            skill_path.mkdir()

            skill_md_path = skill_path / "SKILL.md"
            skill_md_path.write_text(content, encoding="utf-8")

            _download_skill_directory(repo, skill_dir_path, skill_path)

            scan_data = run_cisco_scan(skill_path)
            snyk_data = run_snyk_scan(skill_md_path)

    except Exception as exc:
        print(f"      ⚠️  Temp directory error: {exc}")
        if scan_data is None:
            scan_data = {
                "error": f"Temp directory error: {exc}",
                "findings_count": 0,
                "max_severity": "UNKNOWN",
                "is_safe": None,
            }
        if snyk_data is None:
            snyk_data = {"error": f"Temp directory error: {exc}"}

    return scan_data, snyk_data


def scrape_repository(repo_config: Dict) -> List[Dict]:
    """Scrape skills from a single repository."""
    owner = repo_config["owner"]
    repo_name = repo_config["repo"]
    path = repo_config["path"]
    enabled = repo_config.get("enabled", True)

    if not enabled:
        print(f"\n⏭️  Skipping {owner}/{repo_name} (disabled)")
        return []

    print(f"\n📦 Processing {owner}/{repo_name}")

    try:
        repo = g.get_repo(f"{owner}/{repo_name}")

        stars = repo.stargazers_count
        repo_license = repo.license.spdx_id if repo.license else None

        print(f"  ⭐ Stars: {stars}")
        print(f"  📄 License: {repo_license or 'Unknown'}")

        is_wildcard = "/*/" in path
        skill_files = find_skill_files(repo, path, is_wildcard)

        print(f"  📝 Found {len(skill_files)} skills")

        skills_data = []

        for skill_info in skill_files:
            try:
                skill_name = skill_info["name"]
                skill_file = skill_info["file"]

                content = skill_file.decoded_content.decode("utf-8")

                commits = repo.get_commits(path=skill_file.path)
                latest_commit = (
                    commits[0].sha[:7] if commits.totalCount > 0 else "unknown"
                )

                skill_dir_path = "/".join(skill_file.path.split("/")[:-1])

                license_info = extract_license(
                    content, repo, skill_dir_path, repo_license
                )
                summary = generate_summary(content)
                tags = categorize_skill(skill_name, content)

                scan_data, snyk_data = _run_scanners(
                    repo, skill_dir_path, skill_name, content
                )

                skill_data = {
                    "name": skill_name,
                    "creator": owner,
                    "category": tags,
                    "summary": summary,
                    "url": skill_file.html_url,
                    "license": license_info,
                    "trust": stars,
                    "version": latest_commit,
                    "repo": f"{owner}/{repo_name}",
                    "security-scanners": {
                        "cisco-ai-defense": scan_data,
                        "snyk": snyk_data,
                    },
                }

                skills_data.append(skill_data)
                print(f"    ✓ {skill_name}")

                time.sleep(0.1)  # Rate limiting protection

            except Exception as exc:
                print(f"    ✗ Error processing {skill_info['name']}: {exc}")

        return skills_data

    except GithubException as exc:
        print(f"  ❌ Repository error: {exc}")
        return []
    except Exception as exc:
        print(f"  ❌ Unexpected error: {exc}")
        return []


def main():
    """Main scraper function."""
    print("=" * 60)
    print("OpenSkills Agency - GitHub Skills Scraper")
    print("=" * 60)

    all_skills = []

    for repo_config in REPOS:
        skills = scrape_repository(repo_config)
        all_skills.extend(skills)
        time.sleep(0.5)  # Be nice to GitHub API

    print("\n" + "=" * 60)
    print(f"✅ Total skills collected: {len(all_skills)}")
    print("=" * 60)

    # Save to JSON
    output_path = Path(__file__).parent.parent / "public" / "skills-data.json"
    output_path.parent.mkdir(exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_skills, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Data saved to: {output_path}")
    print(f"📊 File size: {output_path.stat().st_size / 1024:.2f} KB")

    # Print statistics
    print("\n📈 Statistics:")
    print(f"  - Unique creators: {len(set(s['creator'] for s in all_skills))}")
    print(f"  - Unique licenses: {len(set(s['license'] for s in all_skills))}")

    # Top categories
    all_tags = []
    for skill in all_skills:
        all_tags.extend(skill["category"])
    tag_counts = Counter(all_tags)
    top = ", ".join(
        f"{tag}({count})"
        for tag, count in tag_counts.most_common(5)
    )
    print(f"  - Top categories: {top}")


if __name__ == "__main__":
    main()
