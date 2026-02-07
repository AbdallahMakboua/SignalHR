# Runbook — How to run, test, and demo the MVP

**CRITICAL:** This runbook is the executable specification for running the SignalHR demo. All commands, outputs, and verification steps are binding. Deviations from this runbook require a documented Change Request in `docs/CHANGE_REQUESTS.md`.

---

## ⚠️ EMERGENCY: LOCAL SIMULATION MODE (CR-2026-003)

**Status:** AWS services blocked by explicit deny policies. Running in LOCAL-SIMULATION MVP mode.

**See:** `docs/CHANGE_REQUESTS.md#CR-2026-003` for full details.

**Quick Start (LOCAL):**
```bash
# 1. Start local simulator (API + EventBridge + SQS)
bash scripts/run_local.sh

# 2. Run demo (3-user scenario)
bash scripts/demo.sh

# Total time: <2 minutes
```

**Outputs:** `artifacts/local_demo_<timestamp>/`
- `01_bus_metrics.json` — EventBridge events
- `02_queue_metrics.json` — SQS queue depth
- `03_aggregates.json` — DynamoDB aggregates
- `DEMO_SUMMARY.md` — Report

**Architecture:** Local Python simulators mirror AWS design. Swap to AWS later when permissions available.

### Python Module Resolution (Local Simulator)

**Status:** ✅ Fixed (BUGFIX applied 2026-02-07)

The local simulator requires Python to discover packages in the repo root. Both `scripts/run_local.sh` and `scripts/demo.sh` automatically set `PYTHONPATH` to resolve imports from `core/`, `api/`, `store/`, and `lambdas/` directories.

**Verification:** Imports resolve correctly
```bash
export PYTHONPATH="/Users/abdallahmakboua/Desktop/Hackathon/SignalHR:${PYTHONPATH:-}"
python3 << 'EOF'
from core.bus import EventBus
from core.queue import QueuePair
from store.aggregates_store import AggregatesStore
from lambdas.normalize_handler import normalize_event
print("✓ All imports successful")
EOF
```

**Expected output:** `✓ All imports successful`

For details on this bugfix, see `docs/BUGFIX_IMPORT_RESOLUTION.md`.

---

## Prerequisites & Environment Validation (Phase 0)

Before starting the demo, verify the environment:

### Required AWS Resources
- AWS account and CLI configured (region: `us-east-1`)
- EventBridge bus: `signalhr-bus-dev`
- SQS queue: `signalhr-ingest-queue-dev` (+ DLQ)
- Lambda function: `signalhr-normalize-dev` (or equivalent name from ING-01 → PROC-01)
- DynamoDB: `AggregatesTable-dev`, `AlertsTable-dev`
- S3 buckets: `signalhr-raw-events-dev`, `signalhr-aggregates-dev`, `signalhr-explanations-dev`, `signalhr-test-reports`
- StepFunctions: `signalhr-rollup-dev` state machine
- SageMaker endpoint: `signalhr-xgb-mvp`
- Bedrock: available and API accessible
- Cognito: `signalhr-userpool-dev` with test users (Manager, Employee, HR)
- Amplify app: deployed to `signalhr-dev.amplifyapp.com` (or custom domain)
- Synthetic generator: `/tools/synthetic_generator.py` or `/tools/synthetic_generator.js`

### Environment Variables (set before demo)
```bash
# NOTE: Project brief defaults to us-east-1. Current execution uses us-east-2 (see DRAFT CR).
export AWS_REGION=us-east-2
export AWS_PROFILE=default  # or your configured profile
export DEMO_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
export DEMO_WEEK=2026-W06  # Fixed week for determinism
export S3_REPORTS=s3://signalhr-test-reports/demo/${DEMO_TIMESTAMP}
export API_ENDPOINT=https://<api-id>.execute-api.us-east-2.amazonaws.com/dev
```

### Validation Commands (run once before demo)
```bash
# Check AWS CLI access
aws sts get-caller-identity

# Verify EventBridge bus exists
aws events describe-event-bus --name signalhr-bus-dev

# Verify SQS queue exists
aws sqs get-queue-url --queue-name signalhr-ingest-queue-dev

# Verify DynamoDB tables exist
aws dynamodb describe-table --table-name AggregatesTable-dev
aws dynamodb describe-table --table-name AlertsTable-dev

# Verify S3 buckets exist

# Test synthetic generator locally (no AWS required)
cd /Users/abdallahmakboua/Desktop/Hackathon/SignalHR
python3 tools/synthetic_generator.py --profile alice --rate 10 --duration 0.01 --dry-run | head -5

# Test normalization handler locally (no AWS required)
python3 -m pytest tests/test_normalize.py -v
aws s3 ls signalhr-raw-events-dev/
aws s3 ls signalhr-aggregates-dev/

# Verify Cognito user pool exists
aws cognito-idp describe-user-pool --user-pool-id <pool-id>

# Verify SageMaker endpoint is active
aws sagemaker describe-endpoint --endpoint-name signalhr-xgb-mvp

# Verify Bedrock is accessible
aws bedrock list-models

# Verify Amplify app is deployed
# (manually: open browser to https://signalhr-dev.amplifyapp.com and verify login page loads)
```

**STOP CONDITION:** If ANY validation fails, HALT and file a CR. Do not proceed.

---

## Phase 0.5: Local Code Validation (NEW - Slice 0 Code Testing)

**Objective:** Validate that the locally-created code files (generator, handler, tests) work correctly without AWS deployment.

**Duration:** ~5 minutes
**Note:** This phase MUST pass before deploying any AWS resources.

### 0.5.1: Test Synthetic Generator (ING-04)

**Command:**
```bash
cd /Users/abdallahmakboua/Desktop/Hackathon/SignalHR
python3 tools/synthetic_generator.py --profile all --dry-run 2>&1 | head -20
```

**Expected Output:**
- No errors
- Sample JSON event from alice, ben, carol (one per profile)
- Events contain: ingestionId (UUID), schemaVersion=1, userId (UUID), timestamp (ISO 8601), signals (numeric counts)

**PASS CONDITION:** All 3 profiles produce valid JSON events with numeric signals only.

### 0.5.2: Test Normalization Handler (PROC-01)

**Commands:**
```bash
# Install pytest if needed
pip3 install pytest -q

# Run unit test
python3 -m pytest tests/test_normalize.py -v
```

**Expected Output:**
```
tests/test_normalize.py::test_normalize_basic PASSED
```

**PASS CONDITION:** Test passes (signal coercion works, text fields dropped).

### 0.5.3: Verify Generator + Handler End-to-End (Local)

**Command:**
```bash
python3 tools/synthetic_generator.py --profile alice --rate 1000 --duration 0.001 --dry-run | \
  python3 -c "import sys, json; from lambdas.normalize_handler import normalize_event; \
  [print(json.dumps(normalize_event(json.loads(line)))) for line in sys.stdin if line.strip()]" | \
  head -3
```

