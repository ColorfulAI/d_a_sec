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

### T18: Stuck PR Recovery — Cron Sweep Retry (EC13)

**Purpose**: Verify that when our workflow fails to dispatch (rate limit, API error), the PR does not get stuck forever. The cron sweep should detect the stuck PR and trigger a retry automatically — no self-scheduling, no developer action required.

**Relates to**: Edge Case 13 (Stuck PR — Failed Dispatch with No Re-Trigger)

**Why NOT self-scheduling**: Self-scheduling retry was rejected (see DESIGN.md EC13). At enterprise scale (50+ repos, 2-hour Devin outage), self-scheduling creates hundreds of queued `workflow_dispatch` retries that cause a thundering herd when Devin recovers. Each retry clutters the Actions tab. The cron sweep is strictly better: centralized, rate-limited, capacity-aware, no accumulation during outages.

**Setup**:
1. Occupy all 5 Devin session slots
2. Push vulnerable code to a PR with CodeQL alerts
3. Ensure the cron sweep workflow is installed and enabled

**Steps**:
1. CodeQL runs, detects alerts (red check)
2. Our workflow triggers, tries to create session, gets 429
3. Verify: workflow exits red (not green — EC11 fix prerequisite)
4. Verify: workflow writes DEFERRED markers with `tool_down` reason (EC14)
5. Verify: PR comment says "Temporarily Delayed — automatic retry within 15 minutes"
6. Wait for next cron sweep interval (15 min)
7. Sweep checks Devin capacity — if still at capacity, sweep exits (no retries dispatched, no accumulation)
8. Free up Devin slots before next sweep
9. Next sweep detects stuck PR with deferred markers, triggers `workflow_dispatch`
10. Verify: retry run creates session successfully, transitions alerts DEFERRED → CLAIMED
11. Verify: PR comment updates from "Temporarily Delayed" to "Fixing in Progress"

**Expected**:
- Original run: exits red, writes deferred markers with `tool_down` reason
- PR comment: "Temporarily Delayed — automatic retry within 15 minutes"
- Cron sweep (15 min later): detects stuck PR, checks capacity, dispatches retry
- Retry succeeds: PR comment updates to "Fixing in Progress"
- No manual intervention required. No visible clutter in Actions tab beyond the sweep runs.

**Worry (thundering herd on recovery)**: After a 2-hour outage across 50 repos, the sweep runs once and dispatches retries only up to the available Devin capacity (budget-aware). Remaining stuck PRs wait for the NEXT sweep. Verify: sweep dispatches at most N retries per run (where N = available session slots).

**Worry (PR stuck forever with no retry mechanism — current state)**:
1. Using the CURRENT workflow (no cron sweep), push vulnerable code
2. Ensure our workflow fails (rate limit)
3. Do NOT push any new code to the PR
4. Wait 30 minutes
5. Verify: NO new workflow runs triggered. PR is stuck. CodeQL red, our workflow green (or red with EC11 fix).
6. This confirms the stuck PR problem exists and motivates the cron sweep.

**Escalation sub-test (1+ hour failure)**:
1. Keep Devin at capacity for 1+ hour (4 sweep intervals)
2. Verify: after 4 failed sweep attempts, PR comment escalates to "Requires Attention — Devin unavailable for 1+ hour"
3. Verify: Slack/email webhook fires to security team (if configured)
4. Verify: alert stays DEFERRED (NOT UNFIXABLE) — tool-down alerts never give up permanently

**`/devin retry` command sub-test (hidden power-user escape hatch)**:
1. With cron sweep disabled or developer wants immediate retry
2. Developer posts a comment on the PR: `/devin retry`
3. Verify: `issue_comment` workflow detects the command and triggers `workflow_dispatch`
4. Verify: security review workflow runs for this PR, creates session
5. Verify: rate limit on `/devin retry` — posting it twice within 5 min should only trigger once
6. Note: `/devin retry` is NOT mentioned in the standard PR comment. It exists only for power users and debugging.

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

### T22: TOOL_DOWN vs AI_FAILED Classification Correctness (EC14)

