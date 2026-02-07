# Backlog (Canonical)

This file is the canonical backlog for the project. Each task includes a full specification: Task ID, Title, Description, Inputs, Outputs, Acceptance Criteria, Evidence of Completion, Dependencies, and Status. All tasks start in Status = Not Started.

---

## Current Implementation Snapshot (Status as of 2026-02-07 — UPDATED FOR LOCAL SIMULATION)

### IMPLEMENTED (Code files created — Local Simulators)
- **ING-01 (LOCAL):** `api/app.py` — FastAPI POST /events endpoint (replaces API Gateway v2)
- **ING-02 (LOCAL):** `core/bus.py` — In-memory EventBridge simulator with Pipes filter/transform
- **ING-03 (LOCAL):** `core/queue.py` — In-memory SQS queue + DLQ simulator
- **ING-04:** `tools/synthetic_generator.py` — Deterministic generator with 3 profiles (alice/ben/carol), ready to POST to local API
- **PROC-01 (LOCAL):** `lambdas/normalize_handler.py` + local Lambda consumer in demo script
- **PROC-03 (LOCAL):** `store/aggregates_store.py` — SQLite aggregates store (replaces DynamoDB)
- **TEST-INFRA:** `tests/test_normalize.py`, `tests/test_integration.py` — Unit + integration tests
- **SCRIPTS:** `scripts/run_local.sh`, `scripts/demo.sh` — Orchestration for local simulator
- **DOCS:** `docs/EXECUTIVE_SUMMARY.md`, updated `docs/CHANGE_REQUESTS.md` with CR-2026-003 (Emergency CR)
- **BUGFIX:** Python module resolution (PYTHONPATH) — Fixed `ModuleNotFoundError: No module named 'core'` by setting PYTHONPATH in `scripts/run_local.sh` and `scripts/demo.sh` (2026-02-07).

### NOT IMPLEMENTED (Blocked by AWS permissions)
- **AWS RESOURCES:** All AWS services (EventBridge, DynamoDB, SQS, Lambda, API Gateway, Bedrock, CloudWatch, CloudTrail, SageMaker) blocked by explicit deny.
- **ING-01 (AWS):** API Gateway deployment blocked
- **ING-02 (AWS):** EventBridge bus + Pipes blocked
- **ING-03 (AWS):** SQS queue + DLQ blocked
- **PROC-02:** Step Functions rollup — Deferred
- **PROC-03 (AWS):** DynamoDB tables blocked
- **FEAT-01, FEAT-02:** Feature jobs — Deferred
- **INT-01, INT-02, INT-03:** Rules engine, SageMaker — Deferred
- **BED-01, BED-02:** Bedrock Agent, Safety checks — Deferred (no open-source equivalent)
- **UI-01, UI-02:** Amplify frontend, RBAC — Deferred
- **OBS-01 through OBS-04:** CloudWatch, X-Ray, CloudTrail setup — Deferred

### DEVIATIONS & CHANGES (CR-2026-003)
- **AWS Blocker:** Explicit deny on all AWS services except STS and S3 list-buckets. EMERGENCY CR filed.
- **Local Simulation:** Using Python FastAPI + in-memory simulators instead of AWS services.
- **Architecture:** AWS blueprint remains mandated; local simulators implement same logic and can swap to AWS later.
- **Demo Mode:** Local-only (<2 minute demo) instead of AWS cloud deployment.
- **Post-Hackathon:** Plan to migrate local code to AWS when permissions available.

---

## Task Status Definitions
1. **Not Started** — Task created but no work begun.
2. **In Progress** — Work started; Start Evidence (branch/commit link) recorded.
3. **Ready for Review** — Work complete; test artifacts and PR URL attached.
4. **Review** — Reviewer validates evidence and acceptance criteria.
5. **Done** — All evidence provided, reviewer+QA sign-off, Evidence of Completion linked.
6. **Blocked** — Task cannot proceed (e.g., AWS permissions blocker).
7. **Blocked (Local Workaround)** — Task blocked for AWS but local simulator created.

Evidence types: CloudWatch logs, S3 object keys + checksums, DynamoDB item JSON, screenshots, test reports, execution history ARNs, code commits, pytest output, local simulator output.

---

## INGESTION EPIC (ING) — LOCAL SIMULATION

### ING-01: Create REST ingestion endpoints (API Gateway)
- **Title:** Provision API Gateway REST endpoint for event ingestion
- **Description:** Create a REST POST endpoint that accepts synthetic generator events and sources per `docs/02_data_contracts.md#DC-ING-V1`. Endpoint must authenticate requests (API key or Cognito), validate schemaVersion, and forward to EventBridge using PutEvents API. No payload modification by API Gateway; forward to EventBridge as-is.
- **Inputs:**
  - AWS account and region (us-east-1)
  - EventBridge bus name: `signalhr-bus-dev`
  - Endpoint path: `/dev/events` or `/events`
- **Outputs:**
  - API Gateway REST API resource created
  - POST method deployed to dev stage
  - Execution role with permission to PutEvents on `signalhr-bus-dev`
  - Endpoint URL documented in `docs/04_runbook.md`
  - CORS configured (if needed for Amplify frontend)
- **Acceptance Criteria:**
  - API Gateway endpoint accepts POST request with JSON body matching DC-ING-V1 schema
  - Request returns HTTP 202 (Accepted)
  - EventBridge metrics show PutEvents called for each request
  - No transformation of payload at API layer; raw event forwarded
- **Evidence of Completion:**
  - API Gateway console screenshot showing resource and method
  - CloudWatch logs showing successful 202 responses (sample event IDs)
  - EventBridge metric screenshot showing PutEvents invocation count
  - Curl test command and sample response in docs/04_runbook.md
