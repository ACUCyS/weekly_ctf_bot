# Contribution Guideline - Weekly CTF Bot

First off, thank you for considering contributing! We welcome all kinds of contributions — from bug reports and documentation fixes to new features and performance improvements. This guide will help you get started.

## ⭕ Reporting Issues

If you find a bug or have a feature request, please:

1. Search existing issues to avoid duplicates.
2. Open a new issue in the Issues tab with:
   - A clear title (e.g., “feat(commands): support flag submission modal”).
   - A concise description of the problem or desired behavior.
   - Steps to reproduce (for bugs) or rationale (for features).
   - Screenshots or logs, if applicable.

## 🌱 Branching Strategy

### Branch Structure

- `main` - Production branch
- `dev` - Development branch

### Branch Naming Convention

Feature branches must follow the pattern:

```
<feature-name>/<your-name>
```

**Feature branches must always branch off from the latest `dev` branch.**

## ✒️ Commit Messages

We adhere to the [Conventional Commits](https://www.conventionalcommits.org/) specification to keep our history clean and meaningful.

**Format:**

```
<type>(<scope>): <short description>
```

**Example:**

```
feat(challenges): add hint command for CTFd
```

**If there are multiple changes to many different files, please do not include all your changes in one single commit.  
Instead, break it down into smaller, more focused commits using the above listed format.**

## 🔃 Pull Requests

- PRs should **always** target the `dev` branch.
- Make sure your branch is up to date with `dev` before opening a PR.
- Fill out the PR template, including:
  - Describe what your PR does (scope, deliverables, what changed, why).
  - Related issue number (if applicable).
  - Include screenshots (if applicable).
- Address any feedback recieved:
  - Make additional commits to your feature branch.
  - Rebase or merge latest `dev` as needed.

## 🙌 Thank You!

We appreciate your time and effort 💗
