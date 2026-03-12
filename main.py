#!/usr/bin/env python3
"""
OpenSkills Agency - Local Skills Processor
Processes SKILL.md files from locally cloned GitHub repositories
and generates a JSON data file.
"""

import os
import re
import json
import sys
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
from collections import Counter
from skill_scanner import SkillScanner
from skill_scanner.core.analyzers import BehavioralAnalyzer

# Note: GITHUB_TOKEN no longer required for main.py
# Use scripts/populate_metadata.py to update repository metadata


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
    frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if frontmatter_match:
        frontmatter = frontmatter_match.group(1)
        # Look for license field in YAML frontmatter
        license_match = re.search(r"^license:\s*(.+?)$", frontmatter, re.MULTILINE)
        if license_match:
            license_info = license_match.group(1).strip()
            # Remove quotes if present
            license_info = license_info.strip("\"'")
            if license_info:
                # Normalize any license containing "MIT" to just "MIT"
                if re.search(r"\bMIT\b", license_info, re.IGNORECASE):
                    return "MIT"
                return license_info
    return None


def extract_license_from_file_local(skill_dir_path: Path) -> Optional[str]:
    """Extract license from LICENSE file in skill directory."""
    try:
        # Look for LICENSE files (case-insensitive)
        for license_file in skill_dir_path.glob("LICENSE*"):
            if license_file.is_file():
                license_content = license_file.read_text(encoding="utf-8")

                # Extract first or second meaningful line (skip empty lines)
                lines = [
                    line.strip() for line in license_content.split("\n") if line.strip()
                ]

                if len(lines) >= 1:
                    # Return first line; use two if first is very short
                    first_line = lines[0]
                    if len(first_line) < 20 and len(lines) >= 2:
                        license_text = f"{first_line} {lines[1]}"
                    else:
                        license_text = first_line

                    # Normalize any license containing "MIT" to just "MIT"
                    if re.search(r"\bMIT\b", license_text, re.IGNORECASE):
                        return "MIT"
                    return license_text

    except Exception:
        pass

    return None


def extract_license_from_referenced_file_local(
    skill_dir_path: Path, content: str
) -> Optional[str]:
    """
    Check SKILL.md content for references to license files (e.g., LICENSE.txt).
    If found, fetch the file and extract the first or second meaningful line.
    """
    # Look for license file references in the content
    license_file_pattern = r"\b(LICENSE(?:\.[a-zA-Z0-9]+)?)\b"
    matches = re.findall(license_file_pattern, content, re.IGNORECASE)

    if not matches:
        return None

    # Try to fetch each referenced license file
    for license_filename in set(matches):  # Use set to avoid duplicates
        try:
            license_path = skill_dir_path / license_filename

            if not license_path.exists():
                continue

            license_content = license_path.read_text(encoding="utf-8")

            # Extract first or second meaningful line (skip empty lines)
            lines = [
                line.strip() for line in license_content.split("\n") if line.strip()
            ]

            if len(lines) >= 1:
                # Return first line; use two if first is very short
                first_line = lines[0]
                if len(first_line) < 20 and len(lines) >= 2:
                    license_text = f"{first_line} {lines[1]}"
                else:
                    license_text = first_line

                # Normalize any license containing "MIT" to just "MIT"
                if re.search(r"\bMIT\b", license_text, re.IGNORECASE):
                    return "MIT"
                return license_text

        except Exception:
            continue

    return None


def extract_license(content: str, skill_dir_path: Path) -> str:
    """Extract license information from skill sources."""
    # 1. Check YAML frontmatter first
    frontmatter_license = extract_license_from_frontmatter(content)
    if frontmatter_license:
        return frontmatter_license

    # 2. Check for LICENSE file in skill directory
    file_license = extract_license_from_file_local(skill_dir_path)
    if file_license:
        return file_license

    # 3. Check content for license patterns
    for pattern, license_name in LICENSE_PATTERNS.items():
        if re.search(pattern, content, re.IGNORECASE):
            return license_name

    # 4. Check if SKILL.md references a license file and fetch it
    referenced_license = extract_license_from_referenced_file_local(
        skill_dir_path, content
    )
    if referenced_license:
        return referenced_license

    return "Unknown"


