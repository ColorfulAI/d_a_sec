# Pipeline Test Suite

Systematic tests for the Devin Security Review closed-loop pipeline.
Run these periodically to validate the pipeline works end-to-end.

---

## Test Categories

1. **Alert Detection** — Does CodeQL find the vulnerabilities?
2. **Alert Classification** — Are alerts correctly split into new-in-PR vs pre-existing?
3. **Devin Session Creation** — Are sessions created with correct prompts?
4. **Fix Quality** — Did Devin actually fix the issues? Did CodeQL confirm?
5. **Fix Granularity** — Did Devin make 1 commit per alert as instructed?
6. **PR Comment UX** — Is the PR comment informative and actionable?
7. **Non-blocking** — Does the workflow exit quickly without waiting for Devin?
8. **Batching** — Are pre-existing alerts batched correctly?
9. **Edge Cases** — Zero alerts, huge alert counts, mixed severity

---

## Test Results Log

### Run 1 — 2026-02-15 (PR #3, commit 2881be7)

#### T1: Alert Detection

| Test | Expected | Actual | Pass? |
|------|----------|--------|-------|
| CodeQL detects py/sql-injection | Yes | Yes (server.py:16) | PASS |
| CodeQL detects py/command-line-injection | Yes | Yes (server.py:23) | PASS |
| CodeQL detects py/flask-debug | Yes | Yes (server.py:32) | PASS |
| CodeQL detects py/reflective-xss | Yes | Yes (server.py:18) | PASS |
| CodeQL detects py/url-redirection | Yes | Yes (server.py:29) | PASS |
| CodeQL detects actions/code-injection | Yes | No (fixed by workflow rewrite) | N/A |

**Notes**: All 5 Python vulnerabilities in `server.py` detected. The `actions/code-injection` alert was present in earlier workflow versions but resolved by the rewrite.

#### T2: Alert Classification

| Test | Expected | Actual | Pass? |
|------|----------|--------|-------|
| Python alerts classified as new-in-PR | 5 | 5 | PASS |
| Pre-existing alerts (from main) | 0 Python (main has no Python) | 0 | PASS |
| actions/missing-workflow-permissions on main | 1 | 1 (correctly excluded from new-in-PR) | PASS |

**Notes**: Classification correctly identifies that all Python alerts are new (since main has no Python code). The `actions/missing-workflow-permissions` alert on main is correctly excluded from the new-in-PR set.

#### T3: Devin Session Creation

| Test | Expected | Actual | Pass? |
|------|----------|--------|-------|
| Session created for new-in-PR alerts | Yes | Yes (session devin-58cbe98f) | PASS |
| Session URL in PR comment | Yes | Yes | PASS |
| Session prompt includes all 5 alerts | Yes | Yes (verified in Devin UI) | PASS |
| Session prompt includes PR branch name | Yes | Yes | PASS |
| No pre-existing sessions (0 pre-existing alerts) | 0 sessions | 0 sessions | PASS |

#### T4: Fix Quality

| Alert | Fixed? | CodeQL Confirms? | Fix Description |
|-------|--------|-----------------|-----------------|
| py/sql-injection | YES | YES (state=fixed) | Parameterized query with `?` placeholder |
| py/command-line-injection | YES | YES (state=fixed) | Allowlist + shlex.split + shell=False |
| py/flask-debug | YES | YES (state=fixed) | Changed debug=True to debug=False |
| py/reflective-xss | YES | YES (state=fixed) | Changed return dict to jsonify() |
| py/url-redirection | PARTIAL | NO (1 still open at line 44) | Multiple fix attempts but CodeQL still flags redirect(safe_path) |

**Notes**:
- 4 out of 5 alerts fully resolved and confirmed by CodeQL
- `py/url-redirection` remains open at line 44: `return redirect(safe_path)` where `safe_path` comes from `parsed.path`. CodeQL traces taint from `request.args.get("url")` through `urlparse()` to `redirect()`. The fix adds validation (scheme/netloc checks, path prefix checks) but CodeQL still considers `parsed.path` tainted.
- **Root cause of residual alert**: CodeQL's taint tracking follows data through `urlparse()` — the parsed path is still considered user-controlled. A fully clean fix would need to use a hardcoded allowlist of paths or validate against a known set of internal routes.

**Score: 4/5 alerts fully fixed (80%)**

