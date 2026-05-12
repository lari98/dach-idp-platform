# GitHub Setup & Agile Version Workflow

This guide explains how to push this project to GitHub and how to keep adding features
using the same agile versioning approach — so you can always roll back to any previous version.

---

## 1. First-Time Push to GitHub

### Step 1 — Create the repository on GitHub
1. Go to [github.com/new](https://github.com/new)
2. Repository name: `dach-idp-platform`
3. Description: `Production-ready DACH Intelligent Document Processing Platform — Azure AI, FastAPI, GDPR`
4. Set to **Public** (required for portfolio visibility)
5. **Do NOT** tick "Add README" or "Add .gitignore" — the repo already has these
6. Click **Create repository**

### Step 2 — Connect and push from your computer

Open a terminal, `cd` into the `dach-idp-platform` folder you received, then run:

```bash
# Add your GitHub repo as the remote origin
git remote add origin https://github.com/YOUR_USERNAME/dach-idp-platform.git

# Push all commits AND all version tags (v1.0.0, v2.0.0, etc.)
git push -u origin main --follow-tags
```

That's it. Both the `v1.0.0` and `v2.0.0` tags will appear on GitHub under
**Releases → Tags**.

---

## 2. Adding a New Feature (Agile Flow)

Every time you want to add something new, follow this exact pattern:

```
main  ──── v1.0.0 ──── v2.0.0 ──── v2.1.0 ──── v3.0.0 ...
```

### The 5-step process

```bash
# 1. Make sure you are on the latest main
git checkout main
git pull origin main

# 2. Create a feature branch
git checkout -b feature/my-new-feature

# 3. Make your changes, then stage and commit
git add .
git commit -m "feat: describe what you added"

# 4. Merge back into main
git checkout main
git merge feature/my-new-feature

# 5. Tag the new version
git tag -a v2.1.0 -m "v2.1.0: describe what this version adds"
git push origin main --follow-tags
```

Done — GitHub now shows the new tag and the full history is preserved.

---

## 3. Rolling Back to a Previous Version

If something breaks and you want to go back to v1.0.0 (or any other tag):

```bash
# Option A — just VIEW the old code without changing anything
git checkout v1.0.0

# Option B — create a new branch FROM the old version and work from there
git checkout -b hotfix/rollback-v1 v1.0.0

# Option C — hard reset main back to v1.0.0 (WARNING: loses newer commits)
git checkout main
git reset --hard v1.0.0
git push --force origin main
```

**Recommended:** use Option B — it's the safest and keeps all history intact.

---

## 4. Version Numbering Guide

| Change type | Example bump | When to use |
|---|---|---|
| **Major** (v1 → v2) | `v2.0.0 → v3.0.0` | Breaking API changes, new Azure service, major refactor |
| **Minor** (v2.0 → v2.1) | `v2.0.0 → v2.1.0` | New endpoints, new dashboard panels, new mock personas |
| **Patch** (v2.0.0 → v2.0.1) | `v2.0.0 → v2.0.1` | Bug fixes, typo corrections, test additions |

---

## 5. Branch Strategy (Recommended)

```
main          — always stable, always tagged
  ├── feature/xxx   — new feature (merge → main → tag)
  ├── fix/xxx       — bug fix (merge → main → tag patch)
  └── hotfix/xxx    — urgent fix from a tag (merge → main → tag patch)
```

Keep `main` clean — never push unfinished code directly to it.

---

## 6. What Claude Does When You Ask for New Features

When you say *"add feature X"*, here is exactly what happens:

1. The new code is written and tested
2. Files are updated in the repo folder on your computer
3. A new commit is made: `git commit -m "feat: X"`
4. A new version tag is created: e.g. `git tag -a v2.1.0 -m "v2.1.0: X"`
5. You run `git push origin main --follow-tags` to publish

You always have the full history — every version is recoverable.

---

## 7. Viewing Version History

```bash
# See all tags
git tag

# See what changed between versions
git diff v1.0.0 v2.0.0 --stat

# See the commit log
git log --oneline

# See what files a specific version contained
git show v1.0.0 --stat
```

---

## 8. Protecting Secrets

**Never commit real Azure credentials.** The `.env.example` file shows which variables to set.
Copy it to `.env` locally (it is in `.gitignore` so it won't be pushed):

```bash
cp .env.example .env
# then fill in your real values in .env
```

For production, use **Azure Key Vault** (already wired in `app/config.py`).

---

## 9. GitHub Actions CI (already configured)

The repo includes `.github/workflows/ci.yml`. Every push to `main` or any PR will automatically:
- Run `ruff` linting
- Run all 47 tests in mock mode (no Azure credentials needed)
- Build the Docker image

No setup needed — it works out of the box once the repo is on GitHub.
