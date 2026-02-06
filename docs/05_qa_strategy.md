# QA Strategy — Tests, Evaluation Rubric, and Quality Gates

This document defines testing levels, acceptance criteria, and evidence requirements.

Testing levels
- Unit tests: normalization logic, feature functions, cohort z-score computation.
- Integration tests: EventBridge → SQS → Lambda → S3/DynamoDB path; StepFunction rollups.
- E2E tests: Synthetic generator → full pipeline → UI rendering + Bedrock explanation.
- LLM/Bedrock evaluation: hallucination checks, policy adherence, sensitive data leakage scanning.

Evaluation rubric (pass/fail thresholds)
- Pipeline correctness: End-to-end synthetic run reproduces expected aggregate values for 90% of sample events.
- Performance targets (MVP): Lambda normalize ≤200ms per event; StepFunction rollup for 10k events ≤5 minutes (soft).
- Rules precision: ≥0.8 on synthetic labeled test set.
- ML model: probability calibration plausible on synthetic test; returns top features.
- Bedrock: sensitive data leakage = 0 occurrences; hallucination rate ≤5% on synthetic evaluation cases.

Quality Gates (after each Epic)
- Security Gate: IAM/KMS validated, no overly permissive policies.
- Privacy Gate: automated PII scan confirms no text fields persisted.
- Test Coverage Gate: unit + integration tests passing; coverage ≥70% for changed modules.
- LLM Gate: Bedrock outputs pass guardrail tests.

Automated tests & CI
- Define test commands and store test output to s3://signalhr-test-reports/
- Unit test runner: `pytest` or `npm test` depending on implementation
- Integration harness: shell scripts invoking AWS CLI to validate resources

Evidence requirements
- Unit test logs and coverage report (HTML or text)
- Integration run logs: StepFunction execution ARN, DynamoDB item JSON, S3 object keys
- E2E: UI screenshots and Bedrock explanation saved
- LLM eval: report of prompt, response hash, KB references, hallucination detection result

LLM evaluation tests (examples)
- Provide known KB passages to agent and assert agent references KB paragraphs when explaining.
- Provide adversarial prompt injection to ensure agent refuses unsafe requests.
- Sensitive leakage scan: regex-based PII detection on outputs.

Reporting
- QA produces a test summary and attaches artifacts to the related task in docs/03_backlog.md.