**Expected Output:**
- 1–3 normalized events printed as JSON
- Each contains: ingestionId, schemaVersion=1, timestamp, profile, signals (numeric only)

**PASS CONDITION:** Normalized output contains numeric signals only; no errors.

---

## Phase 0.6: ING-01 Deployment (HTTP API + EventBridge) (NEW)

**Objective:** Deploy API Gateway HTTP API and integrate with EventBridge PutEvents using AWS CLI only.

**Prerequisite:** Set AWS_REGION=us-east-2 and AWS_PROFILE, and ensure EventBridge bus exists (created by script if missing).

### 0.6.1 Deploy Ingestion API (CLI Script)

**Command:**
```bash
cd /Users/abdallahmakboua/Desktop/Hackathon/SignalHR
bash scripts/deploy_ingestion.sh
```

**Expected Output:**
- EventBridge bus ARN printed
- API ID printed
- API Endpoint URL printed
- IAM role ARN printed

**PASS CONDITION:** API endpoint is printed and reachable (see test below).

### 0.6.1a Exact AWS CLI Commands (ING-01)

```bash
export AWS_REGION=us-east-2
export BUS_NAME=signalhr-bus-dev
export ROLE_NAME=signalhr-apigw-putevents-role-dev
export API_NAME=signalhr-ingest-http-api-dev
export STAGE_NAME=dev

# Create EventBridge bus (if missing)
aws events describe-event-bus --name ${BUS_NAME} --region ${AWS_REGION} \
  || aws events create-event-bus --name ${BUS_NAME} --region ${AWS_REGION}

BUS_ARN=$(aws events describe-event-bus --name ${BUS_NAME} --region ${AWS_REGION} --query 'Arn' --output text)

# Create IAM role for API Gateway
cat > /tmp/apigw_trust.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "apigateway.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

ROLE_ARN=$(aws iam create-role \
  --role-name ${ROLE_NAME} \
  --assume-role-policy-document file:///tmp/apigw_trust.json \
  --query 'Role.Arn' --output text)

cat > /tmp/apigw_putevents_policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "events:PutEvents",
      "Resource": "${BUS_ARN}"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name ${ROLE_NAME} \
  --policy-name signalhr-apigw-putevents-policy \
  --policy-document file:///tmp/apigw_putevents_policy.json

# Create HTTP API
API_ID=$(aws apigatewayv2 create-api --name ${API_NAME} --protocol-type HTTP --region ${AWS_REGION} --query 'ApiId' --output text)

# Create integration
INTEGRATION_ID=$(aws apigatewayv2 create-integration \
  --api-id ${API_ID} \
  --integration-type AWS_PROXY \
  --integration-subtype EventBridge-PutEvents \
  --credentials-arn ${ROLE_ARN} \
  --request-parameters "EventBusName=${BUS_NAME},Source=$request.body.source,DetailType=$request.body.eventType,Detail=$request.body" \
  --region ${AWS_REGION} \
  --query 'IntegrationId' --output text)

# Create route
aws apigatewayv2 create-route --api-id ${API_ID} --route-key "POST /events" --target "integrations/${INTEGRATION_ID}" --region ${AWS_REGION}

# Create stage
aws apigatewayv2 create-stage --api-id ${API_ID} --stage-name ${STAGE_NAME} --auto-deploy --region ${AWS_REGION}

echo "API Endpoint: https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com/${STAGE_NAME}"
```

### 0.6.2 Test Ingestion API (CLI Script)

**Command:**
```bash
export API_ID=<api-id-from-deploy>
bash scripts/test_ingestion.sh
```

**Expected Output:**
- HTTP status 200 or 202
- Response body from API

**PASS CONDITION:** HTTP status is 200/202 and EventBridge PutEvents metric increments.

### 0.6.3 Minimal Required Fields (Enforced by EventBridge)

**Required:** `source`, `eventType`, and non-empty request body.

**Expected Behavior:** If `source` or `eventType` is missing, EventBridge PutEvents fails and API returns non-2xx.

**PASS CONDITION:** Invalid payloads are rejected.

---

## If CreateEventBus is denied (Permission Blocker Recovery)

If you see: `AccessDenied: User is not authorized to perform: events:CreateEventBus`

**This is expected** if your AWS role doesn't have EventBridge bus creation permission.

### Step 1: List available buses

```bash
aws events list-event-buses --region us-east-2
```

### Step 2: Choose an existing bus or request creation

**Option A: Use an existing bus**
```bash
BUS_NAME=my-existing-bus bash scripts/deploy_ingestion.sh
```

**Option B: Request mentor to create or grant permission**

See `docs/MENTOR_MESSAGE.md` for ready-to-send Discord message. Share this with mentor:
- Your role ARN: `arn:aws:sts::528613214077:assumed-role/WSParticipantRole/Participant`
- Region: `us-east-2`
- Bus name: `signalhr-bus-dev`

Mentor will either:
1. Create the bus using AWS Console or CLI
2. Grant `events:CreateEventBus` permission to your role

After mentor action, re-run deploy script:
```bash
bash scripts/deploy_ingestion.sh
```

---

## Local Demo Output Artifacts (Phase 0.1 — Outputs Reference)

When you run `bash scripts/demo.sh`, the following artifacts are generated in `artifacts/local_demo_<timestamp>/`:

| Artifact | Format | Purpose | What It Proves |
|----------|--------|---------|---|
| `01_bus_metrics.json` | JSON | EventBridge bus event dump | ING-02 works: Events accepted by bus (shows event count, sample events, detects filtering) |
| `02_queue_metrics.json` | JSON | SQS queue depth snapshot | ING-03 works: Queue receives routed events (shows main queue + DLQ depth) |
| `03_aggregates.json` | JSON | DynamoDB-style aggregate store | PROC-01 + PROC-03 work: Normalization + aggregation complete (shows per-user/week features: meetings, messages, PRs, context_switch_rate, collaboration_index, growth_index) |
| `04_alerts.json` | JSON | AI-generated alerts | INT-01 works: Rules engine scored aggregates (shows burnout, HiPo, drift scores with explainable reasons) |
| `05_ai_explanations.json` | JSON | Natural language explanations | INT-03 works: Explainability layer produced human-readable summaries (shows summaries, why_flagged, next_best_actions per alert) |
| `DEMO_SUMMARY.md` | Markdown | Human-readable demo report | Full pipeline visible: event counts → alert summary → explanation examples |
| `aggregates.db` | SQLite | Persistent aggregate store | PROC-03 works: SQLite database persisted aggregates (can query with `sqlite3 aggregates.db "SELECT * FROM aggregates"`) |
| `post_events.log` | Text | HTTP POST event logs | ING-04 works: Synthetic generator posted 90 events (shows HTTP 202 status for each POST) |
| `server.log` | Text | FastAPI server logs | ING-01 works: API server running and processing requests (shows POST requests, validation) |

