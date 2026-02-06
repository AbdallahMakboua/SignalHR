# Security, Privacy & Ethics — Rules and Guardrails

**CRITICAL:** This document defines enforceable security, privacy, and ethics controls. All rules are binding and verifiable. Violations mandate incident response and Change Requests. No component may circumvent these controls.

---

## Control Index (NEW)

Stable Control IDs organize all security, privacy, and ethics requirements. Each Control ID is immutable; versioning via CR only.

### Security Controls (SEC-*)

| Control ID | Control Name | Enforces | Where | Task |
|------------|--------------|----------|-------|------|
| SEC-01 | IAM Least Privilege | All roles follow least-privilege principle; no `*:*` permissions | IAM policies | OBS-02 |
| SEC-02 | KMS Encryption (S3) | All S3 buckets encrypted with KMS key at rest | S3 bucket policy + CloudFormation | OBS-02 |
| SEC-03 | KMS Encryption (DynamoDB) | All DynamoDB tables encrypted with KMS key at rest | DynamoDB table encryption | OBS-02 |
| SEC-04 | CloudTrail Logging | All API calls logged to CloudTrail; logs encrypted and immutable | CloudTrail → S3 | OBS-02 |
| SEC-05 | Secret Management | API keys, DB passwords, Bedrock API keys stored in Secrets Manager (not code) | Lambda env, Secrets Manager | OBS-02 |
| SEC-06 | Network Isolation | API Gateway only entry point; no direct Lambda/DynamoDB internet access | VPC, Security Groups (if applicable) | OBS-02 |

### Privacy Controls (PRIV-*)

| Control ID | Control Name | Enforces | Where | Task |
|------------|--------------|----------|-------|------|
| PRIV-01 | No Raw Text Storage | Message text, keystrokes, screenshots never persisted | EventBridge Pipes + Lambda | PROC-01 |
| PRIV-02 | No PII in Aggregates | Aggregates contain only opaque userId, numeric signals, metadata | Lambda normalization | PROC-01, PROC-03 |
| PRIV-03 | Opaque User Identifiers | userId is UUID/hash, never reversible to email/phone/name | API Gateway + Lambda | ING-01 |
| PRIV-04 | Data Retention Policy | Raw events 90d TTL, aggregates 2yr, explanations 1yr (configurable) | S3 lifecycle + DynamoDB TTL | OBS-02 |
| PRIV-05 | Bedrock Input Sanitization | Only non-sensitive features passed to Bedrock; userId, raw cohort data excluded | Lambda → Bedrock call | BED-01 |
| PRIV-06 | No PII in Explanations | Post-response scanner detects email, phone, SSN, password; blocks output if found | Bedrock Lambda wrapper | BED-02 |
| PRIV-07 | Employee Data Isolation | Employee portal shows only own data; Manager sees team aggregate; HR sees audit trail | Cognito RBAC + Lambda filters | UI-01, UI-02 |

### LLM / Bedrock Controls (LLM-*)

| Control ID | Control Name | Enforces | Where | Task |
|------------|--------------|----------|-------|------|
| LLM-01 | Guardrail: No Punitive Advice | Bedrock must not recommend firing, demotion, or disciplinary action | Bedrock guardrail policy + post-response filter | BED-01 |
| LLM-02 | Guardrail: Coaching Only | Bedrock recommendations limited to wellness, time management, team dynamics | Bedrock system prompt | BED-01 |
| LLM-03 | Hallucination Detection | Post-response scanner detects unsupported claims; blocks output if hallucination detected | Python hallucination detector | BED-02 |
| LLM-04 | KB Reference Requirement | Explanations must cite KB documents; bare claims rejected | Bedrock agent RAG setup | BED-02 |
| LLM-05 | Adversarial Input Filter | Prompt injection attempts detected and logged; agent refuses unsafe inputs | Bedrock guardrail + WAF (if applicable) | BED-01 |

### Bias Mitigation Controls (BIAS-*)

| Control ID | Control Name | Enforces | Where | Task |
|------------|--------------|----------|-------|------|
| BIAS-01 | Cohort-Based Normalization | Z-scores computed within cohort only; no cross-cohort comparisons | Lambda feature job | FEAT-02 |
| BIAS-02 | Cohort Context in Alerts | Each alert includes cohort ID and baseline stats for comparison | Lambda rules engine | INT-01 |
| BIAS-03 | Bias Audit (Monthly) | Alert rates compared across cohorts (role, seniority, team) to detect skew | Analyst report (QA-LLM-03) | QA-01 |
| BIAS-04 | Human Review Gate | No automated action taken on alerts; humans review before any HR decision | UI + Audit view | UI-02 |

### Audit & Compliance Controls (AUDIT-*)

| Control ID | Control Name | Enforces | Where | Task |
|------------|--------------|----------|-------|------|
| AUDIT-01 | CloudTrail Audit Trail | All API calls logged with user, timestamp, resource, action | CloudTrail → S3 | OBS-02 |
| AUDIT-02 | HR Audit View | HR role can view all alerts, explanations, KB references, no PII | UI Audit View | UI-02 |
| AUDIT-03 | Incident Logging | Security incidents logged to S3 with timestamp, severity, remediation | Lambda incident logger | PROC-01 onwards |
| AUDIT-04 | Access Log Review | Weekly review of CloudTrail logs for anomalies (suspicious deletions, privilege escalation) | Manual (analyst task) | OBS-01 |

---

## Control Specification: What, Where, How, Evidence

For each control, this section defines enforcement, verification, and evidence.

### SEC-01: IAM Least Privilege

**What is enforced:**
All IAM roles grant only the minimum permissions required for their function. No `*:*` (wildcard) permissions. No cross-service permissions (e.g., Lambda role cannot access Cognito).

**Where it is enforced:**
- IAM policy documents (terraform, CloudFormation)
- Roles: `signalhr-lambda-ingest-role`, `signalhr-lambda-process-role`, `signalhr-lambda-feature-role`, `signalhr-lambda-bedrock-role`, `signalhr-ui-role` (Amplify), `signalhr-stepfunctions-role`

**How it is verified:**
1. Policy document review: Scan all IAM policies for `"*"` in Action or Resource fields
2. AWS Access Analyzer: Run analysis on roles for findings (unintended access)
3. CloudTrail review: Check for denied/error API calls (over-restrictive)
4. Test: Attempt to perform out-of-scope action (e.g., Lambda calling DeleteItem on DynamoDB) → should be denied

**Required Evidence:**
- IAM policy JSON (all 6 roles)
- AWS Access Analyzer report (0 findings required)
- CloudTrail logs showing 0 denied calls (within 24h window)
- Test execution log: "Attempted out-of-scope action, received 403 Denied" ✓

