# Devin Security Review — Installation Guide

This document details every step needed to install the Devin Security Review pipeline on a new repository. It is designed for enterprise deployment and includes permission rationale for CISO review.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Secrets Configuration](#secrets-configuration)
3. [Workflow Installation](#workflow-installation)
4. [CodeQL Configuration](#codeql-configuration)
5. [Permissions Reference](#permissions-reference)
6. [Verification](#verification)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Requirement | Details |
|-------------|---------|
| GitHub repository | Any GitHub.com or GitHub Enterprise Cloud repository |
| GitHub Actions | Must be enabled for the repository |
| Code scanning | GitHub Advanced Security must be enabled (free for public repos, requires GHAS license for private repos) |
| Devin account | Any tier (Free, Team, or Enterprise) with API access |
| Languages supported | Python (currently). Extensible to JavaScript, Java, Go, C/C++ — see CodeQL Configuration |

---

## Secrets Configuration

Two secrets must be added to the repository (or organization) settings. Navigate to **Settings → Secrets and variables → Actions → New repository secret**.

### Secret 1: `GH_PAT` — GitHub Personal Access Token

**What**: A GitHub Personal Access Token (classic or fine-grained) used by the workflow to read code scanning alerts, post PR comments, and manage labels.

**Why not use `GITHUB_TOKEN`?**: The built-in `GITHUB_TOKEN` has limited access to the Code Scanning API. Reading alerts across refs (PR merge ref vs main) and managing labels requires a PAT with broader permissions. This is a GitHub platform limitation.

**Required scopes (Classic PAT)**:

| Scope | Why | What it accesses |
|-------|-----|-----------------|
| `repo` | Read/write repository contents, PRs, issues, labels | Needed to post PR comments, add/remove labels, read PR metadata |
| `security_events` | Read code scanning alerts | Needed to fetch CodeQL alerts from the Code Scanning API (`/code-scanning/alerts`) |

**Required permissions (Fine-grained PAT)**:

| Permission | Access level | Why |
|------------|-------------|-----|
| Contents | Read | Read repository files and refs for alert comparison |
| Pull requests | Read and write | Post/update PR comments |
| Issues | Read and write | Manage PR labels (PRs are issues in GitHub's API) |
| Code scanning alerts | Read | Fetch CodeQL alert data |
| Metadata | Read | Required by all fine-grained PATs |

**CISO rationale**: This token only needs read access to code scanning data and write access to PR comments/labels. It does NOT need:
- ~~`admin:org`~~ — No org-level access needed
- ~~`delete_repo`~~ — No destructive operations
- ~~`admin:repo_hook`~~ — No webhook management
- ~~`workflow`~~ — Does not modify workflow files

**Token owner**: Should be a machine account (bot user) or service account dedicated to the security review pipeline. This limits blast radius if the token is compromised.

**Recommended token expiration**: 90 days (rotate quarterly via your secrets management system).

---

### Secret 2: `DEVIN_API_KEY` — Devin Service API Key

**What**: A Devin API key used to create sessions that analyze and fix security vulnerabilities.

**Key type**: Service User API key (`apk_` prefix) — works with Devin v1 API on all plan tiers (Free, Team, Enterprise).

**How to obtain**:
1. Log in to [app.devin.ai](https://app.devin.ai)
2. Navigate to **Settings → API Keys**
3. Create a new API key (or use an existing one)
4. Copy the key (starts with `apk_`)

**What this key can do**:
- Create Devin sessions (POST `/v1/sessions`)
- List sessions (GET `/v1/sessions`)
- Get session details (GET `/v1/sessions/{id}`)
- Send messages to sessions (POST `/v1/sessions/{id}/message`)

**What this key CANNOT do**:
- Access your source code directly (Devin clones via its own GitHub integration)
- Modify organization settings
- Access billing or user management
- Access other customers' data

**CISO rationale**: The API key is scoped to session management only. Devin accesses the repository through its own GitHub App integration (see "Devin GitHub Access" below), not through this API key. The key simply orchestrates sessions — it cannot read code, secrets, or credentials from your infrastructure.

**Recommended rotation**: Quarterly, or immediately if compromised.

---

### Secret 3 (Optional): Devin GitHub App Access

**What**: Devin needs access to clone and push to your repository. This is configured through Devin's GitHub App integration, NOT through the secrets above.

**How to configure**:
1. In Devin settings, go to **Git Connections**
2. Connect your GitHub organization
3. Grant access to the specific repository (or all repositories)

**What Devin's GitHub App needs**:

| Permission | Why |
|------------|-----|
| Repository contents: Read and write | Clone the repo, read code for context, push fix commits |
| Pull requests: Read | Read PR metadata to understand which branch to push to |
| Metadata: Read | Required by GitHub Apps |

**CISO rationale**: Devin's GitHub App access is the standard GitHub App OAuth model. It:
- Only accesses repositories you explicitly grant access to
- Uses short-lived installation tokens (not long-lived PATs)
- Can be revoked instantly from GitHub Settings → Applications
- Follows GitHub's permission model (no admin access, no org-level access)
- All actions are logged in GitHub's audit log under the Devin app

---

## Workflow Installation

### Step 1: Copy workflow files

Copy these files into the target repository:

```
.github/workflows/devin-security-review.yml   # Main workflow
.github/workflows/codeql.yml                  # CodeQL analysis config
```

### Step 2: Customize the workflow

Edit `devin-security-review.yml` if needed:

| Setting | Default | Where to change | Notes |
|---------|---------|-----------------|-------|
| Max attempts per alert | 2 | Step 5 (`MAX_ATTEMPTS = 2`) | Higher = more retries before marking unfixable |
| Max sessions per run | 20 | Step 7 (`max_total_sessions = 20`) | Cap on total Devin sessions created per workflow run |
| Concurrent sessions | 3 | Step 7 (`max_concurrent = 3`) | Sessions created before a 30s pause |
| Alerts per batch | 15 | Step 7 (`max_per_batch = 15`) | Max alerts sent to a single Devin session |
| ACU limit per session | 10 | Steps 6 & 7 (`max_acu_limit: 10`) | Caps compute cost per Devin session |
| Unfixable alert label | `devin:manual-review-needed` | Step 9 | GitHub label name for PRs with unfixable alerts |

### Step 3: Customize CodeQL configuration

Edit `codeql.yml` to match the target repository's languages:

```yaml
strategy:
  matrix:
    language: [ 'python' ]           # Add: javascript, java, go, csharp, cpp, ruby, swift
    # For compiled languages, you may need a build command:
    # include:
    #   - language: java
    #     build-mode: autobuild
```

**Query suite options**:
| Suite | Coverage | False positive rate |
|-------|----------|-------------------|
| `default` | Standard security queries only | Low |
| `security-extended` | Standard + extended security queries | Medium |
| `security-and-quality` (recommended) | All security + code quality queries | Higher, but Devin filters with full context |

### Step 4: Add secrets to the repository

1. Go to repository **Settings → Secrets and variables → Actions**
2. Add `GH_PAT` with your GitHub PAT
3. Add `DEVIN_API_KEY` with your Devin API key

### Step 5: Verify Devin's GitHub access

1. In Devin, go to **Settings → Git Connections**
2. Confirm the target repository is listed and accessible
3. Devin should be able to clone and push to the repository

---

## CodeQL Configuration

### Default configuration (recommended for most repos)

The provided `codeql.yml` includes:

```yaml
queries: security-and-quality     # Broadest query suite
threat-models:
  - remote                        # Network-based attacks (API, HTTP)
  - local                         # File-based, env var, CLI attacks
```

### Custom configuration (advanced)

For organizations with custom security policies, create `.github/codeql/codeql-config.yml`:

```yaml
name: "Custom CodeQL Config"

# Add custom query packs
packs:
  python:
    - codeql/python-queries:codeql-suites/python-security-and-quality.qls
    # Add your custom packs here:
    # - your-org/custom-security-queries

# Exclude paths from analysis (e.g., vendor, generated code)
paths-ignore:
  - '**/node_modules/**'
  - '**/vendor/**'
  - '**/*.generated.*'
  - '**/test/**'
  - '**/tests/**'
```

Then reference it in `codeql.yml`:

```yaml
- name: Initialize CodeQL
  uses: github/codeql-action/init@v3
  with:
    languages: ${{ matrix.language }}
    config-file: .github/codeql/codeql-config.yml
```

---

## Permissions Reference

### Complete permission map

This table shows every permission the pipeline needs, what uses it, and what would break without it.

| Permission | Used by | Required for | What breaks without it |
|------------|---------|--------------|----------------------|
| `repo` (PAT scope) | Workflow | Post PR comments, manage labels | No PR feedback — workflow runs silently |
| `security_events` (PAT scope) | Workflow | Read CodeQL alerts | Cannot fetch alerts — workflow exits with 0 alerts |
| `contents: read` (workflow) | checkout action | Clone repo in CI | Workflow fails at checkout step |
| `security-events: write` (workflow) | CodeQL upload | Upload SARIF results | CodeQL results not visible in Security tab |
| `pull-requests: write` (workflow) | Comment posting | Post/update PR comments | No developer visibility into results |
| Devin GitHub App: contents read+write | Devin sessions | Clone repo, push fix commits | Devin can analyze but cannot push fixes |
| Devin GitHub App: pull-requests read | Devin sessions | Read PR metadata | Devin cannot determine correct branch |
| Devin API key | Workflow | Create Devin sessions | No automated fix sessions created |

### What we DON'T need (and why)

| Permission | Why we don't need it |
|------------|---------------------|
| `admin:org` | No org-level operations. Everything is repo-scoped. |
| `admin:repo_hook` | No webhook creation/management. We use GitHub Actions events. |
| `workflow` | We don't modify workflow files programmatically. |
| `delete_repo` | No destructive operations on the repository. |
| `admin:gpg_key` | No key management needed. |
| `user` | No user profile access needed. |
| `notifications` | No notification management. We use PR comments. |
| Devin GitHub App: admin | No admin operations on the repository. |
| Devin GitHub App: secrets | No access to repository secrets (Devin uses its own config). |

---

## Verification

After installation, verify the pipeline works end-to-end:

### Quick verification (5 minutes)

1. Create a branch and add a file with a known vulnerability:

```python
# test_vuln.py
import sqlite3
from flask import Flask, request

app = Flask(__name__)

@app.route("/search")
def search():
    query = request.args.get("q", "")
    conn = sqlite3.connect("app.db")
    results = conn.execute(f"SELECT * FROM users WHERE name = '{query}'").fetchall()
    return str(results)
```

2. Open a PR with this file against `main`
3. Wait for CodeQL to complete (~2-5 minutes)
4. Verify the Devin Security Review workflow runs
5. Check the PR comment for alert summary and Devin session link
6. Verify Devin creates a session and starts working on the fix
7. After Devin pushes, verify the PR comment updates (not a new comment)
8. Delete the test branch

### Full verification (30 minutes)

Run the full test suite documented in `TESTS.md`. Key scenarios:
- T1: CodeQL detects vulnerabilities
- T3: Devin session created with correct prompt
- T4: Only 1 comment (edited in place)
- T5: Loop stops after 2 attempts
- T7: Safe-to-merge signal accurate

---

## Troubleshooting

### "No alerts found" but vulnerabilities exist

**Cause**: CodeQL is not configured for the correct language.
**Fix**: Check `codeql.yml` matrix includes the language of the vulnerable file. If the file was added in a PR and the language didn't exist on `main` before, you need the explicit `codeql.yml` (not GitHub's "default setup").

### "ERROR: Failed to create Devin session"

**Cause**: Devin API key is invalid, expired, or rate limited.
**Fix**: Verify the `DEVIN_API_KEY` secret is set correctly. Check the Devin API response body in the workflow logs for details.

### PR comment not appearing

**Cause**: `GH_PAT` doesn't have `repo` scope, or the token has expired.
**Fix**: Regenerate the PAT with `repo` and `security_events` scopes.

### CodeQL alerts not visible in Code Scanning API

**Cause**: GitHub Advanced Security is not enabled (required for private repos).
**Fix**: Go to **Settings → Code security and analysis → GitHub Advanced Security → Enable**.

### Devin can't push to the repository

**Cause**: Devin's GitHub App doesn't have write access to the repository.
**Fix**: Go to Devin **Settings → Git Connections** and grant access to the repository.

### Branch protection blocks Devin pushes

**Cause**: Branch protection rules require PR reviews or status checks before pushing.
**Fix**: Either:
- Add Devin's GitHub App to the "bypass" list in branch protection rules
- Or: Change the workflow to have Devin create a sub-PR instead of pushing directly (requires workflow modification)

---

## Enterprise Deployment Checklist

For deploying across an organization:

- [ ] Create a dedicated machine account (bot user) for the `GH_PAT`
- [ ] Store secrets in GitHub organization-level secrets (shared across repos)
- [ ] Create a Devin service user with a dedicated API key
- [ ] Grant Devin's GitHub App access to all target repositories
- [ ] Copy workflow files to each repository (or use a GitHub Actions reusable workflow)
- [ ] Configure CodeQL for each repository's language stack
- [ ] Test on a non-critical repository first
- [ ] Monitor initial runs for false positives and adjust query suite if needed
- [ ] Set up quarterly PAT/API key rotation schedule
- [ ] Brief the security team on the `devin:manual-review-needed` label workflow
- [ ] Document escalation path for unfixable alerts
