# Directory Structure Reference

## New Structure (repos/owner/repo/)

After the GitHub Actions workflow runs, your repository will have this structure:

```
skills/
├── .github/
│   ├── workflows/
│   │   └── update-skills.yml          # Main automation workflow
│   └── QUICK_START.md                 # Quick reference guide
│
├── scripts/
│   └── update-repo.sh                 # Sparse checkout script
│
├── repos/                              # All external repos stored here
│   ├── anthropics/
│   │   └── skills/                    # Contains content from anthropics/skills repo
│   │       ├── SKILL1.md
│   │       └── SKILL2.md
│   │
│   ├── openai/
│   │   └── skills/                    # Contains content from openai/skills repo
│   │       └── (skills content from skills/.curated path)
│   │
│   ├── vercel-labs/
│   │   └── agent-skills/              # Contains content from vercel-labs/agent-skills repo
│   │       └── (skills content from skills path)
│   │
│   ├── bmad-code-org/
│   │   └── BMAD-METHOD/               # Contains content from bmad-code-org/BMAD-METHOD repo
│   │       └── (skills content from .claude/skills path)
│   │
│   ├── martinellich/
│   │   └── aiup-marketplace/
│   │       └── (skills content from aiup-core/skills path)
│   │
│   ├── openclaw/
│   │   └── openclaw/
│   │       └── (skills content from skills path)
│   │
│   ├── microsoft/
│   │   ├── GitHub-Copilot-for-Azure/
│   │   │   └── (skills content from plugin/skills path)
│   │   └── skills/
│   │       └── (skills content from .github/skills path)
│   │
│   ├── inference-sh/
│   │   └── skills/
│   │       └── (skills content from skills path)
│   │
│   ├── github/
│   │   └── awesome-copilot/
│   │       └── (skills content from skills path)
│   │
│   ├── wshobson/
│   │   └── agents/
│   │       └── (skills content from plugins path)
│   │
│   ├── angelo-v/
│   │   └── opencode-playground/
│   │       └── (skills content from .opencode/skills path)
│   │
│   └── google-gemini/
│       └── gemini-cli/
│           └── (skills content from .gemini/skills path)
│
├── repos.json                         # Configuration: which repos to sync
├── categories.json                    # Category definitions
├── main.py                            # Script to regenerate skills data
├── requirements.txt                   # Python dependencies
├── skills-data.json                   # Generated skills data (auto-updated)
├── AUTOMATION_SETUP.md                # Full setup guide
├── README.md                          # Project README
└── LICENSE                            # MIT License

```

## Key Benefits of This Structure

### 1. **Clear Organization**
- All external repos under `repos/` directory
- Easy to identify owner and repo at a glance
- No confusion with project files

### 2. **Namespace Isolation**
- `repos/microsoft/skills/` and `repos/microsoft/GitHub-Copilot-for-Azure/` can coexist
- Same owner, different repos clearly separated

### 3. **Git-Friendly**
- Add `repos/` to `.gitignore` if needed (though we commit them)
- Easy to clean: `rm -rf repos/` removes all external content
- Individual repo updates create clear git history

### 4. **Scalability**
- Easy to add new repos - just edit `repos.json`
- No name collisions between owners
- Can handle hundreds of repos without confusion

## Example Paths

Based on your `repos.json` configuration:

| Owner | Repo | Source Path | Local Path |
|-------|------|-------------|------------|
| anthropics | skills | `skills` | `repos/anthropics/skills/` |
| openai | skills | `skills/.curated` | `repos/openai/skills/` |
| vercel-labs | agent-skills | `skills` | `repos/vercel-labs/agent-skills/` |
| bmad-code-org | BMAD-METHOD | `.claude/skills` | `repos/bmad-code-org/BMAD-METHOD/` |
| martinellich | aiup-marketplace | `aiup-core/skills` | `repos/martinellich/aiup-marketplace/` |
| openclaw | openclaw | `skills` | `repos/openclaw/openclaw/` |
| microsoft | GitHub-Copilot-for-Azure | `plugin/skills` | `repos/microsoft/GitHub-Copilot-for-Azure/` |
| microsoft | skills | `.github/skills` | `repos/microsoft/skills/` |
| inference-sh | skills | `skills` | `repos/inference-sh/skills/` |
| github | awesome-copilot | `skills` | `repos/github/awesome-copilot/` |
| wshobson | agents | `plugins` | `repos/wshobson/agents/` |
| angelo-v | opencode-playground | `.opencode/skills` | `repos/angelo-v/opencode-playground/` |
| google-gemini | gemini-cli | `.gemini/skills` | `repos/google-gemini/gemini-cli/` |

## Accessing Skills

### Via Command Line
```bash
# List all repos
ls -la repos/

# List all skills from anthropics
ls -la repos/anthropics/skills/

# Find all SKILL.md files
find repos/ -name "SKILL.md"

# Count total skills
find repos/ -name "SKILL.md" | wc -l
```

### Via Python (main.py)
The `main.py` script will need to be updated to scan `repos/` instead of individual directories at the root level.

## Migration from Old Structure

If you previously had repos at the root level:

```bash
# Old structure
anthropics/skills/
openai/skills/

# New structure
repos/anthropics/skills/
repos/openai/skills/
```

The GitHub Actions workflow handles this automatically. Just:
1. Delete old directories at root
2. Run workflow
3. New structure created automatically

---

**Last Updated:** 2026-03-09  
**Structure Version:** 2.0 (repos/owner/repo)