---

## Troubleshooting — Common Issues & Recovery

### Issue: `ModuleNotFoundError: No module named 'core'`

**Cause:** Python cannot find repo modules. PYTHONPATH not set.

**Solution:** Already fixed. Both `scripts/run_local.sh` and `scripts/demo.sh` set PYTHONPATH automatically.

**Verify:**
```bash
export PYTHONPATH="/Users/abdallahmakboua/Desktop/Hackathon/SignalHR:${PYTHONPATH:-}"
python3 << 'EOF'
from core.bus import EventBus
from api.app import EventPayload
from store.aggregates_store import AggregatesStore
print("✓ All imports successful")
EOF
```

### Issue: `HTTP 422 Validation Error` on POST /events

**Cause:** API validation failed. Event payload missing required fields or has wrong field names.

**Solution:** Check that payload has:
- `signalCounts` (dict of numeric counts, not `signals`)
- `eventType` (optional, defaults to "signal.ingestion.v1")
- `userId` (required, UUID string)
- `timestamp` (ISO 8601)

**Verify:**
```bash
cat > /tmp/test_event.json << 'EOF'
{
  "userId": "test-user",
  "timestamp": "2026-02-07T10:00:00Z",
  "signalCounts": {"meetings": 3, "messages": 20},
  "ingestionId": "test-id",
  "source": "synthetic",
  "schemaVersion": 1
}
EOF

curl -X POST http://127.0.0.1:8000/events \
  -H "Content-Type: application/json" \
  -d @/tmp/test_event.json
```

**Expected:** HTTP 202 response

### Issue: `HTTP 400 - Event filtered by Pipes`

**Cause:** EventBridge Pipes schema validation rejected the event (field filtering).

**Solution:** Verify event only contains whitelisted fields:
- `signalCounts` (numeric), `signals` (numeric), `userId`, `timestamp`, `eventType`, `ingestionId`, `source`, `profile`, `schemaVersion`
- No text fields like `message`, `content`, `description`

**Check:** View `artifacts/local_demo_*/validation_errors.log` if it exists

### Issue: `API error: bind: address already in use` (Port 8000 in use)

**Cause:** Stray FastAPI process still running on port 8000.

**Solution:** Kill process and restart
```bash
lsof -ti tcp:8000 | xargs kill -9
bash scripts/run_local.sh
```

### Issue: Demo produces 0 alerts

**Cause:** Aggregates weren't processed by rules engine (previous failure in demo.sh).

**Solution:** Check that `03_aggregates.json` was created (step [4/5] of demo.sh completed successfully)

**Verify:**
```bash
ls -la artifacts/local_demo_*/03_aggregates.json
cat artifacts/local_demo_*/03_aggregates.json | jq length
# Should be > 0
```

---

## Run Phases (Phase 1–5)

Demo execution is split into 5 sequential phases. Each phase has allowed commands, expected outputs, verification steps, and STOP conditions. **NO ad-hoc commands outside this runbook are allowed during demo.**

---

## Phase 1: Ingestion Run (Task ING-04)

**Objective:** Emit 3 synthetic user profiles (Alice, Ben, Carol) as events to API Gateway. Events flow: Generator → API Gateway → EventBridge → Pipes → SQS.

**Duration:** ~2 minutes
**Determinism:** Fixed user IDs and signal counts per profile. Week = DEMO_WEEK (2026-W06). Timestamps = current day.

### Allowed Commands

**1a. Start synthetic generator (read-only, pre-computed profiles)**

```bash
# Profile: alice (high overload)
python tools/synthetic_generator.py \
  --profile alice \
  --week ${DEMO_WEEK} \
  --rate 5 \
  --duration 1 \
  --api-endpoint ${API_ENDPOINT}
```

Expected output in stdout:
```
Generator started: profile=alice, week=2026-W06, rate=5/min
Event 1: ingestionId=<uuid>, eventType=slack_interaction, userId=alice-uuid
Event 2: ingestionId=<uuid>, eventType=calendar_change, userId=alice-uuid
... (5 events total)
Total events sent: 5
HTTP responses: 5x 202 Accepted
Generator completed: duration=1min
```

**1b. Start synthetic generator (profile: ben, high growth)**

```bash
python tools/synthetic_generator.py \
  --profile ben \
  --week ${DEMO_WEEK} \
  --rate 5 \
  --duration 1 \
  --api-endpoint ${API_ENDPOINT}
```

Expected output: 5 events, HTTP 202 responses, messages logged.

**1c. Start synthetic generator (profile: carol, baseline)**

```bash
python tools/synthetic_generator.py \
  --profile carol \
  --week ${DEMO_WEEK} \
  --rate 5 \
  --duration 1 \
  --api-endpoint ${API_ENDPOINT}
```

Expected output: 5 events, HTTP 202 responses, messages logged.

### Expected Outputs (Phase 1)

| Service | Artifact | Location |
|---------|----------|----------|
| Synthetic Generator | Execution logs (stdout) | Terminal, screenshot to `${S3_REPORTS}/01_generator_logs.txt` |
| API Gateway | HTTP 202 responses | CloudWatch logs: `/aws/apigateway/signalhr-dev` |
| EventBridge | PutEvents metrics | CloudWatch metrics: EventBridge invocation count should be 15 (5 per profile × 3) |
| SQS | Queue messages | `signalhr-ingest-queue-dev` should have ~15 messages (visible in console) |

### Verification Steps

```bash
# Step 1.1: Verify EventBridge received events
aws cloudwatch get-metric-statistics \
  --namespace AWS/Events \
  --metric-name Invocations \
  --start-time $(date -u -d '5 min ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Sum

# Expected: Sum >= 15 (one invocation per event)

# Step 1.2: Verify SQS queue has messages
aws sqs get-queue-attributes \
  --queue-url $(aws sqs get-queue-url --queue-name signalhr-ingest-queue-dev --query 'QueueUrl' --output text) \
  --attribute-names ApproximateNumberOfMessages

# Expected: ApproximateNumberOfMessages >= 15

# Step 1.3: Check for errors in DLQ (should be empty)
aws sqs get-queue-attributes \
  --queue-url $(aws sqs get-queue-url --queue-name signalhr-ingest-dlq-dev --query 'QueueUrl' --output text) \
  --attribute-names ApproximateNumberOfMessages

# Expected: ApproximateNumberOfMessages = 0
```

### STOP Conditions

- If generator errors or HTTP responses are not 202, **HALT and debug** (see Failure Handling Playbook).
- If SQS queue depth does not increase after generator runs, **HALT** (EventBridge Pipes or SQS issue).
- If DLQ has messages, **HALT and inspect** (validation failed at Pipes layer).

