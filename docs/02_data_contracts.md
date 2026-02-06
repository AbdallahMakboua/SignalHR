# Data Contracts — SignalHR

This document defines ingestion event schemas, DynamoDB schemas, S3 partitioning, feature schemas, and operational contracts. All schema changes require a Change Request in `docs/CHANGE_REQUESTS.md` and must increment `schemaVersion`.

## Contract Index (stable IDs) (NEW)
- `DC-ING-V1` — Ingestion Event Schema v1
- `DC-DDB-AGG-V1` — DynamoDB AggregatesTable Schema v1
- `DC-DDB-ALERT-V1` — DynamoDB AlertsTable Schema v1
- `DC-S3-RAW-V1` — S3 Raw Reduced Events Layout v1
- `DC-S3-AGG-V1` — S3 Aggregates Snapshots Layout v1
- `DC-FEAT-V1` — Feature Parquet Schema v1
- `DC-EXPLAIN-V1` — Explanation Contract v1

---

## 1) Ingestion Event JSON Schema (reduced, non-sensitive) — DC-ING-V1

Example schema (v1):

```json
{
  "type": "object",
  "required": ["eventType","source","timestamp","userId","orgId","teamId","signalCounts","ingestionId","schemaVersion"],
  "properties": {
    "eventType": {"type":"string"},
    "source": {"type":"string"},
    "timestamp": {"type":"string","format":"date-time"},
    "userId": {"type":"string"},
    "orgId": {"type":"string"},
    "teamId": {"type":"string"},
    "role": {"type":"string"},
    "seniority": {"type":"string"},
    "signalCounts": {
      "type":"object",
      "properties": {
        "commits": {"type":"integer"},
        "prs": {"type":"integer"},
        "comments_count": {"type":"integer"},
        "meetings": {"type":"integer"},
        "meeting_duration_minutes": {"type":"integer"},
        "messages_sent": {"type":"integer"},
        "reactions_received": {"type":"integer"},
        "context_switches": {"type":"integer"}
      }
    },
    "metadata": {"type":"object"},
    "ingestionId": {"type":"string"},
    "schemaVersion": {"type":"integer"},
    "privacyMarker": {
      "type":"object",
      "properties": {
        "optIn": {"type":"boolean"},
        "hashedIdSaltVersion": {"type":"integer"}
      }
    }
  }
}
```

Notes:
- No free text fields allowed. Any incoming optional text must be dropped by EventBridge Pipes.
- `userId` must be opaque (UUID) and not contain PII.

### Strict Validation & Sanitization Rules (NEW)
- Drop rules:
  - Any fields not defined in `DC-ING-V1` MUST be dropped immediately by EventBridge Pipes. Pipes must apply a whitelist schema and remove unknown keys.
- Reject rules:
  - Events missing any `required` fields MUST be rejected at the EventBridge consumer boundary (Lambda or Pipe). Rejected events MUST NOT be persisted beyond transient logs.
  - Fields with invalid types or numeric values outside allowed bounds (see Allowed Enums & Numeric Bounds) MUST be rejected.
- DLQ / Poison message rules:
  - Messages failing normalization more than 3 attempts (SQS redrive count) are considered poison and moved to DLQ.
  - DLQ messages MUST contain only metadata about the failure (`ingestionId`, `schemaVersion`, `source`, `timestamp`, `failureCode`) — not raw payload.
  - Operators must inspect DLQ metadata and reprocess by replaying sanitized events from S3 where applicable.

### Allowed Enums & Numeric Bounds (NEW)
- `eventType` (enum): "issue_event", "pull_request", "slack_interaction", "calendar_change", "hris_update", "synth"
- `source` (enum): "jira", "github", "slack", "calendar", "hris", "synth"
- `role` (enum): MVP set — "engineer", "manager", "designer", "product", "qa", "other"
- `seniority` (enum): "junior", "mid", "senior", "lead", "manager", "director"
- Numeric bounds for counts (inclusive):
  - `commits`, `prs`, `comments_count`, `messages_sent`, `reactions_received`, `context_switches`: integer, min 0, max 100000
  - `meetings`: integer, min 0, max 1000
  - `meeting_duration_minutes`: integer, min 0, max 100000
- Numeric fields outside these bounds MUST be rejected as invalid.

---

## 2) DynamoDB: AggregatesTable (per-user-per-week) — DC-DDB-AGG-V1
- PK: `PK = "USER#<userId>"`
- SK: `SK = "WEEK#<YYYY-WW>"`
- Attributes: `userId`, `week`, `orgId`, `teamId`, `role`, `seniority`, `aggregates` (map of counts and computed indices), `cohort_baseline` (map), `z_scores` (map), `createdAt`, `updatedAt`, `encryptionMarker`
- GSI: `GSI1` PK = `"TEAM#<teamId>"`, SK = `"WEEK#<YYYY-WW>"` (for Manager queries)

