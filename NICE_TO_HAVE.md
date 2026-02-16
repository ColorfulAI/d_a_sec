# Nice to Have: Configurable Concurrent Session Limit

## Current State
The orchestrator hardcodes a max of 5 concurrent Devin sessions (with a default of 3 active children, reserving 2 slots for PR workflows). This is based on the standard Devin API concurrent session limit.

## Problem
The 5-session limit is not universal across all Devin accounts. Enterprise customers may have higher limits (e.g., 10, 20, or unlimited). Hardcoding 5 means these customers can't utilize their full capacity.

## Proposed Solution

### 1. Workflow Input Override (Quick Win)
Already partially implemented via `max_concurrent` input (capped at 5). Simply raise or remove the cap:
```yaml
max_concurrent:
  description: "Maximum concurrent child workflows (default: 3)"
  required: false
  type: string
  default: "3"
```
The `min(int(...), 5)` cap in the Python code would become configurable.

### 2. API-Based Auto-Detection (Ideal)
Query the Devin API to determine the account's session limit at runtime:
```
GET https://api.devin.ai/v1/account/limits
# or
GET https://api.devin.ai/v1/sessions/limits
```
If such an endpoint exists, the orchestrator could:
1. Query the limit at startup
2. Set `max_concurrent` = limit - 2 (reserving 2 for PR workflows)
3. Log the detected limit for transparency

**Note**: As of now, the Devin API docs don't document a limits endpoint. This would need to be confirmed with Cognition's team.

### 3. Fallback Chain
```
configured_limit = workflow_input OR api_detected_limit OR default(5)
max_children = configured_limit - session_reservation(2)
```

## Implementation Priority
- **Low** — The current default of 3 concurrent children works for standard accounts
- **Revisit** when onboarding enterprise customers with higher Devin session limits