**File paths:**
- Policies: `infrastructure/iam/roles.tf` (or CloudFormation equivalent)
- Evidence: `s3://signalhr-test-reports/qa/SEC-01/` (policy JSON + analyzer report)

---

### SEC-02: KMS Encryption (S3)

**What is enforced:**
All S3 buckets (`signalhr-raw-events-dev`, `signalhr-aggregates-dev`, `signalhr-explanations-dev`, `signalhr-test-reports`) use KMS customer-managed keys for encryption at rest. Keys are rotated annually.

**Where it is enforced:**
- S3 bucket server-side encryption configuration (SSE-KMS)
- KMS key policy allowing S3 service to use the key

**How it is verified:**
1. Describe S3 bucket encryption: `aws s3api get-bucket-encryption --bucket signalhr-raw-events-dev`
2. Verify SSE algorithm is `aws:kms` (not `AES256`)
3. Verify KMS key ARN matches expected key
4. Test: Put object and verify encryption headers show KMS key ID

**Required Evidence:**
- S3 bucket encryption configuration JSON (4 buckets)
- KMS key ARN and rotation status
- Test object metadata showing SSE-KMS headers
- Rotation schedule documentation

**File paths:**
- Config: `infrastructure/s3/buckets.tf`
- Evidence: `s3://signalhr-test-reports/qa/SEC-02/`

---

### SEC-03: KMS Encryption (DynamoDB)

**What is enforced:**
All DynamoDB tables (`AggregatesTable-dev`, `AlertsTable-dev`, `Features-dev`) use KMS customer-managed keys for encryption at rest.

**Where it is enforced:**
- DynamoDB table encryption settings

**How it is verified:**
1. Describe DynamoDB table: `aws dynamodb describe-table --table-name AggregatesTable-dev | jq .Table.SSEDescription`
2. Verify Status = `ENABLED` and SSEType = `KMS`
3. Verify KMS key ARN matches expected key

**Required Evidence:**
- DynamoDB table encryption configuration JSON (3 tables)
- KMS key ARN verification
- Test query showing successful read/write (encrypted at rest)

**File paths:**
- Config: `infrastructure/dynamodb/tables.tf`
- Evidence: `s3://signalhr-test-reports/qa/SEC-03/`

---

### SEC-04: CloudTrail Logging

**What is enforced:**
All API calls to AWS services (API Gateway, EventBridge, SQS, Lambda, DynamoDB, S3, Bedrock, Cognito, IAM) are logged to CloudTrail. Logs are stored in encrypted S3 bucket with immutability enabled (Object Lock).

**Where it is enforced:**
- CloudTrail trail configuration (multi-region)
- S3 bucket for logs with MFA delete + Object Lock

**How it is verified:**
1. Describe CloudTrail trail: `aws cloudtrail describe-trails --trail-name signalhr-trail`
2. Verify Status = `enabled` and IsMultiRegionTrail = `true`
3. Verify S3 bucket exists and has Object Lock enabled
4. Generate test API call (e.g., `aws s3 ls`) and verify it appears in CloudTrail logs within 15 min

**Required Evidence:**
- CloudTrail trail configuration JSON
- S3 bucket configuration (Object Lock status)
- Sample CloudTrail events showing API call logged
- Log integrity (no missing events in time window)

**File paths:**
- Config: `infrastructure/audit/cloudtrail.tf`
- Evidence: `s3://signalhr-test-reports/qa/SEC-04/`

---

### SEC-05: Secret Management

**What is enforced:**
API keys, database passwords, Bedrock API keys, and other secrets are stored in AWS Secrets Manager (or Parameter Store), not in code or environment variables (except references to Secrets Manager).

**Where it is enforced:**
- Lambda environment variables reference Secrets Manager ARNs (not actual values)
- CloudFormation/Terraform parameter files do not contain plaintext secrets

**How it is verified:**
1. Search codebase for hardcoded patterns (API keys, passwords): `grep -r "api_key=\|password=" --include="*.py" --include="*.js" --include="*.tf"`
2. Verify Secrets Manager secrets exist: `aws secretsmanager list-secrets`
3. Verify Lambda environment variables only contain references: `aws lambda get-function-configuration --function-name signalhr-normalize-dev | jq .Environment.Variables`
4. Attempt to access secret: `aws secretsmanager get-secret-value --secret-id signalhr/bedrock-api-key` → should succeed with proper IAM role

**Required Evidence:**
- Codebase grep results showing 0 hardcoded secrets
- Secrets Manager list (secret names only, not values)
- Lambda environment variables JSON (showing ARN references)
- Secret access test log

**File paths:**
- Code: `src/`, `infrastructure/`
- Secrets Manager: AWS console
- Evidence: `s3://signalhr-test-reports/qa/SEC-05/`

---

### SEC-06: Network Isolation

**What is enforced:**
API Gateway is the only public internet entry point. Lambda, DynamoDB, S3, and other backend services have no direct internet exposure. If using VPC, security groups restrict traffic.

**Where it is enforced:**
- API Gateway endpoint (public)
- Lambda security groups (if VPC) → restrict to VPC endpoints only
- DynamoDB access policy → only allow from Lambda role
- S3 bucket policy → only allow from Lambda/API Gateway roles

**How it is verified:**
1. Verify API Gateway is public: `aws apigateway get-stage --rest-api-id <api-id> --stage-name dev | jq .accessLogSetting`
2. Verify Lambda has no internet gateway attached (if VPC): `aws ec2 describe-security-groups --filters Name=group-id,Values=<sg-id> | jq .SecurityGroups[0].IpPermissions`
3. Verify DynamoDB policy restricts to expected principals: `aws dynamodb get-item --table-name AggregatesTable-dev --key ... ` should work from Lambda, fail from internet

**Required Evidence:**
- API Gateway public endpoint URL
- Lambda security group configuration (if VPC)
- DynamoDB bucket policy JSON
- Test: Attempt direct DynamoDB access from internet → should be denied (403)

**File paths:**
- Config: `infrastructure/network/`, `infrastructure/iam/`
- Evidence: `s3://signalhr-test-reports/qa/SEC-06/`

---

### PRIV-01: No Raw Text Storage

**What is enforced:**
EventBridge Pipes transformation and Lambda normalization MUST drop any optional free-text fields (message body, event description, etc.) before writing to S3 or DynamoDB. Only numeric signal counts and metadata are persisted.

