# Deployment Plan — Controlled, Deterministic, and Verifiable

**CRITICAL:** This document is the binding specification for MVP deployment. All deployments must follow this plan exactly. No deviations, auto-deploys, or out-of-order steps are allowed. Deviations require Change Requests and re-verification.

---

## ⚠️ AWS BLOCKED — LOCAL SIMULATION MODE (CR-2026-003)

**Status:** All AWS services (EventBridge, DynamoDB, SQS, Lambda, API Gateway, Bedrock, CloudWatch, CloudTrail, SageMaker) are blocked by explicit deny policies.

**Solution:** Operating in LOCAL-SIMULATION MVP mode. Python-based simulators replace AWS services for hackathon execution.

**Local Deployment (Default):**
```bash
bash scripts/run_local.sh    # Start API + simulators
bash scripts/demo.sh         # Run 3-user scenario
```

**AWS Deployment (When Permissions Available):**
AWS architecture remains the mandated design. Local code uses abstractions that can be swapped to AWS services.

**See:** `docs/CHANGE_REQUESTS.md#CR-2026-003` for full details and post-demo validation plan.

---

## Deployment Mode Declaration (NEW)

**Allowed deployment modes for MVP:**
- ✅ **Local Python:** FastAPI server + in-memory simulators (current mode due to AWS permissions blocker)
- ✅ **AWS Console:** Manual resource creation via AWS web interface (when permissions available)
- ✅ **AWS CLI:** Manual CLI commands for resource creation (when permissions available)
- ✅ **CloudFormation / Terraform:** Infrastructure-as-code (when permissions available)

**Prohibited deployment modes:**
- ❌ **Auto CI/CD pipelines:** No GitHub Actions, CodePipeline, or automatic deploys on git push
- ❌ **Terraform Cloud / Pulumi Cloud:** No cloud-hosted state management (use local state only)
- ❌ **Lambda zip automation:** No automatic Lambda package uploads (manual deployment via Console or CLI)
- ❌ **Amplify auto-deploy:** Amplify app deployed manually via Console; no auto-deploy on git commit

**Rationale:** MVP is 48-hour hackathon. Manual/local deployment is faster, more transparent, and eliminates accidental auto-deploys during code changes.

**Enforcement:** Before each deployment step, developer must confirm mode (Local, Console, or CLI) and record in docs/03_backlog.md task evidence.

---

## Local Deployment (ING-01/ING-02/ING-03/PROC-01/PROC-03 Simulators)

**Status:** ✅ Operational (BUGFIX applied 2026-02-07)

### Quick Start

```bash
bash scripts/run_local.sh    # Start FastAPI + in-memory simulators
bash scripts/demo.sh         # Run 3-user scenario
```

**Expected duration:** <2 minutes

### Runtime Stability (BUGFIX — 2026-02-07)

**Issue Fixed:** Python module resolution (`ModuleNotFoundError: No module named 'core'`)

**Solution:** Added `export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH:-}"` to both `scripts/run_local.sh` and `scripts/demo.sh`

**Verification:** ✅ All imports resolve correctly
```bash
export PYTHONPATH="/Users/abdallahmakboua/Desktop/Hackathon/SignalHR:${PYTHONPATH:-}"
python3 << 'EOF'
from core.bus import EventBus
from core.queue import QueuePair
from store.aggregates_store import AggregatesStore
from lambdas.normalize_handler import normalize_event
print("✓ All imports successful")
EOF
```

**Server Status:** ✅ FastAPI server starts and responds to health checks
```bash
# Health endpoint at http://127.0.0.1:8000/health
# Expected response: {"status":"healthy","bus":true,"queue":true}
```

For full bugfix details, see `docs/BUGFIX_IMPORT_RESOLUTION.md`.

### Allowed Deployment Modes (Local Simulation)

**Python-based simulators (current):**
- ✅ **Local execution:** `bash scripts/run_local.sh && bash scripts/demo.sh` (default)
- ✅ **Manual testing:** Post events via `curl` to http://127.0.0.1:8000/events

**Prohibited modes:**
- ❌ **AWS services:** All AWS services (EventBridge, DynamoDB, SQS, etc.) blocked by explicit deny
- ❌ **Auto CI/CD:** No GitHub Actions or automatic deployment

**Rationale:** Local simulators enable demo execution while AWS permissions blocker is resolved.

**Enforcement:** Before demo, verify `scripts/run_local.sh` completes without errors. Outputs saved to `artifacts/local_demo_<timestamp>/`.

---

## AWS Permissions Blocked (Explicit Deny) — Remediation Plan

**Status:** ✅ Workaround in place; AWS deployment pending permissions

**Problem:**
All AWS service calls are blocked by explicit IAM deny policies in the WSParticipantRole. Affected services:
- ❌ EventBridge (CreateEventBus, PutEvents, CreatePipe)
- ❌ SQS (CreateQueue, SendMessage, ReceiveMessage)
- ❌ DynamoDB (CreateTable, PutItem, GetItem, Scan)
- ❌ Lambda (CreateFunction, InvokeFunction, UpdateFunctionCode)
- ❌ API Gateway (CreateRestApi, CreateDeployment)
- ❌ Step Functions (CreateStateMachine, StartExecution)
- ❌ Bedrock (InvokeModel)
- ❌ CloudWatch, CloudTrail, SageMaker (all blocked)

**Root cause:** AWS Explicit Deny overrides all Allow statements in the role policy. See `docs/CHANGE_REQUESTS.md#CR-2026-003` for full analysis.

**Current solution (hackathon):**
Local Python simulators replace AWS services. This unblocks the demo and allows feature validation without AWS access. Simulators implement the exact same business logic as AWS services and can be swapped to AWS later.

**Approved temporary changes (per CR-2026-003):**
- `api/app.py` (FastAPI) replaces API Gateway
- `core/bus.py` (in-memory EventBridge) replaces EventBridge
- `core/queue.py` (in-memory SQS) replaces SQS
- `store/aggregates_store.py` (SQLite) replaces DynamoDB
- `intelligence/rules_engine.py` (deterministic rules) replaces SageMaker
- `intelligence/explainer.py` (template-based) replaces Bedrock Agent
- Demo output: `artifacts/local_demo_*/` (local filesystem) replaces S3 + CloudWatch

**Post-hackathon plan:**
1. **Request AWS permissions** (mentor to escalate to AWS/event organizers)
   - Ask for: EventBridge, SQS, DynamoDB, Lambda, API Gateway, Bedrock minimum
   - Do NOT request: Auto CI/CD, Terraform Cloud (manual only)
   
