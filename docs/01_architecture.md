# Architecture Mapping — SignalHR MVP

This document maps the mandated AWS Reference Architecture to concrete services and data flow. This file is part of the documentation system and must be used by all agents.

High-level service mapping
- API Layer: Amazon API Gateway (REST) or AppSync (GraphQL) — ingest endpoints for connectors and synthetic generators.
- Event Bus & Pipes: Amazon EventBridge (custom bus) + EventBridge Pipes for filter/transform to reduce payloads.
- Queueing: Amazon SQS (standard) + DLQ for message durability.
- Processing: AWS Lambda for normalization; AWS Step Functions for daily/weekly rollups.
- Storage: DynamoDB (AggregatesTable) for per-user-per-week aggregates; Amazon S3 for raw reduced events + historical snapshots; Glue Data Catalog for S3 schemas.
- Feature Jobs: AWS Glue or Lambda jobs to compute features and cohort baselines.
- Intelligence: Lambda Rules engine (fast MVP) and SageMaker Serverless (XGBoost) for light ML.
- Explainability & Coaching: Amazon Bedrock Agent for Manager Copilot; KB stored in S3 and optionally indexed in OpenSearch Serverless for retrieval.
- Experience: AWS Amplify Hosting (Next.js) and Amazon Cognito for RBAC.
- Observability: CloudWatch (logs/metrics), X-Ray (traces), CloudTrail (audit), KMS (encryption), IAM least-privilege.

Exact Data Flow (MANDATED - do not change)
Events → API Gateway → EventBridge
EventBridge Pipes → SQS → Lambda Normalize
Aggregates → DynamoDB + Raw → S3
Feature Jobs → Feature Store
Scoring → Alert Store
Bedrock Agent → Explanation + Coaching
UI → Alert + Why + Action + Transparency

Resource naming & environment notes (dev/demo)
- EventBus name: signalhr-bus-dev
- SQS: signalhr-ingest-queue-dev; DLQ: signalhr-ingest-dlq-dev
- DynamoDB: AggregatesTable-dev, AlertsTable-dev
- S3 buckets: signalhr-raw-events-dev, signalhr-aggregates-dev, signalhr-kb-dev
- Glue DB: signalhr_raw_db
- SageMaker model: signalhr-xgb-mvp
- Bedrock: bedrock-agent-signalhr (logical)

Permissions (summary)
- API Gateway: role to PutEvents to EventBridge (least privilege for only PutEvents on signalhr-bus-dev)
- EventBridge Pipes: IAM role with PutMessage to SQS
- Lambda: role to read SQS, write S3, update DynamoDB (least privilege)
- Step Functions: execution role to read S3, invoke Lambdas, write DynamoDB
- SageMaker: role for training access to S3 and logs
- Bedrock: role/credentials per org policy (only access to KB objects, no raw user data)

Operational constraints & cost notes
- Favor serverless (Lambda, DynamoDB on-demand, S3, SageMaker Serverless) to minimize cost for MVP.
- Glue usage limited to small jobs; prefer Lambda for light feature calculations if Glue startup overhead is prohibitive.

Diagrams & pointers
- Include ASCII diagram and pointer to any created CloudFormation/Terraform templates in docs/08_deployment_plan.md

Change control: Any change to this file that impacts the mandated architecture must be accompanied by a CR in docs/CHANGE_REQUESTS.md.