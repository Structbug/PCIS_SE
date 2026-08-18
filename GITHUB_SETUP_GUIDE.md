# Push This Folder to GitHub — Step-by-Step Guide

This guide turns the `Actual Project` folder into its own GitHub repository.

## Prerequisites

- A GitHub account
- Git installed (check with `git --version`)
- GitHub CLI (`gh`) installed OR you can create the repo on the GitHub website

---

## Step 0 — Why you need to read this (your current setup)

Before starting, note these two gotchas that will break a normal `git push`:

1. **The current git repo root is the parent folder**
   (`6th Semester/Software Engineering`), not this folder. It has no commits
   yet and its working tree contains unrelated files (PDFs, DOCX, `.env`
   files, `node_modules/`). Pushing from there would upload secrets and junk.
2. **`django_migration/.git` is a nested, empty git repo.** If you leave it,
   Git treats it as an *embedded repository* and will NOT push its contents.
   It has no commits, so deleting it is safe.

This guide creates a **fresh, clean repo** that contains only this folder.

---

## Step 1 — Remove the leftover/nested `.git` folders

Open a terminal inside `Actual Project` and run:

```bash
# 1a. Delete the empty leftover .git dir that is just sitting here
rm -rf .git

# 1b. Delete the nested empty repo inside django_migration (it has no commits)
rm -rf django_migration/.git
```

> The `django_migration/.git` has no commits, so nothing is lost. If it ever
> had commits you wanted, you'd copy the folder out first instead.

---

## Step 2 — Create a `.gitignore` at the folder root

Create a file named `.gitignore` in `Actual Project` (same level as the
`frontend/` and `django_migration/` folders) with this content:

```gitignore
# Environment / secrets
.env
*.env
!*.env.example

# Python / Django
__pycache__/
*.py[cod]
*.sqlite3
staticfiles/
.venv/
venv/
logs
*.log

# Node / Vite
node_modules/
dist/
dist-ssr/
*.local

# Editor / OS
.vscode/*
!.vscode/extensions.json
.idea
.DS_Store
*.suo
*.ntvs*
*.njsproj
*.sln
*.sw?
```

> **Security note:** the `!*.env.example` line keeps `.env.example` files
> (safe templates) but excludes every real `.env`. Do NOT push `.env`,
> `atlas-credentials.env`, or any file containing passwords/tokens.

---

## Step 3 — Initialize the repo and commit

Run these from the `Actual Project` folder:

```bash
# 3a. Start a fresh git repo in THIS folder
git init

# 3b. See exactly what will be added
git status

# 3c. Stage everything (the .gitignore above keeps secrets/junk out)
git add .

# 3d. Verify no secrets are staged (read this list!)
git status

# 3e. First commit
git commit -m "Initial commit: inventory management system (Django + React)"
```

If anything sensitive (`.env`, `node_modules/`) appears in `git status` at
step 3d, fix the `.gitignore` before committing.

---

## Step 4 — Create the repository on GitHub

### Option A: with GitHub CLI

```bash
gh auth login
gh repo create inventory-management-system --private --source=. --push
```

> Use `--public` instead of `--private` if you want it public. This command
> creates the repo AND pushes, so you can skip Step 5.

### Option B: on the GitHub website

1. Go to <https://github.com/new>
2. Name: `inventory-management-system`
3. Choose **Private** or **Public**
4. Leave "Add a README" **unchecked**
5. Click **Create repository**

---

## Step 5 — Link and push

Run this from the `Actual Project` folder (skip if you used `gh repo create`):

```bash
# Replace YOUR_USERNAME with your GitHub username
git remote add origin https://github.com/YOUR_USERNAME/inventory-management-system.git

git branch -M main
git push -u origin main
```

You're done. Refresh your GitHub page — the code should be there.

---

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `remote origin already exists` | `git remote set-url origin <new-url>` |
| `push rejected: failed to push some refs` | You created the repo with a README; run `git pull origin main --rebase` then `git push` again. |
| `.env` or `node_modules` got committed | `git rm -r --cached .env node_modules`, add them to `.gitignore`, commit again, then push. |
| `embedded repository` warning | You missed Step 1b; delete `django_migration/.git`. |

---

## Quick reference (all commands, in order)

```bash
rm -rf .git django_migration/.git     # clean up nested repos
git init
git add .
git commit -m "Initial commit: inventory management system (Django + React)"
gh repo create inventory-management-system --private --source=. --push
# or, without gh:
#   git remote add origin https://github.com/YOUR_USERNAME/inventory-management-system.git
#   git branch -M main
#   git push -u origin main
```
