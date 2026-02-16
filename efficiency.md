# Devin Platform Efficiency Guide

Ideas for using the Devin platform more effectively in our automated security review workflow.

---

## 1. Separation of Concerns: Prompt vs Playbook vs Knowledge vs Snapshot

The session prompt should only describe **what** needs to be done. The **how** belongs in Playbooks, repo-specific context belongs in Knowledge, and environment setup belongs in Snapshots.

### Current Problem

Our workflow embeds everything into a single session prompt: the task description, the methodology, the guardrails, the PR format, and repo-specific commands. This makes prompts bloated, hard to maintain, and inconsistent across runs.

### Proposed Structure

| Layer | Responsibility | Example |
|-------|---------------|---------|
| **Prompt** | The "what" — task-specific, changes every run | `"Fix the following CodeQL findings in {repo}: [SARIF attachment]"` |
| **Playbook** | The "how" — methodology, guardrails, PR format | Fix-verify-test loop, commit-per-alert convention, PR body template, "never suppress alerts" rule |
| **Knowledge** | Repo-specific context | Test commands (`pytest -x`), linting config, ORM conventions, branch naming rules |
| **Snapshot** | Environment pre-installed | Python deps, CodeQL CLI, repo cloned, virtualenv ready |

### Why This Matters

- **Playbooks are reusable** across repos and teams. Write the security fix methodology once, apply everywhere.
- **Knowledge scales per-repo** without touching the playbook. Adding a new customer repo means adding a Knowledge entry, not editing a prompt template.
- **Snapshots eliminate cold-start time.** Devin doesn't spend 5 minutes installing CodeQL CLI and pip dependencies on every session.
- **Prompts become trivial.** The GitHub Action only needs to pass the SARIF data and target repo. Everything else is already configured.

### Devin Should Give Feedback on Suboptimal Prompts

When a session prompt is too long or mixes concerns, Devin should flag it and suggest breaking it down:
- "This prompt includes methodology instructions that would be better as a Playbook."
- "This prompt includes repo-specific test commands that would be better as a Knowledge entry."
- "Consider splitting this into 3 smaller sessions for better reliability."

This feedback loop helps teams adopt the platform's layered architecture incrementally rather than requiring perfect prompt engineering upfront.

---

## 2. v3 API and Advanced Mode Batch Sessions

### Recommendation

Use the v3 API and Advanced Mode batch sessions instead of looping through sessions in a Python script. Upload the SARIF as an attachment and let Devin's batch mode handle the fan-out.

### Why This Is Better

- **More elegant**: One API call with `advanced_mode: "batch"` + a `child_playbook_id` replaces our entire Python loop that creates sessions one-by-one with sleep/retry logic.
- **More resilient**: Devin's batch infrastructure handles session scheduling, concurrency limits, and failure recovery natively. Our custom retry/backoff code becomes unnecessary.
- **Shows deep product knowledge**: Using batch mode demonstrates we understand Devin's architecture, which matters for credibility when selling this to customers.
- **`bypass_approval: true`** enables fully automated workflows where sessions start immediately without manual approval — exactly what our CI pipeline needs.

### Plan Requirements

Advanced Mode (including batch sessions) is available on the **Team and Enterprise plans**. The v3 API requires service user credentials with RBAC. Before adopting this approach:

1. Confirm the account is on the Team or Enterprise plan (Advanced Mode requires `UseDevinExpert` permission, included in default `org_member` and `org_admin` roles).
2. Create a service user with the appropriate organization-level role for v3 API access.
3. The v1 API (`apk_` key) we currently use works for session creation but does not support the `advanced_mode` parameter — migration to v3 is required for batch mode.

### Current vs Proposed Flow

**Current (v1 API + Python loop):**
```
GitHub Action -> Python script -> for alert_batch in batches: -> POST /v1/sessions (one by one) -> sleep(30) -> retry on failure
```

**Proposed (v3 API + batch mode):**
```
GitHub Action -> POST /v3beta1/organizations/{org_id}/sessions (advanced_mode: "batch", child_playbook_id: "...", bypass_approval: true, attachment: SARIF)
```

---

## 3. CodeQL Verification Before PR Creation: The Trust-Building Requirement

### Why This Is Non-Negotiable

Testing fixes against CodeQL before offering a PR is the single most important trust-building feature for this MVP. Without it, we're asking humans to trust that an AI fix didn't introduce a new vulnerability — which is exactly the trust problem that blocks adoption.

### The Trust Equation

```
Fix PR created -> Human reviewer sees it -> Reviewer asks: "Did this actually fix the issue?"
  -> If CodeQL passes on first try: "Yes, I can trust this tool."
  -> If CodeQL fails: "This tool is creating busywork. I'll ignore future PRs."
```

In a Fortune 500 setting, a stream of failing fix PRs destroys confidence in the tool permanently. It's easier to never adopt than to un-adopt.

### What We Already Have (DESIGN.md)

Our design specifies a two-layer verification:
1. **Layer 1 (Devin prompt)**: Devin runs CodeQL CLI internally before committing.
2. **Layer 2 (Pipeline gate)**: Post-session workflow step runs CodeQL with exact CI config before PR creation.

### What We Need to Guarantee

- Every fix PR that gets created passes CodeQL CI on the first try.
- If internal verification fails after 2 attempts, the alert is skipped — no broken fix is committed.
- The pipeline gate blocks PR creation if any new alerts are detected in modified files.
- PR body includes a `codeql-verified` label and verification results section.