**Traceability:** Task ING-04 (synthetic generator) and ING-01 (API endpoint).

---

## Phase 2: Processing & Rollups (Tasks PROC-01, PROC-02)

**Objective:** Consume SQS messages, normalize, write to S3 and DynamoDB, execute rollup job to compute aggregates.

**Duration:** ~3 minutes
**Determinism:** Fixed week and user IDs ensure idempotent aggregation.

### Allowed Commands

**2a. Monitor Lambda normalization**

```bash
# Tail Lambda logs (last 5 min)
aws logs tail /aws/lambda/signalhr-normalize-dev --follow --since 5m

# Expected: Lines like:
# {"ingestionId":"<uuid>","schemaVersion":1,"success":true,"eventType":"slack_interaction"}
# (no raw payloads, only metadata)
```

**2b. Verify S3 raw events written**

```bash
# List raw events for DEMO_WEEK
aws s3 ls s3://signalhr-raw-events-dev/year=2026/week=W06/

# Expected: At least one .jsonl file with size > 0
# Example: year=2026/month=02/day=07/source=synth/events-20260207T120000Z.jsonl

# Get sample of raw file content
SAMPLE_FILE=$(aws s3 ls s3://signalhr-raw-events-dev/year=2026/week=W06/ | head -1 | awk '{print $NF}')
aws s3 cp s3://signalhr-raw-events-dev/year=2026/week=W06/${SAMPLE_FILE} - | head -1 | jq .

# Expected: JSON with userId (opaque UUID), eventType, schemaVersion=1, signalCounts (no text fields)
```

**2c. Execute StepFunctions rollup (manual invoke)**

```bash
# Start rollup execution
ROLLUP_ARN=$(aws stepfunctions list-state-machines \
  --query "stateMachines[?name=='signalhr-rollup-dev'].stateMachineArn" \
  --output text)

EXECUTION_ARN=$(aws stepfunctions start-execution \
  --state-machine-arn ${ROLLUP_ARN} \
  --name demo-rollup-${DEMO_TIMESTAMP} \
  --input "{\"week\":\"${DEMO_WEEK}\"}" \
  --query 'executionArn' \
  --output text)

echo "Rollup execution: ${EXECUTION_ARN}"

# Wait for completion (up to 5 min)
aws stepfunctions wait execution-succeeded --execution-arn ${EXECUTION_ARN} --max-attempts 60 --delay 5

# Expected: Execution status = SUCCEEDED
```

**2d. Verify DynamoDB aggregates written**

```bash
# Query aggregates for Alice (demo determinism: alice-uuid = fixed UUID)
aws dynamodb get-item \
  --table-name AggregatesTable-dev \
  --key "{\"PK\":{\"S\":\"USER#alice-uuid\"},\"SK\":{\"S\":\"WEEK#${DEMO_WEEK}\"}}" \
  --output json > /tmp/alice_agg.json

cat /tmp/alice_agg.json | jq .Item

# Expected: Item with PK, SK, aggregates (meetings, PRs, etc.), cohort_baseline (mu, sigma), z_scores map
```

### Expected Outputs (Phase 2)

| Service | Artifact | Location |
|---------|----------|----------|
| Lambda | Normalization logs | CloudWatch: `/aws/lambda/signalhr-normalize-dev` |
| S3 | Raw events JSONL | `s3://signalhr-raw-events-dev/year=2026/month=02/day=*/source=synth/*.jsonl` |
| StepFunctions | Rollup execution history | Execution ARN in stdout; CloudWatch logs |
| DynamoDB | Aggregate items | `AggregatesTable-dev` with PK=USER#*, SK=WEEK#2026-W06 |

### Verification Steps

```bash
# Step 2.1: Count normalization successes
aws logs filter-log-events \
  --log-group-name /aws/lambda/signalhr-normalize-dev \
  --filter-pattern "\"success\":true" \
  --start-time $(date -d '5 min ago' +%s)000 \
  --query 'events | length(@)'

# Expected: >= 15

# Step 2.2: Verify StepFunction execution succeeded
aws stepfunctions describe-execution --execution-arn ${EXECUTION_ARN} --query 'status'

# Expected: SUCCEEDED

# Step 2.3: Count DynamoDB aggregates for DEMO_WEEK
aws dynamodb query \
  --table-name AggregatesTable-dev \
  --key-condition-expression "SK = :week" \
  --expression-attribute-values "{\":week\":{\"S\":\"WEEK#${DEMO_WEEK}\"}}" \
  --query 'Count'

# Expected: >= 3 (Alice, Ben, Carol)

# Step 2.4: Verify no raw text in aggregates
aws dynamodb get-item \
  --table-name AggregatesTable-dev \
  --key "{\"PK\":{\"S\":\"USER#alice-uuid\"},\"SK\":{\"S\":\"WEEK#${DEMO_WEEK}\"}}" \
  | jq '.Item.aggregates'

# Expected: Object with numeric fields only (meetings: N, prs: N, etc.), no text
```

### STOP Conditions

- If Lambda logs show errors (ingestionId + reason), **HALT and inspect DLQ** (Failure Handling Playbook).
- If S3 raw events not written, **HALT** (Lambda write permission or input issue).
- If StepFunctions execution fails, **HALT** (check execution history for error).
- If DynamoDB aggregates not created, **HALT** (StepFunctions job issue).

**Traceability:** Task PROC-01 (Lambda), PROC-02 (StepFunctions), PROC-03 (DynamoDB).

---

## Phase 3: Scoring & Explainability (Tasks FEAT-01, FEAT-02, INT-01, INT-02, INT-03, INT-04)

**Objective:** Compute features, apply rules engine, invoke ML scoring, generate explanations via Vertex AI Gemini (with fallback to rule-based).

**Duration:** ~4 minutes
**Determinism:** Features computed from fixed aggregates; rules applied consistently; Gemini deterministic (temperature=0.0); fallback is 100% deterministic rule-based.

### Allowed Commands

**3a. Trigger feature job (Glue or Lambda)**

```bash
# Invoke feature extraction Lambda
aws lambda invoke \
  --function-name signalhr-feature-job-dev \
  --payload "{\"week\":\"${DEMO_WEEK}\"}" \
  --log-type Tail \
  response.json

# Expected: FunctionResponse status 200, output contains feature_manifest with row count
cat response.json | jq .
```

**3b. Run rules engine (Lambda)**

```bash
# Invoke rules engine Lambda
aws lambda invoke \
  --function-name signalhr-rules-engine-dev \
  --payload "{\"week\":\"${DEMO_WEEK}\"}" \
  --log-type Tail \
  response.json

# Expected: Alerts created for Alice (overload) and Ben (hippo), not Carol (baseline)
cat response.json | jq .
```

