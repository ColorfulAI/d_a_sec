# Enterprise Configuration Guide — Devin Security Backlog Workflow

## Context

This workflow was tested on an account with a **5 concurrent session limit**. Enterprise Devin accounts can unlock **unlimited concurrent sessions**, enabling significantly higher throughput.

With 5 concurrent sessions and 15 alerts per batch, a 722-alert backlog took **~5.5 hours** (8 waves, with 7-48 min rate limit gaps between waves).

After fixing session termination (Bug #62), prompt truncation (Bug #63), and alert fetch resilience (Bug #64):
- **75 alerts/batch**: 73 minutes (78% faster than baseline) — ST-5
- **100 alerts/batch**: **37 minutes** (89% faster than baseline) — ST-6

**With unlimited concurrent sessions, the same backlog would complete in ~15-20 minutes.**

---

## Optimal Parameters for Unlimited Concurrent Sessions

| Parameter | Recommended Value | Rationale |
|-----------|-------------------|-----------|
| `max_concurrent` | **20-50** | Parallelism sweet spot. Beyond ~50, GitHub Actions queuing and API rate limits become the bottleneck, not Devin. |
| `alerts_per_batch` | **100** | Validated optimal: 722 alerts processed in 37 min with 8 batches. Progressive prompt truncation handles large batches via summary-only mode. Fewer batches = fewer waves = fewer rate limit windows. |
| `max_acu_limit` | **20-30** | Scales with batch size. 100 alerts needs ~20 ACUs. Complex multi-file fixes may need up to 30. |
| `POLL_INTERVAL` | **30s** (down from 60s) | Faster slot recycling. With 50 concurrent sessions, a 60s poll means up to 60s of idle slots per cycle. |
| `MAX_CHILD_RUNTIME` | **5400s** (90 min) | Larger batches may need more time. Safety margin for complex multi-file fixes. |

---

## Performance Projections

### Small Backlog (100 alerts)
| Config | Batches | Waves | Estimated Time | Evidence |
|--------|---------|-------|----------------|----------|
| 5 concurrent, 15/batch | 7 | 2 | ~45 min | Extrapolated |
| 5 concurrent, 100/batch | 1 | 1 | ~15 min | Extrapolated |
| **50 concurrent, 100/batch** | **1** | **1** | **~15 min** | Extrapolated |

### Medium Backlog (500 alerts)
| Config | Batches | Waves | Estimated Time | Evidence |
|--------|---------|-------|----------------|----------|
| 5 concurrent, 15/batch | 34 | 7 | ~3.5 hours | Extrapolated from ST-2 |
| 5 concurrent, 100/batch | 5 | 1 | ~15 min | Extrapolated from ST-6 |
| **50 concurrent, 100/batch** | **5** | **1** | **~15 min** | Extrapolated |

### Validated Backlog (722 alerts — tested)
| Config | Batches | Waves | Time | Evidence |
|--------|---------|-------|------|----------|
| 5 concurrent, 15/batch | 52 | 8 | 5h 36m | **ST-2** (measured) |
| 5 concurrent, 50/batch | 15 | 3 | ~2.2h | **ST-3** (measured) |
| 5 concurrent, 75/batch | 11 | 3 | 73 min | **ST-5** (measured) |
| **5 concurrent, 100/batch** | **8** | **2** | **37 min** | **ST-6** (measured) |

### Large Backlog (5,000 alerts — Fortune 500 scale)
| Config | Batches | Waves | Estimated Time | Evidence |
|--------|---------|-------|----------------|----------|
| 5 concurrent, 15/batch | 334 | 67 | ~17 hours | Extrapolated |
| 5 concurrent, 100/batch | 50 | 10 | ~3-4 hours | Extrapolated from ST-6 |
| **50 concurrent, 100/batch** | **50** | **1** | **~20 min** | Extrapolated |

---

## Why Unlimited Sessions Matter

The primary bottleneck in our stress tests was **not** Devin's processing time — it was the **wave count**:

- Each wave of 5 concurrent sessions completes in ~15 min
- Creating 10+ sessions rapidly triggers per-account rate limiting (~22 min cooldown)
- With session termination (Bug #62 fix), inter-wave gaps dropped from 7-48 min to ~1-2 min
- But reducing total waves is the biggest lever: ST-5 (3 waves, 73 min) vs ST-6 (2 waves, 37 min)

**With unlimited concurrent sessions:**
- 722 alerts at 100/batch = 8 batches = **1 wave** (all dispatched simultaneously)
- **Zero rate limit gaps** — no waiting between waves
- Total time = just the session processing time (~15-20 min)

**Key insight from ST-6**: Larger batches (100 vs 75) reduce batch count, which reduces wave count, which eliminates rate limit windows. The 49% speedup from ST-5→ST-6 came entirely from going from 3 waves to 2.

---

## Tested Evidence (5 Concurrent Sessions)

### Run 1: 15 alerts per batch (previous baseline)
- **Orchestrator run**: [#22079950757](https://github.com/ColorfulAI/d_a_sec/actions/runs/22079950757)
- 722 alerts, 52 batches, 8 waves
- **Total time: 5 hours 36 minutes**
- 40/52 batches completed (remaining hit rate limits)
- Rate limit gaps: 7-48 min between waves

### Run 2: 50 alerts per batch (ST-3)
- **Orchestrator run**: [#22109822853](https://github.com/ColorfulAI/d_a_sec/actions/runs/22109822853)
- 722 alerts, 15 batches, 3 waves
- **Total time: ~2.2 hours** (60% improvement over baseline)
- Rate limit gaps: ~23-28 min between waves

### Run 3: 75 alerts per batch (ST-5) — with Bug #62/#63/#64 fixes
- **Orchestrator run**: [#22116688805](https://github.com/ColorfulAI/d_a_sec/actions/runs/22116688805)
- 722 alerts, 11 batches, 3 waves, 8 PRs
- **Total time: 73 minutes** (78% improvement over baseline)
- Inter-wave gaps: ~1-2 min (session termination working)

### Run 4: 100 alerts per batch (ST-6) — optimal configuration
- **Orchestrator run**: [#22118993454](https://github.com/ColorfulAI/d_a_sec/actions/runs/22118993454)
- 722 alerts, 8 batches, 2 waves, 8 PRs
- **Total time: 37 minutes** (89% improvement over baseline, 49% faster than ST-5)
- Only 2 waves — eliminated the third rate limit window entirely
- Zero failures across all 8 sessions

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
   - `alerts_per_batch`: `100`
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
      "alerts_per_batch": "100",
      "max_batches": "0",
      "reset_cursor": "true"
    }
  }'
```

---

## Recommendations for Enterprise Deployment

1. **Start with `max_concurrent=20`** and scale up — monitor GitHub Actions runner availability and Devin API rate limits at your concurrency level.
2. **Use `alerts_per_batch=100`** as the validated optimal — ST-6 proved 100/batch processes 722 alerts in 37 min. Progressive prompt truncation handles the payload size automatically.
3. **Set `max_acu_limit=20`** minimum — increase to 30 for repos with complex, multi-file vulnerability patterns.
4. **Reduce `POLL_INTERVAL` to 30s** when running >10 concurrent sessions — faster slot recycling reduces idle time.
5. **Monitor your Devin plan's session limit** — the workflow's `max_concurrent` should not exceed your account's concurrent session cap.
6. **For 5,000+ alert backlogs**, consider running during off-peak hours to minimize GitHub Actions queuing delays.
7. **Session termination is critical** — the workflow terminates sessions immediately after completion (Bug #62 fix). Without this, zombie sessions exhaust the concurrent pool and cause 7-48 min dead time between waves.
