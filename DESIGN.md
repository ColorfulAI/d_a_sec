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

### Planned Improvements

- **Custom CodeQL query packs**: Support for organization-specific security rules
- **Fix approval workflow**: Optional human review gate before Devin pushes fix commits
- **Metrics dashboard**: Track fix rate, false positive rate, mean time to remediation
- **Multi-language expansion**: Add JavaScript/TypeScript, Java, Go, C/C++ to the CodeQL matrix
- **Semgrep integration**: Support Semgrep as an alternative/complementary SAST engine
- **Pre-built Devin snapshot**: Snapshot with CodeQL CLI pre-installed to reduce session startup time
- **Webhook callback**: Register a webhook so Devin can notify the workflow when it finishes, enabling a completion comment with actual fix details
