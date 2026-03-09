# Quick Start Guide - Automated Skills Sync

## 🚀 First Time Setup (Do This Once)

### 1. Clean Existing Subdirectories
```bash
# Remove repo subdirectories (they'll be recreated by GitHub Actions under repos/)
rm -rf anthropics/ openai/ vercel-labs/ bmad-code-org/ martinellich/ \
       openclaw/ microsoft/ inference-sh/ github/ wshobson/ angelo-v/ google-gemini/

# Create the repos directory structure
mkdir -p repos
```

### 2. Commit and Push Workflow Files
```bash
# Add the automation files
git add .github/ scripts/ AUTOMATION_SETUP.md

# Commit
git commit -m "Add GitHub Actions automation for skills sync"

# Push to GitHub
git push
```

### 3. Enable GitHub Actions
1. Go to: https://github.com/steftuxorg/skills/actions
2. Click "I understand my workflows, go ahead and enable them"

### 4. Test the Workflow
1. Go to: https://github.com/steftuxorg/skills/actions
2. Click "Update Skills Repositories"
3. Click "Run workflow" → "Run workflow"
4. Watch it run! ⏱️ (~2-5 minutes)

### 5. Verify Success
```bash
# Pull the new commits
git pull

# Check that subdirectories were created under repos/
ls -la repos/anthropics/ repos/openai/ repos/vercel-labs/

# View the structure
tree repos/ -L 2

# View commit history
git log --oneline -20
```

## ✅ What Happens Next

- **Daily at 2 AM UTC**: Automatic updates
- **Individual commits**: One per updated repo
- **Email notifications**: On failures only
- **Issues created**: For troubleshooting

## 📝 Common Tasks

### Add a New Repository
```bash
# Edit repos.json
nano repos.json

# Add entry:
# {
#   "owner": "new-org",
#   "repo": "new-repo", 
#   "path": "path/to/skills",
#   "enabled": true
# }

# Commit and push
git add repos.json
git commit -m "Add new-org/new-repo to skills sync"
git push

# Manually trigger workflow or wait for next scheduled run
```

### Disable a Repository
```bash
# Edit repos.json
nano repos.json

# Change: "enabled": true → "enabled": false

# Commit and push
git add repos.json
git commit -m "Disable old-repo from sync"
git push
```

### Manual Update (On Demand)
1. Go to: https://github.com/steftuxorg/skills/actions
2. Click "Update Skills Repositories"  
3. Click "Run workflow" → "Run workflow"

## 🔍 Monitoring

- **Workflow runs**: https://github.com/steftuxorg/skills/actions
- **Commits**: https://github.com/steftuxorg/skills/commits/main
- **Issues (failures)**: https://github.com/steftuxorg/skills/issues

## 📖 Full Documentation

See [AUTOMATION_SETUP.md](../AUTOMATION_SETUP.md) for complete details.

## ⚡ Key Features

✅ Shallow clones (--depth 1) - minimal bandwidth  
✅ Sparse checkout - only specified subdirectories  
✅ Parallel processing - updates run concurrently  
✅ Auto-recovery - continues on individual failures  
✅ Individual commits - clear history per repo  
✅ Automatic data regeneration - runs main.py after updates  

---

**Ready to go!** Follow steps 1-5 above to get started.
