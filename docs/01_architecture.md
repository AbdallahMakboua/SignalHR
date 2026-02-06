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

<!-- NEW SECTION: Architecture Guardrails & Boundaries -->
## Architecture Guardrails & Boundaries (NEW)

These guardrails enforce the privacy-first, signal-only mandate. They are binding for all agents and implementers.

- Service access prohibitions (MAY NOT):
	- AppSync/API Gateway/Pipes/SQS/Lambda/Step Functions **MAY NOT** persist or forward any free-text fields, message content, keystrokes, screenshots, or file contents. EventBridge Pipes must remove such fields before delivery.
	- Bedrock Agent **MAY NOT** receive raw event payloads, `userId` in cleartext, or any PII. Only sanitized aggregates, cohort statistics, and KB excerpts may be passed.
	- SageMaker Serverless training or scoring **MAY NOT** access raw message text or PII; training input must be feature parquet in S3 (derived features only).
	- OpenSearch (if used) **MAY NOT** index or store raw content or identifiers that are reversible to PII; only KB and policy/playbook content allowed.
	- UI (Amplify/Next.js) **MAY NOT** render raw events or any PII. UI calls must be mediated by backend APIs that enforce RBAC and privacy filters.

- Data flow boundaries:
	- EventBridge and EventBridge Pipes are the first line of defense for payload reduction — they must implement schema enforcement rules and drop disallowed fields.
	- SQS is a transient buffer for reduced events only. No raw content should exist in the queue.
	- Lambda normalization must validate schemaVersion and reject any event with unexpected free-text fields, logging rejections to CloudWatch only (no content persistence).

- Encryption & keys:
	- All persisted data must be encrypted with KMS keys. Keys must be scoped by environment and rotated per org policy.

- Permissioning:
	- Roles for services must be least privilege. No cross-service role should grant broader read access than necessary (e.g., Lambda role should not have global S3 read/write).

Non-compliance with any guardrail requires a CR and an incident log entry in `docs/03_backlog.md` with remediation plan.

<!-- NEW SECTION: Failure Handling & Reliability (MVP Scope) -->
## Failure Handling & Reliability (MVP Scope) (NEW)

This section defines minimal reliability behavior for the MVP and manual recovery expectations.

- EventBridge & Pipes:
	- EventBridge PutEvents is best-effort; producers should handle HTTP 5xx/429 by retrying with exponential backoff (client-side). EventBridge Pipes should be configured with simple transformations and a retry policy where supported.

- SQS:
	- Messages in the ingest queue must have a VisibilityTimeout appropriate to Lambda batch processing time (e.g., 2x max Lambda timeout).
	- Redrive policy: after 3 receive attempts (configurable), messages move to DLQ.

- Lambda normalization (consumer of SQS):
	- Implement idempotency keys based on `ingestionId` to avoid double-processing.
	- Lambda retries are controlled by SQS redelivery. For transient errors, rely on SQS redelivery; for deterministic schema errors, send to DLQ with rejection metadata.
	- On failure, Lambda must emit structured error logs containing `ingestionId` and failure reason (no payload) to CloudWatch and X-Ray trace.

- Step Functions (rollups):
	- Define retry behavior for transient steps (3 attempts with exponential backoff) in state definitions.
	- For partial failures in Map/Parallel states, mark affected partitions and write a failure manifest to S3 for targeted reprocessing.

- DLQ Handling & Manual Recovery Expectations:
	- Operators must monitor DLQ via CloudWatch alarm (DLQ > 0) and inspect the DLQ message metadata (not payload). Recovery steps:
		1. Investigate error reason via CloudWatch logs and X-Ray traces using `ingestionId` and timestamps.
		2. If fixable (schema mismatch or transformation bug), fix the transformation and reprocess messages by replaying stored reduced events from S3 (if present) or by re-invoking producers for synthetic data.
		3. For corrupted messages that cannot be replayed, document incident and delete from DLQ after approval.

 - SLA expectations (MVP):
	 - Typical end-to-end processing should be minutes for single events; batch rollups may take up to the targets defined in docs/00_project_brief.md Success Criteria.

<!-- NEW SECTION: Data Classification (NEW) -->
## Data Classification (NEW)

Classify all data to enforce storage and access rules. Each class maps to permitted storage locations and allowed consumers.

- Signal (raw reduced events):
	- Definition: Incoming numeric counts and event markers produced by sources (no free text). Example: {commits: 3, meetings: 2, context_switches: 5}.
	- Allowed storage: transient SQS, S3 raw reduced events (retention 90 days), EventBridge (ephemeral). Not allowed in DynamoDB aggregates except via normalized aggregates.
	- Consumers: Lambda normalization, Step Functions (rollup orchestration), Glue jobs for feature extraction.

- Aggregate:
	- Definition: Per-user-per-week aggregated counts and indices (the canonical privacy-preserving stored view).
	- Allowed storage: DynamoDB AggregatesTable (primary), S3 aggregates snapshots (Parquet) for historical analysis.
	- Consumers: Feature Jobs, UI (per RBAC and opt-in), Bedrock (only sanitized aggregates and cohort stats), Rules engine.

- Derived:
	- Definition: Computed features, z-scores, model inputs/outputs, alert objects, and SHAP-like explanations.
	- Allowed storage: S3 feature store (Parquet), DynamoDB AlertsTable (summary), SageMaker artifacts (model artifacts in S3).
	- Consumers: SageMaker (training & scoring on features), Bedrock (explanation input limited to sanitized derived data), UI (alerts and explanations per RBAC), Rules engine.

