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

### T15: Alert Claiming Prevents Duplicate Sessions (EC10)

**Purpose**: Verify that when two workflow runs see the same unfixed alert, only one dispatches a Devin session. The second run should see the claim marker and skip.

**Relates to**: Edge Case 10 (Alert Claiming with TTL)

**Setup**:
1. Configure workflow to run on a schedule (cron every 5 min) or trigger two `workflow_dispatch` runs in quick succession
2. Ensure at least 1 CodeQL alert is open and unfixed on the PR

**Steps**:
1. Trigger workflow run A — it creates a Devin session and writes a `claimed:` marker to the PR comment
2. Within 30 seconds, trigger workflow run B (before Devin has fixed the alert)
3. Run B reads the PR comment, finds the `claimed:` marker with a valid TTL
4. Run B skips the alert (does NOT create a duplicate session)

**Expected**:
- Run A: Creates session, writes `<!-- claimed:ALERT_KEY=RUN_A:TIMESTAMP:SESSION_ID -->`
- Run B: Reads claimed marker, logs "Alert ALERT_KEY already claimed by run RUN_A (TTL valid)", skips
- Only 1 Devin session exists for the alert, not 2
- PR comment shows the claim metadata in DEBUG mode

**Worry**: Two runs read the comment at the exact same moment (before either writes the claim). Both think it's unclaimed and both dispatch. Mitigation: `idempotent=true` on Devin sessions means identical prompts reuse the same session. Verify this fallback works.

**TTL expiry sub-test**:
1. After 30+ minutes (or by faking the timestamp), trigger run C
2. Run C should see the claim as expired (zombie), reclaim the alert, and dispatch a new session
3. Verify the old claim is replaced with a new one

---

### T16: Session Creation Failure Produces Honest State (EC11)

**Purpose**: Verify the workflow exits with the correct status code and posts an honest PR comment when Devin session creation fails.

**Relates to**: Edge Case 11 (Session Creation Failure / False-Green Check)

**Setup**:
1. Ensure all 5 Devin session slots are occupied (create 5 sessions manually or from previous runs)
2. Push vulnerable code to a PR to trigger CodeQL alerts

**Steps**:
1. Wait for CodeQL to complete and our workflow to trigger
2. Workflow attempts to create a Devin session, gets HTTP 429
3. Workflow retries once after backoff, gets 429 again
4. Check workflow exit code
5. Check PR comment content

**Expected**:
- Workflow exits with code 1 (red check), NOT code 0 (green)
- PR comment states: "**FAILED**: Devin could not create any sessions (HTTP 429 — concurrent session limit). All N alerts require manual attention. Will retry on next run."
- PR comment does NOT say "Devin is fixing these issues" (that would be a lie)
- CodeQL check is also red (independent of our workflow)
- Developer sees TWO red checks, understands both what's wrong (CodeQL) and why it's not being fixed (our workflow)

**Worry (EC11a)**: Workflow exits green despite total failure. Developer trusts the green check, waits forever, nothing gets fixed. This is the highest-priority bug to fix.

**Partial failure sub-test (EC11b)**:
1. Have 3 alerts. Occupy 4/5 Devin slots.
2. Workflow creates session for alert 1 (success, slot 5 used)
3. Workflow tries alert 2, gets 429 (no slots left)
4. Verify: exit code 1, PR comment shows "1/3 alerts dispatched, 2 could not be dispatched"
5. Verify: `dispatched:` marker for alert 1, `failed_dispatch:` marker for alerts 2-3

**Worry (EC11b)**: Partial success is reported as full success. Alerts 2-3 are silently dropped and never retried.

**Degraded mode sub-test**:
1. Make Devin API completely unreachable (bad API key or network block)
2. Verify: health check detects Devin unavailability
3. Verify: workflow exits 0 (green — this is correct in degraded mode, CodeQL still protects)
4. Verify: PR comment says "Devin is currently unavailable. N alerts listed below require manual review."

**Worry**: Degraded mode (Devin fully down) should NOT exit red — that would block CI for something outside the developer's control. Only partial/rate-limit failures should exit red.

---

### T17: Deferred Alerts Are Preserved and Picked Up (EC12)

**Purpose**: Verify that when Devin is at capacity, alerts are marked as DEFERRED (not silently dropped), and a subsequent workflow run picks them up when capacity is available.

**Relates to**: Edge Case 12 (Busy Devin / State Preservation / Zombie Detection)

**Setup**:
1. Occupy all 5 Devin session slots
2. Push vulnerable code to a PR with 3 CodeQL alerts