This is not a "nice to have." It is a prerequisite for customer adoption.

---

## 4. Failure Mode Analysis for MVP

Not all failure modes are equally relevant for the MVP. Here's an assessment of each:

### Relevant for MVP — Must Address

| Failure Mode | Risk Level | Why It Matters | Mitigation |
|-------------|-----------|---------------|------------|
| **Devin's fix is wrong and tests pass anyway** (low test coverage) | HIGH | This is the most insidious failure — the fix looks good, tests pass, but the vulnerability is still there or a new one was introduced. Silent failures erode trust without anyone noticing until a security audit. | The two-layer CodeQL verification loop is our primary defense. Layer 2 (pipeline gate) runs CodeQL deterministically regardless of test coverage. This is why CodeQL verification before PR is non-negotiable — tests alone are not sufficient for security fixes. |
| **Devin can't fix a finding** (hangs, empty PR, unclear failure) | HIGH | If Devin can't fix something, we need a clear signal — not silence. A hanging session wastes ACUs. An empty PR wastes reviewer time. No signal at all means the alert falls through the cracks. | The internal retry loop gives Devin 2 attempts. If both fail, the alert is skipped (not committed). The PR comment should explicitly list skipped alerts with the reason. For session hangs, the workflow has a 60-minute timeout and terminates stale sessions. Consider filing a GitHub issue for unfixable alerts so they're tracked. |
| **The GitHub Action hits rate limits on the Devin API** (creating 20 sessions at once) | MEDIUM | Our batching strategy already creates max 3 concurrent sessions with 30s pauses between waves. But a repo with 100+ pre-existing alerts could still hit API rate limits across multiple workflow runs, especially during initial onboarding when the backlog is large. | Current mitigations: 3 concurrent sessions, 30s inter-wave pause, max 20 sessions per run. Additional: implement exponential backoff on 429 responses, add a daily session cap for the initial backlog burn-down phase. The v3 batch mode (see section 2) would handle this natively. |
| **Two pushes happen in quick succession and both trigger the action** (race condition) | MEDIUM | Developer pushes a fix, then immediately pushes again. Both pushes trigger CodeQL + Devin workflows. The second run may see alerts that the first run is already fixing, creating duplicate sessions and conflicting fix commits on the same branch. | Idempotency key on session creation helps but doesn't fully solve it (see DESIGN.md Bug #2). Better: use GitHub's `concurrency` key on the workflow to cancel in-progress runs when a new push arrives. The latest push always gets the most current alert state. |

### Less Relevant for MVP — Defer or Document

| Failure Mode | Risk Level | Why It's Deferred | Notes |
|-------------|-----------|-------------------|-------|
| **Customer's repo requires VPN access** | LOW for MVP | Devin VPN configuration is a whole separate infrastructure setup that varies per customer. This is an enterprise deployment concern, not an MVP workflow concern. | Document it as a known limitation. Devin does support VPN config, but it requires per-customer setup. Don't try to solve this generically in the MVP — handle it case-by-case during onboarding. |
| **CodeQL times out on a huge monorepo** | LOW for MVP | Our MVP targets repos where CodeQL already runs successfully in CI. If CodeQL can't complete, that's a repo-level infrastructure problem, not a workflow problem. | The workflow should handle partial SARIF results gracefully (process whatever alerts are available rather than failing entirely). But optimizing CodeQL performance on monorepos is out of scope — that's a customer prerequisite, not our problem to solve. |

### Summary

The MVP must handle the first four failure modes robustly. The last two are real but belong to the deployment/onboarding phase, not the core workflow. Documenting them as known limitations is sufficient for now.

---

## 5. Additional Efficiency Ideas

### Snapshot Pre-warming

Create a base snapshot with:
- CodeQL CLI pre-installed
- Common Python security libraries (e.g., `defusedxml`, `markupsafe`)
- Repo already cloned and indexed

This eliminates 3-5 minutes of setup time per session. For a workflow creating 7 sessions per run, that's 20-35 minutes saved.

### Playbook Iteration via Advanced Mode

Use Advanced Mode's `analyze` and `improve` capabilities:
1. Run initial security fix sessions.
2. Use `analyze` mode to review session outcomes (which fixes passed, which failed, why).
3. Use `improve` mode to refine the playbook based on failure patterns.
4. Repeat. The playbook gets better with every iteration.

This creates a feedback loop where the playbook self-improves based on real results.

### Session Insights for Prompt Optimization

After each batch run, review Session Insights to identify:
- Which prompts led to successful fixes vs failures
- Common patterns in failed sessions (missing context, wrong approach)
- Opportunities to move recurring instructions from prompts into Knowledge entries

---

## 6. Checklist: Platform Adoption Maturity

| Level | Description | What to Configure |
|-------|------------|-------------------|
| **L0 — Basic** | Session prompt contains everything | Nothing beyond API key |
| **L1 — Structured** | Prompt is task-only, Playbook handles methodology | Create a Playbook for the fix-verify-test loop |
| **L2 — Contextualized** | Knowledge entries per repo | Add Knowledge for test commands, conventions, branch rules |
| **L3 — Optimized** | Snapshots pre-warm environments | Create Snapshot with CodeQL CLI + deps pre-installed |
| **L4 — Autonomous** | v3 batch mode, self-improving playbooks | Migrate to v3 API, enable Advanced Mode feedback loop |

We are currently at **L0**. The goal is to reach **L2** for the MVP and **L4** for production.