### DynamoDB Access Patterns (Queries) (NEW)
- Supported exact queries (single-table patterns):
  - Get aggregate for a user for a week:
    - Query by PK = `USER#<userId>` and SK = `WEEK#<YYYY-WW>` — returns single item.
  - List aggregates for a user over N weeks:
    - Query PK = `USER#<userId>` and SK begins_with `WEEK#` with limit.
  - Manager team week view:
    - Query `GSI1` with PK = `TEAM#<teamId>` and SK = `WEEK#<YYYY-WW>` — returns team members' aggregates for that week.
  - Alerts retrieval for a user:
    - Query `AlertsTable` by SK pattern (see `DC-DDB-ALERT-V1`).
- Not supported (MVP): heavy cross-team scans; avoid full table scans.

---

## 3) DynamoDB: AlertsTable — DC-DDB-ALERT-V1
- PK: `ALERT#<alertId>`
- SK: `USER#<userId>#WEEK#<YYYY-WW>`
- Attributes: `scoreProbability`, `topFeatures` (list), `ruleTriggered`, `mlModelVersion`, `explanationRef` (S3 key or Bedrock conversation id), `createdAt`, `status`

### DynamoDB Access Patterns for Alerts & UI (NEW)
- Query alerts for a user:
  - Query `AlertsTable` by SK begins_with `USER#<userId>#WEEK#` to retrieve recent alerts.
- Query alerts for team (Manager):
  - Scan is not recommended. Manager views should query `AggregatesTable` by `GSI1` to get users for team and then fetch `AlertsTable` items per-user as needed (batchGetItem).
- Supported UI patterns:
  - Manager dashboard: query `GSI1` for team week then batch fetch alerts for listed users.
  - Employee portal: direct query by PK/SK for user/week aggregates and alerts.

---

## 4) S3 Partitioning & Glue Catalog — DC-S3-RAW-V1 & DC-S3-AGG-V1
- Raw events bucket (`DC-S3-RAW-V1`): `s3://signalhr-raw-events-dev/year=YYYY/month=MM/day=DD/source={source}/events-<timestamp>.jsonl`
  - Files MUST be newline-delimited JSON with sanitized reduced events only.
  - S3 object metadata MUST include: `ingestionId`, `schemaVersion`, `source`, and `checksum`.
- Aggregates snapshot bucket (`DC-S3-AGG-V1`): `s3://signalhr-aggregates-dev/year=YYYY/week=YYYY-WW/aggregates-<timestamp>.parquet`
  - Parquet files MUST match the Feature Parquet Schema where applicable.
- Glue DB: `signalhr_raw_db`; tables: `events_v1` (JSON), `aggregates_parquet`

---

## 5) Feature Parquet Schema (feature store logical) — DC-FEAT-V1
- Columns: `userId`, `week`, `overload_trend`, `context_switch_rate`, `collaboration_index`, `growth_index`, `cohortId`, `z_overload_trend`, `z_context_switch_rate`, `z_collaboration_index`, `z_growth_index`
- Storage: S3 feature store path MUST be `s3://signalhr-aggregates-dev/features/year=YYYY/week=YYYY-WW/feature-<timestamp>.parquet`

### Idempotency & Dedup Policy (NEW)
- Primary dedup key: `ingestionId` (opaque UUID supplied by source or generator). `DC-ING-V1` requires `ingestionId`.
- Dedup window: 7 days for ingest-level deduplication. Implement dedup via a short-lived dedup store (DynamoDB table or Lambda idempotency cache) keyed by `ingestionId` with TTL 7 days.
- Duplicate handling:
  - If `ingestionId` already seen within dedup window, drop the event and emit a duplicate metric; no further processing.
  - If `ingestionId` absent or expired, process normally and record `ingestionId` in dedup store.
  - On dedup store failure, fail safe: process event but log potential duplicate risk and raise an alarm.

---

## Time Semantics (NEW)
- All timestamps MUST be in UTC (ISO 8601). Services MUST normalize times to UTC on ingestion.
- Week definition: ISO week starting Monday. WEEK key MUST be formatted as `YYYY-WW` where `WW` is ISO week number.
- Timestamp → WEEK rules:
  - For any event timestamp, compute WEEK by its UTC date's ISO week. The rollup Step Functions MUST use timestamp → WEEK mapping consistently.
  - Events with timestamps outside reasonable ranges (older than 365 days or future > 30 days) SHOULD be rejected.