- Metadata:
	- Definition: IngestionId, timestamps, schemaVersion, org/team identifiers (non-PII), retention markers, encryption markers.
	- Allowed storage: S3, DynamoDB, CloudWatch logs (structured, no PII), CloudTrail.
	- Consumers: All services for routing and audit; Bedrock must not receive raw metadata that can identify individuals (e.g., userId) unless hashed/aggregated.

Access Matrix (summary):

 - API Gateway / EventBridge / Pipes: may handle Signal and Metadata (must drop text).
 - SQS / Lambda / Step Functions / Glue: may handle Signal, Derived (during processing), and Metadata; must not leak raw identifiers beyond hashed/opaque IDs.
 - DynamoDB AggregatesTable: stores Aggregate + Metadata only.
 - S3 buckets: raw reduced events (Signal), aggregates snapshots (Aggregate), feature parquet (Derived), KB (policies/playbooks).
 - SageMaker: may read Derived (feature parquet) and write model artifacts to S3; may not read Signal raw events containing any unreduced payload.
 - Bedrock Agent: may read Aggregate (sanitized) and Derived (explanations) and KB; must NOT read Signal raw events or metadata containing PII.
 - UI: may display Aggregate and Derived (alerts/explanations) per RBAC and employee opt-in; must never display raw Signal payloads or raw metadata that could identify employees.

Any deviation from the matrix requires a documented CR and approval.

<!-- NEW SECTION: Environment & Isolation Rules (NEW) -->
## Environment & Isolation Rules (NEW)

To prevent cross-environment leakage and accidental production access, follow these rules.

- Dev/demo-only assumptions:
	- All current work is in a dev/demo environment. No production data or credentials are permitted.
	- Resources must be tagged with `Environment=dev` or `Environment=demo` as appropriate.

- Naming conventions (isolation boundary):
	- Use predictable prefixes and suffixes to separate environments, e.g., `signalhr-<component>-dev`, `signalhr-raw-events-dev`, `AggregatesTable-dev`.
	- KMS keys must be named and scoped per environment (e.g., `alias/signalhr-dev-key`).

- Explicit cross-environment access rule:
	- Resources in `dev` must not access or assume roles in `prod` (if prod exists). IAM policies must explicitly deny `sts:AssumeRole` across environment boundaries.
	- Network, S3 bucket policies, and Glue catalogs must prohibit cross-environment reads/writes by default.

- Isolation enforcement:
	- CI/CD and deployment scripts must accept `ENV` parameter (dev/demo) and create resources only within that namespace.
	- Any request to copy data across environments must be a CR and include justification, data minimization, and audit plan.

<!-- NEW SECTION: ASCII Architecture Diagram (NEW) -->
## ASCII Architecture Diagram (NEW)

Matches mandated data flow: Events → API Gateway → EventBridge → EventBridge Pipes → SQS → Lambda Normalize → Aggregates → DynamoDB + Raw → S3 → Feature Jobs → Feature Store → Scoring → Alert Store → Bedrock Agent → Explanation + Coaching → UI

ASCII diagram (left-to-right):

+----------------+    +----------------+    +------------------+    +--------+    +-----------+
|  External Src  | -> | API Gateway /  | -> | EventBridge Bus  | -> | Pipes  | -> |  SQS DLQ  |
| (Jira/GitHub/  |    | AppSync (REST) |    |  (signalhr-bus)  |    |        |    |(DLQ attached)
|  Slack/Cal/HR) |    +----------------+    +------------------+    +--------+    +-----------+
				|                                                                        |
				|                                                                        v
				|                                                                  +-----------+
				|                                                                  |  SQS Q   |
				|                                                                  +-----------+
				|                                                                        |
				v                                                                        v
	(synthetic)                                                         +--------------------+
																																			 | Lambda Normalize  |
																																			 |  (reads SQS,     |
																																			 |   validates,     |
																																			 |   writes S3 &    |
																																			 |   updates DDB)   |
																																			 +--------------------+
																																								|
																																								v
																																			+-----------------------+
																																			| DynamoDB Aggregates   |
																																			|  (per-user-per-week)  |
																																			+-----------------------+
																																								|
																																								v
																																			+-----------------------+
																																			| S3 Raw Reduced Events | <--- (also stores snapshots, features parquet)
																																			+-----------------------+
																																								|
																																								v
																																			+-----------------------+
																																			| Feature Jobs (Glue /  |
																																			|  Lambda) -> Feature   |
																																			|  Store (S3+Glue)      |
																																			+-----------------------+
																																								|
																																								v
																																			+-----------------------+
																																			| SageMaker Serverless  |
																																			|  (XGBoost scoring)    |
																																			+-----------------------+
																																								|
																																								v
																																			+-----------------------+
																																			| AlertsTable (DynamoDB)|
																																			+-----------------------+
																																								|
																																								v
																																			+-----------------------+
																																			| Bedrock Agent (KB +   |
																																			|  Explanation + Coach) |
																																			+-----------------------+
																																								|
																																								v
																																			+-----------------------+
																																			| Amplify / Next.js UI  |
																																			| Cognito (RBAC)        |
																																			+-----------------------+

Optional: OpenSearch Serverless (Vector) used only for KB RAG; it sits adjacent to S3 KB and Bedrock and must not index Signal or personal identifiers.

Change control: Any alterations to these guardrails or diagram must be proposed via a CR in docs/CHANGE_REQUESTS.md.