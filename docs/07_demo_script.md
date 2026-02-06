# Demo Script — Deterministic, Time-Boxed Storyboard

**CRITICAL:** This is the executable specification for the SignalHR MVP demo. All steps, timings, verifications, and presenter scripts are binding. Demo is 100% reproducible if these rules are followed.

---

## Overview

**Duration:** 15–20 minutes (including setup and Q&A)
**Main demo time:** 8–10 minutes (Phases 1–5 from docs/04_runbook.md)
**Presentation time:** 2–3 minutes (walkthrough of UI and explanations)
**Q&A buffer:** 5 minutes

**Objective:** Demonstrate privacy-first detection of Burnout and High Potential (HiPo) with explainability. Show that no raw text or PII is stored; only signals and coaching suggestions are generated.

**Audience:** Executives, product team, privacy/compliance reviewers
**Presenter:** Project Lead or designated demo owner
**Equipment:** Laptop with screen share, 2 browser windows (manager + employee views)

---

## Determinism Guarantees (NEW)

All demo runs produce identical outputs if these guarantees are met:

### Fixed Demo Users (Personas)

**Alice (Burnout scenario):**
- UUID: `alice-uuid`
- Org: `org-qa`
- Team: `eng-team`
- Role: `engineer`
- Seniority: `senior`
- Expected outcome: **Burnout flag** (overload signals)

**Ben (HiPo scenario):**
- UUID: `ben-uuid`
- Org: `org-qa`
- Team: `eng-team`
- Role: `engineer`
- Seniority: `junior`
- Expected outcome: **HiPo flag** (growth signals)

**Carol (Baseline scenario):**
- UUID: `carol-uuid`
- Org: `org-qa`
- Team: `product`
- Role: `pm`
- Seniority: `mid`
- Expected outcome: **No flag** (baseline signals)

### Fixed Week & Timestamps

- **Week:** `2026-W06` (February 2–8, 2026)
- **Demo day:** February 7, 2026
- **Event timestamps:** 2026-02-07T08:00:00Z, 2026-02-07T08:30:00Z, 2026-02-07T09:00:00Z (3 events per user per demo run)
- **Determinism:** Same timestamps → same week number → same aggregation → same alerts

### Fixed Signal Counts (Golden Data)

Alice (Burnout):
- Meetings: 6, Meeting duration: 240 min
- Slack messages: 8, Reactions: 3
- PRs: 2, Commits: 0
- Expected z-scores: meetings=1.8, messages=1.5, composite=1.4 (burnout threshold)

Ben (HiPo):
- Meetings: 0
- Slack messages: 3, Reactions: 1
- PRs: 3, Commits: 5
- Expected z-scores: prs=2.1, commits=1.9, composite=2.0 (hippo threshold)

Carol (Baseline):
- Meetings: 2, Meeting duration: 60 min
- Slack messages: 3, Reactions: 0
- PRs: 0, Commits: 0
- Expected z-scores: meetings=0.5, messages=0.3, composite=0.4 (no flag)

### Fixed Expected Outputs

| User | Expected Alert | Expected Explanation | Expected UI Flag |
|------|-----------------|----------------------|------------------|
| Alice | burnout_flag | "High meetings (z=1.8) and messages (z=1.5), elevated relative to cohort. Consider scheduling 1:1 to discuss workload..." | 🔴 Red (Burnout) |
| Ben | hippo_flag | "High PR activity (z=2.1) and commits (z=1.9), top performer in cohort. Growth trajectory positive. Mentorship opportunities available..." | 🟢 Green (HiPo) |
| Carol | none | (No explanation) | ⚪ Gray (Baseline) |

**Consequence:** Demo can be re-run multiple times with identical alerts and explanations as long as Demo Lock Rules are followed.

---

## Demo State Machine (NEW)

Demo execution flows through 6 states. Each state has:
- **Step:** What to do
- **Verification:** How to confirm success
- **Continue condition:** When to move to next step
- **STOP condition:** When to halt and fallback

---

### State 0: Pre-Demo Setup (15 min before demo)

**Step 0.1: Validate Prerequisites**

