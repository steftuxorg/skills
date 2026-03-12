#!/usr/bin/env python3
"""
Test script to scan a single skill from a GitHub URL
"""

import os
import sys
import json
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv
from github import Github
from skill_scanner import SkillScanner
from skill_scanner.core.analyzers import BehavioralAnalyzer
import re

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN not found in .env file")

# Initialize GitHub client
g = Github(GITHUB_TOKEN)


def extract_license_from_referenced_file(
    repo, skill_dir_path: str, branch: str, content: str
) -> Optional[str]:
    """
    Check SKILL.md content for references to license files (e.g., LICENSE.txt).
    If found, fetch the file and extract the first or second meaningful line.
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
            # Construct the full path to the license file in the skill directory
            license_path = f"{skill_dir_path}/{license_filename}"
            print(
                f"  📄 Found license file reference: {license_filename}, attempting to fetch..."
            )

            # Get the license file from GitHub
            license_file = repo.get_contents(license_path, ref=branch)
            license_content = license_file.decoded_content.decode("utf-8")

            # Extract first or second meaningful line (skip empty lines)
            lines = [
                line.strip() for line in license_content.split("\n") if line.strip()
            ]

            if len(lines) >= 1:
                # Return the first line, or first two lines if first is very short
                first_line = lines[0]
                if len(first_line) < 20 and len(lines) >= 2:
                    return f"{first_line} {lines[1]}"
                return first_line

        except Exception as e:
            print(f"  ⚠️  Could not fetch {license_filename}: {e}")
            continue

    return None


def extract_snyk_labels(snyk_result: Dict) -> Dict:
    """Extract only the 4 specific labels from Snyk scanner output."""
    try:
        # Navigate through the Snyk result structure to find labels
        # Structure: {"<path>": {"servers": [{"name": "...", ...}], "labels": [[{labels_dict}]]}}
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


def run_snyk_scanner(skill_path: Path) -> Dict:
    """Run Snyk scanner on a skill directory."""
    print(f"\n  🔍 Running Snyk scanner...")

    try:
        # Run uvx snyk-agent-scan command (without 'inspect', pass directory not file)
        cmd = ["uvx", "snyk-agent-scan@latest", "--json", "--skills", str(skill_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        # Parse JSON output
        if result.stdout:
            # The output has progress indicators on stderr, but stdout should be pure JSON
            # Split by lines and find lines that look like JSON objects
            lines = result.stdout.strip().split("\n")

            # Try to find the JSON object (starts with { and ends with })
            json_lines = []
            in_json = False
            brace_count = 0

            for line in lines:
                # Skip progress indicator lines (contain special chars)
                if any(
                    c in line
                    for c in ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
                ):
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
                json_output = "\n".join(json_lines)
                try:
                    snyk_result = json.loads(json_output)
                    # Extract only the 4 specific labels from Snyk output
                    snyk_data = extract_snyk_labels(snyk_result)
                    print(f"  ✅ Snyk scan completed!")
                    return snyk_data
                except json.JSONDecodeError:
                    # If still fails, try to extract just the last complete JSON object
                    json_start = result.stdout.find("{")
                    json_end = result.stdout.rfind("}")
                    if json_start != -1 and json_end != -1:
                        json_output = result.stdout[json_start : json_end + 1]
                        # Remove any non-JSON lines
                        json_output = "\n".join(
                            [
                                l
                                for l in json_output.split("\n")
                                if not any(
                                    c in l
                                    for c in [
                                        "⠋",
                                        "⠙",
                                        "⠹",
                                        "⠸",
                                        "⠼",
                                        "⠴",
                                        "⠦",
                                        "⠧",
                                        "⠇",
                                        "⠏",
                                    ]
                                )
                            ]
                        )
                        snyk_result = json.loads(json_output)
                        snyk_data = extract_snyk_labels(snyk_result)
                        print(f"  ✅ Snyk scan completed!")
                        return snyk_data
                    else:
                        raise
            else:
                return {"error": "No valid JSON found in Snyk output"}
        else:
            return {"error": "No output from Snyk scanner"}

    except subprocess.TimeoutExpired:
        print(f"  ⚠️  Snyk scanner timeout")
        return {"error": "Snyk scanner timeout"}
    except json.JSONDecodeError as e:
        print(f"  ⚠️  Failed to parse Snyk output")
        return {
            "error": f"Failed to parse Snyk output: {str(e)}",
            "raw_output": result.stdout[:500] if "result" in locals() else "N/A",
        }
    except FileNotFoundError:
        print(f"  ⚠️  uvx not found - Snyk scanner not available")
        return {"error": "uvx command not found - please install uv"}
    except Exception as e:
        print(f"  ⚠️  Snyk scanner error: {e}")
        return {"error": f"Snyk scanner error: {str(e)}"}


def parse_github_url(url):
    """Parse a GitHub URL to extract owner, repo, branch, and path"""
    # Pattern: https://github.com/{owner}/{repo}/blob/{branch}/{path}
    pattern = r"https://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+)"
    match = re.match(pattern, url)

    if not match:
        raise ValueError(f"Invalid GitHub URL format: {url}")

    owner, repo, branch, path = match.groups()
    return owner, repo, branch, path


def test_skill_from_url(url):
    """Test scanning a skill from a GitHub URL"""
    print("=" * 60)
    print("Testing Cisco AI Defense Skill Scanner")
    print(f"URL: {url}")
    print("=" * 60)

    try:
        # Parse the URL
        owner, repo_name, branch, file_path = parse_github_url(url)

        print(f"\n📦 Repository: {owner}/{repo_name}")
        print(f"🌿 Branch: {branch}")
        print(f"📄 File: {file_path}")

        # Get the repository
        repo = g.get_repo(f"{owner}/{repo_name}")

        # Determine the skill directory (parent of SKILL.md)
        skill_dir_path = str(Path(file_path).parent)
        skill_name = Path(file_path).parent.name

        print(f"\n📝 Processing skill: {skill_name}")
        print(f"📁 Skill directory: {skill_dir_path}")

        # Get the SKILL.md file
        skill_file = repo.get_contents(file_path, ref=branch)
        content = skill_file.decoded_content.decode("utf-8")

        print(f"  📄 SKILL.md URL: {skill_file.html_url}")
        print(f"  📏 Content length: {len(content)} characters")

        # Extract license from referenced file if present
        license_from_file = extract_license_from_referenced_file(
            repo, skill_dir_path, branch, content
        )
        if license_from_file:
            print(
                f"  📜 License extracted from referenced file: {license_from_file[:100]}..."
            )

        # Get all files in the skill directory
        dir_contents = repo.get_contents(skill_dir_path, ref=branch)

        # Create temporary directory to save the skill for scanning
        with tempfile.TemporaryDirectory() as temp_dir:
            skill_path = Path(temp_dir) / skill_name
            skill_path.mkdir()

            # Save SKILL.md to temp directory
            skill_md_path = skill_path / "SKILL.md"
            skill_md_path.write_text(content, encoding="utf-8")

            # Download other files from the skill directory if they exist
            for file in dir_contents:
                if file.type == "file" and file.name != "SKILL.md":
                    try:
                        file_path_obj = skill_path / file.name
                        file_content = file.decoded_content
                        file_path_obj.write_bytes(file_content)
                        print(f"  📥 Downloaded: {file.name}")
                    except Exception as e:
                        print(f"  ⚠️  Could not download {file.name}: {e}")

            print(f"\n  🔍 Running Cisco AI Defense scanner...")

            # Create scanner with behavioral analyzer
            scanner = SkillScanner(analyzers=[BehavioralAnalyzer()])

            # Run security scanner on the skill directory in lenient mode
            scan_result = scanner.scan_skill(str(skill_path), lenient=True)

            print(f"  ✅ Cisco scan completed!")

            # Convert scan result to serializable format
            scan_data = {
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

            # Run Snyk scanner (pass skill directory, not SKILL.md file)
            snyk_data = run_snyk_scanner(skill_path)

            # Build result
            result = {
                "name": skill_name,
                "creator": owner,
                "url": skill_file.html_url,
                "repo": f"{owner}/{repo_name}",
                "branch": branch,
                "license_from_file": license_from_file,  # Add extracted license
                "security-scanners": {"cisco-ai-defense": scan_data, "snyk": snyk_data},
            }

            # Display scan result summary
            print(f"\n  📊 Security Scan Results for '{skill_name}':")
            print(f"\n  Cisco AI Defense:")
            print(f"     Findings: {scan_data['findings_count']}")
            print(f"     Max Severity: {scan_data['max_severity']}")
            print(f"     Is Safe: {scan_data['is_safe']}")
            if scan_data["findings"]:
                print(f"\n     Findings Details:")
                for i, finding in enumerate(scan_data["findings"], 1):
                    print(f"       {i}. [{finding['severity']}] {finding['title']}")
                    if finding.get("description"):
                        print(f"          Description: {finding['description']}")
                    if finding["file"]:
                        print(f"          File: {finding['file']}")
                    if finding["line"]:
                        print(f"          Line: {finding['line']}")

            print(f"\n  Snyk:")
            if "error" in snyk_data:
                print(f"     Error: {snyk_data['error']}")
            else:
                print(f"     Is Public Sink: {snyk_data.get('is_public_sink', 0)}")
                print(f"     Destructive: {snyk_data.get('destructive', 0)}")
                print(
                    f"     Untrusted Content: {snyk_data.get('untrusted_content', 0)}"
                )
                print(f"     Private Data: {snyk_data.get('private_data', 0)}")
                if "note" in snyk_data:
                    print(f"     Note: {snyk_data['note']}")

            # Save results
            output_path = Path(__file__).parent / "test_scan_results.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump([result], f, indent=2, ensure_ascii=False)

            print("\n" + "=" * 60)
            print(f"✅ Test completed!")
            print(f"💾 Results saved to: {output_path}")
            print("=" * 60)

            return result

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_scanner_url.py <github_url>")
        print(
            "Example: python test_scanner_url.py https://github.com/user/repo/blob/main/path/to/SKILL.md"
        )
        sys.exit(1)

    url = sys.argv[1]
    test_skill_from_url(url)
