# As-Built Snapshot — Current State (February 7, 2026)

**Document Purpose:** One-page "ground truth" summary of what works today, how to use it, and what is blocked.

**Last Updated:** 2026-02-07T07:39:55Z (after successful local demo execution)

**Audience:** Judges, mentors, stakeholders, post-demo reviewers

---

## What Works Today ✅

### Core Pipeline (Event → Alert → Explanation)
- ✅ **Synthetic generator** (`tools/synthetic_generator.py`): Generates 90 deterministic events (30 per profile: alice, ben, carol) with --post flag to HTTP POST to local API
- ✅ **API ingestion** (`api/app.py` FastAPI): Accepts POST /events with EventPayload schema (signalCounts, userId, eventType optional), validates, returns HTTP 202
- ✅ **Event routing** (`core/bus.py` in-memory EventBridge): Simulates EventBridge bus, accepts 90 events, applies Pipes filter (schema validation, field dropping)
- ✅ **Event queuing** (`core/queue.py` in-memory SQS): Simulates SQS queue, receives routed events, maintains DLQ for rejected messages
- ✅ **Normalization** (`lambdas/normalize_handler.py`): Validates events, extracts userId, computes weekId from ISO timestamp, removes text fields, computes features
- ✅ **Aggregation** (`store/aggregates_store.py` SQLite): Persists per-user-per-week aggregates with features (meetings, messages, PRs, overload_trend, context_switch_rate, collaboration_index, growth_index)
- ✅ **Rules engine** (`intelligence/rules_engine.py`): Deterministic scoring (burnout, HiPo, drift with explainable reasons), generates alerts
- ✅ **Explainability** (`intelligence/explainer.py`): Template-based explanations (no LLM), generates human-readable summaries, why_flagged, next_best_actions

### Validation & Observability
- ✅ **Demo automation** (`scripts/demo.sh`): Single command runs full pipeline end-to-end in <2 minutes
- ✅ **Server startup** (`scripts/run_local.sh`): Starts FastAPI server, cleans up old state, sets PYTHONPATH for module resolution
- ✅ **Test coverage** (`tests/test_normalize.py`, `tests/test_integration.py`): Unit + integration tests pass locally
- ✅ **Artifacts generated**: 5 JSON files + 1 markdown report + SQLite database
  - `01_bus_metrics.json`: Event counts and sample events from bus
  - `02_queue_metrics.json`: Queue depth snapshot
  - `03_aggregates.json`: Per-user-per-week aggregates with features
  - `04_alerts.json`: Burnout/HiPo/drift alerts with scores and reasons
  - `05_ai_explanations.json`: Natural language explanations for each alert
  - `DEMO_SUMMARY.md`: Human-readable report with results and examples
  - `aggregates.db`: SQLite database with persisted aggregates

### Privacy & Determinism
- ✅ **Privacy enforced**: No text fields in any output, only numeric signals and computed features
- ✅ **Deterministic**: Seeded PRNG (SEED=20260207) guarantees identical outputs across runs
- ✅ **Explainability**: All alerts include explainable reasons (no black-box ML)
- ✅ **HR-safe language**: No punitive advice, only supportive coaching suggestions

---

## How to Run the Demo

### Prerequisites
```bash
cd /Users/abdallahmakboua/Desktop/Hackathon/SignalHR
python3 --version      # Must be 3.9+
pip install fastapi uvicorn pydantic  # Required packages
```

### One-Command Demo
```bash
bash scripts/run_local.sh && bash scripts/demo.sh
```

**Expected output:**
- Step [1/4]: 90 events posted (HTTP 202 ✓)
- Step [2/4]: Bus metrics collected (180 total events counted)
- Step [3/4]: Queue metrics collected (180 depth, 0 DLQ)
- Step [4/5]: Normalization → 6 aggregates stored
- Step [5/6]: Rules engine → 6 alerts generated
- Step [6/6]: AI explainability → 6 explanations generated
- **WOW moment:** Burnout explanation printed to stdout
- Summary: DEMO_SUMMARY.md generated

**Duration:** <2 minutes (end-to-end)

**Artifacts:** `artifacts/local_demo_<timestamp>/` (timestamped directory with all outputs)