def generate_summary(content: str, max_length: int = 150) -> str:
    """Generate a summary from SKILL.md content."""
    # Check for YAML frontmatter with description field
    frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if frontmatter_match:
        frontmatter = frontmatter_match.group(1)
        # Look for description field in YAML frontmatter
        desc_match = re.search(r"^description:\s*(.+?)$", frontmatter, re.MULTILINE)
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


def get_latest_commit_local(repo_path: Path, file_path: Path) -> str:
    """Get latest commit SHA for a file using git log."""
    try:
        rel_path = file_path.relative_to(repo_path)
        result = subprocess.run(
            ["git", "log", "-1", "--format=%h", "--", str(rel_path)],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def find_skill_files_local(repo_path: Path, sparse_path: str) -> List[Dict]:
    """Find all SKILL.md files in local repository path."""
    skills = []

    # Check if wildcard path (contains /*/)
    is_wildcard = "/*/" in sparse_path

    if is_wildcard:
        # Handle wildcard paths like "plugins/*/skills"
        # Split by /*/ to get pattern parts
        parts = sparse_path.split("/*/")
        if len(parts) == 2:
            parent_pattern, child_pattern = parts
            parent_path = repo_path / parent_pattern

            if not parent_path.exists():
                return skills

            # Find all subdirectories matching the pattern
            for subdir in parent_path.iterdir():
                if subdir.is_dir():
                    skill_base = subdir / child_pattern
                    if skill_base.exists():
                        # Look for skill directories within
                        for skill_dir in skill_base.iterdir():
                            if skill_dir.is_dir():
                                skill_md = skill_dir / "SKILL.md"
                                if skill_md.exists():
                                    skills.append(
                                        {
                                            "name": skill_dir.name,
                                            "path": str(
                                                skill_md.relative_to(repo_path)
                                            ),
                                            "file_path": skill_md,
                                        }
                                    )
        return skills

    # Regular path handling (no wildcard)
    # Note: repo_path already points to the sparse checkout result
    # so we search directly in repo_path, not repo_path/sparse_path
    base_path = repo_path

    if not base_path.exists():
        return skills

    # Look for directories containing SKILL.md
    for item in base_path.iterdir():
        if item.is_dir():
            # Check for SKILL.md (case-insensitive)
            skill_md = None
            for file in item.iterdir():
                if file.is_file() and file.name.upper() == "SKILL.MD":
                    skill_md = file
                    break

            if skill_md:
                skills.append(
                    {
                        "name": item.name,
                        "path": str(skill_md.relative_to(repo_path)),
                        "file_path": skill_md,
                    }
                )

    return skills


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
                                "is_public_sink": labels_dict.get("is_public_sink", 0),
                                "destructive": labels_dict.get("destructive", 0),
                                "untrusted_content": labels_dict.get(
                                    "untrusted_content", 0
                                ),
                                "private_data": labels_dict.get("private_data", 0),
                            }

        # If we couldn't find labels in the expected structure, return defaults
        return {
            "is_public_sink": 0,
            "destructive": 0,
            "untrusted_content": 0,
            "private_data": 0,
            "note": "No security labels returned by Snyk (skill may be safe or requires additional analysis)",
        }
    except Exception as e:
        return {
            "error": f"Failed to extract labels: {str(e)}",
            "is_public_sink": 0,
            "destructive": 0,
            "untrusted_content": 0,
            "private_data": 0,
        }


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
        raw = stdout[json_start : json_end + 1]
        clean = "\n".join(ln for ln in raw.split("\n") if not _is_snyk_spinner_line(ln))
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