**Where it is enforced:**
1. **EventBridge Pipes Transformer:** Input event transformation rules (drop rules for text fields)
2. **Lambda Normalization:** Incoming event validation; reject if text fields present (or drop before writing)

**How it is verified:**
1. Review EventBridge Pipes rule: Check transformer configuration for drop rules
2. Review Lambda code: Confirm no string fields from signalCounts (only numbers)
3. Sample data: Read raw S3 objects and confirm no text fields (only numeric aggregates)
4. Test: Send event with message text → verify it's dropped and not in S3/DynamoDB

**Required Evidence:**
- EventBridge Pipes transformer configuration (drop rules)
- Lambda code snippet (input validation + output schema)
- Sample S3 raw event (JSONL): verify only numeric fields
- Sample DynamoDB aggregate: verify no text fields
- Test execution: "Event with text sent, S3 object verified to contain only numbers" ✓

**File paths:**
- Pipes config: `infrastructure/eventbridge/pipes.tf`
- Lambda: `src/normalize/handler.py` (or equivalent)
- Evidence: `s3://signalhr-test-reports/qa/PRIV-01/`

---

### PRIV-02: No PII in Aggregates

**What is enforced:**
DynamoDB aggregates and S3 snapshots contain only:
- `userId` (opaque UUID, not reversible to email/phone/name)
- `cohortId` (hash of role/seniority/team, not reversible to individuals)
- Numeric signal counts (meetings, messages, PRs, etc.)
- Metadata (week, timestamp, schemaVersion)

NO: email, phone, SSN, name, address, title, department (only opaque cohort ID).

**Where it is enforced:**
- Lambda normalization: Strip PII before write
- DynamoDB table access policy: Restrict to approved roles
- S3 object tagging: Tag sensitive aggregates with `Classification=Aggregate`

**How it is verified:**
1. DynamoDB schema review: Query sample items and list all fields
2. S3 object review: Read sample aggregates and list all fields
3. Regex PII scan: Run PII detector on 100 random items
4. Access test: Attempt to access aggregates from unauthorized role → should be denied

**Required Evidence:**
- DynamoDB item JSON (3 sample items: Alice, Ben, Carol)
- S3 aggregate objects (3 samples)
- PII regex scan report (0 matches required)
- Access test log (unauthorized access rejected)

**File paths:**
- Schema: `docs/02_data_contracts.md` (DC-DDB-AGG-V1)
- Evidence: `s3://signalhr-test-reports/qa/PRIV-02/`

---

### PRIV-03: Opaque User Identifiers

**What is enforced:**
All user IDs in the system are UUIDs or cryptographic hashes, never reversible to email, phone, or name. No user identity exposed in logs, metrics, or dashboards beyond necessary opaque IDs.

**Where it is enforced:**
- API Gateway: Accept `userId` as UUID from client (no email-to-UUID reversal)
- Lambda: Pass-through opaque userId; never decrypt/reverse
- DynamoDB: PK = USER#<opaque-uuid>, never USER#email
- Bedrock: Receive only opaque userId in context (not passed to agent)
- UI: Display only user names from authorized source (not inferred from aggregate data)

**How it is verified:**
1. API schema review: Confirm `userId` field accepts UUID format only
2. Lambda code review: Search for email/phone/name handling → should not exist
3. DynamoDB scan: Verify all PKs match pattern `USER#[a-f0-9-]{36}` (UUID format)
4. Bedrock context review: Verify no userId passed to agent in prompt/context

**Required Evidence:**
- API Gateway request schema (userId field definition)
- Lambda code snippet (userId pass-through, no reversal)
- DynamoDB item PKs (verify UUID pattern)
- Bedrock context log (no userId in agent input)

**File paths:**
- API: `infrastructure/api/openapi.yaml`
- Lambda: `src/normalize/handler.py`
- Evidence: `s3://signalhr-test-reports/qa/PRIV-03/`

---

### PRIV-04: Data Retention Policy

**What is enforced:**
- Raw reduced events: 90-day TTL (in S3 with lifecycle policy)
- Aggregates (DynamoDB): 2-year retention
- Explanations (S3): 1-year retention
- CloudTrail logs: 7-year retention (compliance)

**Where it is enforced:**
- S3 lifecycle policy for raw-events bucket
- DynamoDB TTL attribute for aggregates
- S3 lifecycle policy for explanations bucket
- CloudTrail S3 bucket with Glacier transition

**How it is verified:**
1. S3 lifecycle policy review: Confirm expiration rule for raw events (90 days)
2. DynamoDB TTL check: `aws dynamodb describe-time-to-live --table-name AggregatesTable-dev`
3. S3 lifecycle policy for explanations: Confirm expiration rule (1 year)
4. CloudTrail S3 transition: Verify Glacier transition at 90 days

**Required Evidence:**
- S3 lifecycle policy JSON (2 policies: raw + explanations)
- DynamoDB TTL configuration
- CloudTrail S3 policy (transition rules)
- Retention matrix document

**File paths:**
- S3 policies: `infrastructure/s3/lifecycle.tf`
- DynamoDB: `infrastructure/dynamodb/tables.tf`
- Evidence: `s3://signalhr-test-reports/qa/PRIV-04/`

---

### PRIV-05: Bedrock Input Sanitization

**What is enforced:**
Only non-sensitive data passed to Bedrock:
- Aggregate counts (numeric): meetings, messages, PRs, commits
- Cohort stats: mean, std dev (NOT individual identifiers)
- Feature scores: numeric only
- KB references: only policy/playbook document IDs

NEVER passed to Bedrock:
- userId (opaque or not)
- User name, email, phone
- Raw cohort member lists
- Raw event logs

**Where it is enforced:**
- Lambda function that calls Bedrock (BED-01 task)
- Input sanitization before Bedrock API call

**How it is verified:**
1. Lambda code review: Inspect Bedrock API call; list all fields in input payload
2. Prompt inspection: Verify prompt contains only aggregates and cohort stats, no PII
3. Context inspection: Verify context/RAG retrieval does not leak user IDs
4. Test: Send request with PII in payload → verify it's stripped before Bedrock call

**Required Evidence:**
- Lambda Bedrock wrapper code (sanitization logic)
- Sample API payloads (input to Bedrock, scrubbed fields)
- Bedrock prompt (no PII visible)
- Test log: "PII input stripped before Bedrock call" ✓

**File paths:**
- Lambda: `src/bedrock/explainer.py`
- Evidence: `s3://signalhr-test-reports/qa/PRIV-05/`

---

### PRIV-06: No PII in Explanations

