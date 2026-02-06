# Change Requests (CR) — Enforceable Template & Log

**CRITICAL:** All deviations from the Project Brief, Architecture, Privacy Rules, or Data Schemas MUST be submitted as a Change Request. No implementation work that affects architecture, privacy, security, LLM behavior, or data structure may proceed without an APPROVED CR. Any work begun without an APPROVED CR is INVALID and must be reverted.

---

## CR Lifecycle (NEW)

**All CRs flow through a strict state machine. Only defined transitions allowed.**

### State Definitions

| State | Definition | Allowed Transitions | Duration |
|-------|-----------|-------------------|----------|
| **DRAFT** | CR created, pre-submission; incomplete | → NOT APPROVED | Until submitter ready (no time limit) |
| **NOT APPROVED** | Submitted to Project Owner for review | → APPROVED, REJECTED, SUPERSEDED, RETURNED | Up to 48h for decision (hackathon time-bound) |
| **APPROVED** | Project Owner approved; implementation may begin | → SUPERSEDED (if new CR replaces), CLOSED | From approval date until post-demo review |
| **REJECTED** | Project Owner rejected; no implementation allowed | → DRAFT (only if resubmitted with changes) | Final unless resubmitted |
| **SUPERSEDED** | Another CR replaces this one | Final | Replaced CRs remain in log for traceability |
| **CLOSED** | Post-demo review completed; CR fully resolved | Final | After demo (QA-Pass + 24h) |

### Transition Rules (Enforceable)

1. **DRAFT → NOT APPROVED:** Submitter clicks "Submit for Review"
2. **NOT APPROVED → APPROVED:** Project Owner signs off (must include approval timestamp + name)
3. **NOT APPROVED → REJECTED:** Project Owner declines (must include rejection reason)
4. **NOT APPROVED → RETURNED:** Project Owner requests changes; CR reverts to DRAFT
5. **APPROVED → SUPERSEDED:** Only if another CR (CR-new) replaces it; old CR marked "Superseded by CR-new"
6. **APPROVED → CLOSED:** Post-demo review (no implementation issues found, resolved, or documented)
7. **REJECTED → DRAFT:** Only if submitter rebuts and resubmits with new data

**Forbidden transitions:** NOT APPROVED → CLOSED (must be APPROVED first), REJECTED → APPROVED (must go through DRAFT), SUPERSEDED → any other state

---

## Change Classification (NEW)

**Every CR must be classified. Each classification specifies required reviews.**

### Classification Types & Required Reviews

| Classification | Definition | Required Reviews | Examples | Architecture Impact | Privacy Impact |
|---|---|---|---|---|---|
| **Architecture** | Changes to AWS service selection, topology, or data flow | (1) Architecture Lead, (2) Security Lead, (3) Project Owner | Switch DynamoDB → Aurora; add VPC; change event bus topology | **Yes** | Depends |
| **Privacy/Security** | Changes affecting data handling, encryption, access control, redaction, consent | (1) Privacy/Compliance Lead, (2) Security Lead, (3) Project Owner | Add userId logging; relax redaction; change IAM policy scope | Depends | **Yes** |
| **Data Schema** | Changes to DC-* data contracts (ingestion, aggregates, features) | (1) Data Engineer, (2) QA Lead, (3) Project Owner | Add new signal type; change aggregate structure; rename fields | Depends | Depends |
| **LLM/Prompt** | Changes to Bedrock prompt, guardrails, KB, or response handling | (1) LLM Lead, (2) Privacy/Compliance Lead, (3) Project Owner | Modify system prompt; adjust guardrails; add KB documents | No | **Yes** |
| **UI/Demo** | Changes to UI, demo flow, presenter scripts, or demo data | (1) Demo Lead, (2) QA Lead, (3) Project Owner | Add new dashboard; change demo user profiles; add feature to UI | No | Depends |
| **Ops/Cost** | Changes to infrastructure costs, deployment process, scaling, observability | (1) DevOps Lead, (2) Project Owner | Increase DynamoDB capacity; change KMS key policy; add alarms | No | Depends |

**Note:** CRs may span multiple classifications (e.g., "Add new signal type" = Data Schema + Privacy). List all applicable classifications; require all reviews.

---

## Impact Matrix (Mandatory for Every CR) (NEW)