**Steps**:
1. Workflow run A triggers, detects 3 alerts, tries to dispatch
2. All dispatch attempts fail (429) — alerts transition to DEFERRED state
3. Verify PR comment contains `deferred:` markers for all 3 alerts with timestamp and reason code
4. Free up 2 Devin session slots (stop 2 existing sessions)
5. Trigger workflow run B (via `workflow_dispatch` or new push)
6. Run B reads deferred markers, finds 3 alerts queued for retry
7. Run B dispatches sessions for all 3 (capacity now available)
8. Verify deferred markers are replaced with claimed markers

**Expected**:
- Run A: Writes `<!-- deferred:ALERT_KEY=RUN_A:TIMESTAMP:429:retry_0 -->` for each alert
- Run A: PR comment says "3 alerts deferred — Devin at capacity. Will retry on next run."
- Run B: Reads deferred markers, dispatches sessions, transitions to CLAIMED
- No alerts are lost between runs

**Worry (state loss)**: If run A crashes after detecting alerts but before writing deferred markers, the state is lost. Mitigation: write deferred markers BEFORE attempting dispatch (optimistic deferral), then upgrade to claimed on success.

**Zombie detection sub-test**:
1. Run A claims an alert (creates session). Session ID is recorded.
2. Wait 35 minutes (past CLAIM_TTL of 30 min) — or fake the timestamp
3. Alert is still in CodeQL results (not fixed)
4. No fix commits matching the rule_id exist since claim timestamp
5. Run C triggers, detects the stale claim, marks it as ZOMBIE
6. Run C reclaims the alert and dispatches a new session
7. Verify: attempt count incremented, old session ID replaced

**Worry (zombie vs slow fix)**: A Devin session that takes 40 minutes is legitimate, not zombie. Mitigation: check for recent fix commits before declaring zombie. If a `fix: [rule_id]` commit exists since claim, the alert is likely fixed — wait for CodeQL rescan.

**Worry (EC10/EC12 collision)**: A deferred alert gets confused with a claimed alert, or vice versa. Mitigation: distinct marker prefixes (`claimed:` vs `deferred:`). Verify by checking that run B treats deferred alerts as "please retry" and claimed alerts as "hands off."

---

### T18: Stuck PR Recovery — Self-Scheduling Retry (EC13)

**Purpose**: Verify that when our workflow fails to dispatch (rate limit, API error), the PR does not get stuck forever. The workflow should self-schedule a retry so the PR eventually gets fixed without manual intervention.

**Relates to**: Edge Case 13 (Stuck PR — Failed Dispatch with No Re-Trigger)

**Setup**:
1. Occupy all 5 Devin session slots
2. Push vulnerable code to a PR with CodeQL alerts

**Steps**:
1. CodeQL runs, detects alerts (red check)
2. Our workflow triggers, tries to create session, gets 429
3. Verify: workflow exits red (not green — EC11 fix prerequisite)
4. Verify: workflow schedules a `workflow_dispatch` retry for this PR (5-10 min delay with jitter)
5. Wait for retry to fire
6. If still at capacity: verify retry schedules another retry (with increased backoff)
7. Free up Devin slots before next retry
8. Verify: retry run creates session successfully, transitions alerts from DEFERRED to CLAIMED
9. Verify: total retries capped at MAX_RETRIES (e.g., 6)

**Expected**:
- Original run: exits red, writes deferred markers, schedules retry
- Retry 1 (5 min later): reads deferred markers, tries dispatch, fails, schedules retry 2
- Retry 2 (10 min later): reads deferred markers, tries dispatch, succeeds
- PR comment updated: "Alert dispatched on retry attempt 2"
- No manual intervention required

**Worry (infinite self-scheduling)**: Without a retry cap, the workflow schedules retries forever, burning CI minutes. Mitigation: `MAX_RETRIES=6` with exponential backoff. After exhaustion, PR comment says "Automatic retry exhausted. Use `/devin retry` to trigger manually."

**Worry (PR stuck forever with no retry mechanism — current state)**:
1. Using the CURRENT workflow (no self-scheduling), push vulnerable code
2. Ensure our workflow fails (rate limit)
3. Do NOT push any new code to the PR
4. Wait 30 minutes
5. Verify: NO new workflow runs triggered. PR is stuck. CodeQL red, our workflow green (or red with EC11 fix).
6. This confirms the stuck PR problem exists and motivates Solution 2.

**`/devin retry` command sub-test (EC13 Solution 5)**:
1. After automatic retries are exhausted (or with no self-scheduling implemented)
2. Developer posts a comment on the PR: `/devin retry`
3. Verify: `issue_comment` workflow detects the command and triggers `workflow_dispatch`
4. Verify: security review workflow runs for this PR, creates session
5. Verify: rate limit on `/devin retry` — posting it twice within 5 min should only trigger once