**What is enforced:**
Post-response scanner runs on all Bedrock outputs before they are returned to UI or stored in S3. If PII patterns detected (email, phone, SSN, password), the explanation is:
1. Logged as incident
2. NOT displayed to user
3. Replaced with sanitized fallback text

**Where it is enforced:**
- Lambda function wrapper (after Bedrock response received)
- Regex + heuristic-based PII detector

**How it is verified:**
1. Code review: Inspect post-response scanner logic
2. Test: Generate explanation that (inadvertently) contains email → verify scanner blocks it and logs incident
3. Scanner report: PII detector config (regex patterns for email, phone, SSN, password)
4. Incident log: Verify scan-blocked explanations logged to CloudWatch/S3

**Required Evidence:**
- Lambda wrapper code (post-response filter)
- PII detector configuration (regex patterns)
- Test results: "Explanation with PII detected and blocked" ✓
- Incident log showing blocked explanations (if any)

**File paths:**
- Lambda: `src/bedrock/response_filter.py`
- Evidence: `s3://signalhr-test-reports/qa/PRIV-06/`

---

### PRIV-07: Employee Data Isolation

**What is enforced:**
- **Employee:** UI shows only own aggregates, alerts, explanations (filtered by userId)
- **Manager:** UI shows team aggregates, alerts, explanations (filtered by teamId)
- **HR:** UI shows all alerts, explanations, audit trail (no filtering, read-only)
- **Public API:** No access to any personal/team data

**Where it is enforced:**
- Cognito user pool with 3 groups: Employee, Manager, HR
- Lambda API Gateway authorizer: Validates Cognito token and group membership
- Lambda functions serving dashboard APIs: Apply row-level security filters based on group

**How it is verified:**
1. Cognito pool review: Verify 3 groups created and users assigned correctly
2. Authorizer code review: Verify token validation and group extraction
3. API filter review: Inspect dashboard API Lambda for row-level filters
4. Test (3 scenarios):
   - Employee login: Can see own data, NOT team/org data
   - Manager login: Can see team data, NOT other teams
   - HR login: Can see all data, no filters applied

**Required Evidence:**
- Cognito user pool JSON (3 groups)
- Test user assignments (1 employee, 1 manager, 1 HR)
- Authorizer code (token validation + group extraction)
- Dashboard API code (row-level filters)
- Test results: "Employee sees only own data, Manager sees team, HR sees all" ✓

**File paths:**
- Cognito config: `infrastructure/cognito/`
- Authorizer: `src/api/authorizer.py`
- Dashboard APIs: `src/api/dashboard_api.py`
- Evidence: `s3://signalhr-test-reports/qa/PRIV-07/`

---

### LLM-01: Guardrail: No Punitive Advice

**What is enforced:**
Bedrock agent must NEVER recommend or suggest:
- Firing, demotion, or termination
- Salary reduction or bonus withhold
- Disciplinary action (PIP, write-up)
- Performance rating reduction
- Transfer or exile to undesirable team
- Any action that could be construed as punishment

**Where it is enforced:**
- Bedrock guardrail policy (explicit prohibition in config)
- Post-response scanner (regex for punitive keywords)

**How it is verified:**
1. Bedrock guardrail config review: Verify policy states prohibition on punitive advice
2. Scanner regex review: Verify patterns for firing, demotion, PIP, salary, etc.
3. Test (adversarial): Prompt Bedrock to suggest firing → verify it's blocked or redirected
4. Explanation sample review: Read 20 generated explanations → verify none suggest punitive action

**Required Evidence:**
- Bedrock guardrail policy configuration
- Post-response scanner regex patterns
- Adversarial test: "Attempted to solicit punitive advice, blocked by guardrail" ✓
- Sample explanations (20 cases): "0/20 suggest punitive action" ✓

**File paths:**
- Bedrock guardrails: AWS Bedrock console (or Terraform config)
- Scanner: `src/bedrock/guardrail_filter.py`
- Evidence: `s3://signalhr-test-reports/qa/LLM-01/`

---

### LLM-02: Guardrail: Coaching Only

**What is enforced:**
Bedrock recommendations are limited to:
- Wellness suggestions (exercise, meditation, mental health resources)
- Time management coaching (prioritization, blocking focus time)
- Team communication improvements (1:1 suggestions, meeting effectiveness)
- Learning/development opportunities
- Work-life balance discussions

**Where it is enforced:**
- Bedrock system prompt: Explicitly constrain response type
- KB documents: Curated playbooks on coaching, wellness, team dynamics (NOT HR policies on actions)
- Post-response scanner: Verify output is coaching-style (not prescriptive/actionable)

**How it is verified:**
1. System prompt review: Confirm coaching constraint stated
2. KB document review: Verify documents are playbooks/guides, not HR policies
3. Prompt testing: Ask Bedrock for coaching on overwork → verify suggestions are coaching-style
4. Explanation sample review: 20 explanations → verify all are coaching/suggestive, not prescriptive

**Required Evidence:**
- Bedrock system prompt
- KB document titles and summaries (coaching-focused)
- Test prompt: "Employee with high signals; what coaching would help?" → Verify coaching output
- Sample explanations (20 cases): "20/20 are coaching-style" ✓

**File paths:**
- System prompt: `infrastructure/bedrock/system_prompt.txt`
- KB setup: `infrastructure/bedrock/knowledge_base.md`
- Evidence: `s3://signalhr-test-reports/qa/LLM-02/`

---

### LLM-03: Hallucination Detection

**What is enforced:**
Post-response scanner detects hallucinations (unsupported claims, contradictions, false KB references). If detected, explanation is logged as incident and NOT shown to user.

**Where it is enforced:**
- Lambda response filter (after Bedrock response)
- Hallucination detector (Python, heuristic + manual review)

**How it is verified:**
1. Detector logic review: Understand heuristics (e.g., "claim not in KB", "claim contradicts input data")
2. Test (20 evaluation cases): Generate explanations for known data; detect hallucinations manually
3. Detector accuracy: Verify it catches known hallucinations with >80% precision
4. Incident log: Verify hallucinated explanations logged to S3 for review

**Required Evidence:**
- Hallucination detector code (heuristics + KB reference validator)
- Evaluation dataset (20 cases with ground truth)
- Detection results (precision, recall, F1)
- Incident log (hallucinations detected and logged)

**File paths:**
- Detector: `src/bedrock/hallucination_detector.py`
- Evidence: `s3://signalhr-test-reports/qa/LLM-03/`

---

### LLM-04: KB Reference Requirement

**What is enforced:**
All explanations must cite KB documents. If Bedrock generates explanation without KB reference, it's rejected.

