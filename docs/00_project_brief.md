# Project Brief — SignalHR (Immutable)

IMPORTANT: This file is the single source of truth for project scope, constraints, and assumptions. It is immutable and may be changed only via a documented Change Request recorded in docs/CHANGE_REQUESTS.md.

Project: HR Intelligence — Hackathon MVP (48h)
Goal: Privacy-first signals (not surveillance) to detect Burnout, Performance Drift, and HiPo potential with explainability.

Hard Constraints
- Must implement the provided AWS Reference Architecture exactly. No architectural changes without a Change Request (CR).
- Serverless-first and minimal cost for MVP.
- Synthetic/demo data only for this hackathon.
- Explainability and employee transparency mandatory.
- NEVER store message text, keystrokes, screenshots, or other raw content.

MVP Deliverables
- Ingestion endpoints (API Gateway → EventBridge). EventBridge Pipes filter/transform.
- SQS + DLQ buffer.
- Lambda normalization; Step Functions for daily/weekly rollups.
- DynamoDB per-user-per-week aggregates; S3 raw reduced events + Glue Data Catalog.
- Feature extraction jobs and cohort z-score normalization.
- Rules engine + SageMaker Serverless XGBoost (light ML) for scoring with explanations.
- Amazon Bedrock Agent (Manager Copilot) for "Why flagged" and "Next best action".
- OpenSearch Serverless optional for KB/RAG.
- UI hosted via Amplify/Next.js with Cognito RBAC (Manager/Employee/HR).
- Observability via CloudWatch, X-Ray, CloudTrail; KMS encryption; IAM least privilege.

Assumptions (documented; update only via CR)
- AWS region: us-east-1
- DynamoDB chosen for MVP due to cost/perf; Aurora Serverless v2 reserved as alternate (CR required to switch).
- Bedrock access exists in account; if unavailable, CREATE CR.
- Synthetic generator produces opaque `userId` (UUID) and non-sensitive numeric signals.

Owner & Contacts
- Project Owner: TBD (assign before implementation)
- Demo Lead: TBD

Change Request (CR) Process
- All deviations must be raised as a CR in docs/CHANGE_REQUESTS.md using the template there.
- CRs start as NOT APPROVED; Project Owner approves or rejects.
- No work that changes the architecture or privacy rules may begin until CR is APPROVED.

Audit header
- Created: 2026-02-06
- Version: 1.0
- Last Modified: 2026-02-06 (only via CR)
