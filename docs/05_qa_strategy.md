# QA Strategy — Tests, Evaluation Rubric, and Quality Gates

**CRITICAL:** This document is the binding specification for QA execution. All tests, pass/fail criteria, and evidence are enforceable. Deviations require documented Change Requests. No test can transition a task to Done without explicit QA sign-off.

---

## QA Test Index (NEW)

Stable Test IDs organize all QA tests by type and map to Backlog tasks. Each Test ID is immutable; versioning via CR only.

### Unit Tests (QA-UNIT-*)

| Test ID | Test Name | Covers | Backlog Task |
|---------|-----------|--------|--------------|
| QA-UNIT-01 | Normalize event schema validation | Input validation, reject rules, enums/bounds | PROC-01 |
| QA-UNIT-02 | Z-score computation (in-cohort normalization) | Cohort aggregation, z-score formula, edge cases (small cohorts) | FEAT-02 |
| QA-UNIT-03 | Feature extraction (missing signal handling) | Signal aggregation, null/missing field handling, feature selection | FEAT-01 |
| QA-UNIT-04 | Rules engine thresholds | Burnout rule (z > 2), HiPo rule (z > 1.5), alert generation | INT-01 |
| QA-UNIT-05 | Privacy check (no text fields) | Signal counts only, no raw events, no PII in aggregates | PROC-01, PROC-03 |
| QA-UNIT-06 | Dedup logic (ingestionId-based) | Duplicate detection, 7-day window, idempotency | PROC-01 |
| QA-UNIT-07 | Explanation template rendering | JSON schema conformance, safe characters, no injection | BED-01 |
| QA-UNIT-08 | Cohort baseline computation | Mu/sigma calculation, min cohort size=5, fallback logic | FEAT-02 |

### Integration Tests (QA-INT-*)

| Test ID | Test Name | Covers | Backlog Task |
|---------|-----------|--------|--------------|
| QA-INT-01 | API → EventBridge → Pipes → SQS flow | Message transformation, no data loss, DLQ empty | ING-01, ING-02, ING-03 |
| QA-INT-02 | SQS → Lambda normalize → S3 write | Lambda invocation, raw event persistence, checksum match | PROC-01 |
| QA-INT-03 | Lambda normalize → DynamoDB aggregates | DynamoDB write, item schema, timestamp consistency | PROC-01, PROC-03 |
| QA-INT-04 | StepFunctions rollup (daily/weekly) | Execution success, artifact generation, fault handling | PROC-02 |
| QA-INT-05 | Feature job → Feature store | Feature parquet creation, row count ≥ expected, cohort coverage | FEAT-01 |
| QA-INT-06 | Rules engine → Alerts table | Alert creation, only expected users flagged, metadata present | INT-01 |
| QA-INT-07 | Bedrock agent → Explanation storage | Explanation JSON creation, S3 save, no PII leakage | BED-01, BED-02 |
| QA-INT-08 | UI (Cognito) → Dashboard API → DynamoDB | Auth token validation, RBAC enforcement, data filtering | UI-01, UI-02 |

### End-to-End Tests (QA-E2E-*)

| Test ID | Test Name | Covers | Backlog Task |
|---------|-----------|--------|--------------|
| QA-E2E-01 | Full pipeline: generator → API → demo UI | Synthetic generator, all phases, UI rendering | ING-04, PROC-*, FEAT-*, INT-*, BED-*, UI-* |
| QA-E2E-02 | Demo scenario (Alice/Ben/Carol) | Correct alerts, explanations, UI display | DEMO-01 |

### LLM / Bedrock Evaluation Tests (QA-LLM-*)

| Test ID | Test Name | Covers | Backlog Task |
|---------|-----------|--------|--------------|
| QA-LLM-01 | Bedrock guardrail: no PII leakage | Input sanitization, output scanning, regex patterns | BED-01 |
| QA-LLM-02 | Bedrock guardrail: no punitive advice | Prompt constraint, policy enforcement, output rejection | BED-01 |
| QA-LLM-03 | Hallucination detection | Prompt evaluation, KB reference coverage, false claims | BED-02 |
| QA-LLM-04 | KB ingestion: policy/playbook coverage | Documents indexed, searchable, referenced in explanations | BED-02 |

---