**3c. Run SageMaker scoring (invoke endpoint)**

```bash
# Query DynamoDB for feature record (Alice)
ALICE_FEATURES=$(aws dynamodb get-item \
  --table-name Features-dev \
  --key "{\"PK\":{\"S\":\"USER#alice-uuid\"},\"SK\":{\"S\":\"WEEK#${DEMO_WEEK}\"}}" \
  --output json | jq '.Item')

# Invoke SageMaker endpoint with feature vector
aws sagemaker-runtime invoke-endpoint \
  --endpoint-name signalhr-xgb-mvp \
  --body "${ALICE_FEATURES}" \
  --content-type application/json \
  response.json

# Expected: Probability and feature importances for Alice (high probability of burnout)
cat response.json | jq .
```

**3d. Trigger Vertex AI Gemini explanation (primary) or rule-based fallback**

```bash
# Set up Google Cloud credentials (if using Gemini)
export GOOGLE_APPLICATION_CREDENTIALS=~/signalhr-gemini-key.json
export GOOGLE_CLOUD_PROJECT=<your-gcp-project>

# Invoke explanation via Python (automatically tries Gemini, falls back to rules)
python3 << 'EOF'
from ai.gemini_explainer import explain_alerts, ExplanationConfig
from store.aggregates_store import AggregatesStore
from intelligence.rules_engine import get_alerts

# Load aggregates and alerts
store = AggregatesStore()
aggregates = store.get_all()
alerts = get_alerts(aggregates)

# Generate explanations (tries Gemini first, falls back to rules if unavailable)
config = ExplanationConfig(use_gemini=True)
explanations = explain_alerts(alerts, aggregates, config)

# Save to JSON
import json
with open("05_ai_explanations.json", "w") as f:
    json.dump(explanations, f, indent=2)

print(f"✓ Generated {len(explanations)} explanations")
print(f"✓ Saved to 05_ai_explanations.json")
EOF

# Expected: explanations.json with "summary", "why_flagged", "next_best_actions", "ai_source" per alert
cat 05_ai_explanations.json | jq '.[] | {userId, alertType, ai_source}'
```

**3d-alt. Lambda-based explanation (AWS only, when permissions available):**

```bash
# If using Lambda instead of local Python
aws lambda invoke \
  --function-name signalhr-gemini-explainer-dev \
  --payload "{\"alertId\":\"ALERT#alice-alert-1\",\"week\":\"${DEMO_WEEK}\"}" \
  --log-type Tail \
  response.json

# Expected: Explanation JSON with "summary", "why_flagged", "next_best_actions"
cat response.json | jq .
```

### Expected Outputs (Phase 3)

| Service | Artifact | Location |
|---------|----------|----------|
| Feature Job | Feature parquet | `s3://signalhr-aggregates-dev/features/year=2026/week=W06/feature-*.parquet` |
| Rules Engine | Alerts | `AlertsTable-dev` with entries for Alice and Ben |
| SageMaker | Scoring output | stdout, JSON with probability and feature importances |
| Vertex AI Gemini / Rule-based | Explanation JSON | `05_ai_explanations.json` (local) or `s3://signalhr-explanations-dev/<explanationId>.json` (AWS) |

### Verification Steps

```bash
# Step 3.1: Verify features created
aws s3 ls s3://signalhr-aggregates-dev/features/year=2026/week=W06/ | wc -l

# Expected: >= 1 parquet file

# Step 3.2: Query alerts from AlertsTable
aws dynamodb scan \
  --table-name AlertsTable-dev \
  --filter-expression "begins_with(SK, :prefix)" \
  --expression-attribute-values "{\":prefix\":{\"S\":\"USER#alice\"}}" \
  --query 'Items'

# Expected: At least 1 alert for Alice with ruleTriggered and topFeatures

# Step 3.3: Verify explanation exists and is readable
# For local: cat 05_ai_explanations.json | jq .
# For AWS S3: aws s3 cp s3://signalhr-explanations-dev/<file>.json - | jq .
cat 05_ai_explanations.json | jq '.[] | {summary, why_flagged, next_best_actions}'

# Expected: JSON object with "summary", "why_flagged", "next_best_actions" per alert

# Step 3.4: Verify no PII in explanation
cat 05_ai_explanations.json | grep -i "password\|ssn\|email\|phone" || echo "✓ No PII detected"

# Expected: No matches or ✓ message

# Step 3.5: Verify AI source (Gemini vs rule-based)
cat 05_ai_explanations.json | jq '.[] | {userId, ai_source}'

# Expected: "ai_source": "gemini" (if GCP credentials available) or "rule-based" (if not)
```

### STOP Conditions

- If feature job fails, **HALT** (check Lambda logs and DynamoDB/S3 permissions).
- If rules engine returns 0 alerts, **HALT** (thresholds too high or features not computed).
- If SageMaker endpoint times out, **HALT and open CR for Vertex AI fallback**.
- If Gemini returns unsafe output (detected by post-response scanner), **HALT and log incident** (or fallback to rule-based).
- If explanation contains PII, **HALT and escalate to security** (privacy breach).

**Traceability:** Task FEAT-01, FEAT-02, INT-01, INT-02, INT-03, INT-04.

---

## Phase 4: UI & Demo (Task UI-02)

**Objective:** Open Amplify UI, authenticate as Manager, view dashboard, navigate to alert, view explanation.

**Duration:** ~3 minutes
**Determinism:** Fixed demo users in Cognito; alerts pre-populated in AlertsTable.

### Allowed Commands

**4a. Open Amplify dashboard (manager login)**

```bash
# Open browser to Amplify app
open https://signalhr-dev.amplifyapp.com

# Or use curl to verify endpoint is up
curl -s -o /dev/null -w "%{http_code}" https://signalhr-dev.amplifyapp.com

# Expected: HTTP 200 (app loaded)
```

**4b. Authenticate as Manager**

- Click "Login"
- Username: manager-demo (from Cognito test users)
- Password: (use temporary password or MFA as configured)
- Expected: Dashboard loads showing team heatmap with 3 users (Alice, Ben, Carol)

**4c. Navigate to Alice alert**

- On Manager Dashboard, locate Alice in the heatmap
- Click on Alice row/card
- Expected: Alert detail modal opens showing:
  - Alert ID
  - Burnout flag (red indicator)
  - "Why flagged" summary from Bedrock explanation
  - "Next best action" suggestions

**4d. View explanation details**

- Click "Show Full Explanation" in modal
- Expected: Explanation text loaded from S3 and displayed, including:
  - Signal contributors (e.g., "High meetings (z=2.3), High messages (z=1.9)")
  - Cohort comparison ("Top 10% overload in role=engineer cohort")
  - Suggested actions ("Schedule 1:1 to discuss workload", "Encourage wellness resources")

