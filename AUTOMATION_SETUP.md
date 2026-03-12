# GitHub Actions Automation Setup Guide

This guide explains how to set up and use the automated skills repository synchronization system.

## 📋 Overview

The automation system:
- **Automatically updates** nested repository subdirectories daily at 2 AM UTC
- **Uses sparse checkout** to clone only specified subdirectories (minimal bandwidth)
- **Creates shallow clones** (--depth 1) to save storage space
- **Regenerates skills data** after each update
- **Creates individual commits** for each updated repository
- **Sends notifications** on failures via GitHub Issues

## 🚀 Initial Setup

### Step 1: Clean Existing Subdirectories (One-Time)

Before the first workflow run, remove existing repository subdirectories to let GitHub Actions manage them:

```bash
# Remove all existing repo subdirectories (if they exist outside repos/)
rm -rf anthropics/ openai/ vercel-labs/ bmad-code-org/ martinellich/ \
       openclaw/ microsoft/ inference-sh/ github/ wshobson/ angelo-v/ google-gemini/

# Create the repos directory structure
mkdir -p repos

# Commit the cleanup
git add -A
git commit -m "Prepare for automated repo management under repos/"
git push
```

**Why?** This ensures a clean state and verifies that the automation works end-to-end.

**New Structure:** All repositories will be organized as `repos/owner/repo/`

### Step 2: Verify Workflow Files

The following files should already be in your repository:
- `.github/workflows/update-skills.yml` - Main workflow
- `scripts/update-repo.sh` - Sparse checkout script (executable)

Verify they exist:
```bash
ls -la .github/workflows/update-skills.yml
ls -la scripts/update-repo.sh
```

### Step 3: Configure GitHub Repository Settings

**Option A: Using Default GitHub Token (Recommended for Testing)**

The workflow uses `GITHUB_TOKEN` which is automatically provided by GitHub Actions. This works for:
- ✅ Cloning public repositories
- ✅ Committing to your repository
- ✅ Creating issues

No additional setup needed for initial testing!

**Option B: Using Personal Access Token (For Production)**

If you want more control or encounter permission issues:

1. Go to: https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Configure:
   - **Name:** `Skills Auto-Update Bot`
   - **Scopes:** Check `repo` and `workflow`
   - **Expiration:** Choose appropriate duration
4. Click "Generate token" and copy it
5. Add to repository secrets:
   - Go to: `https://github.com/steftuxorg/skills/settings/secrets/actions`
   - Click "New repository secret"
   - **Name:** `PAT_TOKEN`
   - **Value:** Paste your token
   - Click "Add secret"

Then update `.github/workflows/update-skills.yml`:
```yaml
# Change this line in the checkout steps:
token: ${{ secrets.GITHUB_TOKEN }}
# To:
token: ${{ secrets.PAT_TOKEN }}
```

### Step 4: Enable GitHub Actions

1. Go to: `https://github.com/steftuxorg/skills/actions`
2. If prompted, click "I understand my workflows, go ahead and enable them"
3. Verify the workflow appears: "Update Skills Repositories"

## 🧪 Testing the Workflow

### Test 1: Manual Trigger (Recommended First)

1. Go to: `https://github.com/steftuxorg/skills/actions`
2. Click on "Update Skills Repositories" workflow
3. Click "Run workflow" → Select branch `main` → Click "Run workflow"
4. Watch the workflow execute in real-time
5. Verify:
   - ✅ All enabled repos were processed
   - ✅ Subdirectories were created
   - ✅ Commits were made (one per repo)
   - ✅ `skills-data.json` was regenerated

### Test 2: Verify Sparse Checkout

Check that only specified paths were downloaded:

```bash
# Example: anthropics repo should be at repos/anthropics/skills/
ls -la repos/anthropics/skills/
# Should show: contents of the skills/ subdirectory

# Example: openai repo
ls -la repos/openai/skills/
# Should show: contents of the skills/.curated subdirectory

# View overall structure
tree repos/ -L 2
# Should show: repos/owner/repo/ hierarchy
```

### Test 3: Add a New Repository

1. Edit `repos.json`:
   ```json
   {
     "owner": "test-org",
     "repo": "test-repo",
     "path": "test-path",
     "enabled": true
   }
   ```
2. Commit and push
3. Manually trigger workflow (or wait for scheduled run)
4. Verify new directory `repos/test-org/test-repo/` was created automatically

## 📅 Scheduled Runs

The workflow runs automatically **daily at 2 AM UTC** (9 PM EST / 6 PM PST).

To change the schedule, edit `.github/workflows/update-skills.yml`:
```yaml
schedule:
  - cron: '0 2 * * *'  # Change to desired time
```

