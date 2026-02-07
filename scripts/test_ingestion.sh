#!/usr/bin/env bash
set -euo pipefail

# Test ING-01 ingestion endpoint using a single synthetic event

AWS_REGION=${AWS_REGION:-us-east-2}
API_ID=${API_ID:-}
STAGE_NAME=${STAGE_NAME:-dev}

echo "=========================================="
echo "ING-01 Endpoint Test"
echo "=========================================="
echo ""

# Pre-check: List available EventBridge buses (informational)
echo "[Pre-check] Available EventBridge buses in ${AWS_REGION}:"
aws events list-event-buses --region "${AWS_REGION}" --query "EventBuses[*].Name" --output text | tr '\t' '\n' | sed 's/^/  - /'
echo ""

# Pre-check: Verify API_ID is set
if [[ -z "${API_ID}" ]]; then
  echo "ERROR: API_ID not set."
  echo ""
  echo "ACTION REQUIRED:"
  echo "  1. Run deployment first: bash scripts/deploy_ingestion.sh"
  echo "  2. Then export the API_ID: export API_ID=<api-id-from-deploy>"
  echo "  3. Re-run this test: bash scripts/test_ingestion.sh"
  echo ""
  exit 1
fi

echo "✓ Using API_ID: ${API_ID}"
echo ""

API_ENDPOINT="https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com/${STAGE_NAME}"

echo "Testing API endpoint..."
echo "  POST ${API_ENDPOINT}/events"
echo ""

# Generate one event (dry-run) and post it
PAYLOAD=$(python3 tools/synthetic_generator.py --profile alice --rate 1 --duration 0.001 --dry-run 2>/dev/null | head -1)

if [[ -z "${PAYLOAD}" ]]; then
  echo "ERROR: Failed to generate payload"
  exit 1
fi

echo "Payload (sample):"
echo "  ${PAYLOAD:0:100}..."
echo ""

HTTP_CODE=$(curl -s -o /tmp/ingest_resp.json -w "%{http_code}" \
  -X POST "${API_ENDPOINT}/events" \
  -H "Content-Type: application/json" \
  -d "${PAYLOAD}")

echo "Response:"
echo "  HTTP Status: ${HTTP_CODE}"
echo "  Response Body:"
cat /tmp/ingest_resp.json | sed 's/^/    /'
echo ""

if [[ "${HTTP_CODE}" == "200" || "${HTTP_CODE}" == "202" ]]; then
  echo "✓ Test PASSED. API endpoint is working."
  echo "  Next: Monitor CloudWatch logs and EventBridge metrics"
elif [[ "${HTTP_CODE}" == "403" ]]; then
  echo "✗ Test FAILED with 403 Forbidden."
  echo "  This may indicate EventBridge bus permissions issue."
  echo "  See docs/MENTOR_MESSAGE.md for support request."
else
  echo "✗ Test FAILED with HTTP ${HTTP_CODE}."
  echo "  Check AWS CLI error messages and API Gateway logs."
fi

exit 0