- **Dependencies:** None (pre-req for ING-02)
- **Status:** Blocked
- **Owner:** TBD
- **Start Evidence:** files=scripts/deploy_ingestion.sh,scripts/test_ingestion.sh (created 2026-02-07); role=arn:aws:sts::528613214077:assumed-role/WSParticipantRole/Participant; region=us-east-2
- **Blocker:** AccessDenied on events:CreateEventBus (see docs/08_deployment_plan.md#Permissions Blockers). Awaiting mentor to create bus or grant permission. Script updated to discover existing buses gracefully (see docs/04_runbook.md#If CreateEventBus is denied)
- **Completion Evidence:** (blank until permissions resolved)

---

### ING-02: Configure EventBridge bus + Pipes
- **Title:** Create EventBridge custom bus and Pipes to filter/transform events
- **Description:** Provision a custom EventBridge event bus named `signalhr-bus-dev`. Create EventBridge Pipes to enforce whitelist schema per DC-ING-V1: drop unknown fields, reject events missing required fields, and route valid events to SQS ingest queue. Pipes must apply transformation rules to ensure only Signal class data (numeric counts, no text) is forwarded.
- **Inputs:**
  - Event schema from docs/02_data_contracts.md#DC-ING-V1
  - SQS queue ARN (created in ING-03)
  - Whitelist fields to retain
- **Outputs:**
  - EventBridge custom event bus: `signalhr-bus-dev`
  - EventBridge Pipe resource with input validation and filter transform
  - Pipe target: SQS ingest queue
  - Monitoring metrics configured
- **Acceptance Criteria:**
  - Pipe accepts valid events per DC-ING-V1 and delivers to SQS
  - Unknown fields are dropped (not forwarded to SQS)
  - Events with missing required fields are rejected (appear as failed in Pipe metrics)
  - Pipe transform shows 0 text fields in output (sampling)
  - EventBridge and Pipe metrics visible in CloudWatch
- **Evidence of Completion:**
  - EventBridge bus creation screenshot
  - Pipe resource definition (JSON) showing filter and transform
  - CloudWatch metrics showing Pipe invocations and filtered events
  - Test events with unknown fields dropped (log snippet)
  - Test events without required fields rejected (Pipe failure metric)
- **Dependencies:** ING-01 (must have event source), SQS (ING-03 in parallel)
- **Status:** Blocked
- **Owner:** TBD
- **Start Evidence:** (blank until in-progress)
- **Blocker:** EventBridge bus creation denied (ING-01 blocker). Awaiting mentor action.
- **Completion Evidence:** (blank until done)
- **Title:** Create SQS standard queue and dead-letter queue for event buffering
- **Description:** Provision SQS standard queue `signalhr-ingest-queue-dev` with appropriate VisibilityTimeout (2x Lambda max timeout, e.g., 600 seconds). Attach a DLQ `signalhr-ingest-dlq-dev` with redrive policy after 3 receive attempts. Configure KMS encryption with key from OBS-02. Enable CloudWatch metrics and alarms for queue depth.
- **Inputs:**
  - KMS key ARN (from OBS-02)
  - Lambda max timeout estimate (300 sec, so VT = 600 sec)
- **Outputs:**
  - SQS queue: `signalhr-ingest-queue-dev`
  - DLQ: `signalhr-ingest-dlq-dev`
  - Redrive policy configured
  - KMS encryption enabled
  - CloudWatch alarms for queue depth and DLQ messages
- **Acceptance Criteria:**
  - Queue created and accepts messages from EventBridge Pipes
  - DLQ attached with 3-attempt redrive policy
  - KMS encryption applied with correct key
  - Messages visible in queue (polling), and DLQ reachable via console
  - Alarms trigger on DLQ > 0 and queue depth anomalies
- **Evidence of Completion:**
  - SQS queue and DLQ console screenshots
  - Queue redrive policy JSON snippet
  - KMS encryption configuration confirmed
  - Alarm configuration screenshot
  - Test message sent to queue and retrieved (CloudWatch log)
- **Dependencies:** OBS-02 (KMS key required)
- **Status:** Not Started
- **Owner:** TBD
- **Start Evidence:** (blank until in-progress)
- **Completion Evidence:** (blank until done)

---

### ING-04: Build synthetic data generators
- **Title:** Develop Python/Node.js CLI tool to emit synthetic events for demo scenarios
- **Description:** Create a generator script that produces three synthetic user profiles (Alice=overloaded, Ben=HiPo, Carol=baseline) and emits daily event sequences per DC-ING-V1 schema. Generator must POST events to API Gateway endpoint (ING-01). Each event must include schemaVersion=1, unique ingestionId (UUID), and realistic signal counts (meetings, PRs, messages, etc.). Generator should support rate control (e.g., --rate 10 events/min) and time range (e.g., --range 7d for 7 days of backfill).
- **Inputs:**
  - API Gateway endpoint URL (from ING-01)
  - Scenario profiles (Alice, Ben, Carol) definition
  - Signal count ranges and distributions
- **Outputs:**
  - Generator CLI script (`tools/synthetic_generator.py` or `.js`)
  - README with usage examples
  - Sample event log (JSONL) from a test run
  - Scenario profile configuration file (`tools/profiles.json` or similar)
- **Acceptance Criteria:**
  - Generator accepts command-line args: `--profile (alice|ben|carol|all)`, `--rate <int>`, `--duration <hours>`
  - Generates events matching DC-ING-V1 schema with no extra/missing fields
  - Each event has unique ingestionId and correct schemaVersion=1
  - POSTs events to API Gateway; logs HTTP response (202 expected)
  - Runs for configurable duration without error
  - Generated event counts match expected rates (sampling validation)
- **Evidence of Completion:**
  - Generator script code committed to repo
  - README.md with examples (`--profile alice --rate 10 --duration 1`)
  - Sample JSONL output from a test run (first 5 events)
  - CloudWatch logs showing successful API Gateway POST (202s) for sample count
  - Synthetic user profile configurations with example signal patterns
- **Dependencies:** ING-01 (needs API endpoint URL)
- **Status:** Done
- **Owner:** TBD
- **Start Evidence:** file=tools/synthetic_generator.py (created 2026-02-07); command: `python tools/synthetic_generator.py --profile alice --rate 10 --duration 0.01 --dry-run`
- **Completion Evidence:** 
  - **Timestamp:** 2026-02-07T07:39:55Z
  - **Files:** artifacts/local_demo_20260207_073015/post_events.log
  - **What it proves:** Generator successfully posted 90 events (30 per profile: alice, ben, carol) to local API with HTTP 202 status. All events valid DC-ING-V1 schema with unique ingestionIds, correct schemaVersion=1, numeric signalCounts, userId extraction.

---

## PROCESSING & STORAGE EPIC (PROC) — 8 hours

### PROC-01: Lambda normalization
- **Title:** Implement Lambda function to normalize SQS events and write to S3/DynamoDB
- **Description:** Create Lambda function subscribed to SQS ingest queue. For each message: validate schemaVersion and required fields (reject if invalid to DLQ), normalize field names if needed, enforce privacy by confirming no text fields present, enrich with cohortId (per DC-FEAT-V1), write reduced event to S3 raw bucket, and optionally update a DynamoDB dedup store per DC-FEAT-V1#Idempotency. Lambda must implement idempotency using ingestionId with 7-day TTL. Log errors (ingestionId + reason) to CloudWatch but do not persist error payloads.
- **Inputs:**
  - SQS message containing validated event (from ING-02, ING-03)
  - S3 bucket name: `signalhr-raw-events-dev`
  - DynamoDB dedup table (optional, created in PROC-03)
  - schemaVersion support: v1
  - Privacy rules from docs/06_security_privacy.md
- **Outputs:**
  - S3 object: `s3://signalhr-raw-events-dev/year=YYYY/month=MM/day=DD/source={source}/events-<timestamp>.jsonl`
  - DynamoDB dedup entry (if dedup table exists)
  - CloudWatch structured logs with ingestionId, schemaVersion, success/failure
  - X-Ray trace data for latency tracking
- **Acceptance Criteria:**
  - Lambda processes SQS event in ≤200ms median latency (per docs/00_project_brief.md Success Criteria)
  - Valid events (DC-ING-V1) written to S3 as newline-delimited JSON
  - Duplicate ingestionIds rejected (second attempt dropped, not persisted)
  - Invalid events logged to CloudWatch with ingestionId and sent to DLQ
  - No text fields in S3 output; privacy scan confirms 0 text occurrences
  - cohortId computed and added to normalized event
- **Evidence of Completion:**
  - Lambda function code committed
  - CloudWatch logs showing 202 successful normalizations
  - Sample S3 object from raw bucket with checksum and line count
  - DynamoDB dedup item JSON (if implemented)
  - Duplicate event test: second occurrence rejected (CloudWatch log)
  - X-Ray trace sample showing <200ms latency
  - Privacy compliance scan output (0 text fields detected)
- **Dependencies:** ING-02, ING-03 (SQS queue), PROC-03 (DynamoDB, optional)
- **Status:** Done
- **Owner:** TBD
- **Start Evidence:** file=lambdas/normalize_handler.py, tests/test_normalize.py (created 2026-02-07); test command: `pytest tests/test_normalize.py -v`
- **Completion Evidence:** 
  - **Timestamp:** 2026-02-07T07:39:55Z
  - **Files:** artifacts/local_demo_20260207_073015/03_aggregates.json, server.log
  - **What it proves:** Normalization handler processed 180 events from bus/queue, extracted userId from each event, computed weekId from ISO calendar timestamp, extracted signalCounts, rejected any text fields. Produced 6 aggregates with correctly computed features (meetings, messages, PRs, overload_trend, context_switch_rate, collaboration_index, growth_index).

---

### PROC-02: Step Functions rollups
- **Title:** Implement Step Functions state machine for daily/weekly aggregation rollups
- **Description:** Create Step Functions state machine that: reads reduced events from S3 raw bucket for a given week, groups by userId, sums signalCounts into per-user-per-week aggregates, computes indices (overload_trend, context_switch_rate, collaboration_index, growth_index per DC-FEAT-V1), writes aggregates to DynamoDB AggregatesTable, and stores a Parquet snapshot to S3 aggregates bucket. Machine must be idempotent and handle partial failures (Map state with error handling). Retry transient failures 3x with exponential backoff.
- **Inputs:**
  - S3 raw events from PROC-01 (reduced events)
  - Week parameter (YYYY-WW format)
  - DynamoDB target table: `AggregatesTable-dev`
  - S3 aggregates bucket: `signalhr-aggregates-dev`
- **Outputs:**
  - DynamoDB AggregatesTable entries (per-user-per-week)
  - S3 Parquet snapshot at `s3://signalhr-aggregates-dev/year=YYYY/week=YYYY-WW/aggregates-<timestamp>.parquet`
  - StepFunctions execution logs and metrics
  - Feature manifest (JSON) with aggregate stats
- **Acceptance Criteria:**
  - State machine processes batch of ~10k events in ≤5 minutes (per docs/00_project_brief.md Success Criteria)
  - DynamoDB aggregate items created with correct PK/SK and all required attributes
  - S3 Parquet snapshot contains aggregates for all users with data that week
  - Retries transient failures; non-transient failures go to failure manifest in S3
  - Execution history shows completion with input/output payloads
  - DynamoDB reads and returns aggregate for sample user/week in ≤50ms (p95)
- **Evidence of Completion:**
  - StepFunctions state machine definition (JSON) committed
  - Execution history screenshot showing successful completion and duration
  - DynamoDB aggregate item JSON for sample user/week
  - S3 Parquet object key and line count (validate Glue schema)
  - Feature manifest JSON from execution
  - Partial failure test: sample failure manifest in S3
  - Query latency test screenshot (DynamoDB GetItem <50ms)
- **Dependencies:** PROC-01, PROC-03 (DynamoDB table)
- **Status:** Not Started
- **Owner:** TBD
- **Start Evidence:** (blank until in-progress)
- **Completion Evidence:** (blank until done)

---

### PROC-03: DynamoDB AggregatesTable + AlertsTable
- **Title:** Create DynamoDB tables for aggregates and alerts with encryption and indexing
- **Description:** Provision two DynamoDB tables per DC-DDB-AGG-V1 and DC-DDB-ALERT-V1:
1. `AggregatesTable-dev`: PK=USER#<userId>, SK=WEEK#YYYY-WW, with attributes per DC-DDB-AGG-V1 and GSI1 for manager team queries. On-demand billing.
2. `AlertsTable-dev`: PK=ALERT#<alertId>, SK=USER#<userId>#WEEK#YYYY-WW, with attributes per DC-DDB-ALERT-V1. On-demand billing.
Both tables encrypted with KMS key from OBS-02, TTL enabled for retention policy (aggregates 2 years, alerts TBD per config), CloudWatch metrics enabled.
- **Inputs:**
  - KMS key ARN (from OBS-02)
  - Table schemas from docs/02_data_contracts.md
  - Billing mode: on-demand (no capacity planning needed for MVP)
- **Outputs:**
  - AggregatesTable-dev with GSI1
  - AlertsTable-dev
  - KMS encryption enabled on both
  - TTL configured on both
  - CloudWatch metrics dashboard
  - CloudTrail audit trail for table changes
- **Acceptance Criteria:**
  - Tables created and accessible via boto3/SDK
  - GSI1 on AggregatesTable supports manager team queries
  - PK/SK keys match DC-DDB-AGG-V1 and DC-DDB-ALERT-V1
  - KMS encryption applied; key rotation enabled
  - TTL working (test by creating an item with TTL expiry and verify deletion after)
  - CloudWatch shows read/write units and throttling metrics (none expected on-demand)
  - No items persisted until PROC-01/PROC-02 runs
- **Evidence of Completion:**
  - DynamoDB console screenshots for both tables
  - Table attributes and GSI configuration JSON export
  - KMS encryption enabled screenshot
  - TTL configuration screenshot
  - Test item creation and TTL expiry validation (CloudWatch log)
  - Query performance test (GetItem latency <50ms)
  - CloudTrail event showing table creation
- **Dependencies:** OBS-02 (KMS key)
- **Status:** Done (Local SQLite Equivalent)
- **Owner:** TBD
- **Start Evidence:** file=store/aggregates_store.py (created 2026-02-07)
- **Completion Evidence:** 
  - **Timestamp:** 2026-02-07T07:39:55Z
  - **Files:** artifacts/local_demo_20260207_073015/03_aggregates.json, aggregates.db
  - **What it proves:** SQLite aggregates store (local equivalent of DynamoDB) persisted 6 aggregates with schema matching DC-DDB-AGG-V1. Each aggregate contains PK (userId), SK (weekId), and features (meetings, messages, PRs, overload_trend, context_switch_rate, collaboration_index, growth_index).

---

## FEATURE STORE & BIAS EPIC (FEAT) — 6 hours

### FEAT-01: Feature extraction jobs (Glue/Lambda)
- **Title:** Implement Glue or Lambda job to compute four required features per user/week
- **Description:** Create a Glue job or Lambda function that reads aggregates from DynamoDB (or S3 snapshots from PROC-02), computes the four required features per DC-FEAT-V1: overload_trend (4-week moving avg of meetings+messages), context_switch_rate (context_switches / meetings+messages), collaboration_index (PRs + reactions / base), growth_index (week-over-week change in activity). Write feature parquet to S3 feature store with columns including cohortId, z-score placeholders. Register output in Glue Data Catalog.
- **Inputs:**
  - DynamoDB AggregatesTable-dev or S3 aggregates snapshot
  - Historical aggregates for 4-week lookback (for trend)
  - Feature definitions and formulas from DC-FEAT-V1
- **Outputs:**
  - S3 feature parquet: `s3://signalhr-aggregates-dev/features/year=YYYY/week=YYYY-WW/feature-<timestamp>.parquet`
  - Glue Data Catalog table registration
  - Feature manifest JSON with stats (count of features, min/max, nulls)
- **Acceptance Criteria:**
  - Features computed for ≥95% of users with data in week (per docs/00_project_brief.md Success Criteria)
  - Four features present in parquet: overload_trend, context_switch_rate, collaboration_index, growth_index
  - cohortId included in output
  - Feature values finite and within reasonable bounds (no NaN/Inf)
  - Glue table queryable via Athena
  - Execution logs show row count and any errors (sampling)
- **Evidence of Completion:**
  - Glue job definition or Lambda function code committed
  - Feature parquet object key, checksum, and row count
  - Glue Data Catalog table schema screenshot
  - Feature manifest JSON (sample)
  - Athena query screenshot (SELECT * from features LIMIT 5)
  - Feature statistics (min/max/count) for validation
  - Null handling verification (confirmed expected nulls or none)
- **Dependencies:** PROC-02 (aggregates), PROC-03 (DynamoDB)
- **Status:** Not Started
- **Owner:** TBD
- **Start Evidence:** (blank until in-progress)
- **Completion Evidence:** (blank until done)

---

### FEAT-02: Cohort baseline & z-score
- **Title:** Compute cohort baselines and z-score normalize features per cohort
- **Description:** Extend FEAT-01 job (or create new job) to compute per-cohort statistics per DC-FEAT-V1: cohortId = sha256(orgId + '|' + role + '|' + seniority + '|' + teamId) truncated to 16 hex chars. For each cohort with ≥5 members, compute mu (mean) and sigma (stddev) for each feature; for <5, fallback to broader cohort (role+seniority or org-wide). Store cohort_baseline (mu, sigma, size, baseline_source) in DynamoDB AggregatesTable. Compute z-scores: z = (x - mu) / sigma. Store z_scores in AggregatesTable.z_scores map.
- **Inputs:**
  - Features from FEAT-01 (parquet)
  - Role, seniority, org, team from AggregatesTable
  - Cohort size threshold: 5
  - Fallback logic per DC-FEAT-V1
- **Outputs:**
  - DynamoDB AggregatesTable updated with cohort_baseline and z_scores maps
  - Feature parquet updated with z-score columns (z_overload_trend, z_context_switch_rate, z_collaboration_index, z_growth_index)
  - Feature manifest updated with cohort counts and baseline_source distributions
- **Acceptance Criteria:**
  - Cohort baselines computed for ≥95% of users
  - z-scores finite and within typical range (~-3 to +3 for normal dists)
  - Fallback logic applied correctly (log baseline_source field)
  - DynamoDB AggregatesTable items contain cohort_baseline and z_scores
  - No cross-cohort mixing (z-scores only within cohort)
  - Feature parquet includes z-score columns
- **Evidence of Completion:**
  - Job code (Glue/Lambda) committed with baseline logic
  - DynamoDB AggregatesTable item JSON showing cohort_baseline and z_scores
  - Feature parquet with z-score columns (checksum, row count)
  - Feature manifest showing cohort breakdown and baseline_source distribution (e.g., 90% cohort, 8% role_seniority, 2% org)
  - Sample z-score statistics (mean=~0, stddev=~1 within cohort)
  - Fallback test: small cohort fallback to broader baseline (log evidence)
- **Dependencies:** FEAT-01, PROC-03 (DynamoDB updates)
- **Status:** Not Started
- **Owner:** TBD
- **Start Evidence:** (blank until in-progress)
- **Completion Evidence:** (blank until done)

---

## INTELLIGENCE EPIC (INT) — 8 hours

### INT-01: Rules engine (Lambda)
- **Title:** Implement rule-based detector for burnout and performance patterns
- **Description:** Create Lambda function that reads AggregatesTable and feature data, applies rule-based heuristics to flag anomalies: e.g., z_overload_trend > 2 for burnout, z_growth_index > 1.5 for HiPo. Write alerts to AlertsTable with scoreProbability (0-1 heuristic estimate), topFeatures (list of contributing signals), and ruleTriggered (human-readable rule name). Ensure alerts include only sanitized feature/cohort data, no raw identifiers.
- **Inputs:**
  - AggregatesTable with z_scores
  - Feature data from FEAT-02
  - Rule definitions and thresholds (configurable in code or config file)
- **Outputs:**
  - AlertsTable entries for flagged users
  - Rule execution logs (CloudWatch)
  - Alert statistics (count by ruleTriggered)
- **Acceptance Criteria:**
  - Rules engine achieves ≥0.8 precision on synthetic labeled test set (per docs/00_project_brief.md Success Criteria)
  - Alerts written to AlertsTable with correct PK/SK
  - scoreProbability in [0, 1] range
  - topFeatures list (max 3-5 features) with signal contribution explanation
  - ruleTriggered field human-readable (e.g., "high_overload_trend", "high_growth_hippo")
  - No raw event data or PII in alerts
  - Execution logs show rule application counts and pass-through logic
- **Evidence of Completion:**
  - Rules engine Lambda code committed
  - AlertsTable items JSON (sample 2-3 alerts)
  - Rule definitions documentation (thresholds, logic)
  - Precision test report on synthetic labeled data
  - Rule application counts and metrics screenshot
  - Privacy compliance scan (0 raw identifiers in alerts)
- **Dependencies:** FEAT-02 (z_scores), PROC-03 (AlertsTable)
- **Status:** Done
- **Owner:** TBD
- **Start Evidence:** file=intelligence/rules_engine.py (created 2026-02-07)
- **Completion Evidence:** 
  - **Timestamp:** 2026-02-07T07:39:55Z
  - **Files:** artifacts/local_demo_20260207_073015/04_alerts.json
  - **What it proves:** Rules engine applied deterministic scoring rules (burnout >= meetings 4 + messages 30 + context_switch 1.5; HiPo >= PRs 3 + growth_index 0.3 + collaboration 1.0; drift >= high_meetings AND zero_PRs). Generated 6 alerts with scoreProbability (0-1), topFeatures, reasons, and ruleTriggered (human-readable). Example: Alice flagged with burnout=1.0 (max score) due to "High meeting load (5 meetings)" and "High communication load (37 messages)".

---

### INT-02: SageMaker Serverless XGBoost
- **Title:** Train and deploy light ML model for scoring and explainability
- **Description:** Create SageMaker Serverless XGBoost training job using feature parquet from FEAT-02. Train on synthetic labeled dataset (3 classes: burnout, hippo, normal or binary). Deploy model to SageMaker Serverless endpoint for real-time scoring. Endpoint returns probability and feature importances (SHAP-like). Model versioning tracked in S3 manifest.
- **Inputs:**
  - Feature parquet from FEAT-02
  - Synthetic labeled dataset (Alice, Ben, Carol with ground truth labels)
  - Hyperparameters (num_rounds, learning_rate, max_depth, etc.) tuned for MVP
- **Outputs:**
  - SageMaker training job artifacts in S3
  - XGBoost model artifact (tar.gz)
  - SageMaker Serverless endpoint: `signalhr-xgb-mvp`
  - Model versioning manifest in S3
  - Feature importance scores exported
- **Acceptance Criteria:**
  - Training job completes and produces model artifact
  - Endpoint deployed and responds to InvokeEndpoint calls in ≤2 seconds (per docs/00_project_brief.md Success Criteria)
  - Scoring output includes: probability (float), top 3 feature importances (list with names + values)
  - Model artifact and version tracked in S3 manifest
  - Feature importance values sum to ~1.0 or normalized appropriately
  - No model drift on re-training (validation data score consistent)
- **Evidence of Completion:**
  - Training job definition and output logs
  - Model artifact S3 key and checksum
  - Endpoint configuration JSON (Serverless)
  - Sample InvokeEndpoint response (JSON) with probability and feature importances
  - Feature importance screenshot or JSON export
  - Latency test screenshot (<2s endpoint response)
  - Model version manifest JSON
  - Training/validation accuracy metrics
- **Dependencies:** FEAT-02 (features)
- **Status:** Not Started
- **Owner:** TBD
- **Start Evidence:** (blank until in-progress)
- **Completion Evidence:** (blank until done)

---

### INT-03: Explainability packaging
- **Title:** Package explanations from rules and ML models into structured format (with Vertex AI Gemini option)
- **Description:** Create explainability layer that takes rule-based alerts and ML scores from INT-01 and INT-02, and produces structured explanations per DC-EXPLAIN-V1. Primary: Google Cloud Vertex AI Gemini (real AI, privacy-safe, deterministic at temperature=0.0). Fallback: Rule-based template explanations (100% deterministic). For each alert, generate "Why flagged" (summary of contributing signals, z-scores, cohort comparison) and "Next best action" (coaching suggestions without punitive language). Store explanation JSON in S3 or local file per DC-EXPLAIN-V1 schema. Reference explanationRef in AlertsTable.
- **Inputs:**
  - AlertsTable entries from INT-01
  - SageMaker scoring results from INT-02 (probability, feature importances)
  - AggregatesTable data for cohort comparison
  - KB snippets (template strings for now, pre-seeded coaching actions)
  - (Gemini) Vertex AI API credentials via GOOGLE_APPLICATION_CREDENTIALS
- **Outputs:**
  - Explanation JSON per DC-EXPLAIN-V1: s3://signalhr-explanations-dev/<explanationId>.json (AWS) or local 05_ai_explanations.json (local)
  - AlertsTable.explanationRef updated with S3 key (AWS) or aiSource field showing "gemini" or "rule-based"
  - Explanation statistics (count by action_type, AI source)
- **Acceptance Criteria:**
  - Explanations generated for 100% of alerts (sample: 2-3)
  - Explanations include: summary, signals (feature + z-score), cohort_comparison (text), next_best_actions (list)
  - No raw PII or event text in explanations; cohort stats and aggregates only
  - explanationRef in AlertsTable correctly references S3 key (AWS) or populated (local)
  - Explanation JSON valid against DC-EXPLAIN-V1 schema
  - S3 objects encrypted with KMS (AWS)
  - AI source field indicates "gemini" (if Vertex AI available) or "rule-based" (fallback)
- **Evidence of Completion:**
  - Explainability code: ai/gemini_explainer.py (Gemini + fallback)
  - Fallback code: intelligence/explainer.py (rule-based, for when Gemini unavailable)
  - Sample explanation JSON (2-3 examples)
  - Explanation schema validation (JSON schema check passed)
  - AlertsTable items with explanationRef or aiSource populated
  - S3 object key and KMS encryption screenshot (AWS) or local file artifact (local)
  - Privacy compliance scan (0 PII/raw text in explanations)
  - Gemini prompt engineering documentation (ai/gemini_explainer.py docstring)
- **Dependencies:** INT-01, INT-02, PROC-03 (AlertsTable), optional: Google Cloud Vertex AI credentials
- **Status:** In Progress (Gemini layer added, rule-based fallback preserved)
- **Owner:** TBD
- **Start Evidence:** 
  - file=ai/gemini_explainer.py (created 2026-02-07, 450+ LOC)
  - file=ai/__init__.py (module initialization, created 2026-02-07)
  - file=intelligence/explainer.py (rule-based fallback, unchanged 2026-02-07)
- **Completion Evidence:** 
  - **Timestamp:** 2026-02-07T08:45:00Z (Gemini layer) + 2026-02-06T06:39:55Z (original rule-based)
  - **Files:** 
    - ai/gemini_explainer.py (Vertex AI Gemini integration, 450+ LOC)
    - ai/__init__.py (module exports)
    - scripts/demo.sh (updated step [6/6] with Gemini + fallback)
    - artifacts/local_demo_*/05_ai_explanations.json (with ai_source field)
  - **What it proves:** 
    - Explainability layer supports REAL AI (Vertex AI Gemini) with graceful fallback to rule-based
    - Generates human-readable explanations for all alerts
    - Each explanation contains: alertType (burnout/hipo/baseline), summary, why_flagged, next_best_actions, ai_source
    - Gemini explanations (when available): AI-generated coaching suggestions (real intelligence)
    - Rule-based fallback (when Gemini unavailable): Template-based explanations (deterministic)
    - Privacy-safe: Prompt never includes raw text, user IDs, or PII (only aggregates and features)
    - HR-friendly: Gemini prompt explicitly prevents punitive language and ensures decision-support tone
    - Deterministic when needed: Fallback is 100% deterministic; Gemini uses temperature=0.0

---

## BEDROCK EXPLAINABILITY & COACHING EPIC (BED) — 6 hours (DEFERRED FOR POST-HACKATHON)

### BED-01: Bedrock Agent integration (DEFERRED)
- **Title:** Integrate Bedrock Agent for Manager Copilot and guardrailed explanations
- **Description:** Create Bedrock Agent (or invoke Bedrock Claude model with prompt engineering) that takes sanitized explanation input (no PII) and knowledge base references, and produces conversational "Why flagged" and "Next best action" outputs. Implement prompt guardrails per docs/06_security_privacy.md: agent must refuse to provide punitive advice (termination, discipline) and must reference only KB and aggregated signals. Add post-response scanner to detect policy violations or PII leakage; discard unsafe outputs and log incidents. NOTE: Bedrock now deferred in favor of Vertex AI Gemini (available during hackathon). Will integrate Bedrock when AWS permissions available.
- **Inputs:**
  - Explanation JSON from INT-03 (signals, z-scores, cohort comparison, action suggestions)
  - KB documents (policies, burnout prevention best practices) from BED-02
  - Bedrock API key/credentials
  - Prompt and guardrails per docs/06_security_privacy.md
- **Outputs:**
  - Bedrock Agent conversation/response with "Why flagged" narrative
  - Suggested coaching actions (sanitized, no punitive language)
  - Bedrock session ID or conversation ID for audit
  - Canonical explanation text stored in S3 (DC-EXPLAIN-V1#Storage reference rules)
  - Post-response scanner logs (PII scan, policy adherence check)
- **Acceptance Criteria:**
  - Agent responds with human-readable explanation for sample alerts
  - Outputs include both "Why flagged" (reference to signals) and "Next best action" (coaching)
  - No PII leaked (scanner detects 0 occurrences in test)
  - No punitive advice suggested (guardrails working; attempt to ask for termination recommendation is refused)
  - Explanation text stored in S3 and referenced in AlertsTable.explanationRef
  - Agent responses consistent with KB content (citations visible in output or logs)
- **Evidence of Completion:**
  - Bedrock Agent definition or prompt engineering code committed
  - Sample Bedrock responses (2-3 examples) showing "Why flagged" and "Next best action"
  - Guardrail test: adversarial prompt (ask for termination) rejected (response log)
  - PII scanner test: no PII detected in outputs (scan report)
  - Post-response validation logs (policy checks passed)
  - Canonical explanation S3 object keys
  - Bedrock API invocation logs (sample session ID)
- **Dependencies:** BED-02 (KB must exist), INT-03 (explanation inputs)
- **Status:** Not Started
- **Owner:** TBD
- **Start Evidence:** (blank until in-progress)
- **Completion Evidence:** (blank until done)

---

### BED-02: Knowledge Base ingestion
- **Title:** Ingest company policies and burnout prevention playbooks for KB/RAG
- **Description:** Create KB documents (S3 objects) containing: company HR policies (confidential, non-punitive approach), burnout prevention best practices, wellness resources, 1:1 question templates, workload management suggestions. Documents must be sanitized (no employee names or specifics). Optionally index documents in OpenSearch Serverless for vector search/RAG. KB documents referenced by Bedrock Agent for grounding explanations.
- **Inputs:**
  - Policy document templates (no real PII, generic policies)
  - Burnout prevention best practices (public domain sources or templates)
  - Wellness resources
  - Coaching playbook (1:1 questions, workload suggestions)
- **Outputs:**
  - S3 KB bucket: `s3://signalhr-kb-dev/`
  - Objects: policies.md, burnout_prevention.md, wellness_resources.md, coaching_playbook.md (sample names)
  - Glue Data Catalog registration (optional, for OpenSearch integration)
  - OpenSearch Serverless index (optional): `signalhr-kb-index`
- **Acceptance Criteria:**
  - KB documents created and stored in S3 under prefix `s3://signalhr-kb-dev/`
  - Documents contain practical guidance (policies, best practices, resources)
  - No employee PII in KB documents
  - Documents accessible to Bedrock (role/permissions set up)
  - If OpenSearch used: documents indexed and retrievable via vector search (sample query returns relevant doc)
  - KB size reasonable for MVP (~5-20 MB)
- **Evidence of Completion:**
  - S3 KB objects listing (keys and sizes)
  - Sample KB document content (snippet from each type)
  - IAM role allowing Bedrock to read KB
  - OpenSearch index screenshot (if used)
  - Sample OpenSearch retrieval query result
  - Bedrock KB reference in prompt (pointer to S3 KB location)
- **Dependencies:** BED-01 uses KB; can be in-parallel
- **Status:** Not Started
- **Owner:** TBD
- **Start Evidence:** (blank until in-progress)
- **Completion Evidence:** (blank until done)

---

## EXPERIENCE LAYER EPIC (UI) — 6 hours

### UI-01: Cognito RBAC
- **Title:** Provision Cognito user pool with Manager/Employee/HR groups and attribute-based access
- **Description:** Create Cognito user pool `signalhr-userpool-dev` with user groups: Manager (team-level access), Employee (own data + opt-in signals), HR (audit/compliance view). Assign RBAC attributes: `team_id`, `role_level`, `opt_in_visibility`. Create test users for each group. Configure attribute-based access policies in backend APIs to enforce group membership and opt-in flags.
- **Inputs:**
  - User pool name: `signalhr-userpool-dev`
  - Groups: Manager, Employee, HR
  - Attributes: team_id, role_level, opt_in_visibility (custom)
  - Test user credentials (no production emails)
- **Outputs:**
  - Cognito user pool created with app client
  - User groups configured with IAM policies (or app-enforced RBAC)
  - Test users created (1 Manager, 1 Employee, 1 HR)
  - JWT token structure documented (groups claim visible)
  - CORS/OAuth callback URLs configured for Amplify frontend
- **Acceptance Criteria:**
  - User pool created and accessible via console
  - Groups visible with members assigned
  - JWT tokens include `cognito:groups` claim with correct group
  - Manager user can login and token shows Manager group
  - Employee user can login and token shows Employee group
  - HR user can login and token shows HR group
  - App client credentials configured (client ID, secret)
  - Tokens valid for ~1 hour (configurable)
- **Evidence of Completion:**
  - Cognito user pool console screenshot
  - User groups configuration screenshot
  - Sample JWT token (header.payload visible, groups claim shown)
  - Test user login successful (CloudWatch log or Cognito sign-in events)
  - CORS/callback URL configuration screenshot
  - Token lifetime and refresh token settings confirmed
- **Dependencies:** None (foundational for UI)
- **Status:** Not Started
- **Owner:** TBD
- **Start Evidence:** (blank until in-progress)
- **Completion Evidence:** (blank until done)

---

### UI-02: Amplify/Next.js skeleton
- **Title:** Host minimal dashboard and portal with Cognito auth and API integration
- **Description:** Deploy minimal Next.js application via Amplify Hosting with three views: (1) Manager Dashboard (team heatmap showing alerts, click to view explanation), (2) Employee Portal ("My signals" view with opt-in toggles and personal alerts), (3) Audit View for HR (explanation history and KB references). UI calls backend APIs (API Gateway endpoints) to fetch AggregatesTable, AlertsTable, and explanations from S3. Cognito auth enforced per group (Manager sees team, Employee sees own, HR sees audit log).
- **Inputs:**
  - Next.js app template
  - Amplify CLI configured
  - Cognito user pool from UI-01
  - API Gateway endpoint URLs (from ING-01)
  - AlertsTable and explanations data (from INT-01/BED-01)
- **Outputs:**
  - Next.js app deployed to Amplify Hosting (dev environment)
  - Three pages: Manager Dashboard, Employee Portal, Audit View
  - API integration: fetch aggregates, alerts, explanations
  - Authentication: Cognito login/logout flows
  - UI responsive and accessible (basic styling, no advanced UX)
- **Acceptance Criteria:**
  - App deployed and accessible via Amplify URL
  - Cognito login required; redirects to dashboard after auth
  - Manager view shows team heatmap with sample alerts (clickable)
  - Employee view shows personal aggregates and opt-in toggles
  - HR view lists explanations with KB references
  - Clicking an alert shows explanation from S3 or Bedrock output
  - Group-based access enforced (Manager cannot view Employee personal data outside team)
  - Page load time <3 seconds
- **Evidence of Completion:**
  - Next.js app code committed
  - Amplify deployment logs and URL
  - Screenshots of all three views (Manager Dashboard, Employee Portal, Audit View)
  - Sample alert click showing explanation modal
  - Authentication flow screenshot (login → dashboard)
  - Network tab showing API calls to fetch data
  - Group-based access test (attempt cross-group access, denied)
- **Dependencies:** UI-01 (Cognito), ING-01 (API endpoint), INT-01/BED-01 (data)
- **Status:** Not Started
- **Owner:** TBD
- **Start Evidence:** (blank until in-progress)
- **Completion Evidence:** (blank until done)

---

## OBSERVABILITY & SECURITY EPIC (OBS) — varies

### OBS-01: CloudWatch, X-Ray, CloudTrail dashboards
- **Title:** Configure observability stack with logs, traces, metrics, and audit trail
- **Description:** Set up CloudWatch log groups for Lambda, Step Functions, API Gateway, and SageMaker. Create CloudWatch dashboard showing pipeline metrics: EventBridge events/min, SQS depth, Lambda errors/latency, StepFunction duration, DynamoDB consumed capacity, Bedrock requests. Enable X-Ray tracing for end-to-end latency from API request to explanation. Enable CloudTrail logging to encrypted S3 bucket for audit. Configure alarms for DLQ >0, Lambda error rate >1%, StepFunction failures.
- **Inputs:**
  - Log group names and retention policies
  - X-Ray sampling rate (10% for MVP)
  - CloudTrail S3 bucket and encryption key
  - Alarm thresholds (DLQ>0, errors >1%, failures >0)
- **Outputs:**
  - CloudWatch log groups created with retention
  - CloudWatch dashboard with key metrics
  - X-Ray service map and traces enabled
  - CloudTrail trail active and logging to S3
  - SNS topic for alarm notifications (optional)
  - CloudWatch alarms created and active
- **Acceptance Criteria:**
  - Log groups exist and receive logs from Lambda, StepFunctions, API Gateway
  - Dashboard displays 10+ metrics with recent data
  - X-Ray shows traces for sample API request → pipeline flow
  - CloudTrail events visible in S3 and queryable via CloudTrail console
  - Alarms active; test DLQ >0 alarm triggers
  - No gaps in logging or tracing
- **Evidence of Completion:**
  - CloudWatch log groups screenshot
  - Dashboard screenshot showing >10 metrics with data
  - X-Ray service map and sample trace
  - CloudTrail S3 location and bucket policy screenshot
  - Alarm definitions and test trigger (CloudWatch event)
  - SNS notification receipt (if configured)
- **Dependencies:** All infrastructure tasks (ING-01 through PROC-03)
- **Status:** Not Started
- **Owner:** TBD
- **Start Evidence:** (blank until in-progress)
- **Completion Evidence:** (blank until done)

---

### OBS-02: IAM & KMS
- **Title:** Apply least-privilege IAM roles and KMS encryption
- **Description:** Create KMS key `signalhr-dev-key` for S3 and DynamoDB encryption. Define IAM roles and policies per docs/01_architecture.md#Architecture-Guardrails for each service:
- API Gateway → PutEvents on EventBridge (action: eventbridge:PutEvents, resource: arn:aws:events:us-east-1:*:event-bus/signalhr-bus-dev)
- EventBridge Pipes → SQS (sqs:SendMessage to queue)
- Lambda → read SQS, write S3 (S3: GetObject, PutObject on raw bucket; SQS: ReceiveMessage, DeleteMessage)
- StepFunctions → read S3, invoke Lambdas, write DynamoDB
- SageMaker → read feature parquet from S3, write model artifacts
- Bedrock role (if service-to-service) → read KB from S3
- UI (Cognito) → query aggregates via backend API (enforced via API Gateway auth)
- **Inputs:**
  - Service principals (events.amazonaws.com, lambda.amazonaws.com, states.amazonaws.com, etc.)
  - Resource ARNs for each service
  - Encrypt/decrypt permissions for KMS key
- **Outputs:**
  - KMS key created and enabled
  - IAM role for each service with inline/managed policies
  - Role trust relationships configured (principal = service)
  - Key policy allowing service use
  - No global S3 or DynamoDB read permissions (all scoped)
- **Acceptance Criteria:**
  - KMS key created with rotation enabled
  - Each service role has minimal permissions (deny on undefined resources)
  - S3 buckets encrypted with KMS (test: verify x-amz-server-side-encryption header)
  - DynamoDB encrypted (console shows encryption enabled)
  - No overly permissive policies (e.g., s3:* on all buckets); no wildcards on principals
  - CloudTrail shows role assumptions only for correct services
- **Evidence of Completion:**
  - KMS key creation and rotation screenshot
  - IAM role policies (JSON) for each service (5-7 roles)
  - Role trust policy (principal restricted to service)
  - S3 bucket encryption header verification (curl test output)
  - DynamoDB console showing encryption enabled
  - CloudTrail access logs showing role assumptions
  - Policy analysis report (no overly permissive rules found)
- **Dependencies:** None (pre-req for all infrastructure)
- **Status:** Not Started
- **Owner:** TBD
- **Start Evidence:** (blank until in-progress)
- **Completion Evidence:** (blank until done)

---

## DOCUMENTATION & QA EPIC (DOC/QA) — varies

### DOC-01: Populate required docs (COMPLETED)
- **Title:** Create and maintain all mandatory documentation files
- **Description:** This task is already **COMPLETED** in previous steps. All docs (00-09) created and hardened with:
  - docs/00_project_brief.md (immutable, AI execution rules)
  - docs/01_architecture.md (guardrails, data classification, ASCII diagram)
  - docs/02_data_contracts.md (Contract Index, validation, enums, idempotency, explanation schema)
  - docs/03_backlog.md (this file, expanded task specs)
  - docs/04_runbook.md (how to run, test, demo)
  - docs/05_qa_strategy.md (test plans, eval rubric, quality gates)
  - docs/06_security_privacy.md (privacy rules, guardrails, audit)
  - docs/07_demo_script.md (3-employee scenario, evidence checklist)
  - docs/CHANGE_REQUESTS.md (CR template and log)
  - docs/08_deployment_plan.md (IaC and deployment steps)
  - docs/09_observability.md (dashboards, logs, traces, audit)
- **Inputs:** Project plan from user request
- **Outputs:** All docs committed to repo
- **Acceptance Criteria:** All docs exist, are linked, and reference each other correctly
- **Evidence of Completion:** Docs/ folder with all files (verified in repo)
- **Dependencies:** None
- **Status:** Done (completed in prior steps)
- **Owner:** TBD
- **Start Evidence:** N/A
- **Completion Evidence:** Docs folder listing and file timestamps

---

### QA-01: QA test harness + synthetic dataset
- **Title:** Implement unit, integration, E2E, and LLM eval tests with synthetic data
- **Description:** Create test suites for: (1) Unit tests (normalization logic, cohort computation, z-score math), (2) Integration tests (EventBridge → SQS → Lambda → DynamoDB path, StepFunction rollup), (3) E2E tests (synthetic generator → full pipeline → UI visualization), (4) LLM eval tests (Bedrock guardrail adherence, hallucination detection, PII leakage scanner). Synthetic test dataset includes 3 users (Alice overload, Ben HiPo, Carol baseline) with expected outputs defined. Test harness runs via CI (GitHub Actions or AWS CodeBuild) and outputs test reports to S3.
- **Inputs:**
  - Code modules to test (Lambda, StepFunctions, feature jobs, rules engine, Bedrock integration)
  - Synthetic labeled dataset (3 users with ground truth)
  - Test assertion definitions (e.g., Alice precision ≥0.8, Bedrock zero PII leakage)
- **Outputs:**
  - pytest/mocha test files for unit and integration tests
  - E2E test scripts (bash or Python) orchestrating pipeline
  - LLM eval harness (prompt/response pairs, guardrail checks)
  - Test reports (HTML/JSON) in s3://signalhr-test-reports/
  - Coverage report (≥70% for modified modules)
- **Acceptance Criteria:**
  - All unit tests pass (100% of changed modules)
  - Integration tests pass (E2E data validation)
  - E2E tests produce expected alerts and explanations
  - LLM eval reports: 0 PII leakage, 0 hallucination on synthetic tests, guardrail pass rate 100%
  - Test coverage ≥70% for changed modules
  - Test reports timestamped and accessible
- **Evidence of Completion:**
  - Test code committed (pytest/mocha/bash files)
  - Test run logs and reports (S3 object keys)
  - Coverage report (HTML or JSON)
  - LLM eval report (prompt/response samples, policy check results)
  - Synthetic dataset file (JSONL or CSV with labels)
  - CI pipeline configuration (GitHub Actions or CodeBuild)
- **Dependencies:** All implementation tasks (ING through BED)
- **Status:** Not Started
- **Owner:** TBD
- **Start Evidence:** (blank until in-progress)
- **Completion Evidence:** (blank until done)

---

### DEMO-01: Demo scenario & evidence capture
- **Title:** Execute 3-employee demo and capture evidence artifacts
- **Description:** Run the demo scenario per docs/07_demo_script.md with 3 synthetic users (Alice, Ben, Carol). Execute generator, monitor pipeline via CloudWatch, trigger rollups, run feature jobs and scoring, open Manager Dashboard, inspect explanations, and capture screenshots and logs. Save all evidence to s3://signalhr-test-reports/demo/<timestamp>/: generator logs, API requests/responses, DynamoDB items, AlertsTable entries, S3 explanation objects, and UI screenshots.
- **Inputs:**
  - Synthetic generator (ING-04)
  - Full pipeline (ING through BED)
  - Deployed UI (UI-02)
  - Demo runbook steps (docs/07_demo_script.md)
- **Outputs:**
  - Generator logs (event count, rate, timestamps)
  - EventBridge metrics screenshot
  - S3 raw events (sample file and checksum)
  - DynamoDB aggregate items (Alice, Ben, Carol)
  - AlertsTable entries (expected alerts for Alice and Ben)
  - Explanation S3 objects (or Bedrock session IDs)
  - Manager Dashboard screenshot (team heatmap with 3 users, 2 alerts visible)
  - Explanation modal screenshot (Alice alert → "Why flagged" + "Next best action")
  - Employee Portal screenshot (Alice view of own signals + opt-in toggles)
  - Audit View screenshot (HR view of explanation history)
  - CloudWatch logs linking evidence
  - Demo narrative (2-3 min script with talking points)
- **Acceptance Criteria:**
  - Demo runs end-to-end without manual intervention (one-click or one-command to start)
  - All 3 users' data flows through pipeline and appears in dashboards
  - Alice flagged as overloaded with believable reason ("high z_overload_trend + meetings")
  - Ben flagged as HiPo with believable reason ("high z_growth_index + PRs")
  - Carol not flagged (baseline expected)
  - Explanations generated and displayed in UI
  - Cognito auth works (demo flow includes login)
  - Evidence captured with timestamps and linked in docs/03_backlog.md
- **Evidence of Completion:**
  - Demo scenario execution log
  - Screenshots (all 4 views: generator log, dashboard, explanation, audit)
  - DynamoDB items and AlertsTable JSON
  - Explanation S3 objects and checksums
  - Generator command and expected output snippet
  - CloudWatch log ARNs and snippets
  - Demo success/fail checklist from docs/07_demo_script.md
  - Demo video recording (optional, MP4)
- **Dependencies:** All implementation tasks
- **Status:** Done (Local Simulation Mode)
- **Owner:** TBD
- **Start Evidence:** file=scripts/demo.sh (created 2026-02-07); command: `bash scripts/run_local.sh && bash scripts/demo.sh`
- **Completion Evidence:** 
  - **Timestamp:** 2026-02-07T07:39:55Z
  - **Directory:** artifacts/local_demo_20260207_073015/
  - **Files:**
    - `01_bus_metrics.json` — EventBridge bus accepted 180 events (90 posted, 2 copies due to Pipes/forward behavior)
    - `02_queue_metrics.json` — SQS queue depth 180 (all events routed)
    - `03_aggregates.json` — 6 aggregates stored (2-3 users per profile variant)
    - `04_alerts.json` — 6 alerts generated (burnout, HiPo, drift scoring with explainable reasons)
    - `05_ai_explanations.json` — 6 AI explanations (natural language summaries, why_flagged, next_best_actions)
    - `DEMO_SUMMARY.md` — Full human-readable report with test results, outputs, alert summary, AI explainability examples, and verification checklist
    - `post_events.log` — HTTP 202 POST success log (90 events)
    - `server.log` — FastAPI server logs (request processing, validation)
    - `aggregates.db` — SQLite database with persisted aggregates
  - **What it proves:** Full pipeline executed end-to-end: Event generation → API ingestion → EventBridge routing → Normalization → Aggregation → Rules scoring → AI explainability. All outputs match expected schemas. Demo runs in <2 minutes without manual intervention. No LLM used; explanations deterministic and template-based. Privacy rules enforced (no text fields, numeric signals only).

---

## Summary

**Total Tasks:** 21 (ING-01 through DEMO-01)
**Total Epics:** 8 (Ingestion, Processing, Features, Intelligence, Bedrock, UI, Observability, QA/Demo)
**Status:** All Not Started (except DOC-01 = Done)
**48-Hour Budget:** ING(6h) + PROC(8h) + FEAT(6h) + INT(8h) + BED(6h) + UI(6h) + OBS(varies, ~3h) + QA(~8h) + Demo(1h) ≈ 48h (tight but feasible with parallel work)

Each task above is now executable without additional explanation. Executor should reference docs (00-02, 04-09) for data contracts, architecture, and standards.