## Deterministic Test Dataset (NEW)

All QA tests use fixed, reproducible test data. No randomization or live data.

### Fixed Synthetic Seed

**Generator profile:** `qa-deterministic`
**Fixed users:** 3 personas (same as demo: alice-uuid, ben-uuid, carol-uuid)
**Fixed week:** `2026-W06` (same as demo)
**Fixed timestamps:** Day 2026-02-07, 8 AM UTC (start of workday for 3 events per user per day)
**Determinism guarantee:** Running tests with same seed produces identical events and outputs.

### Golden Test Data (Expected Outputs)

Store in `tests/qa_golden_data/`:

**File:** `tests/qa_golden_data/ingestion_qa_seed.json`
```json
{
  "version": 1,
  "seed": "qa-deterministic",
  "week": "2026-W06",
  "users": [
    {
      "userId": "alice-uuid",
      "orgId": "org-qa",
      "teamId": "eng-team",
      "role": "engineer",
      "seniority": "senior",
      "events": [
        {"eventType": "slack_interaction", "timestamp": "2026-02-07T08:00:00Z", "signalCounts": {"messages": 8, "reactions": 3}},
        {"eventType": "calendar_change", "timestamp": "2026-02-07T08:30:00Z", "signalCounts": {"meetings": 6, "meeting_duration": 240}},
        {"eventType": "pull_request", "timestamp": "2026-02-07T09:00:00Z", "signalCounts": {"prs": 2}}
      ]
    },
    {
      "userId": "ben-uuid",
      "orgId": "org-qa",
      "teamId": "eng-team",
      "role": "engineer",
      "seniority": "junior",
      "events": [
        {"eventType": "slack_interaction", "timestamp": "2026-02-07T08:00:00Z", "signalCounts": {"messages": 3, "reactions": 1}},
        {"eventType": "pull_request", "timestamp": "2026-02-07T08:15:00Z", "signalCounts": {"prs": 3, "commits": 5}},
        {"eventType": "github_issue", "timestamp": "2026-02-07T09:00:00Z", "signalCounts": {"comments": 2}}
      ]
    },
    {
      "userId": "carol-uuid",
      "orgId": "org-qa",
      "teamId": "product",
      "role": "pm",
      "seniority": "mid",
      "events": [
        {"eventType": "calendar_change", "timestamp": "2026-02-07T08:00:00Z", "signalCounts": {"meetings": 2, "meeting_duration": 60}},
        {"eventType": "slack_interaction", "timestamp": "2026-02-07T08:30:00Z", "signalCounts": {"messages": 2}},
        {"eventType": "slack_interaction", "timestamp": "2026-02-07T09:00:00Z", "signalCounts": {"messages": 1, "reactions": 0}}
      ]
    }
  ]
}
```

**File:** `tests/qa_golden_data/expected_aggregates.json`
```json
{
  "week": "2026-W06",
  "aggregates": [
    {
      "userId": "alice-uuid",
      "cohort": "eng-team|engineer|senior",
      "meetings": 6,
      "messages": 8,
      "prs": 2,
      "z_score_meetings": 1.8,
      "z_score_messages": 1.5,
      "z_score_prs": 0.9,
      "composite_z": 1.4,
      "expected_alert": "burnout_flag"
    },
    {
      "userId": "ben-uuid",
      "cohort": "eng-team|engineer|junior",
      "meetings": 0,
      "messages": 3,
      "prs": 3,
      "commits": 5,
      "z_score_prs": 2.1,
      "z_score_commits": 1.9,
      "composite_z": 2.0,
      "expected_alert": "hippo_flag"
    },
    {
      "userId": "carol-uuid",
      "cohort": "product|pm|mid",
      "meetings": 2,
      "messages": 3,
      "prs": 0,
      "z_score_meetings": 0.5,
      "z_score_messages": 0.3,
      "composite_z": 0.4,
      "expected_alert": "none"
    }
  ]
}
```

### Test Data Lifecycle

1. **Golden data stored in repo** (`tests/qa_golden_data/`): Version controlled, immutable except via CR.
2. **Test runner reads golden data** before each test suite.
3. **Expected outputs generated** from golden data (deterministic computation).
4. **Test assertions compare** actual outputs against expected.
5. **If test fails:** Either code is wrong (fix code) or golden data is wrong (file CR to update golden data).