**Worry (developer doesn't know about `/devin retry`)**: The PR comment after exhausted retries must clearly state this command as an option. Verify the comment text includes the exact command.

---

### T19: CodeQL Alerts Persist on Open PRs (EC13d)

**Purpose**: Verify that CodeQL alerts from a PR scan remain available via the GitHub API even when our workflow failed to act on them. This confirms we CAN pick up from failed PRs, not just from main.

**Relates to**: Edge Case 13d (CodeQL alerts on PR are not the same as alerts on main)

**Steps**:
1. Push vulnerable code to a PR branch
2. Wait for CodeQL to detect alerts
3. Verify alerts exist via API: `GET /code-scanning/alerts?ref=refs/pull/{N}/merge`
4. Let our workflow run and FAIL to create a Devin session
5. Wait 1 hour (simulate abandoned PR)
6. Query the same API endpoint again
7. Verify alerts are STILL present (they don't expire or get cleaned up)

**Expected**:
- Alerts persist as long as the PR is open and the code hasn't changed
- Alerts are queryable by PR merge ref
- A future workflow run can read these alerts and dispatch sessions for them
- Alerts do NOT transfer to main's alert list until the PR is merged

**Worry**: CodeQL alerts from PR scans have a TTL or get garbage-collected after the associated check run ages out. Verify they persist indefinitely on open PRs.

---

### T20: Cron Sweep Detects Stuck PRs (EC13 Solution 3)

**Purpose**: Verify the cron-based sweep workflow can find open PRs with unresolved deferred alerts and trigger retries.

**Relates to**: Edge Case 13 Solution 3 (Cron-based sweep)

**Setup**:
1. Have 2 open PRs: PR-A (has deferred alerts), PR-B (all alerts resolved)
2. Configure sweep workflow to run on schedule

**Steps**:
1. Sweep workflow runs (manually triggered or on cron)
2. Sweep lists all open PRs
3. For each PR, checks for `devin-security-state` comment with `deferred:` entries
4. Finds PR-A has deferred alerts, triggers `workflow_dispatch` for PR-A
5. Does NOT trigger for PR-B (no deferred alerts)
6. Verify: security review workflow runs for PR-A

**Expected**:
- Sweep correctly identifies stuck PRs by scanning comment markers
- Only stuck PRs get retried (no unnecessary runs)
- Sweep is idempotent: running it twice doesn't trigger duplicate dispatches (checks if a run is already in progress)

**Worry**: Sweep triggers retries for PRs where the developer intentionally paused work (e.g., draft PRs). Mitigation: skip draft PRs, respect a `<!-- devin-paused -->` marker that developers can add manually.

---

### T21: Session Accumulation and Cleanup (EC12 Root Cause)

**Purpose**: Verify that the workflow cleans up stale Devin sessions to prevent slot exhaustion, addressing the root cause of the 5-session pileup observed in production.

**Relates to**: Edge Case 12 (session lifecycle is unbounded)

**Setup**:
1. Create 5 Devin sessions via previous workflow runs
2. Let at least 3 reach "blocked" state (Devin finished work, waiting for human input)
3. Wait 1+ hour so blocked sessions are older than SESSION_CLEANUP_AGE

**Steps**:
1. Trigger a new workflow run
2. Pre-dispatch cleanup step runs: queries Devin API for active sessions
3. Identifies 3 sessions in "blocked" state older than 1 hour
4. Stops those 3 sessions (freeing 3 slots)
5. Proceeds to dispatch new session for current PR's alerts

**Expected**:
- Pre-dispatch: 5/5 slots occupied
- After cleanup: 2/5 slots occupied (3 stale sessions stopped)
- New session created successfully
- Workflow log shows: "Cleaned up 3 stale sessions (blocked > 1h)"

**Worry**: Cleanup stops a session the developer is actively reviewing. Mitigation: only stop "blocked" sessions older than SESSION_CLEANUP_AGE (1 hour). Sessions in "running" state are never stopped (Devin is still working). The cleanup age is conservative enough that any legitimate review would have concluded.

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
- [ ] T15: Alert claiming prevents duplicate sessions (EC10)
- [ ] T16: Session creation failure produces honest state (EC11)
- [ ] T17: Deferred alerts are preserved and picked up (EC12)
- [ ] T18: Stuck PR recovery via self-scheduling retry (EC13)
- [ ] T19: CodeQL alerts persist on open PRs (EC13d)
- [ ] T20: Cron sweep detects stuck PRs (EC13 Solution 3)
- [ ] T21: Session accumulation and cleanup (EC12 root cause)
