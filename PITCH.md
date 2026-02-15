# Devin Automated Security Review — 3-Minute Pitch

## The Problem

Every development team faces the same security dilemma: **CodeQL finds vulnerabilities, but who fixes them?**

Today, when CodeQL flags an issue on a PR:
1. A developer has to stop what they're doing
2. Understand the security context (often unfamiliar territory)
3. Research the right fix pattern
4. Apply the fix, hope it's correct
5. Wait for CodeQL to re-scan to confirm

This takes **hours per alert**. In a mature codebase with hundreds of pre-existing alerts, the backlog grows faster than teams can fix it. Most teams end up ignoring all but the most critical findings.

## The Solution

**Devin Automated Security Review** closes the loop automatically:

```
CodeQL detects vulnerability
        |
        v
Our workflow classifies the alert (new vs pre-existing)
        |
        v
Devin clones the repo, understands the full codebase,
applies a fix, verifies it with CodeQL, runs the tests,
and pushes the fix commit — all autonomously.
        |
        v
Developer reviews a clean, verified fix on their PR.
```

**One PR comment. Zero noise. Fixes that actually work.**

## Why This Beats GitHub Autofix

GitHub's built-in Autofix has documented limitations: *"The system may suggest fixes that fail to remediate the underlying security vulnerability and/or introduce new security vulnerabilities."*

| | GitHub Autofix | Devin Security Review |
|---|---|---|
| **Context** | Sees ~3 files around the alert | Clones and navigates the **entire repo** |
| **Fix strategy** | Template-based pattern matching | Reasons about codebase conventions, ORM patterns, existing sanitizers |
| **Verification** | None — suggests a fix, hopes it works | Re-runs CodeQL locally to **prove** the alert is resolved |
| **Testing** | None | Runs the existing test suite to catch regressions |
| **Result** | A suggestion you review manually | A verified commit pushed to your branch |

### The Fix-Verify-Test Loop

This is the core differentiator. For each alert, Devin:
1. Reads the surrounding code and understands the full call chain
2. Applies a minimal fix following existing codebase patterns
3. **Re-runs CodeQL locally** — if the alert persists, revises and retries (up to 2 attempts)
4. **Runs the test suite** — if tests fail, revises the fix
5. Only pushes the commit once both CodeQL and tests pass

No other automated security tool performs this level of end-to-end verification.

## The Trust Model: CodeQL Is the Gate, We're the Fixer

A critical design question: **What if Devin is down? Can vulnerable code still merge?**

**No.** Here's why:

CodeQL's "code scanning" creates check runs that can be configured as **required status checks** on the branch protection rule for `main`. If CodeQL finds alerts matching a severity threshold (configurable), it marks the check as failed, which **blocks the PR from merging**. This is GitHub's built-in mechanism and is the industry-standard trust model.

Our workflow **inherits trust from CodeQL**:

| Layer | Role | Blocks PR? | If down? |
|-------|------|-----------|----------|
| **CodeQL** | The gate — detects vulnerabilities, blocks merging | **Yes** (required status check) | PR can't be analyzed — use branch protection to require it |
| **Devin Security Review** | The fixer — auto-fixes what CodeQL finds | **No** (advisory only) | Alerts still reported, developer fixes manually |

This means:
- **CodeQL down** = no analysis happens, but branch protection can require it before merge
- **Devin down** = alerts are still detected and reported on the PR, but fixes must be applied manually. We call this **"degraded mode"** — the workflow still runs, still posts the alert summary, but skips session creation and tells the developer to fix manually
- **Both up** = full automation: detect, fix, verify, push

**We never block your pipeline.** Our workflow is purely additive — it can only help, never hurt. The worst case is it does nothing, and you're exactly where you'd be without it.

## Graceful Degradation in Practice

When Devin is unavailable, developers see this on their PR:

> **DEGRADED MODE** — Devin API is currently unavailable. Alerts are listed below but cannot be auto-fixed.
>
> **Your code is still protected.** CodeQL's required status check blocks merging of PRs with unresolved security alerts. Fix these issues manually or wait for Devin to come back online and re-run this workflow.

The workflow validates API availability at startup (health check), enters degraded mode gracefully, and never crashes or blocks the PR.

## DX: Developer Experience That Doesn't Suck

We solved every annoyance from the first iteration:

| Problem | Before | After |
|---------|--------|-------|
| Comment flood | 14 duplicate bot comments | **1 comment**, edited in-place |
| Infinite loops | 41 workflow runs chasing the same alert | **Max 2 attempts** per alert, then marked unfixable |
| No visibility | "Devin is working on it" (where? what?) | Links to Devin session, commits tab, files changed |
| Silent failures | Unfixable alerts disappeared | **"REQUIRES MANUAL REVIEW"** table with severity, rule, file |
| No merge signal | Developer guesses if it's safe | Clear **safe-to-merge** or **needs-review** status |
| Resource waste | 8 sessions for 6 alerts | Idempotent sessions, ACU caps, attempt tracking |

## What You Get

1. **Drop-in GitHub Action** — add the workflow file, set 2 secrets (`GH_PAT`, `DEVIN_API_KEY`), done
2. **Works with any Python project** (extensible to JS/TS, Java, Go, C/C++)
3. **Zero config** — uses your existing CodeQL setup or provides one
4. **Non-blocking** — never delays your PR, runs in parallel
5. **Self-healing** — gracefully degrades when Devin is down, recovers automatically
6. **Auditable** — every fix is a separate commit with the CodeQL rule ID in the message

## The Numbers (from real testing)

| Metric | Before (manual) | After (automated) |
|--------|-----------------|-------------------|
| Alerts detected | 10 | 10 |
| Alerts auto-fixed | 0 | **9/10 (90%)** |
| Time to first fix | Hours (developer queue) | **~15 minutes** |
| PR comments | 14 (noise) | **1** (signal) |
| Workflow runs wasted | 41 | **2** (detect + verify) |
| Developer effort | Review + fix each alert | Review Devin's commits |

## One More Thing

Pre-existing alerts — the ones already on `main` that nobody wants to deal with — get fixed too. The workflow detects them, batches them by file, and creates a separate fix branch. Your PR stays clean, and your security debt shrinks with every review.

---

*Built with Devin by Cognition AI. The workflow, design docs, and this pitch are open source.*
