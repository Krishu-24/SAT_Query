# Team Workflow and Contributing Guide

This project is designed for parallel work across backend, frontend, and ML components. A simple and disciplined workflow keeps the repo stable and prevents merge conflicts.

## Branching Strategy

Do not commit directly to `main`.

1. `main` is the stable branch for verified, working code.
2. Every task should be developed on a feature branch.

Branch naming format:

```text
[member_id]/[feature_name]
```

Examples:

- `m1/api-error-handling`
- `m2/react-dashboard`
- `m4/tinycd-integration`

## Daily Workflow

### 1. Sync with the latest main branch

```bash
git checkout main
git pull origin main
```

### 2. Create a feature branch

```bash
git checkout -b m[X]/your-feature-name
```

Replace `[X]` with the relevant member number.

### 3. Commit work in small, reviewable chunks

```bash
git add .
git commit -m "feat(router): add validation for geotiff inputs"
```

### 4. Keep the branch up to date

Other team members will merge to `main` while you work. Stay synchronized.

```bash
git pull origin main
```

Resolve conflicts locally before continuing.

### 5. Push and open a pull request

```bash
git push origin m[X]/your-feature-name
```

Open a pull request into `main` and request review from the appropriate team member.

### 6. Review and merge

- Request review before merging.
- Do not merge your own pull request without another reviewer.
- Once approved, merge into `main` and remove the feature branch.

## Team Standards

1. Communicate early when changing shared interfaces such as `backend/app/api/schemas.py` or routing contracts.
2. Pull from `main` frequently to minimize divergence.
3. Do not break stub contracts until the replacement implementation is ready and tested.
4. Keep commit messages specific and traceable to the work being done.

## Review Checklist

Before opening a pull request, confirm:

- the feature works locally
- the relevant tests or smoke checks pass
- the output remains compatible with the API contract
- the branch is current with `main`
