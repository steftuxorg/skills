#!/usr/bin/env python3
"""
Test Snyk scanner with a local skill file to diagnose the label extraction issue.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
SNYK_TOKEN = os.getenv("SNYK_TOKEN")

print("=" * 60)
print("Testing Snyk Scanner with Local Skill")
print("=" * 60)

if SNYK_TOKEN:
    print(f"✅ SNYK_TOKEN found: {SNYK_TOKEN[:10]}...")
    # Set as environment variable for snyk-agent-scan
    os.environ["SNYK_TOKEN"] = SNYK_TOKEN
else:
    print("⚠️  SNYK_TOKEN not found in .env file")
    print("   Snyk scanner may not work properly without authentication")

# Pick a skill to test - let's use anthropics/skills/webapp-testing
skill_path = Path("repos/anthropics/skills/webapp-testing")

if not skill_path.exists():
    print(f"\n❌ Error: Skill not found at {skill_path}")
    print("   Please clone repositories first: ./scripts/update-repos.sh")
    sys.exit(1)

skill_md = skill_path / "SKILL.md"
print(f"\n📝 Testing skill: {skill_path.name}")
print(f"📂 Skill directory: {skill_path}")
print(f"📄 SKILL.md exists: {skill_md.exists()}")
if skill_md.exists():
    print(f"📏 SKILL.md size: {skill_md.stat().st_size} bytes")

print(f"\n🔍 Running Snyk scanner...")
print(f"   Command: uvx snyk-agent-scan@latest --json --skills {skill_path}")

try:
    cmd = ["uvx", "snyk-agent-scan@latest", "--json", "--skills", str(skill_path)]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60,
        env=os.environ.copy(),  # Pass environment variables including SNYK_TOKEN
    )

    print(f"\n📤 Return code: {result.returncode}")

    # Show stderr (may contain useful info)
    if result.stderr:
        print(f"\n📋 Stderr output:")
        print(result.stderr[:500])

    # Parse stdout
    if result.stdout:
        print(f"\n📄 Stdout output ({len(result.stdout)} chars):")
        print(f"First 500 chars:\n{result.stdout[:500]}")

        # Try to find and parse JSON
        try:
            # Remove spinner characters
            spinner_chars = frozenset("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏")
            lines = result.stdout.strip().split("\n")
            json_lines = []
            in_json = False
            brace_count = 0

            for line in lines:
                # Skip lines with spinner characters
                if any(c in line for c in spinner_chars):
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
                json_str = "\n".join(json_lines)
                snyk_result = json.loads(json_str)

                print(f"\n✅ Successfully parsed JSON output!")
                print(f"\n📊 Snyk Result Structure:")
                print(json.dumps(snyk_result, indent=2))

                # Try to extract labels
                print(f"\n🔍 Attempting to extract labels...")
                for path_key, path_data in snyk_result.items():
                    print(f"\n   Path key: {path_key}")
                    if isinstance(path_data, dict):
                        print(f"   Keys in path_data: {list(path_data.keys())}")

                        if "labels" in path_data:
                            labels_data = path_data["labels"]
                            print(f"   Labels type: {type(labels_data)}")
                            print(f"   Labels content: {labels_data}")

                            if labels_data and isinstance(labels_data, list):
                                print(f"   Labels list length: {len(labels_data)}")
                                if len(labels_data) > 0:
                                    print(
                                        f"   First element type: {type(labels_data[0])}"
                                    )
                                    print(f"   First element: {labels_data[0]}")
                        else:
                            print(f"   ⚠️  'labels' key not found in path_data")

            else:
                print(f"\n❌ Could not extract valid JSON from output")

        except json.JSONDecodeError as e:
            print(f"\n❌ JSON parsing error: {e}")
            print(f"   Failed to parse JSON from output")
    else:
        print(f"\n❌ No stdout output from Snyk scanner")

except subprocess.TimeoutExpired:
    print(f"\n❌ Snyk scanner timeout (60s)")
except FileNotFoundError:
    print(f"\n❌ uvx command not found")
    print(f"   Please install uv: curl -LsSf https://astral.sh/uv/install.sh | sh")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 60)
print("Test completed!")
print("=" * 60)