Cron syntax: `minute hour day month weekday`
- Example: `'0 14 * * *'` = 2 PM UTC daily
- Example: `'0 2 * * 1'` = 2 AM UTC every Monday

## 🔔 Notifications

### On Success
- No notifications sent (quiet success)
- View commits in repository history

### On Failure
1. **GitHub Issue Created** with:
   - List of failed repositories
   - Link to workflow run
   - Error details
   - Assigned to repository owner

2. **Email Notification** (if enabled in your GitHub settings)
   - Go to: https://github.com/settings/notifications
   - Ensure "Actions" notifications are enabled

## 🔧 Maintenance

### Adding New Repositories

1. Edit `repos.json`:
   ```json
   {
     "owner": "new-owner",
     "repo": "new-repo",
     "path": "path/to/skills",
     "enabled": true
   }
   ```
2. Commit and push
3. The next workflow run will automatically:
   - Create the directory structure
   - Clone the specified path
   - Make initial commit

**No manual initialization needed!**

### Disabling a Repository

Edit `repos.json` and set `enabled: false`:
```json
{
  "owner": "old-repo",
  "repo": "deprecated",
  "path": "skills",
  "enabled": false  ← Set to false
}
```

The workflow will skip this repository. To remove its directory:
```bash
rm -rf repos/old-repo/
git add .
git commit -m "Remove deprecated old-repo skills"
git push
```

### Troubleshooting

#### Problem: Workflow fails with "Path not found"

**Cause:** Repository path in `repos.json` is incorrect or changed

**Solution:**
1. Check the error message in workflow logs for available paths
2. Update `repos.json` with correct path
3. Re-run workflow manually

#### Problem: "Permission denied" errors

**Cause:** GitHub token lacks required permissions

**Solution:**
1. Verify repository settings → Actions → General → Workflow permissions
2. Select "Read and write permissions"
3. Click "Save"

#### Problem: No commits being made despite changes

**Cause:** Git configuration or token issues

**Solution:**
1. Check workflow logs for git errors
2. Verify `GITHUB_TOKEN` or `PAT_TOKEN` is configured
3. Ensure workflow has `contents: write` permission

#### Problem: main.py fails during regenerate-data job

**Cause:** Missing dependencies or environment variables

**Solution:**
1. Check if `GITHUB_TOKEN` is needed by main.py (it is!)
2. Verify `requirements.txt` is complete
3. Check workflow logs for Python errors

## 📊 Monitoring

### View Workflow Runs
- **URL:** `https://github.com/steftuxorg/skills/actions`
- **Filter by:** Status (success/failure), branch, date range

### View Commits
- **URL:** `https://github.com/steftuxorg/skills/commits/main`
- **Look for:** `[bot]` commits with "Update" messages

### View Issues (Failures)
- **URL:** `https://github.com/steftuxorg/skills/issues`
- **Filter by:** Label `automation` or `bug`

## 📈 Resource Usage

### GitHub Actions Free Tier
- **Limit:** 2,000 minutes/month
- **This workflow uses:** ~5 min/day × 30 days = ~150 min/month (7.5%)
- **Plenty of headroom!**

### Storage
- **Cache storage:** ~100 MB (Python dependencies)
- **Artifact storage:** Minimal (only failure logs, 7-day retention)
- **Repo size:** ~65-260 MB (sparse checkout savings!)

## 🔒 Security Notes

- The workflow only clones **public repositories**
- Uses **read-only** access for external repos
- Uses **write** access only for your repository (commits)
- `GITHUB_TOKEN` is scoped to this repository only
- Never commit sensitive data (tokens, API keys) to `repos.json`

## 🎯 Expected Workflow Execution

```
Scheduled Trigger (Daily 2 AM UTC)
  ↓
Job 1: prepare
  - Loads repos.json
  - Creates matrix of enabled repos
  ↓
Job 2: update-repos (parallel, max 5 at a time)
  - anthropics/skills → Clone → Commit if changed
  - openai/skills → Clone → Commit if changed
  - vercel-labs/agent-skills → Clone → Commit if changed
  - ... (all enabled repos)
  ↓
Job 3: regenerate-data
  - Pull all new commits
  - Install Python dependencies (cached)
  - Run main.py
  - Commit skills-data.json if changed
  ↓
Job 4: report-failures (only if any failed)
  - Create GitHub issue with error details
  - Email notification sent
```

## 📞 Support

- **Issues:** https://github.com/steftuxorg/skills/issues
- **Workflow Runs:** https://github.com/steftuxorg/skills/actions
- **Documentation:** This file!

---

**Last Updated:** 2026-03-09  
**Version:** 1.0