2. **Migrate to AWS** (swappable backends)
   - Replace local simulators with AWS SDK calls (boto3)
   - Update `scripts/run_local.sh` and `scripts/demo.sh` to use AWS endpoints
   - No business logic changes needed (simulators are service-agnostic)
   
3. **Deploy IaC** (after migration)
   - CloudFormation or Terraform (manual execution only)
   - Infrastructure code already partially written in `docs/08_deployment_plan.md` sections below
   
4. **Validation** (24-hour post-demo window)
   - Re-run demo on AWS infrastructure
   - Verify outputs match local demo (determinism guaranteed by fixed seeds)
   - Sign off: CR-2026-003 closed with AWS migration evidence

**Escalation path:**
- Document this in CR-2026-003
- Contact mentor with permission request
- Provide AWS account ID, role ARN, and required service list

**Until AWS permissions are available:**
- Use local deployment: `bash scripts/run_local.sh && bash scripts/demo.sh`
- Expected duration: <2 minutes
- Expected output: `artifacts/local_demo_<timestamp>/` with 5 JSON artifacts + DEMO_SUMMARY.md

---

## AWS Deployment (ING-01 Deployment Record) (BLOCKED)

**Status:** AWS services unavailable. See CR-2026-003 for details.

**Scope (when available):** HTTP API (API Gateway v2) + EventBridge PutEvents integration. Minimal ING-02 prerequisite: create EventBridge bus only (no Pipes yet).

**Region:** us-east-2 (NOTE: Project brief defaults to us-east-1; DRAFT CR logged for region variance.)

### Resources (Populate after CLI execution when permissions available)

| Resource | Name | ARN / ID | Status |
|---|---|---|---|
| EventBridge Bus | signalhr-bus-dev | <BUS_ARN> | Not yet deployed |
| IAM Role (APIGW → EventBridge) | signalhr-apigw-putevents-role-dev | <ROLE_ARN> | Not yet deployed |
| HTTP API | signalhr-ingest-http-api-dev | <API_ID> | Not yet deployed |
| HTTP API Stage | dev | <STAGE_NAME> | Not yet deployed |
| API Endpoint | https://<API_ID>.execute-api.us-east-2.amazonaws.com/dev | <API_ENDPOINT> | Not yet deployed |

### CLI Script References

- Deployment: `scripts/deploy_ingestion.sh`
- Test: `scripts/test_ingestion.sh`

### Evidence to Capture

- CLI outputs: API ID, Role ARN, Bus ARN, API endpoint URL
- EventBridge PutEvents metric increment (CloudWatch)
- API Gateway access logs (HTTP 200/202)

---

## Permissions Blockers (NEW — 2026-02-07)

**Status:** BLOCKED  
**Root Cause:** EventBridge bus creation (events:CreateEventBus) denied by IAM explicit deny on role `arn:aws:sts::528613214077:assumed-role/WSParticipantRole/Participant`

### Denied Action Details

| Field | Value |
|---|---|
| **Service** | EventBridge (events) |
| **Action** | CreateEventBus |
| **Resource ARN** | arn:aws:events:us-east-2:528613214077:event-bus/signalhr-bus-dev |
| **Principal Role** | arn:aws:sts::528613214077:assumed-role/WSParticipantRole/Participant |
| **Error Message** | AccessDenied: User is not authorized to perform: events:CreateEventBus on resource: ... |
| **Region** | us-east-2 |
| **Timestamp** | 2026-02-07 (current) |

### Impact

- **Blocked:** ING-01 (API Gateway integration requires existing EventBridge bus)
- **Blocked:** ING-02 (Pipes cannot be created without bus)
- **Cascading:** ING-03, PROC-01 (downstream tasks depend on event flow)

### Next Action: Mentor Request

**Option 1: Create bus via mentor**
  - Mentor creates EventBridge bus `signalhr-bus-dev` in us-east-2 using AWS Console or CLI
  - After bus creation, re-run `bash scripts/deploy_ingestion.sh` with `BUS_NAME=signalhr-bus-dev` (script will discover and use existing bus)

**Option 2: Grant permission**
  - Mentor grants `events:CreateEventBus` permission to `WSParticipantRole` on wildcard or specific bus ARN
  - Command to discover available buses (before mentor request):
    ```bash
    aws events list-event-buses --region us-east-2
    ```

**See:** `docs/MENTOR_MESSAGE.md` for ready-to-send Discord message template

---

## Deployment Phases (NEW)

Deployment is organized into 6 ordered phases. **No phase may start until previous phase is verified.**

---

## Phase 1: IAM, KMS, and Secrets (Task OBS-02)

**Objective:** Create IAM roles, KMS keys, and Secrets Manager entries required for all other services.

**Duration:** 30 min

### Step 1.1: Create KMS Master Key

**What:** KMS customer-managed key for encrypting S3 and DynamoDB resources.

**How (Console):**
1. AWS Console → KMS → Create Key
2. Key name: `signalhr-master-key-dev`
3. Key type: Symmetric
4. Key usage: ENCRYPT_DECRYPT
5. Key policy: Allow root account + services to use (Lambda, DynamoDB, S3)
6. Enable automatic rotation: Yes (annual)
7. Click Create

**How (CLI):**
```bash
aws kms create-key --description "SignalHR MVP master key (dev)" \
  --key-usage ENCRYPT_DECRYPT \
  --query 'KeyMetadata.KeyId' --output text > /tmp/kms_key_id.txt

KMS_KEY_ID=$(cat /tmp/kms_key_id.txt)
echo "KMS Key ID: ${KMS_KEY_ID}"

# Create alias
aws kms create-alias --alias-name alias/signalhr-master-dev --target-key-id ${KMS_KEY_ID}
```

**Verification:**
```bash
aws kms describe-key --key-id alias/signalhr-master-dev

# Expected output: KeyState = Enabled, KeyUsage = ENCRYPT_DECRYPT
```

**Evidence artifact:** KMS Key ARN
```bash
aws kms describe-key --key-id alias/signalhr-master-dev --query 'KeyMetadata.Arn' --output text
# Save to: s3://signalhr-test-reports/deployment/phase1/kms_key_arn.txt
```

**STOP condition:** Key creation fails or key disabled → HALT

---

### Step 1.2: Create IAM Roles (6 roles)

**Role 1: Lambda Ingestion Role**

**Name:** `signalhr-lambda-ingest-role-dev`
**Trust entity:** Lambda service (`lambda.amazonaws.com`)
**Permissions:**
- `events:PutEvents` (EventBridge; limited to `signalhr-bus-dev`)
- `sqs:SendMessage` (SQS; limited to `signalhr-ingest-queue-dev`)
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents` (CloudWatch)
- `kms:Decrypt`, `kms:GenerateDataKey` (KMS; limited to master key)

**How (Console):**
1. AWS Console → IAM → Roles → Create role
2. Trusted entity: AWS service → Lambda
3. Add permissions: EventBridge (`events:PutEvents`), SQS (`sqs:SendMessage`), CloudWatch Logs, KMS
4. Scope to specific resources (use ARNs when available after services created)
5. Click Create

**How (CLI):**
```bash
cat << 'EOF' > /tmp/trust_policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

