# Codecov Setup Guide

## 🎯 Quick Fix for Codecov Rate Limit Error

Your CI/CD pipeline is failing because Codecov requires authentication. Follow these steps to fix it:

---

## Step 1: Get Your Codecov Token

1. **Go to Codecov**: Visit [https://codecov.io/](https://codecov.io/)
2. **Sign in** with your GitHub account
3. **Navigate to your repository**: 
   - Click on your username → Select `Assignment7_mcp-multi-agent-game`
   - Or go directly to: `https://app.codecov.io/gh/fouada/Assignment7_mcp-multi-agent-game`
4. **Get the token**:
   - Click **Settings** (gear icon)
   - Go to **General** tab
   - Find **Repository Upload Token**
   - Click **Copy** to copy the token

---

## Step 2: Add Token to GitHub Secrets

1. **Go to your GitHub repository**: 
   ```
   https://github.com/fouada/Assignment7_mcp-multi-agent-game
   ```

2. **Navigate to Secrets**:
   - Click **Settings** (top menu)
   - In left sidebar: **Secrets and variables** → **Actions**

3. **Add new secret**:
   - Click **New repository secret** button
   - **Name**: `CODECOV_TOKEN`
   - **Secret**: Paste the token you copied from Codecov
   - Click **Add secret**

---

## Step 3: Verify the Setup

1. **Commit and push** the new workflow file:
   ```bash
   cd /Users/fouadaz/LearningFromUniversity/Learning/LLMSAndMultiAgentOrchestration/course-materials/assignments/Assignment_7_MCP_Multi_Agent_Game
   git add .github/workflows/ci.yml
   git commit -m "Add GitHub Actions workflow with Codecov token support"
   git push origin main
   ```

2. **Check the workflow**:
   - Go to your repository on GitHub
   - Click **Actions** tab
   - You should see the workflow running
   - The "📊 Coverage Analysis" job should now succeed

---

## Step 4: (Optional) Re-run Failed Workflow

If you don't want to wait for a new commit:

1. Go to **Actions** tab on GitHub
2. Click on the failed workflow run
3. Click **Re-run all jobs** button
4. The workflow will now use the token you added

---

## ✅ What's Changed

The new workflow file (`.github/workflows/ci.yml`) includes:

- **Proper Codecov token usage**: Line 139
  ```yaml
  - name: Upload coverage to Codecov
    uses: codecov/codecov-action@v3
    with:
      token: ${{ secrets.CODECOV_TOKEN }}  # ← Token is now used
  ```

- **Multi-platform testing**: Ubuntu, macOS, Windows
- **Multiple Python versions**: 3.11, 3.12
- **Comprehensive checks**:
  - ✅ Linting & Formatting
  - ✅ Type Checking
  - ✅ Security Scanning
  - ✅ Unit Tests
  - ✅ Integration Tests
  - ✅ Performance Tests
  - ✅ Coverage Analysis (80% minimum)
  - ✅ Docker Build & Test

---

## 🔍 Verify It Works

After adding the token and pushing changes, you should see:

```
✅ Upload coverage to Codecov
   ✓ Codecov report uploaded successfully
   ✓ View report at: https://codecov.io/gh/fouada/Assignment7_mcp-multi-agent-game
```

---

## 🚨 Troubleshooting

### Token Still Not Working?

1. **Double-check the secret name**: Must be exactly `CODECOV_TOKEN`
2. **Verify token is correct**: Copy it again from Codecov
3. **Check token permissions**: Make sure it's the Repository Upload Token, not a different token
4. **Wait for rate limit**: If you hit the rate limit, wait ~48 minutes before retrying

### Still Getting Rate Limited?

The error message said: "Expected time to availability: 2876s" (~48 minutes)

If you need to run immediately:
1. Wait the specified time
2. Or add the token first, then re-run

### Need Help?

Check these resources:
- [Codecov Documentation](https://docs.codecov.com/docs)
- [GitHub Actions Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- Your project's CI/CD guide: `docs/CI_CD_GUIDE.md`

---

## 📊 Expected Coverage Report

Once working, you'll see coverage badges like:

```markdown
![Coverage](https://codecov.io/gh/fouada/Assignment7_mcp-multi-agent-game/branch/main/graph/badge.svg)
```

Add this to your `README.md` to display coverage status!

---

**Created**: December 26, 2025  
**Status**: Ready to use ✅

