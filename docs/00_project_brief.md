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

<!-- NEW SECTION: Explicit Out of Scope -->
## Explicit Out of Scope (NEW)

- Storing or processing raw message text, keystrokes, screenshots, file contents, or conversation transcripts.
- Any automated punitive actions (terminations, pay changes, disciplinary actions) initiated by the system.
- Production/integration with live customer data or PII for the Hackathon MVP — synthetic/demo data only.
- Advanced offline model training on PII-containing datasets.
- Broad cross-role ranking or public leaderboards comparing employees across disparate roles or seniority.

These out-of-scope rules are strict and enforceable: any request to implement them must be submitted as a Change Request (docs/CHANGE_REQUESTS.md) and will be considered outside the MVP.

<!-- NEW SECTION: Success Criteria -->
## Success Criteria (NEW)

Measurable MVP outcomes that must be met for acceptance:
- Ingestion throughput: pipeline accepts and processes 1,000 synthetic events/hour end-to-end (API Gateway → EventBridge → SQS → Lambda). Measured by EventBridge metric and SQS depth logs.
- Normalization latency: `Lambda normalization` processes a single event in median ≤200ms (CloudWatch metric).
- Rollup latency: `Step Functions` daily/weekly rollup completes 10k-event batch in ≤5 minutes (execution history).
- Aggregates responsiveness: DynamoDB returns per-user-per-week aggregate in ≤50ms (p95) for test queries.
- Feature coverage: Feature jobs produce the four required features for ≥95% of synthetic users in test set.
- Rule precision: Rule-based detector precision ≥0.8 on labeled synthetic test cases.
- ML scoring: SageMaker Serverless XGBoost returns probability + top 3 feature importances; scoring latency ≤2s for MVP requests.
- Explainability: Bedrock Agent produces "Why flagged" + "Next best action" without any sensitive data leakage; sensitive-leakage tests must show 0 occurrences in QA runs.
- Transparency & RBAC: Cognito RBAC restricts views properly; employees can view opt-in settings and their own signals.
- Demo reproducibility: The 3-employee demo reproduces expected flags and explanations and captures required evidence artifacts.

Evidence for each criterion must be uploaded and linked in `docs/03_backlog.md` for verification before marking tasks Done.

<!-- NEW SECTION: Documentation Authority rules -->
## Documentation Authority (NEW)

- Canonical single source of truth: `docs/00_project_brief.md` remains the authoritative project brief.
- Editorial exception: This hardening update is an authorized editorial clarification that does NOT change architecture, scope, or privacy rules. It is recorded here and does not require a Change Request.
- Change control rules:
	- Any modification that affects architecture, privacy, security, or scope MUST be submitted as a CR in `docs/CHANGE_REQUESTS.md` and remain in status `NOT APPROVED` until Project Owner approval.
	- Minor editorial clarifications to supporting docs (`docs/01_*`–`docs/09_*`) require a pull request and one reviewer sign-off; they do NOT require a CR unless they affect architecture/privacy/security.
	- Only the Project Owner (or an explicitly delegated Document Maintainer) can approve CRs and set CR status to `APPROVED`.
- AI & automation rules for docs:
	- Automated agents MUST read and cite the exact doc file and section ID before taking any action.
	- Automated agents MUST create CR entries for any intended change to `docs/00_project_brief.md` or any change that affects architecture/privacy/security.

<!-- NEW SECTION: 48-hour Time Budget -->
## 48-hour Time Budget (NEW)

This project is time-boxed to 48 hours. Execution constraints and rules:
- Total elapsed time budget: 48 hours from project start.
- High-level time allocation (guideline only):
	- Ingestion & infra bootstrap: 6 hours
	- Normalization & storage rollups: 8 hours
	- Feature jobs & bias normalization: 6 hours
	- Rules engine & light ML setup: 8 hours
	- Bedrock explainability & KB ingestion: 6 hours
	- UI + Auth + Observability: 6 hours
	- QA, packaging, demo prep: 8 hours
- The Executor must track time and update `docs/03_backlog.md` with start/finish timestamps for each task. If a task is estimated to exceed its allocation, a CR must be raised for schedule adjustment.

<!-- NEW SECTION: AI Execution Rules (assumptions & hallucination prevention) -->
## AI Execution Rules (NEW)

These rules make the AI's behavior enforceable and reduce hallucination risk.

1) Data & Documentation Binding
	- The AI MUST treat `docs/00_project_brief.md` as the immutable source of truth for scope and privacy constraints (except the authorized editorial clarification above).
	- The AI MUST reference specific doc paths and section headers (e.g., `docs/02_data_contracts.md#Ingestion-Event-JSON-Schema`) when making design or implementation choices.

2) No Assumptions Without CR
	- The AI MUST NOT invent infrastructure, ARNs, credentials, or unapproved defaults. Any missing decision (region, resource names, Bedrock availability) must be recorded as an assumption in `docs/00_project_brief.md` and logged as a CR if it affects architecture or privacy.

3) Evidence-Driven State Changes
	- The AI MUST NOT change a task status in `docs/03_backlog.md` from `In Progress` to `Done` unless the required Evidence of Completion (as defined in backlog tasks) is provided and linked (S3 object key, CloudWatch log link, DynamoDB item JSON, screenshot, or PR link).
	- Before marking `Ready for Review`, the AI must attach test artifacts and at least one independent verification artifact (e.g., StepFunction execution ARN, S3 checksum).

4) Hallucination Prevention for LLMs
	- When producing prompts for Bedrock or any LLM, the AI MUST:
		- Only pass sanitized, non-identifying aggregates and cohort statistics.
		- Never include `userId`, PII, or raw event details.
		- Add prompt injection mitigations: prepend the system prompt with explicit guardrails (see `docs/06_security_privacy.md`).
	- All LLM outputs intended for user consumption MUST pass an automated post-response scanner that checks for: PII, legal/HR action recommendations, and unsupported factual assertions. If the scanner flags the output, the AI must discard it, log an incident, and generate a safe fallback response.

5) Traceability & Audit
	- All AI actions that modify infrastructure, create CRs, or update backlog statuses MUST be recorded with: timestamp, agent identifier, source doc references, and evidence links in `docs/03_backlog.md` or `docs/CHANGE_REQUESTS.md`.

6) Use of Memory
	- The AI MUST NOT rely on ephemeral memory between sessions for authoritative decisions. It must re-read the canonical docs referenced above at the start of each planning/execution cycle.

7) Escalation
	- If the AI encounters an ambiguous requirement or a potential privacy/security conflict, it MUST open a CR (docs/CHANGE_REQUESTS.md) with status `NOT APPROVED` and notify the Project Owner; no implementation work may continue on the conflicting item.

8) Safe Defaults & Fail-Closed
	- When in doubt, the AI will choose the privacy-preserving, conservative option (e.g., drop optional text fields, do not persist uncertain attributes). Systems must fail-closed with respect to privacy.

9) Developer/Executor Collaboration
	- Human Executors may override AI implementation suggestions but must record the rationale and link to the approving CR in `docs/CHANGE_REQUESTS.md`.

10) Testing Requirement Prior to Presentation
	- Before any demo or stakeholder presentation, the AI MUST run the QA checklist in `docs/05_qa_strategy.md` and include the test report link in the demo evidence bundle.

-- End of NEW Sections --