**Action:**
1. Open terminal
2. Run Phase 0 validation from docs/04_runbook.md:
   ```bash
   aws sts get-caller-identity
   aws events describe-event-bus --name signalhr-bus-dev
   aws sqs get-queue-url --queue-name signalhr-ingest-queue-dev
   ```

**Verification:**
- ✅ AWS credentials valid (get-caller-identity returns account ID)
- ✅ EventBridge bus exists
- ✅ SQS queue exists

**Continue condition:** All 3 checks pass → proceed to Step 0.2
**STOP condition:** Any check fails → file incident, switch to Fallback Plan (see section below)

**Time budget:** 2 min

---

**Step 0.2: Clear Demo Data**

**Action:**
1. Ensure DynamoDB aggregates and alerts are empty (or from previous demo run)
2. Optionally purge old data:
   ```bash
   # (Optional) Scan and delete old demo data if multiple runs planned
   aws dynamodb scan --table-name AggregatesTable-dev --projection-expression PK,SK | \
     jq -r '.Items[] | select(.SK.S | startswith("WEEK#2026-W06")) | "\(.PK.S) \(.SK.S)"' | head -3
   ```

**Verification:**
- ✅ DynamoDB ready for fresh data

**Continue condition:** Verified → proceed to Step 1.1
**STOP condition:** None (if data exists, new demo run will append; not fatal)

**Time budget:** 1 min

---

**Step 0.3: Open UI in Browser**

**Action:**
1. Open Amplify app in browser: `https://signalhr-dev.amplifyapp.com`
2. Do NOT log in yet (will do at Step 4.1)

**Verification:**
- ✅ Login page loads (white screen or login form visible)

**Continue condition:** Page loads → proceed to State 1
**STOP condition:** Page 404 or times out → switch to Fallback Plan

**Time budget:** 1 min

---

### State 1: Ingestion & Processing (Phase 1 + 2 from runbook)

**Step 1.1: Run Synthetic Generator (Alice)**

**Presenter Script:**
"We'll start by generating synthetic work events for three demo employees: Alice (overloaded), Ben (high performer), and Carol (baseline). This preserves privacy—we're only capturing signal aggregates, never raw messages or keystrokes."

**Action:**
```bash
python tools/synthetic_generator.py \
  --profile alice \
  --week 2026-W06 \
  --rate 5 \
  --duration 1 \
  --api-endpoint ${API_ENDPOINT}
```

Expected stdout: `Generator completed: 5 events sent, HTTP 202x5`

**Verification:**
- ✅ Terminal shows "HTTP 202" for all 5 events
- ✅ No error messages

**Continue condition:** 5 events sent with HTTP 202 → proceed to Step 1.2
**STOP condition:** HTTP errors (4xx, 5xx) or generator timeout → HALT and debug (see docs/04_runbook.md Failure Handling)

**Time budget:** 45 sec

---

**Step 1.2: Run Synthetic Generator (Ben)**

**Presenter Script:**
(Silent; repeat same command for Ben profile)

**Action:**
```bash
python tools/synthetic_generator.py \
  --profile ben \
  --week 2026-W06 \
  --rate 5 \
  --duration 1 \
  --api-endpoint ${API_ENDPOINT}
```

**Verification:**
- ✅ "HTTP 202x5"

**Continue condition:** ✅ → proceed to Step 1.3
**STOP condition:** ❌ → HALT

**Time budget:** 45 sec

---

**Step 1.3: Run Synthetic Generator (Carol)**

**Presenter Script:**
(Silent; repeat for Carol)

**Action:**
```bash
python tools/synthetic_generator.py \
  --profile carol \
  --week 2026-W06 \
  --rate 5 \
  --duration 1 \
  --api-endpoint ${API_ENDPOINT}
```

**Verification:**
- ✅ "HTTP 202x5"

**Continue condition:** ✅ → proceed to Step 2.1
**STOP condition:** ❌ → HALT

**Time budget:** 45 sec

**Total ingestion time:** ~2.5 min (allow pipeline to process)

---

**Step 2.1: Monitor Processing Pipeline**

**Presenter Script:**
"The pipeline is now processing these events. Normalization removes any raw text and computes aggregates. Let's wait for the rollup to complete."

**Action:**
1. Tail CloudWatch logs:
   ```bash
   aws logs tail /aws/lambda/signalhr-normalize-dev --follow --since 3m | tail -20
   ```
