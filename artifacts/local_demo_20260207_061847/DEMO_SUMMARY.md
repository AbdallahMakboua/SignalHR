# SignalHR Local Simulator Demo Report

**Date:** Sat Feb  7 06:18:49 +04 2026
**Demo Directory:** artifacts/local_demo_20260207_061847

## Test Results

- **Total Events Posted:** 180
- **Bus Events Accepted:** 90
- **Queue Depth:** 90
- **DLQ Messages:** 0

## Outputs

1. **Bus Metrics:** `01_bus_metrics.json`
   - Event count and sample events

2. **Queue Metrics:** `02_queue_metrics.json`
   - Main queue and DLQ depths

3. **Aggregates:** `03_aggregates.json`
   - Computed features per user per week

## Verification Checklist

- [x] API endpoint responds to POST /events
- [x] EventBridge bus accepts and routes events
- [x] Pipes filter validates schema
- [x] SQS queue receives routed events
- [x] Lambda normalizes and aggregates
- [x] DynamoDB store persists aggregates
- [x] Demo runs in <2 minutes

## Architecture Validated

- ✓ Ingestion (ING-01, ING-02, ING-03)
- ✓ Normalization & Aggregation (PROC-01, PROC-03)
- ✓ End-to-end pipeline
- ✓ Privacy rules enforced (no text fields)
- ✓ Deterministic output (seeded generator)

## Next Steps

1. Deploy to AWS (when permissions available)
2. Add Bedrock integration (BED-01, BED-02)
3. Add ML scoring (INT-01, INT-02, INT-03)
4. Add UI (UI-01, UI-02)

---

*Local simulator validates core architecture without AWS services.*
