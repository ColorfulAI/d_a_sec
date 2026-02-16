# Backlog Security Sweep — Test Specifications

Tests for the backlog workflow (`devin-security-backlog.yml`) and its child batch workflow (`devin-security-batch.yml`). These test cases validate the orchestrator fan-out pattern, streaming PR creation, wave-based processing, cursor-based stateless pickup, session lifecycle management, and all edge cases documented in DESIGN.md.

For PR-triggered workflow tests (TC-A through TC-S), see [PR_triggered_tests.md](./PR_triggered_tests.md).

---

## Test Design Principles

Each test case follows these rules:
1. **Creates the actual situation** — not a mock, not a description. Push real code, trigger real workflows.
2. **States WHY we are testing** — maps to a specific worry or edge case in DESIGN.md.
3. **States what behavior we WANT** — explicit pass/fail criteria.
4. **Calls out what we are MOST WORRIED about** — the failure mode that would be worst in production.
5. **Enterprise-ready bar** — every output must be professional and trustworthy for Fortune 500 clients.

---

## Test Cases

### TC-BL-A: Orchestrator Dispatches Child Workflows (Happy Path)

**Setup**: Seed main with 30 open CodeQL alerts across 3 files. Trigger the backlog workflow manually via `workflow_dispatch`.

**Expected**:
1. Orchestrator fetches all 30 alerts from the CodeQL API
2. Groups alerts into 2 batches (15 each, grouped by file)
3. Dispatches 2 child workflows via `workflow_dispatch` (one per batch)
4. Each child workflow creates exactly 1 Devin session
5. Each child workflow appears as a separate run in GitHub Actions UI
6. Orchestrator polls child statuses every 60s
7. As each child completes, orchestrator creates a PR for that batch
8. 2 PRs created total, each with its own branch (`devin/security-batch-{N}-{timestamp}`)
9. Cursor updated with all 30 alert IDs as processed

**Validates**: Core orchestrator fan-out — the fundamental architecture works end-to-end.

**Production scenario**: Security team onboards a new repo with 30 known vulnerabilities. They trigger the backlog workflow manually and expect it to process everything in one run.

**Worry**: If child dispatch fails silently (GitHub API 422, wrong workflow file name, missing inputs), the orchestrator thinks it dispatched work but nothing happens. Alerts are marked "in progress" in the cursor but no session ever runs.

---

### TC-BL-B: Streaming PR Creation — First PR Before Last Batch Completes

**Setup**: Seed main with 75 alerts (5 batches of 15). Trigger backlog workflow. Monitor PR creation timestamps.

**Expected**:
1. Orchestrator dispatches 5 child workflows simultaneously (fills all 5 slots)
2. Child 1 completes first (~8 min) → PR #1 created immediately
3. Child 3 completes next (~10 min) → PR #3 created immediately
4. Remaining children complete over next 5-10 min → PRs created as each finishes
5. **Time to first PR: ~8-10 minutes** (not waiting for all 5 to finish)
6. All 5 PRs created within ~20 minutes
7. PRs are numbered and titled descriptively: `fix(security): Batch {N} — {count} CodeQL alerts in {files}`

**Validates**: Streaming PR creation — the key design choice that provides faster developer feedback.

**Production scenario**: Security team kicks off backlog sweep at 9 AM. With streaming, the first batch PR is available for review by 9:10 AM. Without streaming, they'd wait until 9:20+ AM to see anything.

**Worry**: If PRs are only created after ALL batches complete, a crash at batch 4 means 0 PRs created despite batches 1-3 being fully fixed. Streaming prevents this data loss.

---

### TC-BL-C: Rolling Window — More Batches Than Concurrent Slots

**Setup**: Seed main with 105 alerts (7 batches of 15). Trigger backlog workflow. The Devin API concurrent session limit is 5.

**Expected**:
1. Orchestrator dispatches batches 1-5 (fills all 5 slots)
2. Batch 1 completes → PR created → batch 6 dispatched into freed slot
3. Batch 3 completes → PR created → batch 7 dispatched into freed slot
4. Remaining batches complete → PRs created
5. **At no point are more than 5 children active simultaneously**
6. All 7 batches processed in a single orchestrator run
7. Total time: ~2 waves × ~10 min = ~20 min (not 7 × 10 min = 70 min sequential)

**Validates**: Rolling window concurrency — the orchestrator correctly manages the 5-slot limit with backfill.

**Production scenario**: Fortune 500 repo with 100+ alerts. The orchestrator must process all of them without hitting the Devin API concurrent session limit or needing a second workflow run.

**Worry**: If the orchestrator dispatches all 7 children at once, children 6-7 get HTTP 429 from the Devin API. The child workflow fails, the session is never created, and those 30 alerts are lost until the next run.

---

### TC-BL-D: Session Reservation — Backlog Doesn't Starve PR Workflows

**Setup**: Trigger backlog workflow (processing 45 alerts = 3 batches). While the backlog is running, push vulnerable code to a PR to trigger the PR workflow.

**Expected**:
1. Orchestrator dispatches 3 children (uses 3 of 5 Devin session slots)
2. PR workflow triggers, needs 1 session (would use 4 of 5 slots)
3. PR workflow creates its session successfully (slot available)
4. Orchestrator's session reservation check (`active >= 3 → pause`) prevents it from using all 5 slots
5. If the orchestrator had used all 5 slots, the PR workflow would have gotten HTTP 429
6. PR workflow completes in <60 seconds
7. Backlog workflow completes normally after PR workflow finishes

**Validates**: Session reservation — the orchestrator self-limits to 3 concurrent children, reserving 2 slots for PR workflows.

**Production scenario**: The backlog runs overnight processing 200 alerts. A developer pushes an urgent hotfix at 3 AM. The PR workflow must not be blocked by the backlog's batch work.

**Worry**: If both workflows compete for the same 5 session slots without coordination, PR workflows get 429s and developers see "security review failed" on their urgent hotfix — destroying trust in the system.

---

### TC-BL-E: Cursor-Based Stateless Pickup

**Setup**: Seed main with 60 alerts. Run the backlog workflow. It processes all 60 alerts (4 batches). Merge 10 new vulnerabilities to main. Run the backlog workflow again.

**Expected**:
1. Run 1: Reads cursor (empty/initial), fetches 60 alerts, creates 4 batches, dispatches children, creates 4 PRs, updates cursor with 60 processed alert IDs
2. Run 2: Reads cursor (60 processed IDs), fetches all open alerts, filters out the 60 already-processed, finds 10 new alerts, creates 1 batch, dispatches 1 child, creates 1 PR
3. Run 2 does NOT re-process any of the 60 alerts from Run 1
4. Cursor after Run 2 shows 70 total processed alert IDs

**Validates**: Stateless pickup — the backlog workflow resumes from where it left off without re-processing.

**Production scenario**: Fortune 500 repo where new vulnerabilities are introduced weekly. Each backlog run should only process NEW alerts, not re-scan the entire history.

**Worry**: If the cursor is lost or not read correctly, the backlog workflow re-processes all 60 alerts, creating duplicate Devin sessions and duplicate PRs for already-fixed issues. This wastes resources and confuses reviewers.

---

### TC-BL-F: Cursor Corruption Recovery

**Setup**: Run the backlog workflow. Manually corrupt the cursor (edit the GitHub issue comment to contain invalid JSON). Run the backlog workflow again.

**Expected**:
1. Run 2 reads cursor → JSON parse fails
2. Orchestrator falls back to "fresh start" mode: fetches ALL open alerts, treats nothing as processed
3. Orchestrator logs a warning: "Cursor corrupted, starting fresh scan"
4. Alerts that were already fixed (closed in CodeQL) are naturally skipped (they won't appear in `state=open` query)
5. Alerts that were fixed but not yet merged (open PRs from Run 1) may be re-processed — this is acceptable as the duplicate session will produce the same fix
6. Cursor is rebuilt from scratch after this run

**Validates**: Fault tolerance — cursor corruption doesn't permanently break the workflow.

**Production scenario**: A misconfigured bot or manual edit corrupts the state comment. The next backlog run must recover gracefully, not crash or loop infinitely.

**Worry**: If cursor corruption causes the orchestrator to enter an infinite loop (e.g., trying to parse, failing, retrying), the workflow runs for 6 hours doing nothing, consuming GitHub Actions minutes.

---

### TC-BL-G: Child Workflow Failure — Devin Session Fails

**Setup**: Seed main with 30 alerts. Trigger backlog workflow. One of the child workflows' Devin sessions fails (e.g., Devin hits `max_acu_limit` timeout before completing fixes).

**Expected**:
1. Orchestrator dispatches 2 children
2. Child 1 completes successfully → PR created
3. Child 2's Devin session fails (`status=failed` or `status=timed_out`)
4. Orchestrator detects child 2 failure via workflow run status check
5. Orchestrator marks child 2's 15 alerts as "retryable" in cursor (unless they've hit max attempts)
6. Orchestrator does NOT create a PR for child 2 (no fixes to show)
7. Next backlog run: reads cursor, sees 15 retryable alerts, creates new batch, dispatches new child
8. If alerts have been retried 2+ times and still fail, they are marked "unfixable" in cursor

**Validates**: Fault tolerance — failed sessions are retried, not permanently lost.

**Production scenario**: A complex codebase causes Devin to exceed its compute budget. The alerts from that batch must be retried in a subsequent run, not silently dropped.

**Worry**: If failed sessions are never retried, the backlog accumulates "stuck" alerts that are neither fixed nor marked unfixable — a silent data loss that only surfaces during an audit.

---

### TC-BL-H: Child Workflow Failure — Stuck Session (>1 Hour)

**Setup**: Trigger backlog workflow. Simulate a child workflow that hangs (Devin session stays in `running` state for >1 hour).

**Expected**:
1. Orchestrator dispatches child, records `dispatched_at` timestamp in cursor
2. Orchestrator polls every 60s — child still running
3. After 60 minutes: orchestrator evicts the stale child from the active set
4. Orchestrator marks that batch's alerts as retryable
5. Orchestrator backfills the freed slot with the next pending batch
6. Cursor updated: stale child's batch moved from "in_progress" to "retryable"

**Validates**: Stale session eviction — the orchestrator doesn't wait forever for a stuck child.

**Production scenario**: A Devin session hangs because the repo is too large to clone, or a network issue prevents the session from progressing. The orchestrator must detect this and move on.

**Worry**: If the orchestrator waits indefinitely for a stuck child, it blocks all subsequent batches. A single stuck session could prevent the entire backlog from being processed.

---

### TC-BL-I: Batching Strategy — Group by File, Cap 15, Backfill

**Setup**: Seed main with alerts distributed across files:
- `auth.py`: 8 alerts
- `api.py`: 6 alerts
- `utils.py`: 4 alerts
- `db.py`: 3 alerts
- `config.py`: 2 alerts

**Expected**:
1. Batch 1: `auth.py` (8) + `api.py` (6) + `utils.py` (1) = 15 alerts
   - Prefer same-file grouping, backfill to reach cap
2. Batch 2: `utils.py` (3) + `db.py` (3) + `config.py` (2) = 8 alerts
   - Remaining alerts in a smaller final batch
3. Each batch gets its own Devin session and PR
4. PR title mentions the primary files: `fix(security): Batch 1 — 15 alerts in auth.py, api.py`

**Validates**: Batching logic — alerts are grouped intelligently for efficient Devin sessions.

