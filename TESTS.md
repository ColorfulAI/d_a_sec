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

## Batch Session Creation (Advanced Mode) Tests

### TC-BL-BATCH-1: Orchestrator Creates Sessions Up-Front (Happy Path)

**Setup**: Trigger the backlog workflow with `max_batches=2` and `reset_cursor=true`. Ensure there are enough open CodeQL alerts to create 2 batches.

**Expected**:
1. Orchestrator log shows "WAVE 1: Batch-creating up to 5 sessions"
2. For each batch, log shows "Creating Devin session for Batch N..." followed by "Session created: https://app.devin.ai/sessions/..."
3. Child workflows receive `session_id` and `session_url` inputs (visible in workflow run inputs)
4. Child workflow log shows "BATCH MODE: Using pre-created session" (not "STANDALONE MODE: Creating new session")
5. Summary shows "Sessions created in batch: 2"

**Validates**: The core batch session creation flow — orchestrator creates sessions, passes IDs to children, children skip creation.

**Production scenario**: Normal operation with 5 concurrent slots. All 5 sessions in a wave should start working simultaneously when the orchestrator creates them up-front.

**Worry**: If the orchestrator creates sessions but the child workflow doesn't recognize them (e.g., input name mismatch, empty string check fails), every batch falls back to standalone mode and we lose the parallelization benefit entirely — silently, with no error.

---

### TC-BL-BATCH-2: Graceful Fallback to Standalone Mode on Session Creation Failure

**Setup**: Trigger the backlog workflow when 5 Devin sessions are already running (from a previous wave or external usage), causing the orchestrator's `create_devin_session()` to hit HTTP 429.

**Expected**:
1. Orchestrator log shows "Rate limited (429) — will retry later"
2. Orchestrator dispatches child WITHOUT session_id (fallback)
3. Child workflow log shows "STANDALONE MODE: Creating new Devin session"
4. Child creates its own session with exponential backoff (60s, 120s, 240s)
5. Batch still completes successfully despite the fallback

**Validates**: Graceful degradation from batch mode to standalone mode when the Devin API is at capacity.

**Production scenario**: A Fortune 500 client has external Devin sessions running (developers using Devin for other tasks). The backlog workflow should not fail just because it can't create sessions in batch — it should fall back to letting children handle their own session creation.

**Worry**: If the fallback path is broken (e.g., `dispatch_child()` sends empty string instead of omitting `session_id`), the child might receive `session_id=""` and skip creation thinking it's batch mode, then fail because there's no actual session.

---

### TC-BL-BATCH-3: Mixed Batch/Standalone in Same Wave

**Setup**: Trigger backlog with 3 batches. Have 3 existing Devin sessions running so the orchestrator can create 2 new sessions (hitting the 5-session limit on the 3rd).

**Expected**:
1. Batches 1-2: Created in batch mode (orchestrator creates sessions)
2. Batch 3: Falls back to standalone mode (429 on session creation)
3. All 3 child workflows complete successfully
4. Summary shows "Sessions created in batch: 2" (not 3)
5. Children 1-2 log "BATCH MODE", child 3 logs "STANDALONE MODE"

**Validates**: A single wave can contain a mix of batch-mode and standalone-mode children without any coordination issues.

**Production scenario**: During peak hours, the Devin session pool is partially occupied. The orchestrator should maximize batch creation for available slots and gracefully fall back for the rest.

**Worry**: If the orchestrator tracks `sessions_created` incorrectly in the mixed case, the summary could report wrong numbers, misleading operators about system utilization.

---

### TC-BL-BATCH-4: Backfill Uses Batch Mode

**Setup**: Trigger backlog with 7 batches and `max_concurrent=3`. Wait for 1 child to complete, triggering a backfill dispatch.

**Expected**:
1. Wave 1: Batches 1-3 dispatched in batch mode
2. When batch 1 completes: backfill dispatches batch 4 in batch mode (orchestrator creates session first)
3. Backfill log shows "[BACKFILL] Batch 4..." followed by session creation
4. Child 4 receives pre-created session_id

**Validates**: Backfill (slot refill after completion) also uses batch mode, not just the initial wave.

**Production scenario**: With 35 batches and 5 slots, most batches are dispatched via backfill (only the first 5 are in the initial wave). If backfill doesn't use batch mode, 30 of 35 batches lose the parallelization benefit.