### Expected Outputs (Phase 4)

| Service | Artifact | Location |
|---------|----------|----------|
| Amplify | Dashboard page HTML | Browser; screenshot to `${S3_REPORTS}/04_manager_dashboard.png` |
| Cognito | Auth token | Browser DevTools; verify `cognito:groups` claim = [Manager] |
| UI Fetch | Alert details JSON | Browser Network tab; screenshot to `${S3_REPORTS}/04_alert_response.json` |
| S3 Explanation | Explanation text | Browser render; screenshot to `${S3_REPORTS}/04_explanation_modal.png` |

### Verification Steps

**Manual (visual inspection in browser):**
1. Dashboard loaded and 3 users visible
2. Manager group claim present in JWT (DevTools → Application → Cookies → check token)
3. Alert for Alice flagged as "Burnout"
4. Explanation modal contains "Why flagged" and "Next best action"
5. No raw event text visible (only aggregates and z-scores)

### STOP Conditions

- If login fails, **HALT** (Cognito auth issue; check user pool and test user setup).
- If dashboard does not load, **HALT** (Amplify deployment issue or API Gateway integration broken).
- If alert details are blank, **HALT** (AlertsTable or explanation S3 not accessible from UI).
- If explanation contains raw PII, **HALT and escalate** (privacy breach).

**Traceability:** Task UI-01 (Cognito), UI-02 (Amplify/Next.js).

---

## Phase 5: Evidence Capture (Task DEMO-01)

**Objective:** Save all artifacts for demo validation and archive.

**Duration:** ~5 minutes

### Allowed Commands

**5a. Create evidence directory in S3**

```bash
# Create timestamped evidence directory (should exist from env setup)
# Verify it's empty and ready
aws s3 ls ${S3_REPORTS}/ | wc -l

# Expected: 0 (empty or new directory)
```

**5b. Save generator logs**

```bash
# From Phase 1, save terminal output
cat << 'EOF' > /tmp/generator_logs.txt
[Paste stdout from Phase 1 generator runs here]
EOF

aws s3 cp /tmp/generator_logs.txt ${S3_REPORTS}/01_generator_logs.txt
```

**5c. Save EventBridge metrics**

```bash
# Export EventBridge invocation count
aws cloudwatch get-metric-statistics \
  --namespace AWS/Events \
  --metric-name Invocations \
  --dimensions Name=EventBusName,Value=signalhr-bus-dev \
  --start-time $(date -u -d '10 min ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Sum \
  > /tmp/eventbridge_metrics.json

aws s3 cp /tmp/eventbridge_metrics.json ${S3_REPORTS}/02_eventbridge_metrics.json
```

**5d. Save DynamoDB aggregates**

```bash
# Export Alice aggregate
aws dynamodb get-item \
  --table-name AggregatesTable-dev \
  --key "{\"PK\":{\"S\":\"USER#alice-uuid\"},\"SK\":{\"S\":\"WEEK#${DEMO_WEEK}\"}}" \
  > /tmp/alice_aggregate.json

aws s3 cp /tmp/alice_aggregate.json ${S3_REPORTS}/02_alice_aggregate.json

# Repeat for Ben and Carol
aws dynamodb get-item \
  --table-name AggregatesTable-dev \
  --key "{\"PK\":{\"S\":\"USER#ben-uuid\"},\"SK\":{\"S\":\"WEEK#${DEMO_WEEK}\"}}" \
  > /tmp/ben_aggregate.json

aws s3 cp /tmp/ben_aggregate.json ${S3_REPORTS}/02_ben_aggregate.json

aws dynamodb get-item \
  --table-name AggregatesTable-dev \
  --key "{\"PK\":{\"S\":\"USER#carol-uuid\"},\"SK\":{\"S\":\"WEEK#${DEMO_WEEK}\"}}" \
  > /tmp/carol_aggregate.json

aws s3 cp /tmp/carol_aggregate.json ${S3_REPORTS}/02_carol_aggregate.json
```

**5e. Save alerts**

```bash
# Query all alerts for demo week
aws dynamodb scan \
  --table-name AlertsTable-dev \
  --filter-expression "begins_with(SK, :prefix)" \
  --expression-attribute-values "{\":prefix\":{\"S\":\"USER#\"}}" \
  > /tmp/all_alerts.json

aws s3 cp /tmp/all_alerts.json ${S3_REPORTS}/03_all_alerts.json
```

**5f. Save explanations**

```bash
# List all explanation objects
aws s3 ls s3://signalhr-explanations-dev/ > /tmp/explanation_listing.txt

# Copy all explanations to evidence bucket
aws s3 sync s3://signalhr-explanations-dev/ ${S3_REPORTS}/03_explanations/ --exclude "*" --include "*.json"

# Also save raw event samples
aws s3 sync s3://signalhr-raw-events-dev/year=2026/week=W06/ ${S3_REPORTS}/02_raw_events/ --exclude "*" --include "*.jsonl"
```

**5g. Save UI screenshots (manual)**

```bash
# Use browser DevTools or screenshot tool:
# 1. Manager Dashboard (with 3 users visible): save to local file
#    → upload to: ${S3_REPORTS}/04_manager_dashboard.png

# 2. Alert detail modal (Alice): save to local file
#    → upload to: ${S3_REPORTS}/04_alice_alert_modal.png

# 3. Explanation view: save to local file
#    → upload to: ${S3_REPORTS}/04_explanation_detail.png

# 4. Employee Portal (as alice-demo user): save to local file
#    → upload to: ${S3_REPORTS}/04_employee_portal.png

# 5. Audit View (as HR user): save to local file
#    → upload to: ${S3_REPORTS}/04_audit_view.png

# Upload screenshots
aws s3 cp ~/Downloads/manager_dashboard.png ${S3_REPORTS}/04_manager_dashboard.png
aws s3 cp ~/Downloads/alice_alert_modal.png ${S3_REPORTS}/04_alice_alert_modal.png
aws s3 cp ~/Downloads/explanation_detail.png ${S3_REPORTS}/04_explanation_detail.png
aws s3 cp ~/Downloads/employee_portal.png ${S3_REPORTS}/04_employee_portal.png
aws s3 cp ~/Downloads/audit_view.png ${S3_REPORTS}/04_audit_view.png
```

**5h. Save logs**

```bash
# Export CloudWatch logs (last 15 min) for key services
for LOG_GROUP in /aws/lambda/signalhr-normalize-dev /aws/lambda/signalhr-rules-engine-dev /aws/lambda/signalhr-bedrock-explainer-dev; do
  aws logs get-log-events \
    --log-group-name ${LOG_GROUP} \
    --log-stream-name $(aws logs describe-log-streams --log-group-name ${LOG_GROUP} --order-by LastEventTime --descending --max-items 1 --query 'logStreams[0].logStreamName' --output text) \
    --start-time $(date -d '15 min ago' +%s)000 \
    > /tmp/$(basename ${LOG_GROUP}).json
  
  aws s3 cp /tmp/$(basename ${LOG_GROUP}).json ${S3_REPORTS}/logs/$(basename ${LOG_GROUP}).json
done
```