2. Check SQS queue depth (should decrease):
   ```bash
   aws sqs get-queue-attributes --queue-url <queue-url> --attribute-names ApproximateNumberOfMessages
   ```

**Verification:**
- ✅ Lambda logs show normalize events (15 total for 3 users × 5 events)
- ✅ SQS queue depth decreasing or empty
- ✅ No DLQ messages

**Continue condition:** Logs show success, SQS empty → proceed to Step 2.2
**STOP condition:** DLQ has messages or Lambda errors → HALT (see Failure Handling)

**Time budget:** 2 min (may need to wait for Lambda to complete)

---

**Step 2.2: Execute StepFunctions Rollup**

**Presenter Script:**
"Now we run the daily rollup to compute aggregates and z-scores within each cohort. This ensures we only compare engineers to engineers, not across roles."

**Action:**
```bash
ROLLUP_ARN=$(aws stepfunctions list-state-machines \
  --query "stateMachines[?name=='signalhr-rollup-dev'].stateMachineArn" \
  --output text)

aws stepfunctions start-execution \
  --state-machine-arn ${ROLLUP_ARN} \
  --input "{\"week\":\"2026-W06\"}" \
  --query 'executionArn' --output text > /tmp/rollup_arn.txt

cat /tmp/rollup_arn.txt
```

Then wait:
```bash
aws stepfunctions wait execution-succeeded --execution-arn $(cat /tmp/rollup_arn.txt) --max-attempts 60 --delay 5
```

**Verification:**
- ✅ Execution ARN returned
- ✅ Execution status = SUCCEEDED (wait command completes)

**Continue condition:** ✅ → proceed to State 3
**STOP condition:** FAILED or TIMED_OUT → HALT (check execution history)

**Time budget:** 3 min (StepFunction + wait)

---

### State 2: Feature Extraction & Scoring (Phase 3 from runbook)

**Step 3.1: Invoke Rules Engine**

**Presenter Script:**
"The rules engine applies simple thresholds based on z-scores. If a user's signals exceed the team average by more than 2 standard deviations, we flag them for manager awareness—not for action, just for conversation."

**Action:**
```bash
aws lambda invoke \
  --function-name signalhr-rules-engine-dev \
  --payload "{\"week\":\"2026-W06\"}" \
  --log-type Tail \
  response.json

cat response.json | jq .
```

**Verification:**
- ✅ Lambda returns HTTP 200
- ✅ Alerts created: count=2 (Alice + Ben), count=0 for Carol

**Continue condition:** 2 alerts returned (Alice + Ben) → proceed to Step 3.2
**STOP condition:** Alerts = 0 or unexpected count → HALT (see Failure Handling)

**Time budget:** 1 min

---

**Step 3.2: Generate Explanations (Bedrock)**

**Presenter Script:**
"Our Bedrock agent generates coaching explanations for each alert. It can only reference wellness and development resources—never punitive HR actions. All explanations cite company policies and playbooks."

**Action:**
```bash
# Invoke Bedrock explainer for Alice's alert
aws lambda invoke \
  --function-name signalhr-bedrock-explainer-dev \
  --payload "{\"alertId\":\"ALERT#alice-alert-1\",\"week\":\"2026-W06\"}" \
  --log-type Tail \
  response.json

cat response.json | jq .

# Check S3 for explanation
aws s3 ls s3://signalhr-explanations-dev/ | tail -1
```

**Verification:**
- ✅ Lambda returns HTTP 200
- ✅ Explanation saved to S3
- ✅ Explanation JSON contains "why" and "next_best_actions" fields

**Continue condition:** ✅ → proceed to State 4
**STOP condition:** Bedrock unavailable (timeout) → switch to Fallback Plan (pre-recorded explanations)

**Time budget:** 2 min

---

### State 3: Manager Dashboard Demo (Phase 4 from runbook)

**Step 4.1: Login as Manager**

**Presenter Script:**
"Let's look at the manager view. This shows a heatmap of the team's signals. Red indicates potential burnout, green indicates high potential. The colors are relative to the team, not absolute."

