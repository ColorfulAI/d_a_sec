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

**Stateless pickup via cursor**:
The backlog workflow must be able to run multiple times and incrementally make progress without re-processing already-handled alerts. It uses a **cursor** stored as a GitHub issue comment or repository variable:

```
┌──────────────────────────────────────────────────────┐
│  Backlog State (stored in GitHub issue #N or          │
│  repo variable SECURITY_BACKLOG_CURSOR)               │
│                                                       │
│  {                                                    │
│    "last_run": "2026-02-16T00:00:00Z",               │
│    "processed_alert_ids": [101, 102, 103, ...],      │
│    "in_progress_session_ids": ["sess_abc", ...],     │
│    "unfixable_alert_ids": [104, 105],                │
│    "next_offset": 45,                                │
│    "total_backlog": 200                               │
│  }                                                    │
│                                                       │
│  Each run:                                            │
│  1. Read cursor → know where to start                │
│  2. Fetch alerts from offset → pick next batch       │
│  3. Check in_progress sessions → skip if still       │
│     running (don't create duplicates)                │
│  4. Create sessions for unprocessed alerts           │
│  5. Update cursor with new processed IDs + offset    │
│  6. Exit (next cron run picks up from new offset)    │
└──────────────────────────────────────────────────────┘
```

**Session budget**: Configurable, default 5 sessions per run. With 15 alerts per session, each run processes up to 75 alerts. A nightly run clears 75 alerts; a 6-hour cron clears 300/day.

**Concurrency control**:
```yaml
concurrency:
  group: security-backlog-${{ github.repository }}
  cancel-in-progress: false
```
Only 1 backlog run at a time per repo. If a cron triggers while a previous run is still going, it queues (does NOT cancel the in-progress run, because that would lose work).

**Output**: Pushes fixes to a long-lived branch `devin/security-backlog` and opens/updates a single "Security Backlog Fixes" PR. Each run adds commits to the same branch rather than creating new branches.

**Exit code**: Always `0`. The backlog is best-effort. Failures are logged, and the cursor is updated so the next run retries failed alerts.

### Concurrency Management

#### Worry: What if the backlog workflow and a PR workflow both try to create sessions at the same time?

**Mitigation**: The PR workflow creates at most 1 session. The backlog workflow creates up to 5. Total concurrent sessions: 6 (within the Devin API limit of 5 + exponential backoff handles overflow). In practice, the backlog runs on a schedule (nightly) when PR activity is low.

**Design rule**: PR workflows ALWAYS have priority over backlog workflows. If the PR workflow hits a rate limit, the backlog workflow should be the one that backs off or defers.

Implementation: The backlog workflow checks the Devin API's active session count before creating new sessions. If active sessions ≥ 3 (leaving room for PR workflows), it pauses.

```
Before each session creation:
  1. GET /v1/sessions?status=running → count active sessions
  2. If active >= 3: wait 120s and re-check (max 5 retries)
  3. If active < 3: create session
  4. This reserves ~2 slots for PR workflows at all times
```

#### Worry: What if two backlog runs overlap (cron fires while previous run is still going)?

**Mitigation**: GitHub Actions `concurrency` group ensures only 1 backlog run at a time per repo with `cancel-in-progress: false`. The second run queues until the first completes.

#### Worry: Multiple PRs open at the same time, each trying to create a session?

**Mitigation**: Each PR workflow creates at most 1 session. With 20 concurrent PRs, that's 20 session attempts. With a concurrent session limit of 5, 15 will get rate-limited. The exponential backoff (60s → 120s → 240s) handles this. In the worst case, all 20 PRs get their session within ~7 minutes as earlier sessions complete.

**Key insight from stress test**: The exponential backoff makes the system self-regulating. When sessions are scarce, workflows wait longer. As sessions free up, waiting workflows succeed. No external coordinator needed.

### Stateless Pickup: How the Backlog Workflow Resumes

The backlog workflow must be fully stateless — each run reads the current state from GitHub APIs and a stored cursor, processes a batch, and updates the cursor. No in-memory state survives between runs.