**5i. Create summary document**

```bash
cat << 'EOF' > /tmp/DEMO_SUMMARY.md
# SignalHR Demo Evidence Summary

**Date:** ${DEMO_TIMESTAMP}
**Week:** ${DEMO_WEEK}
**Region:** us-east-1

## Users
- Alice (UUID: alice-uuid): Flagged as Burnout (high overload)
- Ben (UUID: ben-uuid): Flagged as HiPo (high growth)
- Carol (UUID: carol-uuid): No flags (baseline)

## Artifacts
- Generator logs: 01_generator_logs.txt
- EventBridge metrics: 02_eventbridge_metrics.json
- Aggregates: 02_alice_aggregate.json, 02_ben_aggregate.json, 02_carol_aggregate.json
- Raw events: 02_raw_events/
- Alerts: 03_all_alerts.json
- Explanations: 03_explanations/
- UI screenshots: 04_*.png
- CloudWatch logs: logs/

## Verification Checklist
- [ ] 15 events ingested (5 per user)
- [ ] 3 aggregates created in DynamoDB
- [ ] 2 alerts created (Alice, Ben)
- [ ] 2 explanations generated
- [ ] Manager dashboard displayed all 3 users
- [ ] Alert click showed explanation
- [ ] Employee portal accessible
- [ ] Audit view shows explanation history
- [ ] No PII or raw text in any artifact

EOF

aws s3 cp /tmp/DEMO_SUMMARY.md ${S3_REPORTS}/DEMO_SUMMARY.md
```

### Expected Outputs (Phase 5)

All artifacts saved to `s3://signalhr-test-reports/demo/${DEMO_TIMESTAMP}/`:
- Generator logs, metrics, aggregates, alerts, explanations, raw events
- UI screenshots (5 views)
- CloudWatch logs (4 services)
- Summary document

### Verification Steps

```bash
# Verify all files uploaded
aws s3 ls ${S3_REPORTS}/ --recursive | wc -l

# Expected: >= 20 objects

# Verify checksums (data integrity)
aws s3 cp ${S3_REPORTS}/DEMO_SUMMARY.md - | head -5
```

---

## Command Authority (NEW)

**CRITICAL:** Only commands explicitly listed in this runbook are authorized during demo. Any missing command or ad-hoc CLI usage **MUST** trigger a documentation update via CR, not improvisation.

### Authorized Commands by Category

**AWS CLI (Service API calls):**
- `aws sts get-caller-identity`
- `aws events describe-event-bus`
- `aws sqs get-queue-url`, `get-queue-attributes`, `receive-message`
- `aws dynamodb describe-table`, `get-item`, `query`, `scan`
- `aws s3 ls`, `s3 cp`, `s3 sync`
- `aws logs tail`, `filter-log-events`, `get-log-events`
- `aws cloudwatch get-metric-statistics`
- `aws stepfunctions describe-execution`, `start-execution`, `wait`
- `aws lambda invoke`
- `aws sagemaker describe-endpoint`, `sagemaker-runtime invoke-endpoint`
- `aws bedrock list-models` (read-only)
- `aws cognito-idp describe-user-pool`

**Python/Shell Tools:**
- `python tools/synthetic_generator.py` (with args from Phase 1)
- `curl` (to verify HTTP endpoints, 202 responses only)
- `jq` (JSON parsing, output display)
- `date`, `grep`, `wc` (standard Unix tools for verification)

**Browser (UI-specific):**
- Open `https://signalhr-dev.amplifyapp.com`
- Login as test users (manager-demo, employee-demo, hr-demo)
- Navigate views: Manager Dashboard, Employee Portal, Audit View
- Click alerts to view explanations
- Take screenshots

**NOT Authorized:**
- `aws dynamodb delete-item`, `delete-table`, `put-item` (data mutation outside planned phases)
- `aws s3 rm` (deletion of evidence)
- `aws stepfunctions stop-execution` (interruption of pipeline)
- `python tools/synthetic_generator.py --regenerate` (new data during demo)
- Custom Lambda functions or ad-hoc deployments
- Schema or configuration changes
- Database rollbacks or purges

---

## Failure Handling Playbook (NEW)

If demo encounters errors, follow this decision tree. **Do NOT skip steps or guess.**

### Scenario A: DLQ has messages

**Symptom:** Phase 1 verification Step 1.3 shows `ApproximateNumberOfMessages > 0`

**Root cause:** EventBridge Pipes rejected events (validation or transformation failure)

**Action:**
1. Inspect DLQ message metadata (do NOT read raw payload):
   ```bash
   aws sqs receive-message --queue-url <dlq-url> --max-number-of-messages 1 --attribute-names All
   ```
2. Extract failure reason from message attributes or body (metadata only).
3. Cross-check against docs/02_data_contracts.md: is a required field missing? Invalid enum?
4. If generator bug, **file CR** and update docs/04_runbook.md (do not fix generator during demo).
5. If Pipes config issue, **HALT and escalate** (not recoverable without redeployment).

### Scenario B: Lambda errors in CloudWatch

**Symptom:** Phase 2 logs show Lambda failures or timeouts

**Root cause:** Normalization logic error, permission issue, or timeout

**Action:**
1. Read CloudWatch log for `ingestionId` and `failureCode`.
2. If timeout: Lambda memory/timeout too low → **file CR** for task PROC-01 (do not change Lambda during demo).
3. If permission error: S3 write or DynamoDB access denied → **HALT** (IAM misconfiguration, not recoverable).
4. If schema validation error: check incoming event format → **HALT** (generator produced invalid events; not recoverable).

### Scenario C: StepFunctions execution fails

**Symptom:** Phase 2 Step 2.2 shows StepFunction status `FAILED` or `TIMED_OUT`

**Root cause:** Aggregation logic error, DynamoDB throttle, or S3 access issue

**Action:**
1. Inspect execution history for failed step name.
2. If DynamoDB throttle (on-demand should not throttle): wait 5 min and retry execution.
3. If S3 read error: **HALT** (permissions or bucket issue).
4. If aggregation error: **HALT and file CR** (code bug not recoverable during demo).

### Scenario D: Missing DynamoDB aggregates

**Symptom:** Phase 2 Step 2.3 shows `Count = 0` or < 3

**Root cause:** StepFunction succeeded but wrote 0 items (data validation failure in rollup job)

**Action:**
1. Check StepFunction output for error manifests (written to S3).
2. Read manifest to identify which users failed aggregation.
3. **HALT and file CR** (data quality issue requires investigation).