**Worry**: If backfill uses the old `dispatch_child()` directly instead of `create_and_dispatch()`, backfilled batches silently run in standalone mode — the initial wave looks fast but subsequent dispatches are slow.

---

### TC-BL-BATCH-5: Session Created But Child Dispatch Fails

**Setup**: Trigger backlog workflow, but simulate a GitHub API failure on `workflow_dispatch` (e.g., by temporarily revoking PAT permissions or hitting dispatch rate limits).

**Expected**:
1. Orchestrator creates Devin session successfully (session starts working)
2. `dispatch_child()` returns False (HTTP error on workflow_dispatch)
3. Batch is put back in `pending_batches` for retry
4. On next poll cycle, `create_and_dispatch()` is called again — creates a NEW session (the old one is orphaned)
5. The orphaned session eventually times out via `max_acu_limit`

**Validates**: What happens when session creation succeeds but child dispatch fails — we don't get stuck, but we do orphan a session.

**Production scenario**: GitHub Actions has occasional API blips. If the orchestrator creates a session but can't dispatch the child to poll it, the session runs unsupervised. The `max_acu_limit` is the safety net.

**Worry**: If the orchestrator doesn't put the batch back in `pending_batches` on dispatch failure, that batch is permanently lost — alerts never get processed. Worse, the orphaned session might push commits to a branch that no child workflow is monitoring, creating phantom branches.

---

### TC-BL-BATCH-6: Batch Mode Session Prompt Contains Correct CodeQL Config

**Setup**: Trigger backlog workflow with `max_batches=1`. Inspect the Devin session's prompt (via Devin dashboard or API `GET /v1/sessions/{id}`).

**Expected**:
1. Session prompt contains the repo's actual CodeQL languages (from `.github/workflows/codeql.yml`)
2. Session prompt contains the exact query suite (e.g., `security-and-quality`)
3. Session prompt contains all threat models (e.g., `remote AND local`)
4. The CodeQL CLI commands in the prompt use these exact values (not defaults)
5. `CODEQL_CONFIG_SOURCE` in logs shows the actual workflow file path, not "defaults"

**Validates**: The orchestrator's `build_session_prompt()` correctly injects dynamically-parsed CodeQL config into the Devin session prompt.

**Production scenario**: A Java/Kotlin monorepo has `languages: java-kotlin,javascript-typescript` with custom query packs. If the batch mode prompt hardcodes `python`, Devin runs CodeQL with the wrong config and the internal verification is meaningless.

**Worry**: If `CODEQL_LANGUAGES` step output is empty (parsing failed silently), the prompt falls back to "python" and Devin's internal CodeQL verification doesn't match CI — fixes pass internal check but fail CI CodeQL. This is the exact bug that caused PRs #111 and #112 to fail.

---

### TC-BL-BATCH-7: CodeQL Verification Uses Correct Language (Not `actions`)

**Setup**: Trigger backlog workflow on a repo whose `codeql.yml` has `languages: [actions, python]` in the matrix. Let batch workflow complete and inspect the "Verify fixes with CodeQL" step logs.

**Expected**:
1. Logs show `Creating CodeQL database (language=python)...` — NOT `language=actions`
2. SARIF results contain Python-specific rules (e.g., `py/sql-injection`, `py/reflective-xss`)
3. Post-session verification correctly identifies remaining Python alerts
4. The PR body's "CodeQL Verification" section reflects Python analysis, not YAML analysis

**Validates**: Bug #47 fix — filtering out `actions` language when real code languages exist.

**Production scenario**: A Fortune 500 monorepo with `languages: [actions, csharp, javascript, python]` in the CodeQL matrix. Before the fix, verification would create a database for `actions` (alphabetically first), scan only YAML workflow files, report "0 alerts found" for all Python/JS/C# vulnerabilities, and stamp every PR as "CodeQL Verification: PASSED" — completely defeating the verification gate. Every fix PR would appear verified but actually fail CI.

**Worry**: If the `actions` language is the only language (repo with no application code, only workflow files), filtering it out would leave an empty list. The fix must fall back to `actions` in this edge case. Also, if a NEW language is added to the CodeQL config between the orchestrator parsing and the child's verification step, the language list could be stale.

---

### TC-BL-BATCH-8: Multi-Language Repo CodeQL Verification

**Setup**: Modify the repo's `codeql.yml` to include `languages: [python, javascript]`. Push vulnerable Python and JavaScript code. Trigger backlog workflow.

