# Q-Mol GitHub Setup Guide

## Step 1: Create a GitHub Account
1. Go to https://github.com/signup
2. Sign up with your email
3. Verify your email

## Step 2: Create a New Repository
1. Click the + icon → "New repository"
2. Name: `qmol` (or `qmol-v2`)
3. Description: `Q-Mol v2.0 — Molecular Informatics & Drug Discovery Platform`
4. Visibility: **Public** (for open source) or **Private** (if you want to keep it closed)
5. Check "Add a README file"
6. Click "Create repository"

## Step 3: Push Your Local Code

Open Git Bash in `D:\Qmol-3`:

```bash
cd /d/Qmol-3

# Initialize git (if not already done)
git init

# Add the remote
git remote add origin https://github.com/YOUR_USERNAME/qmol.git

# Stage all files
git add .

# Commit
git commit -m "Q-Mol v2.0.0 — initial release"

# Push
git push -u origin main
```

If you get "failed to push some refs", do:
```bash
git pull --rebase origin main
git push -u origin main
```

## Step 4: Set Up GitHub Actions (CI/CD)

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: '3.12'
    - name: Install deps
      run: pip install -r requirements.txt
    - name: Syntax check
      run: python -m py_compile api.py
    - name: Run tests
      run: pytest tests/ -v
```

## Step 5: Update Your Microsite

Edit `deploy/index.html` and replace:
- `https://github.com/yourusername/qmol` → your real repo URL

Then re-upload to your hosting.

## Step 6: Deploy with Render (Free)

1. Go to https://render.com, sign in with GitHub
2. Click "New +" → "Web Service"
3. Connect your GitHub repo
4. Use `render.yaml` from `deploy/render.yaml`
5. Click "Create Web Service"
6. Render auto-deploys on every push

## Step 7: Deploy with Fly.io (Free)

```bash
# Install flyctl
powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"

# Sign up
fly auth signup

# Deploy
cd D:\Qmol-3
fly deploy --config deploy/fly.toml
```

---

## Quick Commands Reference

```bash
# Check status
git status

# Add all changes
git add .

# Commit
git commit -m "your message"

# Push
git push

# Pull latest
git pull
```