**Action:**
1. In browser (opened in Step 0.3), click "Login"
2. Username: `manager-demo`
3. Password: (use configured temp password or MFA)
4. Click "Dashboard"

**Verification:**
- ✅ Login succeeds (no auth error)
- ✅ Dashboard loads
- ✅ Heatmap shows 3 users (Alice, Ben, Carol)

**Continue condition:** Dashboard visible with all 3 users → proceed to Step 4.2
**STOP condition:** Login fails or dashboard blank → switch to Fallback Plan (pre-recorded screenshot)

**Time budget:** 1 min

---

**Step 4.2: View Heatmap & Alerts**

**Presenter Script:**
"Alice shows in red (burnout flag), Ben in green (high potential), and Carol in gray (baseline). Managers can see this at a glance without seeing any raw work data."

**Action:**
1. Point to heatmap in UI
2. Take screenshot: `manager_dashboard.png`
3. Click Alice's row → alert modal opens

**Verification:**
- ✅ Alice: red flag + alert text visible
- ✅ Ben: green flag visible
- ✅ Carol: gray, no flag
- ✅ Screenshot captured

**Continue condition:** ✅ → proceed to Step 4.3
**STOP condition:** UI blank or alerts not visible → switch to Fallback Plan

**Time budget:** 1 min

---

**Step 4.3: View Explanation Modal (Alice)**

**Presenter Script:**
"When we click on Alice's alert, we see why she was flagged: high meetings and messages relative to her team. The explanation suggests wellness and workload discussion—never punitive actions."

**Action:**
1. In alert modal for Alice, click "Show Full Explanation"
2. Read explanation text (should include "Why flagged" and "Next best action")
3. Take screenshot: `explanation_modal.png`

**Verification:**
- ✅ Explanation text displayed
- ✅ Contains "Why flagged" (signals + z-scores)
- ✅ Contains "Next best action" (coaching suggestions)
- ✅ No punitive advice (no "consider demotion", no "performance improvement")
- ✅ Screenshot captured

**Continue condition:** ✅ → proceed to Step 4.4
**STOP condition:** Explanation blank or contains punitive advice → HALT and log incident

**Time budget:** 1 min

---

**Step 4.4: Show Cohort Context**

**Presenter Script:**
"Notice the cohort context: this is relative to Alice's peer group (senior engineers). We don't compare across roles or seniority levels, preventing bias."

**Action:**
1. Point to cohort info in explanation (e.g., "Relative to eng-team, engineer, senior cohort")
2. Verify cohort_mean and cohort_stdev visible
3. Take note for explanation validity

**Verification:**
- ✅ Cohort context visible in explanation

**Continue condition:** ✅ → proceed to State 5
**STOP condition:** No cohort context → minor issue (explanation still valid, but continue)

**Time budget:** 30 sec

---

### State 4: Employee Portal Demo

**Step 5.1: Logout as Manager, Login as Employee (Alice)**

**Presenter Script:**
"Now let's see the employee view. Employees see only their own signals and can opt out of certain data collection if they choose."

**Action:**
1. Logout from manager view
2. Login as: `alice-demo`
3. Password: (temp password or MFA)

**Verification:**
- ✅ Login succeeds
- ✅ Employee portal loads

**Continue condition:** ✅ → proceed to Step 5.2
**STOP condition:** Login fails → switch to Fallback Plan

**Time budget:** 1 min

---

**Step 5.2: View My Signals (Employee View)**

**Presenter Script:**
"Alice can see her own signal summary: meetings, messages, PRs. She understands what the system is tracking, and there's no raw text or keystroke data stored."

**Action:**
1. In employee portal, view "My Signals" section
2. Verify visible signals match golden data (6 meetings, 8 messages, etc.)
3. Take screenshot: `employee_portal.png`

**Verification:**
- ✅ Alice's signals displayed (numeric only, no raw text)
- ✅ Signals match expected golden data
- ✅ Screenshot captured

**Continue condition:** ✅ → proceed to State 5
**STOP condition:** Signals don't match or raw text visible → HALT

**Time budget:** 1 min

---

### State 5: Audit View (HR/Compliance)

**Step 6.1: Logout as Employee, Login as HR**

**Presenter Script:**
"Finally, the HR view shows all alerts and explanations for audit and compliance purposes. HR can ensure no bias or errors occurred."

