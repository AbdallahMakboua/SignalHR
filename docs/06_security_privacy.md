# Security, Privacy & Ethics — Rules and Guardrails

Privacy-First Rules (must be enforced programmatically)
- NEVER store message text, keystrokes, screenshots, or raw conversation content.
- EventBridge Pipes and Lambda normalization MUST drop any optional free-text fields before persistence.
- Store only aggregates, counts, trends, z-scores, cohort baselines.
- `userId` must be opaque and not reversible to PII.
- Use KMS encryption for S3 and DynamoDB; rotate keys per policy.
- Data retention: raw reduced events 90 days (configurable TTL), aggregates 2 years.

Access & IAM
- Principle of least privilege for all roles.
- Cognito groups: Manager, Employee, HR — map permissions explicitly.
- Service roles scoped to minimal resource actions (e.g., Lambda role only s3:PutObject for raw bucket and dynamodb:UpdateItem for AggregatesTable).

Bedrock & LLM Guardrails
- Only pass non-sensitive features and cohort stats to Bedrock; never pass userId or raw events.
- Include explicit prompt constraints: do not give legal/sanctioned HR actions; only coaching suggestions.
- Post-response policy scanner to detect PII or disallowed advice. If detected, do not present to user and log incident.

Bias Mitigation
- Compute baselines per cohort (role/seniority/team). No cross-role z-score comparisons.
- Alerting decisions must include cohort context and allow human review before any action.
- Periodic bias audits (monthly) comparing alert rates across cohorts (synthetic for MVP).

Audit & Compliance
- CloudTrail enabled and logged to encrypted S3; retain per org policy.
- Audit view in UI for HR showing explanationRef and KB references for each alert (no PII).

Change Requests
- Any change to privacy rules must be submitted as a CR in docs/CHANGE_REQUESTS.md and approved before implementation.