**Where it is enforced:**
- Bedrock agent prompt: Explicitly require KB citation
- Post-response validator: Verify `kb_references` field populated in explanation JSON

**How it is verified:**
1. Agent prompt review: Confirm KB citation requirement stated
2. Agent trace review: Verify agent retrieved documents before generating explanation
3. Output JSON review: Verify `kb_references` list is non-empty
4. Test: Generate explanation → verify `kb_references` field contains document IDs

**Required Evidence:**
- Bedrock agent prompt (KB requirement)
- Agent trace log (document retrieval shown)
- Sample explanations (20 cases): All have `kb_references` populated
- KB coverage report: % of explanations citing ≥1 document

**File paths:**
- Agent prompt: `infrastructure/bedrock/agent_prompt.txt`
- Evidence: `s3://signalhr-test-reports/qa/LLM-04/`

---

### BIAS-01: Cohort-Based Normalization

**What is enforced:**
Z-scores are computed ONLY within cohort (role, seniority, team). No cross-cohort comparisons. Cohort baseline (mu, sigma) calculated from ≥5 users in same cohort; fallback logic for smaller cohorts.

**Where it is enforced:**
- Lambda feature job (z-score calculation)
- Feature store: cohortId included in every record
- Rules engine: Uses cohort-specific thresholds (not global)

**How it is verified:**
1. Feature job code review: Verify z-score formula uses cohort-specific mu/sigma
2. Feature store sample: Verify cohortId present in all records
3. Cohort computation test: Query 2 cohorts with different means; verify z-scores are cohort-relative
4. Cross-cohort test: User A in cohort1 has z=2, same signal counts in cohort2 should have z≠2 (if cohort means differ)

**Required Evidence:**
- Feature job code (z-score formula)
- Feature store samples (3 cohorts): verify cohortId, mu, sigma
- Cohort test results: "User A z-score differs by cohort" ✓
- Fallback logic test: "Cohort with <5 users triggers fallback" ✓

**File paths:**
- Feature job: `src/features/z_score_job.py`
- Evidence: `s3://signalhr-test-reports/qa/BIAS-01/`

---

### BIAS-02: Cohort Context in Alerts

**What is enforced:**
Every alert includes cohort ID and baseline stats (mean, std dev of the cohort). When alert is displayed, context includes "User A's z=2.1 relative to engineer cohort mean=1.2, stdev=0.8".

**Where it is enforced:**
- Lambda rules engine: Include cohort context in alert JSON
- UI dashboard: Display cohort context when showing alert
- Explanation: Reference cohort context when explaining alert

**How it is verified:**
1. Alert JSON schema review: Verify `cohortId`, `cohort_mean`, `cohort_stdev` fields present
2. Alert sample review: 3 sample alerts have cohort context populated
3. UI test: View alert in Manager Dashboard → verify cohort context displayed
4. Explanation test: Generate explanation → verify cohort context included in "Why flagged"

**Required Evidence:**
- Alert JSON schema (fields: cohortId, cohort_mean, cohort_stdev, etc.)
- Sample alerts (3 cases)
- UI screenshot showing cohort context
- Explanation sample (cohort context visible)

**File paths:**
- Rules engine: `src/intelligence/rules_engine.py`
- Evidence: `s3://signalhr-test-reports/qa/BIAS-02/`

---

### BIAS-03: Bias Audit (Monthly)

**What is enforced:**
Monthly analysis comparing alert rates across cohorts (role, seniority, team) to detect potential bias. If significant skew detected (e.g., senior engineers flagged at 2× rate of junior engineers), escalation and investigation required.

**Where it is enforced:**
- Analyst task: Monthly report generation and review
- Evidence: Bias audit report stored in S3

**How it is verified:**
1. Audit report review: Verify report compares alert rates by role, seniority, team
2. Statistical test: Chi-square or similar to identify significant differences
3. Threshold: Alert if ratio > 1.5x (e.g., senior vs junior rates)
4. Investigation: If threshold exceeded, root cause analysis required (code fix or expected)

**Required Evidence:**
- Bias audit report (monthly)
- Alert rate statistics by cohort
- Statistical test results (p-value, ratio)
- Investigation summary (if threshold exceeded)

**File paths:**
- Reports: `s3://signalhr-test-reports/qa/bias_audits/`
- Evidence: `s3://signalhr-test-reports/qa/BIAS-03/`

---

### BIAS-04: Human Review Gate

**What is enforced:**
No automated action taken based on alerts. All alerts are informational only. Humans (managers, HR) review before any HR decision (conversation, PIP, transfer, etc.).

**Where it is enforced:**
- UI design: Alert shows "For manager review — no automated action" disclaimer
- Audit view: HR can review all alerts and approvals
- No API endpoint for auto-action (e.g., no `PATCH /alerts/{id}/auto_approve`)

**How it is verified:**
1. UI review: Verify alert modal includes disclaimer
2. API review: Verify no auto-action endpoints exist
3. Audit view test: Open audit view → verify all alerts show review status (pending, reviewed, etc.)
4. No-action test: Generate alert → verify no system-initiated actions taken (no email to manager without user interaction)

**Required Evidence:**
- UI screenshot showing disclaimer
- API endpoint list (verify no auto-action endpoints)
- Audit view screenshot
- Test log: "Alert created, no automated action triggered" ✓

**File paths:**
- UI: `src/ui/components/AlertModal.tsx`
- API: `src/api/openapi.yaml`
- Evidence: `s3://signalhr-test-reports/qa/BIAS-04/`

---

### AUDIT-01: CloudTrail Audit Trail

**What is enforced:**
All API calls to AWS services are logged to CloudTrail with:
- User identity (Cognito user or IAM role)
- Timestamp (ISO 8601 UTC)
- Resource (bucket, table, API endpoint)
- Action (PutObject, Query, PutItem, etc.)
- Source IP
- Result (success/failure)

**Where it is enforced:**
- CloudTrail trail (multi-region, all services)
- S3 bucket for logs (encrypted, MFA delete, Object Lock)

**How it is verified:**
1. CloudTrail config review: Verify trail enabled and all services included
2. S3 bucket review: Verify encryption, MFA delete, Object Lock enabled
3. Sample event review: Query CloudTrail for recent API call; verify all fields present
4. Completeness test: Perform 10 API actions; verify all 10 appear in CloudTrail within 15 min

**Required Evidence:**
- CloudTrail trail configuration
- S3 bucket configuration (security settings)
- Sample CloudTrail events (10 events with all fields)
- Completeness test log

**File paths:**
- Config: `infrastructure/audit/cloudtrail.tf`
- Evidence: `s3://signalhr-test-reports/qa/AUDIT-01/`

