# Devin Security Review — Test Suite

This document tracks all test scenarios, results, and regression checks for the security review pipeline.

---

## Test Inventory

### T1: CodeQL Alert Detection (Python)

**Purpose**: Verify CodeQL detects Python security vulnerabilities with our configuration (`security-and-quality` suite, `remote+local` threat models).

**Steps**:
1. Push `app/server.py` containing known vulnerabilities to a PR branch
2. Wait for CodeQL to complete
3. Fetch alerts via GitHub Code Scanning API

**Expected**:
- `py/sql-injection` detected (high)
- `py/command-line-injection` detected (critical)
- `py/reflective-xss` detected (medium)
- `py/url-redirection` detected (medium)
- `py/flask-debug` detected (high)

**Run 1 result**: PASS — All 5 Python vulnerability types detected (10 total instances across the file).

**Run 2 result**: PASS — Same alerts detected. 9/10 fixed by Devin, 1 residual (`py/url-redirection`).

**Run 3 result**: PASS — All 10/10 alerts now fixed. The residual `py/url-redirection` was resolved by commit `129fbc2` (string concat sanitizer pattern).

---

### T2: Alert Classification (new-in-PR vs pre-existing)

**Purpose**: Verify the workflow correctly classifies alerts by comparing PR merge ref vs main branch.

**Steps**:
1. Trigger workflow on a PR with Python vulnerabilities
2. Check workflow logs for classification output

**Expected**:
- Alerts only on PR branch → classified as "new-in-PR"
- Alerts also on main → classified as "pre-existing"
- When no Python code on main → all Python alerts are "new-in-PR"

**Run 1 result**: PASS — 5 new-in-PR, 0 pre-existing (correct — no Python on main).

---

### T3: Devin Session Creation

**Purpose**: Verify the workflow creates Devin sessions with correct prompts.

**Steps**:
1. Trigger workflow with alerts present
2. Check Devin API for created sessions
3. Verify session prompt includes: repo URL, branch name, alert details, fix instructions

**Expected**:
- 1 session for new-in-PR alerts (push to PR branch)
- Batched sessions for pre-existing alerts (push to fix branch)
- Session prompt includes CodeQL CLI verification instructions
- `idempotent=true` and `max_acu_limit` set

**Run 1 result**: PASS — Session created, prompt included all alert details.

**Run 2 result**: PARTIAL — Sessions created, but without CodeQL CLI verification or `idempotent` flag (old workflow version).

---

### T4: Comment Flood Prevention

**Purpose**: Verify only ONE comment is posted/updated per PR, not a new one on each run.

**Steps**:
1. Push vulnerable code to trigger workflow
2. Let Devin push fixes (triggers re-run)
3. Count total comments from the bot

**Expected (with fix)**:
- Exactly 1 bot comment, updated in-place on each run
- Comment identified by `<!-- devin-security-review -->` marker
- Each update reflects current alert state

**Pre-fix result (Run 2)**: FAIL — 14 comments posted (8 near-identical). Each workflow run posted a new comment.

**Post-fix expected**: 1 comment, updated via PATCH.

---

### T5: Infinite Loop Circuit Breaker

**Purpose**: Verify the workflow stops retrying after 2 failed fix attempts per alert.

**Steps**:
1. Push code with a vulnerability that is hard/impossible to auto-fix
2. Let workflow run → create Devin session → Devin pushes fix
3. If fix fails CodeQL, workflow re-runs → check attempt counter
4. After 2 attempts, verify alert is marked "unfixable" and skipped

**Expected**:
- Attempt 1: Session created, fix pushed
- Attempt 2 (if alert persists): Session created, another fix attempt
- Attempt 3+: Alert skipped, marked unfixable in comment, `devin:manual-review-needed` label added

**Pre-fix result (Run 2)**: FAIL — No attempt tracking. 14 Devin Security Review runs, 8 sessions created for the same alert. Loop only stopped because Devin API rejected session creation (rate limit).

**Post-fix expected**: Max 2 sessions per alert, then clean stop.