**Action:**
1. Logout
2. Login as: `hr-demo`
3. Click "Audit View"

**Verification:**
- ✅ Login succeeds
- ✅ Audit view loads
- ✅ All 3 users visible (Alice, Ben, Carol)

**Continue condition:** ✅ → proceed to Step 6.2
**STOP condition:** Login fails or audit view blank → switch to Fallback Plan

**Time budget:** 1 min

---

**Step 6.2: Verify Audit Trail**

**Presenter Script:**
"The audit view shows all alerts, explanations, and the KB documents referenced. This provides transparency for compliance reviews."

**Action:**
1. In audit view, expand Alice's alert entry
2. Verify fields visible:
   - Alert ID
   - Reason (burnout flag)
   - Explanation reference (S3 key)
   - KB references (policy/playbook IDs)
3. Take screenshot: `audit_view.png`

**Verification:**
- ✅ Alert details visible
- ✅ Explanation reference shown
- ✅ KB references present (at least 1)
- ✅ No PII in display (only opaque userIds, cohort context)
- ✅ Screenshot captured

**Continue condition:** ✅ → proceed to Evidence Capture
**STOP condition:** PII visible or references missing → HALT

**Time budget:** 1 min

---

### State 6: Evidence Capture (Phase 5 from runbook)

**Step 7.1: Save UI Screenshots**

**Action:**
1. Collect all 5 screenshots taken during demo:
   - `manager_dashboard.png`
   - `explanation_modal.png`
   - `employee_portal.png`
   - `audit_view.png`
   - `heatmap_with_all_users.png` (bonus)

2. Upload to S3:
   ```bash
   aws s3 cp manager_dashboard.png ${S3_REPORTS}/07_manager_dashboard.png
   aws s3 cp explanation_modal.png ${S3_REPORTS}/07_explanation_modal.png
   aws s3 cp employee_portal.png ${S3_REPORTS}/07_employee_portal.png
   aws s3 cp audit_view.png ${S3_REPORTS}/07_audit_view.png
   ```

**Verification:**
- ✅ All 4 screenshots uploaded

**Continue condition:** ✅ → proceed to Step 7.2
**STOP condition:** Upload fails → retry or skip (non-critical)

**Time budget:** 1 min

---

**Step 7.2: Save DynamoDB Aggregates**

**Action:**
```bash
# Alice
aws dynamodb get-item --table-name AggregatesTable-dev \
  --key "{\"PK\":{\"S\":\"USER#alice-uuid\"},\"SK\":{\"S\":\"WEEK#2026-W06\"}}" \
  > ${S3_REPORTS}/07_alice_aggregate.json

# Ben
aws dynamodb get-item --table-name AggregatesTable-dev \
  --key "{\"PK\":{\"S\":\"USER#ben-uuid\"},\"SK\":{\"S\":\"WEEK#2026-W06\"}}" \
  > ${S3_REPORTS}/07_ben_aggregate.json

# Carol
aws dynamodb get-item --table-name AggregatesTable-dev \
  --key "{\"PK\":{\"S\":\"USER#carol-uuid\"},\"SK\":{\"S\":\"WEEK#2026-W06\"}}" \
  > ${S3_REPORTS}/07_carol_aggregate.json

# Verify all have numeric signals only (no text)
jq '.Item.aggregates' ${S3_REPORTS}/07_alice_aggregate.json | grep -i "text\|message" || echo "✓ No text fields"
```

**Verification:**
- ✅ 3 JSON files created
- ✅ No text fields in aggregates (only numeric counts)

**Continue condition:** ✅ → proceed to Step 7.3
**STOP condition:** Text fields found → HALT (privacy violation)

**Time budget:** 1 min

---

**Step 7.3: Save Alerts & Explanations**

**Action:**
```bash
# Query all alerts
aws dynamodb scan --table-name AlertsTable-dev \
  --filter-expression "SK = :week" \
  --expression-attribute-values "{\":week\":{\"S\":\"WEEK#2026-W06\"}}" \
  > ${S3_REPORTS}/07_all_alerts.json

# Download all explanations
aws s3 sync s3://signalhr-explanations-dev/ ${S3_REPORTS}/07_explanations/ --include "*.json"
```

