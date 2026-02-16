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
10. [Circuit Breaker and Internal Retry Design](#circuit-breaker-and-internal-retry-design)
11. [Design Decisions Log](#design-decisions-log)
12. [Secrets and Authentication](#secrets-and-authentication)
13. [Fortune 500 Production Edge Cases](#fortune-500-production-edge-cases)
14. [Split-Trigger Architecture: PR-Scoped vs Scheduled Batch](#split-trigger-architecture-pr-scoped-vs-scheduled-batch)
15. [Limitations and Future Work](#limitations-and-future-work)

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

## Circuit Breaker and Internal Retry Design

### Problem: The Idempotent Session Trap (BUG #2)

The original design used `idempotent: true` on Devin API session creation calls. This flag uses the prompt text as a deduplication key — if you send the exact same prompt twice, the API returns the existing session instead of creating a new one. The intent was to prevent duplicate sessions on workflow re-runs.

**The bug manifests in the circuit breaker flow:**

```
Run A — Push vulnerable code.
  CodeQL finds py/command-line-injection at task_runner.py:9.
  Workflow builds prompt with this alert, calls POST /v1/sessions
    with idempotent: true.
  Devin API creates Session X (new). Attempt counter → 1/2.

Session X executes — Devin clones repo, fixes vuln, pushes commit c5459f9.
  This push triggers a new workflow run.

Run B — CodeQL re-analyzes. Two scenarios:

  Scenario 1: Alert is FIXED.
    Alert disappears from open alerts. Workflow marks it fixed. ✓

  Scenario 2: Alert STILL EXISTS (fix didn't satisfy CodeQL).
    Workflow builds prompt again for this alert.
    The prompt is IDENTICAL to Run A's prompt (same alert details,
      same file, same line).
    Calls POST /v1/sessions with idempotent: true.
    Devin API sees same prompt → returns Session X (already completed).
    is_new_session: false. No new Devin work happens.
    Attempt counter → 2/2.

Run C — Workflow sees attempt count = 2/2 → marks alert unfixable.
  But Devin never got a SECOND CHANCE to try a different fix approach.
  The counter says 2/2 but only 1 real session ever ran.
```

**Root cause:** With `idempotent: true` and an identical prompt, the 2nd "attempt" is a no-op. The circuit breaker counter increments, but no real second attempt occurs.

### Solution: Internal CodeQL Verification Loop

Instead of relying on multiple workflow runs to retry, all retry logic happens **inside a single Devin session**:

```
Workflow Run — Creates 1 Devin session for the batch of alerts.

Inside the session, for each alert:
  1. Apply fix
  2. Run CodeQL CLI locally (same config as repo)
  3. Check if alert still appears in SARIF output
     → If resolved: commit the fix, move to next alert
     → If still present: revise fix, re-run CodeQL (attempt 2 of 2)
       → If resolved: commit, move on
       → If still present: SKIP this alert (do NOT commit broken fix)
  4. Report which alerts were fixed and which were skipped

Workflow marks skipped alerts as unfixable on the next run
  (alert still present in CodeQL → attempt counter at max → unfixable).
```

**Key properties:**
- Only 1 Devin session per batch of alerts (no excessive session creation)
- Devin gets 2 real fix attempts per alert with local CodeQL verification
- Broken fixes are never committed (skipped if CodeQL still flags them)
- The `idempotent` flag is removed — no longer needed since retries are internal
- The workflow-level circuit breaker still works: if an alert persists after the session completes, the next workflow run increments the attempt counter and eventually marks it unfixable

### Why Not Multiple Sessions?

| Approach | Sessions Created | Real Attempts | Latency | Cost |
|----------|-----------------|---------------|---------|------|
| `idempotent: true` (old) | 1 (reused) | 1 | 2+ workflow runs | Low but broken |
| Unique key per attempt | 2 separate | 2 | 2+ workflow runs | 2x session cost |
| **Internal retry (current)** | **1** | **2** | **1 workflow run** | **1x session cost** |

The internal retry approach is strictly better: fewer sessions, faster feedback, lower cost, and the verification happens immediately rather than waiting for another full CodeQL workflow cycle.

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

---

## Secrets and Authentication

| Secret | Environment Variable | Purpose | API |
|--------|---------------------|---------|-----|
| GitHub PAT | `GH_PAT` | Read code scanning alerts, post PR comments, manage check runs | GitHub REST API |
| Devin API Key | `DEVIN_API_KEY` | Create and poll Devin sessions | Devin v1 API |

**Required GitHub PAT scopes:** `repo`, `workflow`, `security_events`

**Devin API key type:** Service User API key (`apk_` prefix) — works with v1 API on all plan tiers.

---

## Fortune 500 Production Edge Cases

These edge cases were identified through systematic testing and code analysis. Each represents a real failure mode that can occur in enterprise environments with high PR volume and accumulated security debt.

### EC-1: Batch Isolation — Pre-existing Failures Must Not Fail PR Check

**Scenario**: A developer opens a PR on a codebase with 200 pre-existing CodeQL alerts on main. Their PR code is clean, but the pre-existing batch session fails (API error, timeout, etc.).

**Why this matters**: In enterprise environments, main branches accumulate hundreds of pre-existing alerts. A new PR author should not be blocked or stigmatized for tech debt they didn't create. If the workflow marks the PR check as "failed" because of pre-existing batch issues, developers lose trust and start ignoring security checks.

**Design rule**: The workflow exit code ONLY fails when:
1. New-in-PR session creation fails (`session_failed=true`)
2. Devin API is unavailable AND there are new-in-PR actionable alerts

Pre-existing batch failures are logged but never affect the PR's pass/fail status.

### EC-2: Banner and Label Misattribution

**Scenario**: A PR introduces 2 new alerts (both fixable by Devin) but the codebase has 5 pre-existing unfixable alerts on main. The PR comment shows "REQUIRES MANUAL REVIEW — 5 alerts could not be auto-fixed" and applies the `devin:manual-review-needed` label.

**Why this matters**: The PR author sees a scary banner and red label implying THEIR code has unfixable security issues. In reality, their code is fine — the unfixable alerts are inherited from main. This erodes trust and creates friction in the PR review process.

**Design rule**:
- The "REQUIRES MANUAL REVIEW" banner only appears for NEW-IN-PR unfixable alerts
- Pre-existing unfixable alerts get a softer "Note" callout that explicitly says "not introduced by this PR"
- The `devin:manual-review-needed` label is only applied when NEW-IN-PR alerts are unfixable
- Unfixable counts are split: `new_unfixable_count` and `pre_unfixable_count`

### EC-3: Comment Race Condition Under High PR Volume

**Scenario**: Developer pushes code → workflow run A starts. Devin pushes a fix → workflow run B starts. Both runs read the same PR comment, build their own updated version, and PATCH it. Run B's PATCH overwrites run A's attempt history.

**Why this matters**: Fortune 500 repos can have dozens of PRs per hour. Each Devin fix push triggers a re-run. If two runs overlap, the second PATCH silently overwrites the first's data, potentially resetting attempt counters or losing fixed-alert tracking.

**Current mitigation**: The `<!-- devin-security-review -->` marker ensures we always find the correct comment. Each run reads the latest state before writing. However, there is no lock/mutex — true concurrent PATCHes can still race.

**Future improvement**: Use GitHub's `If-Match` / ETag headers on PATCH requests to detect conflicts, or implement a simple retry-on-conflict loop.

### EC-4: Alert Explosion — Hundreds of Pre-existing Alerts

**Scenario**: A mature codebase has 500+ pre-existing CodeQL alerts. Developer opens a PR that adds 2 new alerts.

**Why this matters**: The workflow creates up to 20 sessions (15 alerts each = 300 max). The remaining 200+ alerts are silently dropped. The PR comment could become enormous (hundreds of table rows), potentially exceeding GitHub's 65536 character limit for comment bodies.

**Current mitigation**:
- Session cap: max 20 sessions per run (300 alerts)
- Severity prioritization: critical/high alerts processed first
- Per-alert status tables could grow very large

**Future improvement**: Paginate alert tables (show top 50, collapse the rest), add a "and N more" summary, implement cross-run continuity so subsequent runs pick up where the previous left off.

### EC-5: Concurrent PRs Fixing Same Pre-existing Alerts

**Scenario**: PR #10 and PR #11 are open simultaneously. Both detect the same 20 pre-existing alerts on main. Both create Devin sessions to fix them. Both sessions push to branch `devin/security-fixes-prN`.

**Why this matters**: Two Devin sessions fixing the same alert independently will produce conflicting commits. When the fix PRs try to merge to main, there will be merge conflicts.

**Current mitigation**: The fix branch name is deterministic per PR (`devin/security-fixes-pr{N}`), so different PRs use different branches. However, the fixes target the same code, so merging both to main will conflict.

**Future improvement**: Implement a global lock (GitHub issue comment or label) to prevent concurrent pre-existing fix sessions. Or use a single shared fix branch with conflict detection.

### EC-6: Stress Test — Mass PR Creation

**Scenario**: 100 PRs are opened simultaneously against a repo with pre-existing vulnerabilities.

**Why this matters**: This tests the system's behavior under load — API rate limits (both GitHub and Devin), concurrent workflow runs competing for resources, comment creation contention, and session exhaustion.

**Key concerns**:
- GitHub Actions concurrency limits (varies by plan)
- Devin API rate limits (429 responses)
- GitHub REST API rate limits (5000 req/hr for PATs)
- Each PR creates its own comment, sessions, and labels — no cross-PR interference expected
- But all PRs detect the same pre-existing alerts, creating redundant session work

**Actual stress test results (99 PRs, Feb 2026)**:
- 99/100 PRs created (1 failed due to transient git 500 error)
- 11 out of ~30 completed Devin Security Review runs **failed** — all due to Devin API HTTP 429 ("concurrent session limit of 5")
- The workflow's single-retry (60s wait) was insufficient: after 60s the concurrent sessions were still running, so the retry also got 429
- CodeQL runs: 100% success rate — no failures under load
- CI runs: 100% success rate — no failures under load
- No cross-PR contamination detected — each PR's comment was independent
- GitHub REST API rate limits were NOT exhausted (stayed under 5000 req/hr)
- GitHub Actions queued runs gracefully (242 queued at peak, processing ~20 at a time)

### EC-7: Devin API Rate Limiting — Insufficient Retry Logic (BUG #9)

**Scenario**: Multiple concurrent workflow runs each try to create a Devin session. The Devin API enforces a concurrent session limit (e.g., 5 sessions). The first 5 succeed; the rest get HTTP 429. The workflow retries once after 60s, but the original sessions are still running, so the retry also gets 429.

**Why this matters**: In a Fortune 500 environment, PR bursts are common (release branches, batch merges, CI/CD pipelines). If 20 PRs are opened in 5 minutes, only 5 will get Devin sessions — the other 15 will fail permanently with no further retry. The workflow marks these as "session creation failed" and fails the PR check, even though the failure is transient and due to capacity, not a real problem with the PR's code.

**How discovered**: Stress test with 99 PRs. 11 out of ~30 completed Devin Security Review runs failed, all with the same error: `HTTP 429 — "You exceeded your concurrent session limit of 5"`. The single 60s retry was insufficient because concurrent sessions from other PRs were still active.

**Design rule**: Rate limiting (429) is a transient failure. The workflow must implement exponential backoff with multiple retries (at least 3 attempts with increasing wait times: 60s, 120s, 240s) to give concurrent sessions time to complete before retrying. After all retries are exhausted, the workflow should mark the run as needing manual re-trigger rather than permanently failing.

**Fix applied**: Changed from single 60s retry to 3-attempt exponential backoff (60s → 120s → 240s). Total maximum wait: 420s (7 minutes). This gives concurrent Devin sessions time to complete before retrying.

---

## Split-Trigger Architecture: PR-Scoped vs Scheduled Batch

### The Problem: Single Workflow Doing Too Much

The current architecture uses a single workflow triggered by `pull_request` that handles BOTH:
1. **New-in-PR alerts** — vulnerabilities introduced by the PR's code changes
2. **Pre-existing alerts** — accumulated tech debt on `main` that happens to be visible on the PR's merge ref

This creates several production-critical problems:

#### Problem 1: PR Workflows Blocked by Batch Work

When a PR triggers the workflow, it creates Devin sessions for both new-in-PR and pre-existing alerts. If there are 100 pre-existing alerts, the workflow creates up to 20 sessions (15 alerts each). Each session creation takes time (API calls, rate limit backoff). The PR author's workflow run is now blocked for minutes handling tech debt they didn't create.

**Real scenario**: Developer pushes a 2-line fix. The workflow spends 7+ minutes creating and rate-limit-retrying sessions for 100 pre-existing alerts. The developer sees "workflow running" for 10 minutes for what should be a 30-second check.

#### Problem 2: Session Explosion Under Concurrent PRs

If 20 PRs are open simultaneously, EACH PR's workflow run tries to create sessions for the SAME pre-existing alerts. That's 20 × 20 = 400 session creation attempts for identical work. With a concurrent session limit of 5, this causes cascading 429 failures.

**Stress test evidence**: 99 PRs opened → 201 Devin Security Review runs → 83 failures (41%). Most failures were rate limits caused by redundant pre-existing session creation across PRs.

#### Problem 3: Redundant Work

PR #10 and PR #11 both detect the same 50 pre-existing alerts on main. Both create separate Devin sessions to fix them. Both sessions produce identical fixes targeting the same code on main. This is pure waste — double the sessions, double the cost, potential merge conflicts when both push to similar branches.

#### Problem 4: No Incremental Progress on Backlog

If a rate-limited workflow run fails to create a session for pre-existing alerts, those alerts are simply lost. There is no mechanism for the next run to "pick up where it left off." The backlog only gets retried when someone pushes new code to a PR — which may not happen for days or weeks.

### The Solution: Two Separate Workflows

```
┌─────────────────────────────────────────────────────────┐
│                    TRIGGER SPLIT                         │
│                                                         │
│  ┌───────────────────┐    ┌───────────────────────────┐ │
│  │  PR Workflow       │    │  Backlog Workflow          │ │
│  │  (per-PR trigger)  │    │  (scheduled trigger)       │ │
│  │                    │    │                            │ │
│  │  Trigger:          │    │  Trigger:                  │ │
│  │  - pull_request    │    │  - schedule (cron)         │ │
│  │  - workflow_run    │    │  - workflow_dispatch        │ │
│  │    (after CodeQL)  │    │    (manual backlog run)     │ │
│  │                    │    │                            │ │
│  │  Scope:            │    │  Scope:                    │ │
│  │  ONLY new-in-PR    │    │  ONLY pre-existing alerts  │ │
│  │  alerts             │    │  on main/default branch    │ │
│  │                    │    │                            │ │
│  │  Sessions:         │    │  Sessions:                 │ │
│  │  1 session max     │    │  Up to N sessions          │ │
│  │  (just this PR's   │    │  (batched, rate-limited,   │ │
│  │   new alerts)      │    │   picks up from cursor)    │ │
│  │                    │    │                            │ │
│  │  Output:           │    │  Output:                   │ │
│  │  PR comment with   │    │  Dedicated backlog PR      │ │
│  │  new-alert status  │    │  OR GitHub issue tracker   │ │
│  │                    │    │                            │ │
│  │  Exit code:        │    │  Exit code:                │ │
│  │  Fails ONLY if     │    │  Always succeeds (backlog  │ │
│  │  new-in-PR session │    │  is best-effort, never     │ │
│  │  fails             │    │  blocks anything)          │ │
│  └───────────────────┘    └───────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Workflow 1: PR Security Review (`devin-security-review.yml`)

**Trigger**: `pull_request` (synchronize/opened) + `workflow_run` (after CodeQL)

**Scope**: ONLY new-in-PR alerts. Pre-existing alerts are acknowledged in the PR comment (count + note) but NOT dispatched to Devin.

**Session budget**: 1 Devin session maximum. A PR should never need more than 1 session because new-in-PR alerts are typically a small set (the developer just introduced them).

**Exit code logic**:
- `exit 0` (pass) — if no new-in-PR alerts, or if all new-in-PR alerts were dispatched to Devin
- `exit 1` (fail) — ONLY if new-in-PR session creation failed (API error, rate limit exhaustion)
- Pre-existing alert counts are displayed but NEVER affect the exit code

**PR comment content**:
- New-in-PR alert table with status
- Devin session link for the new-in-PR fix
- A "Note" section: "N pre-existing alerts detected on main. These are handled separately by the scheduled backlog workflow."
- NO sessions created for pre-existing alerts

**Why this is better**:
- PR workflow completes in seconds (1 session creation, not 20)
- No rate limit contention between PRs (each PR uses at most 1 session slot)
- Developer's PR is never blocked by batch work
- 20 concurrent PRs = 20 session attempts (manageable), not 400

### Workflow 2: Backlog Security Sweep (`devin-security-backlog.yml`)

**Trigger**: `schedule` (cron, e.g., every 6 hours or nightly) + `workflow_dispatch` (manual)

**Scope**: ALL open CodeQL alerts on the default branch (`main`). Scans the full alert backlog, not tied to any specific PR.

**Output model**: **1 PR per batch**. Each batch of alerts gets its own branch (`devin/security-batch-{N}-{timestamp}`) and its own PR. This makes review easier — each PR is focused on a specific set of files/alerts and can be reviewed and merged independently.

**Exit code**: Always `0`. The backlog is best-effort. Failures are logged, and the cursor is updated so the next run retries failed alerts.

### Devin Session Lifecycle: Why 1 New Session Per Batch

The Devin API is designed around **1 session = 1 scoped task**. This is confirmed by the API's architecture:

- `POST /v1/sessions` — Creates a new session with a prompt. Each session gets its own isolated environment (fresh clone, tools, shell, browser).
- `POST /v1/sessions/{session_id}/message` — Sends a follow-up message to an **active** session. This is for mid-session guidance (e.g., "also fix the tests"), NOT for post-completion reuse. Once a session completes (`status=finished`), its environment is torn down.
- `idempotent` flag — Deduplication safety net (same prompt returns existing session). We removed this (see BUG #2 above) because it broke the retry loop.
- Devin's own "Start Batch Sessions" feature (Advanced Mode) creates **separate individual sessions** per task item — it does not pack multiple tasks into one session.

**Design rule**: Each batch of alerts = 1 new Devin session. We do NOT reuse completed sessions. The `send message` API is used only for the internal retry loop (Devin runs CodeQL inside the session, finds the fix didn't work, tries again — all within the same active session).

| Operation | API | When to Use |
|-----------|-----|-------------|
| Create new session | `POST /v1/sessions` | Every new batch of alerts |
| Send follow-up message | `POST /v1/sessions/{id}/message` | Internal retry (mid-session CodeQL re-check) |
| Check session status | `GET /v1/sessions/{id}` | Orchestrator polling for completion |
| Terminate stuck session | `DELETE /v1/sessions/{id}` | Session exceeded time budget |

**Cost control**: The `max_acu_limit` parameter caps compute per session. With playbooks, we standardize the prompt so each session is efficient. Smart batching (grouping related alerts) ensures each session does meaningful work rather than context-switching between unrelated files.

### Sub-Workflow Fan-Out Architecture

The backlog workflow uses a **two-tier architecture**: an orchestrator workflow dispatches independent child workflows, one per batch.

```
┌──────────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR (devin-security-backlog.yml)                       │
│  Trigger: schedule (cron) or workflow_dispatch (manual)          │
│                                                                  │
│  1. Fetch ALL open CodeQL alerts on main (paginated)             │
│  2. Read cursor → skip already-processed/unfixable alerts        │
│  3. Group remaining alerts into batches (15 per batch, by file)  │
│  4. For each batch: dispatch a child workflow                    │
│  5. Poll child workflow statuses (rolling window of 5 active)    │
│  6. As each child completes → create PR for that batch (stream)  │
│  7. Update cursor with results                                   │
│  8. Exit when all batches dispatched + all children completed    │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ Child 1  │ │ Child 2  │ │ Child 3  │ │ Child 4  │  ...      │
│  │ Batch 1  │ │ Batch 2  │ │ Batch 3  │ │ Batch 4  │           │
│  │ 15 alerts│ │ 15 alerts│ │ 15 alerts│ │ 12 alerts│           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│       │             │             │             │                │
│       ▼             ▼             ▼             ▼                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ Devin    │ │ Devin    │ │ Devin    │ │ Devin    │           │
│  │ Session  │ │ Session  │ │ Session  │ │ Session  │           │
│  │ (1 per   │ │ (1 per   │ │ (1 per   │ │ (1 per   │           │
│  │  batch)  │ │  batch)  │ │  batch)  │ │  batch)  │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│       │             │             │             │                │
│       ▼             ▼             ▼             ▼                │
│   PR #101       PR #102       PR #103       PR #104             │
│  (batch 1)     (batch 2)     (batch 3)     (batch 4)            │
└──────────────────────────────────────────────────────────────────┘
```

**Why sub-workflows instead of a single long-running job?**

| Concern | Single Job | Sub-Workflow Fan-Out |
|---------|-----------|---------------------|
| Timeout risk | 6-hour GitHub Actions limit; 500 alerts = ~70 min but 1000+ alerts could exceed | Each child has its own 6-hour limit; orchestrator is lightweight |
| Debuggability | One massive log file; hard to find "what happened to batch 3?" | Each batch is a separate workflow run with its own logs |
| Failure isolation | One batch failure can cascade to the whole run | Child 3 failing doesn't affect children 1, 2, 4 |
| GitHub Actions UI | Single run, hard to see per-batch status | Each child is visible as a separate run |
| Retry granularity | Must re-run entire orchestrator to retry one batch | Can re-dispatch just the failed child |

**How child dispatch works**: The orchestrator uses GitHub's `workflow_dispatch` event to trigger child workflows via the GitHub API:

```bash
curl -s -X POST \
  -H "Authorization: token $GH_PAT" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/$REPO/actions/workflows/devin-security-batch.yml/dispatches" \
  -d '{
    "ref": "main",
    "inputs": {
      "batch_id": "3",
      "alert_ids": "101,102,103,104,105",
      "branch_name": "devin/security-batch-3-1708041600"
    }
  }'
```

Each child workflow (`devin-security-batch.yml`) is a simple, single-purpose workflow:
1. Receive batch ID + alert IDs as inputs
2. Create 1 Devin session with those alerts
3. Wait for Devin to complete (poll session status)
4. Report results back (structured output or workflow artifacts)

### Orchestrator Slot Management (Rolling Window)

The Devin API enforces a concurrent session limit of 5. The orchestrator manages this as a **rolling window**: it never dispatches a child workflow if 5 children are already active.

```
100 alerts = 7 batches, 5 concurrent slots

Time ──────────────────────────────────────────────────────►

Slot 1: [  Batch 1  ]                    [  Batch 6  ]
Slot 2: [  Batch 2       ]               [  Batch 7  ]
Slot 3: [  Batch 3  ]         (idle — all batches dispatched)
Slot 4: [    Batch 4    ]
Slot 5: [  Batch 5  ]

         ◄── Wave 1 ──►  ◄─ backfill ─►  ◄── done ──►
         Fill all 5       As slots free,   All 7 batches
         slots            dispatch 6, 7    complete
```

**Orchestrator polling loop**:

```
active_children = {}
pending_batches = [batch_1, batch_2, ..., batch_7]

# Initial fill: dispatch up to 5
while len(active_children) < 5 and pending_batches:
    batch = pending_batches.pop(0)
    child_run_id = dispatch_child_workflow(batch)
    active_children[child_run_id] = batch

# Poll loop
while active_children:
    sleep(60)
    for run_id in list(active_children.keys()):
        status = check_workflow_run_status(run_id)
        if status == "completed":
            batch = active_children.pop(run_id)
            # STREAMING: create PR immediately for this batch
            create_pr_for_batch(batch)
            update_cursor(batch, status="fixed")
            # Backfill: dispatch next pending batch
            if pending_batches:
                next_batch = pending_batches.pop(0)
                next_run_id = dispatch_child_workflow(next_batch)
                active_children[next_run_id] = next_batch
        elif status == "failure":
            batch = active_children.pop(run_id)
            update_cursor(batch, status="failed")
            # Backfill freed slot
            if pending_batches:
                next_batch = pending_batches.pop(0)
                next_run_id = dispatch_child_workflow(next_batch)
                active_children[next_run_id] = next_batch
```

**Session reservation for PR workflows**: The orchestrator self-limits to 3 concurrent children (not 5), reserving 2 slots for PR workflows that may fire at any time. This is configurable:

```
Before dispatching a child:
  1. GET /v1/sessions?status=running → count ALL active Devin sessions
  2. If active >= 3: wait 120s and re-check (max 5 retries)
  3. If active < 3: dispatch child
  4. This reserves ~2 slots for PR workflows at all times
```

### Streaming PR Creation

Instead of waiting for all batches to complete before creating PRs, we **create each PR as soon as its batch's session finishes**. This provides faster developer feedback.

```
Timeline with streaming:

  t=0      Orchestrator starts, dispatches batches 1-5
  t=8min   Batch 1 session finishes → PR #101 created immediately
  t=10min  Batch 3 session finishes → PR #103 created immediately
  t=12min  Batch 5 session finishes → PR #105 created, batch 6 dispatched
  t=15min  Batch 2 session finishes → PR #102 created, batch 7 dispatched
  t=18min  Batch 4 session finishes → PR #104 created
  t=22min  Batch 6 session finishes → PR #106 created
  t=25min  Batch 7 session finishes → PR #107 created
  t=25min  All done. 7 PRs created over 25 minutes.

Timeline WITHOUT streaming (batch approach):

  t=0      Orchestrator starts, dispatches batches 1-5
  t=25min  All 7 batches complete
  t=26min  Create PRs #101-#107 (all at once)

  Developers see NOTHING for 25 minutes, then 7 PRs appear at once.
```

**Why streaming is better**:
- First PR available for review within ~8-10 minutes, not 25+
- Developers can start reviewing and merging batch 1 fixes while batches 5-7 are still being processed
- If the orchestrator crashes at t=15min, 4 PRs are already created (no work lost)
- Spreads the review load over time instead of dumping 7 PRs at once

**PR naming convention**: Each batch gets a descriptive branch and PR title:
- Branch: `devin/security-batch-{N}-{timestamp}`
- PR title: `fix(security): Batch {N} — {count} CodeQL alerts in {files}`
- PR body: Alert table, Devin session link, which rules were addressed

### Stateless Pickup via Cursor

The backlog workflow must be able to run multiple times and incrementally make progress without re-processing already-handled alerts. It uses a **cursor** stored as a GitHub issue comment:

```
┌──────────────────────────────────────────────────────┐
│  Backlog State (stored in GitHub issue #N)            │
│                                                       │
│  {                                                    │
│    "last_run": "2026-02-16T00:00:00Z",               │
│    "processed_alert_ids": [101, 102, 103, ...],      │
│    "in_progress_batches": [                          │
│      {"batch_id": 6, "run_id": 12345,               │
│       "alert_ids": [201,202,203],                    │
│       "dispatched_at": "2026-02-16T00:05:00Z"}      │
│    ],                                                 │
│    "unfixable_alert_ids": [104, 105],                │
│    "total_backlog": 200,                              │
│    "total_fixed": 150,                                │
│    "total_unfixable": 15                              │
│  }                                                    │
│                                                       │
│  Each run:                                            │
│  1. Read cursor → know where to start                │
│  2. Check in_progress batches → poll child status    │
│  3. Fetch all open alerts on main                    │
│  4. Filter out processed + unfixable                 │
│  5. Group remaining into batches                     │
│  6. Dispatch children (rolling window of 3-5)        │
│  7. Stream PRs as children complete                  │
│  8. Update cursor with results                       │
│  9. Exit when all batches done                       │
└──────────────────────────────────────────────────────┘
```

**Concurrency control**:
```yaml
concurrency:
  group: security-backlog-${{ github.repository }}
  cancel-in-progress: false
```
Only 1 orchestrator run at a time per repo. If a cron triggers while a previous run is still going, it queues (does NOT cancel the in-progress run, because that would lose work).

**Key property**: If the orchestrator crashes mid-run, no data is lost. Completed batches already have their PRs created (streaming). The cursor has the state from the last successful update. The next run re-checks in-progress children and retries as needed.

### Why Not Just Re-run Failed PR Workflows?

You could argue: "if a PR workflow fails due to rate limiting, just re-run it later." This doesn't work because:

1. **No automatic re-trigger**: GitHub Actions doesn't auto-retry failed workflow runs. Someone must manually click "Re-run" or push new code.
2. **PR workflows are PR-scoped**: They only run when someone pushes to a PR branch. If the developer's code is done, they won't push again.
3. **Backlog work is global**: Pre-existing alerts are the same across all PRs. Processing them per-PR is redundant. A single scheduled workflow handles the entire backlog efficiently.
4. **Rate limit fairness**: If 20 PRs are open, each PR workflow competing for sessions is unfair to all developers. A scheduled backlog workflow processes alerts on its own timeline without blocking anyone.

### Considerations and Worries

#### Worry: Will the backlog workflow ever "catch up" with a large alert backlog?

**Analysis**: With the sub-workflow fan-out, the math changes significantly. The orchestrator processes the ENTIRE backlog in a single run:
- 500 alerts = 34 batches (15 each)
- 5 concurrent slots, ~10 min per session
- 34 batches ÷ 5 slots = 7 waves × 10 min = ~70 minutes total
- Well within the 6-hour GitHub Actions limit

For truly massive backlogs (1000+ alerts):
- 67 batches ÷ 5 slots = 14 waves × 10 min = ~140 minutes
- Still within the 6-hour limit

**Safety valve**: If approaching the timeout (5.5 hours elapsed), the orchestrator saves the cursor and exits cleanly. The next cron run picks up from where it left off. But for most repos, one run handles the entire backlog.

#### Worry: What if new alerts accumulate faster than the backlog clears them?

**Analysis**: New alerts only appear when code is merged to main. The backlog workflow processes the entire backlog per run. If the team merges 10 new alerts/day and the backlog clears 500/run, the backlog is always ahead.

**Mitigation**: Monitor the backlog size over time. The cursor tracks `total_backlog`, `total_fixed`, and `total_unfixable` for this purpose.

#### Worry: The cursor stored in a GitHub issue comment could be overwritten by concurrent edits.

**Mitigation**: The `concurrency` group ensures only 1 orchestrator run at a time. Additionally, the cursor update uses a compare-and-set pattern: read the current cursor, validate it matches expectations, then write the updated cursor. If a mismatch is detected, the run aborts and the next scheduled run retries.

#### Worry: A long-running Devin session blocks a slot indefinitely.

**Analysis**: Devin sessions have a `max_acu_limit` (default: 10). Sessions time out after ~30 minutes. The orchestrator tracks session creation timestamps and assumes failure if a child has been running for >1 hour.

**Mitigation**: The orchestrator evicts stale children (>1 hour) from the active set, marks their alerts as retryable, and backfills the freed slot with the next pending batch.

#### Worry: Fixes pushed by the backlog workflow conflict with ongoing PR work.

**Analysis**: The backlog fixes code on `main`. PRs branch off main. If a backlog fix is merged to main while a PR is open, the PR may need to rebase to pick up the fix. This is standard git workflow — no different from any other team member merging code to main.

**Mitigation**: Each batch gets its own independent PR. Small, focused PRs are easier to merge without conflicts than one giant PR. The PR comment includes a note: "This PR contains automated security fixes. Review before merging."

#### Worry: PR workflow shows "N pre-existing alerts on main" but doesn't fix them. Developer thinks the tool is broken.

**Mitigation**: The PR comment explicitly says: "These alerts exist on main and are handled separately by the scheduled backlog workflow. See [backlog PR #N] for progress." This sets expectations and provides a link to track progress.

#### Worry: Sub-workflow dispatch fails (GitHub API error, rate limit).

**Analysis**: The orchestrator dispatches children via the GitHub Actions API (`POST /repos/{repo}/actions/workflows/{id}/dispatches`). This API has its own rate limits (1000 requests/hour for PATs).

**Mitigation**: With 34 batches, we make 34 dispatch calls — well within the rate limit. If a dispatch fails, the orchestrator retries with exponential backoff. If it still fails, the batch stays in `pending_batches` and the cursor is updated so the next run retries it.

#### Worry: Child workflow fails but orchestrator doesn't notice.

**Mitigation**: The orchestrator polls child workflow run statuses via `GET /repos/{repo}/actions/runs/{id}`. If a child reports `conclusion: failure`, the orchestrator marks that batch's alerts as retryable (up to max attempts) and logs the failure. The cursor captures which batches failed and why.

#### Worry: Creating many PRs floods the team with review requests.

**Analysis**: A 500-alert backlog creates 34 PRs. This could overwhelm a team's review queue.

**Mitigation**: Configurable PR consolidation strategy:
- Default: 1 PR per batch (max review granularity)
- Option: Consolidate all batches into 1 PR (minimize review count but harder to review)
- Option: 1 PR per file group (compromise — related fixes together)

The PR titles include severity and rule information so teams can prioritize review.

#### Worry: What if both the PR workflow and backlog workflow create sessions at the same time?

**Mitigation**: PR workflows ALWAYS have priority. The orchestrator self-limits to 3 concurrent children, reserving 2 slots for PR workflows. Implementation:
```
Before each child dispatch:
  1. GET /v1/sessions?status=running → count active Devin sessions
  2. If active >= 3: wait 120s and re-check (max 5 retries)
  3. If active < 3: dispatch child
```

**Key insight from stress test**: The exponential backoff makes the system self-regulating. When sessions are scarce, workflows wait longer. As sessions free up, waiting workflows succeed. No external coordinator needed beyond the orchestrator's own slot management.

### Migration Path from Current Architecture

The split can be implemented incrementally:

1. **Phase 1** (low risk): In the current `devin-security-review.yml`, remove the pre-existing session creation step. Keep the pre-existing alert counting and display in the PR comment. This immediately fixes the PR-blocking and session-explosion problems.

2. **Phase 2**: Create `devin-security-batch.yml` (the child workflow) — a simple workflow that takes a batch of alert IDs, creates 1 Devin session, waits for completion, and reports results.

3. **Phase 3**: Create `devin-security-backlog.yml` (the orchestrator) — fetches alerts, groups into batches, dispatches children via `workflow_dispatch`, polls for completion, streams PR creation, manages cursor.

4. **Phase 4**: Add session reservation logic (orchestrator checks active sessions before dispatching). Connect the PR comment to the backlog PRs via cross-links.

### Summary: Before vs After

| Dimension | Current (single workflow) | Split (PR + Backlog with Fan-Out) |
|-----------|--------------------------|----------------------------------|
| PR workflow duration | Minutes (creates 20+ sessions) | Seconds (creates 0-1 sessions) |
| Sessions per PR | Up to 21 (1 new + 20 pre-existing) | 1 (new-in-PR only) |
| 20 concurrent PRs | 400+ session attempts, massive 429s | 20 session attempts, manageable |
| Backlog progress | Only when PRs are pushed | Entire backlog in 1 orchestrator run |
| Redundant work | Each PR processes same pre-existing alerts | Backlog processed once, globally |
| PR exit code | Can fail due to pre-existing batch issues | Fails ONLY for new-in-PR issues |
| Rate limit impact | PR blocked while retrying pre-existing | PR never blocked; orchestrator manages slots |
| Developer experience | "Why is my PR workflow running for 10 minutes?" | "My PR check passed in 30 seconds" |
| Time to first fix PR | N/A (no batch PRs from single workflow) | ~8-10 min (streaming) |
| Timeout risk | 6-hour limit for single job processing all batches | Each child has own timeout; orchestrator is lightweight |
| Debuggability | One massive log | Each batch = separate workflow run with own logs |
| Failure isolation | One batch failure cascades | Child 3 failing doesn't affect children 1, 2, 4 |
| PR review load | N/A | 1 focused PR per batch, reviewable independently |

---

## Limitations and Future Work

### Current Limitations

- **Language coverage**: Currently configured for Python and Actions. Adding more languages requires updating the matrix in `codeql.yml`.
- **CodeQL only**: The pipeline is specific to CodeQL. Other SAST tools (Semgrep, Snyk Code) would require adapter logic.
- **Async only**: The workflow does not wait for Devin to finish — it fires sessions and exits. Monitoring session completion requires checking session URLs manually or building a callback webhook.
- **Single repo**: Designed for a single repository. Multi-repo orchestration would need a separate dispatcher.
### Planned Improvements

- **Implementation of split-trigger architecture**: Build the orchestrator, child workflow, and PR workflow changes designed above
- **Alert deduplication**: Skip alerts that were already fixed in a previous Devin session
- **Custom CodeQL query packs**: Support for organization-specific security rules
- **Fix approval workflow**: Optional human review gate before Devin pushes fix commits
- **Metrics dashboard**: Track fix rate, false positive rate, mean time to remediation
- **Multi-language expansion**: Add JavaScript/TypeScript, Java, Go, C/C++ to the CodeQL matrix
- **Semgrep integration**: Support Semgrep as an alternative/complementary SAST engine
- **PR consolidation options**: Configurable strategy (1 PR per batch vs consolidated PR)
- **Webhook callbacks**: Devin session completion webhooks instead of polling