**Purpose**: Verify the workflow correctly classifies failures into TOOL_DOWN (infrastructure issue, should auto-retry) vs AI_FAILED (Devin tried and couldn't fix, human must review). This is the foundational test for the failure mode taxonomy — if classification is wrong, every downstream behavior (retry logic, PR comments, cron sweep) is wrong.

**Why we test this**: The single most dangerous failure in the entire system is misclassification. If a TOOL_DOWN alert gets labeled AI_FAILED, it will NEVER be retried — the developer is told "fix it yourself" when the only problem was Devin being temporarily busy. If an AI_FAILED alert gets labeled TOOL_DOWN, the cron sweep will retry it every 15 minutes forever, wasting Devin sessions on something Devin already proved it can't fix.

**Relates to**: Edge Case 14 (Failure Mode Taxonomy)

**Setup**:
1. Prepare a PR with 4 CodeQL alerts of varying fixability
2. Occupy 4/5 Devin session slots (to force partial failure)

**Steps**:

*Scenario A — TOOL_DOWN (dispatch-level):*
1. Alert 1: workflow tries to create session, gets HTTP 429 (rate limit)
2. Verify: alert marked `deferred:ALERT_KEY=RUN:TS:429:tool_down:retry_0`
3. Verify: PR comment shows "Queued for automatic retry" for this alert
4. Verify: cron sweep WILL pick this up on next run

*Scenario B — TOOL_DOWN (session-level):*
1. Alert 2: session created successfully, but Devin session errors out immediately (crashes before pushing any code)
2. Verify: alert marked `deferred:ALERT_KEY=RUN:TS:session_error:tool_down:retry_0`
3. Verify: PR comment shows "Queued for automatic retry" (not "Needs manual fix")
4. Verify: this is treated identically to dispatch failure for retry purposes

*Scenario C — AI_FAILED (max attempts):*
1. Alert 3: Devin creates session, pushes fix, CodeQL re-scans, alert persists. Attempt 2: same result.
2. Verify: alert marked `unfixable:ALERT_KEY:ai_failed:attempt_2`
3. Verify: PR comment shows "Needs manual fix" with link to Devin's attempted fix session
4. Verify: cron sweep will NOT retry this alert

*Scenario D — AI_FAILED (no fix pushed):*
1. Alert 4: Devin creates session, session completes, but no commits were pushed (Devin couldn't figure out a fix)
2. Verify: alert marked `unfixable:ALERT_KEY:ai_failed:no_fix_pushed`
3. Verify: PR comment shows "Needs manual fix — Devin could not determine a fix"

**Expected**:
- Each alert has the correct failure mode in its marker
- PR comment accurately reflects per-alert status with no conflation
- TOOL_DOWN alerts: retryable, shown as "Queued for retry"
- AI_FAILED alerts: terminal, shown as "Needs manual fix" with session link

**Worry (misclassification — TOOL_DOWN as AI_FAILED)**: Devin API returns 500 (internal server error) during session creation. The workflow incorrectly treats this as "Devin tried and failed" instead of "infrastructure issue." Result: alert marked AI_FAILED, never retried, developer told to fix manually when Devin never even attempted it. This is the WORST possible misclassification because the developer is blamed for an infrastructure problem.

**Worry (misclassification — AI_FAILED as TOOL_DOWN)**: Devin session runs, pushes a fix that doesn't resolve the CodeQL alert, but the workflow marks it as TOOL_DOWN (e.g., because the session status check returned an unexpected status code). Result: cron sweep retries every 15 minutes, creating new Devin sessions that make the same unsuccessful fix attempt. At enterprise scale: hundreds of wasted sessions per day.

**Worry (ambiguous session failure)**: Devin session created, ran for 20 minutes, then stopped with status "errored." Did Devin TRY to fix and fail (AI_FAILED)? Or did the session crash due to infrastructure (TOOL_DOWN)? Classification heuristic: check if any fix commits were pushed. If yes: AI attempted, classify based on CodeQL rescan. If no commits: TOOL_DOWN (session-level infrastructure failure).

**Sub-test (boundary case — partial fix)**:
1. Devin fixes 2 of 3 alerts in one session, but the 3rd persists after 2 attempts
2. Verify: alerts 1-2 marked FIXED, alert 3 marked AI_FAILED
3. Verify: PR comment shows mixed state correctly — "Fixed" for 1-2, "Needs manual fix" for 3
4. Verify: cron sweep ignores this PR entirely (no TOOL_DOWN alerts remain)

---

### T23: Cron Sweep Respects Failure Mode Taxonomy (EC14 + EC13)

**Purpose**: Verify the cron sweep ONLY retries TOOL_DOWN alerts and NEVER retries AI_FAILED alerts. This is the critical integration test between EC13 (cron sweep) and EC14 (failure taxonomy). Without this, the sweep becomes a resource-burning bot.

**Why we test this**: At enterprise scale (100+ repos, thousands of alerts), the cron sweep runs every 15 minutes across all repos. If it doesn't respect failure modes, it will create Devin sessions for alerts that Devin already proved it can't fix. At $X per session, this is directly burning money with zero expected value.

**Relates to**: Edge Case 13 (Cron Sweep) + Edge Case 14 (Failure Mode Taxonomy)

**Setup**:
1. Have 3 open PRs with our bot comment:
   - PR-A: 2 alerts marked `deferred:...:tool_down:retry_1` (dispatch failed, should retry)
   - PR-B: 2 alerts marked `unfixable:...:ai_failed:attempt_2` (Devin tried, human must fix)
   - PR-C: 1 alert marked `deferred:...:tool_down:retry_0` + 1 alert marked `unfixable:...:ai_failed:attempt_2` (mixed)
2. Devin has 3 available session slots

**Steps**:
1. Cron sweep runs
2. Sweep scans all 3 PRs, reads deferred/unfixable markers
3. For PR-A: finds 2 TOOL_DOWN alerts, dispatches retry
4. For PR-B: finds only AI_FAILED alerts, SKIPS entirely (no dispatch)
5. For PR-C: finds 1 TOOL_DOWN alert, dispatches retry for that one only. AI_FAILED alert untouched.
6. Verify: exactly 2 workflow_dispatch calls made (PR-A and PR-C), NOT 3

**Expected**:
- PR-A: retried (both alerts are TOOL_DOWN)
- PR-B: NOT retried (all alerts are AI_FAILED — nothing to do)
- PR-C: retried, but ONLY the TOOL_DOWN alert. The AI_FAILED alert stays unfixable.
- Total Devin sessions created: 2 (not 3, not 4)

**Worry (sweep retries AI_FAILED alerts)**: Sweep doesn't check the `reason` field in deferred markers and treats ALL deferred/unfixable alerts as retryable. Result: every 15 minutes, it creates new Devin sessions for alerts Devin already failed to fix. The enterprise customer sees their Devin session budget being consumed with no new fixes. Trust destroyed.

**Worry (sweep skips TOOL_DOWN alerts)**: Sweep checks for `deferred:` markers but the marker format changed (e.g., new field added) and the regex no longer matches. Result: TOOL_DOWN alerts are invisible to the sweep. PRs stay stuck forever. The cron sweep exists but is silently broken.

**Worry (capacity exhaustion from retries)**: Sweep dispatches retries for PR-A (2 alerts) using 2 of 3 available slots. PR-C's TOOL_DOWN alert needs 1 more slot. What if retrying PR-A's alerts consumes all 3 slots (because each alert gets its own session)? Verify: sweep checks remaining capacity after each dispatch and stops when budget is exhausted.

**Sub-test (sweep during extended outage)**:
1. Devin has 0 available slots for 1+ hour
2. Sweep runs 4 times (every 15 min), each time finds 0 capacity, exits immediately
3. Verify: NO retries dispatched during the outage (no accumulation)
4. Verify: each sweep run costs <5 seconds of Actions time (capacity-first exit)
5. After 1 hour: PR comments escalate to "Requires Attention — Devin unavailable for 1+ hour"
6. Verify: escalation webhook fires (if configured)
7. Verify: TOOL_DOWN alerts still in DEFERRED state (NOT UNFIXABLE — tool-down never gives up)

---

### T24: Mixed Failure Modes on Single PR (EC14 UX)

**Purpose**: Verify the PR comment correctly displays mixed alert states (FIXED + TOOL_DOWN + AI_FAILED) in a single unified view. This is the "one glance" test — a developer looking at the comment should immediately understand which alerts need their attention, which are being handled, and which are done.

**Why we test this**: Enterprise developers manage dozens of PRs. They need to triage quickly. If the comment conflates failure modes or requires reading hidden markers to understand status, developers will ignore it. The comment must be scannable in under 5 seconds.

**Relates to**: Edge Case 14 (PR comment UX per failure mode)

**Setup**:
1. PR with 5 CodeQL alerts that have been through various lifecycle stages:
   - Alert 1: FIXED (Devin pushed fix, CodeQL confirmed resolved)
   - Alert 2: AI_FAILED (Devin tried 2x, vulnerability persists)
   - Alert 3: TOOL_DOWN / DEFERRED (dispatch failed, queued for cron sweep retry)
   - Alert 4: CLAIMED (Devin session in progress, actively being fixed)
   - Alert 5: AI_FAILED (Devin session completed, no commits pushed)

**Steps**:
1. Trigger workflow run that reads the unified state block
2. Workflow builds PR comment with per-alert status table
3. Verify comment content and formatting

**Expected PR comment structure**:
```
**Devin Security Review** — Partially Delayed

| Alert | Severity | Status | Detail |
|-------|----------|--------|--------|
| py/sql-injection at server.py:18 | high | Fixed | Resolved in commit abc123 |
| py/xss at server.py:46 | medium | Needs manual fix | Devin tried 2x, vulnerability persists [View attempt](url) |
| py/command-injection at server.py:25 | critical | Queued for retry | Devin at capacity, auto-retry in ~15 min |
| py/flask-debug at server.py:51 | warning | Fixing in progress | Devin session active [View session](url) |
| py/unsafe-deser at server.py:37 | critical | Needs manual fix | Devin could not determine a fix [View attempt](url) |

CodeQL is still protecting this PR from merging with unresolved vulnerabilities.
```

**Verify**:
- Comment title reflects the WORST active state ("Partially Delayed" because there's a TOOL_DOWN alert)
- FIXED alerts show commit link
- AI_FAILED alerts show Devin session link (so developer can review what Devin tried)
- TOOL_DOWN alerts say "auto-retry in ~15 min" (sets developer expectation, no action needed)
- CLAIMED alerts say "Fixing in progress" with session link
- NO mention of `/devin retry` or any manual retry action in the standard comment

**Worry (all alerts shown as same status)**: Comment doesn't differentiate between failure modes. All 5 alerts shown as "In Progress" or all as "Failed." Developer can't tell which need their attention. This is the pre-EC14 behavior we're fixing.

**Worry (comment title doesn't reflect reality)**: Comment says "All Resolved" but 2 alerts are AI_FAILED. Or says "Temporarily Delayed" but some alerts are permanently unfixable. Title must reflect the worst active state.

**Worry (stale comment after retry succeeds)**: Alert 3 was "Queued for retry." Cron sweep retries, Devin fixes it. But the PR comment still says "Queued for retry" because the retry workflow didn't update the comment. Verify: after successful retry, the comment is updated and alert 3 transitions to "Fixing in progress" then "Fixed."

**Sub-test (comment title progression)**:
1. Initial state: 3 TOOL_DOWN alerts -> title: "Temporarily Delayed"
2. Sweep retries, 2 succeed, 1 still deferred -> title: "Partially Delayed"
3. Last TOOL_DOWN retry succeeds, but 1 AI_FAILED remains -> title: "Requires Manual Review"
4. Developer fixes the AI_FAILED alert, CodeQL re-scans -> title: "All Resolved"
5. Verify: each transition updates the title correctly

---

### T25: Auth Failure — Non-Retryable TOOL_DOWN (EC14 Special Case)

**Purpose**: Verify that `auth_failure` (HTTP 401/403 from Devin API) is classified as TOOL_DOWN but is NOT auto-retried. This is a special case: the tool is "down" from our perspective (can't create sessions), but retrying won't help because the API key is invalid. Must escalate immediately.

**Why we test this**: If the API key expires or is rotated and someone forgets to update the repo secret, EVERY workflow run will fail with 401. Without special handling, the cron sweep would retry every 15 minutes forever, each time getting 401, each time wasting Actions time and logging noise. Worse: the PR comments would say "auto-retry in 15 min" indefinitely, setting a false expectation.

**Relates to**: Edge Case 14 (TOOL_DOWN sub-categories, auth_failure special case)

**Setup**:
1. Set `DEVIN_API_KEY` repo secret to an invalid/expired key
2. Push vulnerable code to a PR to trigger CodeQL alerts

**Steps**:
1. CodeQL runs, detects alerts
2. Our workflow triggers, health check step tries to validate Devin API key
3. Devin API returns HTTP 401 or 403
4. Verify: health check identifies this as `auth_failure`
5. Verify: workflow does NOT attempt to create any sessions (skip dispatch entirely)
6. Verify: workflow exits red (not green)
7. Check PR comment content
8. Check if cron sweep handles this correctly

**Expected**:
- Health check: "Devin API key invalid (HTTP 401). Sessions cannot be created."
- Workflow exits code 1 (red check)
- PR comment:
  > **Devin Security Review** — Configuration Error
  >
  > Devin API key is invalid or expired. Automatic security fixes are disabled until this is resolved.
  > {N} security alerts detected by CodeQL require attention.
  >
  > **Action required**: Repository admin must update the `DEVIN_API_KEY` secret.
  >
  > CodeQL is still protecting this PR from merging with unresolved vulnerabilities.
- Alert markers: `deferred:ALERT_KEY=RUN:TS:401:tool_down:auth_failure:no_retry`
- The `no_retry` flag means the cron sweep will NOT dispatch retries for this PR

**Worry (infinite retry on bad API key)**: Cron sweep doesn't check for `auth_failure` sub-category and retries every 15 minutes. Each retry: workflow starts, health check fails with 401, posts same "configuration error" comment, exits red. 96 failed runs per day, each consuming ~30 seconds of Actions time. GitHub sends 96 "workflow failed" email notifications. Enterprise admin's inbox flooded.

**Worry (auth_failure confused with rate_limit)**: HTTP 429 (rate limit) and HTTP 401 (auth failure) are both "can't create session" but have completely different remediation. Rate limit: wait and retry. Auth failure: fix the API key. If the workflow doesn't distinguish them, a rate limit gets treated as "configuration error" (developer told to update API key when the key is fine) or an auth failure gets treated as "temporarily at capacity" (developer waits forever for something that will never auto-resolve).

**Worry (API key rotated mid-session)**: Devin API key was valid at health check time, but rotated between health check and session creation. Session creation gets 401. Verify: workflow retries once (could be transient), on second 401 classifies as `auth_failure` and stops.

**Sub-test (key fixed, sweep recovers)**:
1. Start with invalid API key, verify auth_failure state (markers + comment)
2. Admin fixes the API key (updates repo secret)
3. Developer pushes new code to PR (triggers CodeQL, triggers workflow_run)
4. New workflow run: health check passes, sessions created, alerts transition from `deferred:auth_failure:no_retry` to `claimed`
5. Verify: the system fully recovers without needing to manually clear any state
6. Alternative path: admin manually re-runs the failed workflow. Verify: same recovery.

**Sub-test (distinguish 401 vs 403)**:
1. HTTP 401 (Unauthorized): API key is missing or malformed. Message: "API key invalid."
2. HTTP 403 (Forbidden): API key is valid but lacks permissions (e.g., wrong scope). Message: "API key lacks required permissions."
3. Verify: both are `auth_failure` (no auto-retry), but the PR comment message is specific enough for the admin to know which to fix.

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
- [ ] T18: Stuck PR recovery via cron sweep (EC13)
- [ ] T19: CodeQL alerts persist on open PRs (EC13d)
- [ ] T20: Cron sweep detects stuck PRs (EC13 Solution 3)
- [ ] T21: Session accumulation and cleanup (EC12 root cause)
- [ ] T22: TOOL_DOWN vs AI_FAILED classification correctness (EC14)
- [ ] T23: Cron sweep respects failure mode taxonomy (EC14 + EC13)
- [ ] T24: Mixed failure modes on single PR (EC14 UX)
- [ ] T25: Auth failure — non-retryable TOOL_DOWN (EC14 special case)