**Expected**:
1. Orchestrator parses both languages from CodeQL config
2. Batch session prompt includes both languages
3. Post-session verification uses `python` (first real code language) for database creation
4. Python alerts are correctly verified

**Validates**: Language selection logic works correctly with multiple real code languages (no `actions` in the mix).

**Production scenario**: A full-stack monorepo with Python backend and JavaScript frontend. The backlog workflow should verify fixes against the correct language for each batch's alerts, not just the first one alphabetically.

**Worry**: If a batch contains alerts from BOTH Python and JavaScript files, the verification only runs with one language. This means JavaScript alerts in a mixed batch won't be verified. Future improvement: run verification for each language that has alerts in the batch.

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

### TC-BL-REG-31: Unblock Counter Resets After Session Resumes Working (Bug #37)

**Type**: Regression — validates that the unblock counter resets when a session transitions from blocked → working

**Why we test this**: In production, a Devin session processing a large batch (15 alerts across 5+ files) may encounter multiple independent blocking points — one per file or vulnerability type. Each blocking point is unrelated to the previous one. Without counter reset, a session that successfully resumes work after an unblock still counts that attempt toward the lifetime budget. A batch touching 4 files could legitimately block 4 times, but the old code would kill it after the 2nd block.

**Setup**:
1. Seed the repo with 15+ CodeQL alerts spread across 4-5 different files to create a large batch
2. Trigger the orchestrator with `max_batches=1`, `reset_cursor=true`
3. Wait for the batch workflow to start polling the Devin session
4. Monitor the poll logs for blocked → working → blocked transitions

**Expected**:
1. When the session transitions from `blocked` to `working`, the log shows: "Session resumed working after unblock — resetting unblock counter (was N/3)"
2. The `UNBLOCK_ATTEMPTS` counter resets to 0 after each successful resume
3. The session can handle 3+ independent blocking points across different files (as long as it resumes working between each)
4. The session is only terminated when it blocks 3 times CONSECUTIVELY without resuming work

**Validates**: Bug #37 — The old code used a monotonically increasing counter that never reset. A session processing a 15-alert batch across 5 files could block at 3 different files, but was killed after the 2nd block even though each unblock successfully resumed work. The fix tracks `LAST_STATUS` and resets the counter on `blocked → working` transitions.

**Production scenario**: A Fortune 500 monorepo has 200 CodeQL alerts across 40 files. Batches of 15 alerts cover 3-4 files each. Devin asks a clarifying question when switching between files (e.g., "Should I use the existing sanitizer in utils.py or create a new one?"). With 5 concurrent batches, each batch session may block 3-4 times (once per file transition). Without counter reset, 60% of sessions would be killed prematurely after just 2 files. With counter reset, sessions complete all files as long as they resume work after each unblock.

**Worry**: The counter reset could mask a pathological case: a session that rapidly alternates between blocked and working without making progress (e.g., blocked → working for 1 second → blocked again). The counter resets each time, so the session never hits the consecutive-block limit. The 45-poll timeout (45 minutes) is the only safety net. In production, this could waste a Devin session slot for 45 minutes on a non-productive session.

### TC-BL-REG-32: PR Body Updated with Classification Metadata After Collect-Results (Bug #38)

**Type**: Regression — validates that the PR body includes classification data from collect-results

**Why we test this**: The PR body is the primary artifact enterprise teams review. If it shows "0 fixed, 0 attempted, 0 unfixable" when 12 alerts were actually attempted, the team loses trust in the system. The classification metadata must be written AFTER the collect-results step computes the actual numbers.

**Setup**:
1. Trigger the orchestrator with `max_batches=1`, `reset_cursor=true`
2. Wait for the batch workflow to complete (session finishes or times out)
3. Check the PR body via GitHub API: `GET /repos/{repo}/pulls/{pr_number}`

**Expected**:
1. The PR body contains a "### Alert Classification Summary" table
2. The table shows non-zero counts matching the actual alert classification
3. The PR body contains a `<!-- batch-classification-metadata {...} -->` HTML comment
4. The JSON inside the HTML comment has correct `fixed_alert_ids`, `attempted_alert_ids`, `unfixable_alert_ids`
5. The `run_id` in the metadata matches the batch workflow's run ID
6. The `session_id` in the metadata matches the Devin session ID

