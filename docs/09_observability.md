# Observability & Audit — Dashboards, Logs, and Traces

**CRITICAL:** This document defines enforceable observability, audit, and evidence controls. All observability rules are binding, verifiable, and aligned with docs/06_security_privacy.md (AUDIT-01, AUDIT-02, AUDIT-03, AUDIT-04).

---

## Observability Control Index (NEW)

Stable observability control IDs organize logging, tracing, dashboards, and audit requirements. Maps to backlog tasks OBS-01, OBS-02, OBS-03, OBS-04.

| Control ID | Control Name | Enforces | Where | Task |
|------------|--------------|----------|-------|------|
| OBS-01 | Observability Infrastructure | CloudWatch, X-Ray, CloudTrail provisioned and enabled | AWS console + IaC | OBS-02 |
| OBS-02 | Encryption & Secret Management | All logs encrypted with KMS; secrets in Secrets Manager | S3, CloudWatch Logs, Secrets Manager | OBS-02 |
| OBS-03 | Log Group Naming Conventions | Standardized naming per service (Lambda, EventBridge, SQS, etc.) | CloudWatch Logs | OBS-02 |
| OBS-04 | Trace Coverage & Sampling | Mandatory paths traced; optional paths opt-in; no PII in traces | X-Ray configuration | OBS-02 |
| OBS-05 | Dashboard Redaction Enforcement | No raw userId, email, phone, SSN in aggregated metrics; hashed/opaque IDs only | CloudWatch Dashboard definitions | OBS-03 |
| OBS-06 | Metric & Alarm Ownership | All alarms assigned; ownership, action rules (Continue/Pause/Abort) documented | Alarm configuration | OBS-03 |
| OBS-07 | Evidence Contract (Artifacts) | Naming conventions, timestamps, integrity checksums for all evidence | Evidence repository | OBS-03 |
| OBS-08 | CloudTrail Immutability | Logs stored in S3 with Object Lock, MFA delete, versioning enabled | S3 + CloudTrail settings | OBS-02 |
| OBS-09 | Access Log Review (AUDIT-04) | Weekly manual review of CloudTrail logs for anomalies | Analyst task | OBS-01 |
| OBS-10 | Incident Logging (AUDIT-03) | Security incidents logged to S3 with timestamp, severity, remediation | Lambda incident logger | PROC-01 onwards |

---

## 1. Observability Scope & Boundaries (NEW)

**CRITICAL CONSTRAINT:** Observability is for operational monitoring and audit compliance ONLY. Surveillance of per-user activity is EXPLICITLY FORBIDDEN.

### 1.1 Explicitly Monitored (Allowed)

Observability WILL track:

1. **Infrastructure Health Metrics:**
   - EventBridge: events/minute, success/failure counts (aggregate, not per-user)
   - SQS: queue depth, age of oldest message, DLQ message count
   - Lambda: error rate (%), memory utilization, duration (p50, p95, p99)
   - DynamoDB: consumed read/write capacity units, throttle events
   - S3: PUTs, GETs, object count per bucket
   - API Gateway: request count, error rate (4xx, 5xx), latency (p95)
   - StepFunctions: execution count, duration, failure count
   - Bedrock: request count, latency, error rate

2. **Pipeline Correctness & Determinism:**
   - Normalization: valid events processed, duplicates rejected, schema violations logged
   - Rollups: aggregates written, feature jobs completed, expected row counts
   - Rules engine: alerts generated per rule, threshold breaches
   - Bedrock: explanations generated, latency, guardrail violations (LLM-01, LLM-02)
   - SageMaker: scoring latency, feature importance

3. **Security & Compliance Events:**
   - IAM authentication failures (API key invalid, Cognito MFA fail)
   - Unauthorized access attempts (API 403, DynamoDB policy denial)
   - Schema validation failures (malformed events, missing fields)
   - Privacy violations detected (text field in numeric aggregate, PII in explanation)
   - Incident creation (severity, category, timestamp)

4. **Audit & Forensics (Per Docs/06 AUDIT-* Controls):**
   - CloudTrail: all API calls (API Gateway, Lambda, DynamoDB, S3, Bedrock, Cognito, IAM, Secrets Manager)
   - HR Audit view: alerts, explanations, KB references (read-only, aggregated by cohort)
   - Access logs: who (Cognito user), what (resource), when (timestamp), result (allowed/denied)

### 1.2 Explicitly Forbidden (Surveillance Prohibition)

Observability WILL NOT track:

1. **Per-User Activity:**
   - Individual user signal counts or trends (in dashboards)
   - Individual explanation requests (log only in audit trail, not metrics)
   - Individual feature values (aggregates only)
   - User engagement metrics (login frequency, session duration per user)
   - User names, emails, phone numbers, SSNs, or reversible identifiers

2. **Behavioral Surveillance:**
   - Message content analysis (word frequency, sentiment per user)
   - Meeting patterns beyond aggregate signals (no "user X was in N meetings")
   - Communication graph (who talks to whom)
   - Work-from-office patterns per individual

3. **Non-Aggregate Dashboards:**
   - No per-user scatter plots or heat maps showing individual rank/position
   - No "Top 10 users" leaderboards (violates BIAS-04)
   - No comparative charts that identify individuals by appearance

4. **Inference & Derived Metrics:**
   - Predicted churn per user (not logged, not cached)
   - Inferred attributes (marital status, health condition, etc.) from signals
   - Discrimination risk scores per individual

**Rationale:** Per docs/00_project_brief.md "Explicit Out of Scope" and docs/06_security_privacy.md BIAS-04 (Human Review Gate) and LLM-01/02 (no punitive advice), SignalHR is a coaching tool, not a surveillance system. This boundary is legally and ethically binding.

### 1.3 Scope Boundary Violation Response

If observability reveals a violation:
1. **Immediate action:** Disable the metric/dashboard/log immediately
2. **Incident logging:** Log to S3 with severity=Critical (OBS-10)
3. **Change Request:** Create CR in docs/CHANGE_REQUESTS.md to recover or remove the feature
4. **Project Owner approval required** before resuming any logging of the same type

---

## 2. Metric & Alarm Ownership (NEW)

**All alarms must be owned, actionable, and mapped to a decision rule (Continue / Pause / Abort).**

### 2.1 Alarm Index (Stable IDs)