#### T5: Fix Granularity (1 commit per alert)

| Test | Expected | Actual | Pass? |
|------|----------|--------|-------|
| Each alert gets its own commit | 5 separate commits | 1 combined commit (25575e4) + 2 follow-up redirect fixes | FAIL |

**Details**: Devin combined all 5 fixes into one commit:
```
25575e4 Fix CodeQL security alerts: py/sql-injection, py/command-line-injection, py/flask-debug, py/reflective-xss, py/url-redirection
3a70e52 Fix py/url-redirection: prevent open redirect bypasses
147e2eb Fix CodeQL py/url-redirection: use parsed path instead of raw user input in redirect
```

**Root cause**: This run used the OLD prompt (before the "1 commit per alert" instruction was added). The updated prompt now explicitly says "Fix each alert ONE AT A TIME" and "Each security issue MUST be a separate commit." This needs re-testing after the prompt update.

#### T6: PR Comment UX

| Test | Expected | Actual | Pass? |
|------|----------|--------|-------|
| Comment posted on PR | Yes | Yes | PASS |
| Total alert count shown | Yes | Yes ("Total CodeQL Alerts: 5") | PASS |
| New-in-PR section with alert list | Yes | Yes (all 5 listed with severity) | PASS |
| Alerts sorted by severity | critical > high > medium | Yes | PASS |
| Devin session URL included | Yes | Yes | PASS |
| Pre-existing section (when 0) | Should be absent | Absent | PASS |
| Links to commits/files tabs | Yes | No (not in this run — added after) | FAIL* |

*Note: The "links to commits/files tabs" test fails for this run because the UX improvement was committed after this workflow run. Will pass on next run.

#### T7: Non-blocking

| Test | Expected | Actual | Pass? |
|------|----------|--------|-------|
| Workflow completes without waiting for Devin | Yes | Yes (~3 min total) | PASS |
| PR not blocked by security review | Yes | Yes (PR mergeable during review) | PASS |

#### T8: Batching

Not testable on this run (0 pre-existing alerts). Needs a test case where main has existing vulnerabilities.

#### T9: Edge Cases

| Test | Expected | Actual | Pass? |
|------|----------|--------|-------|
| Devin session blocked/failed | Graceful handling | Session status=blocked, but PR comment still posted | PASS |
| Multiple workflow runs on same PR | Each posts its own comment | Yes (6 comments from various runs) | PASS |

### Run 2 — 2026-02-15 (PR #3, commit b298d59, full thread analysis)

**Context**: 12 total PR comments, 7 Devin sessions created across multiple workflow runs, 18 commits on the branch.

#### T1: Alert Detection (re-run)

| Test | Expected | Actual | Pass? |
|------|----------|--------|-------|
| Total alerts detected across all runs | 5 original + derivatives | 10 total (1 open, 9 fixed) | PASS |

#### T4: Fix Quality (re-run)

| Alert | Fixed? | CodeQL Confirms? |
|-------|--------|-----------------|
| py/sql-injection | YES | YES (state=fixed) |
| py/command-line-injection | YES | YES (state=fixed) |
| py/flask-debug | YES | YES (state=fixed) |
| py/reflective-xss | YES | YES (state=fixed) |
| py/url-redirection (original line 29) | YES | YES (state=fixed) |
| py/url-redirection (line 39, 41, 44) | YES | YES (3 variants fixed) |
| py/url-redirection (line 42) | NO | NO — still open | 
| actions/code-injection | YES | YES (state=fixed) |

**Score: 9/10 alert instances fixed. 1 residual url-redirection remains.**

The url-redirection alert has been fixed and re-introduced 4 times as Devin's successive fix attempts shift the tainted line number. This is a significant DX finding (see DX Analysis below).

#### T3: Devin Session Status

| Session ID | Status | Created by run |
|-----------|--------|----------------|
| devin-4e325fb3 | blocked | Run 1 (1 alert, actions only) |
| devin-2e5a1c5e | finished | Run 2 (1 alert, actions only) |
| devin-f0093722 | finished | Run 3 (6 alerts, first Python) |
| devin-f209b6eb | blocked | Run 4 (6 alerts, duplicate) |
| devin-58cbe98f | blocked | Run 5 (5 alerts, classified) |
| devin-fc4f5bad | blocked | Run 6 (1 url-redir residual) |
| devin-7f966e17 | working | Run 7 (1 url-redir residual) |