```
Run N:
  1. Read cursor from GitHub issue comment (or repo variable)
     → "processed IDs: [1,2,3,...,44], offset: 45"
  2. Fetch open alerts on main: GET /code-scanning/alerts?state=open&per_page=100
  3. Filter out already-processed alerts (skip IDs in cursor)
  4. Filter out unfixable alerts (IDs in cursor's unfixable set)
  5. Check in-progress Devin sessions from cursor
     → For each session_id: GET /v1/session/{id}
     → If status=finished: check if alerts are fixed, update cursor
     → If status=running: skip these alerts (session still working)
     → If status=failed: mark alerts as retryable, increment attempt counter
  6. Pick next batch of unprocessed alerts (up to 5 sessions × 15 alerts)
  7. Create Devin sessions for each batch
  8. Update cursor: add new session IDs, advance offset, record processed IDs
  9. Exit 0

Run N+1 (6 hours later):
  1. Read cursor → offset: 45, in_progress: [sess_abc, sess_def]
  2. Check sess_abc: finished → alerts fixed → move to processed
  3. Check sess_def: failed → mark alerts as retryable
  4. Pick next batch starting from offset 45 (+ retryable alerts)
  5. Create sessions, update cursor
  6. Exit 0
```

**Key property**: If the workflow crashes mid-run, no data is lost. The cursor still has the state from the last successful update. The next run re-checks in-progress sessions and retries as needed.

### Why Not Just Re-run Failed PR Workflows?

You could argue: "if a PR workflow fails due to rate limiting, just re-run it later." This doesn't work because:

1. **No automatic re-trigger**: GitHub Actions doesn't auto-retry failed workflow runs. Someone must manually click "Re-run" or push new code.
2. **PR workflows are PR-scoped**: They only run when someone pushes to a PR branch. If the developer's code is done, they won't push again.
3. **Backlog work is global**: Pre-existing alerts are the same across all PRs. Processing them per-PR is redundant. A single scheduled workflow handles the entire backlog efficiently.
4. **Rate limit fairness**: If 20 PRs are open, each PR workflow competing for sessions is unfair to all developers. A scheduled backlog workflow processes alerts on its own timeline without blocking anyone.

### Considerations and Worries

#### Worry: Will the backlog workflow ever "catch up" with a large alert backlog?

**Analysis**: If a repo has 500 pre-existing alerts and the backlog runs every 6 hours processing 75 alerts per run, it takes ~7 runs (42 hours) to process the full backlog. If Devin fixes 80% of alerts, the backlog shrinks to 100 unfixable alerts which are catalogued and never retried.

**Mitigation**: For initial onboarding of a large codebase, run the backlog workflow manually multiple times or increase the session budget temporarily.

#### Worry: What if new alerts accumulate faster than the backlog clears them?

**Analysis**: New alerts only appear when code is merged to main. The backlog workflow runs on a schedule. If the team merges 10 new alerts/day and the backlog clears 75/run (4 runs/day = 300/day), the backlog shrinks rapidly.

**Mitigation**: Monitor the backlog size over time. If it's growing, increase the cron frequency or session budget. The cursor tracks total backlog size for this purpose.

#### Worry: The cursor stored in a GitHub issue comment could be overwritten by concurrent edits.

**Mitigation**: The `concurrency` group ensures only 1 backlog run at a time. Additionally, the cursor update uses a compare-and-set pattern: read the current cursor, validate it matches expectations, then write the updated cursor. If a mismatch is detected, the run aborts and the next scheduled run retries.

#### Worry: A long-running Devin session blocks the backlog from making progress.

**Analysis**: Devin sessions have a `max_acu_limit` (default: 10). Sessions time out after ~30 minutes. If a session is stuck, the next backlog run detects it as `status=failed` or `status=timed_out` and retries the alerts.

**Mitigation**: The cursor tracks session creation timestamps. If a session has been "in progress" for >1 hour, it's assumed failed and its alerts are marked for retry.