| Alarm ID | Alarm Name | Threshold | Owner | Trigger Action | Continue Condition | Pause Condition | Abort Condition |
|----------|------------|-----------|-------|-----------------|-------------------|------------------|-----------------|
| ALM-001 | DLQ-Messages | Messages > 0 | PROC-Owner | Investigate | DLQ cleared, root cause identified | More than 5 messages for >2h | Same after 3 retries |
| ALM-002 | Lambda-Error-Rate | Error% > 1% | PROC-Owner | Check logs | Error% < 0.5% and 10 min passing | Error% stays 1–5% for >15 min | Error% > 5% or Lambda unavailable |
| ALM-003 | StepFunctions-Failure | Executions failed > 0 | PROC-Owner | Check state machine | No failures in 10 min window | Failures increasing trend | >10 consecutive failures |
| ALM-004 | SQS-Depth | Queue depth > 100 | ING-Owner | Monitor | Depth returns to <50 | Depth stays 100–500 for >30 min | Depth > 1000 or age > 1h |
| ALM-005 | SQS-Age | Age of oldest message > 5 min | ING-Owner | Monitor | Age < 2 min | Age 5–15 min sustained | Age > 30 min, likely processing stall |
| ALM-006 | Lambda-Duration | p95 latency > 500ms | PROC-Owner | Monitor | p95 < 300ms | p95 300–500ms for >5 executions | p95 > 1000ms or timeout |
| ALM-007 | DynamoDB-Throttle | Throttle events > 0 | PROC-Owner | Check capacity | No throttles in 10 min | Throttles <5 per min | Throttles >10 per min, enable on-demand |
| ALM-008 | API-Error-Rate | 5xx errors > 1% | ING-Owner | Check API Gateway logs | 5xx < 0.5% | 5xx 1–3% | 5xx > 5% or API unavailable |
| ALM-009 | Bedrock-Timeout | Timeout count > 5 in 5 min | BED-Owner | Check Bedrock quota | Timeouts < 2 per 5 min | Timeouts 2–5 per 5 min | Timeouts > 10 per 5 min, invoke fallback |
| ALM-010 | Bedrock-Guardrail-Violation | LLM-01/02 violations > 0 | BED-Owner | Check prompt/KB | 0 violations in sample | 1–2 violations, review prompt | >2 violations, block explanations, CR required |

### 2.2 Alarm Decision Rules

For each alarm, the action is deterministic:

**Continue (Green):** Pipeline continues; no action required beyond passive monitoring.
- Example: ALM-001 DLQ-Messages = 0 → Continue (healthy state)

**Pause (Yellow):** Pipeline pauses after this phase completes; manual review and fix required before resuming next phase.
- Example: ALM-002 Lambda-Error-Rate = 3% for 15 min → Pause before Phase 3 rollups
- Action: Review CloudWatch logs, identify root cause (out of memory? permission issue?), fix, increment Lambda version, restart with CR

**Abort (Red):** Pipeline halts immediately; incident triggered; Change Request required to resume.
- Example: ALM-009 Bedrock-Timeout > 10 per 5 min → Abort immediately
- Action: Log incident (OBS-10), activate fallback (docs/07_demo_script.md fallback plan), file CR with Bedrock quota increase

### 2.3 Alarm Configuration & Evidence

**Task OBS-03:** Provision all alarms in CloudWatch.

- Alarm configuration: CloudWatch console or IaC (`infrastructure/cloudwatch/alarms.tf`)
- SNS topic for notifications: `signalhr-alarms-dev`
- Alarm actions: 
  - **Alarm state → ALARM:** Publish to SNS + log to CloudWatch (timestamp, severity, remediation link)
  - **Alarm state → OK:** Publish to SNS (notification) + close any open incident
- Evidence artifact: Alarm configuration JSON (all 10 alarms) + SNS topic ARN

**Storage location:** `s3://signalhr-test-reports/qa/OBS-03/alarms-config-<timestamp>.json`

---

## 3. Trace Coverage Rules (NEW)

**Tracing provides end-to-end visibility for debugging and performance analysis. Rules define mandatory vs. optional paths.**

### 3.1 Mandatory Traced Paths (Always Enabled)

These paths MUST be traced at all times (100% sampling):

1. **API Ingestion (ING-01):**
   - Path: API Gateway POST /events → EventBridge PutEvents
   - Trace segments: API Gateway (request/response), EventBridge (publish success/failure)
   - Capture: ingestionId, schemaVersion, event size, latency
   - Redaction: NO userId in X-Ray trace logs (redact before sending)

2. **Normalization (PROC-01):**
   - Path: SQS ReceiveMessage → Lambda invoke → S3 PutObject
   - Trace segments: SQS (message age), Lambda (init, execution, errors), S3 (put latency)
   - Capture: ingestionId, schemaVersion, event size, processing time, dedup status
   - Redaction: NO cohortId, NO signal counts (numeric noise only)

3. **Rollup (PROC-02):**
   - Path: Lambda (rollup orchestrator) → DynamoDB Query → Feature job → DynamoDB Write
   - Trace segments: Lambda (duration), DynamoDB (query latency, write latency), errors
   - Capture: week, aggregate count, feature job status, final row count
   - Redaction: NO individual aggregates (statistics only: min, max, avg)

4. **Bedrock Explanation (BED-01/02):**
   - Path: Lambda (prepare features) → Bedrock InvokeAgent → Post-response scanner → Return
   - Trace segments: Feature prep, Bedrock latency, guardrail check, PII/hallucination detection, final output
   - Capture: request ID, latency, guardrail violations, scanner findings, response length
   - Redaction: NO user features, NO explanation text (summary only: length, safety score)

### 3.2 Optional Traced Paths (Sampling-Based)

These paths are traced at 10% sampling rate (configurable):

1. **Individual Signal Validation (PROC-01):**
   - Path: EventBridge Pipes → Lambda field validation → Error decision
   - Sampling: 10% of events
   - Rationale: Expensive to trace every field check; sample for anomaly detection

2. **Feature Job Execution (FEAT-*):**
   - Path: Lambda (batch) → SageMaker notebook execution → S3 artifact write
   - Sampling: 10% of job runs
   - Rationale: Feature jobs can be long-running; sampling reduces overhead

3. **UI Database Queries (UI-01/02):**
   - Path: Cognito auth → API Gateway → Lambda query → DynamoDB GetItem
   - Sampling: 10% of authenticated requests
   - Rationale: High volume; sample for latency/error patterns

