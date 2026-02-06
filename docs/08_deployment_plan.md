# Deployment Plan & CI/CD Notes

Purpose: Minimal deployment steps for MVP and resource reference. This file should be updated with concrete IaC templates (CloudFormation/Terraform) when available.

CI/CD approach (MVP)
- Use minimal scripts to deploy resources or CloudFormation templates.
- Prefer AWS Console/CLI for quick MVP but record created resource ARNs in docs.

Suggested steps
1. Create IAM bootstrap roles and KMS keys (OBS-02).
2. Deploy EventBridge bus, SQS queues, and API Gateway.
3. Deploy Lambdas, StepFunctions, and DynamoDB tables.
4. Create S3 buckets and Glue catalog entries.
5. Deploy SageMaker training job or use prebuilt container.
6. Deploy Cognito user pool and Amplify app.

Artifacts & manifests
- Add CloudFormation/Terraform files here once authored.

Rollback notes
- Keep resource naming predictable to allow safe re-deploy and deletion in dev.

Post-deploy verification
- Validate EventBridge→SQS→Lambda pipeline with synthetic event.
- Verify DynamoDB items and S3 objects.
- Confirm Cognito authentication and UI login flow.

Security: store secrets in AWS Secrets Manager and reference via roles.