**Every CR submission MUST complete this matrix. Missing answers = CR returned to DRAFT.**

### Impact Template

```
CR-ID: [filled on creation]
CR Title: [title]

IMPACT MATRIX (Mandatory)

1. **Architecture Impact:**
   [ ] Yes — Changes service topology, data flow, or service selection
   [ ] No — Affects only config, scripts, or documentation within existing services

2. **Privacy Impact:**
   [ ] Yes — Changes data handling, retention, encryption, redaction, consent, user identifiers
   [ ] No — Does not affect PII, signal handling, or user data

3. **QA Re-Run Required:**
   [ ] Yes — Implementation requires QA test suite re-run (new path, schema change, LLM change)
   [ ] No — Changes only non-critical code, docs, or observability (no test re-run needed)

4. **Demo Impact:**
   [ ] Yes — Changes demo flow, demo data, expected outputs, or presenter scripts
   [ ] No — Does not affect demo reproducibility or expected results

5. **Freeze Impact:**
   [ ] Yes — Changes are proposed AFTER QA-Pass (violates observability/security/demo freeze rules)
   [ ] No — Changes are proposed BEFORE QA-Pass
   [If Yes] Freeze Exception Needed: [ ] Architecture Fix, [ ] Bug Fix, [ ] Compliance, [ ] Emergency

IMPACT SUMMARY (auto-generated):
- Architecture affected: [Yes/No]
- Privacy affected: [Yes/No]
- QA re-run: [Yes/No]
- Demo affected: [Yes/No]
- Post-Freeze: [Yes/No]
```

---

## Emergency CR (Hackathon Exception) (NEW)

**Strict criteria for emergency CRs when normal review cannot complete in time.**

### Emergency CR Criteria (ALL must be true)

1. **Critical Blocker:** Change unblocks a critical failure that prevents completion of an essential deliverable (MVP pillar: ingestion, normalization, rollup, scoring, Bedrock, UI, demo)
2. **No Alternative:** No workaround available; change is unavoidable
3. **Time Constraint:** Normal CR review would miss a hard deadline (e.g., <2h until demo start)
4. **Minimal Scope:** Change is narrow and well-scoped (single function, single config, single document)
5. **Low Risk:** Change does NOT affect privacy, security, architecture, or data schema; only ops/cost or minor UI/demo

### Emergency CR Process (Temporary Approval)

1. **Fast-Track Submission:**
   - Classification: "Emergency: [underlying type]"
   - Impact Matrix: Complete (required)
   - Justification: Explain why normal process cannot be followed
   - Proposed change: Detailed, scoped description

2. **Temporary Approval (2-hour window):**
   - Project Owner approves with "APPROVED (TEMPORARY)" status
   - Timestamp recorded
   - Work may begin immediately
   - Approval is provisional; final decision after demo

3. **Post-Demo Validation (Mandatory):**
   - Within 24h after demo, conduct full review (all standard reviews)
   - CR status changes from "APPROVED (TEMPORARY)" to either:
     - "CLOSED" (change validated, no issues found)
     - "APPROVED with Restrictions" (change valid but requires future follow-up)
     - "REVERTED" (change caused issues; must be undone before scoring)
   - If REVERTED, work is rolled back; emergency CR marked as failed in log

### Emergency CR Forbidden For

- Architecture changes
- Privacy/security changes
- Data schema changes (that affect persistence)
- Bedrock prompt/guardrail changes
- Demo changes that alter expected results
- After-demo changes (only possible during execution, not during preparation)

**Rationale:** Emergency CRs are a safety valve for unexpected technical issues during hackathon execution. They are temporary, heavily scoped, and subject to mandatory post-demo review.

---

## Traceability Requirements (Mandatory for Every CR) (NEW)

**Every CR must trace its impact on backlog tasks and documentation. Links must be specific and verifiable.**

### Traceability Template