### 3.3 Explicitly Excluded from Tracing (Privacy Hard Stops)

These are FORBIDDEN from any trace:

1. **Raw Signal Content:** No message text, keystroke patterns, screenshot descriptions
2. **Individual User Data:** No per-user feature values, no per-user signal counts
3. **Explanation Text:** No Bedrock response body (summary only)
4. **Personal Identifiers:** No email, phone, SSN, name (opaque userId only)
5. **Cohort Disaggregation:** No trace showing "cohort A has X signal, cohort B has Y" (aggregates only)

**Enforcement:** X-Ray integration in Lambda MUST:
- Redact ingestion events before sending to X-Ray (remove userId)
- Skip tracing explanation text (capture only metadata: latency, safety score)
- Use opaque trace IDs (not user IDs)

---

## 4. Evidence Contract (NEW)

**All observability evidence must follow a strict naming, storage, and integrity contract for reproducibility and audit.**

### 4.1 Evidence Artifact Types & Naming Conventions

| Artifact Type | Example Filename | Storage Location | Retention | Integrity |
|---------------|------------------|------------------|-----------|-----------|
| CloudWatch Dashboard | `dashboard-ingest-overview-<timestamp>.html` | `s3://signalhr-test-reports/qa/OBS-03/dashboards/` | 1 year | SHA256 checksum |
| CloudWatch Logs Export | `logs-lambda-normalize-<date>-<time>.json` | `s3://signalhr-test-reports/qa/<task>/logs/` | 90 days | SHA256 + line count |
| X-Ray Trace JSON | `xray-trace-<trace-id>-<timestamp>.json` | `s3://signalhr-test-reports/qa/OBS-04/traces/` | 30 days | SHA256 checksum |
| CloudTrail Events | `cloudtrail-<date>-<event-count>.json` | `s3://signalhr-audit-trail/` | 7 years | S3 Object Lock, versioning |
| Alarm Screenshot | `alarm-<alarm-id>-<timestamp>.png` | `s3://signalhr-test-reports/qa/OBS-03/alarms/` | 1 year | SHA256 checksum |
| Metric Query Result | `metric-<query-name>-<date>.csv` | `s3://signalhr-test-reports/qa/OBS-03/metrics/` | 90 days | SHA256 checksum |
| Incident Report | `incident-<severity>-<id>-<timestamp>.json` | `s3://signalhr-audit-trail/incidents/` | 7 years | Immutable (Object Lock) |
| HR Audit View Export | `audit-view-<date>-<cohort-count>.csv` | `s3://signalhr-test-reports/qa/AUDIT-02/` | 2 years | SHA256 checksum |

### 4.2 Timestamp & Alignment Rules

1. **All Evidence Must Include Timestamp:**
   - Format: ISO 8601 UTC (`2026-02-07T14:30:00Z`)
   - Location: Filename suffix (`-<timestamp>`) AND file metadata (S3 object creation date)

2. **Alignment Rules (For Linking Evidence):**
   - Dashboard screenshot + trace ID must be from same 5-minute window
   - Example: ALM-002 alarm triggered at 14:30:05Z → collect dashboard screenshot, X-Ray trace, CloudWatch logs all from window 14:25:00–14:35:00Z
   - Timestamp mismatch >5 min requires explanation in evidence manifest

3. **Checksum Computation:**
   - Algorithm: SHA256
   - Input: File contents (uncompressed)
   - Output: Hex string, stored as metadata in S3 object tags (`checksum=<hex>`)
   - Validation: `sha256sum <file> | awk '{print $1}'` must match S3 tag

### 4.3 Storage Location & Retention Policy

**Primary Evidence Repository:** `s3://signalhr-test-reports/` (KMS encrypted, versioning enabled)

| Path | Retention | Access | Lifecycle |
|------|-----------|--------|-----------|
| `qa/OBS-03/dashboards/` | 1 year | QA team | Delete after 1 year |
| `qa/OBS-03/alarms/` | 1 year | QA team | Delete after 1 year |
| `qa/OBS-03/metrics/` | 90 days | QA team | Delete after 90 days |
| `qa/OBS-04/traces/` | 30 days | DevOps team | Delete after 30 days |
| `qa/<task>/logs/` | 90 days | Task owner | Delete after 90 days |
| `audit-trail/` | 7 years | HR + Audit team | Immutable (Object Lock) |
| `audit-trail/incidents/` | 7 years | Compliance team | Immutable (Object Lock) |

**Secondary Repository (Audit Trail):** `s3://signalhr-audit-trail/` (S3 Object Lock enabled, MFA delete)
- CloudTrail logs
- Incident reports
- HR audit exports

---

## 5. Backlog Traceability (NEW)

**All observability components map to specific backlog tasks for completeness and ownership.**