---

### AUDIT-02: HR Audit View

**What is enforced:**
HR role has read-only access to:
- All alerts (across org, all teams)
- All explanations (with KB references)
- Audit trail (user actions, approvals)
- No PII exposed (only opaque userIds and cohort context)

**Where it is enforced:**
- UI Audit View component (HR role only)
- Lambda API (filters applied: HR sees all, employees see own, managers see team)
- Cognito group: HR

**How it is verified:**
1. UI component review: Verify Audit View exists and is HR-only (Cognito group check)
2. API test: Login as HR → query all alerts → verify response includes all alerts
3. PII test: Audit view loaded → scan for email, phone, name → should see only opaque IDs
4. Read-only test: Attempt to modify alert from Audit View → should be denied

**Required Evidence:**
- UI component code (HR check)
- Cognito user assignment (HR user)
- API test results (all alerts returned for HR)
- PII scan results (0 findings)
- Modification denial log

**File paths:**
- UI: `src/ui/views/AuditView.tsx`
- API: `src/api/alerts_api.py`
- Evidence: `s3://signalhr-test-reports/qa/AUDIT-02/`

---

### AUDIT-03: Incident Logging

**What is enforced:**
Security incidents (PII leakage, guardrail violation, unauthorized access) are logged to S3 with:
- Timestamp
- Severity (Critical, High, Medium, Low)
- Description (event, root cause, remediation)
- Affected component (Bedrock, Lambda, DynamoDB, UI, etc.)
- Remediation status (Open, In Progress, Resolved)

**Where it is enforced:**
- Lambda functions: Catch exceptions and log to incident logger
- Bedrock wrapper: Log guardrail violations and PII detections
- CloudWatch: Alarms for incident log growth

**How it is verified:**
1. Incident logger code review: Verify structure and S3 write logic
2. Test incident: Inject test incident (mock PII detection) → verify logged to S3
3. Log format review: Sample incident JSON → verify all required fields
4. Retrievability test: Query incidents by severity/date → verify accessible

**Required Evidence:**
- Incident logger code
- Test incident log entry (S3 object)
- Sample incident JSON
- Query results (incidents retrievable by date/severity)

**File paths:**
- Logger: `src/observability/incident_logger.py`
- Evidence: `s3://signalhr-test-reports/qa/AUDIT-03/`

---

### AUDIT-04: Access Log Review

**What is enforced:**
Weekly review of CloudTrail logs for anomalies:
- Unusual API calls (e.g., DeleteTable, ModifyIamRole)
- Privilege escalation attempts
- Repeated access denials (potential attacks)
- Off-hours access to sensitive resources
- Changes to security settings (KMS, IAM, CloudTrail)

**Where it is enforced:**
- Analyst task: Weekly report generation
- CloudTrail Insights (automated anomaly detection)

**How it is verified:**
1. Review process: Analyst task scheduled weekly
2. Report template: Includes date range, unusual events, decisions (no action vs escalation)
3. Sample report: Verify structure and completeness

**Required Evidence:**
- Weekly access review report (1 sample from MVP period)
- Anomalies identified (if any) and decisions
- CloudTrail Insights config (if using automated detection)

**File paths:**
- Reports: `s3://signalhr-test-reports/audit/weekly_reviews/`
- Evidence: `s3://signalhr-test-reports/qa/AUDIT-04/`

---

## Data Access Matrix (NEW)

This matrix defines who (Actor) can access what (Data Class) and in what context.

| Data Class | Employee (Own User) | Manager (Team) | HR (Org-wide) | Bedrock Agent | System (Lambda) |
|------------|-------------------|-------------------|--------------|---------------|-----------------|
| **Signal** (raw event metadata) | ❌ Denied (not exposed to UI) | ❌ Denied | ❌ Denied | ❌ Denied (PII risk) | ✅ Allowed (normalization) |
| **Aggregate** (counts, z-scores) | ✅ Read own (UI portal) | ✅ Read team (dashboard) | ✅ Read all (audit view) | ✅ Read sanitized (no userId) | ✅ Read/Write (all operations) |
| **Feature** (numeric features, cohort) | ❌ Denied | ❌ Denied | ✅ Read only (audit) | ✅ Read sanitized (no userId) | ✅ Read/Write (scoring) |
| **Alert** (flag, rule triggered) | ✅ Read own (if generated) | ✅ Read team (assigned to manage) | ✅ Read all (audit trail) | ❌ Denied (after explanation generated) | ✅ Read/Write (generation, status) |
| **Explanation** (coaching text, KB refs) | ✅ Read own (if alert assigned) | ✅ Read team (if alert assigned) | ✅ Read all (audit view, no PII) | ✅ Generate (Bedrock agent) | ✅ Read/Write (storage, retrieval) |
| **Audit Log** (user actions, approvals) | ❌ Denied | ❌ Denied | ✅ Read only (HR review) | ❌ Denied | ✅ Write (logging) |
| **KB Documents** (policies, playbooks) | ❌ Denied | ❌ Denied | ✅ Read (HR authority) | ✅ Read (agent retrieval for RAG) | ✅ Read (indexing) |

**Justifications:**
- **Signal** denied to UI actors: Raw event text could contain PII or keystrokes
- **Aggregate** allowed: Only numeric counts and opaque IDs, safe for UI consumption
- **Feature** restricted: Numeric safe, but includes cohort stats (HR audit only)
- **Alert** access tied to ownership/management responsibility
- **Explanation** follows alert access; Bedrock denies after explanation (already generated)
- **Audit Log** HR-only for compliance review
- **KB Documents** HR-controlled (policy authority); Bedrock RAG access for context retrieval

---

## Incident Response (MVP) (NEW)

This section defines how to respond to security and privacy incidents.

### Incident Severity Levels

- **Critical:** PII leaked to external actor or stored in wrong location (e.g., raw text in DynamoDB)
- **High:** Guardrail violation detected (e.g., Bedrock suggests firing), unauthorized access attempt blocked
- **Medium:** Anomalous API pattern (unusual time or frequency), configuration drift detected
- **Low:** Non-actionable warning (e.g., CloudTrail event processed, no action needed)

### Incident Response Workflow

**Step 1: Detection**
- Automated: CloudWatch alarms, Bedrock guardrail violations, PII scanner triggers
- Manual: Weekly CloudTrail review, incident reports from team

**Step 2: Severity Assessment**
- Assign severity level (Critical, High, Medium, Low)
- Determine scope (affect to 1 user, 1 team, entire org)

