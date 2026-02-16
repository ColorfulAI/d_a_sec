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

### REQUIREMENT: No "Pretend Fixes" — Every Fix PR Must Pass CodeQL

**Core invariant**: A fix PR must never introduce new CodeQL alerts or leave existing alerts unresolved. If Devin "fixes" an alert but introduces an unused import, a new taint flow, or any other CodeQL finding, the fix is worse than useless — it creates a PR that fails CI, wastes reviewer time, and erodes trust in the system.

**Why we verify internally (not just in CI)**:
- CI catches CodeQL failures *after* the PR is created. By then, the damage is done: the PR exists, reviewers are notified, and the failure is visible. In a Fortune 500 setting, a stream of failing fix PRs destroys confidence in the tool.
- Internal verification catches issues *before* the PR is created. If the fix doesn't pass CodeQL, it's either retried or skipped — no broken PR is ever opened.
- The goal is: **every fix PR that gets created should pass CodeQL CI on the first try.**

### Dynamic CodeQL Configuration — Portability Across Repos

**Problem**: This workflow may be deployed on different repositories, each with its own CodeQL configuration (different languages, query suites, threat models). Hardcoding `python`, `security-and-quality`, and `remote+local` breaks portability.

**Solution**: Step 0 of the batch workflow dynamically parses the target repo's `.github/workflows/codeql*.yml` at runtime to extract:
- **Languages**: From the matrix strategy (e.g., `python`, `actions`, `javascript`)
- **Query suite**: From the `codeql-action/init` step's `queries` input (e.g., `security-and-quality`)
- **Threat models**: From the `codeql-action/init` step's `config` block (e.g., `remote`, `local`)

If no CodeQL workflow is found, sensible defaults are used (`python`, `security-and-quality`, `remote+local`).

These parsed values are passed to both:
1. The Devin prompt (so Devin runs the correct CodeQL CLI commands internally)
2. The post-session verification gate (so the pipeline verifies with the exact same config)

**Edge case**: If the repo uses `${{ matrix.language }}` in the init step's `languages` input (template variable), the parser extracts the language from the matrix definition instead. This handles the common GitHub Actions pattern of matrix-based language analysis.

### Bug #42: CodeQL Internal Verification Gap