| Dashboard / Alarm / Metric | Dashboard Name | Backlog Task | Owner | Evidence Artifact |
|---------------------------|----------------|-------------|-------|-------------------|
| **Ingest Overview Dashboard** | `ingest-overview-dev` | ING-01, ING-02, ING-03 | ING-Owner | `dashboard-ingest-overview-<timestamp>.html` |
| - EventBridge events/min | (metric in dashboard) | ING-02 | ING-Owner | Metric query result |
| - SQS queue depth | (metric in dashboard) | ING-03 | ING-Owner | Metric query result |
| - API Gateway 5xx errors | (metric in dashboard) | ING-01 | ING-Owner | Metric query result |
| **Processing & Rollup Dashboard** | `processing-rollup-dev` | PROC-01, PROC-02, PROC-03 | PROC-Owner | `dashboard-processing-<timestamp>.html` |
| - Lambda normalization errors | (metric in dashboard) | PROC-01 | PROC-Owner | Metric query result |
| - StepFunctions execution duration | (metric in dashboard) | PROC-02 | PROC-Owner | Metric query result |
| - DynamoDB write capacity used | (metric in dashboard) | PROC-03 | PROC-Owner | Metric query result |
| **Feature & ML Dashboard** | `feature-ml-dev` | FEAT-01, FEAT-02, INT-01 | ML-Owner | `dashboard-feature-ml-<timestamp>.html` |
| - Feature job duration | (metric in dashboard) | FEAT-01, FEAT-02 | ML-Owner | Metric query result |
| - Rules engine alerts generated | (metric in dashboard) | INT-01 | ML-Owner | Metric query result |
| - SageMaker scoring latency | (metric in dashboard) | INT-01 | ML-Owner | Metric query result |
| **Bedrock & Safety Dashboard** | `bedrock-safety-dev` | BED-01, BED-02, PRIV-06 | BED-Owner | `dashboard-bedrock-<timestamp>.html` |
| - Bedrock request latency | (metric in dashboard) | BED-01 | BED-Owner | Metric query result |
| - Guardrail violations (LLM-01/02) | (metric in dashboard) | BED-01 | BED-Owner | Metric query result |
| - PII/hallucination detections | (metric in dashboard) | BED-02 | BED-Owner | Metric query result |
| **UI & Auth Dashboard** | `ui-auth-dev` | UI-01, UI-02 | UI-Owner | `dashboard-ui-auth-<timestamp>.html` |
| - API Gateway request rate | (metric in dashboard) | UI-01 | UI-Owner | Metric query result |
| - Cognito authentication errors | (metric in dashboard) | UI-02 | UI-Owner | Metric query result |
| - DynamoDB query latency (p95) | (metric in dashboard) | UI-01, UI-02 | UI-Owner | Metric query result |
| **ALM-001: DLQ-Messages Alarm** | DLQ depth > 0 | PROC-01 (Lambda), ING-03 (SQS) | PROC-Owner | `alarm-ALM-001-<timestamp>.png` |
| **ALM-002: Lambda-Error-Rate Alarm** | Lambda error% > 1% | PROC-01, PROC-02, FEAT-*, BED-* | PROC-Owner | `alarm-ALM-002-<timestamp>.png` |
| **ALM-003: StepFunctions-Failure Alarm** | SF executions failed > 0 | PROC-02 | PROC-Owner | `alarm-ALM-003-<timestamp>.png` |
| **ALM-004/005: SQS-Depth/Age Alarms** | SQS depth > 100 OR age > 5 min | ING-03 | ING-Owner | `alarm-ALM-004-<timestamp>.png`, `alarm-ALM-005-<timestamp>.png` |
| **ALM-006: Lambda-Duration Alarm** | Lambda p95 > 500ms | PROC-01, PROC-02 | PROC-Owner | `alarm-ALM-006-<timestamp>.png` |
| **ALM-007: DynamoDB-Throttle Alarm** | Throttle events > 0 | PROC-03 | PROC-Owner | `alarm-ALM-007-<timestamp>.png` |
| **ALM-008: API-Error-Rate Alarm** | API 5xx > 1% | ING-01 | ING-Owner | `alarm-ALM-008-<timestamp>.png` |
| **ALM-009: Bedrock-Timeout Alarm** | Timeout count > 5 in 5 min | BED-01 | BED-Owner | `alarm-ALM-009-<timestamp>.png` |
| **ALM-010: Bedrock-Guardrail Alarm** | Guardrail violations > 0 | BED-01 | BED-Owner | `alarm-ALM-010-<timestamp>.png` |
| **X-Ray End-to-End Trace** | API → EventBridge → Lambda → DynamoDB | ING-01, PROC-01, PROC-02 | DevOps | `xray-trace-<trace-id>-<timestamp>.json` |
| **CloudTrail Audit Trail** | All API calls | OBS-01 (Enable), OBS-02 (KMS/S3) | Compliance | `s3://signalhr-audit-trail/` |
| **HR Audit View** | Read-only dashboard for HR role | UI-02 (RBAC), AUDIT-02 | UI-Owner | `audit-view-<date>-<timestamp>.csv` |

---

## 6. Observability Freeze Rule (Pre-Demo) (NEW)

**After QA-Pass (docs/05_qa_strategy.md), no observability changes allowed without Change Request.**

### 6.1 Freeze Scope

The following are LOCKED after QA-Pass:
1. **Dashboards:** No new dashboards, no metric changes, no layout changes
2. **Alarms:** No new alarms, no threshold changes, no action rule changes
3. **Traces:** No new trace paths, no sampling rate changes
4. **Log Groups:** No new log groups, no retention changes
5. **Redaction Rules:** No relaxation of PII redaction (only tightening allowed)
6. **CloudTrail:** No disabling or reconfiguration

### 6.2 Freeze Exceptions (CR Required)

Changes allowed ONLY via Change Request (CR) in docs/CHANGE_REQUESTS.md:

1. **Bug Fix:** Alarm threshold too tight (causing false positives) → CR for threshold adjustment
2. **Performance Tuning:** Sampling rate causing lag → CR for rate increase
3. **New Incident Type:** Unforeseen failure mode discovered → CR to add alarm
4. **Regulatory Requirement:** Compliance mandate to retain logs longer → CR to extend retention

All CRs must be approved by Project Owner before implementation.

### 6.3 Freeze Enforcement

- **Timeline:** QA-Pass timestamp recorded in docs/05_qa_strategy.md → freeze begins immediately
- **Lock method:** 
  1. Documentation lock: Section "Observability Freeze Active From: <timestamp>" added to this file
  2. Infrastructure lock: All IaC (CloudFormation/Terraform) pinned to commit hash (no `terraform apply` without CR)
  3. Runbook lock: docs/04_runbook.md Phase 3–5 forbid "terraform apply" or "aws cloudwatch put-metric-alarm" without CR approval
- **Unlock method:** Change Request approved → new commit created with CR ID in message → deployment proceeds

---

## 7. Redaction Rules (Expanded) (NEW)

**Redaction is a hard boundary. All PII must be removed before data enters observability systems.**

### 7.1 PII Definition (Binding)

**Personal Identifiable Information (PII)** is any data that can identify an individual or be linked to identify an individual. In SignalHR, PII includes:

| PII Category | Examples | Forbidden In |
|--------------|----------|-------------|
| **Direct Identifiers** | Name, email, phone, SSN, employee ID | Logs, dashboards, traces, metrics |
| **Quasi-Identifiers** | Role, department, team, seniority, location | Logs, metrics (unless aggregated by cohort) |
| **Message Content** | Email body, chat text, meeting notes | All logs, S3 objects (PRIV-01) |
| **Behavioral Patterns** | "User X was in N meetings", "User Y sent K messages" | Metrics, dashboards, X-Ray (per-user view) |
| **Signal Counts** | "alice-uuid had 20 meetings" (individual aggregate) | Dashboards (must aggregate across cohort) |
| **Inferred Data** | Predicted churn, inferred health status, assumed marital status | All logs, metrics, dashboards |
| **Technical IDs Linked to Identity** | IP address, MAC address (if reversible to user) | Logs (unless hashed or salted) |