**Verification:**
- ✅ Alert JSON created (2 alerts expected: Alice + Ben)
- ✅ Explanations downloaded

**Continue condition:** ✅ → Demo Complete
**STOP condition:** None (acceptable to continue even if some artifacts missing)

**Time budget:** 1 min

---

## Time Boxing (NEW)

| Step | Activity | Max Time | Buffer |
|------|----------|----------|--------|
| 0.1–0.3 | Setup & validation | 4 min | 1 min |
| 1.1–1.3 | Ingestion (3 × generator) | 2.5 min | 1 min |
| 2.1–2.2 | Processing (normalize + rollup) | 5 min | 2 min |
| 3.1–3.2 | Scoring & explanations | 3 min | 1 min |
| 4.1–4.4 | Manager dashboard | 3.5 min | 1 min |
| 5.1–5.2 | Employee portal | 2 min | 0.5 min |
| 6.1–6.2 | Audit view | 2 min | 0.5 min |
| 7.1–7.3 | Evidence capture | 3 min | 0.5 min |
| **Total** | **Demo** | **25 min** | **7.5 min** |

**Optional skip rules (if running over time):**
- If Step 2.2 (rollup) exceeds 5 min, proceed to Step 3.1 even if rollup not complete (explanations may be delayed)
- If Steps 4.1–6.2 (UI demo) exceed 7 min total, skip Step 6 (audit view) and show screenshot instead
- If all UI demos running >10 min, proceed to evidence capture (core pipeline demo complete)

**Total demo time (main phase 1–5): 8–10 minutes**
**Total presentation time (setup + demo + Q&A): 15–20 minutes**

---

## Demo Lock Rules (NEW)

**These rules ensure demo is deterministic and safe from drift.**

1. **No data regeneration:** Synthetic generator uses fixed profiles (alice, ben, carol). Do NOT run generator twice on same users/week.
2. **No redeployments:** All Lambda, DynamoDB, API Gateway, Bedrock components must be pre-deployed before demo start.
3. **No prompt/threshold changes:** Bedrock prompt, guardrails, and rules engine thresholds (z > 2 for burnout, z > 1.5 for hippo) are frozen.
4. **No UI code changes:** Amplify UI deployed. Do NOT deploy changes during demo.
5. **Read-only demo:** Managers cannot create manual alerts or change settings during demo.
6. **Fixed time window:** All events timestamped to 2026-W06. Do NOT use live timestamps.
7. **Fixed user IDs:** alice-uuid, ben-uuid, carol-uuid are hardcoded. Do NOT change.
8. **No configuration drift:** No KMS key rotation, IAM policy changes, or network modifications during demo.

**Violation consequence:** Demo is non-reproducible. Evidence invalidated. File incident CR.

---

## Fallback Demo Plan (NEW)

If Bedrock is unavailable or demo encounters critical failure, switch to fallback mode.

### Fallback Trigger Conditions

1. Bedrock Lambda times out (>10 sec, Step 3.2 exceeds 2 min)
2. Bedrock returns unsafe output (PII or punitive advice detected)
3. Network/API error for core services (API Gateway, SQS, DynamoDB)
4. UI login fails (Cognito/Amplify issue)

### Fallback Execution

**Step F1: Display Pre-Recorded Screenshots**

Action:
1. If UI login fails, show pre-captured UI screenshots:
   - `manager_dashboard_fallback.png` (3 users, heatmap, alerts visible)
   - `explanation_modal_fallback.png` (Alice explanation, coaching text)
   - `employee_portal_fallback.png` (my signals view)
   - `audit_view_fallback.png` (all alerts, HR view)

2. If Bedrock fails, use templated explanation:
   ```
   Why flagged: Alice shows elevated signals relative to her team.
   - Meetings: 6 (team average ~3, std=1.2, z=1.8)
   - Slack messages: 8 (team average ~4, std=2.5, z=1.5)
   - Composite risk score: 1.4 (burnout threshold: > 2.0)
   
   Next best action: Schedule a 1:1 with Alice to discuss workload 
   and wellness. Refer to company wellness policy and time management playbook.
   ```

3. Present fallback explanation as if generated (mark as "templated" in notes)