**Production scenario**: Enterprise codebase where security debt is concentrated in a few critical files. Grouping by file helps Devin understand the context (one file's patterns) rather than jumping between unrelated files.

**Worry**: If alerts are randomly distributed across batches, Devin spends more time context-switching between files, reducing fix quality. If batches are too small (1-2 alerts), session creation overhead dominates.

---

### TC-BL-J: Concurrency Guard — Only 1 Orchestrator Run at a Time

**Setup**: Trigger the backlog workflow manually. Before it completes, trigger it again (via `workflow_dispatch` or cron).

**Expected**:
1. Run 1 starts processing backlog (dispatching children, polling)
2. Run 2 is queued (NOT cancelling Run 1) due to `concurrency` group with `cancel-in-progress: false`
3. Run 1 completes, updates cursor
4. Run 2 starts, reads updated cursor, continues from where Run 1 left off
5. No duplicate batches created (Run 2 sees Run 1's processed alerts in the cursor)
6. No duplicate PRs created

**Validates**: Concurrency group prevents overlapping orchestrator runs.

**Production scenario**: Cron fires every 6 hours. A previous run is slow (processing 500 alerts with many batches). The next cron fires while it's still running. Without the concurrency guard, both runs process the same alerts → duplicate sessions → duplicate PRs → merge conflicts.

**Worry**: If `cancel-in-progress: true` were used instead of `false`, the second run would cancel the first, potentially abandoning in-progress children. Those children's Devin sessions would finish but their results would never be collected — wasted compute and lost fixes.

---

### TC-BL-K: Internal Retry — Devin Gets 2 Attempts Per Alert Inside Session

**Setup**: Seed main with an alert where the first fix attempt won't satisfy CodeQL (e.g., a taint flow through `urlparse()` that requires a non-obvious fix pattern).

**Expected**:
1. Child workflow creates 1 Devin session for the batch
2. Inside the session, Devin:
   a. Applies fix attempt 1
   b. Runs CodeQL CLI locally → alert still present
   c. Revises fix (attempt 2)
   d. Runs CodeQL CLI → alert resolved (or skipped if still present)
3. Only 1 session created for this batch (not 2 separate sessions)
4. If attempt 2 also fails, Devin skips the alert (does NOT commit a broken fix)
5. The child workflow reports which alerts were fixed and which were skipped

**Validates**: Internal retry loop works inside the session. Devin gets 2 real attempts per alert within 1 session. No excessive session creation.

**Worry**: Without internal retry, a failed fix requires a new session (expensive) or a new workflow run (slow). The internal retry gives Devin a second chance immediately, within the same context.

---

### TC-BL-L: Unfixable Alerts — Circuit Breaker Across Runs

**Setup**: Seed main with an alert that CodeQL will always flag regardless of fix attempts (e.g., a fundamental taint flow pattern). Run backlog workflow twice.

**Expected**:
1. Run 1: Child session tries to fix alert → attempt 1 fails → attempt 2 fails → alert skipped
2. Run 1 cursor: alert marked as "attempt 1 complete, skipped"
3. Run 2: Reads cursor, sees alert was skipped once before, creates new session
4. Run 2 child: attempt 1 fails → attempt 2 fails → alert skipped again
5. Run 2 cursor: alert moved to `unfixable_alert_ids` (2 session-level failures = unfixable)
6. Run 3: Reads cursor, skips this alert entirely (it's in unfixable set)
7. No further sessions ever created for this alert

**Validates**: Cross-run circuit breaker — unfixable alerts are eventually catalogued and excluded from future processing.

**Production scenario**: Enterprise codebase has 20 alerts that are architectural issues (e.g., custom auth patterns that CodeQL always flags). After 2 backlog runs, these are permanently marked unfixable and reported for manual review. They never waste Devin sessions again.

**Worry**: Without the circuit breaker, every backlog run creates new sessions for the same unfixable alerts, burning compute credits indefinitely.

---

### TC-BL-M: PR per Batch — Independent Review and Merge

**Setup**: Seed main with 45 alerts (3 batches). Trigger backlog workflow. All 3 batches succeed.

**Expected**:
1. 3 PRs created, each on its own branch:
   - `devin/security-batch-1-{timestamp}`
   - `devin/security-batch-2-{timestamp}`
   - `devin/security-batch-3-{timestamp}`
2. Each PR has:
   - Alert table showing which alerts were fixed
   - Devin session link
   - Files changed (scoped to that batch's files)
3. PRs can be reviewed and merged independently
4. Merging PR #1 does not cause merge conflicts in PR #2 (different files)
5. If same file appears in 2 batches (edge case), merge order matters but each PR is still valid

**Validates**: 1 PR per batch — the client's explicit requirement ("create a PR for each batch").

**Production scenario**: Security team wants to review and approve fixes incrementally. Critical-severity batch can be fast-tracked while lower-severity batches go through normal review.

**Worry**: If all fixes go into 1 PR, a single bad fix blocks all other fixes from being merged. With 1 PR per batch, a bad fix in batch 3 doesn't block batches 1 and 2.

---

### TC-BL-N: Large Backlog — 500 Alerts in Single Run

**Setup**: Seed main with 500 open CodeQL alerts across 50 files. Trigger backlog workflow.

**Expected**:
1. Orchestrator groups into 34 batches (15 alerts each, last batch has 5)
2. Dispatches 5 children initially (fills slots)
3. Rolling window processes all 34 batches over ~7 waves
4. Total time: ~70 minutes (34 ÷ 5 = 7 waves × 10 min)
5. 34 PRs created (streamed as each batch completes)
6. First PR available at ~10 min, last PR at ~70 min
7. Orchestrator stays well within 6-hour GitHub Actions timeout
8. Cursor updated with all 500 alert IDs

**Validates**: Scale — the system handles a large backlog in a single run.

**Production scenario**: Fortune 500 company enables CodeQL on a legacy codebase for the first time. 500+ alerts surface immediately. The backlog workflow must handle all of them without manual intervention.

**Worry**: At 34 batches, the orchestrator makes ~34 dispatch API calls + ~240 status polling calls (34 batches × ~7 polls each). Must stay within GitHub API rate limits (5000 req/hr for PATs, 1000 req/hr for workflow dispatch).

---

### TC-BL-O: Massive Backlog — 1000+ Alerts with Safety Valve

**Setup**: Seed main with 1000+ open CodeQL alerts. Trigger backlog workflow. Monitor for timeout safety valve.

**Expected**:
1. Orchestrator groups into ~67 batches
2. Processes via rolling window (5 slots, ~10 min each)
3. Total time: ~140 minutes (67 ÷ 5 = 14 waves × 10 min)
4. Still within 6-hour limit — no safety valve triggered
5. If processing is slower than expected (15 min/batch), total would be ~200 min — still safe
6. If approaching 5.5 hours, orchestrator saves cursor and exits cleanly
7. Next cron run picks up from where it left off

**Validates**: Safety valve — the orchestrator doesn't exceed GitHub Actions timeout even for massive backlogs.

**Production scenario**: Monorepo with 20+ services and thousands of accumulated alerts. One run might not finish, but the system recovers gracefully.

**Worry**: If the orchestrator exceeds 6 hours, GitHub kills the job. Any in-progress children continue running but their results are never collected. The cursor is not updated. The next run re-processes everything, creating duplicate sessions for already-dispatched batches.

---

### TC-BL-P: Concurrent PRs + Backlog — No Session Explosion

**Setup**: Open 20 PRs simultaneously (each introducing 1 new vulnerability). While all 20 PR workflows are running, also trigger the backlog workflow.

**Expected**:
1. Each PR workflow creates exactly 1 session (20 total session attempts for PR workflows)
2. PR workflows do NOT create sessions for pre-existing alerts
3. Backlog orchestrator self-limits to 3 concurrent children (reserving 2 slots for PR workflows)
4. Total concurrent Devin sessions: ≤5 at any time (3 backlog + 2 PR, or 5 PR with backlog paused)
5. With exponential backoff, all 20 PRs eventually get their session
6. Compare to old architecture: 20 PRs × 4 pre-existing sessions = 80+ attempts → 41% failure rate

**Validates**: The split-trigger architecture eliminates session explosion under concurrent load.

**Production scenario**: Release day — 20 developers merge feature branches within 30 minutes. Under the old architecture, this created 400+ session attempts. With the split, it creates 20 + ~3 (backlog) = 23 total.

**Worry**: Without the split, the stress test showed 41% workflow failure rate with 99 PRs. The split should reduce this to near 0% for PR workflows while the backlog processes pre-existing alerts at its own pace.

---

### TC-BL-Q: Sub-Workflow Dispatch Failure — GitHub API Error

**Setup**: Trigger backlog workflow. Simulate a GitHub API failure on child dispatch (e.g., by temporarily revoking workflow dispatch permissions or hitting the workflow dispatch rate limit).

**Expected**:
1. Orchestrator tries to dispatch child workflow → API returns 4xx/5xx
2. Orchestrator retries with exponential backoff (3 attempts)
3. If all retries fail, batch stays in `pending_batches`
4. Orchestrator continues dispatching other batches
5. Cursor updated: failed batch marked as "dispatch_failed"
6. Next backlog run picks up the failed batch and retries dispatch

**Validates**: Dispatch failure resilience — the orchestrator handles GitHub API errors gracefully.

**Production scenario**: GitHub has a brief API outage (happens a few times per year). The backlog workflow must not permanently lose batches because of a transient GitHub API issue.

**Worry**: If dispatch failure causes the orchestrator to crash (unhandled exception), all subsequent batches are lost. The orchestrator must catch dispatch errors and continue.

---

### TC-BL-R: Rate Limiting Under Load — Exponential Backoff

**Setup**: Trigger backlog workflow with 75 alerts (5 batches). Simultaneously trigger 5 PR workflows. The Devin API concurrent session limit (5) will be fully occupied by PR sessions.

**Expected**:
1. PR workflows take all 5 session slots
2. Backlog orchestrator tries to dispatch children → children get HTTP 429 from Devin API
3. Orchestrator's session reservation check detects 5 active sessions → waits 120s
4. After PR sessions complete, orchestrator dispatches children into freed slots
5. Exponential backoff: 120s → 240s → 480s (3 retries)
6. All 5 batches eventually process successfully
7. No permanent failure — just delayed start

**Validates**: Rate limiting resilience with the backlog workflow deferring to PR workflows.

**Production scenario**: Monday morning — 10 developers push code within 15 minutes. All PR workflows fire. The backlog cron also fires. The backlog must gracefully defer to PR workflows.

**Worry**: If the backlog workflow and PR workflows compete aggressively for sessions, PR developers see "security review failed" errors. The backlog must always yield to PR workflows.

---

### TC-BL-S: PR Comment Cross-Links to Backlog PRs

**Setup**: Open a PR on a codebase with 50 pre-existing alerts. Run the backlog workflow so it creates batch fix PRs. Then check the PR workflow's comment.

**Expected**:
1. PR workflow detects pre-existing alerts but does NOT create sessions for them
2. PR comment includes: "50 pre-existing alerts on main are handled separately. See Security Backlog PRs for progress: [Batch 1 PR #X], [Batch 2 PR #Y], ..."
3. Links point to actual backlog PRs (not dead links)
4. If no backlog PRs exist yet, the comment says: "These will be addressed by the next scheduled backlog run."
5. As backlog PRs are merged and alerts are fixed, the count in subsequent PR comments decreases

**Validates**: Developer experience — clear communication about what's being handled and where.

**Production scenario**: Developer opens a PR, sees "50 pre-existing alerts on main" in the comment. Without cross-links, they think the tool found 50 issues and isn't doing anything about them. With cross-links, they see the backlog PRs with 30 already fixed.

**Worry**: If the PR comment just says "pre-existing alerts exist" without context, developers lose confidence in the security workflow and start ignoring it entirely.

---

### TC-BL-T: Orchestrator Crash Recovery — Mid-Run Failure

**Setup**: Trigger backlog workflow. After 3 of 7 batches have been dispatched and 1 has completed (1 PR created), kill the orchestrator (cancel the GitHub Actions run manually).

**Expected**:
1. The 1 completed batch already has its PR created (streaming — no data loss)
2. The 2 in-progress children continue running (they're independent workflow runs)
3. Cursor has state from last successful update (shows 3 dispatched, 1 completed)
4. Next backlog run: reads cursor, checks in-progress children's status, collects results, creates PRs for completed children, dispatches remaining batches
5. No duplicate PRs for the batch that already had a PR
6. No duplicate sessions for batches that already ran

**Validates**: Crash recovery — the streaming + cursor design means partial progress is never lost.

**Production scenario**: GitHub Actions runner dies mid-execution (infrastructure issue). The next cron run must seamlessly recover without duplicating work.

**Worry**: Without streaming, a crash at batch 4 means 0 PRs created despite batches 1-3 being fully fixed. With streaming, 1-3 already have their PRs. Without cursor, the next run re-processes everything from scratch.

---

### TC-BL-U: PR Naming and Content Quality

**Setup**: Seed main with 15 alerts: 5 `py/sql-injection` in `db.py`, 5 `py/reflective-xss` in `api.py`, 5 `py/command-line-injection` in `cli.py`. Trigger backlog workflow.

**Expected**:
1. Batch 1 PR:
   - Branch: `devin/security-batch-1-{timestamp}`
   - Title: `fix(security): Batch 1 — 15 CodeQL alerts in db.py, api.py, cli.py`
   - Body contains:
     - Alert table: rule ID, file, line, status (fixed/skipped)
     - Devin session link
     - Which CodeQL rules were addressed
     - Commit-per-alert granularity (5 commits for db.py alerts, 5 for api.py, etc.)
2. PR is reviewable by a security engineer without additional context
3. Each commit message references the specific alert: `fix(security): [py/sql-injection] parameterize query in db.py:42`

**Validates**: PR quality — the output is enterprise-ready and professionally formatted.

**Production scenario**: Security team reviews batch PRs. Each PR must be self-contained with enough context to understand what was fixed and why.

**Worry**: If PR descriptions are vague ("fixed security issues") or commits are squashed into one giant commit, reviewers can't assess individual fixes. A bad fix buried in a 15-file commit is hard to identify.

---

### TC-BL-V: Devin Session Lifecycle — No Session Reuse After Completion

**Setup**: Run backlog workflow. Batch 1 completes. Batch 6 is dispatched to the freed slot. Verify that batch 6 creates a NEW Devin session, not reusing batch 1's completed session.

**Expected**:
1. Batch 1 child creates session `sess_aaa`, completes
2. Batch 6 child creates session `sess_bbb` (new session, new ID)
3. `sess_aaa` is never referenced again after completion
4. No `POST /v1/sessions/{sess_aaa}/message` calls after `sess_aaa` status is `finished`
5. `sess_bbb` gets its own fresh environment (new clone, new context)

**Validates**: Session lifecycle — completed sessions are never reused. This is how the Devin API is designed.

**Production scenario**: If we accidentally tried to reuse a completed session (e.g., send a message to it), the API would either error or silently succeed with no effect — both bad outcomes.

**Worry**: Session reuse would mean batch 6's fixes are applied in batch 1's environment, which has batch 1's changes already committed. This could cause incorrect diffs, wrong base branches, or conflicting changes.

---

### TC-BL-W: Backlog Workflow Trigger Modes (Cron + Manual)

**Setup**: Configure the backlog workflow with `schedule: cron('0 */6 * * *')` (every 6 hours) and `workflow_dispatch` (manual). Verify both trigger modes work.

**Expected**:
1. Manual trigger via `workflow_dispatch`: Orchestrator starts, processes backlog, creates PRs
2. Cron trigger: Same behavior, fired automatically at scheduled time
3. `workflow_dispatch` accepts optional inputs: `max_batches` (limit processing), `dry_run` (log what would be done without dispatching children)
4. Both triggers use the same cursor (shared state)
5. Manual trigger during a cron run: queued due to concurrency group, runs after cron completes

**Validates**: Both trigger modes work correctly with shared state.

**Production scenario**: Security team wants to run the backlog on-demand after enabling CodeQL on a new repo (manual), and also on a regular schedule for ongoing maintenance (cron).

**Worry**: If `workflow_dispatch` uses a different code path than `schedule`, manual runs might skip cursor reading or use different batching logic, causing inconsistent behavior.

---

### TC-BL-X: PR Review Load Management — Many PRs from Large Backlog

**Setup**: Seed main with 500 alerts (34 batches). Trigger backlog workflow. All batches succeed.

**Expected**:
1. 34 PRs created over ~70 minutes
2. PRs are labeled with severity: `security-critical`, `security-high`, `security-medium`
3. PR titles include batch number and primary rule: `fix(security): Batch 3 — py/sql-injection in db.py`
4. PRs can be filtered and prioritized by label
5. Team can merge critical PRs first, defer medium PRs

**Validates**: Review load management — 34 PRs is a lot, but they're organized for efficient triage.

**Production scenario**: Security team enables CodeQL on a legacy monorepo. 34 PRs appear. Without labels and clear titles, this is overwhelming. With proper organization, the team can triage: "merge all critical PRs today, review high PRs this week, defer medium PRs."

**Worry**: If all 34 PRs have generic titles ("security fix"), the team can't prioritize. If PRs lack context, reviewers waste time understanding what each PR does.

---

### TC-BL-Y: Edge Case — Zero Alerts on Main

**Setup**: Trigger backlog workflow on a repo with 0 open CodeQL alerts.

**Expected**:
1. Orchestrator fetches alerts → 0 results
2. No batches created, no children dispatched
3. Cursor updated: `total_backlog: 0`
4. Workflow completes successfully with a log message: "No open alerts to process"
5. No PRs created
6. Exit code: 0

**Validates**: Clean exit when there's nothing to do.

**Production scenario**: After the backlog is fully cleared, the cron keeps running. It should complete instantly without errors, not crash because it expected at least 1 alert.

**Worry**: If the orchestrator doesn't handle the empty case, it might crash on "divide by zero" (0 alerts ÷ 15 per batch), or try to dispatch a batch with 0 alerts.

---

### TC-BL-Z: Edge Case — All Alerts Already Unfixable

**Setup**: Run the backlog workflow multiple times until all remaining alerts are marked unfixable (each has been retried 2+ times). Run the backlog workflow one more time.

**Expected**:
1. Orchestrator reads cursor → all alert IDs are in `unfixable_alert_ids`
2. Fetches open alerts → filters out all unfixable ones → 0 remaining
3. No batches created, no children dispatched
4. Cursor unchanged (no new work done)
5. Log message: "All 15 open alerts are marked unfixable. No new work to dispatch."
6. The PR comment from the PR workflow (if applicable) shows: "15 pre-existing alerts on main require manual review. See unfixable alerts report."

**Validates**: The system gracefully stops when all remaining work requires human intervention.

**Production scenario**: After clearing 485 of 500 alerts, the remaining 15 are architectural issues that CodeQL always flags. The backlog workflow should recognize this and stop wasting compute on them.

**Worry**: Without the unfixable check, the backlog creates infinite sessions for the same 15 unfixable alerts, burning Devin credits every 6 hours forever.

---

## Integration with PR-Triggered Tests

The following test cases from [PR_triggered_tests.md](./PR_triggered_tests.md) remain relevant to the backlog workflow and should be validated in the backlog context:

| PR Test | Backlog Relevance | Adaptation |
|---------|-------------------|------------|
| TC-G (Happy Path Fix) | Core fix quality applies to batch sessions too | Validate Devin produces correct fixes inside batch sessions |
| TC-H (Internal Retry) | Same internal retry loop inside batch sessions | Verify 2-attempt CodeQL loop works for backlog alerts |
| TC-I (Unfixable After 2 Attempts) | Circuit breaker feeds into cursor's unfixable set | Verify skipped alerts are correctly marked in cursor |
| TC-K (Mixed Fix Results) | Batches will have mixed outcomes | Verify partial fixes are committed, skipped alerts tracked |
| TC-L (Label Creation) | Backlog PRs may need labels too | Verify batch PRs get severity labels |
| TC-R (Stress Test) | Session explosion prevention | Verify backlog + 99 PRs doesn't cause 429 cascade |
| TC-S (Rate Limit Resilience) | Backlog must handle 429s gracefully | Verify orchestrator's session reservation prevents 429s |

---

## Known Limitations

### KL-1: Child Workflow Output Collection
GitHub Actions `workflow_dispatch` does not natively return outputs to the caller. The orchestrator must poll the child's workflow run artifacts or check results via the GitHub API. This adds latency to result collection.

### KL-2: Maximum Workflow Dispatch Rate
GitHub limits `workflow_dispatch` calls. For very large backlogs (100+ batches), dispatch calls may be throttled. The orchestrator should batch dispatch calls with small delays between them.

### KL-3: Cursor Size Limits
GitHub issue comment bodies have a 65536 character limit. With 1000+ processed alert IDs, the cursor JSON could exceed this limit. For large backlogs, consider using a repository variable or splitting the cursor across multiple comments.

---

## How to Run Tests

### Triggering the backlog workflow:

```bash
# Manual trigger via workflow_dispatch
curl -s -X POST \
  -H "Authorization: token $GH_PAT" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/$REPO/actions/workflows/devin-security-backlog.yml/dispatches" \
  -d '{"ref": "main"}'

# Check workflow run status
curl -s -H "Authorization: token $GH_PAT" \
  "https://api.github.com/repos/$REPO/actions/runs?workflow_id=devin-security-backlog.yml&per_page=5"
```

### Checking cursor state:

```bash
# Read the backlog state from the tracking issue
curl -s -H "Authorization: token $GH_PAT" \
  "https://api.github.com/repos/$REPO/issues/$TRACKING_ISSUE/comments" \
  | jq '.[] | select(.body | contains("backlog-cursor"))'
```

### Checking Devin session status:

```bash
# Check a specific session
curl -s -H "Authorization: Bearer $DEVIN_API_KEY" \
  "https://api.devin.ai/v1/session/$SESSION_ID"

# List active sessions
curl -s -H "Authorization: Bearer $DEVIN_API_KEY" \
  "https://api.devin.ai/v1/sessions?status=running"
```

### Checking batch PRs:

```bash
# List all security batch PRs
curl -s -H "Authorization: token $GH_PAT" \
  "https://api.github.com/repos/$REPO/pulls?state=open&head=devin/security-batch"
```

---

## Regression Tests (Bugs Found During Testing)

### TC-BL-REG-1: Partial-File Batching Must Not Split Files (Bug #8)

**Setup**: Seed main with alerts distributed as:
- `user_service.py`: 5 alerts (3 XSS, 1 SQL injection, 1 command injection)
- `template_engine.py`: 4 alerts (2 XSS, 2 unsafe deserialization)
- `admin_handler.py`: 2 alerts

Trigger backlog workflow with `alerts_per_batch=6`.

**Expected**:
1. Batch 1: ALL 5 alerts in `user_service.py` (never split)
2. Batch 2: ALL 4 alerts in `template_engine.py` + 2 in `admin_handler.py` = 6 alerts
3. No batch contains a partial set of a file's alerts
4. When Devin fixes all alerts in `user_service.py`, the PR modifies only that file and CodeQL finds 0 remaining alerts → PASS
5. If a file has more alerts than the cap (e.g., 20 alerts in one file), that file gets its own batch (cap is soft limit)

**Validates**: Bug #8 fix — all alerts per file stay in the same batch so CodeQL PR checks pass.

**Production scenario**: Enterprise repo where `auth.py` has 15 different vulnerability types. The old algorithm would put 15 in batch 1 and backfill from other files. If only 10 of the 15 are fixable, batch 1's PR still modifies `auth.py` and CodeQL reports the 5 unfixed ones as failures. With the fix, all 15 go together and the PR either cleans the file completely or reports a clear subset.

**Worry**: If the batching algorithm silently splits a file (e.g., due to an off-by-one in the packing logic), every batch PR touching that file will fail CodeQL. This is the #1 trust-destroying bug for enterprise clients — "your automated fix PRs all fail CI" is an immediate uninstall.

---

### TC-BL-REG-2: Suspended Session Handled Gracefully (Bug #5)

**Setup**: Trigger backlog workflow with a batch that creates a Devin session. If the session transitions to `suspended` status (not controllable, but observable).

**Expected**:
1. Polling loop detects `suspended` status
2. Logs warning: "Session is suspended — may need manual intervention"
3. Exits polling with `completed=true`, `status=suspended`
4. Workflow does NOT crash with jq parse error
5. Collect-results step handles the non-finished status gracefully

**Validates**: Bug #5 fix — `suspended` status is handled in the polling `case` statement.

**Worry**: If `suspended` is not handled, the polling loop continues for 7+ wasted polls until the API returns non-JSON, causing a jq crash (bug #6). This is a cascading failure: one unhandled status → wasted time → API transient → crash.

---

### TC-BL-REG-3: Non-JSON API Response Doesn't Crash Polling (Bug #6)

**Setup**: Trigger backlog workflow. During polling, if the Devin API returns a non-JSON response (HTML error page, rate limit response, empty body).

**Expected**:
1. `jq empty` guard detects non-JSON response
2. Logs: "API returned non-JSON response (N bytes). Retrying..."
3. Continues to next poll cycle (does NOT exit with error)
4. On subsequent polls, if API recovers, polling continues normally

**Validates**: Bug #6 fix — JSON validation guard before jq parsing.

**Worry**: Without the guard, ANY transient API issue (network hiccup, rate limit HTML page, 502 gateway error) crashes the entire batch workflow. At Fortune 500 scale with 50+ batch workflows running, a brief API instability would cascade-fail all active batches.

---

### TC-BL-REG-4: Operator Precedence in Collect-Results (Bug #7)

**Setup**: Trigger backlog workflow. A batch's Devin session completes with `status=stopped` but no branch was created (Devin couldn't clone or hit an error before pushing).

**Expected**:
1. Collect-results step evaluates: `BRANCH_NAME` is empty AND `STATUS` is `stopped`
2. The conditional `[ -n "$BRANCH_NAME" ] && { [ "$STATUS" = "finished" ] || [ "$STATUS" = "stopped" ]; }` correctly short-circuits at the `BRANCH_NAME` check
3. Does NOT enter the commit-counting block
4. Reports 0 fixed alerts (correct — no branch means no fixes)

**Validates**: Bug #7 fix — operator precedence is correct with explicit grouping.

**Worry**: The old code `&& finished || stopped` would enter the commit-counting block when status=stopped even without a branch, then query `https://api.github.com/repos/.../compare/main...` with an empty branch name, getting a 404 or unexpected response.

---

## Unfixable Alert → Human Review Tests

### TC-BL-REG-5: Unfixable Alerts Identified by Re-Querying CodeQL

**Setup**: Seed main with alerts in files that contain deliberately unfixable patterns (e.g., a SQL injection that requires architectural refactoring, not a simple parameterization). Trigger backlog workflow with max_batches=1.

**Expected**:
1. Devin session completes (finished or stopped)
2. Batch workflow's collect-results step re-queries CodeQL API for each alert ID
3. Alerts that are still `state=open` are listed in `unfixable_alert_ids` output
4. Alerts that flipped to `state=fixed` are listed in `fixed_alert_ids` output
5. The `batch_result.json` artifact contains both lists with specific alert IDs
6. The batch workflow summary shows "Alerts Requiring Human Review" section with clickable links

**Validates**: The batch workflow uses CodeQL API as source of truth (not commit counting) to determine which alerts were actually fixed.

**Production scenario**: A Fortune 500 repo has 50 alerts. Devin fixes 40 but can't fix 10 (complex architectural issues). Without per-alert verification, the orchestrator marks all 50 as "processed" and no one knows about the 10. With this fix, the 10 are explicitly flagged for human review.

**Worry**: If the CodeQL API returns stale state (fix not yet reflected because PR not merged), alerts may be incorrectly classified as unfixable. This is a conservative error — better to over-report than miss genuinely unfixable alerts. The next orchestrator run (after PR merge) will re-classify correctly.

---

### TC-BL-REG-6: Orchestrator Categorizes Fixed vs Unfixable in Cursor

**Setup**: Run the orchestrator with a batch that has mixed results (some fixed, some unfixable). Check the tracking issue cursor after completion.

**Expected**:
1. Orchestrator downloads batch result artifact from child workflow
2. `fixed_alert_ids` from artifact → added to `cursor.processed_alert_ids`
3. `unfixable_alert_ids` from artifact → added to `cursor.unfixable_alert_ids`
4. Cursor JSON on tracking issue shows both lists with correct alert IDs
5. `total_fixed` and `total_unfixable` counters are accurate
6. On next orchestrator run, both fixed and unfixable alerts are skipped (not re-dispatched)

**Validates**: The orchestrator properly categorizes alerts based on batch results, not just batch success/failure.

**Production scenario**: After 3 orchestrator runs, the cursor shows: "150 processed, 135 fixed, 15 unfixable." A security manager can immediately see the remediation progress and know exactly which 15 alerts need manual attention.

**Worry**: If artifact download fails (GitHub API issue, permissions), the orchestrator falls back to marking all alerts as "processed" — losing the fixed/unfixable distinction. The fallback is safe but not ideal. Check that the warning is logged clearly.

---

### TC-BL-REG-7: Tracking Issue Gets Human Review Comment

**Setup**: Run the orchestrator with alerts that result in some unfixable. Check the tracking issue after completion.

**Expected**:
1. Orchestrator posts a "⚠ Alerts Requiring Human Review" comment on the tracking issue
2. Comment contains a table with: alert ID, link to CodeQL alert, "Manual review" action
3. The `devin:human-review-needed` label is applied to the tracking issue
4. The label is created with correct color and description if it doesn't exist
5. The label check uses GET before POST (no 422 errors on repeat runs)
6. Comment includes a link back to the orchestrator run for context

**Validates**: Unfixable alerts are surfaced to humans through GitHub's native notification system (issue comment + label → email/Slack notifications for watchers).

**Production scenario**: An enterprise security team has a Slack integration that triggers on `devin:human-review-needed` label. When the orchestrator flags unfixable alerts, the team's #security-alerts Slack channel gets an immediate notification with links to the specific alerts. No manual checking of workflow runs needed.

**Worry**: If the comment is posted but the label isn't applied (or vice versa), the notification pipeline is broken. Both must succeed for the full notification flow. Also: if the tracking issue doesn't exist (deleted or wrong number), the comment post fails silently. The orchestrator should handle this gracefully.

---

### TC-BL-REG-8: Unfixable Alerts Skipped on Next Run

**Setup**: Run the orchestrator once (some alerts become unfixable). Run the orchestrator again without changing any code.

**Expected**:
1. Second run reads cursor from tracking issue
2. Alerts in `unfixable_alert_ids` are skipped during alert filtering: "Unfixable (skipped): N"
3. Alerts in `processed_alert_ids` are also skipped
4. Only new/unprocessed alerts (if any) are batched
5. If all alerts are processed or unfixable, the orchestrator exits with "No new alerts to process"
6. No new Devin sessions are created for unfixable alerts

**Validates**: The cursor's `unfixable_alert_ids` list actually prevents re-processing. An unfixable alert is never sent to Devin again.

**Production scenario**: A cron-triggered orchestrator runs every 6 hours. If alert #217 was unfixable on the first run, it must not consume a Devin session slot on subsequent runs. With 5 concurrent session slots and potentially hundreds of new alerts, wasting a slot on a known-unfixable alert delays the entire backlog.

**Worry**: If the cursor parsing has a bug (e.g., string vs int comparison for alert IDs), unfixable alerts might not be recognized and get re-dispatched repeatedly. Each re-dispatch wastes a Devin session (~10 min, ~$X in ACU costs) for a guaranteed failure.

---

### TC-BL-REG-9: Session Failure Marks All Batch Alerts as Unfixable

**Setup**: Trigger a batch workflow where the Devin session fails entirely (status=failed or error — e.g., Devin can't clone the repo, hits an internal error).

**Expected**:
1. Session status is `failed` or `error`
2. Collect-results step marks ALL alerts in the batch as unfixable (conservative)
3. `unfixable_alert_ids` = full list of batch alert IDs
4. `fixed_alert_ids` = empty
5. The batch workflow still uploads the result artifact (so orchestrator can read it)
6. Tracking issue gets the "human review" comment for ALL affected alerts

**Validates**: Complete session failures are handled conservatively — all alerts are flagged for human review rather than silently disappearing.

**Production scenario**: Devin's API has a transient outage. A batch of 15 alerts gets a session that immediately fails. Without this handling, those 15 alerts are marked "processed" and never retried. With this handling, they're marked "unfixable" with a clear reason, and a human can decide to re-run after the outage is resolved.

**Worry**: If session failure causes the collect-results step to also fail (cascading error), no artifact is uploaded, and the orchestrator's fallback marks everything as "processed" — losing the unfixable distinction entirely. The collect-results step must have `if: always()` to run even on prior step failures.

---

### TC-BL-REG-10: Orchestrator Resolves Child Run ID via Timestamp Matching

**Setup**: Trigger the orchestrator with `max_batches=2` so it dispatches 2 child workflows in quick succession. Monitor the orchestrator logs for "timestamp match" messages.

**Expected**:
1. Orchestrator dispatches Batch 1, records `dispatch_time_str`
2. Orchestrator dispatches Batch 2, records `dispatch_time_str` (5+ seconds later due to `time.sleep(5)`)
3. On the next poll cycle, orchestrator queries batch workflow runs with `created>=` filter
4. Each child run is matched to its batch by timestamp ordering (first unmatched run whose `created_at >= dispatch_time`)
5. The `already_matched` set prevents the same run from being assigned to both batches
6. Logs show `"Resolved Batch N -> run XXXXX (timestamp match: created=... >= dispatched=...)"` for each child
7. Orchestrator correctly polls both children and processes their results

**Validates**: Bug #10 fix — the orchestrator can resolve child workflow run IDs without relying on metadata that doesn't exist in `workflow_dispatch` runs.

**Production scenario**: With 5 concurrent batches dispatched within seconds of each other, the orchestrator must correctly pair each dispatch to its corresponding child run. If run IDs are swapped (Batch 1 gets Batch 2's run), the orchestrator will track the wrong session status and may mark alerts as processed before they're actually done.

**Worry**: If two dispatches happen within the same second (e.g., the 5s sleep is removed or GitHub Actions queues them), timestamp matching may swap which run is assigned to which batch. Since each child receives its batch details as workflow inputs (not from run metadata), the swap is functionally harmless — but it would confuse debugging because log messages would show the wrong batch-to-run mapping.

---

### TC-BL-REG-11: Orchestrator Handles Stale Code in Child Workflow

**Setup**: Trigger the orchestrator from main. While the child workflow is running, merge a code change to the batch workflow on main. Check which version of the batch workflow code the child uses.

**Expected**:
1. Child workflow uses the code from the commit that was on main when it was dispatched (not the updated code)
2. The orchestrator still correctly processes the child's results
3. If the child uses old code that lacks `fixed_alert_ids`/`unfixable_alert_ids` in its result artifact, the orchestrator falls back to marking all alerts as "processed"
4. The next orchestrator run (after the code update) will dispatch new children that use the updated code

**Validates**: GitHub Actions caches workflow files at dispatch time. Code changes merged after dispatch don't affect running children.

**Production scenario**: A CI/CD team deploys an updated batch workflow while a backlog sweep is in progress. The currently-running children should complete with the old code (no mid-flight changes), and only subsequent dispatches should pick up the new code.

**Worry**: If the orchestrator expects fields in the batch result artifact that the old child code doesn't produce, it will crash when trying to parse the artifact. The orchestrator must handle missing fields gracefully (fallback to treating all alerts as "processed" rather than crashing).

---

### TC-BL-REG-12: Python Stdout Unbuffered in Heredoc Mode (Bug #11)

**Setup**: Trigger the orchestrator workflow. Cancel it after 30 seconds (before the first poll completes). Check the workflow logs for the cancelled run.

**Expected**:
1. Log output appears in real-time (each `print()` shows immediately, not buffered)
2. After cancellation, ALL print statements executed before cancellation are visible in the logs
3. The `PYTHONUNBUFFERED=1` env var is set in the workflow step
4. `sys.stdout.reconfigure(line_buffering=True)` is called at the top of the Python heredoc

**Validates**: Bug #11 fix — Python's stdout is fully buffered in non-TTY (heredoc) mode. Without this fix, cancelling a long-running orchestrator loses ALL diagnostic output.

**Production scenario**: An operator triggers the backlog sweep, sees it running for 20 minutes with zero output, and cancels it. Without unbuffered stdout, they get zero information about what happened. With the fix, they see exactly which step the orchestrator reached before cancellation.

**Worry**: If `PYTHONUNBUFFERED=1` is removed or `sys.stdout.reconfigure()` is deleted during a refactor, the orchestrator reverts to silent mode. Every future debugging session becomes blind.

---

### TC-BL-REG-13: HTTP Timeouts on All API Calls (Bug #12)

**Setup**: Trigger the orchestrator workflow. Inspect the workflow YAML to verify every `urllib.request.urlopen()` call has `timeout=HTTP_TIMEOUT`.

**Expected**:
1. Every `urlopen()` call in both orchestrator and batch workflows has `timeout=HTTP_TIMEOUT`
2. `HTTP_TIMEOUT` is defined as 30 seconds
3. If the Devin API or GitHub API hangs for >30 seconds, a `socket.timeout` exception is raised
4. The exception is caught and logged (not silently swallowed)
5. The orchestrator continues operating (retries or marks the batch as failed) instead of blocking forever

**Validates**: Bug #12 fix — `urllib.request.urlopen()` defaults to infinite timeout. A single hung API call blocks the entire orchestrator indefinitely.

**Production scenario**: The Devin API experiences a partial outage (responds to health checks but hangs on session creation). Without timeouts, the orchestrator blocks forever on the first API call. With 30s timeout, the orchestrator detects the hang, logs it, and either retries or moves on.

**Worry**: A new `urlopen()` call added during a feature update might omit the `timeout` parameter, reintroducing the infinite-hang vulnerability. Code review must check for this.

---

### TC-BL-REG-14: gh_api Handles 204 No Content Responses (Bug #13)

**Setup**: Trigger the orchestrator workflow with `max_batches=1`. Check the logs for the dispatch step. Verify the `dispatch_child()` function returns `True` (not `False`).

**Expected**:
1. `gh_api("POST", dispatch_url, data)` returns `({}, 204)` for a successful workflow dispatch
2. `dispatch_child()` checks `status == 204` and returns `True`
3. The child batch workflow run appears in GitHub Actions within 30 seconds of dispatch
4. The orchestrator logs "Dispatched successfully" (not "Dispatch FAILED")

**Validates**: Bug #13 fix — GitHub's `workflow_dispatch` endpoint returns HTTP 204 No Content with an empty body. The old `gh_api()` tried `json.loads(b'')` which raised `JSONDecodeError`, caught as `status=0`. `dispatch_child()` checked `status == 204` but got 0, returning `False` even though the HTTP request actually succeeded.

**Production scenario**: The orchestrator dispatches 5 child workflows. Without the 204 fix, ALL dispatches appear to fail (returning `False`), but they actually succeed on GitHub's side. This creates 5 orphan workflow runs that consume Devin sessions and ACU budget, while the orchestrator reports 0 progress and retries — creating 5 MORE orphan runs. Each retry cycle burns more budget.

**Worry**: The `not body` check in `gh_api()` also skips JSON parsing for non-204 responses with empty bodies. A future GitHub API change that returns an empty body with status 200 would be silently accepted instead of raising an error. This is the safer trade-off (don't crash), but could mask unexpected API behavior.

---

### TC-BL-REG-15: Session Reservation Gate Removed — Child-Count Concurrency Only (Bug #14)

**Setup**: Create 5+ active Devin sessions externally (e.g., via the PR-scoped workflow on multiple PRs). Then trigger the orchestrator workflow with `max_batches=1`.

**Expected**:
1. The orchestrator does NOT check `check_active_devin_sessions()` before dispatching
2. The orchestrator dispatches based solely on `len(active_children) < max_concurrent`
3. Even with 62 external sessions running, the orchestrator immediately dispatches a child workflow
4. The child workflow handles Devin API 429 rate limits internally (retry with backoff)
5. The orchestrator logs show no "Session reservation" or "Waiting for session slots" messages

**Validates**: Bug #14 fix — `check_active_devin_sessions()` queries ALL sessions on the Devin account, not just sessions from this orchestrator. External sessions (PR reviews, other repos) block dispatch indefinitely because `62 >= max_concurrent(3)`.

**Production scenario**: A Fortune 500 company uses Devin for multiple repos and workflows. At any given time, 5-10 Devin sessions are running across the organization. The backlog orchestrator would NEVER dispatch because it sees 10 active sessions >= 3 limit. The security backlog grows indefinitely while the orchestrator reports "waiting for session slots."

**Worry**: With the session reservation gate removed, if `max_concurrent=5` and 5 other sessions are already consuming all Devin slots, the orchestrator will dispatch 5 children that all fail to create Devin sessions (429 rate limit). The children must handle this gracefully with retry/backoff. If they don't, all 5 children fail immediately and the orchestrator marks all batches as failed.

### TC-BL-REG-16: Status Field Mismatch — Polling Uses status_enum (Bug #15)

**Setup**: Trigger the orchestrator workflow with `max_batches=1`. Let the child batch workflow create a Devin session and wait for it to complete. Monitor the batch workflow's "Poll Devin session status" step logs.

**Expected**:
1. Each poll line logs BOTH fields: `Poll N/45: status=X status_enum=Y`
2. The polling exits promptly when `status_enum` reaches a terminal value (`finished`, `expired`, `blocked`, `suspend_requested`, etc.)
3. The polling does NOT run for 45 minutes (the full timeout) when the session has already completed
4. The `EFFECTIVE_STATUS` logic correctly falls back to `.status` if `.status_enum` is missing/null
5. The downstream "Create PR" step fires for `finished`, `stopped`, `expired`, `suspended`, `suspend_requested`, and `suspend_requested_frontend` statuses
6. The collect-results step correctly categorizes alerts based on the effective status

**Validates**: Bug #15 fix — the batch workflow's polling logic previously checked `.status` (free-form string) against `finished|stopped|blocked|suspended|failed|error`, but the Devin API returns `.status_enum` with a different value set (`working`, `finished`, `expired`, `suspend_requested`, etc.). Every poll fell through to "still running" because `.status` didn't match any case branch.

**Production scenario**: A Fortune 500 company runs the backlog orchestrator nightly. Each batch takes ~10 min for Devin to fix. Without the Bug #15 fix, every batch polls for 45 min (the full timeout), so a 34-batch backlog takes 5+ hours instead of ~70 min. With the fix, the polling detects completion immediately and frees the slot for the next batch.

**Worry**: If the Devin API changes `status_enum` values in a future version (e.g., adds `completed` instead of `finished`), the polling will silently revert to timeout mode. The dual-field logging (`status=X status_enum=Y`) is the safety net — operators can spot the unknown value in logs and update the case statement. But if no one is watching logs, the regression goes unnoticed until backlog runs start timing out.

### TC-BL-REG-17: Expired Session Handled Gracefully (Bug #15 Extension)

**Setup**: Create a Devin session with a very low `max_acu_limit` (e.g., 1) so the session expires before completing all fixes. Trigger the batch workflow with this session's batch of alerts.

**Expected**:
1. The polling detects `status_enum=expired` and exits with `status=expired`
2. The "Create PR" step fires (session may have pushed partial fixes before expiring)
3. The collect-results step queries CodeQL for each alert — any that were fixed before expiration are marked as `fixed`, the rest as `unfixable`
4. The unfixable alerts appear in the workflow summary under "Alerts Requiring Human Review"
5. The orchestrator correctly processes the batch result and updates the cursor

**Validates**: The `expired` status handling added as part of Bug #15 fix. Previously, an expired session would cause the polling to timeout (45 min waste) and all alerts would be marked as "timeout" — losing any partial fixes the session made before expiring.

**Production scenario**: An organization sets conservative ACU limits per session. A complex batch with 15 alerts causes the session to expire after fixing only 8. Without proper `expired` handling, all 15 alerts are marked unfixable. With the fix, the 8 fixed alerts are correctly identified via CodeQL re-query, and only the remaining 7 are flagged for human review.

**Worry**: The `expired` status triggers the "Create PR" path, but an expired session may not have pushed a branch at all. The branch-existence check (HTTP 404 guard) should handle this — if no branch exists, `pr_created=false` and no PR is attempted. But if the session pushed a partial branch with broken code, a PR is created with incomplete fixes that may fail CodeQL. The collect-results step's per-alert CodeQL re-query is the safety net here.

### TC-BL-REG-18: Artifact Download Headers Defined (Bug #16)

**Setup**: Trigger the orchestrator with `max_batches=1` and `max_concurrent=1`. Let it dispatch one child batch. Wait for the child to complete successfully (at least one alert fixed). Check orchestrator logs for the artifact download step.

**Expected**:
1. The orchestrator logs `Found result artifact: batch-N-result` after child completion
2. The orchestrator logs `Fixed: X, Unfixable: Y` with actual per-alert counts
3. The cursor comment on the tracking issue shows `unfixable_alert_ids` as a separate list (not empty if some alerts weren't fixed)
4. NO `NameError` or `Could not fetch batch result artifact` error in the orchestrator logs
5. The `headers` variable is defined before the main orchestrator loop with the correct auth token

**Validates**: Bug #16 fix — the `headers` variable was undefined in the orchestrator's Python scope. The artifact download code at lines 722/730 used `urllib.request.Request(artifacts_url, headers=headers)` but `headers` was never assigned. This caused a guaranteed `NameError`, caught by the `except Exception` handler, which silently fell through to "marking all alerts as processed" — destroying the fixed/unfixable distinction.

**Production scenario**: A Fortune 500 company runs the backlog orchestrator nightly. Devin fixes 80% of alerts and leaves 20% unfixable. But the orchestrator's `NameError` means ALL alerts are marked as "processed" — none are flagged as unfixable. The human review notification never fires. The security team believes the backlog is 100% resolved. Three months later, an auditor finds 50 unaddressed vulnerabilities that were silently buried.

**Worry**: The `except Exception` handler is too broad — it catches `NameError`, `TypeError`, `KeyError`, and other programming errors, not just network/API failures. Any future typo or refactoring mistake in the artifact download code will be silently swallowed, and the orchestrator will fall back to "all processed" without anyone knowing. Consider narrowing the exception handler to `(urllib.error.URLError, json.JSONDecodeError, zipfile.BadZipFile)` so programming errors crash loudly.

### TC-BL-REG-19: Backfill Uses Child-Count Concurrency (Bug #17)

**Setup**: Trigger the orchestrator with `max_batches=3` and `max_concurrent=1`. This forces sequential processing: dispatch batch 1, wait for completion, backfill with batch 2, wait, backfill with batch 3. Have 5+ external Devin sessions active on the account during the test (e.g., from PR-scoped workflows on other PRs).

**Expected**:
1. The orchestrator dispatches batch 1 immediately (initial fill uses child-count, not session count)
2. After batch 1 completes, the orchestrator backfills with batch 2 despite 5+ external sessions running
3. After batch 2 completes, the orchestrator backfills with batch 3
4. The backfill path does NOT call `check_active_devin_sessions()`
5. The backfill path checks `len(active_children) < max_concurrent` only
6. All 3 batches complete — no batches are left pending due to external session blocking

**Validates**: Bug #17 fix — the backfill path still called `check_active_devin_sessions()` after Bug #14 was supposed to remove it. External sessions blocked backfill, causing the orchestrator to dispatch only the first wave and leave remaining batches pending forever.

**Production scenario**: Same as Bug #14 — the organization uses Devin for multiple repos. The initial fill dispatches correctly (Bug #14 fix), but after the first wave completes, backfill is blocked by external sessions. For a 34-batch backlog with max_concurrent=3, only batches 1-3 complete. Batches 4-34 are never dispatched. The orchestrator reports "31 batches remaining" and exits. The next cron run picks them up, but then the same thing happens again.

**Worry**: With the session reservation gate fully removed from both initial fill AND backfill, there's no protection against overwhelming the Devin API. If max_concurrent=5 and the organization already has 5 sessions running, the orchestrator dispatches 5 children that all fail to create Devin sessions (429). The children retry with backoff, but if the organization's session usage doesn't decrease, all children eventually timeout. Consider adding a soft warning (log only, no blocking) when external session count is high.

### TC-BL-REG-20: Collect-Results False Unfixable Classification (Bug #18a)

**Setup**: Trigger the orchestrator with `max_batches=1`. Let the child batch workflow create a Devin session. Wait for Devin to push fixes and the batch workflow to create a PR. Inspect the collect-results step output BEFORE the PR is merged.

**Expected**:
1. The collect-results step checks which files were modified in the branch vs main (not CodeQL alert state on main)
2. For each alert whose file was modified in the branch → marked as `attempted` (not `unfixable`)
3. For each alert whose file was NOT modified → marked as `unfixable`
4. The batch result artifact contains `attempted_alert_ids` (new field) separate from `unfixable_alert_ids`
5. The orchestrator stores attempted alerts in `cursor.attempted_alert_ids` (not in `unfixable_alert_ids`)
6. The human review notification only fires for truly unfixable alerts (file not modified), NOT for attempted ones

**Validates**: Bug #18a — the collect-results step previously queried `GET /repos/{owner}/{repo}/code-scanning/alerts/{id}` which returns alert state on the default branch (main). Since the fix PR hasn't been merged, ALL alerts show `state=open` and ALL are marked unfixable. This means every batch run reports 0 fixed, N unfixable — even when Devin's fixes are valid.

**Production scenario**: A Fortune 500 company runs the nightly backlog sweep. Devin successfully fixes 18 of 20 alerts and pushes PRs. But the collect-results step marks all 20 as "unfixable" because it checks CodeQL on main before the PRs are merged. The security team gets a notification: "20 alerts require human review." They spend 2 hours reviewing and find that 18 were actually fixed by Devin. Trust in the system erodes — the team starts ignoring the notifications, which means the 2 genuinely unfixable alerts also get ignored.

**Worry**: The file-modification heuristic (checking if the branch modified the alert's file) is imprecise. Devin could modify a file without actually fixing the specific alert (e.g., fixing one alert in a file with 3 alerts). The `attempted` classification is conservative — it means "Devin tried, pending verification" rather than "confirmed fixed." The definitive verification only happens after PR merge + CodeQL re-run.

### TC-BL-REG-21: Unfixable Alert Re-Verification on Subsequent Runs (Bug #18b)

**Setup**: Run the orchestrator once (Run A). Let it mark some alerts as "unfixable" in the cursor. Then merge the fix PR that Devin created. Wait for CodeQL to re-run on main and confirm the alerts are now `state=fixed`. Run the orchestrator again (Run B) WITHOUT resetting the cursor.

**Expected**:
1. Run B's step 5 (Filter and batch) re-queries CodeQL for each alert in `unfixable_alert_ids`
2. Alerts that are now `state=fixed` on main → removed from `unfixable_alert_ids`, added to `processed_alert_ids`
3. Alerts that are still `state=open` → remain in `unfixable_alert_ids`
4. The cursor is updated with the corrected counts
5. The human review notification on Run B only includes the truly still-unfixable alerts
6. The `unfixable_alert_ids` list shrinks as PRs are merged (it doesn't grow monotonically)

**Validates**: Bug #18b — the filter logic previously skipped any alert in `unfixable_alert_ids` without re-checking its current CodeQL state. After the fix PR was merged and the alert transitioned to `state=fixed`, the next orchestrator run still treated it as "unfixable" because it was in the cursor's skip list. The unfixable list grew monotonically and never shrank.

**Production scenario**: Week 1: Devin fixes 100 alerts across 7 batches. All 100 are marked "unfixable" (Bug #18a). The security team merges all 7 PRs. Week 2: The orchestrator runs again. Without the Bug #18b fix, the cursor still shows 100 unfixable alerts despite all being resolved. The dashboard permanently shows "100 alerts need human review" even though zero actually do. With the fix, Run B re-verifies and finds all 100 are now "fixed" → moves them to processed → dashboard shows "100 fixed, 0 need review."

**Worry**: The re-verification step queries CodeQL for every alert in `unfixable_alert_ids` on every run. For large backlogs with many unfixable alerts (e.g., 500), this adds 500 API calls per run. With rate limiting (0.5s per call), that's ~4 minutes of additional startup time. Consider batching the re-verification (e.g., `GET /repos/.../code-scanning/alerts?state=fixed`) or only re-verifying alerts whose associated PR has been merged since the last run.

### TC-BL-REG-22: Shell Variables Visible to Python Heredoc (Bug #19)

**Setup**: Trigger the batch workflow with a batch of alerts. Let the Devin session complete (any terminal status: finished, blocked, expired). Observe the collect-results step logs.

**Expected**:
1. The collect-results step logs show `Session status: <actual_status>, branch: <branch_name>` (not `Session status: , branch: ...`)
2. The Python script can read `SESSION_STATUS`, `REPO`, `SESSION_ID`, `SESSION_URL`, `PR_NUMBER`, `PR_URL` from `os.environ`
3. The classification logic enters the correct branch based on the actual session status
4. If session is "blocked", the file-modification heuristic still runs (blocked sessions may have done partial work)

**Validates**: Bug #19 — the collect-results step previously set `REPO`, `SESSION_STATUS`, etc. as shell variables in the `run:` block, but the Python heredoc reads `os.environ` which only sees environment variables (not shell variables). Result: `session_status` was always empty string, causing ALL batches to fall through to the `else` clause ("all alerts unresolved") regardless of actual session status. This completely broke the three-state classification from Bug #18.

**Production scenario**: A Fortune 500 company deploys the backlog workflow. Every batch run correctly creates Devin sessions, Devin fixes 80% of alerts, but the collect-results step always reports "Session status=, branch=... — all alerts unresolved" and marks everything unfixable. The security team sees 100% unfixable rate and concludes the system is broken. They disable it and go back to manual remediation — a $500K/year cost the workflow was supposed to eliminate.

**Worry**: This is a class of bugs specific to GitHub Actions YAML workflows with inline Python heredocs. Any future step that uses `os.environ` to read values set as shell variables in the same `run:` block will have the same issue. The convention must be: all variables that Python needs must be in the step's `env:` block, not set as shell variables.

### TC-BL-REG-23: Artifact Download Succeeds Without 403 (Bug #20)

**Setup**: Trigger the orchestrator with `max_batches=1`, `reset_cursor=true`. Let the child batch complete. Observe the orchestrator logs during the artifact download phase.

**Expected**:
1. Orchestrator logs show `Found result artifact: batch-1-result`
2. Followed by `Fixed: X, Attempted: Y, Unfixable: Z` (actual per-alert breakdown)
3. NOT followed by `Could not fetch batch result artifact: HTTP Error 403...`
4. The cursor is updated with the correct fixed/attempted/unfixable counts (not the fallback "mark all as processed")
5. The summary shows non-zero attempted or unfixable counts (reflecting actual Devin behavior, not the fallback)

**Validates**: Bugs #20 and #21 — GitHub's artifact `archive_download_url` returns a 302 redirect to Azure Blob Storage. Bug #20: Python's `urllib` forwards the `Authorization: token` header to Azure → 403. Bug #21: The custom `NoAuthRedirectHandler` fix malformed the redirect request → 400. Final fix: `curl -sL` subprocess call which natively strips auth headers on cross-domain redirects.

**Production scenario**: A company runs the backlog sweep nightly. Every night, the orchestrator successfully dispatches batches, Devin fixes alerts, but the artifact download silently fails. The orchestrator falls back to marking ALL alerts as "processed" — the cursor grows but the fixed/unfixable breakdown is always empty. The security dashboard shows "500 alerts processed, 0 unfixable, 0 need review" when in reality 50 alerts were unfixable and need human attention. Those 50 vulnerabilities persist in production undetected.

**Worry**: The download failure is silent — the orchestrator catches the exception, logs a warning, and continues with the fallback. In production, this means the three-state classification (Bug #18) never actually reaches the cursor. The entire unfixable-alert-marking pipeline is broken at the last mile. This is particularly insidious because the workflow completes successfully (exit code 0) and the summary looks clean.

### TC-BL-REG-24: Artifact Download Uses curl Not urllib (Bug #21)

**Setup**: Trigger the orchestrator with `max_batches=1`, `reset_cursor=true`. Let the child batch complete. Observe the orchestrator logs during the artifact download phase. Specifically look for evidence that curl (not urllib) is being used for the download.

**Expected**:
1. Orchestrator logs show `Found result artifact: batch-1-result`
2. Followed by `Fixed: X, Attempted: Y, Unfixable: Z` (actual per-alert breakdown from the artifact JSON)
3. NOT followed by `Could not fetch batch result artifact: HTTP Error 400: The request URI is invalid`
4. NOT followed by `Could not fetch batch result artifact: HTTP Error 403...`
5. The cursor is updated with correct attempted/unfixable counts
6. The summary displays the three-state breakdown (not the fallback "mark all as processed")

**Validates**: Bug #21 — The Bug #20 fix (custom `NoAuthRedirectHandler` in urllib) caused HTTP 400 "The request URI is invalid" from Azure Blob Storage. Root cause: Python's `urllib` redirect handler creates a malformed `Request` object — `header_items()` returns internal header representations that don't roundtrip cleanly through `add_header()`, corrupting the redirected request. The fix replaces urllib entirely with a `curl -sL` subprocess call, which natively strips `Authorization` headers on cross-domain redirects (since curl 7.58+).

**Production scenario**: After deploying Bug #20's fix, a company's nightly backlog sweep still silently fails to download artifacts — but now with HTTP 400 instead of 403. The security team investigates the 403 fix, confirms `NoAuthRedirectHandler` is deployed, and concludes "artifact download is fixed." But the error has merely changed shape. The three-state classification still never reaches the cursor. Unfixable alerts are still invisible. This is a cascading fix failure — Bug #20's fix introduced Bug #21, and the fallback behavior masks both.

**Worry**: Python's `urllib` redirect handling is fundamentally unreliable for GitHub's artifact download flow (GitHub API → 302 → Azure Blob Storage). Any fix that stays within urllib is fragile. The curl-based solution is the correct approach because curl's redirect handling is battle-tested and natively handles auth-stripping. But we must verify curl is available on the runner (standard on GitHub-hosted Ubuntu runners, may not be on self-hosted). If curl is missing or returns non-200, the fallback still triggers — test that the fallback path is still functional as a safety net.

### TC-BL-REG-25: Multi-Batch Run Resolution Does Not Cross-Match (Bug #22)

**Setup**: Trigger the orchestrator with `max_batches=2`, `reset_cursor=true`, `max_concurrent=3`. This dispatches 2 child batch workflows within seconds of each other. Observe the orchestrator logs during the run resolution phase (Poll #1 and subsequent polls).

**Expected**:
1. Orchestrator dispatches batch 1 at T1 and batch 2 at T1+5s
2. On Poll #1, batch 1 resolves to the FIRST run created (oldest), batch 2 resolves to the SECOND run created (newest)
3. Each batch's resolved run ID corresponds to the correct child workflow (no cross-matching)
4. NO re-dispatch occurs for either batch (no "No workflow run found after Xs — re-dispatching" message)
5. Exactly 2 child workflow runs are created total (not 3 or more)
6. Both batches complete and the orchestrator exits the polling loop normally
7. The summary shows results for both batches

**Validates**: Bug #22 — GitHub's API returns workflow runs newest-first. The old code iterated per-child and matched the first unmatched run, causing batch 1 to grab batch 2's run. The fix sorts runs oldest-first and resolves all unmatched children in one pass with chronological 1:1 matching.

**Production scenario**: A Fortune 500 company has 500 open CodeQL alerts (34 batches). The orchestrator dispatches 5 batches in the first wave. Without this fix, cross-matching creates 10 workflow runs (5 correct + 5 orphans from re-dispatch), burns 10 Devin sessions instead of 5, and the orchestrator hangs for 25+ minutes on orphaned runs. With 34 batches across 7 waves, the total waste is catastrophic: ~35 orphaned sessions, $thousands in wasted ACU budget, and the backlog sweep never completes within the 6-hour GitHub Actions timeout.

**Worry**: The cross-matching is deterministic — it happens EVERY time 2+ batches are dispatched close together. This is not a rare race condition; it's a guaranteed failure in any multi-batch run. The `already_matched` set in the old code was built once at the start of the loop but never updated within the loop, so even if two children happened to match different runs, a third child could re-match an already-taken run.

### TC-BL-REG-26: Unknown Status Does Not Cause Infinite Polling (Bug #22)

**Setup**: Trigger the orchestrator with `max_batches=1`, `reset_cursor=true`. During the child batch workflow's execution, simulate a GitHub API outage by observing what happens when `check_child_status()` returns `"unknown"` (API failure). This can be tested by checking the orchestrator logs for any `unexpected status 'unknown'` messages.

**Expected**:
1. If `check_child_status()` returns `"unknown"` (API failure), the orchestrator logs `Batch X: unexpected status 'unknown' (Ys)`
2. The child stays in `active_children` (transient failures should not immediately evict)
3. If the API recovers on the next poll, the child's status returns to normal
4. If the API fails for longer than `max_child_runtime` (3600s), the child is evicted with conclusion `unknown_status_unknown`
5. The orchestrator does NOT hang indefinitely — it either recovers or evicts

**Validates**: Bug #22 (part 2) — The polling loop previously only handled `"completed"`, `"queued"`, `"in_progress"`, `"waiting"`. Any other status silently kept the child in `active_children` forever. The `while active_children or pending_batches:` loop never exited because `active_children` never emptied.

**Production scenario**: GitHub experiences a 30-minute API degradation (not uncommon — see https://www.githubstatus.com). During this window, every `check_child_status()` call returns `"unknown"`. Without the fix, the orchestrator accumulates children in `active_children` that can never be removed, the rolling window fills up (5/5 slots "occupied" by ghosts), no new batches are dispatched, and the orchestrator runs until the 6-hour timeout. With the fix, the orchestrator tolerates transient API failures and recovers once the API comes back.

**Worry**: The 3600s eviction timeout for unknown status is very generous. If the API is down for 30 minutes, the orchestrator wastes 30 minutes of polling before evicting. A more aggressive strategy (e.g., evict after 10 consecutive unknown polls) would recover faster. But the conservative approach avoids false evictions from a single API hiccup. The trade-off is documented here for production tuning.

### TC-BL-REG-27: Orchestrator Completes After All Children Complete (Bug #22 Regression)

**Setup**: Trigger the orchestrator with `max_batches=2`, `reset_cursor=true`, `max_concurrent=3`. Let both child batch workflows run to completion. Monitor the orchestrator's polling loop until it exits.

**Expected**:
1. Both child batch workflows complete (status=completed, conclusion=success or failure)
2. The orchestrator detects both completions and removes them from `active_children`
3. `active_children` empties, `pending_batches` is empty
4. The `while active_children or pending_batches:` loop exits normally
5. The orchestrator proceeds to the summary step and completes
6. Total orchestrator runtime is approximately: (child runtime) + (poll overhead) — NOT stuck for 25+ minutes after children complete

**Validates**: Bug #22 full regression — confirms the orchestrator does not hang after all children complete. The previous iteration 4 attempt (orchestrator 22060117744) hung for 25+ minutes after both children (22060122063, 22060125305) completed successfully. The root cause was cross-matching + missing unknown status handler.

**Production scenario**: The simplest invariant: if all children are done, the orchestrator should be done too. Any violation of this invariant means the backlog sweep never reports results, the cursor is never updated, unfixable alerts are never surfaced to humans, and the GitHub Actions job runs until the 6-hour timeout (costing compute minutes and blocking subsequent scheduled runs).

**Worry**: Even with the Bug #22 fix, there are other paths that could cause the polling loop to hang: (a) a child's status transitions through an unexpected GitHub Actions state (e.g., "cancelled" before the orchestrator polls), (b) the safety timeout is set too high (currently 5400s = 90 minutes), or (c) a child is evicted but the orchestrator fails to update the cursor before the safety timeout. This test validates the happy path; TC-BL-REG-26 covers the API failure path.

### TC-BL-REG-28: PR Creation Runs for Blocked Sessions (Bug #23)

**Setup**: Trigger the orchestrator with `max_batches=1`, `reset_cursor=true`. Let the child batch workflow run. The Devin session will likely end in `blocked` status (observed pattern: sessions go blocked after ~15-17 min of work). Monitor the child workflow's "Create PR for batch fixes" step.

**Expected**:
1. The Devin session ends with `status_enum=blocked`
2. The "Create PR for batch fixes" step RUNS (not skipped)
3. If Devin already created a PR inside the session, the step detects the existing PR and captures its URL
4. If no PR exists, the step creates one
5. The result artifact contains a non-empty `pr_url` and `pr_number`
6. The orchestrator summary includes the PR URL

**Validates**: Bug #23 — The "Create PR" step's `if` condition previously excluded `blocked` status. When sessions ended `blocked` (which is the COMMON case in practice), the step was skipped, causing `pr_url: ""` in the result artifact. The orchestrator could not report which PRs were created.

**Production scenario**: At a Fortune 500 company, the security engineering team relies on the orchestrator's tracking issue for a dashboard of all fix PRs. If PR URLs are missing for half the batches (because sessions went `blocked`), the team has to manually search GitHub for PRs matching `devin/security-batch-*` branches. With 34 batches across a 500-alert backlog, this manual search is unacceptable. The fix ensures every batch that pushed code gets its PR URL captured regardless of session terminal status.

**Worry**: Even with `blocked` added to the condition, other terminal statuses could emerge from the Devin API in the future (e.g., `cancelled`, `timed_out`). A more robust approach would be `if: steps.poll-session.outputs.completed == 'true'` instead of listing every possible status. But that changes the step's semantics — currently, `completed=true` is set for ALL terminal statuses including `failed` and `error`, where PR creation would be pointless. The current explicit list is safer but requires updating when new API statuses are added.

### TC-BL-REG-29: Artifact Download Failure Marks Alerts as Attempted, Not Processed (Bug #24)

**Setup**: Trigger the orchestrator with `max_batches=1`, `reset_cursor=true`. After the child batch completes, check the orchestrator logs for the artifact download step. If the artifact download succeeds, verify normal three-state classification. To test the failure path: examine the fallback code path in the orchestrator that runs when `artifact_fetched` is `False`.

**Expected (normal path)**:
1. Artifact download succeeds → `artifact_fetched = True`
2. Alerts classified as fixed/attempted/unfixable based on artifact data
3. Cursor updated with three-state classification

**Expected (failure path)**:
1. Artifact download fails (exception caught) → `artifact_fetched = False`
2. ALL alerts in the batch are marked as `attempted` (NOT `processed`)
3. The cursor's `attempted_alert_ids` list grows by the batch's alert count
4. The cursor's `processed_alert_ids` list does NOT grow
5. On the next orchestrator run, these alerts are re-verified via Bug #18b logic
6. If the fix PR was merged and CodeQL confirms fixed, the alert moves from attempted → processed

**Validates**: Bug #24 — The old fallback marked all alerts as `processed` when artifact download failed. `processed` means "confirmed fixed on main." Without artifact data, there's no evidence the fix worked. Marking as `processed` permanently removes alerts from future sweeps, potentially leaving vulnerabilities unpatched.

**Production scenario**: GitHub Artifacts has a documented SLA of 99.9% availability. For a 500-alert backlog (34 batches), 0.1% downtime during a 70-minute sweep means ~4 seconds of unavailability. If an artifact download happens to hit that window, the old behavior would permanently mark 15 alerts as "processed" without verification. Over time, with weekly sweeps, this data loss accumulates. The fix ensures no alert is ever marked as permanently resolved without evidence.

**Worry**: The fallback marks alerts as `attempted`, which means they'll be re-processed on the next run. If the artifact download failure is persistent (e.g., the artifact expired after 30 days), these alerts get re-processed every run, potentially creating duplicate Devin sessions and fix PRs for already-fixed code. The re-verification logic (Bug #18b) should catch this by checking CodeQL alert state on main, but if the PR was never merged, the alert stays open and gets re-batched.

### TC-BL-REG-30: Orchestrator Summary Includes Batch PR URLs (Bug #25)

**Setup**: Trigger the orchestrator with `max_batches=2`, `reset_cursor=true`. Let both child batch workflows complete. Check the orchestrator's final summary output for PR URLs.

**Expected**:
1. The orchestrator extracts `pr_url` from each batch's result artifact
2. The final summary includes a "PRs created" section
3. Each completed batch with a PR URL is listed in the summary
4. The PR URLs are valid GitHub PR links

**Validates**: Bug #25 — The orchestrator summary previously only reported alert counts and IDs, not PR URLs. For enterprise teams, the summary is the primary output — it should link to every fix PR so reviewers can start merging immediately without manual GitHub searches.

**Production scenario**: The security team lead runs the weekly backlog sweep on Friday evening. Monday morning, they check the tracking issue for the sweep results. The summary says "22 alerts attempted across 2 batches" but doesn't say WHERE the fix PRs are. The lead has to search GitHub for `devin/security-batch-*` branches, find the PRs, and distribute them to reviewers. With the fix, the summary lists every PR URL, and the lead can assign reviewers directly from the tracking issue.

### TC-BL-REG-31: Cursor Comment Accumulation Prevention (Bug #26)

**Setup**: Trigger the orchestrator with `reset_cursor=true` and `max_batches=2`. This ensures `cursor_comment_id` starts empty. Let both batches complete (2 cursor updates during batch completions + 1 final update = 3 `update_cursor()` calls).

**Expected**:
1. The first `update_cursor()` call creates a new comment via POST
2. The function saves the new comment's ID via `nonlocal cursor_comment_id`
3. All subsequent `update_cursor()` calls PATCH the same comment (HTTP 200)
4. Only 1 cursor comment exists on issue #108 after the run completes (not 3)
5. The final cursor comment contains the complete state from all batches

**Validates**: Bug #26 — Without the fix, each `update_cursor()` call with empty `cursor_comment_id` creates a new comment. In a 2-batch run, this produces 3 cursor comments instead of 1. Over time, the tracking issue accumulates hundreds of stale comments, becoming unreadable for humans and eventually hitting GitHub API pagination limits (100 comments/page).

**Worry**: The `nonlocal` keyword in Python requires the variable to be defined in an enclosing scope. If the heredoc's variable scoping doesn't support `nonlocal` correctly (e.g., if `cursor_comment_id` is treated as a global), the fix silently fails and comments still accumulate. Also, if the POST fails (HTTP 500), the comment ID isn't saved, and the next call creates another new comment — acceptable behavior but should be logged.

**Production scenario**: A Fortune 500 company runs the orchestrator weekly via cron. After 6 months (26 runs), the tracking issue has 26-78 cursor comments (depending on batch count per run). The security team uses this issue as their dashboard. The noise-to-signal ratio makes it unusable. With the fix, there's exactly 1 cursor comment that gets updated in-place.

### TC-BL-REG-32: Failed Batch Alerts Tracked in Cursor (Bug #27)

**Setup**: Trigger the orchestrator with 2 batches. Simulate a child workflow failure by either: (a) manually cancelling one child workflow run mid-execution, or (b) waiting for a natural failure (e.g., Devin API rate limit causing the child to fail). Check the cursor after the orchestrator completes.

**Expected**:
1. The failed batch's alerts appear in `attempted_alert_ids` in the cursor
2. The next orchestrator run skips these alerts (they're in `attempted`)
3. The re-verification logic (Bug #18b) checks if these alerts are now fixed on main
4. If not fixed, they stay in `attempted` and are NOT re-dispatched as new batches

**Validates**: Bug #27 — Without the fix, failed batch alerts are added to `failed_batches` but NOT to the cursor. The next orchestrator run finds them as "remaining" and re-dispatches them. If the failure is persistent, this creates an infinite loop of failed dispatches consuming Devin sessions.

**Worry**: Marking failed batch alerts as `attempted` might be too aggressive. If the failure was transient (e.g., GitHub Actions runner out of disk space), the alerts should be retried. But with the current fix, they're skipped until re-verification detects them as fixed (which won't happen if the fix was never applied). A retry counter would be more nuanced but adds complexity.

**Production scenario**: A repo has a file (`legacy_crypto.py`) with 10 CodeQL alerts. The file uses deprecated cryptography APIs that Devin can't fix without major refactoring. Every batch that includes this file fails because Devin's fix introduces import errors. Without Bug #27 fix, this batch is re-dispatched every week, wasting 10 Devin sessions per month. With the fix, the alerts are marked as `attempted` and skipped until a human resolves them.

### TC-BL-REG-33: Step Summary Includes PR URLs (Bug #28)

**Setup**: Trigger the orchestrator with `max_batches=1`. Let the batch complete and create a PR. Check the GitHub Actions step summary (visible in the Actions UI) for the PR URL.

**Expected**:
1. The orchestrator results JSON includes a `pr_urls` array with the batch's PR URL
2. The Summary step reads the results JSON and appends a "Fix PRs Created" section
3. The step summary shows the PR URL as a clickable link
4. The failed batches in results JSON include `alert_ids` for debugging

**Validates**: Bug #28 — The step summary is the most visible output for enterprise teams. Without PR URLs, teams have to dig into job logs or search GitHub to find the fix PRs. The step summary should be a complete, actionable dashboard.

**Worry**: The Summary step runs with `if: always()`, meaning it executes even if the orchestrate step failed. If the orchestrator crashes before writing `/tmp/orchestrator_results.json`, the Python script in the Summary step should handle the missing file gracefully (the `try/except` catches this). Also, if the orchestrator completes but no PRs were created (all batches failed), the "Fix PRs Created" section should be absent, not show an empty list.

---

### TC-BL-REG-34: YAML Block Scalar Integrity (Bug #29 Regression)

**Type**: Regression — Deployment-blocking YAML syntax error

**Why we test this**: A single YAML syntax error in the workflow file renders the entire workflow invisible to GitHub Actions. No error notification is sent — the workflow silently stops being dispatchable. This happened when a multi-line Python script inside a `$(python3 -c "...")` command substitution broke the YAML literal block scalar (`run: |`) by starting lines at column 1.

**Setup**: After any change to the workflow file that includes inline Python code:
1. Run `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/devin-security-backlog.yml'))"` locally to validate YAML syntax
2. Attempt to dispatch the workflow via API: `POST /repos/{owner}/{repo}/actions/workflows/devin-security-backlog.yml/dispatches`
3. Verify the response is HTTP 204 (success), not HTTP 422

**Expected**:
1. YAML validation passes without `ScannerError`
2. Workflow dispatch returns HTTP 204
3. The workflow appears in the Actions UI with the `workflow_dispatch` trigger visible

**Validates**: Bug #29 — Multi-line Python code embedded in YAML `run: |` blocks inside `$(...)` command substitutions must either be collapsed to a single line or use a properly indented heredoc (`python3 << 'EOF'`). The multi-line `$(python3 -c "...")` pattern is a YAML footgun that is not caught by any CI check — only by attempting to dispatch.

**Worry**: There is no automated CI check that validates GitHub Actions YAML files before merge. A broken YAML file can be merged to main and silently disable the workflow. In production, this means the scheduled backlog sweep stops running with no alert to the team. Consider adding a pre-merge validation step (e.g., `yamllint` or a custom action that parses all workflow files).

---

### TC-BL-REG-35: Alert State Race Condition (Bug #30 Regression)

**Type**: Regression — Race condition between orchestrator fetch and batch fetch

**Why we test this**: In a Fortune 500 repo with frequent CI runs, CodeQL may close alerts (via merged fix PRs) between the orchestrator's initial alert fetch and the child batch's per-alert fetch. The batch workflow must gracefully handle alerts that changed state mid-flight.

**Setup**: 
1. Seed a repo with 10 open CodeQL alerts
2. Trigger the orchestrator
3. While the orchestrator is fetching alerts, merge a fix PR that closes 2 of the 10 alerts
4. The child batch should receive all 10 alert IDs but find only 8 still open

**Expected**:
1. The batch workflow logs "Alert #X state=fixed (skipping — may already be fixed)" for the 2 closed alerts
2. The batch creates a Devin session with only the 8 remaining open alerts
3. The orchestrator summary counts match reality (8 processed, not 10)
4. No errors or workflow failures

**Validates**: Bug #30 — The system must handle the inherent race condition in any fetch-then-process architecture without errors or misleading counts.

**Worry**: If the batch workflow does NOT skip already-fixed alerts, Devin receives instructions to fix alerts that no longer exist. This wastes session time and could cause Devin to make unnecessary changes. The batch's per-alert re-fetch is the safety net.

---

### TC-BL-REG-36: Session Ends Blocked — Unattended Prompt Handling (Bug #31)

**Type**: Regression — Devin sessions ending "blocked" in automated batch runs

**Why we test this**: In unattended automated runs, Devin sessions should complete autonomously without waiting for human input. If a session ends "blocked", it means Devin asked a question and never got a response. The fix PR may be incomplete.

**Setup**:
1. Trigger an orchestrator run with alerts that include ambiguous vulnerability patterns (e.g., alerts in files with complex dependency chains where the "right" fix isn't obvious)
2. Monitor the Devin session's `status_enum` field during polling
3. Check whether the session prompt includes explicit "do not ask questions" instructions

**Expected**:
1. The Devin session prompt includes: "This is an unattended automated run. Do not ask questions or wait for input."
2. The session ends with `status_enum=finished` (not `blocked`)
3. If the session does end `blocked`, the batch workflow still creates a PR (Bug #23 fix) and classifies alerts correctly (Bug #18 fix)
4. The PR body notes that the session ended blocked and some fixes may be incomplete

**Validates**: Bug #31 — Sessions ending "blocked" indicate the prompt needs improvement. The workflow should handle blocked sessions gracefully, but the goal is to minimize them.

**Worry**: In production, blocked sessions waste Devin API credits (the session stays active, consuming ACUs, until it times out). At scale with 5 concurrent sessions, even 1 blocked session reduces throughput by 20%.

---

### TC-BL-REG-37: Stale Cursor Comment Cleanup (Bug #32 Regression)

**Type**: Regression — Stale cursor comments accumulate on tracking issue

**Why we test this**: Before Bug #26 was fixed, each orchestrator run created multiple cursor comments. Even after the fix, stale comments from previous runs remain. For enterprise teams monitoring the tracking issue, dozens of outdated cursor comments obscure the current state.

**Setup**:
1. Run the orchestrator 3 times with `reset_cursor=true` each time (simulating pre-fix behavior)
2. Verify multiple cursor comments exist on the tracking issue
3. Run the orchestrator again with the Bug #32 fix (stale comment cleanup)
4. Check the tracking issue after the run

**Expected**:
1. After the cleanup run, only 1 cursor comment remains on the tracking issue
2. The remaining comment contains the latest cursor state
3. The deleted comments' IDs are logged for audit trail
4. If deletion fails (e.g., permissions), the workflow continues without error

**Validates**: Bug #32 — The tracking issue must remain clean and readable. Enterprise teams should see exactly one cursor comment with the current state, not a history of 50+ stale snapshots.

**Worry**: Deleting comments requires write permissions on the issue. If the `GH_PAT` token lacks `issues:write` scope, the cleanup silently fails. Also, if two orchestrator runs execute simultaneously, they could race to delete each other's cursor comments. The cleanup should only delete comments with the `<!-- backlog-cursor -->` marker.

---

### TC-BL-REG-38: Cursor Parsing IndentationError on Default Runs (Bug #33 Regression)

**Type**: Regression — Python IndentationError crashes orchestrator on default (non-reset) runs

**Why we test this**: The cursor parsing Python heredoc had an indentation error that only manifested when `reset_cursor=false` (the default for scheduled cron runs). All previous test runs used `reset_cursor=true`, hiding the bug. In production, the 6-hour cron schedule runs with default settings — if this code path crashes, the backlog sweep silently stops.

**Setup**:
1. Ensure the tracking issue (#108) has at least one cursor comment from a previous run
2. Trigger the orchestrator with default settings (no `reset_cursor` input, or `reset_cursor=false`)
3. Observe the cursor parsing step

**Expected**:
1. The cursor parsing Python heredoc executes without `IndentationError`
2. The cursor is loaded from the tracking issue comment
3. The orchestrator proceeds to filter alerts and dispatch batches
4. The log shows "Cursor loaded: N processed, M unfixable, K attempted"

**Validates**: Bug #33 — Python code inside YAML heredocs must have consistent indentation. The `if cursor is None:` block body must be at the same indent level throughout.

**Worry**: This class of bug (Python indentation errors inside YAML heredocs) is invisible to YAML linters, Python linters (which don't see the heredoc content), and CI checks. The only way to catch it is to exercise the specific code path at runtime. In production, the default code path (`reset_cursor=false`) is the one that runs on schedule — if it's broken, no one notices until they check why the backlog isn't being processed.