def run_snyk_scan(skill_path: Path) -> Dict:
    """
    Run the Snyk agent scanner on *skill_path* (skill directory).

    Returns the four security labels extracted by :func:`extract_snyk_labels`,
    or a dict with an ``error`` key when the scan cannot be completed.
    """
    cmd = [
        "uvx",
        "snyk-agent-scan@latest",
        "--json",
        "--skills",
        str(skill_path),
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


def _copy_skill_directory(skill_dir_path: Path, dest_path: Path) -> None:
    """
    Copy all non-SKILL.md files from skill directory to destination.

    Silently ignores errors so that processing continues with just SKILL.md
    when ancillary files are unavailable.
    """
    try:
        for item in skill_dir_path.iterdir():
            if item.is_file() and item.name.upper() != "SKILL.MD":
                shutil.copy2(item, dest_path / item.name)
    except Exception:
        pass


def _run_scanners(
    skill_dir_path: Path,
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

            _copy_skill_directory(skill_dir_path, skill_path)

            scan_data = run_cisco_scan(skill_path)
            snyk_data = run_snyk_scan(skill_path)

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


def process_repository(repo_config: Dict) -> List[Dict]:
    """Process skills from a locally cloned repository."""
    owner = repo_config["owner"]
    repo_name = repo_config["repo"]
    sparse_path = repo_config.get("path", "")
    enabled = repo_config.get("enabled", True)

    if not enabled:
        print(f"\n⏭️  Skipping {owner}/{repo_name} (disabled)")
        return []

    print(f"\n📦 Processing {owner}/{repo_name}")

    # Construct local repository path
    base_dir = Path(__file__).parent
    repo_path = base_dir / "repos" / owner / repo_name

    if not repo_path.exists():
        print(f"  ⚠️  Repository not found locally: {repo_path}")
        print(f"      Run: ./scripts/update-repos.sh to clone repositories")
        return []

    # Get metadata from repos.json
    stars = repo_config.get("stars", 0)

    print(f"  ⭐ Stars: {stars}")

    # Find skills locally
    try:
        skill_files = find_skill_files_local(repo_path, sparse_path)
    except Exception as e:
        print(f"  ❌ Error finding skills: {e}")
        return []

    print(f"  📝 Found {len(skill_files)} skills")

    skills_data = []

    for skill_info in skill_files:
        try:
            skill_name = skill_info["name"]
            skill_file_path = skill_info["file_path"]
            skill_rel_path = skill_info["path"]

            # Read content from local file
            content = skill_file_path.read_text(encoding="utf-8")

            # Get latest commit for this file
            latest_commit = get_latest_commit_local(repo_path, skill_file_path)

            # Get skill directory path
            skill_dir_path = skill_file_path.parent

            # Extract metadata
            license_info = extract_license(content, skill_dir_path)
            summary = generate_summary(content)
            tags = categorize_skill(skill_name, content)

            # Run scanners
            scan_data, snyk_data = _run_scanners(skill_dir_path, skill_name, content)

            # Construct GitHub URL
            # Assume 'main' as default branch
            branch = "main"
            skill_url = (
                f"https://github.com/{owner}/{repo_name}/blob/{branch}/{skill_rel_path}"
            )

            skill_data = {
                "name": skill_name,
                "creator": owner,
                "category": tags,
                "summary": summary,
                "url": skill_url,
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

        except Exception as exc:
            print(f"    ✗ Error processing {skill_info['name']}: {exc}")

    return skills_data


def main():
    """Main processor function."""
    print("=" * 60)
    print("OpenSkills Agency - Local Skills Processor")
    print("=" * 60)

    # Check if repos directory exists
    base_dir = Path(__file__).parent
    repos_dir = base_dir / "repos"

    if not repos_dir.exists():
        print("\n❌ Error: repos/ directory not found")
        print("   The repos/ directory contains cloned skill repositories.")
        print("\n   To clone repositories, run:")
        print("   ./scripts/update-repos.sh")
        print("\n   Or wait for GitHub Actions to populate it automatically.")
        sys.exit(1)

    all_skills = []

    for repo_config in REPOS:
        skills = process_repository(repo_config)
        all_skills.extend(skills)
        # No sleep needed - no API rate limits!

    print("\n" + "=" * 60)
    print(f"✅ Total skills collected: {len(all_skills)}")
    print("=" * 60)

    # Save to JSON
    output_path = base_dir / "public" / "skills-data.json"
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
    top = ", ".join(f"{tag}({count})" for tag, count in tag_counts.most_common(5))
    print(f"  - Top categories: {top}")


if __name__ == "__main__":
    main()
