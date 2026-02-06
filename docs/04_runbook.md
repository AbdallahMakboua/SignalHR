# Runbook — How to run, test, and demo the MVP

This runbook contains commands and steps to run the pipeline locally/in-dev and to execute the demo. Use this for reproducible demo runs.

Prerequisites
- AWS account with permissions for resources in docs/01_architecture.md
- AWS CLI configured
- Node/Python runtime for synthetic generator (TBD per implementation)

Quick start (dev)
1. Start synthetic generator (example using Python script):

```bash
# from repo root
python tools/synthetic_generator.py --profile demo --rate 10
```

2. Post events to API Gateway endpoint (or use generator to POST directly). Example using curl:

```bash
curl -X POST https://<api-id>.execute-api.us-east-1.amazonaws.com/dev/events \
  -H "Content-Type: application/json" \
  -d '{"eventType":"slack_interaction","source":"synth","timestamp":"2026-02-06T12:00:00Z","userId":"uuid-1","orgId":"org-1","teamId":"team-1","signalCounts":{"messages_sent":5}}'
```

3. Monitor SQS / Lambda logs in CloudWatch and verify S3 raw objects appear under s3://signalhr-raw-events-dev/

4. Execute Step Function rollup (manual invoke for demo):

```bash
aws stepfunctions start-execution --state-machine-arn <rollup-arn> --input '{"week":"2026-W06"}'
```

5. Verify DynamoDB aggregates (example query using AWS CLI):

```bash
aws dynamodb get-item --table-name AggregatesTable-dev --key '{"PK":{"S":"USER#uuid-1"},"SK":{"S":"WEEK#2026-W06"}}'
```

6. Trigger feature job (Glue or Lambda) and run SageMaker scoring (invoke endpoint) — see docs/05_qa_strategy.md for test commands.

Demo-specific checklist (see docs/07_demo_script.md for full script)
- Start generator for 3 demo users (Alice/Ben/Carol)
- Wait for pipeline to process (monitor Step Function)
- Open Manager Dashboard and navigate to alert
- Capture screenshots and save to s3://signalhr-test-reports/demo/<timestamp>/

Evidence collection
- Save screenshots to s3://signalhr-test-reports/demo/<timestamp>/
- Save DynamoDB JSON items and S3 object keys with checksums
- Save Bedrock explanation text as S3 object with hash

Troubleshooting
- If DLQ receives messages: inspect message body in DLQ and check Pipe transformation rules; reprocess after fix.
- If Lambda fails: check CloudWatch logs, increase timeout/memory for batch processing as needed.

Notes
- This runbook is minimal and must be updated with concrete commands after implementation details (script names, ARNs) are created.