**Step 3: Immediate Action (Critical only)**
- **PII Leakage:** 
  1. Identify leaked data location (S3 object, DynamoDB item, log file)
  2. Remove from public access immediately (delete object or revoke credentials)
  3. Notify affected users within 24 hours
  4. File incident report to docs/CHANGE_REQUESTS.md
- **Guardrail Violation:**
  1. Block explanation from user (do not display)
  2. Review Bedrock prompt and guardrails immediately
  3. Disable Bedrock agent if violation is critical
  4. File incident report

**Step 4: Investigation**
- Root cause analysis: Why did control fail?
- CloudTrail/logs review: Identify all affected resources/users
- Scope determination: Single incident or systemic issue?

**Step 5: Remediation**
- Code fix: Update Bedrock prompt, guardrails, PII scanner
- Config fix: IAM policy, security group, encryption settings
- Process fix: Add verification step, manual review gate

**Step 6: Verification & Testing**
- Re-run QA tests (QA-UNIT, QA-INT, QA-E2E) to confirm fix
- Generate incident report with findings and remediation proof
- Sign-off by Project Owner before resuming operations

**Step 7: Closure**
- Update docs/CHANGE_REQUESTS.md with CR for the incident and remediation
- File incident summary in s3://signalhr-test-reports/incidents/

### Scenario Playbooks

#### Scenario 1: PII Detected in Bedrock Output

**Detection:** Post-response PII scanner finds email address in explanation.

**Response:**
```
1. Block explanation (do not return to UI)
2. Log incident: severity=Critical, time=<timestamp>, data=<explanation-hash>
3. Review Bedrock prompt: Did prompt mention user email?
4. Review input: Was email in aggregate data passed to Bedrock? (should not be)
5. If input had PII: STOP, file CR for PRIV-05 violation, re-audit all aggregates for PII
6. If prompt leaked email: STOP, re-write prompt without PII, test with 20 cases for PII
7. Verification: Run QA-PRIV-06 again, confirm 0 PII in 20 new explanations
8. Sign-off: Approver confirms fix before resuming
9. Report: docs/CHANGE_REQUESTS.md CR with date, severity, root cause, remediation
```

**Stop Condition:** Do NOT resume BED-02 task until fix verified and approved.

---

#### Scenario 2: Guardrail Violation (Punitive Advice)

**Detection:** Bedrock explanation suggests "consider transferring user to support role" (perceived as demotion).

**Response:**
```
1. Block explanation immediately (do not return to UI)
2. Log incident: severity=High, time=<timestamp>, advice=<text>
3. Review Bedrock system prompt: Is coaching constraint clear?
4. Review KB documents: Do they suggest punitive actions?
5. If prompt unclear: Rewrite with explicit prohibition on transfers/demotions, test with 20 adversarial prompts
6. If KB has punitive content: Remove from KB, re-index
7. Run post-response scanner: Verify regex detects similar phrases in future outputs
8. Test: Generate 20 explanations for high-signal users, verify none suggest transfers/demotions
9. Verification: Run QA-LLM-01 and QA-LLM-02 again, confirm 0 violations
10. Sign-off: Approver confirms fix before resuming
11. Report: docs/CHANGE_REQUESTS.md CR
```

**Stop Condition:** Do NOT resume BED-02 until fix verified and approved.

---

#### Scenario 3: Unauthorized Access Attempt (IAM)

**Detection:** CloudTrail shows failed DeleteTable on AggregatesTable with 5 attempts in 10 min.

**Response:**
```
1. Identify actor: CloudTrail shows which IAM user/role
2. Investigate: Is this legitimate user? Did credentials leak?
3. If legitimate user with wrong permissions: Update IAM policy to remove DeleteTable, notify user
4. If unknown actor: Revoke credentials, enable MFA, audit CloudTrail for other anomalies
5. Verification: Run SEC-01 (IAM least privilege) again, verify role permissions correct
6. Escalation: Report to security team (if external actor)
7. Report: docs/CHANGE_REQUESTS.md CR (if policy change needed)
```

**Stop Condition:** If external actor suspected, HALT and escalate immediately.

---

#### Scenario 4: Data Retention Policy Breach (Config Drift)

**Detection:** Weekly audit log review shows S3 lifecycle policy disabled on raw-events bucket (raw data should expire after 90 days).

**Response:**
```
1. Identify when disabled: CloudTrail shows who/when changed lifecycle policy
2. Identify scope: How much raw data is past 90 days?
3. Remediation: 
   a. Re-enable lifecycle policy immediately
   b. Manually delete raw events older than 90 days
   c. Verify remaining data is within retention window
4. Root cause: Why was policy changed? (operator error, automation failure?)
5. Prevention: Add alert for lifecycle policy changes
6. Verification: Run PRIV-04 test again, confirm lifecycle policy enabled and working
7. Report: docs/CHANGE_REQUESTS.md CR (if config change needed)
```

**Stop Condition:** If >1 year of raw data retained (exceeding retention policy), escalate as High incident.

---

### Incident Report Template

**File:** `s3://signalhr-test-reports/incidents/INCIDENT-<id>-<date>.md`

```markdown
# Incident Report: [Title]

## Overview
- **Incident ID:** INCIDENT-001-2026-02-07
- **Severity:** Critical / High / Medium / Low
- **Detected at:** 2026-02-07T14:32:00Z
- **Detected by:** [Automated scanner / Manual review]
- **Status:** Open / In Progress / Resolved

## Description
[What happened? Which control failed? Impact to users/data?]

## Root Cause
[Why did control fail? Misconfiguration? Code bug? Process failure?]

## Scope
[How many users affected? How much data exposed?]

## Remediation
[What was fixed? Code change? Config change? Process change?]

## Verification
[How was fix verified? QA tests re-run? Manual confirmation?]

## Sign-off
- Remediation by: [name], [timestamp]
- Verified by: [QA team], [timestamp]
- Approved by: [Project Owner], [timestamp]

## Timeline
- Detected: 2026-02-07T14:32:00Z
- Severity assessed: 2026-02-07T14:35:00Z
- Remediation started: 2026-02-07T14:40:00Z
- Verification completed: 2026-02-07T16:00:00Z
- Resolved: 2026-02-07T16:05:00Z
```

---

## Ethics Hard Stops (NEW)

This section defines explicitly forbidden recommendations and mandatory disclaimers.

### Forbidden Outputs (MUST NOT be in Bedrock explanations)