```
AFFECTED BACKLOG TASKS (if any):
- ING-01: [impact description if affected, or "Not affected"]
- ING-02: [impact description if affected, or "Not affected"]
- ... (list all potentially affected tasks)
Status Change Required: [ ] No, [ ] Yes (describe which tasks transition: e.g., "ING-01 moves In Progress → Done")

AFFECTED DOCUMENTATION (if any):
- docs/00_project_brief.md: [section affected, or "Not affected"]
- docs/02_data_contracts.md: [section affected, or "Not affected"]
- docs/04_runbook.md: [section affected, or "Not affected"]
- docs/05_qa_strategy.md: [section affected, or "Not affected"]
- docs/06_security_privacy.md: [section affected, or "Not affected"]
- docs/07_demo_script.md: [section affected, or "Not affected"]
- docs/08_deployment_plan.md: [section affected, or "Not affected"]
- docs/09_observability.md: [section affected, or "Not affected"]
Status Change Required: [ ] No, [ ] Yes (describe which docs must be updated: e.g., "Update docs/04_runbook.md Phase 2 with new EventBridge Pipe configuration")

EVIDENCE ARTIFACTS (what proof will be provided when CR is implemented):
- Artifacts: [list expected evidence: CloudWatch logs, screenshots, test reports, code commits]
- Location: [S3 path or GitHub commit hash where evidence will be stored]
- Timeline: [when evidence expected: e.g., "within 4 hours of CR approval"]

ROLLBACK PLAN (if needed):
- Describe how change can be reverted if issues found: [e.g., "Revert IaC to commit X, re-run Phase 2"]
- Time to rollback: [estimated: e.g., "30 minutes"]
```

---

## Enforcement Rule (NEW)

### The Core Non-Bypassable Rule

**ANY implementation work that begins WITHOUT an APPROVED CR is INVALID and must be REVERTED for demo and scoring purposes.**

### Enforcement Mechanism

1. **Pre-Work Gate:** Before submitting PR or starting implementation, submitter must:
   - Check `docs/CHANGE_REQUESTS.md` for existing CR with same scope
   - If CR needed: Create new CR in DRAFT state, submit for review, WAIT for APPROVED status
   - If no CR needed: Document why (no change to architecture/privacy/schema/LLM/demo), add comment to backlog task

2. **Code Review Gate:** Reviewer must:
   - Verify CR exists and is APPROVED (check CR-ID in commit message or PR description)
   - If CR-ID missing or CR status ≠ APPROVED: **REJECT PR** with comment: "This change requires an APPROVED CR. See docs/CHANGE_REQUESTS.md."
   - If CR exists and is APPROVED: Proceed with code review

3. **QA Gate (Pre-Demo):** QA Lead must:
   - For all "QA Re-Run Required = Yes" CRs: Re-run affected test suites (docs/05_qa_strategy.md)
   - If re-run fails: Mark CR status as "APPROVED with Restrictions" + note which tests failed
   - Block demo from proceeding with failed CR tests

4. **Post-Demo Audit:** Compliance review (within 24h after demo):
   - List all CRs implemented during hackathon
   - Verify each CR: (1) was APPROVED before implementation, (2) all reviews completed, (3) evidence artifacts available
   - Any CR found to be implemented without APPROVED status: Work rolled back or excluded from scoring
   - Report: "CR Audit Report" stored in `s3://signalhr-test-reports/audit/`

### Exceptions (ONLY via Emergency CR)

The only exception to "work without APPROVED CR is invalid" is an **Emergency CR** meeting the strict criteria in Section 4. Even then:
- Emergency approval is temporary; post-demo validation is mandatory
- If post-demo review fails, work is reverted
- Emergency CRs are visibly marked in log and audit trail

---

## CR Template (Complete & Enforceable)

**Use this template for all CRs. Missing fields = CR returned to DRAFT.**

