#!/usr/bin/env bash
set -euo pipefail

# Minimal verification script for Slice 0 pipeline resources.
# This script uses AWS CLI and placeholder names used in this repo's backlog.

echo "Verify AWS resources for SignalHR Slice 0"

REGION=${AWS_REGION:-us-east-1}

echo "Region: $REGION"

echo "Check EventBridge bus: signalhr-bus-dev"
aws events describe-event-bus --name signalhr-bus-dev --region $REGION || echo "EventBridge bus not found"

echo "Check SQS queue: signalhr-ingest-queue-dev"
aws sqs get-queue-url --queue-name signalhr-ingest-queue-dev --region $REGION || echo "SQS queue not found"

echo "Check Lambda function: signalhr-normalize-dev"
aws lambda get-function --function-name signalhr-normalize-dev --region $REGION || echo "Lambda not found"

echo "Check CloudWatch alarms"
aws cloudwatch describe-alarms --region $REGION --query 'MetricAlarms[?contains(AlarmName, `signalhr`)].AlarmName' || echo "No alarms found"

echo "Note: many resources may be placeholders until you deploy via AWS Console/CLI. Replace names as needed."

echo "verify_pipeline.sh completed"