**3/7 sessions blocked (43%). Only 2 finished. 1 still working.**

#### T9: Cascade/Loop Problem (NEW FINDING)

The PR has **12 comments** from the security review workflow. Here's the cascade:

```
Comment 1:  1 alert  (actions only)          → Devin session created
Comment 2:  1 alert  (actions only, re-run)  → Devin session created
Comment 3:  6 alerts (Python detected)       → Devin session created
Comment 4:  6 alerts (duplicate run)         → Devin session created
Comment 5:  5 alerts (classified, improved)  → Devin session created → Devin pushes fixes
Comment 6:  1 alert  (url-redir residual)    → Devin session created → Devin pushes fix
Comment 7:  1 alert  (url-redir residual)    → Devin session created
Comment 8:  1 alert  (url-redir residual)    → no session (API issue?)
Comment 9:  1 alert  (url-redir residual)    → no session
Comment 10: 1 alert  (url-redir residual)    → no session
Comment 11: 1 alert  (url-redir residual)    → no session
Comment 12: 1 alert  (url-redir residual)    → no session
```

**Critical finding**: Each Devin fix push triggers a new workflow run, which finds the residual alert, posts another comment, and creates another session. This is a **feedback loop that doesn't converge** when an alert can't be fully resolved.

---

## Developer Experience Analysis

### What a developer sees on PR #3 right now

A developer opening PR #3 sees:
- **12 bot comments** from the security review workflow, most saying the same thing
- **18 commits**, many of which are merge commits and automated fixes
- No clear summary of "what was fixed and what wasn't"
- Multiple Devin session links, most of which are blocked/unhelpful
- No way to know which comment is the "current" one without reading all 12

### Developer needs vs. current state

| What developers want | Current state | Gap |
|---------------------|---------------|-----|
| **"What vulns does my PR have?"** | Listed in comment, sorted by severity | OK |
| **"Are they being fixed?"** | "Devin is pushing fixes" — but which ones? When? | Missing: no status updates after initial comment |
| **"What did Devin actually change?"** | Must dig through commits tab | Missing: no diff summary in the comment |
| **"Is the fix done?"** | Must click Devin session URL and check | Missing: no completion notification |
| **"Did the fix actually work?"** | Must re-check CodeQL alerts manually | Missing: no re-scan result posted |
| **"Can I merge now?"** | Unknown — is Devin still working? | Missing: clear "safe to merge" signal |
| **"Stop spamming my PR"** | 12 comments, most repetitive | CRITICAL: comment flood from feedback loop |
| **"I only care about MY code"** | Pre-existing alerts mixed in | OK (classified) but pre-existing noise still visible |
| **"Don't touch my branch without asking"** | Devin pushes directly | RISK: some devs prefer review before auto-push |

### Critical DX Issues (Priority Order)

**DX-1: Comment flood / infinite loop (CRITICAL)**
Each Devin fix push triggers a new workflow run → new comment → possibly new session. If an alert can't be fully fixed (like url-redirection), this creates an infinite loop of comments. PR #3 has 12 comments, 7 of which are repetitive.

**Fix**: 
- Edit the existing comment instead of posting a new one (find by marker text)
- Add a max-runs-per-PR guard (e.g., skip if >3 security review comments already exist)
- Skip alerts that were already reported in a previous comment on the same PR
- Add a `[security-review-skip]` label or commit message flag to stop the loop

**DX-2: No completion notification (HIGH)**
Developer has no idea when Devin is done. The initial comment says "Devin is working" but there's no follow-up saying "Devin finished, here's what changed."

**Fix**:
- After Devin session completes, use Devin API webhook or polling to post a follow-up comment with: files changed, commit SHAs, which alerts were resolved, which remain
- Or: add a lightweight "status check" workflow that polls the Devin session and updates the PR comment

**DX-3: No diff visibility in comment (HIGH)**
The comment lists alerts but not what Devin actually changed. Developer must navigate to commits tab.

**Fix**:
- Include a brief code diff or file list in the completion comment
- At minimum: "Fixed in commit `abc1234`: parameterized SQL query in server.py:16"

**DX-4: Blocked sessions waste resources (MEDIUM)**
43% of sessions (3/7) are blocked — likely repo access permissions. These sessions are created but never do useful work.