```markdown
## CR-[YYYY-NNN] — [TITLE]

**Submitted By:** [Name / Role]  
**Date Submitted:** [YYYY-MM-DD]  
**Status:** DRAFT | NOT APPROVED | APPROVED | REJECTED | SUPERSEDED | CLOSED  

---

### 1. Summary
[One-sentence summary of the requested change]

### 2. Description
[Detailed description: What change is being requested? Why is it necessary?]

### 3. Reason
[Business or technical justification: Why can't we proceed as currently scoped?]

### 4. Scope & Impact

**Scope:**
- Affected services/functions/documents: [list specific areas]
- Expected implementation time: [e.g., "2 hours"]

**Impact Matrix (Mandatory):**
- [ ] Architecture Impact: Yes / No
- [ ] Privacy Impact: Yes / No
- [ ] QA Re-Run Required: Yes / No
- [ ] Demo Impact: Yes / No
- [ ] Freeze Impact (Post-QA-Pass): Yes / No

**Change Classification (select all that apply):**
- [ ] Architecture
- [ ] Privacy/Security
- [ ] Data Schema
- [ ] LLM/Prompt
- [ ] UI/Demo
- [ ] Ops/Cost

**Required Reviews (auto-checked based on classification):**
- [ ] Architecture Lead (if Architecture classification)
- [ ] Privacy/Compliance Lead (if Privacy/Security or LLM classification)
- [ ] Security Lead (if Architecture or Privacy/Security classification)
- [ ] Data Engineer (if Data Schema classification)
- [ ] QA Lead (if QA Re-Run = Yes)
- [ ] Demo Lead (if UI/Demo impact)
- [ ] DevOps Lead (if Ops/Cost classification)
- [ ] Project Owner (always required)

### 5. Alternatives Considered
[What other solutions were considered? Why is this the best?]

### 6. Risk Assessment
[What could go wrong? How will it be mitigated?]

**Risk Level:** Low / Medium / High

### 7. Traceability (Mandatory)

**Affected Backlog Tasks:**
- [Task ID]: [Impact description]
- Status change required: Yes / No (describe)

**Affected Documentation:**
- [Document file]: [Section affected]
- Updates required: Yes / No (describe)

**Evidence Artifacts (will be provided on implementation):**
- [List artifact types: CloudWatch logs, screenshots, test reports, commits, etc.]
- Storage location: [S3 path or GitHub]
- Timeline: [when evidence expected]

### 8. Rollback Plan
[How can this change be reverted if issues found? How long?]

### 9. Approver Sign-Off

**Project Owner Review:**
- [ ] Approved
- [ ] Rejected
- [ ] Request Changes (return to DRAFT)

**Approver Name:** [Name]  
**Approval Date & Time:** [YYYY-MM-DD HH:MM UTC]  
**Approval Notes:** [Any conditions, follow-up, or observations]

**Other Reviews (if required):**
- Architecture Lead: Approved / Rejected / Pending  
- Privacy/Compliance Lead: Approved / Rejected / Pending  
- Security Lead: Approved / Rejected / Pending  
- [Other reviewers as needed]

### 10. Implementation Record (filled ONLY after APPROVAL)

**Implementation Started:** [YYYY-MM-DD HH:MM UTC]  
**Implemented By:** [Name / Team]  
**Commit Hash / PR URL:** [Link to code or IaC changes]  
**Evidence Artifacts Provided:** Yes / No (link to S3 path or evidence)  

**Post-Demo Validation (within 24h after demo):**
- [ ] Final Status: CLOSED (change validated)
- [ ] Final Status: APPROVED with Restrictions (requires follow-up)
- [ ] Final Status: REVERTED (change caused issues, rolled back)
- Validation Notes: [Summary]

---

**CR Record:** [link to backlog task or documentation section this CR resolves]
```

---

## CR Log (Canonical)

**All CRs submitted during the hackathon are logged here. CR-ID auto-assigned on submission.**

| CR-ID | Title | Submitted By | Date | Classification | Status | Architecture | Privacy | QA Re-Run | Demo Impact | Approved By | Approval Date |
|-------|-------|--------------|------|---|---|---|---|---|---|---|---|
| CR-2026-001 | Change DynamoDB → Aurora Serverless v2 | [TBD] | [TBD] | Architecture | NOT APPROVED | Yes | No | Yes | No | [TBD] | [TBD] |
| | | | | | | | | | | | |

**Note:** Log entries link to detailed CR sections below. One section per CR, following the template above.

---

## CR Submission Checklist (NEW)

**Before submitting a CR, complete this checklist. Missing items = CR returned to DRAFT.**

- [ ] CR title is clear and specific (not vague)
- [ ] Summary is one sentence
- [ ] Description explains WHAT change is needed and WHY (justification)
- [ ] Scope is bounded (not open-ended)
- [ ] Impact Matrix completed (all 5 questions answered)
- [ ] Change Classification selected (at least one)
- [ ] Risk level assessed (Low/Medium/High)
- [ ] Alternatives considered section filled in
- [ ] Traceability section completed:
  - [ ] Affected backlog tasks listed
  - [ ] Affected documentation listed
  - [ ] Evidence artifacts specified