**Validates**: Bug #38 — The old code PATCHed the PR body in Step 4 (Create PR) before Step 5 (Collect results) ran. The classification fields were always empty/zero. The fix adds Step 5b that PATCHes the PR body AFTER collect-results with the actual classification data.

**Production scenario**: The security team reviews a batch fix PR. The PR body says "12 alerts attempted, 3 unfixable (human review needed)". The team knows exactly what to review: merge the PR for the 12 attempted fixes, then manually investigate the 3 unfixable alerts listed by ID. Without this metadata, the team sees an empty classification and has to dig through workflow logs to understand what happened.

**Worry**: The Step 5b PATCH overwrites whatever was in the PR body before (Devin's description + Step 4's template). If Devin added important context to the PR description (e.g., "I changed the sanitization approach in user_service.py because the existing pattern was deprecated"), that context is lost when Step 5b appends the classification table. The current implementation APPENDS to the existing body rather than replacing it, but this creates an ever-growing PR body if the workflow runs multiple times on the same branch.

### TC-BL-REG-33: Cursor Parsing Path Exercised with reset_cursor=false (Bug #40)

**Type**: Integration — validates that the production cursor parsing code path works end-to-end

**Why we test this**: All test cycles used `reset_cursor=true`, which bypasses cursor parsing entirely. The production cron schedule uses `reset_cursor=false` (the default), which exercises the full cursor load → parse → filter → resume path. Bug #33 (IndentationError) was found in this code path via code review, but the fix was never validated at runtime.

**Setup**:
1. First, run the orchestrator with `reset_cursor=true`, `max_batches=1` to create an initial cursor comment on the tracking issue
2. Wait for the run to complete (cursor comment created with processed/attempted/unfixable alert IDs)
3. Then run the orchestrator again with `reset_cursor=false`, `max_batches=1` to exercise cursor parsing
4. Check the orchestrator logs for cursor parsing output

**Expected**:
1. The second run successfully parses the cursor comment from the tracking issue
2. The log shows "Found cursor comment..." with the correct alert ID counts
3. Already-processed/attempted alerts are excluded from the new batch
4. Only remaining unprocessed alerts are dispatched to new batches
5. The orchestrator does NOT crash with IndentationError or any other Python error

**Validates**: Bug #40 — The cursor parsing Python code has never been executed in a real workflow run. All testing used `reset_cursor=true` which skips cursor parsing entirely. This test validates the full production path.

**Production scenario**: The cron schedule runs every 6 hours with `reset_cursor=false`. The first run processes 15 alerts (batch 1). Six hours later, the second run loads the cursor, sees 15 alerts already attempted, and dispatches the remaining 7 alerts as batch 2. If cursor parsing fails, the second run either crashes (visible failure) or re-processes all 22 alerts (silent duplication, wasting Devin sessions).

**Worry**: The cursor comment format is a JSON blob inside a GitHub issue comment with a `<!-- backlog-cursor -->` marker. If the marker format changes, or if another comment coincidentally contains the marker text, the parsing logic may find the wrong comment or no comment at all. Additionally, if the cursor JSON has been manually edited by a human (e.g., to remove an alert from the unfixable list), the parser may fail on unexpected field types or missing keys.

### TC-BL-REG-34: Session Prompt Prevents Blocking via CRITICAL OPERATING MODE Header (Bug #41)

**Type**: End-to-end — validates that the improved prompt reduces session blocking

**Why we test this**: In all 4 previous test cycles, every Devin session ended with `status_enum=blocked` after ~10 minutes of working. The sessions never resumed after receiving unblock messages. The root cause is that Devin's default behavior uses `block_on_user=true` when uncertain. The fix rewrites the prompt to open with an explicit `CRITICAL OPERATING MODE` header that forbids blocking.

**Setup**:
1. Trigger the orchestrator with `reset_cursor=true`, `max_batches=1` (single batch to isolate prompt behavior)
2. Wait for the batch workflow to create a Devin session
3. Monitor the session's `status_enum` transitions over time via the poll log

**Expected**:
1. The session prompt starts with "CRITICAL OPERATING MODE" (visible in the workflow logs)
2. The session spends MORE time in `working` status before going `blocked` (if it blocks at all)
3. If the session does go `blocked`, the escalating unblock messages include "CRITICAL" and "URGENT" framing
4. The wait time between unblock attempts is 120s (first 2) then 180s (subsequent)
5. `MAX_UNBLOCK_ATTEMPTS` is 5 (increased from 3)
6. `CONSECUTIVE_BLOCKED` counter is logged for each blocked poll

