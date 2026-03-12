#!/usr/bin/env python3
"""
Test script to scan 2 skills from creator angelo-v
"""

import os
import json
import tempfile
import re
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from github import Github
from skill_scanner import SkillScanner
from skill_scanner.core.analyzers import BehavioralAnalyzer

# Load environment variables
load_dotenv(Path(__file__).parent.parent / '.env')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN not found in .env file")

# Initialize GitHub client
g = Github(GITHUB_TOKEN)

def extract_license_from_referenced_file(repo, skill_dir_path: str, content: str, branch: str = "main") -> Optional[str]:
    """
    Check SKILL.md content for references to license files (e.g., LICENSE.txt).
    If found, fetch the file and extract the first or second meaningful line.
    """
    # Look for license file references in the content
    # Pattern: LICENSE.txt, LICENSE.md, etc. in the content
    license_file_pattern = r'\b(LICENSE(?:\.[a-zA-Z0-9]+)?)\b'
    matches = re.findall(license_file_pattern, content, re.IGNORECASE)
    
    if not matches:
        return None
    
    # Try to fetch each referenced license file
    for license_filename in set(matches):  # Use set to avoid duplicates
        try:
            # Construct the full path to the license file in the skill directory
            license_path = f"{skill_dir_path}/{license_filename}"
            print(f"  📄 Found license file reference: {license_filename}, attempting to fetch...")
            
            # Get the license file from GitHub
            license_file = repo.get_contents(license_path, ref=branch)
            license_content = license_file.decoded_content.decode('utf-8')
            
            # Extract first or second meaningful line (skip empty lines)
            lines = [line.strip() for line in license_content.split('\n') if line.strip()]
            
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


def test_angelo_v_skills():
    """Test scanning 2 skills from angelo-v"""
    print("=" * 60)
    print("Testing Cisco AI Defense Skill Scanner")
    print("Testing 2 skills from creator: angelo-v")
    print("=" * 60)
    
    # Repository configuration for angelo-v
    owner = "angelo-v"
    repo_name = "opencode-playground"
    path = ".opencode/skills"
    
    print(f"\n📦 Accessing {owner}/{repo_name}/{path}")
    
    try:
        repo = g.get_repo(f"{owner}/{repo_name}")
        
        # Get contents of skills directory
        contents = repo.get_contents(path)
        
        # Get first 2 skill directories
        skill_dirs = [item for item in contents if item.type == "dir"][:2]
        
        results = []
        
        # Create scanner with behavioral analyzer
        scanner = SkillScanner(analyzers=[BehavioralAnalyzer()])
        
        for skill_dir in skill_dirs:
            try:
                print(f"\n📝 Processing skill: {skill_dir.name}")
                
                # Get SKILL.md file from the directory
                dir_contents = repo.get_contents(skill_dir.path)
                skill_file = None
                
                for file in dir_contents:
                    if file.name.upper() == "SKILL.MD":
                        skill_file = file
                        break
                
                if not skill_file:
                    print(f"  ⚠️  No SKILL.md found in {skill_dir.name}")
                    continue
                
                # Get file content
                content = skill_file.decoded_content.decode('utf-8')
                
                print(f"  📄 SKILL.md URL: {skill_file.html_url}")
                print(f"  📏 Content length: {len(content)} characters")
                
                # Extract license from referenced file if present
                license_from_file = extract_license_from_referenced_file(repo, skill_dir.path, content)
                if license_from_file:
                    print(f"  📜 License extracted from referenced file: {license_from_file[:100]}...")
                
                # Create temporary directory to save the skill for scanning
                with tempfile.TemporaryDirectory() as temp_dir:
                    skill_path = Path(temp_dir) / skill_dir.name
                    skill_path.mkdir()
                    
                    # Save SKILL.md to temp directory
                    skill_md_path = skill_path / "SKILL.md"
                    skill_md_path.write_text(content, encoding='utf-8')
                    
                    # Download other files from the skill directory if they exist
                    for file in dir_contents:
                        if file.type == "file" and file.name != "SKILL.md":
                            file_path = skill_path / file.name
                            file_content = file.decoded_content
                            file_path.write_bytes(file_content)
                    
                    print(f"  🔍 Running Cisco AI Defense scanner...")
                    
                    # Run security scanner on the skill directory
                    scan_result = scanner.scan_skill(str(skill_path))
                    
                    print(f"  ✅ Scan completed!")
                    
                    # Convert scan result to serializable format
                    scan_data = {
                        'findings_count': len(scan_result.findings),
                        'max_severity': str(scan_result.max_severity),
                        'is_safe': scan_result.is_safe,
                        'findings': [
                            {
                                'severity': str(finding.severity),
                                'category': finding.category,
                                'message': finding.message,
                                'file': finding.file,
                                'line': finding.line
                            }
                            for finding in scan_result.findings
                        ]
                    }
                    
                    # Build result
                    result = {
                        'name': skill_dir.name,
                        'creator': owner,
                        'url': skill_file.html_url,
                        'repo': f"{owner}/{repo_name}",
                        'license_from_file': license_from_file,  # Add extracted license
                        'security-scanners': {
                            'cisco-ai-defense': scan_data
                        }
                    }
                    
                    results.append(result)
                    
                    # Display scan result summary
                    print(f"\n  📊 Scan Results for '{skill_dir.name}':")
                    print(f"     Findings: {scan_data['findings_count']}")
                    print(f"     Max Severity: {scan_data['max_severity']}")
                    print(f"     Is Safe: {scan_data['is_safe']}")
                    if scan_data['findings']:
                        print(f"\n     Findings Details:")
                        for i, finding in enumerate(scan_data['findings'], 1):
                            print(f"       {i}. [{finding['severity']}] {finding['message']}")
                            if finding['file']:
                                print(f"          File: {finding['file']}")
                
            except Exception as e:
                print(f"  ❌ Error processing {skill_dir.name}: {e}")
                import traceback
                traceback.print_exc()
        
        # Save results
        output_path = Path(__file__).parent / 'test_scan_results.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print("\n" + "=" * 60)
        print(f"✅ Test completed! Scanned {len(results)} skills")
        print(f"💾 Results saved to: {output_path}")
        print("=" * 60)
        
        return results
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == '__main__':
    test_angelo_v_skills()