- [ ] Rollback plan described (how to revert if needed)
- [ ] Required reviews identified (based on classification)
- [ ] Approver (Project Owner) identified
- [ ] Emergency CR designation (if applicable): Justified if marked "Emergency"

---

## Procedure (Complete Workflow)

### For Submitters (Creating a CR)

1. **Create:** Use CR Template above; save as section in this document
2. **Auto-Assign CR-ID:** CR-2026-NNN (increment from last CR)
3. **Fill All Mandatory Fields:**
   - Summary, Description, Reason, Scope & Impact, Impact Matrix, Classification
   - Alternatives, Risk Assessment, Traceability, Rollback Plan
4. **Mark Status:** DRAFT
5. **Submit Checklist:** Verify all checklist items ✓
6. **Notify Project Owner:** Email link to CR section; request review
7. **Wait for APPROVED Status:** Do NOT implement until status changes to APPROVED

### For Project Owner (Reviewing a CR)

1. **Receive Notification:** Submitter sends link to CR section
2. **Coordinate Reviews:** Based on classification, request reviews from assigned leads
3. **Review Evidence:**
   - Is justification sound?
   - Are risks properly mitigated?
   - Are traceability links correct?
   - Is rollback plan viable?
4. **Decision:** Approve, Reject, or Request Changes
5. **Sign-Off:**
   - [ ] Approved: Fill "Approver Sign-Off" section; change Status to APPROVED; set Approval Date/Time
   - [ ] Rejected: Fill rejection reason; change Status to REJECTED; document why
   - [ ] Request Changes: Change Status back to DRAFT; add comment in "Approver Sign-Off"
6. **Notify Submitter:** Email outcome
7. **If APPROVED:** Implementation may begin; submitter updates "Implementation Record" section when complete

### For Code Reviewer (Checking Implementation)

1. **Pre-Review Check:** Ask submitter: "What CR does this implement?"
2. **Verify CR Status:** Open docs/CHANGE_REQUESTS.md; find CR-ID; confirm Status = APPROVED
3. **Verify Commit Message:** Commit hash or PR URL links to CR
4. **If CR Not Found or Status ≠ APPROVED:** REJECT PR with message: "This PR requires an APPROVED CR per docs/CHANGE_REQUESTS.md"
5. **If CR Is Approved:** Proceed with normal code review

### For QA Lead (Testing CRs)

1. **Identify CRs with "QA Re-Run Required = Yes"**
2. **Re-Run Affected Tests:** Use test suite from docs/05_qa_strategy.md
3. **Record Results:** Pass or Fail
4. **If Fail:** Mark CR as "APPROVED with Restrictions" + note test failures
5. **Block Demo if Critical Failure:** Do not proceed to demo with failed CR tests

### For Post-Demo Auditor (48h after Demo Conclusion)

1. **List All Implemented CRs:** Extract from `docs/CHANGE_REQUESTS.md` Implementation Record sections
2. **Verify Each CR:**
   - Status was APPROVED (or APPROVED TEMPORARY for Emergency CRs) before implementation
   - All required reviews completed (reviewers signed off)
   - Evidence artifacts stored at specified location
   - Implementation recorded with commit hash
3. **For Emergency CRs:** Validate post-demo review completed; status updated to CLOSED, APPROVED with Restrictions, or REVERTED
4. **Identify Any Violations:** CRs implemented without APPROVED status (if found: mark as INVALID; recommend rollback)
5. **Report:** Generate CR Audit Report; store in `s3://signalhr-test-reports/audit/cr-audit-report-<timestamp>.md`
6. **Summary:** "X CRs implemented, Y with valid approval, Z with violations"

---

## CR Alignment Rules (NEW)

**CRs must align with these project constraints. Violations are grounds for rejection.**

### Rule 1: Architecture Must Not Change

CRs requesting changes to:
- Service selection (e.g., "replace Lambda with step function code")
- Service topology (e.g., "remove StepFunctions")
- Data flow (e.g., "bypass EventBridge Pipes")

Are REJECTED unless they replace one AWS service with an equivalent service approved in project scope (e.g., DynamoDB → Aurora).