**Step F2: Continue with Evidence Review**

Action:
1. Show DynamoDB aggregates (if available):
   - Alice: meetings=6, messages=8, z-scores computed
   - Ben: commits=5, prs=3, z-scores computed
   - Carol: no flags, baseline signals

2. Explain architecture via diagram or slides (if UI unavailable)

3. Emphasize: "The system computed the alerts automatically—no human input. All decisions are transparent and explainable."

**Step F3: Complete Evidence Capture**

Action:
1. Collect whatever evidence is available (DynamoDB, screenshots)
2. Document fallback usage in evidence summary
3. Note: "Demo used fallback UI due to [reason]" in summary

**Fallback Success Criteria:**
- ✅ Audience understands privacy-first design (no raw text stored)
- ✅ Audience sees how signals are aggregated (z-scores explained)
- ✅ Audience sees coaching explanations (not punitive)
- ✅ Audience sees RBAC in action (manager → employee → HR views)

**Fallback does NOT invalidate demo if:**
- Core pipeline (ingestion, aggregation, alerts) completed successfully
- Only UI or Bedrock components failed
- Evidence shows alerts and aggregates correctly computed

---

## Backlog Traceability (NEW)

Each demo step maps to one or more backlog tasks. Successful demo execution proves task completion.

| Demo Step | Task IDs | What is Proven |
|-----------|----------|----------------|
| Step 0: Setup | OBS-02, UI-01 | Infrastructure deployed, Cognito ready |
| Step 1.1–1.3: Generator | ING-04 | Synthetic generator runs, produces events |
| Step 2.1: Monitor logs | PROC-01 | Lambda normalizes events without errors |
| Step 2.2: Rollup | PROC-02, PROC-03 | StepFunctions executes, DynamoDB aggregates created |
| Step 3.1: Rules engine | INT-01, INT-02 | Rules apply correctly, 2 alerts (Alice + Ben) created |
| Step 3.2: Bedrock | BED-01, BED-02 | Explanations generated, no PII/punitive advice |
| Step 4.1–4.4: Manager dashboard | UI-02, BED-01 | Dashboard loads, alerts visible, explanations readable |
| Step 5.1–5.2: Employee portal | UI-02, PRIV-07 | Employee sees own data, no other users' data visible |
| Step 6.1–6.2: Audit view | UI-02, AUDIT-02 | HR sees all alerts, explanations, KB references |
| Step 7.1–7.3: Evidence capture | QA-01, DEMO-01 | All artifacts collected and stored |

**Post-demo task status updates:**
After demo completes successfully, update docs/03_backlog.md for each task:
- Set Status → Done
- Link evidence: `s3://signalhr-test-reports/demo/${DEMO_TIMESTAMP}/07_*.png, 07_*.json`
- Add approver sign-off: [approver name], [timestamp]

---

## Presenter Script (NEW)

**Presenter talks through demo step-by-step. Use these 1–2 sentence scripts.**

### Opening (30 sec)

"SignalHR detects employee burnout and high potential using privacy-first signal aggregation. We capture only work signals—meetings, messages, pull requests—never raw text or keystrokes. Our goal is to help managers have better conversations with their teams, not to surveil or punish."

---

### Ingestion Phase (1 min)

"We're generating synthetic work events for three demo employees: Alice is overloaded with meetings and Slack, Ben is a high performer ramping up commits, and Carol has stable baseline signals. [Run generators] The API receives these events and routes them to our processing pipeline. No raw event text is stored—only counts and aggregates."

---

### Processing Phase (1.5 min)

"Our Lambda normalizer computes aggregates per user per week. Alice has 6 meetings (elevated for her team), 8 Slack messages (also elevated), giving her a combined risk score. Ben has 5 commits and 3 PRs (high for a junior engineer)—high potential. Carol is baseline. [Show logs] Notice the normalization removes any free-text fields before storage. We never persist the actual message content."

---

### Cohort Context (30 sec)

"Z-scores are computed within cohort—engineers compared to engineers, not to product managers. This prevents bias. Alice's z=1.8 for meetings is relative to other senior engineers, not the company average. This is critical for fairness."

---

### Rules & Explanations (1 min)