#### Worry: Fixes pushed by the backlog workflow conflict with ongoing PR work.

**Analysis**: The backlog fixes code on `main`. PRs branch off main. If a backlog fix is merged to main while a PR is open, the PR may need to rebase to pick up the fix. This is standard git workflow — no different from any other team member merging code to main.

**Mitigation**: The backlog PR should be reviewed and merged during low-activity windows (e.g., overnight). The PR comment includes a note: "This PR contains automated security fixes. Review before merging to avoid conflicts with in-flight PRs."

#### Worry: PR workflow shows "N pre-existing alerts on main" but doesn't fix them. Developer thinks the tool is broken.

**Mitigation**: The PR comment explicitly says: "These alerts exist on main and are handled separately by the scheduled backlog workflow. See [backlog PR #N] for progress." This sets expectations and provides a link to track progress.

### Migration Path from Current Architecture

The split can be implemented incrementally:

1. **Phase 1** (low risk): In the current `devin-security-review.yml`, remove the pre-existing session creation step. Keep the pre-existing alert counting and display in the PR comment. This immediately fixes the PR-blocking and session-explosion problems.

2. **Phase 2**: Create `devin-security-backlog.yml` as a new workflow with `schedule` trigger. Implement the cursor-based stateless pickup. Test on a small backlog.

3. **Phase 3**: Add the concurrency reservation logic (backlog checks active sessions before creating more). Connect the PR comment to the backlog PR via cross-links.

### Summary: Before vs After

| Dimension | Current (single workflow) | Split (PR + Backlog) |
|-----------|--------------------------|----------------------|
| PR workflow duration | Minutes (creates 20+ sessions) | Seconds (creates 0-1 sessions) |
| Sessions per PR | Up to 21 (1 new + 20 pre-existing) | 1 (new-in-PR only) |
| 20 concurrent PRs | 400+ session attempts, massive 429s | 20 session attempts, manageable |
| Backlog progress | Only when PRs are pushed | Continuous (scheduled) |
| Redundant work | Each PR processes same pre-existing alerts | Backlog processed once, globally |
| PR exit code | Can fail due to pre-existing batch issues | Fails ONLY for new-in-PR issues |
| Rate limit impact | PR blocked while retrying pre-existing | PR never blocked; backlog retries on own schedule |
| Developer experience | "Why is my PR workflow running for 10 minutes?" | "My PR check passed in 30 seconds" |

---

## Limitations and Future Work

### Current Limitations

- **Language coverage**: Currently configured for Python and Actions. Adding more languages requires updating the matrix in `codeql.yml`.
- **CodeQL only**: The pipeline is specific to CodeQL. Other SAST tools (Semgrep, Snyk Code) would require adapter logic.
- **Async only**: The workflow does not wait for Devin to finish — it fires sessions and exits. Monitoring session completion requires checking session URLs manually or building a callback webhook.
- **Single repo**: Designed for a single repository. Multi-repo orchestration would need a separate dispatcher.
- **Single-trigger architecture**: Both PR-scoped and pre-existing alert processing happen in the same workflow, causing PR blocking and session explosion under concurrent load (see Split-Trigger Architecture section for the redesign).

### Planned Improvements

- **Split-trigger architecture**: Separate PR workflow (new-in-PR only) from scheduled backlog workflow (pre-existing only) — see design above
- **Cursor-based stateless pickup**: Backlog workflow resumes from where it left off using a GitHub-stored cursor
- **Session reservation**: Backlog workflow checks active session count and reserves slots for PR workflows
- **Alert deduplication**: Skip alerts that were already fixed in a previous Devin session
- **Custom CodeQL query packs**: Support for organization-specific security rules
- **Fix approval workflow**: Optional human review gate before Devin pushes fix commits
- **Metrics dashboard**: Track fix rate, false positive rate, mean time to remediation
- **Multi-language expansion**: Add JavaScript/TypeScript, Java, Go, C/C++ to the CodeQL matrix
- **Semgrep integration**: Support Semgrep as an alternative/complementary SAST engine
