# Backlog (Canonical)

This file is the canonical backlog for the project and mirrors the tracked todo list. Each task must include: Task ID, Title, Description, Inputs/Outputs, Acceptance Criteria, Evidence of Completion, Dependencies, Status.

Initial tasks (all start: Not Started)

- ING-01: Create REST ingestion endpoints (API Gateway)
- ING-02: Configure EventBridge bus + Pipes
- ING-03: Provision SQS queue + DLQ
- ING-04: Build synthetic data generators
- PROC-01: Lambda normalization
- PROC-02: Step Functions rollups
- PROC-03: DynamoDB AggregatesTable + AlertsTable
- FEAT-01: Feature extraction jobs (Glue/Lambda)
- FEAT-02: Cohort baseline & z-score
- INT-01: Rules engine (Lambda)
- INT-02: SageMaker Serverless XGBoost
- INT-03: Explainability packaging
- BED-01: Bedrock Agent integration
- BED-02: Knowledge Base ingestion
- UI-01: Cognito RBAC
- UI-02: Amplify/Next.js skeleton
- OBS-01: CloudWatch, X-Ray, CloudTrail dashboards
- OBS-02: IAM & KMS
- DOC-01: Populate required docs
- QA-01: QA test harness + synthetic dataset
- DEMO-01: Demo scenario & evidence capture

Status: All tasks currently Not Started. Use this file to update task statuses with evidence links and timestamps.

Verification workflow (copy into each task):
1. Not Started
2. In Progress — attach Start Evidence (branch or commit link)
3. Ready for Review — attach test artifacts and PR URL
4. Review — Reviewer validates evidence
5. Done — Reviewer+QA sign off and add Evidence of Completion

Evidence required: CloudWatch logs, S3 object keys + checksums, DynamoDB item JSON, screenshots, or test reports.

Change requests: See docs/CHANGE_REQUESTS.md