### 7.2 Allowed Identifiers (Non-PII)

The following identifiers are ALLOWED in observability systems:

1. **Opaque UUID (userId):**
   - Format: UUID v4 (e.g., `550e8400-e29b-41d4-a716-446655440000`)
   - Requirement: Non-reversible to email/phone/name
   - Use case: Event deduplication (ingestionId), tracing, incident reports
   - Constraint: ONLY in operational logs and incident reports; NOT in dashboards/metrics

2. **Hashed Cohort ID:**
   - Format: `cohort_<hash>` (e.g., `cohort_a1b2c3d4`)
   - Computation: `SHA256(role + seniority + team) % 1000`
   - Property: Multiple individuals map to same cohort; not reversible
   - Use case: Grouping metrics and dashboards by cohort (allowed)
   - Constraint: Never disaggregate below cohort level

3. **Opaque Trace ID:**
   - Format: 32-character hex string (X-Ray trace ID format)
   - Requirement: Not linked to user ID or cohort
   - Use case: Linking log entries, X-Ray traces, incident reports
   - Constraint: Log only; never exposed in dashboards

4. **Aggregate Statistics:**
   - Format: Counts, sums, averages (no individual values)
   - Examples: "10,000 events ingested", "99th percentile latency = 500ms", "Cohort A avg signal count = 15"
   - Use case: Metrics, dashboards, SLA reports
   - Constraint: No breakdown to individual level

### 7.3 Redaction Rules (Technical Implementation)

#### Rule R1: API Ingestion & EventBridge
- **Input:** Event from API Gateway (ingestionId, userId, schemaVersion, signalCounts, timestamp)
- **Action:** EventBridge Pipes transformer must:
  1. Pass userId through (opaque UUID, acceptable for event dedup)
  2. Drop any optional text fields (message body, description)
  3. Forward to SQS with redacted payload
- **Output:** SQS message contains only (ingestionId, schemaVersion, signalCounts, timestamp) — NO userId in SQS message body

#### Rule R2: Lambda Normalization (PROC-01)
- **Input:** SQS message (processed event)
- **Action:** Lambda must:
  1. Confirm userId absent from SQS body (or if present, remove before writing S3)
  2. Compute cohortId from context metadata (not individual properties)
  3. Write to S3 raw bucket: only (signalCounts, timestamp, schemaVersion, cohortId)
  4. Write to CloudWatch logs: ingestionId, schemaVersion, status — NO userId
- **Output:** S3 object and logs contain NO user-identifiable data

#### Rule R3: DynamoDB Aggregates (PROC-03)
- **Input:** Normalized events (cohortId, signalCounts, week)
- **Action:** Rollup Lambda must:
  1. Group by cohortId only (never by role, seniority, team individually)
  2. Compute per-cohort aggregates (sum, avg, stddev)
  3. PK = `COHORT#<cohort_id>#WEEK#<year>-WW`
  4. Write to DynamoDB: (cohortId, week, aggregate counts, feature values)
  5. Log to CloudWatch: cohortId, week, row count — NO individual users
- **Output:** DynamoDB table contains NO user names, emails, or individual records

#### Rule R4: Dashboards & Metrics (OBS-03)
- **Input:** Aggregated metrics from CloudWatch, DynamoDB
- **Action:** Dashboard must:
  1. Display only cohort-level aggregates (e.g., "Cohort A avg signal count", "Cohort B 95th percentile latency")
  2. NO scatter plots showing individual data points
  3. NO heat maps with user names or IDs on axes
  4. NO "Top 10" or "Bottom 10" lists (BIAS-04 violation)
  5. Alarms trigger on cohort-level thresholds, not individual thresholds
- **Output:** CloudWatch dashboard exposes NO individual users; cohort aggregates only

#### Rule R5: X-Ray Traces (OBS-04)
- **Input:** Operational traces (event flow through system)
- **Action:** Lambda instrumentation must:
  1. Redact userId before sending trace to X-Ray: `trace_userId = "REDACTED"`
  2. Include only opaque trace ID, timestamps, latencies, errors
  3. Skip tracing of signal counts or feature values
- **Output:** X-Ray logs contain NO signal values, NO user IDs; operational metadata only

#### Rule R6: Bedrock Explanations (BED-02 + PRIV-06)
- **Input:** Features for Bedrock (signal counts, trend, cohort stats)
- **Action:** Lambda must:
  1. Prepare feature JSON WITHOUT individual user ID
  2. Include only cohort-level context (e.g., "This user's signal count 1.5 sigma above cohort baseline")
  3. Invoke Bedrock Agent
  4. Post-response PII scanner: reject response if contains (name, email, phone, SSN, department, role)
  5. Hallucination detector: reject if response claims facts not supported by KB or input features
- **Output:** Explanation contains NO individual user PII, NO hallucinations; only coached advice

#### Rule R7: CloudTrail Logs (AUDIT-01)
- **Input:** All AWS API calls
- **Action:** CloudTrail must:
  1. Log all API calls to S3 (immutable, Object Lock enabled)
  2. Include: caller principal (IAM role, not user), resource, action, timestamp, result
  3. Store in `s3://signalhr-audit-trail/`
- **Output:** Audit trail contains NO message content, NO user signals; API calls only

#### Rule R8: Incident Reports (OBS-10, AUDIT-03)
- **Input:** Incident detected (privacy breach, guardrail violation, unexpected output)
- **Action:** Incident logger must:
  1. Log to S3 (immutable, Object Lock enabled)
  2. Include: severity, incident type, timestamp, remediation, evidence (trace ID, error message)
  3. If PII exposed, log "PII of type <category> was exposed" (do NOT include the PII itself)
  4. Reference trace ID or log entry ID (not user ID or email)
- **Output:** Incident report in `s3://signalhr-audit-trail/incidents/`; contains evidence pointers but NOT the exposed data

### 7.4 Redaction Verification (Testing)

**Task OBS-04:** Test all redaction rules.