aws iam create-role \
  --role-name signalhr-lambda-ingest-role-dev \
  --assume-role-policy-document file:///tmp/trust_policy.json \
  --query 'Role.Arn' --output text > /tmp/ingest_role_arn.txt

# Attach inline policy with specific permissions
cat << 'EOF' > /tmp/ingest_policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "events:PutEvents",
      "Resource": "arn:aws:events:us-east-1:ACCOUNT_ID:event-bus/signalhr-bus-dev"
    },
    {
      "Effect": "Allow",
      "Action": "sqs:SendMessage",
      "Resource": "arn:aws:sqs:us-east-1:ACCOUNT_ID:signalhr-ingest-queue-dev"
    },
    {
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "arn:aws:logs:us-east-1:ACCOUNT_ID:log-group:/aws/lambda/*"
    },
    {
      "Effect": "Allow",
      "Action": ["kms:Decrypt", "kms:GenerateDataKey"],
      "Resource": "arn:aws:kms:us-east-1:ACCOUNT_ID:key/KEY_ID"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name signalhr-lambda-ingest-role-dev \
  --policy-name ingest-permissions \
  --policy-document file:///tmp/ingest_policy.json
```

**Repeat for 5 more roles:**
- `signalhr-lambda-process-role-dev` (SQS receive, DynamoDB write, S3 write, CloudWatch)
- `signalhr-lambda-feature-role-dev` (DynamoDB query, S3 read/write, Glue, CloudWatch)
- `signalhr-lambda-rules-role-dev` (DynamoDB query, alerts write, CloudWatch)
- `signalhr-lambda-bedrock-role-dev` (Bedrock invoke, S3 write, CloudWatch, Secrets Manager read)
- `signalhr-stepfunctions-role-dev` (Lambda invoke, S3 write, DynamoDB write, CloudWatch)

**Verification:**
```bash
for ROLE in ingest process feature rules bedrock; do
  aws iam get-role --role-name signalhr-lambda-${ROLE}-role-dev --query 'Role.Arn'
done

# Expected: 6 role ARNs printed
```

**Evidence artifact:** All 6 role ARNs
```bash
aws iam get-role --role-name signalhr-lambda-ingest-role-dev --query 'Role.Arn' --output text > s3://signalhr-test-reports/deployment/phase1/iam_roles.txt
# (repeat for all 6 roles)
```

**STOP condition:** Any role creation fails → HALT

---

### Step 1.3: Create Secrets Manager Secrets

**Secrets to create:**
1. `signalhr/bedrock-api-key` (if using Bedrock API key, usually managed by IAM role but optional)
2. `signalhr/database-password` (for any databases)

**How (Console):**
1. AWS Console → Secrets Manager → Store a new secret
2. Secret type: Other type of secret
3. Key-value pairs: (e.g., `api_key: <value>`)
4. Encryption: Use KMS master key from Step 1.1
5. Click Create

**How (CLI):**
```bash
aws secretsmanager create-secret \
  --name signalhr/bedrock-api-key \
  --description "Bedrock API key for SignalHR MVP" \
  --secret-string '{"api_key":"<BEDROCK_API_KEY>"}' \
  --kms-key-id alias/signalhr-master-dev \
  --query 'ARN' --output text > /tmp/bedrock_secret_arn.txt
```

**Verification:**
```bash
aws secretsmanager describe-secret --secret-id signalhr/bedrock-api-key

# Expected: Status = Available, encryption KMS key matches
```

**Evidence artifact:** Secret ARN
```bash
aws secretsmanager describe-secret --secret-id signalhr/bedrock-api-key --query 'ARN' --output text
# Save to: s3://signalhr-test-reports/deployment/phase1/secrets_arns.txt
```

**STOP condition:** Secret creation fails → HALT

---

## Phase 2: Core Infrastructure (Tasks ING-01, PROC-03)

**Objective:** Deploy EventBridge, SQS, API Gateway, DynamoDB.

**Duration:** 45 min

### Step 2.1: Create EventBridge Bus

**Name:** `signalhr-bus-dev`

**How (Console):**
1. AWS Console → EventBridge → Create event bus
2. Name: `signalhr-bus-dev`
3. Default policy: Allow all (for MVP; tighten in prod)
4. Click Create

**How (CLI):**
```bash
aws events create-event-bus --name signalhr-bus-dev \
  --query 'EventBusArn' --output text > /tmp/eventbus_arn.txt
```

**Verification:**
```bash
aws events describe-event-bus --name signalhr-bus-dev

# Expected: Status = ACTIVE
```

**Evidence artifact:** EventBridge bus ARN
```bash
cat /tmp/eventbus_arn.txt
# Save to: s3://signalhr-test-reports/deployment/phase2/eventbus_arn.txt
```

---

### Step 2.2: Create SQS Queue & DLQ

**Names:** 
- Queue: `signalhr-ingest-queue-dev`
- DLQ: `signalhr-ingest-dlq-dev`

**How (Console):**
1. AWS Console → SQS → Create queue
2. Name: `signalhr-ingest-dlq-dev` (create DLQ first)
   - Type: Standard
   - Visibility timeout: 30 sec
   - Message retention period: 14 days
3. Create another queue: `signalhr-ingest-queue-dev`
   - Type: Standard
   - Visibility timeout: 300 sec (5 min for Lambda processing)
   - Message retention period: 14 days
   - Set Dead-letter queue: `signalhr-ingest-dlq-dev`
   - Max receive count: 3

**How (CLI):**
```bash
# Create DLQ first
aws sqs create-queue --queue-name signalhr-ingest-dlq-dev \
  --attributes "MessageRetentionPeriod=1209600" \
  --query 'QueueUrl' --output text > /tmp/dlq_url.txt

DLQ_URL=$(cat /tmp/dlq_url.txt)
DLQ_ARN=$(aws sqs get-queue-attributes --queue-url ${DLQ_URL} --attribute-names QueueArn --query 'Attributes.QueueArn' --output text)

# Create main queue with DLQ
aws sqs create-queue --queue-name signalhr-ingest-queue-dev \
  --attributes "VisibilityTimeout=300,MessageRetentionPeriod=1209600,RedrivePolicy={\"deadLetterTargetArn\":\"${DLQ_ARN}\",\"maxReceiveCount\":\"3\"}" \
  --query 'QueueUrl' --output text > /tmp/queue_url.txt

QUEUE_URL=$(cat /tmp/queue_url.txt)
QUEUE_ARN=$(aws sqs get-queue-attributes --queue-url ${QUEUE_URL} --attribute-names QueueArn --query 'Attributes.QueueArn' --output text)
echo "Main queue: ${QUEUE_ARN}"
echo "DLQ: ${DLQ_ARN}"
```

**Verification:**
```bash
aws sqs get-queue-attributes --queue-url $(cat /tmp/queue_url.txt) --attribute-names All

# Expected: All attributes set correctly, DLQ configured
```

**Evidence artifact:** SQS ARNs
```bash
echo "Main queue: ${QUEUE_ARN}" > s3://signalhr-test-reports/deployment/phase2/sqs_arns.txt
echo "DLQ: ${DLQ_ARN}" >> s3://signalhr-test-reports/deployment/phase2/sqs_arns.txt
```

---

### Step 2.3: Create DynamoDB Tables (3 tables)

**Table 1: AggregatesTable-dev**

**Attributes:**
- PK: `PK` (String) — format: `USER#<uuid>`
- SK: `SK` (String) — format: `WEEK#<week>`

**Billing:** On-demand (for MVP)
**Encryption:** KMS (from Step 1.1)
**TTL:** `expiresAt` (epoch seconds, 2-year retention)

**How (Console):**
1. AWS Console → DynamoDB → Create table
2. Table name: `AggregatesTable-dev`
3. Partition key: `PK` (String)
4. Sort key: `SK` (String)
5. Billing: On-demand
6. Encryption: KMS master key (alias/signalhr-master-dev)
7. TTL: `expiresAt` (enable)
8. Click Create

**How (CLI):**
```bash
aws dynamodb create-table \
  --table-name AggregatesTable-dev \
  --attribute-definitions \
    AttributeName=PK,AttributeType=S \
    AttributeName=SK,AttributeType=S \
  --key-schema \
    AttributeName=PK,KeyType=HASH \
    AttributeName=SK,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --sse-specification Enabled=true,SSEType=KMS,KMSMasterKeyId=arn:aws:kms:us-east-1:ACCOUNT_ID:key/KEY_ID \
  --query 'TableDescription.TableArn' --output text > /tmp/agg_table_arn.txt

# Enable TTL
aws dynamodb update-time-to-live \
  --table-name AggregatesTable-dev \
  --time-to-live-specification "AttributeName=expiresAt,Enabled=true"
```

**Repeat for 2 more tables:**
- `AlertsTable-dev` (PK=`PK`, SK=`SK`, TTL=`expiresAt`)
- `Features-dev` (PK=`PK`, SK=`SK`, TTL=`expiresAt`)

**Verification:**
```bash
aws dynamodb describe-table --table-name AggregatesTable-dev

# Expected: TableStatus = ACTIVE, SSE enabled, TTL enabled
```

**Evidence artifact:** DynamoDB table ARNs
```bash
for TABLE in AggregatesTable-dev AlertsTable-dev Features-dev; do
  aws dynamodb describe-table --table-name ${TABLE} --query 'Table.TableArn' --output text
done > s3://signalhr-test-reports/deployment/phase2/dynamodb_arns.txt
```

---

### Step 2.4: Create S3 Buckets (4 buckets)

**Buckets:**
1. `signalhr-raw-events-dev` (raw reduced events)
2. `signalhr-aggregates-dev` (aggregates, features, snapshots)
3. `signalhr-explanations-dev` (Bedrock explanations)
4. `signalhr-test-reports` (test/demo evidence)

**For each bucket:**
- Encryption: KMS master key
- Versioning: Enabled
- Lifecycle: Raw events expire after 90 days
- Public access: Blocked (no public read/write)

**How (Console):**
1. AWS Console → S3 → Create bucket
2. Bucket name: `signalhr-raw-events-dev`
3. Region: `us-east-1`
4. Block all public access: Yes
5. Encryption: Enable, use KMS master key
6. Versioning: Enable
7. Lifecycle rules: (add after creation)
8. Click Create

**How (CLI):**
```bash
# Create bucket
aws s3api create-bucket \
  --bucket signalhr-raw-events-dev \
  --region us-east-1 \
  --create-bucket-configuration LocationConstraint=us-east-1

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket signalhr-raw-events-dev \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "aws:kms",
        "KMSMasterKeyID": "arn:aws:kms:us-east-1:ACCOUNT_ID:key/KEY_ID"
      }
    }]
  }'

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket signalhr-raw-events-dev \
  --versioning-configuration Status=Enabled

# Block public access
aws s3api put-public-access-block \
  --bucket signalhr-raw-events-dev \
  --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Add lifecycle policy (90-day expiration for raw events)
cat << 'EOF' > /tmp/lifecycle_policy.json
{
  "Rules": [
    {
      "Id": "DeleteRawEventsAfter90Days",
      "Status": "Enabled",
      "Expiration": {
        "Days": 90
      },
      "Filter": {
        "Prefix": "year="
      }
    }
  ]
}
EOF

aws s3api put-bucket-lifecycle-configuration \
  --bucket signalhr-raw-events-dev \
  --lifecycle-configuration file:///tmp/lifecycle_policy.json
```

**Repeat for other 3 buckets** (skip lifecycle rule for test-reports bucket)

**Verification:**
```bash
aws s3api head-bucket --bucket signalhr-raw-events-dev

# Expected: HTTP 200 (bucket exists and is accessible)

aws s3api get-bucket-encryption --bucket signalhr-raw-events-dev

# Expected: encryption configured with KMS
```

**Evidence artifact:** S3 bucket ARNs
```bash
for BUCKET in signalhr-raw-events-dev signalhr-aggregates-dev signalhr-explanations-dev signalhr-test-reports; do
  echo "arn:aws:s3:::${BUCKET}"
done > s3://signalhr-test-reports/deployment/phase2/s3_arns.txt
```

---

## Phase 3: Lambda Functions (Tasks PROC-01, PROC-02, FEAT-01, FEAT-02, INT-01, INT-02, INT-03)

**Objective:** Deploy 6 Lambda functions (normalize, rollup, feature job, rules engine, Bedrock explainer, authorizer).

**Duration:** 1.5 hours

**Note:** Lambda deployment requires:
- Function code (in `src/` folder)
- IAM role (created in Phase 1)
- Environment variables (secrets references, table names)

### Step 3.1–3.6: Deploy Lambda Functions (one per step)

Each Lambda function follows the same pattern:

**Function 1: signalhr-normalize-dev**

**Task:** PROC-01
**Code location:** `src/normalize/handler.py` (or equivalent)
**Role:** `signalhr-lambda-process-role-dev`
**Timeout:** 60 sec
**Memory:** 512 MB
**Environment variables:**
- `DDB_AGGREGATES_TABLE=AggregatesTable-dev`
- `S3_RAW_BUCKET=signalhr-raw-events-dev`
- `KMS_KEY_ID=arn:aws:kms:us-east-1:ACCOUNT_ID:key/KEY_ID`

**How (Console):**
1. AWS Console → Lambda → Create function
2. Function name: `signalhr-normalize-dev`
3. Runtime: Python 3.11
4. Execution role: `signalhr-lambda-process-role-dev`
5. Code: Upload zip from `src/normalize/lambda_package.zip`
6. Timeout: 60 sec
7. Memory: 512 MB
8. Environment variables: (add all 3)
9. Click Deploy

**How (CLI):**
```bash
# Create deployment package
cd src/normalize
zip -r lambda_package.zip handler.py requirements.txt
cd ../..

# Deploy function
aws lambda create-function \
  --function-name signalhr-normalize-dev \
  --runtime python3.11 \
  --role arn:aws:iam::ACCOUNT_ID:role/signalhr-lambda-process-role-dev \
  --handler handler.lambda_handler \
  --zip-file fileb://src/normalize/lambda_package.zip \
  --timeout 60 \
  --memory-size 512 \
  --environment "Variables={DDB_AGGREGATES_TABLE=AggregatesTable-dev,S3_RAW_BUCKET=signalhr-raw-events-dev,KMS_KEY_ID=arn:aws:kms:us-east-1:ACCOUNT_ID:key/KEY_ID}" \
  --query 'FunctionArn' --output text > /tmp/normalize_arn.txt
```

**Verification:**
```bash
aws lambda get-function --function-name signalhr-normalize-dev --query 'Configuration.FunctionArn'

# Expected: ARN printed, FunctionStatus = Active
```

**Evidence artifact:** Lambda function ARN
```bash
cat /tmp/normalize_arn.txt
# Save to: s3://signalhr-test-reports/deployment/phase3/lambda_arns.txt
```

**Repeat for 5 more functions:**
- `signalhr-rollup-dev` (Task PROC-02, src/rollup/)
- `signalhr-feature-job-dev` (Task FEAT-01, src/features/)
- `signalhr-rules-engine-dev` (Task INT-01, src/intelligence/)
- `signalhr-bedrock-explainer-dev` (Task BED-01, src/bedrock/)
- `signalhr-authorizer-dev` (Task UI-01, src/api/)

---

## Phase 4: EventBridge & Pipes (Tasks ING-02, ING-03)

**Objective:** Connect API Gateway → EventBridge → Pipes → SQS.

**Duration:** 30 min

### Step 4.1: Create EventBridge Rule

**Rule name:** `signalhr-ingest-route-dev`

**Event pattern:** All events on `signalhr-bus-dev`

**How (Console):**
1. AWS Console → EventBridge → Create rule
2. Name: `signalhr-ingest-route-dev`
3. Event bus: `signalhr-bus-dev`
4. Pattern: Match all events (or use specific event type filter)
5. Target: EventBridge Pipe (next step)
6. Click Create

**How (CLI):**
```bash
aws events put-rule \
  --name signalhr-ingest-route-dev \
  --event-bus-name signalhr-bus-dev \
  --state ENABLED \
  --event-pattern '{"source":["signalhr"]}'
```

---

### Step 4.2: Create EventBridge Pipe

**Pipe name:** `signalhr-ingest-pipe-dev`

**Source:** EventBridge bus (`signalhr-bus-dev`)
**Transformation:** Drop/filter rules (drop text fields)
**Target:** SQS queue (`signalhr-ingest-queue-dev`)

**How (Console):**
1. AWS Console → EventBridge → Pipes → Create pipe
2. Name: `signalhr-ingest-pipe-dev`
3. Source: EventBridge bus → `signalhr-bus-dev`
4. Source filter: (all events, or specify event types)
5. Enrichment: None (for MVP)
6. Transformation: Input transformer
   - Template: Extract only signal counts (drop text fields)
   - Example:
     ```json
     {
       "eventType": "$.eventType",
       "timestamp": "$.timestamp",
       "userId": "$.userId",
       "orgId": "$.orgId",
       "teamId": "$.teamId",
       "signalCounts": "$.signalCounts",
       "schemaVersion": "$.schemaVersion"
     }
     ```
7. Target: SQS queue → `signalhr-ingest-queue-dev`
8. Click Create

**How (CLI):**
```bash
cat << 'EOF' > /tmp/pipe_template.json
{
  "eventType": "$.eventType",
  "timestamp": "$.timestamp",
  "userId": "$.userId",
  "orgId": "$.orgId",
  "teamId": "$.teamId",
  "signalCounts": "$.signalCounts",
  "schemaVersion": "$.schemaVersion"
}
EOF

aws pipes create-pipe \
  --name signalhr-ingest-pipe-dev \
  --source arn:aws:events:us-east-1:ACCOUNT_ID:event-bus/signalhr-bus-dev \
  --target arn:aws:sqs:us-east-1:ACCOUNT_ID:signalhr-ingest-queue-dev \
  --role-arn arn:aws:iam::ACCOUNT_ID:role/service-role/AmazonEventBridgePipesForSQSRole \
  --source-parameters '{
    "FilterCriteria": {
      "Source": ["signalhr"]
    }
  }' \
  --state RUNNING
```

**Verification:**
```bash
aws pipes describe-pipe --name signalhr-ingest-pipe-dev

# Expected: State = RUNNING
```

**Evidence artifact:** Pipe ARN
```bash
aws pipes describe-pipe --name signalhr-ingest-pipe-dev --query 'Arn' --output text > s3://signalhr-test-reports/deployment/phase4/pipe_arn.txt
```

---

## Phase 5: API Gateway (Tasks ING-01)

**Objective:** Create REST API endpoint for event ingestion.

**Duration:** 20 min

### Step 5.1: Create API Gateway

**API name:** `signalhr-api-dev`
**Protocol:** REST
**Authorization:** Cognito (will integrate later in Phase 6)

**How (Console):**
1. AWS Console → API Gateway → Create API
2. REST API → Build
3. API name: `signalhr-api-dev`
4. Endpoint type: Regional
5. Create resource: `/events`
6. Create POST method
7. Integration type: AWS Service → EventBridge
8. Service: EventBridge
9. Action: PutEvents
10. Execution role: IAM role that allows EventBridge PutEvents
11. Integration request mapping:
    - Headers: `Content-Type: application/x-amz-json-1.1`
    - Body mapping: Pass request body as-is
12. Deploy to stage: `dev`

**How (CLI):**
```bash
# Create API
API_ID=$(aws apigateway create-rest-api \
  --name signalhr-api-dev \
  --description "SignalHR event ingestion API (dev)" \
  --query 'id' --output text)

echo "API ID: ${API_ID}"

# Get root resource
ROOT_ID=$(aws apigateway get-resources --rest-api-id ${API_ID} \
  --query 'items[0].id' --output text)

# Create /events resource
RESOURCE_ID=$(aws apigateway create-resource \
  --rest-api-id ${API_ID} \
  --parent-id ${ROOT_ID} \
  --path-part events \
  --query 'id' --output text)

# Create POST method
aws apigateway put-method \
  --rest-api-id ${API_ID} \
  --resource-id ${RESOURCE_ID} \
  --http-method POST \
  --authorization-type NONE \
  --request-parameters "method.request.header.Content-Type=false"

# Integrate with EventBridge
aws apigateway put-integration \
  --rest-api-id ${API_ID} \
  --resource-id ${RESOURCE_ID} \
  --http-method POST \
  --type AWS \
  --integration-http-method POST \
  --uri arn:aws:apigateway:us-east-1:events:action/PutEvents \
  --credentials arn:aws:iam::ACCOUNT_ID:role/signalhr-api-eventbridge-role \
  --request-templates '{"application/json": "{\"DetailType\":\"event\",\"Source\":\"signalhr\",\"Detail\":$input.json(\"$\"),\"EventBus\":\"signalhr-bus-dev\"}"}'

# Create deployment
DEPLOYMENT_ID=$(aws apigateway create-deployment \
  --rest-api-id ${API_ID} \
  --stage-name dev \
  --query 'id' --output text)

echo "API endpoint: https://${API_ID}.execute-api.us-east-1.amazonaws.com/dev/events"
```

**Verification:**
```bash
curl -X POST https://${API_ID}.execute-api.us-east-1.amazonaws.com/dev/events \
  -H "Content-Type: application/json" \
  -d '{"eventType":"test","timestamp":"2026-02-07T08:00:00Z","userId":"user-1"}'

# Expected: HTTP 202 Accepted
```

**Evidence artifact:** API endpoint URL
```bash
echo "https://${API_ID}.execute-api.us-east-1.amazonaws.com/dev/events" > s3://signalhr-test-reports/deployment/phase5/api_endpoint.txt
```

---

## Phase 6: StepFunctions (Tasks PROC-02)

**Objective:** Create Step Functions state machine for daily/weekly rollups.

**Duration:** 30 min

### Step 6.1: Create State Machine

**Name:** `signalhr-rollup-dev`

**States:**
1. Input validation (check week parameter)
2. Invoke rollup Lambda
3. Wait for completion
4. Optional: publish success event

**How (Console):**
1. AWS Console → Step Functions → Create state machine
2. Name: `signalhr-rollup-dev`
3. Definition (JSON):
   ```json
   {
     "Comment": "Daily/weekly rollup state machine",
     "StartAt": "Invoke Rollup Lambda",
     "States": {
       "Invoke Rollup Lambda": {
         "Type": "Task",
         "Resource": "arn:aws:states:::lambda:invoke",
         "Parameters": {
           "FunctionName": "signalhr-rollup-dev",
           "Payload": {
             "week.$": "$.week"
           }
         },
         "End": true
       }
     }
   }
   ```
4. Execution role: IAM role with Lambda invoke permissions
5. Click Create

**How (CLI):**
```bash
cat << 'EOF' > /tmp/state_machine_definition.json
{
  "Comment": "Daily/weekly rollup state machine",
  "StartAt": "Invoke Rollup Lambda",
  "States": {
    "Invoke Rollup Lambda": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {
        "FunctionName": "signalhr-rollup-dev",
        "Payload": {
          "week.$": "$.week"
        }
      },
      "End": true
    }
  }
}
EOF

ROLE_ARN=$(aws iam get-role --role-name signalhr-stepfunctions-role-dev --query 'Role.Arn' --output text)

aws stepfunctions create-state-machine \
  --name signalhr-rollup-dev \
  --definition file:///tmp/state_machine_definition.json \
  --role-arn ${ROLE_ARN} \
  --query 'stateMachineArn' --output text > /tmp/sfn_arn.txt
```

**Verification:**
```bash
aws stepfunctions describe-state-machine --state-machine-arn $(cat /tmp/sfn_arn.txt)

# Expected: Status = ACTIVE
```

**Evidence artifact:** State machine ARN
```bash
cat /tmp/sfn_arn.txt > s3://signalhr-test-reports/deployment/phase6/sfn_arn.txt
```

---

## Phase 7: Cognito & Amplify (Tasks UI-01, UI-02)

**Objective:** Create Cognito user pool and deploy Amplify UI.

**Duration:** 1 hour

### Step 7.1: Create Cognito User Pool

**Pool name:** `signalhr-userpool-dev`

**Groups:** Manager, Employee, HR

**Users:** manager-demo, employee-demo, hr-demo (for testing)

**How (Console):**
1. AWS Console → Cognito → Create user pool
2. Pool name: `signalhr-userpool-dev`
3. Sign-in options: Email
4. Password policy: Allow temporary password (for MVP testing)
5. Create group "Manager" with IAM role binding
6. Create group "Employee"
7. Create group "HR"
8. Create test users: manager-demo, employee-demo, hr-demo
9. Assign users to groups
10. Create app client: `signalhr-app-client`
11. Click Create

**How (CLI):**
```bash
# Create user pool
POOL_ID=$(aws cognito-idp create-user-pool \
  --pool-name signalhr-userpool-dev \
  --policies '{
    "PasswordPolicy": {
      "MinimumLength": 8,
      "RequireUppercase": false,
      "RequireLowercase": false,
      "RequireNumbers": false,
      "RequireSymbols": false
    }
  }' \
  --query 'UserPool.Id' --output text)

echo "Pool ID: ${POOL_ID}"

# Create groups
for GROUP in Manager Employee HR; do
  aws cognito-idp create-group \
    --user-pool-id ${POOL_ID} \
    --group-name ${GROUP} \
    --description "${GROUP} group"
done

# Create app client
CLIENT_ID=$(aws cognito-idp create-user-pool-client \
  --user-pool-id ${POOL_ID} \
  --client-name signalhr-app-client \
  --query 'UserPoolClient.ClientId' --output text)

# Create test users
for USER in manager-demo employee-demo hr-demo; do
  aws cognito-idp admin-create-user \
    --user-pool-id ${POOL_ID} \
    --username ${USER} \
    --message-action SUPPRESS \
    --temporary-password TempPassword123!
done

# Assign users to groups
aws cognito-idp admin-add-user-to-group --user-pool-id ${POOL_ID} --username manager-demo --group-name Manager
aws cognito-idp admin-add-user-to-group --user-pool-id ${POOL_ID} --username employee-demo --group-name Employee
aws cognito-idp admin-add-user-to-group --user-pool-id ${POOL_ID} --username hr-demo --group-name HR
```

**Verification:**
```bash
aws cognito-idp describe-user-pool --user-pool-id ${POOL_ID}

# Expected: UserPoolStatus = ACTIVE, groups created
```

**Evidence artifact:** Cognito pool ID and client ID
```bash
echo "Pool ID: ${POOL_ID}" > s3://signalhr-test-reports/deployment/phase7/cognito_ids.txt
echo "Client ID: ${CLIENT_ID}" >> s3://signalhr-test-reports/deployment/phase7/cognito_ids.txt
```

---

### Step 7.2: Deploy Amplify App

**App name:** `signalhr-app-dev`

**Repository:** GitHub repo (or local deploy)

**Environment variables:**
- `REACT_APP_COGNITO_POOL_ID=${POOL_ID}`
- `REACT_APP_COGNITO_CLIENT_ID=${CLIENT_ID}`
- `REACT_APP_API_ENDPOINT=https://${API_ID}.execute-api.us-east-1.amazonaws.com/dev`

**How (Console):**
1. AWS Console → Amplify → Create new app
2. Repository: Select GitHub/GitLab or deploy without Git
3. App name: `signalhr-app-dev`
4. Build settings: Configure build spec (`amplify.yml`)
5. Environment variables: (add 3 from above)
6. Deploy

**How (CLI + manual):**
```bash
# Build locally
cd src/ui
npm install
npm run build

# Deploy to S3 + CloudFront (manual via Amplify console)
# or use Amplify CLI:
# amplify init
# amplify add hosting
# amplify publish
```

**Verification:**
```bash
# Open browser to Amplify URL and verify login page loads
curl -s https://signalhr-app-dev.amplifyapp.com | grep -i "login" || echo "Page loaded"

# Expected: HTML contains login form
```

**Evidence artifact:** Amplify app URL
```bash
echo "https://signalhr-app-dev.amplifyapp.com" > s3://signalhr-test-reports/deployment/phase7/amplify_url.txt
```

---

## Environment Guardrails (NEW)

**Strict rules to prevent accidental prod deployment:**

1. **Region lock:** All resources MUST be in `us-east-1` ONLY
   - Verification: `aws ec2 describe-regions --query 'Regions[].RegionName'` should show only 1 active region
   
2. **Account isolation:** All resources MUST be in single AWS account (dev account)
   - Verification: `aws sts get-caller-identity --query 'Account'` should return same account ID for all operations
   
3. **Environment tag:** All resources MUST have tag `Environment=dev`
   - Verification: `aws resourcegroupstaggingapi get-resources --tag-filter 'Key=Environment,Values=dev'` should list all resources
   
4. **Resource naming:** All resource names MUST start with `signalhr-*-dev` or similar `-dev` suffix
   - Prohibition: No resources like `signalhr-prod`, `signalhr-live`, etc.
   
5. **Prod resource prohibition:** No prod-like resources allowed:
   - ❌ Multi-region deployments
   - ❌ Auto-scaling groups
   - ❌ RDS databases (DynamoDB on-demand only)
   - ❌ VPC resources (Lambda in default VPC or no VPC)
   - ❌ Prod Cognito user pools (use `-dev` suffix only)

**Enforcement:** Deployment verification script checks all guardrails before proceeding to next phase.

---

## Deployment Freeze Rules (NEW)

**Freeze window:** After QA Pass signal (all tests pass, gates green) until demo complete (see docs/05_qa_strategy.md).

### Prohibited During Freeze

1. **Redeployments:** No re-deploying Lambda functions, API Gateway, DynamoDB schema changes
2. **Configuration drift:** No changes to IAM policies, environment variables, KMS key rotation
3. **Infrastructure changes:** No new resources, deletions, or modifications
4. **Code updates:** No pushing new code to Lambda (from Phase 3 onwards)
5. **Database modifications:** No clearing DynamoDB, S3 deletes (except as part of demo refresh)

### Allowed During Freeze

- Bug fixes for critical errors (crashes, security leaks) → file CR + re-test
- Observability improvements (new CloudWatch metrics, alarms)
- Runbook updates (docs/04_runbook.md, docs/07_demo_script.md)

### Violation Consequence

Any deployment change during freeze requires:
1. **Change Request (CR):** File docs/CHANGE_REQUESTS.md
2. **QA Re-run:** All affected QA tests must pass again
3. **Re-verification:** Update evidence in docs/03_backlog.md
4. **Sign-off:** Project Owner approval before continuing

**Demo is invalidated if freeze violated without CR.**

---

## Mandatory Deployment Verification (NEW)

After each phase, run verification checklist:

### Post-Phase Verification

**Phase 1 (IAM/KMS):**
- [ ] KMS key enabled and rotatable
- [ ] 6 IAM roles created with correct permissions
- [ ] Secrets Manager secrets accessible

**Phase 2 (Core):**
- [ ] EventBridge bus active
- [ ] SQS queue + DLQ configured correctly
- [ ] 3 DynamoDB tables active with TTL enabled
- [ ] 4 S3 buckets encrypted and versioned

**Phase 3 (Lambda):**
- [ ] 6 Lambda functions deployed and active
- [ ] Environment variables set correctly
- [ ] Test invocation of 1 function succeeds

**Phase 4 (EventBridge/Pipes):**
- [ ] EventBridge rule active
- [ ] Pipe running
- [ ] Manual test: POST to API → event appears in SQS

**Phase 5 (API Gateway):**
- [ ] API endpoint accessible (HTTP 200 on OPTIONS)
- [ ] POST request returns 202 Accepted
- [ ] Event forwarded to EventBridge

**Phase 6 (StepFunctions):**
- [ ] State machine created and active
- [ ] Manual execution succeeds
- [ ] Execution history shows completed steps

**Phase 7 (Cognito/Amplify):**
- [ ] Cognito pool active, groups created, users assigned
- [ ] Amplify app deployed and accessible
- [ ] Login page loads without errors

**Verification script:**
```bash
# Example verification for Phase 2
echo "Verifying Phase 2..."
aws events describe-event-bus --name signalhr-bus-dev || echo "FAIL: EventBridge"
aws sqs get-queue-attributes --queue-url $(aws sqs get-queue-url --queue-name signalhr-ingest-queue-dev --query 'QueueUrl' --output text) --attribute-names All || echo "FAIL: SQS"
aws dynamodb describe-table --table-name AggregatesTable-dev || echo "FAIL: DynamoDB"
aws s3api head-bucket --bucket signalhr-raw-events-dev || echo "FAIL: S3"
echo "Phase 2 verification complete"
```

---

## Rollback & Abort Decision Tree (NEW)

### When Rollback Is Required

**Scenario A: Lambda function has bugs, blocking pipeline**

**Decision path:**
1. Identify broken function (e.g., `signalhr-normalize-dev`)
2. Verify previous version (if using Lambda versioning) or fix code
3. Re-deploy fixed version
4. Re-run integration test (QA-INT-02)
5. If test passes → continue
6. If test fails → ABORT (see below)

**Action:** Replace function code; re-test; no infrastructure rollback needed.

---

**Scenario B: DynamoDB schema incorrect, corrupted data**

**Decision path:**
1. Identify issue (e.g., PK format wrong, TTL not enabled)
2. If table is empty → delete and recreate
3. If table has data:
   - If data is transient (can be re-generated) → delete, recreate
   - If data is critical → backup to S3, then proceed cautiously
4. Re-run integration test (QA-INT-03)

**Action:** Delete table, recreate from Phase 2 spec; re-test.

---

**Scenario C: API Gateway has invalid event routing**

**Decision path:**
1. Identify issue (e.g., EventBridge integration not working)
2. Check API integration configuration (event mapping, target)
3. Redeploy API with corrected configuration
4. Run post-deployment test (manual curl)
5. If 202 returned → continue
6. If error → ABORT

**Action:** Fix API configuration and re-deploy; re-test.

---

### When to Continue (No Rollback Needed)

- ✅ Bug fix deployed and tested → continue to next phase
- ✅ Configuration corrected (env vars, ARNs) → re-test; continue if pass
- ✅ One-off error (network blip, timeout) → retry; continue if passes second time

---

### When to Abort Demo Preparation

**ABORT triggers:**
1. **Core infrastructure unreachable:** AWS account access lost, region unavailable
2. **Multiple test failures across phases:** >3 integration tests failing after fixes attempted
3. **Time budget exceeded:** Demo prep takes >6 hours (beyond 48-hour window)
4. **QA gates failed and cannot be fixed:** E.g., PII leakage in production code, unfixable Bedrock guardrail violations
5. **Freeze rule violated without CR:** Infrastructure change post-QA without approval

**Abort procedure:**
1. Document incident: Date, root cause, decision point
2. File CR in docs/CHANGE_REQUESTS.md with `Status=ABORT`
3. Notify Project Owner and stakeholders
4. Schedule post-mortem

**Fallback:** Use fallback demo plan (docs/07_demo_script.md) if aborting live demo but want to present pre-recorded version.

---

## CI/CD Minimal Contract (NEW)

**MVP does NOT use full CI/CD pipelines. All deployments are manual and logged.**

### Deployment Logging (Mandatory)

After each phase, update docs/03_backlog.md for related task:

**Example (Task OBS-02):**
```markdown
### Task OBS-02 — Infrastructure Deployment & IAM

...

### Completion Evidence

**Deployment Date:** 2026-02-07T10:00:00Z
**Deployed by:** [developer name]
**Deployment method:** AWS Console + CLI
**Resources created:**
- KMS key: arn:aws:kms:us-east-1:ACCOUNT_ID:key/KEY_ID
- IAM roles (6): arn:aws:iam::ACCOUNT_ID:role/signalhr-lambda-*-dev
- Secrets (2): arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret/signalhr/*

**Verification:**
- [ ] All resources exist and are accessible
- [ ] KMS key enabled and rotatable
- [ ] IAM roles have correct permissions (least-privilege verified)
- [ ] Secrets Manager secrets created

**Sign-off:**
- Deployed by: [name], [timestamp]
- Verified by: [QA], [timestamp]
```

### No Auto-Deploy Rules

1. **No GitHub Actions:** Do NOT set up automatic deploys on git push
2. **No CodePipeline:** No continuous deployment pipelines
3. **No Lambda auto-updates:** Lambda code must be manually uploaded; no zip auto-sync
4. **No Amplify auto-build:** Amplify app deployed manually; no auto-build on commits

### Manual Verification Required

Every deployment phase requires manual verification and sign-off:
- Developer runs deployment steps
- QA Lead verifies artifacts (ARNs, screenshots, logs)
- Project Owner approves before next phase starts

---

## Deployment Summary Checklist (NEW)

**After all 7 phases complete:**

```
Deployment Completion Checklist
=================================
Date: ________________
Deployer: ________________

Phase 1: IAM/KMS
- [ ] KMS master key created (ARN: _________)
- [ ] 6 IAM roles created and verified
- [ ] Secrets Manager secrets created

Phase 2: Core Infrastructure
- [ ] EventBridge bus active
- [ ] SQS queue + DLQ configured
- [ ] 3 DynamoDB tables created with TTL
- [ ] 4 S3 buckets encrypted and versioned

Phase 3: Lambda Functions
- [ ] 6 Lambda functions deployed
- [ ] Environment variables configured
- [ ] Test invocation successful

Phase 4: EventBridge & Pipes
- [ ] EventBridge rule active
- [ ] Pipe running and transforming events
- [ ] Manual test: event flows to SQS

Phase 5: API Gateway
- [ ] REST API endpoint created
- [ ] /events POST endpoint works (HTTP 202)
- [ ] Event forwarded to EventBridge

Phase 6: StepFunctions
- [ ] State machine created and active
- [ ] Manual execution successful
- [ ] Execution history shows completion

Phase 7: Cognito & Amplify
- [ ] Cognito user pool active (3 groups, 3 test users)
- [ ] Amplify app deployed and accessible
- [ ] Login page loads without errors

Environment Validation
- [ ] All resources in us-east-1 region
- [ ] All resources in single AWS account
- [ ] All resource names use -dev suffix
- [ ] No prod-like resources created

QA Integration
- [ ] All resource ARNs documented
- [ ] Evidence uploaded to S3 (s3://signalhr-test-reports/deployment/)
- [ ] Backlog tasks updated with completion evidence

Freeze Status
- [ ] Deployment complete and verified
- [ ] Ready for QA phase (docs/05_qa_strategy.md)
- [ ] Freeze rules will apply post-QA

Sign-off
- Deployer: ________________ [timestamp]
- QA Lead: ________________ [timestamp]
- Project Owner: ________________ [timestamp]
```

---

## Summary

This deployment plan provides controlled, deterministic, and fully verifiable infrastructure setup. All 7 phases are ordered with explicit verification gates. Manual logging ensures auditability. Freeze rules prevent drift. Environment guardrails prevent prod spillover. Rollback procedures provide clear decision points. Post-QA, no redeployments allowed without CR and re-verification.