**NEVER recommend or suggest:**
1. Firing, termination, or layoff
2. Demotion, role downgrade, or "lateral move to support role"
3. Salary reduction, bonus withhold, or compensation change
4. Disciplinary action (PIP, write-up, probation, suspension)
5. Negative performance rating or review score
6. Forced vacation or work-from-home (as punishment)
7. Transfer to undesirable team or location
8. Micromanagement tactics or punitive monitoring
9. Mental health diagnosis or clinical treatment recommendations
10. Any action that implies the person is "failing" or "broken"

**INSTEAD, recommend:**
- Wellness support (EAP, fitness, mental health resources)
- Time management coaching (prioritization, focus time, breaks)
- Team communication (1:1 frequency, async vs sync, feedback)
- Workload adjustment discussions (delegate, defer, deprioritize)
- Learning opportunities (upskilling, mentorship, conferences)
- Career development (growth paths, new skills, stretch projects)
- Work-life balance (PTO reminders, boundary-setting, saying no)

---

### Mandatory Disclaimers

**All explanations MUST include the following disclaimer prominently (before coaching suggestions):**

```
⚠️ IMPORTANT: This analysis is FOR MANAGERIAL AWARENESS ONLY. 
It is not a diagnostic assessment, clinical evaluation, or basis for HR action.

This system identifies patterns in work signals (meetings, communications, etc.) 
and provides coaching suggestions to support employee wellness and productivity.

Any HR decision (conversation, resources, adjustments) must:
1. Be based on direct conversation with the employee
2. Consider context beyond these signals
3. Respect individual circumstances and preferences
4. Follow company policies and legal requirements

Managers should review these insights with their manager and HR before taking any action.
```

---

### Evaluation Checklist

Before any explanation is returned to user, verify:

- [ ] No forbidden outputs (10 items above)
- [ ] Recommendations are coaching/supportive, not prescriptive
- [ ] Explanation includes mandatory disclaimer
- [ ] Cohort context included (shows this is relative to peer group, not absolute)
- [ ] Tone is respectful and non-judgmental
- [ ] KB references present (explanation is grounded)
- [ ] No PII in text (names, emails, identifiers)
- [ ] No assumptions beyond data (e.g., "likely depressed" not supported)

**Failure:** If ANY item fails, block explanation and log incident (see Incident Response).

---

## Evidence Retention & Integrity (NEW)

### Storage Locations

| Evidence Type | Location | Retention | Access |
|---------------|----------|-----------|--------|
| Security control tests | `s3://signalhr-test-reports/qa/SEC-*` | 2 years | Project Owner, QA Lead |
| Privacy control tests | `s3://signalhr-test-reports/qa/PRIV-*` | 2 years | Project Owner, QA Lead, Privacy Officer |
| LLM evaluation | `s3://signalhr-test-reports/qa/LLM-*` | 2 years | Project Owner, QA Lead, AI Lead |
| Bias audit reports | `s3://signalhr-test-reports/qa/bias_audits/` | 3 years | Project Owner, HR Lead |
| Incident reports | `s3://signalhr-test-reports/incidents/` | 7 years | Project Owner, Security Lead, Audit |
| CloudTrail logs | `s3://signalhr-cloudtrail-logs/` | 7 years (AWS compliance) | Audit only (restricted IAM) |
| KMS key audit logs | CloudWatch, CloudTrail | 7 years | AWS compliance |

### Checksum & Integrity

All test evidence files must include SHA256 checksum:

**File:** `<test-id>_<timestamp>_CHECKSUM.txt`
```
sha256 <evidence-file>: <hash>
sha256 <evidence-file2>: <hash>
```

**Verification command:**
```bash
cd s3://signalhr-test-reports/qa/<test-id>/
aws s3 cp <test-id>_<timestamp>_CHECKSUM.txt - | sha256sum -c
# Expected: all checksums match ✓
```

### Immutability

Evidence stored in S3 with Object Lock enabled (if critical):
- **S3 buckets with Object Lock:**
  - `signalhr-cloudtrail-logs` (audit logs)
  - `signalhr-test-reports` (test evidence) — optional but recommended

- **MFA Delete:** Enabled on critical evidence buckets (deletion requires MFA token)

- **Versioning:** Enabled on all evidence buckets (cannot overwrite, only add new versions)

---

## Security & Privacy Freeze Rule (Pre-Demo) (NEW)

**Freeze window:** After QA Pass signal (all tests pass, gates green) until demo complete.

### Prohibited During Freeze

1. **Schema changes:** No modifications to data contracts or Aggregate structure
2. **Control changes:** No IAM policy changes, KMS key rotation, security group modifications
3. **Bedrock changes:** No prompt updates, KB document additions/removals, guardrail policy changes
4. **Privacy settings:** No retention policy changes, TTL modifications, encryption key changes
5. **Ethics rules:** No change to forbidden outputs or disclaimer text
6. **Access control:** No Cognito group changes, role assignments, or RBAC policy updates

### Allowed During Freeze

- Bug fixes for critical security incidents (e.g., unintended IAM permission granted)
- Emergency incident response (see Incident Response section)
- Observability improvements (new CloudWatch metrics, log statements) if not changing control behavior
- Documentation updates (docs/)

### Any Prohibited Change Requires

1. **Change Request (CR):** File docs/CHANGE_REQUESTS.md with CR-ID, justification, impact assessment
2. **CR Approval:** Project Owner must approve before change applied
3. **Full Control Re-validation:** All affected control tests (SEC-*, PRIV-*, LLM-*, BIAS-*, AUDIT-*) must be re-run
4. **Security & Privacy Review:** New risk assessment required
5. **Sign-off renewal:** Project Owner must sign-off again after re-validation passes

**Violation consequence:** Demo is considered non-compliant. Evidence invalidated. Incident filed.

---

## Alignment with Other Docs

**This doc (06_security_privacy.md) is aligned with:**
- `docs/00_project_brief.md`: Out of Scope includes "no PII storage"; AI Execution Rules #7 (fail-closed privacy)
- `docs/02_data_contracts.md`: DC-* contracts enforce privacy rules at schema level; Privacy Checklist
- `docs/03_backlog.md`: Tasks (OBS-02, PROC-01, etc.) implement controls
- `docs/04_runbook.md`: Failure Handling Playbook includes PII and guardrail incidents
- `docs/05_qa_strategy.md`: QA controls map to security/privacy tests (SEC-*, PRIV-*, LLM-*)

---

## Summary

This security and privacy framework provides enforceable controls, verifiable evidence, and clear incident response procedures. All 24 controls (SEC, PRIV, LLM, BIAS, AUDIT) are mapped to implementation locations, verification steps, and evidence artifacts. Hard stops prevent proceeding with violations. Freeze rules protect demo integrity post-QA.

No component may circumvent these controls. Any violation triggers incident response and change request workflows.
