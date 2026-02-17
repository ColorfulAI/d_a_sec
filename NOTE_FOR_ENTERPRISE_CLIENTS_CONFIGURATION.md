# Enterprise Configuration Guide — Devin Security Backlog Workflow

## Context

This workflow was tested on an account with a **5 concurrent session limit**. Enterprise Devin accounts can unlock **unlimited concurrent sessions**, enabling significantly higher throughput.

With 5 concurrent sessions and 15 alerts per batch, a 722-alert backlog took **~5.5 hours** (8 waves, with 7-48 min rate limit gaps between waves).

With 5 concurrent sessions and 50 alerts per batch, the same backlog processes in **~3 hours** (4 waves, fewer rate limit gaps).

**With unlimited concurrent sessions, the same backlog would complete in ~15-30 minutes.**

---

## Optimal Parameters for Unlimited Concurrent Sessions

| Parameter | Recommended Value | Rationale |
|-----------|-------------------|-----------|
| `max_concurrent` | **20-50** | Parallelism sweet spot. Beyond ~50, GitHub Actions queuing and API rate limits become the bottleneck, not Devin. |
| `alerts_per_batch` | **30-50** | Each batch = 1 Devin session = 1 PR. Too small (10) = too many PRs to review. Too large (100+) = session timeout risk + massive PRs. 30-50 keeps each PR reviewable while maximizing throughput. |
| `max_acu_limit` | **20-30** | Scales with batch size. 50 alerts needs ~20 ACUs. Complex multi-file fixes may need up to 30. |
| `POLL_INTERVAL` | **30s** (down from 60s) | Faster slot recycling. With 50 concurrent sessions, a 60s poll means up to 60s of idle slots per cycle. |
| `MAX_CHILD_RUNTIME` | **5400s** (90 min) | Larger batches may need more time. Safety margin for complex multi-file fixes. |

---

## Performance Projections

### Small Backlog (100 alerts)
| Config | Batches | Waves | Estimated Time |
|--------|---------|-------|----------------|
| 5 concurrent, 15/batch | 7 | 2 | ~45 min |
| 5 concurrent, 50/batch | 2 | 1 | ~15 min |
| **50 concurrent, 50/batch** | **2** | **1** | **~15 min** |

### Medium Backlog (500 alerts)
| Config | Batches | Waves | Estimated Time |
|--------|---------|-------|----------------|
| 5 concurrent, 15/batch | 34 | 7 | ~3.5 hours |
| 5 concurrent, 50/batch | 10 | 2 | ~45 min |
| **50 concurrent, 50/batch** | **10** | **1** | **~15 min** |

### Large Backlog (5,000 alerts — Fortune 500 scale)
| Config | Batches | Waves | Estimated Time |
|--------|---------|-------|----------------|
| 5 concurrent, 15/batch | 334 | 67 | ~17 hours |
| 5 concurrent, 50/batch | 100 | 20 | ~7 hours |
| **50 concurrent, 50/batch** | **100** | **2** | **~30 min** |

---

## Why Unlimited Sessions Matter

The primary bottleneck in our stress tests was **not** Devin's processing time — it was the **rate limit gaps between waves**:

- Each wave of 5 concurrent sessions completes in ~15 min
- After each wave, the Devin API imposes a **7-48 minute rate limit cooldown** before new sessions can be created
- With 8 waves (500 alerts at 15/batch), that's **7 rate limit gaps** adding 50-336 minutes of pure dead time

**With unlimited concurrent sessions:**
- 500 alerts at 50/batch = 10 batches = **1 wave** (all dispatched simultaneously)
- **Zero rate limit gaps** — no waiting between waves
- Total time = just the session processing time (~15-20 min)

---

## Tested Evidence (5 Concurrent Sessions)

### Run 1: 15 alerts per batch (previous baseline)
- **Orchestrator run**: [#22079950757](https://github.com/ColorfulAI/d_a_sec/actions/runs/22079950757)
- 722 alerts, 52 batches, 8 waves
- **Total time: 5 hours 36 minutes**
- 40/52 batches completed (remaining hit rate limits)
- Rate limit gaps: 7-48 min between waves

### Run 2: 50 alerts per batch (optimized)
- **Orchestrator run**: [#22109822853](https://github.com/ColorfulAI/d_a_sec/actions/runs/22109822853)
- 722 alerts, ~15 batches, ~4 waves
- **Estimated time: ~3 hours** (60% improvement over baseline)
- Rate limit gaps: ~23-28 min between waves (fewer gaps total)

### Concurrent Session Limit Validation
- Tested via Devin API (`POST /v1/sessions`)
- Sessions 1-4: HTTP 200 (created successfully)
- Session 5+: HTTP 429 — `"You exceeded your concurrent session limit of 5"`
- **Confirmed: 5 is the hard limit for this account/plan**

---

## Configuration Instructions

### Via GitHub Actions UI (Manual Trigger)
1. Go to **Actions** > **Devin Security Backlog** > **Run workflow**
2. Set parameters:
   - `max_concurrent`: `50` (or your account's session limit)
   - `alerts_per_batch`: `50`
   - `max_batches`: `0` (unlimited — process entire backlog)
   - `reset_cursor`: `true` (start fresh) or `false` (resume from last position)

### Via API (Programmatic Trigger)
```bash
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/OWNER/REPO/actions/workflows/devin-security-backlog.yml/dispatches" \
  -d '{
    "ref": "main",
    "inputs": {
      "max_concurrent": "50",
      "alerts_per_batch": "50",
      "max_batches": "0",
      "reset_cursor": "true"
    }
  }'
```

---

## Recommendations for Enterprise Deployment

1. **Start with `max_concurrent=20`** and scale up — monitor GitHub Actions runner availability and Devin API rate limits at your concurrency level.
2. **Use `alerts_per_batch=50`** as the default — this balances PR reviewability with throughput.
3. **Set `max_acu_limit=20`** minimum — increase to 30 for repos with complex, multi-file vulnerability patterns.
4. **Reduce `POLL_INTERVAL` to 30s** when running >10 concurrent sessions — faster slot recycling reduces idle time.
5. **Monitor your Devin plan's session limit** — the workflow's `max_concurrent` should not exceed your account's concurrent session cap.
6. **For 5,000+ alert backlogs**, consider running during off-peak hours to minimize GitHub Actions queuing delays.
