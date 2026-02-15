# Devin Automated Security Review — Design Document

## Table of Contents

1. [Product Overview](#product-overview)
2. [Architecture](#architecture)
3. [Pipeline Flow](#pipeline-flow)
4. [CodeQL Configuration](#codeql-configuration)
5. [Alert Classification](#alert-classification)
6. [Devin Session Strategy](#devin-session-strategy)
7. [Fix Quality — How We Beat Autofix](#fix-quality--how-we-beat-autofix)
8. [Batching Strategy](#batching-strategy)
9. [Cross-Linking and Developer Experience](#cross-linking-and-developer-experience)
10. [Design Decisions Log](#design-decisions-log)
11. [Secrets and Authentication](#secrets-and-authentication)
12. [Limitations and Future Work](#limitations-and-future-work)

---

## Product Overview

A closed feedback loop that automatically detects security vulnerabilities via CodeQL static analysis and dispatches Devin AI sessions to propose and apply fixes — with full codebase context, verification, and developer visibility.

**What it does:**
- Runs CodeQL on every pull request to detect security vulnerabilities
- Classifies alerts as "new in this PR" vs "pre-existing on main"
- Creates targeted Devin sessions that clone the repo, understand the full codebase, and apply fixes
- Pushes fix commits directly to the PR branch (for new alerts) or opens a batch fix PR (for pre-existing alerts)
- Posts PR comments with alert summaries, Devin session links, and cross-references

**Who it's for:** Development teams who want automated, high-quality security remediation integrated into their existing PR review workflow.

---

## Architecture

```
Developer opens PR
        |
        v
+------------------+
|   CodeQL Analysis |  (codeql.yml)
|   - Python        |
|   - Actions       |
|   - security-and- |
|     quality suite |
+------------------+
        |
        v  (all analyses complete)
+---------------------------+
| Devin Security Review     |  (devin-security-review.yml)
| Workflow                  |
|                           |
| 1. Wait for CodeQL        |
| 2. Fetch alerts via API   |
| 3. Classify alerts        |
|    - New in PR            |
|    - Pre-existing on main |
| 4. Create Devin sessions  |
| 5. Post PR comments       |
+---------------------------+
        |                    \
        v                     v
+------------------+   +-------------------+
| Devin Session    |   | Devin Session(s)  |
| (new-in-PR)      |   | (pre-existing)    |
|                  |   |                   |
| - Clones repo   |   | - Clones repo     |
| - Full context   |   | - Full context    |
| - Fixes issues   |   | - Fixes issues    |
| - Runs CodeQL    |   | - Runs CodeQL     |
|   to verify      |   |   to verify       |
| - Runs tests     |   | - Runs tests      |
| - Pushes to PR   |   | - Opens batch PR  |
|   branch         |   |   off main        |
+------------------+   +-------------------+
        |                     |
        v                     v
  PR updated with       Batch fix PR created
  fix commits            + cross-linked
```

### Components

| Component | File | Purpose |
|-----------|------|---------|
| CodeQL Workflow | `.github/workflows/codeql.yml` | Static analysis with optimal vulnerability detection config |
| Security Review Workflow | `.github/workflows/devin-security-review.yml` | Orchestrator: waits for CodeQL, fetches alerts, creates Devin sessions, posts comments |
| Devin v1 API | External service | AI agent that clones repos, understands code, proposes and applies fixes |
| GitHub Code Scanning API | External service | Provides structured alert data (rule ID, severity, file, line, taint flow) |

---

## Pipeline Flow

### Step 1: CodeQL Analysis

Triggered on every PR to `main`. Runs a matrix of language analyzers:

- **Python**: Detects SQL injection, command injection, XSS, open redirect, etc.
- **Actions**: Detects workflow permission issues, code injection in workflows

Uses the `security-and-quality` query suite with `remote` + `local` threat models for maximum coverage.

### Step 2: Wait for CodeQL Completion

The security review workflow polls GitHub's check runs API every 30 seconds until all CodeQL-related checks (both `CodeQL` and `Analyze (*)` jobs) report `completed`. Timeout after 20 minutes.

### Step 3: Fetch and Classify Alerts

Fetches alerts from the GitHub Code Scanning API for the PR's merge ref. Each alert includes:
- Rule ID and description
- Severity (critical, high, medium, low)
- File path and line numbers
- Alert message with remediation hints
- Whether it was introduced by this PR

**Classification logic:**
- **New in PR**: Alert's `introduced_in_pull_request` matches the current PR number, or the alert's file/line is part of the PR diff
- **Pre-existing**: Alert exists on `main` branch (detected because CodeQL scans the merge ref which includes main's code)

### Step 4: Create Devin Sessions

**For new-in-PR alerts (1 session):**
- Prompt includes: PR number, branch name, alert details with taint flow
- Instructions: clone repo, checkout PR branch, fix issues, verify with CodeQL, run tests, push to PR branch
- Result: Fix commits appear directly on the developer's PR

**For pre-existing alerts (batched sessions):**
- Grouped by file, capped at 15 alerts per session
- Prompt includes: alert details, target branch name (`devin/security-fixes-{timestamp}`)
- Instructions: clone repo, create branch off main, fix issues, verify, push
- After all sessions complete: one batch fix PR opened off main

### Step 5: Post PR Comments

Comment on the original PR with:
- Alert count and summary table
- Devin session URL(s) for visibility into what Devin is doing
- Link to batch fix PR (if pre-existing alerts were found)
- Status of each session

---

## CodeQL Configuration

### Why We Use Advanced Setup (Not Default)

GitHub's "default setup" auto-detects languages present on the `main` branch. This fails when:
- New languages are introduced via PR (e.g., Python code added for the first time)
- The repo uses languages that aren't auto-detected reliably

**Our approach**: Explicit `codeql.yml` workflow with a language matrix that we control.

### Query Suite: `security-and-quality`

CodeQL offers three query suites:

| Suite | Coverage | False Positive Rate | What it catches |
|-------|----------|-------------------|-----------------|
| `default` | Baseline | Lowest | High-confidence security issues only |
| `security-extended` | Broader | Moderate | Adds lower-confidence security queries |
| `security-and-quality` | Maximum | Highest | All security queries + code quality issues |

**We chose `security-and-quality`** because:
- Catches the widest range of vulnerabilities
- Includes queries that other suites miss (e.g., Flask debug mode, reflected XSS patterns)
- False positives are acceptable because Devin reviews each alert with full context before fixing — it can skip false positives intelligently
- The cost of missing a real vulnerability outweighs the cost of processing a few false positives

### Threat Models: `remote` + `local`

| Threat Model | Sources Considered Tainted | Default? |
|-------------|---------------------------|----------|
| `remote` | HTTP requests, API inputs, WebSocket data | Yes |
| `local` | File reads, environment variables, CLI arguments, database values | No |

**We enable both** because:
- `remote` covers the standard web attack surface (injection via HTTP parameters)
- `local` catches vulnerabilities where attacker-controlled data enters via files, environment variables, or CLI arguments — common in CLI tools, data pipelines, and server configs
- Real-world attackers exploit both vectors

### Language Matrix

Explicit matrix with `build-mode: none` for interpreted languages (Python, Actions). Compiled languages would use `build-mode: autobuild` or `build-mode: manual` with custom build steps.

---

## Alert Classification

### New-in-PR vs Pre-Existing

This classification determines the fix strategy:

| Alert Type | How to Identify | Fix Strategy |
|-----------|----------------|--------------|
| New in PR | Alert was introduced by code in the PR diff | Push fix commit to the PR branch |
| Pre-existing | Alert exists on main (code was already there) | Batch fix PR off main |

**Detection method**: The GitHub Code Scanning API includes the field `most_recent_instance.ref` and can be filtered by `ref=refs/pull/N/merge` vs `ref=refs/heads/main`. Alerts that appear only on the merge ref (and not on main) were introduced by the PR.

### Why This Matters

You cannot create a "separate fix PR" for code that only exists on an unmerged branch. The code isn't on `main` yet, so a branch off `main` can't fix it. The only clean options for new-in-PR code are:
1. Push fix commits to the same PR branch (our approach)
2. Open a sub-PR targeting the PR branch (more complex)
3. Comment the fix as text (manual, more friction)

We chose option 1 for simplicity and minimal friction.

---

## Devin Session Strategy

### Why Devin (vs Template-Based Autofix)

Devin is a full AI software engineer that:
- **Clones the entire repository** and navigates it like a human developer
- **Understands call chains**: traces how a vulnerable function is called, what data flows through it
- **Follows existing patterns**: if the codebase uses SQLAlchemy, Devin uses parameterized queries via SQLAlchemy — not raw SQL
- **Verifies its own fixes**: can re-run CodeQL after applying a fix to confirm the alert is resolved
- **Runs tests**: executes the existing test suite to catch regressions

### Session Prompt Design

The prompt given to each Devin session is carefully structured:

```
1. Context: PR number, repo, branch name
2. Alert details: rule ID, description, severity, file, line, taint flow
3. Instructions:
   a. Clone the repo and checkout the correct branch
   b. Read and understand the surrounding code context before fixing
   c. Follow existing codebase patterns and conventions
   d. Apply minimal, focused fixes for each alert
   e. Re-run CodeQL locally to verify the alert is resolved
   f. Run the existing test suite to catch regressions
   g. Do NOT suppress or ignore alerts — fix the root cause
   h. Push the fix commit(s) to the specified branch
```

### Concurrency and Rate Limiting

- **New-in-PR**: 1 session (PRs typically have few new alerts); if >20 alerts, split by file
- **Pre-existing batches**: 3 concurrent sessions, processed in waves with 30s pauses
- Max 20 sessions per workflow run to cap resource usage
- Prevents overwhelming the Devin API or GitHub Actions quotas

### Non-Blocking Design

The workflow does NOT block the PR while Devin fixes issues:
1. Workflow posts PR comment with alert classification + Devin session links
2. Workflow exits immediately (success)
3. Devin sessions run asynchronously — developer can continue working on the PR
4. Fixes appear as new commits on the PR branch when Devin finishes

This means the security review never delays PR merging — it runs in parallel.

---

## Fix Quality — How We Beat Autofix

GitHub's Autofix (and similar tools) have a known limitation: *"The system may suggest fixes that fail to remediate the underlying security vulnerability and/or introduce new security vulnerabilities."*

### Root Causes of Autofix Failures

| Autofix Weakness | Why It Happens |
|-----------------|----------------|
| Limited context | Only sees the flagged file + a few neighbors; misses how the code is used elsewhere |
| Template-based | Applies pattern-matched fix templates; doesn't reason about the specific codebase |
| No verification | Suggests a fix but never checks if it actually resolves the CodeQL alert |
| May introduce new vulns | Without full context, a "fix" can shift the vulnerability elsewhere |
| Ignores existing patterns | May introduce new libraries or patterns that conflict with codebase conventions |

### How We Address Each

| Weakness | Our Approach | Why It's Better |
|----------|-------------|----------------|
| Limited context | Devin clones the **entire repo** — understands imports, call chains, shared utilities, test suites | Full codebase context means fixes are informed by how the code is actually used |
| Template-based | Devin **reasons** about each fix — chooses between parameterized queries, ORM methods, or existing sanitizers based on what the codebase already uses | Context-aware reasoning produces idiomatic fixes |
| No verification | Devin **re-runs CodeQL locally** after applying fixes to verify the alert is resolved | Closed verification loop ensures the fix actually works |
| May introduce new vulns | Devin **runs the existing test suite** after fixing to catch regressions | Test execution catches breakage and new issues |
| Ignores existing patterns | Prompt explicitly instructs Devin to follow codebase conventions | Fixes look like they were written by a team member |

### The Fix-Verify-Test Loop

```
Devin receives alert
    |
    v
Read surrounding code + understand context
    |
    v
Apply minimal fix following codebase patterns
    |
    v
Re-run CodeQL locally
    |
    +--> Alert still present? --> Revise fix --> Re-run CodeQL
    |
    v (alert resolved)
Run test suite
    |
    +--> Tests fail? --> Revise fix --> Re-run tests
    |
    v (tests pass)
Push fix commit
```

This loop is the core differentiator. No other automated security fix tool performs this level of end-to-end verification.

---

## Batching Strategy

### Problem: Scaling to Large Alert Counts

A mature codebase may have hundreds or thousands of pre-existing CodeQL alerts. We can't dump all of them into one Devin session (prompt/context limits), and we can't create thousands of sessions simultaneously.

### Approach: Prefer Same-File, Backfill to Fill Batch

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Primary grouping | By file path | Devin sees full file context; related alerts in the same file likely need coordinated fixes |
| Backfill | From other files | If a file has fewer alerts than the batch cap, fill remaining space with alerts from other files |
| Max alerts per session | 15 | Keeps the prompt focused; Devin can handle 15 alerts in one session effectively |
| Max concurrent sessions | 3 | Respects API rate limits; prevents resource contention |
| Max total sessions | 20 | Caps resource usage per workflow run |
| Commit granularity | 1 commit per alert | Each security issue is a separate commit for clean review and easy revert |

### Batching Algorithm

The goal is to minimize the number of PRs/sessions while keeping batches reviewable:

1. **Sort files by severity** — files containing the most critical alerts are processed first
2. **Fill batches from one file first** — if a file has ≥15 alerts, it gets its own batch(es)
3. **Backfill with other files** — if a file has <15 alerts, remaining batch space is filled with alerts from the next most severe files
4. **Each alert = 1 commit** — within a batch, every security fix is a separate commit referencing the CodeQL rule ID

**Tradeoff**: Prefer single-file batches (easier to review per-file PRs) but avoid wasting batch capacity on tiny groups (too many PRs for single issues). Backfilling balances review ergonomics with session efficiency.

### Batching Flow

```
100 pre-existing alerts
    |
    v
Group by file, sort by severity:
  - server.py: 5 alerts (critical, high, high, medium, medium)
  - auth.py: 12 alerts (high, medium, ...)
  - utils.py: 3 alerts (medium, low, low)
  - data_pipeline.py: 22 alerts --> split: batch of 15 + batch of 7
    |
    v
Build batches (cap = 15):
  Batch 1: data_pipeline.py (15 alerts) — full file batch
  Batch 2: data_pipeline.py (7) + server.py (5) + utils.py (3) = 15 — backfilled
  Batch 3: auth.py (12) — single file, under cap but no more alerts to backfill
    |
    v
Each batch → 1 Devin session → 1 branch with N commits (1 per alert)
    |
    v
All sessions push to shared branch: devin/security-fixes-{timestamp}
```

### Prioritization

When there are too many alerts to process in a reasonable time:
1. **Critical** severity first
2. **High** severity second
3. **Medium** and **Low** in subsequent runs
4. Cap total sessions per workflow run (configurable, default: 20)

---

## Cross-Linking and Developer Experience

### PR Comment Structure

**On the original PR (where alerts were found):**

```markdown
## Devin Security Review

### New Alerts (introduced in this PR): 3
| Severity | Rule | File | Status |
|----------|------|------|--------|
| critical | py/command-line-injection | app/server.py:23 | Fix pushed |
| high | py/sql-injection | app/server.py:16 | Fix pushed |
| medium | py/reflective-xss | app/server.py:18 | Fix pushed |

Devin Session: [View fix details](https://app.devin.ai/sessions/...)

### Pre-existing Alerts: 2
These alerts exist on main and are not introduced by this PR.
A batch fix PR has been opened: #4

Devin Sessions: [Session 1](https://...), [Session 2](https://...)
```

**On the batch fix PR:**

```markdown
## Automated Security Fixes

This PR addresses 2 pre-existing CodeQL alerts found during review of PR #3.

| Severity | Rule | File | Alert |
|----------|------|------|-------|
| medium | py/url-redirection | app/server.py:29 | Fixed |
| high | py/flask-debug | app/server.py:32 | Fixed |

Originally detected in: PR #3
Devin Sessions: [Session 1](https://...)
```

### Why Cross-Linking Matters

- Developer reviewing PR #3 sees both their new alerts AND knows about pre-existing issues
- The batch fix PR links back to the original PR for audit trail
- Devin session URLs provide full transparency into how each fix was derived
- Everything is traceable: alert -> session -> fix commit -> PR

---

## Design Decisions Log

| # | Decision | Options Considered | Chosen | Rationale |
|---|----------|-------------------|--------|-----------|
| 1 | CodeQL setup type | Default setup vs Advanced (workflow) | Advanced | Default auto-detects languages from main branch only; misses new languages introduced via PR |
| 2 | Query suite | `default`, `security-extended`, `security-and-quality` | `security-and-quality` | Maximum coverage; false positives acceptable because Devin filters them with full context |
| 3 | Threat models | `remote` only vs `remote` + `local` | Both | Catches more attack vectors (file-based, env var, CLI injection) |
| 4 | Fix delivery for new-in-PR | Same PR branch, sub-PR, comment-only | Same PR branch | Simplest; can't create separate PR for code that only exists on an unmerged branch |
| 5 | Fix delivery for pre-existing | Same PR, separate PR, hybrid | Separate batch PR | Clean separation; doesn't pollute original PR; code exists on main so branching works |
| 6 | Batching strategy | By file, by severity, by rule, fixed size | Prefer same-file, backfill to fill batch (cap 15) | Single-file batches are easier to review; backfilling avoids tiny batches; 1 commit per alert for clean revert |
| 7 | Devin API version | v1, v2, v3 | v1 | v2/v3 require Enterprise tier; v1 works with service API key on all plans |
| 8 | Session concurrency | Unlimited, fixed cap | 3 concurrent, max 20 total | Respects API limits; prevents resource contention |
| 9 | Verification approach | Trust the fix, re-run CodeQL, run tests | Re-run CodeQL + run tests | Closed loop ensures fix actually resolves the alert and doesn't break anything |
| 10 | CodeQL wait strategy | `workflow_run` trigger, polling check runs | Polling check runs | More reliable; `workflow_run` only fires after the entire workflow completes and has edge cases with multiple workflows |
| 11 | Comment management | Post new comment each run, edit existing comment | Edit existing (find by hidden marker) | Prevents comment flood when Devin pushes trigger re-runs; single comment stays up to date |
| 12 | Infinite loop prevention | No guard, max-runs, attempt tracking | Attempt tracking per alert (max 2) + Devin-commit detection | Tracks each alert's fix attempts via hidden markers in PR comment; after 2 failed attempts, alert marked unfixable and skipped forever |
| 13 | Fix verification | Trust the fix, re-run CodeQL in CI, local CodeQL CLI | Local CodeQL CLI inside Devin session (same config) | Catches bad fixes before they're pushed; prevents the push→CI→re-trigger loop entirely |
| 14 | Unfixable alert handling | Ignore, keep retrying, mark and skip | Mark as "unfixable" + GitHub label + PR comment section | Developers can filter by `devin:manual-review-needed` label; unfixable alerts listed in prominent comment section |
| 15 | Merge commit prevention | Regular merge, rebase | `git pull --rebase` in Devin prompt | Keeps commit history linear; falls back to merge if rebase conflicts |
| 16 | Rate limit handling | No handling, fixed delays, exponential backoff | Exponential backoff on 429 + concurrency pauses | Prevents session creation failures; respects API limits gracefully |
| 17 | Resource capping | No limit, fixed ACU, idempotent flag | `max_acu_limit=10` + `idempotent=true` per session | Caps compute cost per session; prevents duplicate sessions on re-runs |
| 18 | Blocked session mitigation | No handling, `playback_mode` API param | Documented limitation (no API param available) | Devin v1 API has no `playback_mode` or `dont_interrupt` parameter; "blocked" status means Devin finished work and is waiting for user response — this is normal end-state, not a failure |

---

## Edge Cases and Failure Modes

### Edge Case 1: Infinite Loop (Devin push → re-trigger → same alert → new session)

**Problem**: When Devin pushes a fix commit to the PR branch, GitHub triggers a new `pull_request` (synchronize) event. This re-runs CodeQL, which re-runs our workflow. If the fix didn't resolve the alert, the workflow creates another Devin session, which pushes another attempt, creating an infinite loop.

**Observed impact**: On PR #3, this caused 41 workflow runs, 14 PR comments, 8 Devin sessions, and ~73 minutes of wasted GitHub Actions time for a single `py/url-redirection` alert.

**Solution (3 layers)**:
1. **Attempt tracking**: Hidden HTML markers in the PR comment (`<!-- attempts:rule:file:line=N -->`) track how many times each alert has been attempted. After 2 attempts, the alert is marked unfixable and skipped.
2. **Devin-commit detection**: If the latest commit message matches `fix: [rule_id]...`, the workflow knows this is a Devin-triggered re-run and applies strict filtering.
3. **Comment editing**: Instead of posting a new comment each run, we find and update the existing one (identified by `<!-- devin-security-review -->` marker).

### Edge Case 2: Unfixable Alerts

**Problem**: Some CodeQL alerts cannot be auto-fixed because CodeQL's taint tracking is too conservative (e.g., `py/url-redirection` traces through `urlparse()` and considers the result user-controlled no matter what validation is applied).

**Solution**:
1. Devin verifies each fix locally using CodeQL CLI (same config: `security-and-quality` suite, `remote+local` threat models) before pushing
2. If the alert persists after 2 local fix attempts, Devin skips it and continues with remaining alerts
3. The workflow marks the alert as unfixable in the PR comment
4. A `devin:manual-review-needed` GitHub label is added to the PR
5. The PR comment includes a "REQUIRES MANUAL REVIEW" section with a table of unfixable alerts

**How developers find unfixable alerts**:
- Filter PRs by the `devin:manual-review-needed` label
- Look at the "REQUIRES MANUAL REVIEW" section in the bot's PR comment
- Filter CodeQL alerts in Security tab by `is:open` (unfixable alerts remain open)

### Edge Case 3: Blocked Devin Sessions

**Problem**: Devin sessions may enter "blocked" status, which means Devin finished its work and is waiting for human interaction. This is a normal end-state, not a failure.

**Investigation finding**: The Devin v1 API has no `playback_mode` or `dont_interrupt` parameter to prevent this. The `CreateSessionParams` only supports: `prompt`, `idempotent`, `knowledge_ids`, `max_acu_limit`, `playbook_id`, `secret_ids`, `session_secrets`, `snapshot_id`, `unlisted`, `structured_output`.

**Mitigation**:
- This is documented as a known limitation
- "Blocked" sessions have already completed their work (pushes, commits) — the status just means Devin is waiting for a follow-up message
- No resource waste occurs because the session's compute work is done
- The workflow does not poll for session completion (non-blocking design), so blocked sessions don't affect workflow execution

### Edge Case 4: Rate Limiting

**Problem**: Creating many Devin sessions quickly may hit API rate limits (HTTP 429). GitHub API also has rate limits (5000 req/hr for authenticated users).

**Solution**:
- **Devin API**: Exponential backoff on 429 responses (30s, 60s, 120s), max 3 retries per session creation
- **GitHub API**: Monitor `X-RateLimit-Remaining` headers; the workflow's operations (fetch alerts, post comment, manage labels) use ~5-10 API calls per run
- **Concurrency pauses**: 30s pause between waves of 3 concurrent sessions
- **Session caps**: Max 20 sessions per workflow run, `max_acu_limit=10` per session

### Edge Case 5: Merge Commits Cluttering History

**Problem**: When multiple actors push to the same branch concurrently (Devin sessions + developer), non-fast-forward pushes require merge commits.

**Solution**: Devin prompt instructs `git pull --rebase` before pushing. This rebases fix commits on top of the latest branch state, maintaining a linear history. If rebase fails (conflicts), Devin falls back to regular merge (better a merge commit than a failed push).

**Note**: In production, this is less of an issue because typically only Devin sessions push to the PR branch during the fix phase. The merge commits observed on PR #3 were caused by this development session also pushing to the same branch simultaneously.

### Edge Case 6: Large Enterprise Codebases (100K+ alerts)

**Problem**: A mature codebase may have thousands of pre-existing CodeQL alerts.

**Solution**:
- Batching: 15 alerts per session, prefer same-file grouping, backfill remaining space
- Prioritization: Critical severity first, then high, medium, low
- Session cap: Max 20 sessions per workflow run (300 alerts max per run)
- Rate limit handling: Exponential backoff prevents API failures
- Subsequent runs process the next batch of alerts (the attempt tracker prevents re-processing already-handled alerts)

### Edge Case 7: Infinite PR Creation from Pre-Existing Alert Batches

**Problem**: When pre-existing alerts are detected, the workflow creates Devin sessions that push fixes to a dedicated branch (`devin/security-fixes-pr{N}`). If Devin autonomously creates a PR from that branch targeting `main`, CodeQL runs on the new PR, detects the same (or new) alerts, triggers another Devin Security Review run, which creates more sessions — potentially cascading into infinite PR creation.

**Risk chain**:
```
PR #3 has pre-existing alerts
  → Workflow creates Devin session → pushes to devin/security-fixes-pr3
  → Devin autonomously opens PR #5 from that branch
  → CodeQL runs on PR #5 → detects alerts
  → Devin Security Review runs on PR #5 → creates sessions
  → Sessions push to devin/security-fixes-pr5
  → Devin opens PR #6 → ...
```

**Solution (4 layers)**:
1. **Deterministic branch names**: Pre-existing alert fix branches use `devin/security-fixes-pr{N}` (where N is the original PR number). If a cascade were to start, subsequent runs would push to the same branch rather than creating new ones.
2. **Explicit prompt instruction**: The Devin prompt for pre-existing alerts includes "Do NOT create a pull request. Only push commits to the specified branch." This prevents the cascade trigger.
3. **Idempotent sessions**: `idempotent=true` on session creation means re-runs with the same prompt don't create duplicate sessions.
4. **Attempt tracking**: Even if a cascade somehow starts, the per-alert attempt tracker (max 2) stops it after 2 fix attempts per alert.

**Residual risk**: Devin may ignore the "do not create a PR" instruction, as AI agents don't always follow negative constraints perfectly. Monitoring is recommended for the first few production runs. A future improvement could add a branch name pattern filter to the workflow trigger (e.g., skip runs on branches matching `devin/security-fixes-*`).

### Edge Case 8: Devin API Downtime — Graceful Degradation

**Problem**: If the Devin API is unreachable (outage, invalid key, rate limits), the workflow must not silently fail, and critically, must not block code from being pushed to main. Companies relying on this tool should never have their development pipeline blocked by an external AI service being down.

**Design principle**: **CodeQL is the gate, our workflow is the fixer.**

| Layer | Role | Blocks PR? | If down? |
|-------|------|-----------|----------|
| **CodeQL** | The gate — detects vulnerabilities, blocks merging | **Yes** (required status check) | PR can't be analyzed — branch protection requires it |
| **Devin Security Review** | The fixer — auto-fixes what CodeQL finds | **No** (advisory only) | Alerts still reported, developer fixes manually |

**Can we rely on CodeQL to block PRs with unfixed vulnerabilities?** Yes — CodeQL's "code scanning" creates check runs that can be configured as **required status checks** on the branch protection rule for `main`. If CodeQL finds alerts matching a severity threshold (configurable), it marks the check as failed, which blocks the PR from merging. This is GitHub's built-in mechanism and is the industry-standard trust model.

**Trust inheritance**: Our workflow inherits its security guarantee from CodeQL. We never need to block a PR ourselves because CodeQL already does. This means our workflow is purely additive — it can only help (auto-fix), never hurt (block). The worst case when Devin is down is that the developer has to fix manually, which is exactly where they'd be without our tool.

**Implementation — Health Check + Graceful Degradation**:

1. **Step 0 (Health Check)**: At workflow start, before any processing:
   - Validate `GH_PAT` is set and can reach GitHub API (HTTP 200)
   - Validate `DEVIN_API_KEY` is set and Devin API is reachable
   - If GH_PAT fails: workflow exits with error (can't do anything without GitHub access)
   - If Devin API fails: set `devin_available=false`, continue in degraded mode

2. **Degraded mode behavior**:
   - Alert detection and classification: **still runs** (uses GitHub API only)
   - Attempt tracking and history: **still runs** (uses GitHub API only)
   - Devin session creation: **skipped** (conditional on `devin_available=true`)
   - PR comment posting: **still runs** with degraded mode banner:
     > **DEGRADED MODE** — Devin API is currently unavailable. Alerts are listed below but cannot be auto-fixed.
     > **Your code is still protected.** CodeQL's required status check blocks merging of PRs with unresolved security alerts.

3. **Recovery**: When Devin comes back online, the next PR push triggers the workflow again. The attempt tracker picks up where it left off — no duplicate sessions, no lost state.

**Key guarantee**: The workflow **never blocks the PR**. It exits with success in both normal and degraded modes. Only CodeQL (as a required status check) can block merging.

**Failure modes**:

| Scenario | What happens | Developer impact |
|----------|-------------|------------------|
| Devin API down | Degraded mode: alerts reported, no auto-fix | Must fix manually; CodeQL still blocks vulnerable merges |
| Devin API slow (429) | Exponential backoff, retry once | Delayed fix, but still works |
| GitHub API down | Workflow can't run at all | No alerts, no fixes — but also no merges (GitHub is down) |
| Invalid DEVIN_API_KEY | Degraded mode (same as down) | Reconfigure secret, re-run |
| Both APIs healthy | Full automation | Review Devin's fix commits |

### Edge Case 9: CodeQL Race Condition — `workflow_run` Trigger

**Problem**: When both CodeQL and the Devin Security Review workflow trigger on `pull_request`, they start simultaneously. Our workflow polls for CodeQL completion (Step 2), but this is inefficient — it wastes runner minutes on polling loops and risks timeout if CodeQL takes longer than 20 minutes.

**Root cause**: GitHub Actions has no native "run this workflow after that one" for the same event trigger. Both workflows receive the `pull_request` event at the same time and start independently.

**Solution**: Use the `workflow_run` trigger instead of (or in addition to) `pull_request`.

```yaml
on:
  workflow_run:
    workflows: ["CodeQL"]   # Only fires after THIS specific workflow
    types: [completed]      # Only when CodeQL finishes (success or failure)
```

**Why `workflow_run` is the right choice**:

| Approach | Race condition? | Runner waste | Complexity |
|----------|----------------|-------------|------------|
| `pull_request` + polling (old) | Mitigated (polling) | High (30s polls for up to 20 min) | Low |
| `workflow_run` (new) | **Eliminated** | **Zero** (only runs after CodeQL) | Medium (PR context resolution) |
| `needs:` job dependency | Not applicable | N/A | N/A — only works within same workflow |

**Key property**: `workflow_run` is workflow-specific. Specifying `workflows: ["CodeQL"]` means ONLY the CodeQL workflow's completion triggers us. Other workflows (CI, build, linting) have no effect. This is not a generic "run after any workflow" trigger.

**Trade-off — PR context resolution**: `workflow_run` runs in the context of the default branch, not the PR branch. This means `github.event.pull_request` is not available. We resolve PR context via:

1. `github.event.workflow_run.pull_requests[0].number` — GitHub populates this array for same-repo PRs
2. Fallback: Search GitHub API by branch name (`GET /repos/{owner}/{repo}/pulls?head={branch}`)
3. If neither resolves a PR: skip the run (CodeQL ran on a push to main, not a PR)

**Implementation — Step 0a (Resolve PR Context)**:

The workflow normalizes PR context at the start regardless of trigger type:

| Trigger | PR number source | Head SHA source |
|---------|-----------------|-----------------|
| `workflow_run` | `workflow_run.pull_requests[0]` or API search | `workflow_run.head_sha` |
| `pull_request` | `event.pull_request.number` | `event.pull_request.head.sha` |
| `workflow_dispatch` | Manual input `pr_number` | API lookup from PR data |

All downstream steps use the normalized `steps.pr-context.outputs.*` values, making them trigger-agnostic.

**Guard clause**: The workflow only runs on `workflow_run` when:
- CodeQL completed **successfully** (`conclusion == 'success'`)
- CodeQL was triggered by a **pull request** (`event == 'pull_request'`)

This prevents running on CodeQL pushes to main or failed CodeQL runs.

**Important prerequisite**: This design means our workflow **depends on CodeQL running**. If CodeQL is not configured or is disabled on the repository, our workflow will never trigger via `workflow_run`. See the [Installation Guide](INSTALL.md) for the prerequisite warning. The `pull_request` trigger is kept as a fallback for development/testing before the workflow is merged to main.

**Polling fallback**: When triggered by `pull_request` (fallback), the old polling logic (Step 2) still runs to wait for CodeQL. When triggered by `workflow_run`, Step 2 is skipped entirely since CodeQL is already complete.

### Edge Case 10: Duplicate Fix Sessions from Concurrent / Scheduled Runs

**Problem**: If the workflow runs on a schedule (e.g., cron every 5 minutes) or multiple `workflow_run` events fire in quick succession, several workflow runs may see the same unfixed alerts simultaneously. Each run dispatches a Devin session for the same alert, wasting resources and potentially creating conflicting fix commits.

**Why existing mitigations are insufficient**:

| Existing mitigation | What it prevents | What it doesn't prevent |
|---------------------|-----------------|------------------------|
| `idempotent=true` on Devin sessions | Duplicate sessions with identical prompts | Sessions with slightly different prompts (different timestamps, run IDs) |
| Attempt tracking (`<!-- attempts:... -->`) | Re-dispatching after max attempts | Two runs reading the same attempt count before either updates it |
| Devin-commit detection | Re-processing after a fix commit | Two runs starting before any fix commit exists |

The core issue is a **TOCTOU race** (time-of-check to time-of-use): Run A reads "0 attempts" → Run B reads "0 attempts" → both dispatch sessions → both increment to "1 attempt".

**Proposed solution — Alert Claiming with TTL**:

Extend the hidden PR comment markers with a **claim** system:

```html
<!-- claimed:py/sql-injection:app/server.py:18=run_22028000619:1739581732 -->
```

Format: `alert_key = workflow_run_id : unix_timestamp_of_claim`

**Claim lifecycle**:

```
1. Workflow reads PR comment, parses claimed: markers
2. For each actionable alert:
   a. If unclaimed → write claimed: marker with run_id + timestamp → dispatch Devin session
   b. If claimed AND (now - claim_timestamp) < TTL → skip (another run is handling it)
   c. If claimed AND (now - claim_timestamp) >= TTL → claim is stale, overwrite → dispatch
3. After Devin completes (or on next run):
   a. If alert is fixed → remove claimed: marker, update attempts:
   b. If alert still exists → increment attempts, remove claimed:
```

**TTL (time-to-live)**: The critical design parameter.

| TTL value | Trade-off |
|-----------|-----------|
| Too short (5 min) | Multiple runs fight over the same alert; Devin may not have finished yet |
| Too long (2 hours) | Stale claims from crashed runs block fixes for hours |
| **30 minutes (recommended)** | Devin sessions typically take 5-20 min; 30 min gives buffer for retries |

TTL should be configurable via workflow input (default: 30 minutes).

**Why PR comment markers (not a database or GitHub Actions cache)?**:

| State store | Pros | Cons |
|-------------|------|------|
| **PR comment markers** (chosen) | Zero infrastructure; visible in DEBUG mode; atomic via GitHub API; already used for attempts | Size limit on comment body (~64KB); GitHub API serialization is eventual, not strict |
| GitHub Actions cache | Fast; built-in | No cross-workflow visibility; expires after 7 days; cache key conflicts |
| External database | Strict locking; unlimited size | Requires infrastructure; another dependency that can go down |
| GitHub commit status / check annotations | Visible in UI | Not designed for structured data; hard to parse |

**Concurrency edge case**: Two runs may PATCH the comment nearly simultaneously. GitHub's API serializes writes, but both runs may have read the old state. The `idempotent=true` flag on Devin sessions provides a safety net — even if two sessions are dispatched for the same alert, Devin's idempotency key prevents duplicate work if the prompts match.

**Implementation status**: DESIGNED, not yet implemented. The current attempt-tracking system handles the common case (sequential runs). The claiming system is needed for high-frequency scheduled runs (cron < 30 min interval).

**Future enhancement — Session polling**: If we add a step that polls Devin session status after creation, we can:
1. Remove the claim when the session finishes (success or failure)
2. Update the PR comment with actual fix results (not just "Devin is working on it")
3. Immediately mark alerts as unfixable if Devin reports failure

This would make the claim TTL less critical, since claims are actively managed rather than passively expired.

### Edge Case 11: Session Creation Failure — False-Green Check and Cascading Failures

**Problem**: The workflow exits with status 0 (green check) even when Devin session creation fails completely. A developer sees "Devin Security Review: Successful" alongside CodeQL's red check and assumes the security issue is being handled. In reality, no session was created and nobody is fixing anything.

**Observed in production**: PR #3 run on 2026-02-15 — Devin API returned HTTP 429 ("concurrent session limit of 5 exceeded"), retry after 60s also returned 429. Workflow posted a PR comment but no session link. Check showed green.

**Sub-cases and enterprise impact**:

#### EC11a: Total session failure (rate limit / API error)

| Aspect | Detail |
|--------|--------|
| **Trigger** | HTTP 429 (rate limit), 500 (server error), 503 (maintenance), network timeout |
| **Behavior** | Workflow detects alerts, fails to create any session, posts comment saying "Devin is fixing" (misleading), exits green |
| **Developer perception** | "Security is handled" — false sense of security |
| **Enterprise risk** | HIGH — vulnerable code merges if CodeQL is not a required check; even if CodeQL blocks, developer delays manual fix because they think Devin is working on it |
| **Cascading effect** | Next cron run hits same rate limit → infinite retry burn with zero progress |

#### EC11b: Partial session creation

| Aspect | Detail |
|--------|--------|
| **Trigger** | 5 alerts need sessions. Sessions 1-3 succeed, session 4 hits rate limit |
| **Behavior** | Some alerts dispatched, others silently dropped. Comment lists all alerts but only some have sessions |
| **Developer perception** | Sees partial fixes come in, waits for "the rest" indefinitely |
| **Enterprise risk** | MEDIUM — some alerts fixed, some silently abandoned. Hard to detect which ones were missed |
| **Cascading effect** | Next run sees remaining unfixed alerts, may create duplicate sessions for already-dispatched ones (no claiming system yet) |

#### EC11c: Session created but Devin fails internally

| Aspect | Detail |
|--------|--------|
| **Trigger** | Session returns 200, but Devin hits internal error (bad repo access, malformed prompt, snapshot failure) |
| **Behavior** | Session exists but status is "errored" or "blocked" with no commits pushed |
| **Developer perception** | Clicks session link, sees Devin errored out. At least there's visibility |
| **Enterprise risk** | MEDIUM — at least the failure is discoverable via the session link |
| **Cascading effect** | Alert stays open, next run increments attempt count, eventually marked unfixable after 2 attempts |

#### EC11d: Infinite retry burn from persistent rate limiting

| Aspect | Detail |
|--------|--------|
| **Trigger** | Enterprise with many repos, all running cron-triggered workflows. Global session limit reached |
| **Behavior** | Every 5 minutes, every repo's workflow tries to create sessions, gets 429, retries, fails, exits green |
| **Developer perception** | Doesn't notice — checks are green, CI logs fill up silently |
| **Enterprise risk** | LOW-MEDIUM — wastes CI minutes, fills logs, masks real issues. At scale (100+ repos), significant cost |
| **Cascading effect** | When rate limit clears, all workflows fire simultaneously → thundering herd → immediately rate limited again |

#### EC11e: Stale "in progress" perception

| Aspect | Detail |
|--------|--------|
| **Trigger** | Session created successfully but Devin takes 45+ minutes (complex multi-file fix) |
| **Behavior** | PR comment says "Devin is fixing" for extended period. Cron runs 9 more times, each seeing unfixed alerts |
| **Developer perception** | "It's been an hour, is Devin stuck?" — no way to tell from PR comment alone |
| **Enterprise risk** | MEDIUM — developer uncertainty, potential duplicate sessions without claiming |
| **Cascading effect** | Combines with EC10 — without claiming, massive session waste at scale |

**Proposed solutions**:

**Solution 1: Workflow exit code reflects actual outcome**

```
if (alerts_found > 0 AND sessions_created == 0 AND devin_available == true):
    exit 1  # FAIL — we found issues and couldn't dispatch a fix
elif (alerts_found > 0 AND sessions_created < alerts_dispatched):
    exit 1  # FAIL — partial dispatch, some alerts unhandled
else:
    exit 0  # OK — either no alerts, or all dispatched, or degraded mode (Devin down)
```

This makes the check red when it should be red. Combined with CodeQL's red check, the developer sees the full picture.

**Important nuance**: In degraded mode (Devin API entirely unreachable, detected at health check), the workflow should still exit 0 and clearly state "Devin unavailable — CodeQL is still protecting this PR." This avoids blocking CI when Devin is down for maintenance. The exit-1 should only happen when Devin is ostensibly available but session creation fails (e.g., rate limit, partial failure).

**Solution 2: Honest PR comment states**

Replace the current unconditional "Devin is fixing these issues" with state-aware messaging:

| State | PR Comment Message |
|-------|--------------------|
| All sessions created | "Devin is fixing these issues. Each fix will appear as a separate commit." |
| Partial creation | "**WARNING**: Devin dispatched fixes for {N}/{M} alerts. {K} alerts could not be dispatched (rate limited). These require manual attention or will be retried." |
| Total failure (rate limit) | "**FAILED**: Devin could not create any sessions (HTTP 429 — concurrent session limit). All {N} alerts require manual attention. Will retry on next run." |
| Total failure (API error) | "**FAILED**: Devin API returned an error (HTTP {code}). All {N} alerts require manual attention." |
| Degraded mode | "Devin is currently unavailable. {N} alerts listed below require manual review. CodeQL is still blocking this PR from merging." |

**Solution 3: Exponential backoff with jitter for cron scenarios**

Current: fixed 60s retry, 1 attempt.

Proposed:
```
wait = min(base_delay * 2^attempt + random(0, jitter), max_wait)
max_retries = 3
```

Additionally, store rate-limit state in the PR comment:
```html
<!-- rate_limited:1739581732:attempt_3 -->
```

Next cron run reads this marker. If `(now - timestamp) < cooldown_period`, skip session creation entirely and just report "waiting for rate limit cooldown."

**Solution 4: Session budget awareness**

Before creating sessions, check capacity:
```bash
ACTIVE=$(curl -s "https://api.devin.ai/v1/sessions?status=running" | jq '.total_count')
LIMIT=5  # from plan tier
AVAILABLE=$((LIMIT - ACTIVE))
```

If budget is tight, prioritize by severity:
1. Critical alerts → always dispatch
2. High alerts → dispatch if budget allows
3. Medium/Low → defer to next run

Document in PR comment: "Session budget: {AVAILABLE}/{LIMIT}. Dispatched {N} sessions for critical/high alerts. {K} medium-severity alerts deferred."

**Solution 5: Per-alert dispatch tracking**

Extend comment markers to track individual alert dispatch status:

```html
<!-- dispatched:py/sql-injection:app/server.py:18=session_abc123:1739581732 -->
<!-- failed_dispatch:py/xss:app/server.py:46=429:1739581732 -->
```

Next run only retries `failed_dispatch` alerts, not `dispatched` ones. This prevents duplicate sessions for partially-dispatched batches.

**Implementation priority** (for production readiness):

| Priority | Solution | Effort | Impact |
|----------|----------|--------|--------|
| P0 (must-have) | Solution 1 (exit code) + Solution 2 (honest comments) | Low | Eliminates false-green problem entirely |
| P1 (should-have) | Solution 5 (per-alert dispatch tracking) | Medium | Prevents partial-dispatch cascading |
| P2 (nice-to-have) | Solution 3 (backoff with jitter) | Low | Reduces rate-limit thundering herd |
| P3 (future) | Solution 4 (session budget) | Medium | Optimizes resource usage at enterprise scale |

**Implementation status**: DESIGNED, not yet implemented. P0 (exit code + honest comments) should be implemented before any production deployment.

### Edge Case 12: Busy Devin — State Preservation, Deferred Alerts, and Zombie Detection

**Problem**: When Devin is at capacity (all concurrent session slots occupied), the workflow cannot create new sessions. Alerts are discovered but cannot be dispatched. If the workflow simply exits, the next run rediscovers the same alerts and hits the same capacity wall — or worse, capacity frees up and the next run duplicates work that a previous run already queued mentally but never recorded.

**Observed in production**: PR #3 testing on 2026-02-15. The Devin API returned HTTP 429 ("concurrent session limit of 5 exceeded"). Investigation revealed 5 active sessions from previous test runs (Run 2 created 8 sessions; 5 were still in running/blocked state when the new workflow run attempted to create more). This is expected behavior — Devin sessions persist until they finish or are manually stopped — but the workflow had no awareness of existing session load.

**Why 5 concurrent sessions existed (investigation)**:

The 5 sessions were NOT from the current test run. They accumulated from multiple previous runs:
- **Run 2** (pre-rewrite testing): Created 8 sessions for 10 alerts. 7 finished, but sessions in "blocked" state (Devin finished work, waiting for human input) still count toward the concurrent limit.
- **Session carryover**: Devin sessions don't auto-terminate. A session in "blocked" or "running" state occupies a slot until explicitly stopped or until Devin's internal timeout (which can be hours).
- **No cleanup step**: Our workflow creates sessions but never cleans them up. Over multiple test runs, sessions accumulate.

This is the root cause: **session lifecycle is unbounded**. The workflow is a session producer with no corresponding consumer/cleanup.

**The core tension — EC10 vs EC12**:

EC10 (Alert Claiming with TTL) and EC12 (State Preservation) address related but distinct problems:

| Aspect | EC10 (Claiming) | EC12 (State Preservation) |
|--------|-----------------|--------------------------|
| **Problem** | Two runs see same alert, both dispatch | Run sees alert, can't dispatch (at capacity), state lost |
| **When it matters** | Devin has capacity (sessions can be created) | Devin is at capacity (sessions cannot be created) |
| **Goal** | Prevent duplicate sessions | Ensure alerts aren't forgotten when dispatch fails |
| **Mechanism** | Lock (claim marker with TTL) | Queue (deferred marker with retry scheduling) |
| **TTL semantics** | "Someone is working on this, don't touch for 30 min" | "We tried and failed, retry after cooldown" |

These two systems must coexist without conflict. The key insight: **they operate on different alert states**.

**Alert state machine** (unified model across EC10, EC11, EC12):

```
                    ┌─────────────────────────────────────────────┐
                    │                                             │
                    ▼                                             │
┌──────────┐   ┌────────┐   ┌───────────┐   ┌─────────┐   ┌─────────┐
│ DETECTED │──▶│DISPATCH│──▶│  CLAIMED   │──▶│  FIXED  │   │UNFIXABLE│
│          │   │ATTEMPT │   │(in-flight) │   │         │   │         │
└──────────┘   └────────┘   └───────────┘   └─────────┘   └─────────┘
                    │              │                             ▲
                    │              │ TTL expired                 │
                    │              │ (EC10)                      │
                    │              ▼                             │
                    │        ┌───────────┐                      │
                    │        │  ZOMBIE   │──────────────────────▶│
                    │        │ (stale)   │   (after max retries) │
                    │        └───────────┘                       │
                    │              │                             │
                    │              │ Reclaimed by next run       │
                    │              ▼                             │
                    │        ┌───────────┐                      │
                    │        │  CLAIMED  │ (new run takes over)  │
                    │        └───────────┘                       │
                    │
                    │ Dispatch failed (429/500)
                    │ (EC11 + EC12)
                    ▼
              ┌───────────┐
              │ DEFERRED  │──▶ (next run picks up)
              │(queued)   │
              └───────────┘
```

**State definitions and marker formats**:

| State | Marker Format | Meaning | Who transitions out |
|-------|---------------|---------|---------------------|
| DETECTED | (no marker — alert exists in CodeQL) | Alert found, not yet processed | Current run |
| CLAIMED | `<!-- claimed:ALERT_KEY=RUN_ID:TIMESTAMP -->` | Session created, Devin is working on it | TTL expiry or fix confirmation |
| DEFERRED | `<!-- deferred:ALERT_KEY=RUN_ID:TIMESTAMP:REASON -->` | Dispatch attempted but failed; queued for next run | Next run with available capacity |
| ZOMBIE | (claimed marker with expired TTL + no fix commits) | Session was created but appears stuck/failed | Next run reclaims it |
| FIXED | (alert disappears from CodeQL results) | CodeQL no longer reports it | Terminal state |
| UNFIXABLE | `<!-- unfixable:ALERT_KEY -->` | Max attempts reached, needs human review | Terminal state (human action) |

**How DEFERRED differs from CLAIMED (preventing EC10/EC12 collision)**:

The critical design decision: DEFERRED and CLAIMED are **distinct states with distinct markers**. A run checking for claims will NOT confuse a deferred alert with a claimed one:

- `<!-- claimed:... -->` → "Don't touch this, someone is actively fixing it"
- `<!-- deferred:... -->` → "Nobody could fix this last time, please try again"

A new run seeing a `deferred:` marker should **immediately try to dispatch** (it's explicitly queued for pickup). A new run seeing a `claimed:` marker should **respect the TTL** and skip unless expired.

**Deferred alert handling (the queue)**:

When dispatch fails (HTTP 429, 500, etc.), instead of silently dropping the alert:

```
1. Write a DEFERRED marker:
   <!-- deferred:py/sql-injection:app/server.py:18=run_22028000619:1739581732:429 -->
   Format: alert_key = run_id : timestamp : http_status_code

2. PR comment honestly states:
   "Alert py/sql-injection deferred — Devin at capacity (HTTP 429). Will retry on next run."

3. Next workflow run:
   a. Reads all deferred markers
   b. Checks if Devin has capacity (EC11 Solution 4: session budget check)
   c. If capacity available: dispatch session, replace deferred→claimed
   d. If still at capacity: update deferred timestamp, increment retry count
   e. If retry count > MAX_DEFERRED_RETRIES (default: 6 = 30 min at 5-min cron):
      escalate to PR comment warning "Alert stuck in queue for 30+ minutes"
```

**Zombie detection (stale claims that should be recycled)**:

A "zombie" is a claimed alert where the session appears to have failed silently:

```
Zombie detection criteria (ALL must be true):
1. claimed: marker exists with timestamp older than CLAIM_TTL (30 min)
2. Alert still exists in CodeQL results (not fixed)
3. No fix commits matching the alert's rule_id since the claim timestamp
4. (Optional) Session status check: GET /v1/sessions/{id} returns "errored" or "stopped"
```

**Why criterion #3 matters**: Without checking for fix commits, we might reclaim an alert that Devin already fixed but CodeQL hasn't re-scanned yet. The commit check provides a grace period — if Devin pushed a `fix: [rule_id]...` commit, the alert is likely fixed and we just need to wait for the next CodeQL run to confirm.

**Zombie resolution**:

```
if is_zombie(alert):
    if alert.attempt_count >= MAX_ATTEMPTS:
        transition to UNFIXABLE
        "Alert zombie detected — Devin session appears stuck after {N} attempts. Marked as unfixable."
    else:
        transition to DETECTED (clear claim, allow re-dispatch)
        increment attempt_count
        "Alert zombie detected — reclaiming for retry (attempt {N+1}/{MAX})."
```

**Session cleanup (addressing root cause)**:

The 5-session pileup reveals a deeper issue: our workflow never cleans up finished sessions. Proposed solutions:

| Approach | Mechanism | Pros | Cons |
|----------|-----------|------|------|
| **Pre-dispatch cleanup** | Before creating sessions, poll existing sessions. Stop any in "blocked" state older than 1 hour. | Frees slots proactively | Requires session list API; may stop sessions user wants to keep |
| **Post-dispatch polling** | After creating session, poll every 2 min for 10 min. If session finishes, update PR comment. | Provides completion feedback | Extends workflow run time; GitHub Actions has 6-hour limit |
| **Deferred cleanup job** | Separate scheduled workflow that runs hourly, stops all "blocked" sessions older than 2 hours | Decoupled; doesn't slow main workflow | Another workflow to maintain; another thing that can break |
| **Session TTL in Devin prompt** | Add to Devin prompt: "If you cannot fix the issue within 20 minutes, stop and report failure" | Simple; no infrastructure | Devin may not honor time-based instructions reliably |

**Recommended approach**: **Pre-dispatch cleanup** for immediate wins, with **deferred cleanup job** for production. The main workflow should be lightweight (fire-and-forget), while a separate cleanup job handles session hygiene.

**Unified marker format (combining EC10 + EC11 + EC12)**:

All state is stored in a single hidden block in the PR comment:

```html
<!-- devin-security-state
claimed:py/sql-injection:app/server.py:18=run_123:1739581732:session_abc
claimed:py/xss:app/server.py:46=run_123:1739581732:session_def
deferred:py/command-injection:app/server.py:25=run_123:1739581800:429:retry_1
deferred:py/flask-debug:app/server.py:51=run_123:1739581800:429:retry_1
unfixable:py/url-redirection:app/server.py:31
rate_limited:1739581800:cooldown_300
-->
```

This single block replaces multiple scattered markers. Benefits:
- **Atomic read-modify-write**: One block to parse, one block to update
- **No marker collision**: All states are in one namespace with distinct prefixes
- **Visible in DEBUG mode**: The entire state machine is inspectable
- **Self-documenting**: Each line has a clear prefix indicating the state

**Parsing logic** (pseudocode for the workflow):

```python
def parse_state_block(comment_body):
    match = re.search(r'<!-- devin-security-state\n(.*?)\n-->', comment_body, re.DOTALL)
    if not match:
        return empty_state()
    
    state = {}
    for line in match.group(1).strip().split('\n'):
        prefix, rest = line.split(':', 1)
        if prefix == 'claimed':
            alert_key, meta = rest.rsplit('=', 1)
            run_id, timestamp, session_id = meta.split(':')
            state[alert_key] = ClaimedAlert(run_id, int(timestamp), session_id)
        elif prefix == 'deferred':
            alert_key, meta = rest.rsplit('=', 1)
            run_id, timestamp, http_code, retry_info = meta.split(':')
            retry_count = int(retry_info.replace('retry_', ''))
            state[alert_key] = DeferredAlert(run_id, int(timestamp), http_code, retry_count)
        elif prefix == 'unfixable':
            state[rest] = UnfixableAlert()
        elif prefix == 'rate_limited':
            timestamp, cooldown = rest.split(':')
            state['_rate_limit'] = RateLimit(int(timestamp), int(cooldown.replace('cooldown_', '')))
    return state
```

**Decision flowchart for each alert** (what the workflow does per alert):

```
For each CodeQL alert:
  1. Is it in UNFIXABLE state? → SKIP (already given up)
  2. Is it in CLAIMED state?
     a. Is claim TTL expired? → Mark as ZOMBIE, go to step 4
     b. Is claim TTL valid? → SKIP (someone is working on it)
  3. Is it in DEFERRED state?
     a. Is retry count > MAX_DEFERRED_RETRIES? → ESCALATE (warn in comment)
     b. Otherwise → try to dispatch (go to step 5)
  4. Is it a ZOMBIE?
     a. Are there fix commits since claim? → SKIP (likely fixed, wait for CodeQL rescan)
     b. attempt_count >= MAX_ATTEMPTS? → transition to UNFIXABLE
     c. Otherwise → clear claim, treat as DETECTED
  5. DISPATCH attempt:
     a. Check session budget (EC11 Solution 4)
     b. If capacity available → create session → transition to CLAIMED
     c. If at capacity → transition to DEFERRED with reason code
```

**How this prevents conflicts between EC10 and EC12**:

| Scenario | EC10 alone | EC12 alone | EC10 + EC12 unified |
|----------|-----------|-----------|---------------------|
| Two runs, Devin has capacity | Both dispatch → duplicate | N/A | First claims, second skips (EC10) |
| One run, Devin at capacity | Claim written but no session | Alert lost | Alert marked DEFERRED, next run picks up (EC12) |
| Claimed alert, session stuck | Claim expires after TTL | N/A | Zombie detected, reclaimed or marked unfixable (EC10 TTL + EC12 zombie) |
| Deferred alert, capacity returns | N/A | Alert rediscovered | Deferred marker triggers immediate dispatch (EC12) |
| Deferred alert, still at capacity | N/A | Alert rediscovered, fails again | Retry count incremented, escalation after threshold (EC12) |

**Configuration parameters**:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `CLAIM_TTL` | 1800 (30 min) | How long a claim is valid before considered stale |
| `MAX_ATTEMPTS` | 2 | Max fix attempts before marking unfixable |
| `MAX_DEFERRED_RETRIES` | 6 | Max times an alert can be deferred before escalation |
| `DEFERRED_ESCALATION_THRESHOLD` | 1800 (30 min) | Time in deferred state before warning |
| `SESSION_CLEANUP_AGE` | 3600 (1 hour) | Age of "blocked" sessions eligible for cleanup |
| `RATE_LIMIT_COOLDOWN` | 300 (5 min) | Minimum wait after rate limit before retrying |

**Implementation status**: DESIGNED, not yet implemented. This is the most complex edge case and should be implemented incrementally:
1. **Phase 1**: Unified state block format + DEFERRED state (replaces current scattered markers)
2. **Phase 2**: Zombie detection + automatic reclaiming
3. **Phase 3**: Pre-dispatch session cleanup
4. **Phase 4**: Deferred cleanup job (separate workflow)

### Edge Case 13: Stuck PR — Failed Dispatch with No Re-Trigger Mechanism

**Problem**: A PR contains vulnerable code. CodeQL detects it (red check). Our workflow runs but fails to create a Devin session (e.g., HTTP 429 rate limit). The workflow exits green (EC11's false-green problem). Now the PR is stuck in a dead state: CodeQL is red (correct), our workflow is green (misleading), and **nothing will cause our workflow to run again** because there's no new push to trigger CodeQL, which means no new `workflow_run` event for us.

**Observed in production**: PR #3 on 2026-02-15. Screenshot shows CodeQL failing with "8 new alerts including 8 critical severity security vulner..." while "Devin Security Review / security-review" shows green. The developer sees this and either (a) thinks Devin is handling it, or (b) is confused about why the green check didn't fix anything.

**Why this is different from EC11 and EC12**:

| Edge Case | Problem | Assumes |
|-----------|---------|---------|
| EC11 | Workflow exits green when it should exit red | A future run will eventually retry |
| EC12 | Alerts are deferred but state is preserved | A future run will pick them up |
| EC13 | **No future run will ever happen** | Nothing triggers a retry without external action |

EC11 and EC12 both assume there will be a "next run." EC13 is about the case where there is NO next run — the trigger chain is broken.

**The trigger chain and where it breaks**:

```
Developer pushes code
       │
       ▼
CodeQL runs (on push/PR event)
       │
       ▼
CodeQL completes
       │
       ▼
workflow_run fires (our workflow)
       │
       ▼
Our workflow tries to create Devin session
       │
       ▼ FAILS (429/500/timeout)
       │
       ▼
Workflow exits (green or red)
       │
       ▼
       ╳ DEAD END — no new push = no new CodeQL = no new workflow_run
```

The chain only restarts if:
1. **Developer pushes new code** → triggers CodeQL → triggers us (but developer may not push for days/weeks)
2. **Someone manually re-runs the workflow** → but if it showed green, nobody thinks to re-run it
3. **A cron schedule triggers a run** → but cron runs on default branch context, not PR context
4. **Someone manually triggers workflow_dispatch** → requires someone to know this is needed

**Sub-cases and developer experience**:

#### EC13a: Developer sees green check, trusts it, waits forever

| Aspect | Detail |
|--------|--------|
| **Scenario** | Developer pushes vulnerable code. CodeQL red, our workflow green (false positive from EC11). Developer thinks "Devin is on it." |
| **What happens** | Nothing. No session was created. No fix will come. CodeQL blocks the merge, so the PR sits. |
| **Developer action** | Waits days. Eventually asks "why hasn't Devin fixed this?" |
| **Enterprise impact** | HIGH — developer productivity lost, trust in automation eroded |
| **Root cause** | No retry mechanism after workflow completes |

#### EC13b: Developer pushes unrelated change, accidentally triggers retry

| Aspect | Detail |
|--------|--------|
| **Scenario** | Days later, developer pushes an unrelated code change to the same PR branch. |
| **What happens** | CodeQL re-runs, finds the same alerts (plus possibly new ones). Our workflow triggers again. If Devin now has capacity, it dispatches sessions and fixes the alerts. |
| **Developer action** | Unintentional fix — developer doesn't realize the security fix was triggered by their unrelated push. |
| **Enterprise impact** | LOW — it works, but only by accident. Unreliable for critical security fixes. |

#### EC13c: PR abandoned due to stuck state

| Aspect | Detail |
|--------|--------|
| **Scenario** | Developer can't merge (CodeQL blocks), doesn't understand why Devin isn't fixing, gives up on the PR. |
| **What happens** | PR sits open indefinitely. Vulnerable code stays in the branch. If someone else merges a different PR touching the same files, conflicts arise. |
| **Developer action** | Opens a new PR, manually fixes the vulnerability, or abandons the feature. |
| **Enterprise impact** | MEDIUM — feature velocity lost, developer frustration. If developer manually fixes, the automation provided zero value. |

#### EC13d: CodeQL alerts on PR are not the same as alerts on main

| Aspect | Detail |
|--------|--------|
| **Scenario** | User asks: "Would the CodeQL issues list show that issue we didn't fix?" |
| **Answer** | YES — CodeQL alerts from PR scans are scoped to the PR's merge ref. They persist in the GitHub Code Scanning API (`GET /code-scanning/alerts?ref=refs/pull/{N}/merge`) as long as the PR is open and the code hasn't changed. They do NOT automatically transfer to main's alert list until the PR is merged. |
| **Implication** | Our workflow CAN always re-read these alerts on a future run — the data is there. The problem is not data loss, it's **trigger loss**. |

#### EC13e: Can we pick up from failed PRs vs only from main?

| Aspect | Detail |
|--------|--------|
| **Scenario** | User asks: "Is our capacity to pick up where we left off only for issues already in a merged commit (on main), or can we pick up from failed PRs?" |
| **Answer** | We CAN pick up from failed PRs — CodeQL alerts on the PR merge ref remain available via API. The issue is triggering a re-run. If we add a cron-based sweep (Solution 3 below), it can query all open PRs with CodeQL alerts and retry failed dispatches. This works for both PR-scoped and main-scoped alerts. |

**Proposed solutions**:

**Solution 1: Fix EC11 first (honest exit code)**

The most critical fix: if our workflow fails to create a session, exit 1 (red check). This means:
- Developer sees TWO red checks (CodeQL + ours) instead of misleading green
- Developer knows something is wrong and can take action (re-run, investigate, fix manually)
- This doesn't solve the "no automatic retry" problem, but at least it doesn't LIE about the state

**Solution 2: Self-scheduling retry via `workflow_dispatch`**

When the workflow detects a dispatch failure, it schedules a retry by triggering itself:

```yaml
- name: Schedule retry on dispatch failure
  if: env.DISPATCH_FAILED == 'true'
  run: |
    sleep $((RANDOM % 300 + 300))  # 5-10 min jittered delay
    curl -X POST \
      -H "Authorization: token ${{ secrets.GH_PAT }}" \
      "https://api.github.com/repos/${{ github.repository }}/actions/workflows/devin-security-review.yml/dispatches" \
      -d '{"ref": "${{ github.ref }}", "inputs": {"pr_number": "${{ env.PR_NUMBER }}", "retry": "true"}}'
```

The workflow already supports `workflow_dispatch` with a `pr_number` input. This creates a self-healing loop:
- Dispatch fails → workflow schedules a retry in 5-10 min
- Retry runs → if Devin has capacity, dispatches session → done
- Retry fails again → schedules another retry (with backoff)
- Max retries cap prevents infinite self-scheduling (e.g., 6 retries = 30 min window)

**Pros**: Fully automatic, no cron needed, PR-specific.
**Cons**: Requires PAT with `workflow` scope (already have it). Could create runaway retries without a cap.

**Solution 3: Cron-based sweep of open PRs with unresolved alerts**

Add a scheduled workflow that runs every 15-30 minutes:

```yaml
on:
  schedule:
    - cron: '*/15 * * * *'  # every 15 min

jobs:
  sweep:
    runs-on: ubuntu-latest
    steps:
      - name: Find stuck PRs
        run: |
          # List open PRs
          PRS=$(curl -s -H "Authorization: token $GH_PAT" \
            "https://api.github.com/repos/$REPO/pulls?state=open" | jq '.[].number')
          
          for PR in $PRS; do
            # Check if PR has our comment with deferred/failed state
            COMMENT=$(curl -s -H "Authorization: token $GH_PAT" \
              "https://api.github.com/repos/$REPO/issues/$PR/comments" \
              | jq -r '.[] | select(.body | contains("devin-security-state")) | .body')
            
            if echo "$COMMENT" | grep -q "deferred:"; then
              # Found a stuck PR — trigger workflow_dispatch for it
              curl -X POST "...dispatches" -d '{"inputs": {"pr_number": "'$PR'"}}'
            fi
          done
```

**Pros**: Catches ALL stuck PRs, not just the current one. Works even if the original workflow never ran (e.g., Devin was down during the original CodeQL run).
**Cons**: Another workflow to maintain. Runs even when not needed (wasted minutes). May re-dispatch for PRs that are intentionally paused.

**Solution 4: GitHub Check Run annotation as trigger**

Instead of relying on `workflow_run`, register a GitHub Check Run in our workflow. If the check fails (dispatch failure), the developer sees a "Re-run" button in the GitHub UI. This turns the retry into a 1-click action instead of requiring a manual `workflow_dispatch`.

Additionally, the check annotation can include a message: "Devin session could not be created. Click 'Re-run' to retry."

**Pros**: Developer-initiated, visible, no automation overhead.
**Cons**: Requires manual action. Developer must know to look for the re-run button.

**Solution 5: Comment-based retry trigger (most creative)**

Add a `/devin retry` command in PR comments. A separate lightweight workflow watches for this comment pattern and triggers the security review workflow:

```yaml
on:
  issue_comment:
    types: [created]

jobs:
  retry:
    if: contains(github.event.comment.body, '/devin retry')
    steps:
      - name: Trigger security review
        run: |
          PR=${{ github.event.issue.number }}
          curl -X POST "...dispatches" -d '{"inputs": {"pr_number": "'$PR'"}}'
```

**Pros**: Developer can retry at will. No cron. Visible in PR conversation. Team members can trigger it.
**Cons**: Another workflow. Developer must know the command exists. Susceptible to abuse (rate limit: max 1 trigger per 5 min via marker check).

**Recommended implementation order**:

| Priority | Solution | Why |
|----------|----------|-----|
| P0 | Solution 1 (honest exit code) | Zero-cost fix. Stop lying about state. |
| P1 | Solution 2 (self-scheduling retry) | Automatic, PR-specific, self-healing. Solves the stuck PR problem entirely. |
| P2 | Solution 5 (`/devin retry` command) | Great DX. Developer has escape hatch. Low maintenance. |
| P3 | Solution 3 (cron sweep) | Catches edge cases that Solutions 1-2 miss (e.g., workflow never ran at all). |
| P4 | Solution 4 (Check Run re-run) | Nice to have but GitHub already has workflow re-run button. |

**The complete "stuck PR" recovery path** (with all solutions implemented):

```
1. Developer pushes vulnerable code
2. CodeQL detects alerts (red check)
3. Our workflow runs, hits rate limit → exits RED (Solution 1)
4. Workflow self-schedules a retry in 5-10 min (Solution 2)
5. Retry #1 runs → still at capacity → schedules retry #2
6. Retry #2 runs → Devin has capacity → session created → alert claimed
7. Devin fixes the issue → pushes commit → CodeQL re-runs → alerts resolved
8. If all retries exhausted: PR comment says "Automatic retry exhausted. 
   Use /devin retry to trigger manually or fix the issues by hand."
   (Solution 5 provides the escape hatch)
9. If developer does nothing for 30+ min: cron sweep detects stuck PR,
   triggers retry (Solution 3)
```

**What needs to happen for the issue on this PR to be fixed without manual nudging** (answering the user's direct question):

With current implementation: **Nothing will happen automatically.** The PR is stuck. Someone must either push new code (accidental retry) or manually re-run the workflow.

With proposed solutions: **Solution 2 (self-scheduling retry) fixes this entirely.** The workflow detects its own failure and schedules a retry. The retry runs in 5-10 minutes. If Devin is still busy, it retries again with backoff. After 6 retries (30 min), it gives up and the PR comment clearly states what happened and how to retry.

**Implementation status**: DESIGNED, not yet implemented. P0 (honest exit code from EC11) is a prerequisite. P1 (self-scheduling retry) is the key fix for this edge case.

---

## Secrets and Authentication

| Secret | Environment Variable | Purpose | API |
|--------|---------------------|---------|-----|
| GitHub PAT | `GH_PAT` | Read code scanning alerts, post PR comments, manage check runs | GitHub REST API |
| Devin API Key | `DEVIN_API_KEY` | Create and poll Devin sessions | Devin v1 API |

**Required GitHub PAT scopes:** `repo`, `workflow`, `security_events`

**Devin API key type:** Service User API key (`apk_` prefix) — works with v1 API on all plan tiers.

---

## Limitations and Future Work

### Current Limitations

- **Language coverage**: Currently configured for Python and Actions. Adding more languages requires updating the matrix in `codeql.yml`.
- **CodeQL only**: The pipeline is specific to CodeQL. Other SAST tools (Semgrep, Snyk Code) would require adapter logic.
- **Async only**: The workflow does not wait for Devin to finish — it fires sessions and exits. Monitoring session completion requires checking session URLs manually or building a callback webhook.
- **Single repo**: Designed for a single repository. Multi-repo orchestration would need a separate dispatcher.
- **No `playback_mode` in Devin API**: The v1 API has no parameter to prevent sessions from entering "blocked" (waiting for human) state. Sessions that complete work and go to "blocked" are normal — they've already pushed their commits. This is a cosmetic concern, not a functional one.
- **CodeQL CLI download overhead**: Each Devin session downloads the CodeQL CLI (~500MB) for local verification. This adds time to each session. Future optimization: use a Devin snapshot with CodeQL pre-installed.

### Solved Problems (from PR #3 testing)

| Problem | Status | Solution |
|---------|--------|----------|
| Comment flood (14 duplicate comments) | SOLVED | Edit existing comment via hidden marker instead of posting new ones |
| Infinite loop (41 workflow runs) | SOLVED | Attempt tracking (max 2) + Devin-commit detection + unfixable marking |
| No completion signal | SOLVED | "All alerts resolved" or "REQUIRES MANUAL REVIEW" status in comment |
| No diff visibility | SOLVED | Links to Commits tab, Files changed tab, Devin session |
| Resource waste (8 sessions for 6 alerts) | SOLVED | Idempotent flag, ACU limits, attempt tracking prevents duplicates |
| Unfixable alerts silently ignored | SOLVED | Prominent "REQUIRES MANUAL REVIEW" section + `devin:manual-review-needed` label |
| Merge commits cluttering history | SOLVED | `git pull --rebase` instruction in Devin prompt |
| Infinite PR creation from pre-existing alerts | MITIGATED | Deterministic branch names + explicit "do not create PR" prompt + idempotent sessions + attempt tracking |
| Devin API downtime blocking development | SOLVED | Health check + graceful degradation: workflow enters degraded mode, still reports alerts, CodeQL blocks merges independently |
| CodeQL race condition (workflow starts before CodeQL finishes) | SOLVED | `workflow_run` trigger fires only after CodeQL completes; polling fallback for `pull_request` trigger |

### Planned Improvements

- **Custom CodeQL query packs**: Support for organization-specific security rules
- **Fix approval workflow**: Optional human review gate before Devin pushes fix commits
- **Metrics dashboard**: Track fix rate, false positive rate, mean time to remediation
- **Multi-language expansion**: Add JavaScript/TypeScript, Java, Go, C/C++ to the CodeQL matrix
- **Semgrep integration**: Support Semgrep as an alternative/complementary SAST engine
- **Pre-built Devin snapshot**: Snapshot with CodeQL CLI pre-installed to reduce session startup time
- **Webhook callback**: Register a webhook so Devin can notify the workflow when it finishes, enabling a completion comment with actual fix details