---

## Testing Levels & Scope

### Unit Tests (QA-UNIT-01 through QA-UNIT-08)

**Objective:** Test individual functions in isolation. No AWS calls, no side effects.

**Scope:**
- Input validation (schema, enums, bounds)
- Business logic (z-score, cohort aggregation, rule evaluation)
- Privacy enforcement (no text field persistence)
- Deduplication logic

**Tools:** `pytest` (Python) or `jest` (Node.js) depending on implementation language.

**Execution:** Local dev environment, no AWS credentials required.

**Pass Criteria (all must pass):**
- All unit tests exit with code 0
- Coverage ≥ 70% for modules under test
- No flaky tests (deterministic on repeated runs)

---

### Integration Tests (QA-INT-01 through QA-INT-08)

**Objective:** Test subsystems interacting (Lambda calling DynamoDB, EventBridge routing events, etc.). AWS mocks or dev environment.

**Scope:**
- API Gateway → EventBridge flow
- EventBridge Pipes transformation
- SQS → Lambda → S3/DynamoDB
- StepFunctions rollup job
- Feature job execution
- Rules engine alert generation
- Bedrock agent invocation

**Tools:** AWS SDK + shell scripts (bash/zsh), CloudWatch log polling, DynamoDB/S3 assertions.

**Execution:** Requires AWS credentials and dev infrastructure (`signalhr-*-dev` resources).

**Pass Criteria (all must pass):**
- EventBridge receives all test events (CloudWatch metrics ≥ expected count)
- SQS queue processes all messages (no DLQ entries)
- Lambda normalizes with ≤ 1% error rate
- S3 raw events match ingested events (checksum match)
- DynamoDB aggregates created with correct PK/SK and data
- StepFunctions execution succeeds with ≤ 5 min duration
- Feature store row count ≥ expected
- Alerts created only for expected users
- Bedrock explanations generated and S3-stored

---

### End-to-End Tests (QA-E2E-01, QA-E2E-02)

**Objective:** Test the complete pipeline end-to-end. Data flows from synthetic generator through API, processing, feature extraction, intelligence, Bedrock, to UI.

**Scope:**
- Synthetic generator → API Gateway POST
- Full pipeline execution (all phases from docs/04_runbook.md)
- UI rendering and interaction
- Expected alerts and explanations displayed

**Tools:** Synthetic generator, AWS CLI, browser automation (Selenium or manual screenshots), curl.

**Execution:** Demo environment, full infrastructure required.

**Pass Criteria (all must pass):**
- Generator produces 9 events (3 users × 3 events)
- API returns 202 for all events
- Pipeline completes in ≤ 10 min (all phases)
- DynamoDB has 3 aggregates (Alice, Ben, Carol)
- Alerts created for Alice and Ben (2 total)
- Explanations generated and accessible in S3
- UI dashboard displays all 3 users with correct flags
- Alert details modal shows explanation text
- No raw text visible in UI or explanations

---

## LLM / Bedrock Evaluation Hardening (NEW)

### Hallucination Definition

**Hallucination:** A claim made by Bedrock explanation that is:
1. Not supported by aggregates or cohort statistics in the input data, OR
2. Not derivable from KB documents referenced, OR
3. Contradicts factual data (e.g., "user had 0 meetings" when aggregate shows 6)

**Examples of hallucinations:**
- "User skipped a 2-hour all-hands meeting" (no calendar data in input)
- "This is the 3rd alert for this user in 2 weeks" (no historical comparison in input)
- "User likely suffering from burnout syndrome" (overly diagnostic; should say "signals of overload")

**Examples of acceptable explanations:**
- "User had 6 meetings (z=1.8) and 8 Slack messages (z=1.5), both elevated relative to cohort"
- "In the engineer cohort, typical z-scores are 0.5; this user is 3× higher"

### Evaluation Dataset

**Size:** 20 test cases (4 alerts × 5 variations)

**Composition:**
1. **Baseline alert (Alice burnout):** 5 variations with different signal combinations (high meetings, high messages, mixed)
2. **Growth alert (Ben HiPo):** 5 variations (high PRs, high commits, mixed growth signals)
3. **Non-alert (Carol baseline):** 5 variations (low signals, should not trigger explanations)
4. **Edge cases:** 5 variations (boundary z-scores, small cohorts, missing signals)

