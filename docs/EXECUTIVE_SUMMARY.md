# Executive Summary — SignalHR (Hackathon MVP)

Problem
- Early signs of employee burnout, performance drift, and hidden high-potential (HiPo) talent are noisy and privacy-sensitive; organizations lack explainable, low-cost signals that protect employee privacy.

Solution
- Privacy-first, serverless MVP that ingests reduced numerical signals, normalizes and aggregates them per-user-per-week, extracts cohort-normalized features, applies rules + light ML scoring, and delivers explainable manager guidance.

Privacy‑first Promise
- Synthetic/demo data only for hackathon; NEVER store raw message text, keystrokes, screenshots, or PII.
- Opaque user identifiers (UUIDs), KMS encryption, IAM least privilege, and explicit sanitization at ingestion.

AWS Architecture Flow (mandated, serverless)
- API Gateway → EventBridge (Pipes filter/transform) → SQS (+ DLQ) → Lambda normalization
- Step Functions for daily/weekly rollups → DynamoDB per-user-per-week aggregates
- S3 for raw reduced events + Glue Data Catalog; feature extraction jobs produce cohort z‑scores
- Rules engine + SageMaker Serverless XGBoost for scoring (with feature importances)
- Amazon Bedrock Agent (Manager Copilot) for "Why flagged" and "Next best action"
- UI hosted via Amplify/Next.js with Cognito RBAC; observability via CloudWatch, X‑Ray, CloudTrail

What the Demo Shows
- End‑to‑end ingestion of deterministic synthetic events → normalized pipeline artifacts
- Per‑user weekly aggregates and cohort‑normalized features
- Rule + ML scoring with probability + top feature contributions
- Explainability output ("Why flagged" and suggested non‑punitive next actions) surfaced to Manager/Employee RBAC views
- Evidence bundle: logs, DynamoDB items, S3 artifacts, screenshots demonstrating privacy compliance

Why This Matters
- Enables early, explainable intervention without surveillance: actionable signals, not content.
- Serverless, low‑cost MVP architecture expedites deployment and reproducibility.
- Built-in auditability, strict privacy guardrails, and deterministic demoability make the solution suitable for compliance review and stakeholder demos.

Audit & Change Control
- Project brief (docs/00_project_brief.md) and architecture mapping (docs/01_architecture.md) are the single sources of truth; any deviation requires a documented Change Request.