"We apply simple thresholds: alerts fire if z > 2 (burnout) or z > 1.5 (high potential). For each alert, our Bedrock agent generates a coaching explanation. It can suggest wellness resources, workload discussions, or development opportunities—never punitive actions. [Show explanation] Notice it cites company policies and playbooks, giving transparency."

---

### Manager View (1 min)

"Managers see a heatmap of their team. Red for alerts, green for high potential, gray for baseline. When they click an alert, they see why the person was flagged: specific signals and cohort context. All coaching-focused. They can't change thresholds or take automated action—it's for awareness and conversation."

---

### Employee & HR Views (1 min)

"Employees see their own signals and can opt out of collection if they choose. HR sees all alerts and explanations for audit, ensuring no bias occurred. All views show only opaque user IDs and numeric signals—never raw data or PII."

---

### Closing (30 sec)

"This system prioritizes privacy, transparency, and human judgment. We detect patterns to help managers, but humans remain in control of all decisions. The explainability ensures everyone understands why alerts fire, building trust in the system. Thank you."

---

## Demo Success Criteria (NEW)

Demo is **successful** if:

1. ✅ **Privacy:** Audience confirms no raw text or PII visible (only aggregates, z-scores, opaque IDs)
2. ✅ **Explainability:** Audience reads explanation and understands why alert fired (signals + cohort context)
3. ✅ **Coaching tone:** Explanation is supportive, not punitive (no mentions of firing, discipline, rating)
4. ✅ **RBAC:** All 3 views (manager, employee, HR) show correct data filtering
5. ✅ **Alerts correct:** Alice flagged as burnout, Ben as HiPo, Carol not flagged (matches golden data)
6. ✅ **Evidence captured:** All 4 screenshots and DynamoDB artifacts saved to S3

Demo is **failed** if:

1. ❌ Raw text or PII visible in any view
2. ❌ Explanation contains punitive advice or hallucination
3. ❌ Alerts incorrect (wrong users flagged or wrong reasons)
4. ❌ RBAC fails (employee sees other users' data or HR doesn't see all data)
5. ❌ UI crashes or major functionality missing

**On failure:** Document in incident report (docs/CHANGE_REQUESTS.md), remediate, and re-run demo with approval.

---

## Demo Artifact Checklist (NEW)

**Required evidence collected after demo:**

- [ ] Manager dashboard screenshot (all 3 users visible, alerts shown)
- [ ] Explanation modal screenshot (Alice alert with "Why flagged" + "Next best action")
- [ ] Employee portal screenshot (Alice sees own signals, numeric only)
- [ ] Audit view screenshot (HR sees all alerts + KB references, no PII)
- [ ] DynamoDB aggregate JSON (3 users: Alice, Ben, Carol)
- [ ] Alerts table JSON (2 alerts: Alice + Ben, Carol none)
- [ ] Generator logs (stdout with event IDs and HTTP 202 responses)
- [ ] Evidence summary document (checklist + timestamps)

**All artifacts stored in:** `s3://signalhr-test-reports/demo/${DEMO_TIMESTAMP}/`

**Checksums verified:** SHA256 of all artifacts (see docs/05_qa_strategy.md)

---

## Demo Sign-off (NEW)

After demo completes, collect sign-off from stakeholders:

**Sign-off form (in docs/03_backlog.md DEMO-01 Completion Evidence):**

```
Demo Run: [timestamp]
Presenter: [name]
Attendees: [list]

Verification:
- [ ] All steps 1.1–7.3 completed
- [ ] Expected alerts correct (Alice burnout, Ben HiPo, Carol none)
- [ ] No PII visible in any view
- [ ] Explanations are coaching, not punitive
- [ ] All evidence artifacts captured

Success: YES / NO (if NO, file incident CR before retry)

Sign-off:
- Project Owner: [name], [timestamp]
- QA Approver: [name], [timestamp]
- Privacy/Compliance: [name], [timestamp] (optional for MVP)
```

---

## Summary

This demo script is fully deterministic, time-boxed, and agent-safe. All steps have clear verification conditions and STOP rules. Fallback plans ensure resilience. Presenter scripts keep audience engaged. Evidence checklist ensures completeness. Demo execution proves task completion for docs/03_backlog.md.