---

## Schema Versioning
- Each record includes `schemaVersion`.
- Changes require CR and increment `schemaVersion`.

---

## Explanation Contract — DC-EXPLAIN-V1 (NEW)
- Purpose: Standardize how "Why flagged" and "Next best action" are stored and referenced.
- Schema for Explanation object (stored in S3 as JSON or referenced via Bedrock session id):

```json
{
  "explanationId": "string",
  "alertId": "string",
  "userScope": "team|user|cohort",
  "why": {
    "summary": "string",
    "signals": [ {"feature": "string", "value": number, "cohort_z": number} ],
    "cohort_comparison": "string"
  },
  "next_best_actions": [ {"action_type":"1:1|workload|resources|wellness","description":"string","confidence":number} ],
  "kb_references": [ "s3://signalhr-kb-dev/policies/burnout.md#L10-L20" ],
  "generatedAt": "ISO8601",
  "generatedBy": { "type":"bedrock|service", "id":"string" },
  "storageRef": { "type":"s3","key":"s3://signalhr-explanations-dev/<explanationId>.json" }
}
```

### Storage reference rules:
- If Bedrock produced the explanation, store the canonical explanation JSON in S3 under prefix `s3://signalhr-explanations-dev/` with key pattern `<explanationId>.json` and reference the S3 key in `AlertsTable.explanationRef`.
- Alternatively, `explanationRef` may carry a Bedrock conversation/session id (prefixed `bedrock://<sessionId>`) but the canonical explanatory text MUST still be persisted to S3 for audit and MUST NOT contain PII.
- S3 explanations MUST be encrypted with KMS and have access restricted to HR audit role and the Manager role as appropriate.

---

## Feature & Normalization Contract — DC-FEAT-V1 (NEW)
- `cohortId` formula:
  - `cohortId = sha256(orgId + '|' + role + '|' + seniority + '|' + teamId)` truncated to first 16 hex chars, salted with `hashedIdSaltVersion`.
  - Cohorts are computed per organization to avoid cross-org leakage.
- `z-score` formula:
  - `z = (x - mu_cohort) / sigma_cohort`
  - `mu_cohort` and `sigma_cohort` are computed on historical feature values for the cohort (minimum required cohort size = 5).
- Cohort size fallback rules:
  - If cohort size < 5, use role+seniority aggregated baseline (broader cohort). If still <5, fallback to org-level baseline and log reduced-confidence flag in feature metadata.
  - All fallback steps MUST be recorded in `cohort_baseline` metadata with `baseline_source` field set to `cohort|role_seniority|org`.
- Feature normalization:
  - Features MUST be numeric, finite, and within expected bounds (see numeric bounds earlier). Out-of-range values MUST trigger rejection or clipping per config (default: reject).

### Feature Storage & Access (NEW)
- Feature parquet files MUST include `cohortId`, `cohort_size`, `baseline_mu`, and `baseline_sigma` columns for auditability.
- Feature jobs MUST write a `feature_manifest.json` for each week with stats and cohort counts.

---

## 9) DynamoDB: AlertsTable (repeated for clarity) — DC-DDB-ALERT-V1
- PK: `ALERT#<alertId>`
- SK: `USER#<userId>#WEEK#<YYYY-WW>`
- Attributes: `scoreProbability`, `topFeatures` (list), `ruleTriggered`, `mlModelVersion`, `explanationRef` (S3 key or Bedrock conversation id), `createdAt`, `status`

---

## Privacy Compliance Checklist (NEW)
For each schema and storage target, perform these checks before marking Done:
- No free-text fields persisted in S3, DynamoDB, or any index.
- `userId` is opaque (UUID) and not reversible; salt version applied.
- Explanations stored in S3 contain no raw PII or event text.
- KMS encryption enabled and keys scoped per environment.
- Access controls (IAM, Cognito groups) restrict read access to Aggregates and Explanations appropriately.
- Audit logs (CloudTrail) record who accessed explanation objects; include evidence link.
- LLM inputs to Bedrock are sanitized (only aggregates/derived values) and logged as hashes/pointers, not raw content.
- For all fallback cohort computations, record `baseline_source` and `reduced-confidence` indicator.

---

## Schema Versioning (reiterated)
- Each record includes `schemaVersion`.
- Changes require CR and increment `schemaVersion`.

---

## Examples
- Provide sample JSON event and sample DynamoDB aggregate item in `examples/` subfolder (TBD).

Change control: edit this file only via CR.