**Problem discovered**: Despite the internal verification loop design above, Devin sessions were pushing fixes that still failed CodeQL CI checks (observed on PRs #111, #112, and #159). PR #159 specifically had an unused import (#228) introduced by Devin while fixing `auth_handler.py`.

**Root cause analysis** — 3 configuration gaps between Devin's internal CodeQL check and the repo's CI:

| Gap | CI Configuration | Devin Prompt (before fix) | Impact |
|-----|-----------------|--------------------------|--------|
| Missing threat model | `threat-models: [remote, local]` | Default (remote only) | Misses vulnerabilities from local sources (env vars, file reads, CLI args) |
| Missing language | `languages: [python, actions]` | `--language=python` only | Cannot verify `.github/workflows/*.yml` alerts |
| Only checks specific rule | Checks ALL rules in modified files | Only checks if specific `RULE_ID` still fires | Misses NEW alerts introduced by the fix (e.g., unused imports) |

**Fix (two-layer verification)**:

1. **Layer 1 — Improved Devin prompt**: Updated CodeQL CLI instructions to:
   - Add `--threat-model=local` flag to match CI's `remote+local` configuration
   - Check ALL alerts in modified files (not just the specific rule being fixed)
   - Explicitly document CI's exact config so Devin knows what to replicate

2. **Layer 2 — Post-session CodeQL verification gate**: New pipeline step (Step 3b) that runs after Devin pushes but before PR creation:
   - Downloads CodeQL CLI and checks out Devin's branch
   - Creates database and runs analysis with exact CI config (`security-and-quality` + `threat-model=local`)
   - Parses SARIF to detect: (a) target alerts still present, (b) new alerts introduced
   - Labels PR as `codeql-verified` (pass) or `codeql-verification-failed` (fail)
   - PR body includes verification results section

**Why two layers**: Layer 1 (prompt) is "best effort" — Devin may skip or misconfigure the check. Layer 2 (pipeline gate) is "trust but verify" — runs deterministically in the workflow with the exact CI config, regardless of what Devin did internally.

**Evidence this would have caught PR #159's issue**: The unused import `#228` in `auth_handler.py` would have been detected by Layer 2's "new alerts in modified files" check, and the PR would have been labeled `codeql-verification-failed` instead of appearing clean.

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

### Batch Session Creation (Advanced Mode)

The orchestrator creates Devin sessions **up-front** for all batches in a wave before dispatching child workflows. This is the "batch session creation" pattern — instead of each child workflow creating its own session sequentially, the orchestrator creates N sessions in rapid succession, then dispatches N children with pre-created session IDs. All sessions in a wave start working simultaneously.

```
WITHOUT batch mode (sequential):                WITH batch mode (parallel):
                                                 
  Orchestrator                                    Orchestrator
     │                                               │
     ├─ dispatch child 1                              ├─ create session 1 ─┐
     │    └─ child creates session → Devin starts     ├─ create session 2 ─┤ (all created
     │       (wait ~5s)                               ├─ create session 3 ─┤  within seconds)
     ├─ dispatch child 2                              ├─ create session 4 ─┤
     │    └─ child creates session → Devin starts     ├─ create session 5 ─┘
     │       (wait ~5s)                               │
     ├─ dispatch child 3                              ├─ dispatch child 1 (session_id=S1)
     │    └─ child creates session → Devin starts     ├─ dispatch child 2 (session_id=S2)
     │       ...                                      ├─ dispatch child 3 (session_id=S3)
     │                                                ├─ dispatch child 4 (session_id=S4)
  Sessions start 5-25s apart                          ├─ dispatch child 5 (session_id=S5)
  (sequential delay)                                  │
                                                   All 5 sessions already working
                                                   when children start polling
```

**How it works:**

1. **Orchestrator creates sessions**: For each batch in the wave, the orchestrator calls `POST /v1/sessions` with the full prompt (including CodeQL config, alert details, branch name). The API returns a `session_id` and `url` immediately — Devin starts working in the background.

2. **Orchestrator dispatches children with session IDs**: The child workflow (`devin-security-batch.yml`) receives `session_id` and `session_url` as `workflow_dispatch` inputs. When a pre-created session ID is present, the child skips session creation entirely and goes straight to polling.

3. **Graceful fallback**: If session creation fails (e.g., rate limit 429), the child is dispatched without a session ID. The child then creates the session itself (standalone mode). This ensures the system never gets stuck — it degrades gracefully from batch mode to standalone mode.

| Mode | Who Creates Session | When | Advantage |
|------|-------------------|------|-----------|
| **Batch** (default) | Orchestrator | Up-front, before dispatch | All sessions start simultaneously; true parallelization |
| **Standalone** (fallback) | Child workflow | After dispatch | Works when orchestrator can't create session (rate limit, API error) |

**Why this matters for production:**
- With 5 concurrent slots and 10-min sessions, batch mode saves ~25s per wave (5 sessions × 5s sequential delay). Over 7 waves (35 batches), that's ~3 minutes of wall-clock time saved.
- More importantly, all 5 sessions in a wave start working at the same moment. In sequential mode, session 5 starts ~25s after session 1, meaning it finishes ~25s later — pushing the entire wave completion time out.
- The graceful fallback means batch mode never causes failures. If the Devin API is overloaded, individual children seamlessly fall back to creating their own sessions.

**Edge case — rate limit during batch creation:**
If the orchestrator hits a 429 (concurrent session limit) while creating session 3 of 5, it:
1. Dispatches children 1-2 with pre-created sessions (batch mode)
2. Dispatches child 3 without a session ID (standalone fallback)
3. Child 3 creates its own session with exponential backoff
4. No sessions are wasted, no children are blocked

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

## Backlog Architecture — Testing Findings

### Iteration 1: First Real Run (Bugs #5–#7)

**What was tested**: Orchestrator dispatched 1 child batch workflow with 3 alert IDs. The child created a Devin session that ran for ~36 minutes before transitioning to `suspended` status.

**What was found**:

| Bug | Root Cause | Impact | Fix (PR #110) |
|-----|-----------|--------|---------------|
| **#5: `suspended` not handled** | Polling `case` statement only had `finished`, `stopped`, `blocked`, `failed`, `error`. `suspended` fell through to default (no-op). | 7 wasted polls (7 min) after session went suspended, then API returned non-JSON → crash. | Added `suspended` to the `blocked` case (both need manual intervention). |
| **#6: jq crash on non-JSON API response** | `jq -r '.status // "unknown"'` called on raw API response without validating it's JSON first. HTML error pages, rate limit responses, or transient failures crash jq with exit code 5. | Entire workflow fails with cryptic `parse error: Invalid numeric literal at line 1, column 7`. No recovery. | Added `jq empty` guard before parsing. Non-JSON responses log a warning and retry on next poll cycle. |
| **#7: Operator precedence in collect-results** | `[ -n "$BRANCH_NAME" ] && [ "$STATUS" = "finished" ] \|\| [ "$STATUS" = "stopped" ]` evaluates as `(BRANCH && finished) \|\| stopped`. | If status is `stopped` but branch is empty, the commit-counting block runs and queries a non-existent branch. | Fixed with explicit grouping: `&& { [ ... ] \|\| [ ... ]; }`. |

**How these were discovered**: By reading the CI job logs line-by-line after the batch workflow failed at poll 43/45. The session status transition pattern (`running` → `suspended` at poll 37) was visible in the poll output. The jq crash was the proximate cause of failure, but the root cause was the missing `suspended` handler — if handled, the workflow would have exited gracefully 6 polls earlier.

**Why these matter in production**: At Fortune 500 scale with dozens of concurrent batch workflows, any unhandled Devin session status is a ticking time bomb. The Devin API may return `suspended`, `paused`, or other statuses not in our original design. Defensive parsing (validate JSON before jq) prevents cascading failures from API transients.

### Bug #8: Partial-File Batching Causes CodeQL PR Failures

**Discovered**: During iteration 2. PRs #111 and #112 (created by the batch workflow) both fail the CodeQL PR check despite Devin successfully fixing the targeted alerts.

**Root cause**: The original batching algorithm split a file's alerts across batches. For example, `user_service.py` had 10 open alerts (3 XSS, 2 SQL injection, 1 command injection, etc.). The orchestrator put only 3 XSS alerts into Batch 1. When Devin fixed those 3 and created a PR, the PR modified `user_service.py`. The CodeQL PR check then scanned the modified file and reported the remaining 7 unfixed alerts as "new alerts in code changed by this pull request" — causing the PR to fail.

**Timeline**:
1. Batch 1 receives alerts #218, #219, #220 (all `py/reflective-xss` in `user_service.py` and `template_engine.py`)
2. Devin fixes all 3 alerts, verifies internally with CodeQL CLI that those specific alerts are resolved ✅
3. PR #112 is created, modifying `user_service.py` and `template_engine.py`
4. CodeQL PR check runs on the modified files → finds 7 OTHER alerts (#201, #205, #206, #212, #213, #216, #217) that were not in this batch
5. PR check reports "1 critical, 2 medium" failures → PR appears broken ❌

**Why this is critical in production**: An enterprise security team sees a batch fix PR that "fails CodeQL." This destroys trust in the automated pipeline immediately. The PR actually did fix its targeted alerts, but the presentation is misleading. Every batch PR that touches a file with unfixed alerts will appear broken.

**Solution**: Never split a file's alerts across batches. When a file is included in a batch, ALL of that file's open alerts must go into the same batch. This way, after Devin fixes all alerts in a file, the PR touches only fully-cleaned files and CodeQL passes. If a file has more alerts than the batch cap, that file gets its own batch (the cap is a soft limit, not a hard split boundary).

**Before** (broken): Batch 1 gets 3 of 10 alerts in `user_service.py` → PR modifies file → CodeQL finds remaining 7 → FAIL

**After** (fixed): Batch 1 gets ALL 10 alerts in `user_service.py` → PR modifies file → CodeQL finds 0 remaining → PASS

### Bug #10: Orchestrator Cannot Resolve Child Workflow Run IDs

**Discovered**: During iteration 2. The orchestrator (run 22053695399) ran for 56+ minutes without ever detecting that its child batch workflow (run 22053848997) had completed successfully. The orchestrator was stuck in an infinite polling loop.

**Root cause**: `workflow_dispatch` runs always report `head_branch: "main"` and `display_title: "Devin Security Batch"` in their GitHub API metadata — they do NOT contain the batch branch name or batch ID anywhere. The orchestrator's run resolution logic tried to match by `batch_branch in str(run)` and `batch_id_str in run_title`, but neither ever matched because the metadata simply doesn't include this information.

**Timeline**:
1. Orchestrator dispatches child for Batch 1 at 07:22:54 UTC, records `branch_name: "devin/security-batch-test1-1771226943"`
2. Child workflow (run 22053848997) starts at 07:29:05 UTC, runs for ~38 min, completes at 08:07:30 UTC
3. Orchestrator polls every 60s, tries to match child run by checking if `"devin/security-batch-test1-1771226943"` appears in the run JSON
4. GitHub API returns `head_branch: "main"` for the run — no match
5. After 5 minutes of no match, orchestrator re-dispatches the batch → creates duplicate run (22053854689, which gets cancelled)
6. The cycle repeats: dispatch → fail to resolve → timeout → re-dispatch

**Why this is critical in production**: With 5 concurrent batch children, the orchestrator would create an infinite cascade of duplicate dispatches. Each re-dispatch creates a new Devin session (consuming a slot), and the orchestrator would eventually exhaust all session slots with duplicate work. At Fortune 500 scale, this burns through ACU budget and creates conflicting fix PRs.

**Solution**: Replace content-based matching with timestamp-based matching. The orchestrator now assigns the first unmatched `workflow_dispatch` run whose `created_at >= dispatch_time`. An `already_matched` set prevents double-assignment across concurrent children.

**Caveat**: If two batches are dispatched within the same second, timestamp ordering alone may swap which run is assigned to which batch. This is acceptable because: (1) dispatches are separated by `time.sleep(5)`, and (2) each child workflow is self-contained (the batch details are passed as inputs, not inferred from run metadata).

### Bug #11: Python Stdout Buffering in Heredoc Mode

**Discovered**: During iteration 3. The orchestrator (run 22055145035) ran for 13+ minutes without producing any output. When cancelled, all print statements were lost — zero diagnostic information was available.

**Root cause**: Python's stdout is fully buffered when running in non-TTY mode (heredoc `python3 << 'EOF'`). All `print()` calls write to a buffer that is only flushed when full (~8KB) or on process exit. When GitHub Actions cancels the process, the buffer is discarded without flushing.

**Why this is critical in production**: Without real-time logs, operators cannot diagnose why an orchestrator run is stuck. Every minute of "no output" translates to blind debugging — checking Devin sessions, GitHub API, and workflow configuration without any clue about which code path the orchestrator is executing.

**Solution**: Added `PYTHONUNBUFFERED=1` environment variable and `sys.stdout.reconfigure(line_buffering=True)` at the top of every Python heredoc block. This forces line-buffered output so each `print()` call flushes immediately.

### Bug #12: No Timeout on urllib.request.urlopen()

**Discovered**: During iteration 3 investigation. Code review revealed that all `urllib.request.urlopen()` calls in both the orchestrator and batch workflows had no explicit timeout parameter.

**Root cause**: `urllib.request.urlopen()` defaults to `socket._GLOBAL_DEFAULT_TIMEOUT` which is effectively infinite. If the Devin API or GitHub API hangs, the entire workflow blocks indefinitely with no way to recover.

**Why this is critical in production**: A transient API hang (common at scale with rate limiting, network partitions, or CDN issues) would silently block the entire orchestrator. Combined with bug #11 (no stdout), the operator sees nothing — just a frozen workflow consuming a GitHub Actions runner slot.

**Solution**: Added `HTTP_TIMEOUT = 30` constant and `timeout=HTTP_TIMEOUT` parameter to every `urlopen()` call in both the orchestrator and batch workflows. After 30 seconds, a `socket.timeout` exception is raised, caught, and logged.

### Bug #13: gh_api() Cannot Handle 204 No Content Responses

**Discovered**: During iteration 3. The orchestrator (run 22055752309) reached step 8 (dispatch) but never dispatched any child workflows. Investigation revealed it was stuck in the initial fill loop.

**Root cause**: GitHub's `workflow_dispatch` endpoint returns HTTP 204 No Content with an empty response body on success. The `gh_api()` function called `json.loads(resp.read())` on this empty body, which raised `json.JSONDecodeError`. The generic `except Exception` handler caught it and returned `status=0`. The `dispatch_child()` function checked `if status == 204` but received 0, so it returned `False` — even though the HTTP request actually succeeded on GitHub's side.

**Compound effect**: In earlier iterations, the dispatch was actually succeeding on GitHub's side (creating the workflow run), but the orchestrator thought it failed. This silently created orphan batch workflow runs that were never tracked by the orchestrator.

**Why this is critical in production**: Every "failed" dispatch that actually succeeded creates an orphan Devin session consuming an ACU slot. At Fortune 500 scale with hundreds of alerts, the orchestrator would burn through the entire session budget with untracked orphan sessions while reporting 0 progress.

**Solution**: Modified `gh_api()` to check for empty body or 204 status before attempting JSON parsing: `if not body or status_code == 204: return {}, status_code`.

### Bug #14: Session Reservation Gate Blocks Dispatch Due to External Sessions

**Discovered**: During iteration 3 (run 22056237926). The orchestrator logged `Active Devin sessions: 62` and `Session reservation: 62 active sessions >= 3 limit. Waiting...` on every poll cycle for 10+ minutes.

**Root cause**: The `check_active_devin_sessions()` function queries the Devin API for ALL sessions with `status_in=running,started` across the entire account — not just sessions created by this orchestrator. The 62 sessions were from the stress test PRs (#6-#104) which each triggered the PR-scoped security review workflow. The orchestrator's session reservation check (`if active_sessions >= max_concurrent`) blocked dispatch because 62 >= 3.

**Why this is critical in production**: Any organization using Devin for multiple purposes (code reviews, feature work, security reviews, multiple repos) will have sessions running that the backlog orchestrator doesn't control. The session reservation gate effectively prevents the orchestrator from ever dispatching if the organization is actively using Devin — which is exactly when they'd want the backlog sweep to run.

**Solution**: Removed `check_active_devin_sessions()` from dispatch decision logic entirely. Concurrency is now controlled solely by `len(active_children) < max_concurrent`, tracking only children the orchestrator itself manages. Child batch workflows handle Devin API 429 rate limits internally with retry/backoff. The `check_active_devin_sessions()` function is retained for diagnostic logging but no longer gates dispatch.

**Trade-off**: If max_concurrent=3 and 4 other sessions are already running, the orchestrator may dispatch 3 children that each fail to create Devin sessions (429). This is acceptable because: (1) child workflows retry with backoff, (2) failed session creation doesn't waste ACU budget, and (3) the orchestrator's poll loop will detect child failures and handle them.

### Bug #15: Status Field Mismatch in Batch Workflow Polling

**Discovered**: During iteration 3 (batch run 22056586654). The batch workflow polled the Devin session for 28+ minutes without detecting completion, despite the session having successfully created PR #121 with all CodeQL checks passing.

**Root cause**: The batch workflow's polling logic extracted the `.status` field (a free-form string) from the Devin API response and matched it against a fixed set of values: `finished|stopped|blocked|suspended|failed|error`. However, the Devin API's well-defined field is `.status_enum`, which uses a different, documented set of values: `working`, `blocked`, `expired`, `finished`, `suspend_requested`, `suspend_requested_frontend`, `resume_requested`, `resume_requested_frontend`, `resumed`. The `.status` field value didn't match any case branch, so every poll fell through to the "still running" path.

**Why this is critical in production**: Every batch workflow run would poll for the full 45-minute timeout and then report "timeout" even when the Devin session completed successfully in 10 minutes. This means: (1) batch workflows take 4.5× longer than necessary, (2) the orchestrator's rolling window is blocked (a slot that should free up in 10 min is held for 45 min), (3) a 34-batch backlog that should take ~70 min takes ~315 min (5+ hours), dangerously close to GitHub Actions' 6-hour timeout, and (4) all alerts are incorrectly marked as "timeout" (unfixable) even when they were successfully fixed.

**Solution**: Updated the polling logic to:
1. Extract both `.status` and `.status_enum` from the API response
2. Prefer `status_enum` (well-defined enum) over `status` (free-form string)
3. Fall back to `.status` only if `status_enum` is missing or null
4. Added `expired` as a recognized terminal state (session timed out)
5. Added `suspend_requested` and `suspend_requested_frontend` to the blocked/needs-intervention case
6. Log both fields (`status=$STATUS status_enum=$STATUS_ENUM`) for future debugging
7. Updated downstream steps (Create PR condition, collect-results) to handle all new status values

**Diagnostic improvement**: Every poll now logs `Poll N/45: status=X status_enum=Y`, making it trivial to diagnose future polling issues from workflow logs.

### Bug #16: `headers` Variable Undefined in Artifact Download (NameError)

**Discovered**: During code review of the orchestrator's main loop on main branch. The artifact download code at lines 722 and 730 uses `urllib.request.Request(artifacts_url, headers=headers)`, but `headers` was never defined in the Python scope.

**Root cause**: The `gh_api()` function builds its own headers internally (`{"Authorization": f"token {gh_pat}", ...}`) but doesn't expose them to the outer scope. The artifact download code was written assuming `headers` existed as a module-level variable, but it doesn't. This causes a guaranteed `NameError` at runtime.

**Why this is critical in production**: This bug silently breaks the entire unfixable-alert-to-human-review pipeline. When a child batch completes successfully, the orchestrator tries to download the batch result artifact to get the per-alert fixed/unfixable breakdown. The `NameError` is caught by the `except Exception` handler, which falls through to "marking all alerts as processed" — silently losing the fixed/unfixable distinction. Every alert appears as "processed" in the cursor, and no alerts are ever flagged as unfixable. The human review notification never fires. The backlog appears 100% complete when it isn't.

**Solution**: Defined a `headers` dict in the orchestrator scope before the main loop, with the same auth token used by `gh_api()`.

### Bug #17: Session Reservation Gate Still in Backfill Path

**Discovered**: During code review. PR #120 (Bug #14) removed `check_active_devin_sessions()` from the initial dispatch loop, but the backfill path (triggered after a child completes, line 769-770) still calls it and gates on `if active_sessions < max_concurrent`.

**Root cause**: Bug #14 fix was incomplete — it only updated the initial fill loop. The backfill path is a separate code block that runs when a child completes and a pending batch needs to be dispatched. This path was missed during the Bug #14 fix.

**Why this is critical in production**: After the first wave of children completes, the orchestrator tries to backfill with the next batch. But if 5+ external Devin sessions are running, `check_active_devin_sessions()` returns >= max_concurrent, and the backfill is blocked. The orchestrator correctly dispatched the initial children (Bug #14 fix), but then gets stuck after the first wave. For a 34-batch backlog, only the first 3 batches complete — the remaining 31 are never dispatched.

**Solution**: Replaced the backfill's `check_active_devin_sessions()` check with `len(active_children) < max_concurrent`, matching the initial fill path.

---

## Unfixable Alert → Human Review Pipeline

### The Problem

When Devin cannot fix an alert after 2 internal CodeQL verification attempts inside the session, that alert must be:
1. **Identified by specific alert ID** (not just a count)
2. **Recorded in the cursor** as `unfixable_alert_ids` (so future runs skip it)
3. **Surfaced to humans** with clear actionable information

Without this pipeline, unfixable alerts are silently buried in the "processed" bucket. No human is notified, no one knows which specific alerts need manual attention, and the backlog appears "complete" when it isn't.

### Architecture

```
Batch Workflow (child)                    Orchestrator
┌─────────────────────┐                   ┌─────────────────────┐
│ Devin session        │                   │                     │
│ completes            │                   │                     │
│         │            │                   │                     │
│         ▼            │                   │                     │
│ Re-query CodeQL API  │                   │                     │
│ for EACH alert ID    │                   │                     │
│ in this batch        │                   │                     │
│         │            │                   │                     │
│    ┌────┴────┐       │                   │                     │
│    │         │       │                   │                     │
│  fixed    still open │   artifact.json   │                     │
│    │         │       │ ─────────────────>│ Download artifact   │
│    ▼         ▼       │                   │         │           │
│ fixed_    unfixable_ │                   │    ┌────┴────┐      │
│ alert_ids alert_ids  │                   │    │         │      │
│                      │                   │ cursor:   cursor:   │
│ Upload as artifact   │                   │ processed unfixable │
└─────────────────────┘                   │         │           │
                                          │         ▼           │
                                          │ Post comment on     │
                                          │ tracking issue:     │
                                          │ "⚠ N alerts need   │
                                          │  human review"      │
                                          │         │           │
                                          │         ▼           │
                                          │ Apply label:        │
                                          │ devin:human-review- │
                                          │ needed              │
                                          └─────────────────────┘
```

### How It Works

**Step 1: Batch workflow verifies each alert (source of truth)**

After the Devin session completes, the batch workflow re-queries the CodeQL API for each alert ID in the batch:
- `state == "fixed"` → alert goes to `fixed_alert_ids`
- `state == "dismissed"` → treated as resolved (someone manually dismissed it)
- `state == "open"` → alert goes to `unfixable_alert_ids`
- API error → conservatively marked unfixable

This is the **source of truth** — not commit counting (which was the old approach and unreliable: 1 commit ≠ 1 fix).

**Step 2: Orchestrator reads batch result artifact**

When a child workflow completes successfully, the orchestrator downloads its `batch-{id}-result` artifact (a ZIP containing `batch_result.json`). This JSON contains:
```json
{
  "fixed_alert_ids": ["201", "205", "206"],
  "unfixable_alert_ids": ["212", "217"],
  "fixed_count": 3,
  "failed_count": 2
}
```

**Step 3: Cursor updated with per-alert granularity**

- Fixed alerts → `cursor.processed_alert_ids` (won't be retried)
- Unfixable alerts → `cursor.unfixable_alert_ids` (won't be retried, AND surfaced to humans)
- If artifact download fails → fallback: all alerts marked as `processed` (safe but loses granularity)

**Step 4: Human notification**

If any unfixable alerts exist after the orchestrator completes:
1. A comment is posted on the tracking issue with a table of unfixable alert IDs + links
2. The `devin:human-review-needed` label is applied to the tracking issue
3. The workflow summary includes the unfixable count

### Why This Matters in Production

| Without this pipeline | With this pipeline |
|---|---|
| Alert silently disappears into "processed" | Alert explicitly tagged as "unfixable" |
| No human is notified | Tracking issue comment + label alerts the team |
| Next run skips it (good) but no one knows why | Next run skips it AND humans know to investigate |
| Backlog dashboard shows 100% complete (misleading) | Dashboard shows "150 fixed, 12 need human review" |
| Enterprise client asks "what happened to alert #217?" | Client sees "Alert #217: Devin attempted, needs human review" |

### Edge Cases and Worries

**Worry: CodeQL API returns stale state (Bug #18 — CONFIRMED)**
After Devin pushes a fix, the CodeQL alert state might not immediately flip to "fixed" because CodeQL re-analysis needs to run on the default branch. The batch workflow queries CodeQL right after the session completes, which may be before the fix is merged.

**Original mitigation (INSUFFICIENT)**: The batch workflow checks alert state on the `main` branch. Since the fix is on a PR branch (not yet merged), alerts will likely still show as "open." This means the first run over-reports ALL alerts as unfixable. The design claimed "on the next orchestrator run, they'll be removed from the unfixable list" — but this was never implemented. The filter logic at step 5 skips any alert in `unfixable_alert_ids` without re-checking its current state. So once an alert is marked unfixable, it stays unfixable forever, even after the PR is merged and the alert is actually fixed.

**Bug #18 — Two-part issue**:

**Part A: False unfixable classification.** The collect-results step queries `GET /repos/{owner}/{repo}/code-scanning/alerts/{id}` which returns the alert state on the default branch (main). Since the fix PR hasn't been merged yet, ALL alerts show `state=open`, and ALL are marked unfixable. This means every batch run reports 0 fixed, N unfixable — even when Devin's fixes are valid. The human review notification fires for every alert, flooding the security team with false positives.

**Part B: No re-verification on subsequent runs.** The filter logic (step 5, lines 326-338) skips alerts in `unfixable_alert_ids` without re-querying their current CodeQL state. After the fix PR is merged and the alert transitions to `state=fixed`, the next orchestrator run still treats it as "unfixable" because it's in the cursor's skip list. The `unfixable_alert_ids` list grows monotonically and never shrinks.

**Solution (Bug #18 fix)**:
1. **Collect-results**: Instead of querying alert state on main (which will always be "open" pre-merge), check if the branch has commits modifying the files containing each alert. If the file was modified → mark as `attempted` (likely fixed, pending PR merge). If the file was NOT modified → mark as `unfixable` (Devin didn't touch it).
2. **Orchestrator re-verification**: On each run, before skipping alerts in `unfixable_alert_ids`, re-query CodeQL for each unfixable alert. If the alert is now `state=fixed` (PR was merged), remove it from `unfixable_alert_ids` and add to `processed_alert_ids`. This implements the "self-healing" behavior the design originally promised.
3. **Three-state classification**: Alerts now have three states in the cursor: `processed` (confirmed fixed), `unfixable` (confirmed not fixed — file was not modified by Devin), and `attempted` (fix was pushed but not yet merged — pending verification).

**Worry: Shell variables invisible to Python heredoc (Bug #19 — CONFIRMED)**
The collect-results step in the batch workflow set `REPO`, `SESSION_STATUS`, `SESSION_ID`, `SESSION_URL`, `PR_NUMBER`, `PR_URL` as shell variables in the `run:` block, but the Python heredoc reads `os.environ` which only sees environment variables. Shell variables are NOT inherited by child processes (like the Python interpreter). Result: `session_status` was always empty, causing ALL batches to fall through to the `else` clause and mark all alerts as "unresolved" regardless of actual session status.

**Solution (Bug #19 fix)**: Move all step-output-dependent variables to the step's `env:` block so they become actual environment variables visible to the Python subprocess. Also added `blocked` to the list of valid session statuses in collect-results (Devin sessions that go blocked may have done partial work — the file-modification heuristic still applies).

**Worry: Artifact download 403 on redirect (Bug #20 — CONFIRMED)**
GitHub's artifact `archive_download_url` returns a 302 redirect to Azure Blob Storage. Python's `urllib` follows the redirect and forwards the `Authorization: token <pat>` header to Azure, which rejects it with HTTP 403 ("Server failed to authenticate the request"). The pre-signed Azure URL doesn't need GitHub auth — and won't accept it.

Without this fix, the orchestrator silently falls back to marking all alerts as "processed" (losing the fixed/attempted/unfixable breakdown from Bug #18). The three-state classification never reaches the cursor.

**Solution (Bug #20 initial fix — superseded by Bug #21 fix)**: Custom `NoAuthRedirectHandler` that strips the `Authorization` header when following redirects. This fix was deployed but caused Bug #21.

**Worry: Artifact download HTTP 400 after redirect handler fix (Bug #21 — CONFIRMED)**
The Bug #20 fix (custom `NoAuthRedirectHandler`) caused a new failure: HTTP 400 "The request URI is invalid" from Azure Blob Storage. Root cause: Python's `urllib` redirect handler creates a malformed `Request` object when constructing the redirected request — the `header_items()` method returns internal header representations that don't roundtrip cleanly through `add_header()`, and the URL itself may be corrupted during the redirect chain.

This meant the three-state classification from Bug #18 still never reached the cursor. The orchestrator fell back to marking all 12 alerts as "processed" instead of the correct "12 attempted, 0 unfixable".

**Solution (Bug #21 fix)**: Replaced the entire urllib-based artifact download with a `subprocess.run(["curl", "-sL", ...])` call. `curl` natively strips `Authorization` headers on cross-domain redirects (since curl 7.58+, standard on all GitHub-hosted runners). This avoids both the 403 (Bug #20) and the 400 (Bug #21) by never touching Python's redirect handling. The function `download_artifact_zip()` writes to a temp file, reads the bytes, and cleans up. A 60-second subprocess timeout prevents hangs.

**Worry: Multi-batch cross-matching causes orphaned runs and infinite polling (Bug #22 — CONFIRMED)**

When 2+ batches are dispatched within seconds of each other, the orchestrator's run resolution logic cross-matches them. GitHub's API returns workflow runs newest-first. The old code iterated this list per-child and grabbed the first unmatched run created after the child's dispatch time. When batch 1 (dispatched at T1) and batch 2 (dispatched at T1+5s) both trigger workflow runs, the API returns batch 2's run first (newest). Batch 1's resolution loop grabs batch 2's run because it was created after T1. Batch 2 then cannot find its own run (the original run for batch 1 was created between T1 and T1+5s but before T1+5s, so it doesn't match batch 2's `>= T1+5s` filter).

**Observed behavior (iteration 4, orchestrator run 22060117744)**:
1. Orchestrator dispatched batch 1 at T1, batch 2 at T1+5s
2. GitHub created run A (for batch 1) and run B (for batch 2)
3. Poll #1: Batch 1 resolved → run B (WRONG — run B was batch 2's run)
4. Batch 2 could never find run A (created before batch 2's dispatch time)
5. After 5 minutes: batch 2 re-dispatched → created run C (3rd workflow run, 3rd Devin session!)
6. Run A completed as an orphan — wasted a Devin session slot
7. Orchestrator stuck polling batch 2's re-dispatched run for 25+ minutes
8. Had to be manually cancelled

**Compound issues**:
- **Orphaned Devin sessions**: Run A created a real Devin session that processed alerts but was never tracked. Its results were lost.
- **Wasted ACU budget**: 3 Devin sessions created instead of 2 (50% waste)
- **Infinite polling**: The `check_child_status()` function returns string `"unknown"` on API failure. The polling loop only handled `"completed"`, `"queued"`, `"in_progress"`, `"waiting"`. Any other status silently kept the child in `active_children` forever.

**Why this is critical in production**: With 34 batches (500 alerts), every pair of concurrent dispatches risks cross-matching. A 5-slot rolling window dispatching 5 batches simultaneously would create 10 Devin sessions (5 correct + 5 orphans), burning the entire session budget in one wave. The orchestrator would then hang indefinitely waiting for the orphaned runs to "complete."

**Solution (Bug #22 fix — two parts)**:
1. **Chronological matching**: Collect ALL unresolved children in one pass. Sort both the API runs and unresolved children oldest-first by timestamp. Match 1:1 in dispatch order. Add `already_matched.add(run_id)` within the loop to prevent double-matching (was also a latent bug in the old code).
2. **Unknown status handler**: Added `else` branch in the polling loop for unexpected statuses. Logs the unexpected status and evicts the child after `max_child_runtime` seconds, preventing infinite hang.

**Worry: PR creation step skips `blocked` sessions — PR URL lost (Bug #23 — CONFIRMED)**

Devin sessions frequently end in `blocked` status instead of `finished`. This happens when Devin completes its work but the session transitions to `blocked` (waiting for human confirmation or hitting an internal limit). The batch workflow's "Create PR" step had an `if` condition that listed specific statuses (`finished`, `stopped`, `suspended`, `suspend_requested`, `suspend_requested_frontend`, `expired`) but NOT `blocked`. When the session went `blocked`:

1. The polling loop correctly detected `blocked` and exited with `status=blocked`
2. The "Create PR" step's `if` condition didn't match → step was SKIPPED
3. Devin had already created a PR inside the session (PRs #134, #135 exist)
4. The result artifact recorded `pr_url: ""` and `pr_number: ""`
5. The orchestrator could not report which PRs were created

**Observed behavior (iteration 4 re-run, batches 22061015908 and 22061018778)**:
- Both sessions ended with `status_enum=blocked` after ~16-17 polls (~16 min)
- Both Devin sessions pushed code and created PRs (#134, #135)
- Both result artifacts had empty `pr_url` and `pr_number`
- The "Create PR" step was skipped for both batches

**Why this is critical in production**: Every batch that ends `blocked` loses its PR URL linkage. The orchestrator summary has no PR URLs to report. Engineers reviewing the tracking issue see alert counts but no links to the actual fix PRs. For an enterprise team reviewing 34 batch PRs, missing links means manual searching through GitHub to find the fixes.

**Solution (Bug #23 fix)**: Added `blocked` to the "Create PR" step's `if` condition. The step already handles existing PRs (lines 431-445): if Devin created a PR inside the session, the step detects it via the GitHub API and captures its URL instead of creating a duplicate.

**Worry: Artifact download failure falsely marks alerts as "processed" (Bug #24 — CONFIRMED)**

When the orchestrator cannot download a child batch's result artifact (network error, artifact expired, malformed JSON), the fallback code marked ALL alerts in that batch as `processed`. This is wrong — `processed` means "confirmed fixed on main." Without artifact data, the orchestrator has no evidence that any fix was applied. Marking as `processed` prevents the next orchestrator run from re-verifying these alerts.

**Impact in production**: If GitHub Artifacts has a brief outage during the orchestrator's result collection phase, every batch whose artifact can't be downloaded gets its alerts marked as `processed`. These alerts are permanently skipped in future runs, even if Devin's fix didn't actually work. The backlog appears "cleared" but the vulnerabilities remain.

**Solution (Bug #24 fix)**: Changed the fallback from `processed` to `attempted`. Alerts marked as `attempted` are re-verified on the next orchestrator run (Bug #18b re-verification logic). If the fix PR was merged and CodeQL confirms the alert is resolved, the alert moves from `attempted` to `processed`. If not, it stays in `attempted` for another attempt.

**Worry: Orchestrator summary doesn't report batch PR URLs (Bug #25 — CONFIRMED)**

The orchestrator's final summary logged alert counts, attempted IDs, and unfixable IDs, but did not report which PRs were created by each batch. For an enterprise team, the summary is the primary output — it should link to every fix PR so reviewers can start merging immediately.

**Solution (Bug #25 fix)**: The orchestrator now extracts `pr_url` from each batch's result artifact and stores it on the batch object. The final summary includes a "PRs created" section listing all batch PR URLs.

**Worry: Unblock counter never resets — sessions terminated prematurely at different blocking points (Bug #37 — CONFIRMED)**

The `UNBLOCK_ATTEMPTS` counter in the batch workflow's poll loop monotonically increases. If a Devin session goes blocked → working → blocked (at a different point in its work), the counter does not reset. With `MAX_UNBLOCK_ATTEMPTS=2`, a batch processing 12 alerts across 3 files could hit 3 separate blocking points (one per file), but the session gets terminated after the 2nd unblock — even though each unblock successfully resumed work.

**Observed behavior (Cycle 4 runs 22064834214 + 22064837375)**: Both batch sessions received 2 unblock messages (HTTP 200 each). The sessions remained in `blocked` status on subsequent polls. The logs show "Session blocked after 2 unblock attempts — accepting as terminal" without checking whether the session resumed work between unblock attempts.

**Production impact**: High — in a Fortune 500 repo with large batches (15 alerts across 5+ files), Devin may need to ask clarifying questions at multiple points during a long session. Each blocking point is independent (different file, different vulnerability type). The fixed budget of 2 unblocks means the session is killed after the 2nd question, regardless of how much useful work happened between questions.

**Solution (Bug #37 fix)**: Three changes: (1) Track `LAST_STATUS` to detect transitions. When the session transitions from `blocked` → `working`, reset `UNBLOCK_ATTEMPTS` to 0. This means the budget applies per consecutive blocking episode, not per session lifetime. (2) Increase `MAX_UNBLOCK_ATTEMPTS` from 2 to 3 for more resilience. (3) Use a more forceful unblock message that explicitly instructs Devin not to ask questions. (4) Wait 90 seconds (instead of 60) after sending unblock to give the session time to process the message.

**Worry: PR body classification metadata appended BEFORE collect-results runs (Bug #38 — CONFIRMED)**

The Bug #36 fix PATCHes the PR body with structured batch metadata during the "Create PR" step (Step 4). However, the three-state classification (fixed/attempted/unfixable) is computed in the "Collect results" step (Step 5), which runs AFTER Step 4. This means the PR body's metadata template has empty classification fields — the actual alert classification data is never written to the PR body.

**Observed behavior (Cycle 4 PRs #148, #149)**: Both PRs had the structured batch metadata template (title, severity table, run link) but the classification section showed 0 fixed, 0 attempted, 0 unfixable — even though the collect-results step correctly classified all 22 alerts as "attempted".

**Production impact**: Medium — enterprise teams reviewing fix PRs see the structured template but with empty/zero classification data. The PR appears to have processed 0 alerts, which is misleading. The actual results are only visible in the workflow run logs and the uploaded artifact, not in the PR itself.

**Solution (Bug #38 fix)**: Added a new step (Step 5b: "Update PR with classification metadata") that runs AFTER collect-results. This step reads the classification outputs (fixed_alert_ids, attempted_alert_ids, unfixable_alert_ids) and PATCHes the PR body to append: (1) a human-readable classification summary table, and (2) a machine-readable JSON block in an HTML comment (`<!-- batch-classification-metadata {...} -->`) for the orchestrator to parse on subsequent runs.

**Worry: Cursor doesn't store per-alert PR URLs for re-verification correlation (Bug #39 — DOCUMENTED)**

The cursor stores `processed_alert_ids`, `attempted_alert_ids`, and `unfixable_alert_ids` as flat lists of alert numbers. When the orchestrator re-verifies "attempted" alerts on a subsequent run, it checks CodeQL alert state on main. If the alert is still open, it needs to know WHICH PR contained the attempted fix — to check if the PR was merged, abandoned, or still open. Currently, there is no mapping from alert ID → PR URL in the cursor.

**Production impact**: Low-medium — the re-verification logic works without this mapping (it checks CodeQL state directly), but it cannot provide actionable guidance like "Alert #42 was attempted in PR #148 which is still open — merge it to resolve." Enterprise teams lose traceability.

**Mitigation**: Document as a future enhancement. The cursor format can be extended to include a `alert_pr_map` dictionary (`{"42": "https://github.com/.../pull/148", ...}`). The Bug #38 fix already writes this data to the PR body, so the orchestrator could extract it from PR bodies during re-verification.

**Worry: Production cursor parsing path (reset_cursor=false) never tested in real run (Bug #40 — DOCUMENTED)**

All 4 test cycles used `reset_cursor=true`, which bypasses the cursor parsing Python code entirely (exits early before the heredoc executes). The Bug #33 fix (IndentationError) was applied based on code review, not runtime validation. If there are other issues in the cursor parsing logic (e.g., JSON parsing edge cases, missing fields, type mismatches), they would only manifest in production scheduled runs.

**Production impact**: Medium — the first scheduled cron run (every 6 hours) will exercise the cursor parsing path. If there's an undetected bug, the cron run fails silently and the backlog sweep stops. The Bug #33 fix addressed the most obvious issue (IndentationError), but there may be others.

**Mitigation**: The next test cycle should explicitly test with `reset_cursor=false` after at least one run has created a cursor comment. This validates the full cursor load → parse → resume path.

**Worry: Devin sessions consistently end "blocked" despite unblock messages (Bug #41 — INVESTIGATION COMPLETE)**

Across all 4 test cycles, every Devin session ended with `status_enum=blocked` despite receiving unblock messages via `POST /v1/sessions/{session_id}/message` (all returning HTTP 200 with `null` body). The sessions work for ~10 minutes, then transition to `blocked` and never resume.

**Root cause analysis**: The Devin API's `POST /message` endpoint queues the message for delivery but does not forcibly unblock the session. When Devin uses `block_on_user=true` internally (which is its default behavior when asking questions or requesting confirmation), the session enters a state that requires the message to be processed by the agent — but the agent may not process queued messages if it's in a deep blocking state. The `null` response body (instead of a `detail` field) suggests the message was accepted but not acted upon.

**Three-part fix (Bug #41)**:
1. **Prevention over cure**: Rewrote the Devin session prompt to open with `CRITICAL OPERATING MODE` that explicitly forbids `block_on_user=true`, asking questions, waiting for confirmation, or requesting approval. The instruction appears FIRST in the prompt (before any task context) to maximize compliance.
2. **Escalating unblock messages**: Instead of a single generic unblock message, the workflow now sends escalating messages — early attempts use "CRITICAL" framing with detailed instructions, later attempts use "URGENT" framing with explicit skip-and-push directives.
3. **More attempts with longer waits**: Increased `MAX_UNBLOCK_ATTEMPTS` from 3 to 5. Wait time between attempts increased from 90s to 120s (first 2 attempts) and 180s (subsequent attempts). Added `CONSECUTIVE_BLOCKED` counter for diagnostic visibility.
4. **Explicit CodeQL verification commands**: The prompt now includes the exact `python3 -c` command to parse SARIF output and check if a specific rule ID still fires, reducing ambiguity in the verification step.

**Production impact**: Critical — if sessions consistently block, no alerts are ever confirmed "fixed." The pipeline produces PRs but they may contain incomplete or unverified fixes.

**Worry: CodeQL internal verification not matching CI configuration (Bug #42 — DOCUMENTED)**

The user observed that PRs #111 and #112 (created by the batch workflow) still fail CodeQL checks in CI, despite the prompt instructing Devin to verify fixes using CodeQL CLI internally. This means either: (a) Devin is not executing the CodeQL verification step, (b) the internal CodeQL configuration differs from CI, or (c) Devin is running CodeQL but not correctly interpreting the results.

**Root cause**: The original prompt's CodeQL verification instructions were high-level ("Run analysis... Check if the specific alert rule ID still appears"). The instructions did not provide the exact SARIF parsing command needed to programmatically check results. Devin may have skipped the verification or checked manually (visually scanning output) and missed residual alerts.

**Fix (Bug #42)**: Updated the prompt to include:
1. Explicit `--overwrite` flag on database creation (required when re-running for multiple alerts)
2. The exact `python3 -c` command to parse SARIF JSON and check for specific rule ID + file combinations
3. Explicit instruction to use the `security-and-quality` query suite with `remote+local` threat models (matching CI configuration)
4. Clear instruction that if verification fails after 2 attempts, the alert must be SKIPPED — do NOT commit a broken fix

**Remaining gap**: Even with explicit instructions, Devin sessions may still skip CodeQL verification if they run out of ACU budget or encounter CodeQL installation failures. A production-grade solution would be to add a post-session CodeQL check in the batch workflow itself (Step 5c), running CodeQL on the branch and comparing results to the original alert list. This is documented as a future enhancement.

**Worry: "Blocked" sessions are NOT stuck — they are COMPLETED (Bug #43 — ROOT CAUSE FOUND)**

Across all 5 test cycles, every Devin session ended with `status_enum=blocked`. Bugs #34, #37, and #41 attempted increasingly aggressive mitigations (unblock messages, escalating urgency, longer waits, CRITICAL OPERATING MODE prompt). None worked — sessions always ended blocked.

**Root cause**: The Devin API documentation's official polling example treats `blocked` and `finished` as **equivalent terminal states**:
```python
if response_json["status_enum"] in ["blocked", "finished"]:
    return response_json["structured_output"]
```
Sessions go `blocked` when Devin completes its work and sends a final message with `block_on_user=true`. This is **normal completion behavior**, not an error. The `POST /v1/sessions/{session_id}/message` API successfully delivers messages (HTTP 200) but doesn't change the session's terminal state — because the session is already done.

**Evidence from Cycle 5**:
- Batch 1: Session worked 11 min (polls 2-11), modified all 3 target files, pushed branch, went blocked at poll 12. 5 unblock attempts over 13 min — all wasted.
- Batch 2: Session worked 17 min (polls 2-18), modified all 3 target files, pushed branch, went blocked at poll 19. 5 unblock attempts over 13 min — all wasted.
- Both sessions completed their work BEFORE blocking. The blocking was Devin saying "I'm done."

**Production impact**: Critical performance — each batch wasted ~13 minutes on unnecessary unblock attempts (5 attempts × 120-180s waits). For a 34-batch backlog across 7 waves, this adds ~91 minutes of pure waste (13 min × 7 waves). A backlog that should complete in ~70 min takes ~160 min.

**Solution (Bug #43 fix)**: Treat `blocked` as equivalent to `finished` in the polling loop — immediately accept as terminal success and proceed to PR creation. Removed all unblock infrastructure (UNBLOCK_ATTEMPTS, MAX_UNBLOCK_ATTEMPTS, CONSECUTIVE_BLOCKED, escalating messages, wait timers). The subsequent steps (branch check, PR creation, result classification) already handle partial work correctly via the file-modification heuristic.

**This supersedes Bugs #34, #37, and #41** — those were treating a symptom (blocked status) as a problem, when it was actually the expected completion signal.

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