**Fix**:
- Pre-validate Devin API connectivity before creating sessions
- If the first session gets blocked, don't create more
- Document required Devin service user permissions in DESIGN.md

**DX-5: Merge commits clutter history (MEDIUM)**
The branch has multiple merge commits from concurrent Devin pushes and our pushes happening at the same time. The commit history is noisy.

**Fix**:
- Devin sessions should pull before pushing to keep history linear
- Or accept this as a trade-off of async non-blocking design

**DX-6: No "safe to merge" signal (LOW)**
Developer doesn't know when all fixes are applied and verified.

**Fix**:
- After all sessions complete, post a final summary comment: "All fixable alerts resolved. 1 alert remains (url-redirection — requires manual review). Safe to merge."
- Or set a PR check status (pass/fail) based on remaining alerts

---

## Test Cases for Future Runs

### TC-A: Pre-existing Alert Batching
**Setup**: Merge vulnerable code to main first, then open a new PR with additional vulnerable code.
**Expected**: New-in-PR alerts fixed on PR branch; pre-existing alerts batched into separate sessions.
**Validates**: T2 classification, T8 batching, cross-linking.

### TC-B: Commit Granularity
**Setup**: Open PR with 3+ distinct vulnerabilities in different files.
**Expected**: Devin creates 1 commit per alert with descriptive message like `fix: [rule_id] description (file:line)`.
**Validates**: T5 granularity with updated prompt.

### TC-C: Large Batch (>15 alerts)
**Setup**: Add 20+ vulnerabilities across multiple files to main.
**Expected**: Alerts batched into sessions of <=15, with backfill from other files.
**Validates**: T8 batching algorithm, concurrency control.

### TC-D: Zero Alerts
**Setup**: Open a clean PR with no vulnerabilities.
**Expected**: Workflow detects 0 alerts, posts no comment, exits cleanly.
**Validates**: Edge case handling.

### TC-E: Fix Verification Loop
**Setup**: Introduce a vulnerability that requires multiple fix attempts.
**Expected**: Devin attempts fix, re-runs CodeQL, revises if alert persists.
**Validates**: T4 fix quality, verification loop.

### TC-F: Session Failure Recovery
**Setup**: Trigger workflow with invalid DEVIN_API_KEY.
**Expected**: Workflow handles API error gracefully, posts comment noting failure.
**Validates**: Error handling, graceful degradation.

---

## Known Issues

### KI-1: py/url-redirection residual alert
**Severity**: Medium
**Description**: CodeQL still flags `redirect(safe_path)` even after extensive validation. The taint flows through `urlparse()` and CodeQL considers `parsed.path` user-controlled.
**Potential fixes**:
- Use `flask.url_for()` with a route name instead of raw path
- Maintain an allowlist of valid redirect paths
- Use `werkzeug.utils.safe_join()` for path validation

### KI-2: Devin session blocked
**Severity**: Low
**Description**: Session `devin-58cbe98f` is in `blocked` state. Previous sessions (from earlier runs) successfully pushed fixes, but this session could not proceed.
**Potential cause**: Repository access permissions for the Devin service user.

### KI-3: Duplicate PR comments
**Severity**: Low
**Description**: Each workflow run posts a new comment. Multiple pushes to the same PR result in multiple comments. Could be improved by editing the existing comment instead of creating a new one.

---

## How to Run Tests

### Manual validation after a workflow run:

```bash
# 1. Check open alerts on PR merge ref
curl -s -L -H "Authorization: token $GH_PAT" \
  "https://api.github.com/repos/OWNER/REPO/code-scanning/alerts?ref=refs/pull/N/merge&state=open"

# 2. Check fixed alerts
curl -s -L -H "Authorization: token $GH_PAT" \
  "https://api.github.com/repos/OWNER/REPO/code-scanning/alerts?ref=refs/pull/N/merge&state=fixed"

# 3. Check Devin session status
curl -s -H "Authorization: Bearer $DEVIN_API_KEY" \
  "https://api.devin.ai/v1/session/SESSION_ID"

# 4. Check PR comments
curl -s -L -H "Authorization: token $GH_PAT" \
  "https://api.github.com/repos/OWNER/REPO/issues/N/comments"

# 5. Check commit history for fix granularity
git log --oneline ORIGINAL_COMMIT..HEAD -- path/to/file.py
```
