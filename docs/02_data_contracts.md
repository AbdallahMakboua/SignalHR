# Data Contracts — SignalHR

This doc defines ingestion event schemas, DynamoDB schemas, S3 partitioning, and feature schemas. All schema changes require a Change Request in docs/CHANGE_REQUESTS.md.

1) Ingestion Event JSON Schema (reduced, non-sensitive)

Example schema (v1):

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

Notes:
- No free text fields allowed. Any incoming optional text must be dropped by EventBridge Pipes.
- `userId` must be opaque (UUID) and not contain PII.

2) DynamoDB: AggregatesTable (per-user-per-week)
- PK: PK = "USER#<userId>"
- SK: SK = "WEEK#<YYYY-WW>"
- Attributes: userId, week, orgId, teamId, role, seniority, aggregates (map of counts and computed indices), cohort_baseline (map), z_scores (map), createdAt, updatedAt, encryptionMarker
- GSI: GSI1 PK = "TEAM#<teamId>", SK = "WEEK#<YYYY-WW>" (for Manager queries)

3) DynamoDB: AlertsTable
- PK: ALERT#<alertId>
- SK: USER#<userId>#WEEK#<YYYY-WW>
- Attributes: scoreProbability, topFeatures (list), ruleTriggered, mlModelVersion, explanationRef (S3 key or Bedrock conversation id), createdAt, status

4) S3 Partitioning & Glue Catalog
- Raw events bucket: s3://signalhr-raw-events-dev/year=YYYY/month=MM/day=DD/source={source}/events-<timestamp>.jsonl
- Aggregates snapshot bucket: s3://signalhr-aggregates-dev/year=YYYY/week=YYYY-WW/aggregates-<timestamp>.parquet
- Glue DB: signalhr_raw_db; tables: events_v1 (JSON), aggregates_parquet

5) Feature Parquet Schema (feature store logical)
- Columns: userId, week, overload_trend, context_switch_rate, collaboration_index, growth_index, cohortId, z_overload_trend, z_context_switch_rate, z_collaboration_index, z_growth_index

6) Schema Versioning
- Each record includes `schemaVersion`.
- Changes require CR and increment schemaVersion.

7) Examples
- Provide sample JSON event and sample DynamoDB aggregate item in examples/ subfolder (TBD).

Change control: edit this file only via CR.