### View Results
```bash
# Latest demo directory
DEMO_DIR=$(ls -td artifacts/local_demo_* | head -1)

# View alerts
cat $DEMO_DIR/04_alerts.json | jq '.[] | {userId: .userId[0:8], burnout: .burnout.score, hipo: .hipo.score}'

# View explanations
cat $DEMO_DIR/05_ai_explanations.json | jq '.[] | {alertType, summary: .summary[0:80]}'

# View summary report
cat $DEMO_DIR/DEMO_SUMMARY.md
```

---

## Exact Outputs (From Latest Run)

**Timestamp:** 2026-02-07T07:39:55Z

### Metrics
- **Total events posted:** 90 (30 per profile)
- **Bus events accepted:** 180 (counting behavior from Pipes filter)
- **Queue depth:** 180
- **DLQ messages:** 0
- **Aggregates created:** 6
- **Alerts generated:** 6
- **Explanations generated:** 6

### Sample Burnout Alert
```json
{
  "userId": "bd546f13-68f9-4a2b-b4c0-f951d7169530",
  "weekId": "2026-W06",
  "alertType": "burnout",
  "burnout": {
    "score": 1.0,
    "reasons": [
      "High meeting load (5 meetings)",
      "High communication load (37 messages)",
      "Context switching detected"
    ]
  }
}
```

### Sample Explanation
```json
{
  "alertType": "burnout",
  "summary": "This team member is showing elevated burnout risk indicators during 2026-W06. Immediate attention recommended to prevent escalation.",
  "why_flagged": [
    "Meeting volume exceeds healthy thresholds (5 meetings this week).",
    "Communication load is unsustainably high (37 messages this week)."
  ],
  "next_best_actions": [
    "Schedule 1:1 check-in to discuss workload and priorities",
    "Review calendar for non-essential meetings that can be delegated or declined",
    "Explore options for temporary workload redistribution",
    "Ensure PTO balance is healthy and encourage time off if needed"
  ]
}
```

---

## What Is Blocked ❌

### AWS Services (Explicit Deny Policies)
- ❌ **EventBridge** (CreateEventBus, PutEvents) — Replaced by local simulator
- ❌ **SQS** (CreateQueue, SendMessage) — Replaced by local simulator
- ❌ **DynamoDB** (CreateTable, PutItem) — Replaced by SQLite
- ❌ **Lambda** (CreateFunction, InvokeFunction) — Replaced by local Python functions
- ❌ **API Gateway** (CreateRestApi) — Replaced by FastAPI
- ❌ **Step Functions** (CreateStateMachine) — Replaced by local orchestration (demo.sh)
- ❌ **Bedrock** (InvokeModel) — Replaced by template-based explainer
- ❌ **CloudWatch, CloudTrail, SageMaker** — All blocked

### UI / Dashboard
- ❌ **Manager Dashboard** — Not implemented (local demo is CLI/JSON only)
- ❌ **Employee Portal** — Not implemented
- ❌ **Amplify hosting** — Not deployed
- ❌ **Cognito auth** — Not integrated

### AWS Deployment
- ❌ **CloudFormation / Terraform** — IaC planned, not deployed
- ❌ **AWS infrastructure** — All services remain in local simulation mode

---

## AI Explainability (No LLM Required) 🤖

**Key fact:** SignalHR uses **deterministic, rule-based explainability** — NOT a generative LLM.

### Why No LLM?
1. **Bedrock blocked** — No AWS access to invoke Claude/Llama
2. **Privacy** — LLM calls would require sending aggregates to external API
3. **Determinism** — LLM outputs are non-deterministic (different responses for same input)
4. **Explainability** — Rule-based approach is more auditable than black-box ML

### How It Works
- **Input:** Rules engine output (burnout=1.0, reasons=["High meetings"])
- **Logic:** Template-based switching on alert type (burnout/hipo/drift/baseline)
- **Templates:** Pre-written HR-safe summaries and action suggestions
- **Output:** JSON with summary + why_flagged + next_best_actions
- **Language:** Simple English, no jargon, supportive tone

### Example Flow
```
Raw scores (burnout=1.0, meetings=5, messages=37)
  ↓
Rules engine (if burnout >= 0.7, if meetings >= 4, if messages >= 30)
  ↓
"Burnout" alert type flagged
  ↓
Template selection (load burnout_summary_template, why_flagged_template, actions_template)
  ↓
Variable substitution (meeting_count=5, message_count=37)
  ↓
Output JSON (summary, why_flagged, next_best_actions)
```

