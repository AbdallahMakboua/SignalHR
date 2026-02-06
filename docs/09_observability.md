# Observability & Audit — Dashboards, Logs, and Traces

Log groups & naming conventions
- Lambda logs: /aws/lambda/<function-name>-dev
- StepFunctions: /aws/vendedlogs/states/<state-machine-name>
- API Gateway access logs: API-Gateway-Access-<stage>
- SQS metrics tracked via CloudWatch metrics for ApproximateNumberOfMessagesVisible and AgeOfOldestMessage

Trace & sampling
- Use AWS X-Ray for end-to-end tracing. Sample key paths: API Gateway → Lambda → DynamoDB → Bedrock.

Dashboards (CloudWatch)
- Ingest Overview: EventBridge events/min, SQS depth, Lambda errors, Lambda duration
- Processing: StepFunction executions, items processed, rollup duration
- Storage: DynamoDB consumed read/write capacity metrics, S3 PUTs
- Bedrock & ML: SageMaker endpoint invocations, Bedrock request success/failure

Alarms
- DLQ messages > 0
- Lambda error rate > 1% (or configurable)
- StepFunction failures > 0
- SQS age > threshold

Audit trails
- CloudTrail enabled for all management events, logged to encrypted S3 bucket
- Retain CloudTrail logs per org policy; restrict access to HR audit role

Evidence for verification
- Dashboard screenshot including timestamp
- Example X-Ray trace showing end-to-end flow (trace id)
- CloudTrail event id for privileged changes

Runbook pointers
- For DLQ: check pipe transformation & reprocess after fix
- For Lambda errors: check CloudWatch logs; increase memory/time if needed

Notes
- Observability must redact PII; do not include userId in aggregated dashboards unless hashed/opaque which is permitted.