1. **Automated Scan (Lambda function):**
   - Name: `redaction-validator`
   - Input: Sample from each log stream, dashboard, S3 bucket
   - Regex patterns: Email (`\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b`), Phone (`\b\d{3}-\d{3}-\d{4}\b`), SSN (`\b\d{3}-\d{2}-\d{4}\b`), Name patterns
   - Output: CSV report with matched lines (if any) and severity (Critical if PII found)
   - Remediation: If PII detected, trigger incident (OBS-10), disable log/dashboard, file CR

2. **Manual Spot Check:**
   - Weekly (every Friday): Random 100-line sample from CloudWatch logs, X-Ray traces, dashboards
   - Check: No individual userId, no cohort disaggregation, no per-user metrics
   - Evidence: Manual audit report in `s3://signalhr-test-reports/qa/OBS-04/manual-audits/`

3. **Test Case (QA):**
   - Create event with PII payload (email, phone, name)
   - Run through pipeline
   - Verify: S3 output contains NO PII
   - Verify: CloudWatch logs contain NO PII
   - Verify: X-Ray trace contains NO PII
   - Evidence: Test report in `s3://signalhr-test-reports/qa/OBS-04/redaction-tests/`

---

## 8. Log Groups & Naming Conventions (ORIGINAL + HARDENED)

**All log groups follow standardized naming. Maps to OBS-03 control.**

| Service | Log Group Name | Retention | Encryption | Task |
|---------|---|-----------|----------|------|
| Lambda (Normalization) | `/aws/lambda/signalhr-normalize-dev` | 90 days | KMS | PROC-01, OBS-02 |
| Lambda (Rollup) | `/aws/lambda/signalhr-rollup-dev` | 90 days | KMS | PROC-02, OBS-02 |
| Lambda (Features) | `/aws/lambda/signalhr-features-dev` | 90 days | KMS | FEAT-01, FEAT-02, OBS-02 |
| Lambda (Rules Engine) | `/aws/lambda/signalhr-rules-dev` | 90 days | KMS | INT-01, OBS-02 |
| Lambda (Bedrock) | `/aws/lambda/signalhr-bedrock-dev` | 90 days | KMS | BED-01, BED-02, OBS-02 |
| Lambda (API/Ingestion) | `/aws/lambda/signalhr-api-dev` | 90 days | KMS | ING-01, OBS-02 |
| StepFunctions | `/aws/vendedlogs/states/signalhr-rollup-sfn-dev` | 90 days | KMS | PROC-02, OBS-02 |
| API Gateway | `/aws/apigateway/signalhr-api-dev` | 90 days | KMS | ING-01, OBS-02 |
| EventBridge | `/aws/events/signalhr-bus-dev` | 30 days | KMS | ING-02, OBS-02 |
| SQS | CloudWatch metrics (no logs by default) | N/A | N/A | ING-03, OBS-02 |
| DynamoDB | CloudWatch metrics (no logs by default) | N/A | N/A | PROC-03, OBS-02 |

---

## 9. Dashboards (CloudWatch) — Refined Metrics

**All dashboards must redact PII. Maps to OBS-05 control.**

### 9.1 Ingest Overview Dashboard
- **Name:** `ingest-overview-dev`
- **Metrics:**
  - EventBridge: `Events published (count/min)` — aggregate, not per-source
  - SQS: `Queue depth`, `Age of oldest message`, `Messages received (count/min)`
  - API Gateway: `Request count`, `4xx errors`, `5xx errors`, `Latency (p95)`
- **Alarms:** ALM-001 (DLQ), ALM-004 (SQS depth), ALM-005 (SQS age), ALM-008 (API 5xx)
- **Redaction:** NO userId, NO ingestionId breakdown
- **Traceability:** ING-01, ING-02, ING-03

### 9.2 Processing & Rollup Dashboard
- **Name:** `processing-rollup-dev`
- **Metrics:**
  - Lambda normalization: `Invocations (count)`, `Duration (p50, p95)`, `Errors (count)`, `Throttles`
  - Lambda rollup: `Executions (count)`, `Duration (p95)`, `Errors`
  - StepFunctions: `Executions (count)`, `Duration (p95)`, `Failures (count)`
  - DynamoDB: `Consumed RCU/WCU`, `Throttle events`, `Latency (p95)`
  - S3: `PUT count`, `PUT latency (p95)`
- **Alarms:** ALM-002 (Lambda error), ALM-003 (SF failure), ALM-006 (Lambda duration), ALM-007 (DDB throttle)
- **Redaction:** NO event contents, NO individual aggregates
- **Traceability:** PROC-01, PROC-02, PROC-03

### 9.3 Feature & ML Dashboard
- **Name:** `feature-ml-dev`
- **Metrics:**
  - Feature jobs: `Duration (p95)`, `Success/failure count`, `Rows processed`
  - Rules engine: `Alerts generated (count)`, `Alerts by rule (stacked bar, per-rule counts only)`
  - SageMaker: `Scoring invocations (count)`, `Latency (p95)`, `Prediction counts`
- **Cohort Breakdown:** Allowed (show "Cohort A: 5 alerts", "Cohort B: 3 alerts") — aggregate only, NOT disaggregated to individuals
- **Alarms:** ALM-002 (Lambda error)
- **Redaction:** NO individual alert records, NO per-user scoring
- **Traceability:** FEAT-01, FEAT-02, INT-01

### 9.4 Bedrock & Safety Dashboard
- **Name:** `bedrock-safety-dev`
- **Metrics:**
  - Bedrock: `Requests (count)`, `Latency (p95)`, `Errors (count)`
  - Safety checks: `Guardrail violations (LLM-01, LLM-02)`, `PII detections`, `Hallucinations detected`, `Safe explanations (count)`
  - Prompt effectiveness: Success rate (%) — "X% of requests returned safe explanations"
- **Alarms:** ALM-009 (Bedrock timeout), ALM-010 (Guardrail violation)
- **Redaction:** NO explanation text, NO user features, NO individual requests
- **Traceability:** BED-01, BED-02

### 9.5 UI & Auth Dashboard
- **Name:** `ui-auth-dev`
- **Metrics:**
  - API Gateway: `Requests (count)`, `Latency (p95)`, `401/403 errors`
  - Cognito: `Authentication successes`, `MFA failures`, `Token refresh count`
  - DynamoDB queries: `GetItem latency (p95)`, `Query latency (p95)`, `Throttle events`
  - S3 (UI assets): `GET count`, `GET latency (p95)`