**Validates**: Bug #41 — The old prompt buried the "UNATTENDED AUTOMATED run" instruction at the end. Sessions consistently blocked. The fix moves the non-blocking instruction to the FIRST line and makes it more explicit.

**Production scenario**: A Fortune 500 company runs the backlog sweep on a repo with 500 alerts (34 batches). If every session blocks and never resumes, the pipeline produces 34 PRs with "attempted" alerts but none confirmed "fixed." The security team has no confidence the fixes actually work. The improved prompt should reduce blocking to <20% of sessions (some may still block if encountering genuinely ambiguous situations).

**Worry**: Even with the improved prompt, Devin may still block in certain situations (e.g., repo requires authentication to clone, CodeQL CLI download fails, file has complex dependencies that Devin can't resolve). The escalating unblock messages may not be sufficient if the session is in a deep blocking state. The 5-attempt budget with 120-180s waits means a blocked session consumes ~12-15 minutes of polling time before being accepted as terminal — this is acceptable but adds to total runtime.

### TC-BL-REG-35: CodeQL Verification Uses Exact CI Configuration (Bug #42)

**Type**: End-to-end — validates that the Devin session executes CodeQL verification matching CI

**Why we test this**: PRs #111 and #112 (created by previous batch workflow runs) failed CodeQL checks in CI, despite the prompt instructing Devin to verify fixes internally. The root cause was vague verification instructions — Devin may have skipped CodeQL or used different settings than CI.

**Setup**:
1. Trigger the orchestrator with `reset_cursor=true`, `max_batches=1`
2. Wait for the batch workflow to complete
3. Check the Devin session URL to inspect what commands Devin actually ran
4. Check the created PR's CodeQL CI check result

**Expected**:
1. The prompt includes the exact CodeQL CLI commands with `--overwrite`, `security-and-quality` suite, and SARIF parsing
2. The Devin session logs show CodeQL being downloaded and executed (look for `codeql database create` and `codeql database analyze` in session transcript)
3. The Devin session logs show SARIF parsing output ("Found X remaining alerts for RULE_ID in FILE")
4. The created PR's CodeQL CI check passes (no new alerts introduced by the fixes)
5. If CodeQL verification failed for an alert, Devin skipped it (no broken fix committed)

**Validates**: Bug #42 — The old prompt said "Check if the specific alert rule ID still appears" without specifying HOW. The fix provides the exact `python3 -c` command to parse SARIF output programmatically.

**Production scenario**: An enterprise security team requires all fix PRs to pass CI before merge. If batch fix PRs consistently fail CodeQL (because Devin's internal verification doesn't match CI), the team loses trust in the pipeline and stops merging automated fixes. Every fix PR must pass CodeQL on the first CI run.

**Worry**: CodeQL CLI installation may fail in Devin's environment (network restrictions, disk space, architecture mismatch). The `security-and-quality` query suite may not be available in the downloaded CodeQL bundle (requires `--download` flag which fetches from GitHub). If CodeQL takes too long (>5 min per database creation), Devin may time out or skip verification to save ACU budget. The SARIF parsing command assumes a specific JSON structure that may change between CodeQL versions.

### TC-BL-CODEQL-1: Post-Session CodeQL Verification Gate Catches Remaining Alerts

**Type**: End-to-end — validates the post-session CodeQL verification gate (Bug #42 Layer 2)

**Why we test this**: Devin's internal CodeQL check (Layer 1) is "best effort" — Devin may skip it, misconfigure it, or run it with wrong settings. The post-session verification gate (Layer 2) runs deterministically in the pipeline with the EXACT same config as CI. This test validates that Layer 2 catches cases where Devin's fix doesn't actually resolve the target alert.

**Setup**:
1. Trigger the orchestrator with `reset_cursor=true`, `max_batches=1`
2. Wait for the batch workflow to complete (Devin session finishes, Step 3b runs)
3. Check the Step 3b logs for CodeQL verification output

**Expected**:
1. Step 3b logs show: "Config source: .github/workflows/codeql.yml"
2. Step 3b logs show dynamically parsed languages, query suite, threat models
3. Step 3b logs show CodeQL CLI download, database creation, and analysis
4. Step 3b logs show "=== CodeQL Verification Results ===" with counts
5. If all fixes are clean: `verified=pass`, PR gets `codeql-verified` label
6. If any fix introduced new alerts: `verified=fail`, PR gets `codeql-verification-failed` label
7. PR body includes "### CodeQL Verification: PASSED" or "### CodeQL Verification: FAILED" section

**Validates**: Bug #42 — The pipeline now has a deterministic verification gate that uses the repo's exact CodeQL config, catching issues that Devin's internal check might miss.

**Production scenario**: Enterprise security team requires all fix PRs to pass CI before merge. The `codeql-verified` label gives reviewers confidence. The `codeql-verification-failed` label flags PRs that need manual review. No "pretend fixes" ever reach the review queue.

**Worry**: CodeQL CLI download fails (network, disk space), database creation fails (unsupported language features), SARIF parsing fails (format changes). The `|| true` fallback means verification errors result in `verified=error`, not a blocked PR — but this means a broken verification gate is silently bypassed.

---

### TC-BL-CODEQL-2: Post-Session Verification Catches NEW Alerts Introduced by Fix

**Type**: Regression — validates that fixes introducing new CodeQL alerts are caught

**Why we test this**: PR #159 showed that Devin added an unused import while fixing a security alert. The internal check only looked for the specific rule_id, so it missed the new `py/unused-import` alert. The post-session gate now checks ALL alerts in modified files.

**Setup**:
1. Seed main with a security alert (e.g., `py/sql-injection` in `user_service.py`)
2. Trigger orchestrator. Devin fixes the SQL injection but adds an unused import
3. Post-session verification runs on Devin's branch

**Expected**:
1. Step 3b SARIF parsing detects the new `py/unused-import` alert in `user_service.py`
2. `verified=fail`, `new_alerts=1`, `remaining_alerts=0`
3. PR body shows "### CodeQL Verification: FAILED" with "New alerts introduced by fixes: 1"
4. PR gets `codeql-verification-failed` label
5. PR is still created (work isn't lost) but flagged for review

**Validates**: The specific failure mode from PR #159 — new alerts introduced by a fix.

**Production scenario**: A fix for command injection adds `import subprocess` which CodeQL flags as unused. Without the verification gate, the PR fails CI and the team sees a red check mark on an "automated security fix" — embarrassing and trust-destroying.

**Worry**: SARIF file path formats might not match between `batch_details.json` and CodeQL output (e.g., `app/foo.py` vs `./app/foo.py`). If paths don't match, the "new alerts in modified files" check won't find matches and will incorrectly report `pass`.

---

### TC-BL-CODEQL-3: Dynamic CodeQL Config Parsing — Portability

**Type**: Unit — validates that Step 0 correctly parses different CodeQL workflow configurations

**Why we test this**: The workflow must work on any repo, not just this one. Step 0 parses the repo's `codeql.yml` to extract config values. If the parsing fails or returns wrong values, both the Devin prompt and verification gate use incorrect settings.

**Setup**:
1. Examine Step 0 logs from any batch workflow run
2. Verify the parsed values match the actual `codeql.yml` configuration

**Expected**:
1. Step 0 output: `Found CodeQL workflow: .github/workflows/codeql.yml`
2. Languages: `actions,python` (sorted alphabetically)
3. Query suite: `security-and-quality`
4. Threat models: `local,remote` (sorted alphabetically)
5. These values appear in the Devin prompt (Step 2 logs)
6. These values appear in the verification gate (Step 3b logs)

**Validates**: Dynamic config parsing — the workflow reads the repo's actual CodeQL config instead of hardcoding values.

**Production scenario**: A client deploys this workflow on a JavaScript/TypeScript repo with `default` query suite and `remote`-only threat model. Without dynamic parsing, the workflow would try to run Python CodeQL on a JS repo — instant failure. With dynamic parsing, it correctly uses `javascript`, `default`, and `remote`.

**Worry**: YAML parsing edge cases — nested config blocks, multi-line strings, template variables (`${{ matrix.language }}`). If the parser crashes, the fallback defaults may not match the repo's actual config, causing silent verification mismatches.

---

### TC-BL-CODEQL-4: Verification Gate Labels — codeql-verified vs codeql-verification-failed

**Type**: Integration — validates that PRs get correct labels based on verification results

**Why we test this**: Labels provide at-a-glance status for reviewers. The `codeql-verified` label means "this PR's fixes were independently verified by our pipeline." The `codeql-verification-failed` label means "review carefully — something didn't pass." Wrong labels destroy trust.

**Setup**:
1. Trigger orchestrator, wait for batch to complete
2. Check the created PR for labels

**Expected**:
1. If verification passed: PR has `codeql-verified` label (green)
2. If verification failed: PR has `codeql-verification-failed` label (red)
3. Label is created automatically if it doesn't exist (no 404 errors)
4. Label creation is idempotent (no 422 errors on repeat runs)

**Validates**: Label-based status reporting for enterprise review workflows.

**Production scenario**: Security team configures branch protection to require `codeql-verified` label before merge. PRs that fail verification are automatically blocked from merge until manually reviewed.

**Worry**: Label creation API returns 422 if label already exists. The workflow checks for existence first (GET before POST), but race conditions between concurrent batch workflows could cause duplicate creation attempts.

---

### TC-BL-CODEQL-5: No Pretend Fixes — Broken Fix Never Creates Clean-Looking PR

**Type**: End-to-end — validates the core "no pretend fixes" requirement

**Why we test this**: This is the fundamental requirement. A fix that doesn't actually resolve the CodeQL alert must NEVER result in a PR that appears clean. The verification gate must catch it and flag it.

**Setup**:
1. Seed main with a complex vulnerability that is hard to fix correctly (e.g., taint flow through multiple files)
2. Trigger orchestrator
3. Devin attempts fix but introduces a new issue or doesn't fully resolve the original
4. Observe PR creation and verification results

**Expected**:
1. Post-session verification detects remaining or new alerts
2. PR is created but with `codeql-verification-failed` label
3. PR body explicitly states "CodeQL Verification: FAILED" with details
4. No reviewer can accidentally mistake this for a clean fix
5. The PR's CodeQL CI check will also fail (double confirmation)

**Validates**: DESIGN.md requirement — "A fix PR must never introduce new CodeQL alerts or leave existing alerts unresolved."

**Production scenario**: An automated fix for SQL injection in a complex ORM layer partially resolves the issue but introduces a new taint flow. Without the verification gate, the PR looks like a valid security fix. A reviewer approves and merges it, introducing a NEW vulnerability while "fixing" an old one. With the gate, the PR is clearly flagged and the reviewer knows to inspect carefully.

**Worry**: If the verification gate itself is broken (CodeQL CLI fails to download, SARIF parsing crashes), the `|| true` fallback means `verified=error` which is treated as "not run" — and the PR is created without any label. This silent failure mode is the most dangerous: the gate exists but doesn't actually gate anything.

---

### TC-BL-REG-36: Escalating Unblock Messages Differentiate Early vs Late Attempts (Bug #41)

**Type**: Behavioral — validates that unblock message content escalates appropriately

**Why we test this**: The original implementation sent the same generic unblock message for every attempt. This doesn't help if the session didn't respond to the first message. The fix sends escalating messages: "CRITICAL" framing for attempts 1-2, "URGENT" framing with explicit skip-and-push directives for attempts 3+.

**Setup**:
1. Trigger a batch workflow that processes alerts likely to cause Devin to block (complex multi-file vulnerabilities)
2. Wait for the session to go `blocked`
3. Monitor the poll logs for unblock message content across multiple attempts

**Expected**:
1. Attempts 1-2: Message contains "CRITICAL" and "You MUST continue working immediately"
2. Attempts 3+: Message contains "URGENT" and "This is attempt N to unblock you" and "SKIP IT immediately"
3. Wait times: 120s after attempts 1-2, 180s after attempts 3+
4. If session resumes working between blocks, the counter resets (Bug #37 fix still active)
5. Maximum 5 unblock attempts before accepting terminal blocked state

**Validates**: Bug #41 escalating message strategy — different urgency levels may be more effective at different points in the session's lifecycle.

**Production scenario**: A session processing 15 alerts blocks at alert #3 (complex taint flow). The first "CRITICAL" unblock message helps it resume. It processes alerts #4-#8, then blocks again at alert #9 (unfamiliar framework). The "CRITICAL" message helps again (counter was reset by Bug #37 fix). It processes #10-#12, blocks at #13 (genuinely unfixable), and the "URGENT" messages with "SKIP IT" directive help it skip #13 and finish #14-#15. Without escalation, a single generic message may not convey the right urgency at each blocking point.
