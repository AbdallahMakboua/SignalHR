# Demo Script — 2–3 Minute Storyboard

Objective: Demonstrate privacy-first detection of Burnout and HiPo potential with explainability for Manager and Employee transparency.

Actors & scenario (3 synthetic users)
- Alice: Overloaded — rising meetings, high context switches
- Ben: HiPo — rising commits, PRs, collaboration index
- Carol: Baseline — stable metrics

Steps
1. Start synthetic generator with profiles for Alice/Ben/Carol.
2. Generator posts events to API Gateway — confirm EventBridge receipt.
3. Monitor SQS → Lambda normalization → S3 raw objects and DynamoDB aggregates.
4. Run StepFunction rollup; run feature extraction and scoring (rules + SageMaker).
5. Open Manager Dashboard (Amplify) as Manager, show team heatmap and alerts.
6. Click Alice alert → show Bedrock "Why flagged" + "Next best action".
7. Open Employee Portal as Alice to show "My signals" and opt-in controls.
8. Open Audit View as HR and display explanationRef + KB references.

Evidence to collect
- Generator logs and event IDs
- EventBridge metric screenshot
- S3 object keys and checksum
- DynamoDB aggregate JSON for each user
- AlertsTable entries and explanationRef S3 key
- Bedrock explanation text saved in S3 with hash
- UI screenshots for Manager Dashboard, Explanation modal, Employee portal, Audit view

Timing & remarks
- Total demo time: ~3 minutes after pipeline warm-up.
- Ensure generator timestamps align to current week for rollup.

Note: Full run commands and exact endpoints will be added to docs/04_runbook.md once ARNs and script names are available.