- **Alarms:** ALM-008 (API error rate)
- **Redaction:** NO user IDs, NO session tokens, NO query filters (e.g., show total queries, not "user X queried")
- **Traceability:** UI-01, UI-02

---

## 10. Alarms — Complete Specification

See Section 2 (Metric & Alarm Ownership) for all 10 alarms (ALM-001 through ALM-010).

**Key principle:** Each alarm has an owner, a decision rule (Continue/Pause/Abort), and a remediation action.

---

## 11. Trace & Sampling (ORIGINAL + HARDENED)

**X-Ray tracing for end-to-end visibility. Sampling reduces overhead.**

### 11.1 Mandatory Traced Paths (100% Sampling)

See Section 3.1. These are always traced:
1. API Ingestion
2. Normalization
3. Rollup
4. Bedrock Explanation

### 11.2 Optional Traced Paths (10% Sampling)

See Section 3.2:
1. Signal Validation
2. Feature Job Execution
3. UI Database Queries

### 11.3 Excluded Paths

See Section 3.3. These are NEVER traced:
1. Raw signal content
2. Individual user data
3. Explanation text
4. Personal identifiers
5. Cohort disaggregation

---

## 12. Audit Trails (ORIGINAL + HARDENED)

**CloudTrail provides immutable audit log of all API activity. Maps to AUDIT-01, AUDIT-03, AUDIT-04.**

### 12.1 CloudTrail Configuration (OBS-02, AUDIT-01)

- **Trail Name:** `signalhr-trail-dev`
- **Scope:** Multi-region (all regions), all API calls (management + data events)
- **S3 Bucket:** `s3://signalhr-audit-trail/`
- **Bucket Encryption:** KMS (customer-managed key)
- **Immutability:** S3 Object Lock enabled (WORM mode)
- **MFA Delete:** Enabled (prevents accidental deletion)
- **Versioning:** Enabled (track all changes to audit logs)
- **Retention:** 7 years (per compliance requirements)

### 12.2 CloudTrail Events Captured

- **API Calls:** All calls to API Gateway, EventBridge, SQS, Lambda, DynamoDB, S3, Bedrock, Cognito, IAM, Secrets Manager, KMS, CloudTrail, CloudWatch
- **Metadata:** Principal (IAM role), action, resource, timestamp, result (success/denial), error code
- **NOT Captured:** Request/response payloads (encrypted at rest, not logged)

### 12.3 Manual Log Review (OBS-01, AUDIT-04)

**Frequency:** Weekly (every Friday EOD)

**Analyst task:**
1. Query CloudTrail for past 7 days
2. Filter for anomalies:
   - Denied API calls (401, 403)
   - Privilege escalation attempts (AssumeRole, AttachUserPolicy)
   - Data deletions (DeleteItem, DeleteTable, DeleteBucket)
   - Unusual access patterns (access outside business hours, from unexpected regions)
3. Generate report: Anomalies found (if any), remediation actions, signed off
4. Store report: `s3://signalhr-audit-trail/weekly-reviews/`

**Evidence artifact:** `cloudtrail-review-<date>.md` with findings and sign-off

---

## 13. HR Audit View (AUDIT-02, UI-02)

**Read-only dashboard for HR role. Enables compliance auditing without PII exposure.**

### 13.1 HR Audit View Scope

HR role can see:
1. **Alerts:** Count of alerts per cohort, per rule, per week (aggregate only)
2. **Explanations:** Sanitized summaries (e.g., "3 burnout-related explanations in Cohort A", "1 HiPo growth opportunity in Cohort B")
3. **KB References:** Which knowledge base documents were cited in explanations (e.g., "Time management" cited in 5 explanations)
4. **Audit Trail:** Who (Cognito user), when (timestamp), what action (viewed alert, generated explanation)

HR role CANNOT see:
1. Individual user names, emails, signal counts
2. Full explanation text
3. Individual alert records
4. Employee portal data (signals, opt-in settings)

### 13.2 HR Audit View Export Format

- **Filename:** `audit-view-<date>-<timestamp>.csv`
- **Columns:** (report_date, cohort_id, rule_name, alert_count, explanation_count, kb_references, audit_action, audit_timestamp)
- **Example row:** `2026-02-07, cohort_a1b2c3d4, burnout_rule, 5, 3, ["time_management", "delegation"], viewed_alert, 2026-02-07T14:30:00Z`
- **Storage:** `s3://signalhr-test-reports/qa/AUDIT-02/`
- **Retention:** 2 years
- **Redaction:** All PII removed; cohort ID hashed; no reversal possible

---

## 14. Evidence for Verification (ORIGINAL + HARDENED)

All observability evidence follows the Evidence Contract (Section 4).

**Required evidence for major operations:**

### 14.1 After Phase 0 (Environment Validation, docs/04_runbook.md)
- CloudWatch log groups exist: Screenshots of all 10 log groups created
- CloudTrail enabled: `aws cloudtrail describe-trails --trail-name signalhr-trail-dev` output
- Dashboards exist: Screenshots of all 5 dashboards
- Alarms exist: `aws cloudwatch describe-alarms` output showing 10 alarms in OK state
- X-Ray enabled: Sample trace showing end-to-end flow

### 14.2 During Phase 1 (Ingestion, docs/04_runbook.md)
- API event successfully logged: CloudWatch logs snippet showing "202 Accepted"
- EventBridge received event: `aws events list-rules --event-bus-name signalhr-bus-dev` + sample PutEvents metric
- SQS received message: `aws sqs receive-message --queue-url <url>` output (redacted)
- CloudTrail captured API call: CloudTrail event JSON showing PutEvents action

### 14.3 During Phase 2 (Normalization, docs/04_runbook.md)
- Lambda invoked: CloudWatch logs showing successful invocations
- S3 raw object written: `aws s3 ls s3://signalhr-raw-events-dev/` output
- DynamoDB deduplicated: CloudWatch logs showing "Duplicate rejected, ingestionId=<id>"
- X-Ray trace: Sample trace showing Lambda → DynamoDB latency