**Execution:**
1. For each test case, invoke Bedrock agent with aggregates + feature data.
2. Capture explanation JSON + response timestamp.
3. Run hallucination detector (regex + heuristics).
4. Store results in hallucination report.

### Scoring Method

**Hallucination Rate = (# hallucinated explanations) / (# total explanations) × 100%**

**Pass threshold:** ≤ 5% (i.e., ≤ 1 hallucination in 20 cases)

**Scoring details:**
- Each explanation reviewed manually and by automated regex (PII, unsafe advice, unsupported claims)
- False positives in regex filtered by human review
- Final score: average of manual + automated (consensus score)

### KB Ingestion Verification

**Required:** All policy/playbook documents ingested and searchable.

**Verification steps:**
1. List all documents in OpenSearch/Bedrock KB
2. Verify document count matches source (policies/, playbooks/ folders)
3. Spot-check: ask agent to explain policy on workload management; verify KB reference in response
4. Verify: agent can retrieve and cite specific policies when queried

**Pass criteria:**
- ≥ 90% of source documents indexed
- Agent can retrieve and cite at least 3 policies in explanations
- KB search latency ≤ 2 sec (for guardrail checks)

---

## Pass / Fail / Stop Rules (NEW)

### Test Result States

**PASS:** Test executed, all assertions succeeded, evidence collected.
**FAIL:** Test executed, ≥1 assertion failed, issue identified.
**BLOCKED:** Test cannot execute (prerequisite not met, infrastructure unavailable).
**STOP:** Test result mandates halt of pipeline and CR filing (critical failure).

### Pass Rules (Task can transition to Ready for Review)

**Unit test pass (QA-UNIT-*):**
- Exit code = 0
- Coverage ≥ 70%
- All assertions pass

**Integration test pass (QA-INT-*):**
- All CloudWatch assertions pass (metrics, log counts, error rates)
- All DynamoDB queries return expected data
- All S3 objects exist and checksums match
- No failures or exceptions in service logs

**E2E test pass (QA-E2E-*):**
- All phases complete in order
- UI displays correct data
- Expected alerts and explanations present
- No PII or raw text exposed

**LLM test pass (QA-LLM-*):**
- Hallucination rate ≤ 5%
- PII scan = 0 findings
- KB coverage ≥ 90%
- All guardrail tests pass (no punitive advice, safe responses)

### Fail Rules (Task reverts to In Progress)

**Unit test fail:**
1. Identify failed assertion (code or test is wrong)
2. Developer fixes code (or updates test if golden data wrong)
3. Re-run test in same session
4. If fail persists: STOP (see STOP rules below)

**Integration test fail:**
1. Identify service failure (DynamoDB, Lambda, S3, etc.)
2. Check service logs and CloudWatch for errors
3. If infrastructure issue: file CR and mark task BLOCKED
4. If code issue: developer fixes and re-runs test
5. If test data wrong: update golden data via CR and re-run

**E2E test fail:**
1. Reproduce issue in Phase 0 validation (docs/04_runbook.md)
2. Identify which phase failed
3. Escalate to that phase's task owner
4. Fix and re-run from Phase 0

**LLM test fail:**
1. Hallucination detected: review explanation and KB coverage; adjust prompt/guardrails via CR
2. PII detected: STOP (security incident; see STOP rules)
3. KB coverage low: ingest missing documents and re-run

### STOP Rules (Pipeline halts; CR required)

**Critical failures that mandate immediate halt:**

1. **PII leakage in output** (QA-LLM-01): Explanation contains SSN, email, password, or phone number.
   - Action: Remove from evidence, log incident, escalate to security, file CR for prompt/guardrail fix.

2. **Unit test fails persistently** (QA-UNIT-*): After 2 re-runs with same input, test still fails.
   - Action: File CR describing issue, mark task as Blocked, do not proceed until CR approved.

3. **Integration test infrastructure unavailable** (QA-INT-*): AWS service (DynamoDB, Lambda, S3) not accessible, region down, permissions revoked.
   - Action: File CR, mark task as Blocked, escalate to DevOps, do not retry without infrastructure fix.

4. **E2E test fails in Phase 0 validation** (QA-E2E-*): Environment validation shows resource missing or misconfigured.
   - Action: Do not start demo. File CR for missing resource. Use docs/04_runbook.md Failure Handling Playbook.

5. **Bedrock guardrail breached** (QA-LLM-02): Agent produces punitive advice or unsafe output despite guardrails.
   - Action: STOP. Review Bedrock guardrail configuration, adjust policy constraints via CR, re-run LLM tests.

---

## Quality Gates (Enhanced with Stop Conditions)

### Security Gate (after OBS-02)

**Objective:** Verify IAM policies, KMS encryption, Cognito RBAC are secure.

**Checks:**
1. All roles follow least-privilege (no `*:*` permissions)
2. All S3 buckets encrypted with KMS
3. All DynamoDB tables encrypted
4. Cognito groups enforce RBAC (Manager, Employee, HR)
5. CloudTrail logs all API calls
6. No hardcoded credentials in code or configs

**Pass Criteria:**
- 0 overly permissive policies (warnings = fail)
- 0 unencrypted resources
- RBAC enforced in at least 3 API calls (UI mocking)

**Stop Condition:** If overly permissive policy detected, HALT and file CR to remediate before proceeding.

---

### Privacy Gate (after PROC-03)

**Objective:** Verify no raw text, PII, or keystrokes persisted.

**Checks:**
1. Scan DynamoDB aggregates: no string fields except metadata (userId, cohortId, etc.)
2. Scan S3 raw events: only signalCounts (numeric), no message text or event body
3. Scan explanations: no email, SSN, password, phone numbers
4. Scan feature store: no raw user data, only numeric features

**Pass Criteria:**
- 0 text fields in aggregates (except opaque UUIDs)
- 0 PII patterns matched in explanations
- 100% of numeric signal counts preserved (no loss)

**Stop Condition:** If PII found, STOP. File security incident. Do NOT proceed until privacy audit complete.

---

### Test Coverage Gate (after INT-*)

**Objective:** Verify sufficient test coverage.

**Checks:**
1. Unit tests cover ≥ 70% of Lambda code
2. Integration tests exercise all 4 main pipelines (ingestion, processing, features, intelligence)
3. E2E test runs full demo scenario

**Pass Criteria:**
- Coverage report shows ≥ 70%
- All integration tests pass
- E2E test produces expected alerts and explanations

**Stop Condition:** If coverage < 70% or E2E fails, mark task as Blocked and file CR for code/test improvements.

---

### LLM / Bedrock Gate (after BED-02)

**Objective:** Verify Bedrock agent is safe, accurate, and well-integrated.

**Checks:**
1. LLM eval (QA-LLM-01 through QA-LLM-04) all pass
2. Hallucination rate ≤ 5%
3. PII leakage = 0
4. KB coverage ≥ 90%
5. Response latency ≤ 5 sec (for explanation generation)

**Pass Criteria:**
- All QA-LLM tests pass
- Hallucination report shows ≤ 1 false claim in 20 test cases
- 0 PII findings

**Stop Condition:** If hallucination rate > 5% or PII detected, file CR and re-run tests after prompt/KB adjustments.

---

## Automated Tests & CI

### Unit Test Execution

**Command (Python):**
```bash
cd /repo
python -m pytest tests/unit/ -v --cov=signalhr --cov-report=html
# Output: tests/reports/unit_coverage.html, tests/reports/unit_results.json
```

**Command (Node.js):**
```bash
cd /repo
npm test -- --coverage --testResultsProcessor=jest-junit
# Output: test-results.xml, coverage/
```

**Execution schedule:** On every git push to main branch. Blocks merge if coverage < 70%.

### Integration Test Execution

**Command:**
```bash
cd /repo/tests
bash integration_test_suite.sh --week 2026-W06 --aws-profile default
# Outputs:
#   tests/reports/integration_results.json (CloudWatch metrics, DynamoDB queries, etc.)
#   tests/reports/cloudwatch_logs.txt
#   tests/reports/s3_manifest.json (all S3 objects created)
```

**Prerequisites:** AWS credentials, dev infrastructure deployed.

**Execution schedule:** Before each demo run (Phase 0 validation includes running integration tests).

### E2E Test Execution

**Command:**
```bash
cd /repo/tests
bash e2e_test_demo.sh --seed qa-deterministic --week 2026-W06 --api-endpoint <api-url>
# Outputs:
#   tests/reports/e2e_results.json (all phases, timing, artifacts)
#   tests/reports/e2e_logs.txt (generator + pipeline logs)
#   tests/reports/e2e_ui_screenshots/ (5 screenshots)
```

**Execution schedule:** Before demo day (docs/04_runbook.md Phase 0).

### LLM Evaluation Execution

**Command:**
```bash
cd /repo/tests
python llm_eval_bedrock.py \
  --dataset tests/qa_golden_data/eval_cases.json \
  --kb-endpoint <bedrock-kb-endpoint> \
  --output tests/reports/llm_eval_results.json \
  --hallucination-detector regex+manual
# Outputs:
#   tests/reports/llm_eval_results.json (per-case scoring)
#   tests/reports/llm_hallucination_report.md (narrative findings)
```

**Execution schedule:** Before BED-02 sign-off and before demo.

---

## Evidence Contract (NEW)

### Required Artifacts by Test Type

**Unit Test Evidence:**
- Artifact type: Coverage HTML report + test execution log
- Naming: `qa_unit_<test-id>_<timestamp>.html`, `qa_unit_<test-id>_<timestamp>.log`
- Location: `s3://signalhr-test-reports/qa/<test-id>/`
- Checksum: SHA256 of coverage HTML (verify no tampering)
- Required fields: Test name, # passed, # failed, coverage %, module names

**Integration Test Evidence:**
- Artifact type: JSON results + CloudWatch logs + DynamoDB JSON + S3 manifest
- Naming: `qa_int_<test-id>_<timestamp>.json`, `qa_int_<test-id>_logs.txt`, `qa_int_<test-id>_s3_manifest.json`
- Location: `s3://signalhr-test-reports/qa/<test-id>/`
- Checksum: SHA256 of results JSON
- Required fields: Test name, phase, service, # assertions, pass/fail status, error details

**E2E Test Evidence:**
- Artifact type: Test results JSON + logs + screenshots (5 UI views)
- Naming: `qa_e2e_<test-id>_<timestamp>.json`, `qa_e2e_<test-id>_<timestamp>.log`, `qa_e2e_ui_*.png`
- Location: `s3://signalhr-test-reports/qa/<test-id>/`
- Checksum: SHA256 of results JSON
- Required fields: Test name, all phases, start/end time, # events processed, # alerts created, # explanations

**LLM Eval Evidence:**
- Artifact type: Eval results JSON + hallucination report (markdown) + per-case explanations (JSON)
- Naming: `qa_llm_<test-id>_<timestamp>.json`, `qa_llm_<test-id>_hallucination_report.md`, `qa_llm_cases_*.json`
- Location: `s3://signalhr-test-reports/qa/<test-id>/`
- Checksum: SHA256 of results JSON
- Required fields: Test name, # cases, hallucination rate, PII findings, KB coverage %, pass/fail

### S3 Path Structure

```
s3://signalhr-test-reports/qa/
├── QA-UNIT-01/
│   ├── qa_unit_01_20260207_120000.html (coverage report)
│   ├── qa_unit_01_20260207_120000.log (test log)
│   ├── qa_unit_01_CHECKSUM.txt (SHA256 of HTML)
│   └── qa_unit_01_results.json (summary)
├── QA-INT-01/
│   ├── qa_int_01_20260207_130000.json (results)
│   ├── qa_int_01_20260207_130000.log (service logs)
│   ├── qa_int_01_s3_manifest.json (S3 artifacts created)
│   └── qa_int_01_CHECKSUM.txt
├── QA-E2E-01/
│   ├── qa_e2e_01_20260207_140000.json (results)
│   ├── qa_e2e_01_20260207_140000.log (pipeline logs)
│   ├── qa_e2e_ui_manager_dashboard.png (screenshot)
│   ├── qa_e2e_ui_alert_modal.png
│   ├── qa_e2e_ui_explanation.png
│   ├── qa_e2e_ui_employee_portal.png
│   ├── qa_e2e_ui_audit_view.png
│   └── qa_e2e_01_CHECKSUM.txt
└── QA-LLM-01/
    ├── qa_llm_01_20260207_150000.json (results)
    ├── qa_llm_01_hallucination_report.md (narrative)
    ├── qa_llm_cases_burnout.json (per-case details)
    ├── qa_llm_cases_hippo.json
    ├── qa_llm_cases_baseline.json
    ├── qa_llm_cases_edges.json
    └── qa_llm_01_CHECKSUM.txt
```

### Checksum Verification

**File:** `<test-id>_CHECKSUM.txt`
```
sha256 qa_unit_01_20260207_120000.html: abc123def456...
sha256 qa_unit_01_results.json: xyz789uvw012...
```

**Verification command:**
```bash
cd s3://signalhr-test-reports/qa/QA-UNIT-01/
aws s3 cp qa_unit_01_CHECKSUM.txt - | sha256sum -c
# Expected: all checksums match (✓)
```

---

## QA Ownership & Sign-off (NEW)

### Roles

**QA Executor:** Runs tests, collects evidence, documents failures.
- Responsible for: Running test suite, troubleshooting failures, filing CRs for infrastructure issues.
- Authority: Cannot approve test pass or transition task to Done.
- Signs: Test execution log with timestamp and executor name.

**QA Reviewer:** Reviews test results and evidence, validates that test is not flaky.
- Responsible for: Inspecting test results, confirming assertions are valid, checking evidence completeness.
- Authority: Cannot approve task Done; can request re-run if evidence incomplete.
- Signs: Review checklist (all artifacts present, no blockers detected).

**QA Approver:** Grants final sign-off for task Done or escalates.
- Responsible for: Final gate check, authorization to transition task status.
- Authority: Can approve task → Done or reject → Blocked (with reason).
- Signs: Formal approval with timestamp and approver name.
- Escalation authority: Can file CR if gates failed.

### Sign-off Process

**Step 1: Test Execution (Executor)**
1. Run test suite per specification (docs/05_qa_strategy.md)
2. Collect all evidence artifacts
3. Document any failures or warnings
4. Sign execution log: `Executed by [name], [timestamp]`

**Step 2: Evidence Review (Reviewer)**
```
QA Review Checklist:
- [ ] All artifacts present (coverage report, logs, JSON, screenshots as applicable)
- [ ] All checksums verified (SHA256 match)
- [ ] No artifacts are empty or corrupted
- [ ] Test assertions are clear and measurable
- [ ] Test is deterministic (re-running produces same result)
- [ ] No flaky timeouts or race conditions
- [ ] All stop conditions checked (if any failed, escalate immediately)
- [ ] Evidence links to correct backlog task IDs (docs/03_backlog.md)
- [ ] No PII or sensitive data in artifacts
```
Sign: `Reviewed by [name], [timestamp]. All checks passed.` OR `Rejected: [reason]`

**Step 3: Final Approval (Approver)**
```
QA Approval:
- [ ] All gates passed (Security, Privacy, Coverage, LLM as applicable)
- [ ] No blockers or unresolved failures
- [ ] Evidence complete and verified
- [ ] Task ready to transition to Done (in docs/03_backlog.md)
```
Sign: `Approved by [name], [timestamp]. Task may transition to Done.` OR `Not Approved: [reason]. File CR before re-submission.`

### Mandatory Sign-off Matrix

| Test Type | Executor | Reviewer | Approver | Required? |
|-----------|----------|----------|----------|-----------|
| QA-UNIT-* | Dev | QA Lead | Project Owner | Yes |
| QA-INT-* | Dev | QA Lead | Project Owner | Yes |
| QA-E2E-* | QA/Demo Lead | QA Lead | Project Owner | Yes |
| QA-LLM-* | QA/AI Lead | QA Lead | Project Owner | Yes |

**No task transitions to Done without Approver sign-off in docs/03_backlog.md Completion Evidence field.**

---

## QA Freeze Rules (Pre-Demo) (NEW)

**Freeze window:** After QA Pass signal (all tests pass, gates green) until demo complete.

### Prohibited During Freeze

1. **Schema changes:** No modifications to DC-ING-V1, DC-DDB-AGG-V1, or other contracts.
2. **Prompt changes:** No updates to Bedrock agent prompt or guardrail policies.
3. **Threshold changes:** No adjustment to rules engine thresholds (burnout z > 2, hippo z > 1.5).
4. **Feature changes:** No new features, feature engineering, or ML model retraining.
5. **Code rollbacks:** No reverting commits after QA pass.
6. **Database purges or resets:** No clearing DynamoDB or S3 between QA pass and demo (except as part of demo refresh).

### Allowed During Freeze

- Bug fixes for critical issues only (security, crash, data loss)
- Config changes (Lambda memory, timeout, environment variables) if not affecting test results
- Observability improvements (new CloudWatch metrics, log statements) if not changing behavior
- Documentation updates (docs/, README)

### Any Prohibited Change Requires

1. **Change Request (CR):** File docs/CHANGE_REQUESTS.md with CR-ID, justification, impact assessment.
2. **CR Approval:** Project Owner must approve before change applied.
3. **QA Re-run:** All affected test suites must be re-run after change.
4. **Sign-off renewal:** QA Approver must sign-off again after re-run passes.

**Violation consequence:** Demo is considered non-reproducible. Evidence invalidated. Incident logged.

---

## Reporting

### QA Test Summary Report

After each test suite runs, generate a summary report:

**File:** `s3://signalhr-test-reports/qa/QA_SUMMARY_<timestamp>.md`

```markdown
# QA Test Summary — [Date/Time]

## Overview
- Total tests run: 25
- Tests passed: 24
- Tests failed: 1
- Blockers: 0

## Unit Tests (QA-UNIT-*)
- QA-UNIT-01: PASS (coverage 75%)
- QA-UNIT-02: PASS (coverage 82%)
- QA-UNIT-03: FAIL (edge case: small cohort < 5 users)
  - Action: File CR to adjust fallback logic
  - Re-run scheduled: [date]

## Integration Tests (QA-INT-*)
- QA-INT-01: PASS (15 events, 0 DLQ)
- QA-INT-02: PASS (Lambda latency 187ms, ✓ < 200ms)
- QA-INT-03: PASS (3 DynamoDB items created)
- QA-INT-04: PASS (StepFunction completed in 3m 45s)
- ... (all others pass)

## End-to-End Tests (QA-E2E-*)
- QA-E2E-01: PASS (full pipeline, 2 alerts, 2 explanations)
- QA-E2E-02: PASS (demo scenario verified)

## LLM Evaluation (QA-LLM-*)
- QA-LLM-01: PASS (0 PII findings)
- QA-LLM-02: PASS (guardrails enforced, no punitive advice)
- QA-LLM-03: PASS (2% hallucination rate, < 5% threshold ✓)
- QA-LLM-04: PASS (KB coverage 96%)

## Gates
- Security Gate: PASS
- Privacy Gate: PASS
- Coverage Gate: PASS (72% overall)
- LLM Gate: PASS

## Artifacts
- All evidence stored in s3://signalhr-test-reports/qa/
- Checksums verified: 21/21 ✓
- Screenshots captured: 5/5 ✓

## Sign-off
- Executor: [name], [timestamp]
- Reviewer: [name], [timestamp]
- Approver: [name], [timestamp]

## Next Steps
1. Fix QA-UNIT-03 (CR filed)
2. Re-run unit tests after CR approval
3. Proceed to demo (all other gates green)
```

### Evidence Linkage to Backlog

After QA passes, update docs/03_backlog.md for each task:

```markdown
## Task: PROC-01 — Lambda Normalization

...

### Completion Evidence
- Evidence collected on 2026-02-07T13:00:00Z
- QA tests: QA-UNIT-01, QA-INT-02, QA-INT-03, QA-E2E-01
- Test artifacts: s3://signalhr-test-reports/qa/QA-INT-02/, s3://signalhr-test-reports/qa/QA-INT-03/
- Key metrics:
  - Lambda latency: 187ms (< 200ms ✓)
  - Error rate: 0.1% (< 1% ✓)
  - Coverage: 78% (> 70% ✓)
- Approver sign-off: [approver name], [timestamp]
```

---

## Summary

This QA strategy provides enforceable, deterministic, and comprehensive quality assurance for the SignalHR MVP. All tests are mapped to backlog tasks, all evidence is collected and verified, all gates are explicit, and all sign-offs are mandatory. No task transitions to Done without QA Approver authorization and evidence linkage in docs/03_backlog.md.