### Scenario E: Feature job fails

**Symptom:** Phase 3 Step 3.1 shows no parquet files created

**Root cause:** Feature extraction logic error or DynamoDB read timeout

**Action:**
1. Check Lambda logs for feature job errors.
2. If timeout: wait 5 min and retry manually via Lambda invoke.
3. If data error: **HALT and file CR** (feature logic bug).

### Scenario F: Rules engine returns 0 alerts

**Symptom:** Phase 3 Step 3.2 shows 0 alerts for Alice or Ben

**Root cause:** Feature z-scores below threshold or features not computed

**Action:**
1. Manually query DynamoDB aggregates and verify z_scores present.
2. If z_scores missing: **go back to Phase 2** and check feature job (Scenario E).
3. If z_scores present but low: thresholds too high → **file CR** for task INT-01 (do not modify rules during demo).

### Scenario G: SageMaker endpoint times out

**Symptom:** Phase 3 Step 3c times out after 30 sec

**Root cause:** Endpoint in cold start or unavailable

**Action:**
1. Check SageMaker endpoint status:
   ```bash
   aws sagemaker describe-endpoint --endpoint-name signalhr-xgb-mvp
   ```
2. If status `InService`: retry after 1 min (cold start warming).
3. If status not `InService`: **file CR** and fallback to rules-only (disable ML for rest of demo).

### Scenario H: Bedrock unavailable or unsafe output

**Symptom:** Phase 3 Step 3d returns error or post-response scanner detects PII/unsafe advice

**Root cause:** Bedrock service unavailable OR prompt/guardrails misconfigured

**Action:**
1. If unavailable: **file CR** and fallback (use templated explanation without Bedrock).
2. If unsafe output detected: **HALT immediately** (security incident). Do NOT show output to users. Log incident and escalate to Project Owner.

### Scenario I: UI dashboard blank or slow

**Symptom:** Phase 4 Step 4c shows no users or takes >5 sec to load

**Root cause:** API Gateway timeout, DynamoDB query slow, or Cognito token invalid

**Action:**
1. Open DevTools Network tab, check API call response time.
2. If API returns 5xx: backend issue (Lambda or DynamoDB) → **HALT** and go to Scenario B or D.
3. If API times out: query too complex → **file CR** for task UI-02 (optimize query during post-MVP).
4. If Cognito auth fails: token invalid or expired → re-login as test user.

### Scenario J: Evidence capture fails (Phase 5)

**Symptom:** S3 upload commands fail with permission error

**Root cause:** S3 bucket permissions or KMS key access

**Action:**
1. Verify S3 bucket exists and is accessible:
   ```bash
   aws s3 ls ${S3_REPORTS}/
   ```
2. If bucket missing: **file CR** (not created during setup).
3. If permission denied: **file CR** (IAM role missing s3:PutObject).
4. Skip Phase 5 until fixed; evidence can be captured post-demo.

---

## Demo Lock Rules (NEW)

**These rules ensure determinism and prevent accidental data corruption during demo.**

1. **No data regeneration:** Synthetic generator must use fixed profiles (alice, ben, carol) with fixed signal counts. No `--random-seed` variation.
2. **Fixed time window:** All events timestamped to `DEMO_WEEK=2026-W06`. No live timestamps.
3. **Fixed user IDs:** alice-uuid, ben-uuid, carol-uuid are hardcoded in generator. No dynamic UUID generation.
4. **Read-only UI mode:** UI must not allow any data mutations (no opt-in toggles flipped, no manual alerts created).
5. **No redeployments:** All infrastructure must be pre-deployed before Phase 0. No Lambda code changes during demo.
6. **No schema changes:** No updates to DC-ING-V1 or other contracts during demo.
7. **No backfilling:** Do not run generator twice on same week/users (dedup logic will reject duplicates).
8. **Immutable explanations:** Once Bedrock explanation generated and saved, do not regenerate or edit.

**Violation consequence:** Demo becomes non-reproducible and evidence invalid. File CR immediately if any rule violated.

---

## Traceability (NEW)

Each phase maps to backlog tasks. Evidence collected in Phase 5 must be linked to task Evidence of Completion fields in docs/03_backlog.md:

| Phase | Task IDs | Evidence Artifacts |
|-------|----------|-------------------|
| Phase 1 | ING-04, ING-01 | `01_generator_logs.txt`, `02_eventbridge_metrics.json` |
| Phase 2 | PROC-01, PROC-02, PROC-03 | `02_alice_aggregate.json`, `02_eventbridge_metrics.json`, `logs/signalhr-normalize-dev.json` |
| Phase 3 | FEAT-01, FEAT-02, INT-01, INT-02, INT-03, BED-01 | `03_all_alerts.json`, `03_explanations/`, `response.json` (ML output) |
| Phase 4 | UI-01, UI-02 | `04_manager_dashboard.png`, `04_alice_alert_modal.png`, `04_explanation_detail.png`, `04_employee_portal.png`, `04_audit_view.png` |
| Phase 5 | DEMO-01 | `DEMO_SUMMARY.md`, all above + `02_raw_events/`, `logs/` directory |

After demo completes, update docs/03_backlog.md for each task:
- Set Status → Done
- Add Evidence of Completion link: `s3://signalhr-test-reports/demo/${DEMO_TIMESTAMP}/`
- Add timestamp of completion

---

## Determinism Guarantees (NEW)

**This demo is 100% reproducible if these guarantees are met:**

1. **Fixed synthetic data:** Generator profiles (Alice, Ben, Carol) have hardcoded signal counts per day. Running generator twice with same --profile and --week produces identical events (modulo timestamps, which are deterministic by --week).
2. **Fixed week:** `DEMO_WEEK=2026-W06` ensures all timestamps map to same week number. Rollup always processes the same data partition.
3. **Fixed user IDs:** User identifiers are hardcoded (alice-uuid, ben-uuid, carol-uuid). DynamoDB aggregates will have consistent PKs across runs.
4. **Idempotent aggregation:** Step Functions and feature jobs use `schemaVersion=1` and `ingestionId` dedup to handle re-runs without duplication. Running demo twice results in same aggregates.
5. **Fixed thresholds:** Rules engine thresholds (z-score > 2 for burnout, z-score > 1.5 for hippo) are hardcoded. Same features always produce same alerts.
6. **ML seed:** SageMaker model weights are frozen (no retraining during demo). Same feature inputs always produce same probability scores.

**Consequence:** Demo can be re-run multiple times with identical outputs (same aggregates, alerts, explanations) as long as demo.lock rules are followed.

---

## Summary

This runbook is the **executable specification** for running the SignalHR MVP demo. All commands, outputs, and steps are binding. Deviations require documented CRs. Evidence from Phase 5 becomes the proof of task completion for docs/03_backlog.md.