### 14.4 During Phase 3 (Rollup, docs/04_runbook.md)
- StepFunctions execution: Execution history showing all states passed
- DynamoDB aggregates: `aws dynamodb scan --table-name AggregatesTable-dev --limit 3` output (redacted)
- S3 Parquet snapshot: `aws s3 ls s3://signalhr-aggregates-dev/` output
- CloudWatch metrics: Dashboard screenshot showing aggregate counts

### 14.5 During Phase 4 (Scoring, docs/04_runbook.md)
- Rules engine fired: CloudWatch logs showing "5 alerts generated"
- Bedrock invoked: CloudWatch logs showing Bedrock request/response latency
- Safety checks passed: Logs showing "0 guardrail violations", "0 PII detected", "0 hallucinations"
- X-Ray trace: End-to-end trace from input features to Bedrock response (redacted)

### 14.6 During Phase 5 (Demo, docs/07_demo_script.md)
- Dashboard visible: Screenshots of Ingest, Processing, Feature, Bedrock, UI dashboards
- Alarms nominal: All 10 alarms in OK state
- HR Audit View accessible: Screenshot of HR audit export CSV
- Audit trail clean: No unexpected API calls, no denied access

---

## 15. Runbook Pointers (ORIGINAL + REFINED)

**Cross-references to docs/04_runbook.md Failure Handling Playbook.**

### 15.1 When ALM-001 (DLQ) Triggers

- **Runbook section:** docs/04_runbook.md → Failure Handling Playbook → "DLQ Messages > 0"
- **Action:** Check Pipes transformer logs; identify rejected events; fix transformation; reprocess DLQ
- **Evidence:** CloudWatch logs + reprocessed message count

### 15.2 When ALM-002 (Lambda Error Rate) Triggers

- **Runbook section:** docs/04_runbook.md → Failure Handling Playbook → "Lambda Error Rate > 1%"
- **Action:** Check CloudWatch logs for error message; investigate root cause (out of memory? permission?); increase Lambda memory or timeout; increment version; restart phase
- **Evidence:** CloudWatch logs + error root cause + remediation

### 15.3 When ALM-003 (StepFunctions Failure) Triggers

- **Runbook section:** docs/04_runbook.md → Failure Handling Playbook → "StepFunctions Failure"
- **Action:** Check StepFunctions execution history; identify failed state; review DynamoDB write permissions; retry with updated role if needed
- **Evidence:** Execution history JSON + remediation proof

### 15.4 When ALM-009 (Bedrock Timeout) Triggers

- **Runbook section:** docs/04_runbook.md → Failure Handling Playbook → "Bedrock Unavailable"
- **Action:** Check Bedrock quota; if quota exceeded, activate demo fallback (pre-recorded screenshots + templated explanation); file CR for quota increase
- **Evidence:** Bedrock API error message + fallback activation log

---

## 16. Observability Tasks (NEW)

Observability implementation is split into 4 backlog tasks:

### OBS-01: Audit Trail Setup & Review Workflow
- **Deliverable:** CloudTrail enabled, weekly audit log review process documented
- **Evidence:** CloudTrail trail created, first weekly review report completed

### OBS-02: Encryption, Secrets, Log Groups, CloudWatch
- **Deliverable:** KMS key provisioned; all log groups created with encryption and retention; CloudTrail logs encrypted
- **Evidence:** Log group list, KMS key ARN, CloudTrail configuration

### OBS-03: Dashboards & Alarms
- **Deliverable:** 5 dashboards created; 10 alarms configured with ownership and decision rules
- **Evidence:** Dashboard screenshots, alarm configuration JSON, ownership documentation

### OBS-04: Trace Configuration & Redaction Testing
- **Deliverable:** X-Ray enabled for mandatory paths; redaction validation test suite passing
- **Evidence:** Sample X-Ray trace, redaction test report (0 PII found)

All tasks must have completion evidence in `s3://signalhr-test-reports/qa/OBS-<number>/`

---

## 17. Summary: What Is Monitored vs. What Is Forbidden

| Category | Monitored (Allowed) | Forbidden (Surveillance) |
|----------|-------------------|--------------------------|
| **Infrastructure** | Event rates, queue depth, error counts (aggregate) | N/A |
| **Pipeline Health** | Latencies, throughput, failure counts | Individual event details |
| **User Activity** | Aggregate signal counts by cohort | Per-user signal counts, activity streams |
| **Alerts** | Count of alerts by rule and cohort | Individual alert records, user names |
| **Explanations** | Count generated, safety score, latency | Explanation text, reasoning chains |
| **Bedrock** | Request count, latency, guardrail violations | Prompt/response content, user features |
| **Audit** | Who, what, when, result (API calls) | PII of users involved in API calls |
| **Security Events** | Incident count, severity, category, remediation | Exposed PII itself (only references) |

---

## 18. Alignment with Security Controls

This observability specification enforces all applicable controls from docs/06_security_privacy.md:

| Security Control | Enforced By (This Doc) |
|------------------|----------------------|
| SEC-04 (CloudTrail) | Section 12 (Audit Trails), OBS-02 |
| PRIV-02 (No PII in Aggregates) | Section 7 (Redaction Rules), OBS-04 |
| PRIV-04 (Data Retention) | Section 4.3 (Storage & Retention), OBS-02 |
| PRIV-06 (No PII in Explanations) | Section 7.3 Rule R6 (Bedrock), OBS-04 |
| PRIV-07 (Data Isolation) | Section 13 (HR Audit View), UI-02 |
| AUDIT-01 (CloudTrail) | Section 12, OBS-02 |
| AUDIT-02 (HR Audit View) | Section 13, OBS-03 |
| AUDIT-03 (Incident Logging) | Section 7.3 Rule R8, OBS-10 |
| AUDIT-04 (Access Log Review) | Section 12.3, OBS-01 |

---

## 19. Observability Freeze State (Post-QA)

**Populated after QA-Pass (docs/05_qa_strategy.md). When freeze becomes active:**

```
Observability Freeze Active From: [QA-Pass Timestamp → TBD]
All dashboards, alarms, log configurations locked.
Changes require Change Request approval by Project Owner.
```

Currently: **NOT FROZEN** (QA not passed yet)

---

**Document Version:** 1.0 (Hardened)  
**Last Updated:** 2026-02-07  
**Status:** Ready for OBS-01–OBS-04 Implementation  
**Next Step:** Implement OBS-02 (Infrastructure), OBS-03 (Dashboards), OBS-04 (Tracing & Redaction Testing)