**Proof from pre-fix data**:
- 41 total workflow runs for a single PR
- 14 Devin Security Review runs
- Gap analysis: runs 5-14 happened in ~20 min (avg 3.5 min gap)
- Devin API started rejecting sessions at run 12-13 (`ERROR: Failed to create Devin session`)
- Run 14 found 0 alerts (Devin's final fix worked)

---

### T6: Unfixable Alert Reporting

**Purpose**: Verify unfixable alerts are prominently reported to developers.

**Steps**:
1. Push code with an alert that Devin cannot fix
2. Let workflow exhaust 2 attempts
3. Check PR comment for "REQUIRES MANUAL REVIEW" section
4. Check PR labels for `devin:manual-review-needed`

**Expected**:
- PR comment includes table of unfixable alerts with severity, rule, file, and attempt count
- `devin:manual-review-needed` label added to PR
- Label removed when all alerts are eventually resolved

**Pre-fix result**: NOT TESTED (feature didn't exist).

---

### T7: Safe-to-Merge Signal

**Purpose**: Verify the PR comment clearly indicates whether it's safe to merge.

**Steps**:
1. Trigger workflow with alerts → verify comment says "fixing in progress"
2. Wait for Devin to fix all alerts → verify comment says "All alerts resolved"
3. If some unfixable → verify comment says "REQUIRES MANUAL REVIEW"

**Expected**:
- Clear status at top of comment
- "All CodeQL alerts have been resolved" when 0 open alerts remain
- "REQUIRES MANUAL REVIEW — N alert(s) could not be auto-fixed" when unfixable alerts exist

**Pre-fix result**: FAIL — No status signal. Comment just listed alerts with no conclusion.

---

### T8: Devin-Commit Detection

**Purpose**: Verify the workflow detects when a run was triggered by a Devin fix commit.

**Steps**:
1. Devin pushes a commit with message `fix: [py/sql-injection] ...`
2. Workflow triggers on the push
3. Check workflow logs for "Detected Devin fix commit" message

**Expected**:
- `is_devin_fix=true` output set
- Workflow applies stricter alert filtering

**Pre-fix result**: NOT TESTED (feature didn't exist).

---

### T9: Rate Limit Handling

**Purpose**: Verify the workflow handles Devin API rate limits gracefully.

**Steps**:
1. Create many sessions rapidly to trigger rate limiting
2. Check workflow logs for retry behavior

**Expected**:
- On HTTP 429: wait 60s and retry
- On repeated failures: exponential backoff (30s, 60s, 120s)
- Error logged but workflow doesn't crash

**Pre-fix observation**: Run 12-13 got `ERROR: Failed to create Devin session` but workflow continued and posted comment.

---

### T10: Resource Usage Efficiency

**Purpose**: Track resource consumption to ensure we're not wasting compute.

**Metrics to track**:
| Metric | Pre-fix (Run 2) | Target | Post-fix |
|--------|-----------------|--------|----------|
| Devin sessions per PR | 8 | 1-2 | TBD |
| Workflow runs per PR | 41 | 3-5 | TBD |
| PR comments per PR | 14 | 1 | TBD |
| Wasted GitHub Actions min | ~63 | 0 | TBD |
| Blocked sessions | 1 | 0-1 | TBD |

**Pre-fix analysis**:
- 8 sessions for 6 unique alert types (minimum needed: 1-2)
- 7 excess sessions = 7x compute cost
- 41 workflow runs (minimum needed: ~3-5) = ~8x overhead
- 14 comments = 13 unnecessary notifications to PR subscribers

---

### T11: Git History Cleanliness

**Purpose**: Verify Devin's fix commits don't create merge commits.

**Steps**:
1. Let Devin push fixes to the PR branch
2. Check git log for merge commits

**Expected**: Linear history (no `Merge branch...` commits from Devin).

**Pre-fix result**: FAIL — 4 merge commits in PR #3 history, caused by concurrent pushes from multiple actors.

**Post-fix expected**: Linear history due to `git pull --rebase` instruction.

---

### T12: CodeQL Config Consistency

**Purpose**: Verify Devin uses the SAME CodeQL configuration locally as the project's CI.

**Steps**:
1. Check project's `codeql.yml` for query suite and threat models
2. Check Devin prompt for CodeQL CLI command
3. Verify they match

**Expected**:
- Project CI: `queries: security-and-quality`, threat-models: `remote, local`
- Devin prompt: `codeql database analyze ... codeql/python-queries:codeql-suites/python-security-and-quality.qls`
- Both use the same analysis depth

---

### T13: Batch Processing Continuity

**Purpose**: Verify Devin continues fixing other alerts when one alert is unfixable.

**Steps**:
1. Push code with multiple vulnerabilities (e.g., sql-injection + url-redirection)
2. Assume url-redirection is unfixable
3. Verify Devin still fixes sql-injection and pushes that commit
4. Verify unfixable alert is reported separately

**Expected**:
- Devin processes each alert independently
- Fixable alerts get committed and pushed
- Unfixable alerts are skipped (no commit) but reported in output

---

### T14: Pre-Existing Alert Sessions Don't Create Infinite PRs

**Purpose**: Verify that Devin sessions created for pre-existing alerts push to a deterministic branch without creating new PRs, preventing an infinite PR creation cascade.

**Steps**:
1. Trigger workflow on a PR with pre-existing alerts (alerts that also exist on main)
2. Verify Devin session prompt includes "Do NOT create a pull request"
3. Verify the target branch name is deterministic: `devin/security-fixes-pr{N}`
4. Verify `idempotent=true` is set on session creation
5. Monitor: no new PRs created by the Devin session
6. If a cascade starts, verify attempt tracking stops it after 2 attempts per alert

**Expected**:
- Devin pushes commits to `devin/security-fixes-pr{N}` (not a new timestamped branch)
- No PR is created by the Devin session
- Re-runs with the same prompt reuse the existing session (idempotent)
- If the same alert is retried, attempt counter increments and stops at 2

**Risk factors**:
- Devin may ignore negative constraints ("do not create a PR") — monitor first few runs
- Future mitigation: add branch pattern filter to workflow trigger to skip `devin/security-fixes-*` branches

---

## Historical Test Runs

### Run 1 (2026-02-14 23:13 UTC) — Initial Pipeline

**Trigger**: First PR (#3) with vulnerable `app/server.py`
**CodeQL result**: 1 alert (`actions/missing-workflow-permissions`)
**Root cause**: CodeQL only scanned Actions language (no Python on main branch)
**Fix**: Added explicit `codeql.yml` with `python` language

### Run 2 (2026-02-15 00:00-00:26 UTC) — Full Pipeline Test

**Trigger**: Updated PR #3 with Python vulnerabilities + fixed CodeQL config
**CodeQL result**: 10 alerts (6 unique rules)
**Classification**: 5 new-in-PR, 0 pre-existing
**Sessions created**: 8 (7 finished, 1 blocked)
**Fixes applied**: 9/10 alerts (residual: `py/url-redirection`)
**Loop behavior**: 14 Devin Security Review runs over 73 min
**Comments**: 14 (comment flood)
**Resources wasted**: ~63 GitHub Actions min, 6-7 excess sessions

### Run 3 (2026-02-15 00:52 UTC) — Status Check

**Trigger**: Manual API checks (no new push)
**Findings**:
- All 10/10 alerts now FIXED (the `py/url-redirection` was eventually resolved)
- Loop stopped: no new workflow runs or comments since 00:26 UTC
- 3 sessions changed from "blocked" to "finished" (completed naturally)
- 1 session still "blocked" (`devin-7f966e17`) — normal end-state
- Root cause of loop stopping: Devin API rejected sessions (rate limit) + final fix worked

---

## Regression Checklist

Before each release, verify:

- [ ] T1: CodeQL detects all expected vulnerability types
- [ ] T2: Alert classification correctly separates new vs pre-existing
- [ ] T3: Devin sessions created with correct prompts and parameters
- [ ] T4: Only 1 PR comment exists (edited in-place, not duplicated)
- [ ] T5: Loop stops after 2 attempts per alert (circuit breaker works)
- [ ] T6: Unfixable alerts appear in "REQUIRES MANUAL REVIEW" section
- [ ] T7: Safe-to-merge signal present and accurate
- [ ] T8: Devin-commit detection correctly identifies fix pushes
- [ ] T9: Rate limits handled gracefully (no crashes)
- [ ] T10: Resource usage within acceptable bounds
- [ ] T11: No merge commits from Devin fix pushes
- [ ] T12: CodeQL config matches between CI and Devin prompt
- [ ] T13: Batch processing continues past unfixable alerts
- [ ] T14: Pre-existing alert sessions don't create infinite PRs
