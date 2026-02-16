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