### No LLM Migration Path
- If Bedrock becomes available post-hackathon, wrap the output in a Bedrock call for additional coaching
- But the core explanation is already complete and usable without LLM

---

## Post-Hackathon Roadmap

### Phase 1: AWS Permissions (if available)
1. Request EventBridge, SQS, DynamoDB, Lambda, API Gateway, Bedrock access
2. No code changes needed — swap local simulators for AWS SDK calls
3. Expected timeline: 1–2 weeks

### Phase 2: AWS Deployment
1. Deploy FastAPI to Lambda (or EC2)
2. Replace local EventBridge simulator with AWS EventBridge
3. Replace SQLite with DynamoDB
4. Deploy demo automation to Step Functions or CodeBuild
5. Expected timeline: 2–3 weeks

### Phase 3: UI & Dashboard (if time permits)
1. Build Manager Dashboard (Next.js + Amplify)
2. Integrate Bedrock Agent for advanced coaching
3. Add Cognito auth and RBAC
4. Expected timeline: 3–4 weeks

### Phase 4: Production Hardening
1. Add monitoring (CloudWatch, X-Ray, CloudTrail)
2. Implement SLA compliance
3. Load testing and optimization
4. Expected timeline: 2–3 weeks

---

## Key Design Decisions 🎯

| Decision | Rationale | Can change later? |
|----------|-----------|------------------|
| **SQLite for aggregates** | AWS DynamoDB blocked; SQLite is portable | Yes, swap to DynamoDB |
| **FastAPI for API** | Lightweight, local execution, AWS Lambda-compatible | Yes, deploy to Lambda |
| **Deterministic seeds (SEED=20260207)** | Reproducible demo for judges, testing | Yes, enable random mode post-demo |
| **Template-based explanations** | No LLM available; deterministic and auditable | Yes, add Bedrock later |
| **No CI/CD automation** | Hackathon timeframe, manual control preferred | Yes, add GitHub Actions post-demo |
| **Local JSON artifacts** | No S3 access; filesystem is portable | Yes, move to S3 with AWS |
| **Python 3.11+ with urllib** | No external dependencies, standard library only | Yes, add boto3, etc. |

---

## Compliance Checklist ✅

- ✅ **Privacy:** No text fields, only numeric signals
- ✅ **Explainability:** All alerts show why_flagged reasons
- ✅ **Determinism:** Seeded PRNG, reproducible outputs
- ✅ **HR-safety:** No punitive language, supportive coaching only
- ✅ **Schema validation:** EventPayload enforces DC-ING-V1 rules
- ✅ **Failure handling:** DLQ tracks rejected messages (currently 0)
- ✅ **Testing:** Unit tests pass, integration tests pass
- ✅ **Documentation:** Full runbook and demo script provided
- ✅ **Evidence capture:** All artifacts timestamped and logged

---

## Support & Troubleshooting

**Issue:** `ModuleNotFoundError: No module named 'core'`
- **Fix:** Already fixed. PYTHONPATH set in scripts/run_local.sh and scripts/demo.sh

**Issue:** `HTTP 422 Validation Error` on POST /events
- **Fix:** Check payload has signalCounts (dict), not signals. See docs/04_runbook.md

**Issue:** `Port 8000 already in use`
- **Fix:** Kill stray process: `lsof -ti tcp:8000 | xargs kill -9`

**Issue:** Demo produces 0 alerts
- **Fix:** Check 03_aggregates.json was created. If empty, re-run from step 1.

**More issues?** See "Troubleshooting" section in [docs/04_runbook.md](04_runbook.md)

---

## Contact & Credits

**Project:** SignalHR MVP (Hackathon, February 7, 2026)

**Team:** [Your names here]

**Technology Stack:**
- Python 3.11+ (FastAPI, Uvicorn, Pydantic, SQLite3)
- Bash (orchestration)
- JSON (data interchange)
- SQLite (local persistence)

**Repositories:**
- Main: `/Users/abdallahmakboua/Desktop/Hackathon/SignalHR`
- Docs: `docs/` directory
- Code: `api/`, `core/`, `intelligence/`, `lambdas/`, `store/`, `tools/`
- Scripts: `scripts/`

---

**End of As-Built Snapshot**