**Exception:** Emergency CR if change unblocks critical deliverable and does not affect core ingestion/rollup/scoring paths.

### Rule 2: Privacy Rules Cannot Be Relaxed

CRs requesting:
- Remove or weaken PII redaction (e.g., "include userId in dashboards")
- Store raw text (e.g., "save message content to S3")
- Expose individual user data (e.g., "show per-user metrics")
- Change data retention downward (shorten TTL below compliance requirement)

Are REJECTED unconditionally. Privacy rules are binding.

**Exception:** Tightening privacy rules (e.g., "add additional redaction check") always approved if technically feasible.

### Rule 3: Demo Expected Outputs Cannot Change (Post-QA-Pass)

CRs requesting changes to demo expected results (e.g., "Alice should not be flagged") are REJECTED if submitted after QA-Pass.

**Exception:** Bug fixes (e.g., "Alice was incorrectly flagged due to algorithm bug") may be approved if:
- Bug cause identified and verified
- Fix is localized (does not require full re-run)
- Demo Lead approves change as "cosmetic correction"

### Rule 4: Critical Path Stays Fixed (Post-Demo-Start)

CRs submitted after demo begins (during execution) requesting changes to demo flow, presenter scripts, or expected outputs are REJECTED.

**Exception:** Emergency CR if change unblocks demo continuation (e.g., "Bedrock unavailable; activate fallback").

---

## FAQ — CR Decision Guide

**Q: When do I need a CR?**
A: You need a CR if your change affects:
1. Architecture (service selection, topology, data flow)
2. Privacy/security (data handling, redaction, encryption, IAM)
3. Data schema (field names, types, persistence model)
4. LLM behavior (Bedrock prompt, guardrails, KB, safety checks)
5. Demo flow/expected results (demo data, presenter scripts, expected outputs)
6. Infrastructure costs (DynamoDB capacity, Lambda memory, data retention)

If your change is purely to documentation (clarification, typo fix), code comments, or non-critical infrastructure (e.g., adding a CloudWatch dashboard), a CR is NOT required (but document why in the backlog task).

**Q: What if I start work without a CR and realize I need one?**
A: Submit the CR immediately (status DRAFT). Pause work. Wait for APPROVED status. Resume work only after approval. Any work done before CR approval is at risk of being reverted.

**Q: Can I work in parallel with CR review?**
A: No. A CR must be APPROVED before implementation begins. Parallel work creates risk of rework if CR is rejected.

**Q: What if Project Owner is unavailable?**
A: Escalate to Project Owner's delegate (documented in docs/00_project_brief.md "Owner & Contacts"). Do not proceed without explicit approval from someone in the approval chain.

**Q: Can an Emergency CR be rejected post-demo?**
A: Yes. If post-demo validation finds the change caused issues, Emergency CR status changes to REVERTED. Work is rolled back. No exceptions.

**Q: How long do CRs stay in the log?**
A: Indefinitely. All CRs (approved, rejected, reverted) remain in docs/CHANGE_REQUESTS.md for audit trail and learning purposes.

---

## Summary: CR Governance

| Aspect | Rule |
|--------|------|
| **Default Status** | NOT APPROVED (work forbidden) |
| **Work Permission** | APPROVED status only (or APPROVED TEMPORARY for Emergency CRs) |
| **Review Requirement** | Mandatory, based on classification |
| **Submitter Responsibility** | Complete all fields, provide justification, link to backlog |
| **Approver Responsibility** | Review impact, consult required leads, sign-off with timestamp |
| **Reviewer Responsibility** | Verify APPROVED CR exists before approving code |
| **QA Responsibility** | Re-run tests for CRs with "QA Re-Run = Yes" |
| **Auditor Responsibility** | Post-demo validation; identify and report violations |
| **Invalid Work** | Any work without APPROVED CR is rolled back for scoring |
| **Emergency Exception** | Strict criteria; temporary approval; mandatory post-demo validation |
| **No Bypass** | CRs are non-bypassable; governance is enforced |

---

**Document Version:** 1.0 (Hardened)  
**Last Updated:** 2026-02-07  
**Status:** Enforceable & Ready for Enforcement  
**Next Step:** Assign Project Owner; document in docs/00_project_brief.md Owner & Contacts
