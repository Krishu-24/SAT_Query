# 🤝 Team Workflow & Contributing Guide

Welcome to the SatQuery AI team! Since we have 6 members working in parallel across frontend, backend, and machine learning pipelines, we need a strict but simple workflow to avoid merge conflicts and lost work.

## 🌳 Branching Strategy

**NEVER commit directly to the `main` branch.**

1. **`main`** - This is our stable, working POC branch. It should always be deployable.
2. **Feature Branches** - Every member creates a branch for their specific task. 

### How to name your branches:
Use the format: `[member_id]/[feature_name]`
- Example (M1): `m1/api-error-handling`
- Example (M2): `m2/react-dashboard`
- Example (M4): `m4/tinycd-integration`

## 🔄 The Daily Workflow

### 1. Update your local repository
Always pull the latest changes from `main` before starting your work to avoid conflicts.
```bash
git checkout main
git pull origin main
```

### 2. Create your branch
```bash
git checkout -b m[X]/your-feature-name
```
*(Replace `[X]` with your member number)*

### 3. Work and Commit
Write your code, test it, and commit it. Write clear commit messages.
```bash
git add .
git commit -m "feat(router): add validation for geotiff formats"
```

### 4. Keep your branch updated (Crucial!)
While you are working, other members will be merging their code into `main`. **You must continuously pull their changes into your branch** so you don't fall behind.
```bash
# While on your feature branch:
git pull origin main
```
*Resolve any merge conflicts locally if they occur.*

### 5. Push and Create a Pull Request (PR)
When your feature is done and tested locally:
```bash
git push origin m[X]/your-feature-name
```
Then, go to GitHub and open a **Pull Request** from your branch into `main`.

### 6. Review and Merge
- Ping the team in your group chat to review your PR.
- **Do not merge your own PR without someone else looking at it.**
- Once approved, merge it into `main` and delete your feature branch.

## 🚨 Golden Rules
1. **Communicate**: If you are changing a core schema in `backend/app/api/schemas.py` or a core router file, tell the team! Other people depend on these contracts.
2. **Pull frequently**: `git pull origin main` is your best friend. Do it every morning and every time someone merges a PR.
3. **Don't break the stubs until ready**: If you are implementing a real ML model, make sure it returns the exact same JSON structure as the stub it is replacing.
