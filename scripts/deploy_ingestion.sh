#!/usr/bin/env bash
set -euo pipefail

# Deploy ING-01: HTTP API + EventBridge PutEvents integration (us-east-2)
# Gracefully handles missing EventBridge bus (permission blocker): discovers existing buses if creation fails.
# 
# Usage:
#   bash scripts/deploy_ingestion.sh                    # Use default BUS_NAME=signalhr-bus-dev
#   BUS_NAME=my-existing-bus bash scripts/deploy_ingestion.sh
#
# If CreateEventBus is denied: script will attempt to list available buses and guide you to pick one.

AWS_REGION=${AWS_REGION:-us-east-2}
API_NAME=${API_NAME:-signalhr-ingest-http-api-dev}
BUS_NAME=${BUS_NAME:-signalhr-bus-dev}
ROLE_NAME=${ROLE_NAME:-signalhr-apigw-putevents-role-dev}
STAGE_NAME=${STAGE_NAME:-dev}

echo "=========================================="
echo "ING-01 Deployment: HTTP API + EventBridge"
echo "=========================================="
echo "Region: ${AWS_REGION}"
echo "Bus (requested): ${BUS_NAME}"
echo ""

# 1) Attempt to find or create EventBridge bus
echo "[1/6] Discovering EventBridge buses..."
BUS_ARN=""

# Try to describe the requested bus
if aws events describe-event-bus --name "${BUS_NAME}" --region "${AWS_REGION}" >/dev/null 2>&1; then
  echo "  ✓ EventBridge bus exists: ${BUS_NAME}"
  BUS_ARN=$(aws events describe-event-bus --name "${BUS_NAME}" --region "${AWS_REGION}" --query 'Arn' --output text)
else
  echo "  ✗ Bus '${BUS_NAME}' not found. Attempting to create..."
  
  # Try to create the bus (this may fail with AccessDenied)
  if aws events create-event-bus --name "${BUS_NAME}" --region "${AWS_REGION}" >/tmp/eb_create.json 2>&1; then
    echo "  ✓ Created EventBridge bus: ${BUS_NAME}"
    BUS_ARN=$(aws events describe-event-bus --name "${BUS_NAME}" --region "${AWS_REGION}" --query 'Arn' --output text)
  else
    # CreateEventBus denied: list available buses and guide user
    echo "  ✗ CreateEventBus permission denied (this is expected)."
    echo ""
    echo "  Available EventBridge buses in ${AWS_REGION}:"
    aws events list-event-buses --region "${AWS_REGION}" --query "EventBuses[*].Name" --output text | tr '\t' '\n' | sed 's/^/    - /'
    echo ""
    echo "  ACTION REQUIRED:"
    echo "    1. Ask mentor to create bus '${BUS_NAME}' or grant events:CreateEventBus permission"
    echo "    2. Or pick an existing bus and re-run: BUS_NAME=<existing-bus> bash scripts/deploy_ingestion.sh"
    echo ""
    echo "  See docs/MENTOR_MESSAGE.md for ready-to-send request."
    echo "  See docs/04_runbook.md#If CreateEventBus is denied for more details."
    echo ""
    exit 1
  fi
fi

echo "  Bus ARN: ${BUS_ARN}"
echo ""

# 2) Create IAM role for API Gateway to call PutEvents (least privilege)
echo "[2/6] Setting up IAM role..."
ROLE_ARN=$(aws iam get-role --role-name "${ROLE_NAME}" --query 'Role.Arn' --output text 2>/dev/null || true)

if [[ -z "${ROLE_ARN}" || "${ROLE_ARN}" == "None" ]]; then
  echo "  Creating IAM role: ${ROLE_NAME}"
  cat > /tmp/apigw_trust.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "apigateway.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

  ROLE_ARN=$(aws iam create-role \
    --role-name "${ROLE_NAME}" \
    --assume-role-policy-document file:///tmp/apigw_trust.json \
    --query 'Role.Arn' --output text)

  cat > /tmp/apigw_putevents_policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "events:PutEvents",
      "Resource": "${BUS_ARN}"
    }
  ]
}
EOF

  aws iam put-role-policy \
    --role-name "${ROLE_NAME}" \
    --policy-name signalhr-apigw-putevents-policy \
    --policy-document file:///tmp/apigw_putevents_policy.json >/dev/null
else
  echo "  ✓ Role exists: ${ROLE_NAME}"
fi
echo "  Role ARN: ${ROLE_ARN}"
echo ""

# 3) Create HTTP API (API Gateway v2)
echo "[3/6] Creating HTTP API..."
API_ID=$(aws apigatewayv2 get-apis --region "${AWS_REGION}" \
  --query "Items[?Name=='${API_NAME}'].ApiId | [0]" --output text 2>/dev/null || true)

if [[ -z "${API_ID}" || "${API_ID}" == "None" ]]; then
  echo "  Creating HTTP API: ${API_NAME}"
  API_ID=$(aws apigatewayv2 create-api \
    --name "${API_NAME}" \
    --protocol-type HTTP \
    --region "${AWS_REGION}" \
    --query 'ApiId' --output text)
else
  echo "  ✓ HTTP API exists: ${API_ID}"
fi
echo "  API ID: ${API_ID}"
echo ""

# 4) Create Integration to EventBridge PutEvents
echo "[4/6] Creating EventBridge integration..."
INTEGRATION_ID=$(aws apigatewayv2 get-integrations --api-id "${API_ID}" --region "${AWS_REGION}" \
  --query "Items[?IntegrationSubtype=='EventBridge-PutEvents'].IntegrationId | [0]" --output text 2>/dev/null || true)

if [[ -z "${INTEGRATION_ID}" || "${INTEGRATION_ID}" == "None" ]]; then
  echo "  Creating integration: EventBridge-PutEvents"
  INTEGRATION_ID=$(aws apigatewayv2 create-integration \
    --api-id "${API_ID}" \
    --integration-type AWS_PROXY \
    --integration-subtype EventBridge-PutEvents \
    --credentials-arn "${ROLE_ARN}" \
    --request-parameters \
      "EventBusName=${BUS_NAME},Source=\$request.body.source,DetailType=\$request.body.eventType,Detail=\$request.body" \
    --region "${AWS_REGION}" \
    --query 'IntegrationId' --output text)
else
  echo "  ✓ Integration exists: ${INTEGRATION_ID}"
fi
echo "  Integration ID: ${INTEGRATION_ID}"
echo ""

# 5) Create Route POST /events
echo "[5/6] Creating API route..."
ROUTE_ID=$(aws apigatewayv2 get-routes --api-id "${API_ID}" --region "${AWS_REGION}" \
  --query "Items[?RouteKey=='POST /events'].RouteId | [0]" --output text 2>/dev/null || true)

if [[ -z "${ROUTE_ID}" || "${ROUTE_ID}" == "None" ]]; then
  echo "  Creating route: POST /events"
  ROUTE_ID=$(aws apigatewayv2 create-route \
    --api-id "${API_ID}" \
    --route-key "POST /events" \
    --target "integrations/${INTEGRATION_ID}" \
    --region "${AWS_REGION}" \
    --query 'RouteId' --output text)
else
  echo "  ✓ Route exists: ${ROUTE_ID}"
fi
echo "  Route ID: ${ROUTE_ID}"
echo ""

# 6) Create Stage (dev) with auto-deploy
echo "[6/6] Creating API stage..."
STAGE_ID=$(aws apigatewayv2 get-stages --api-id "${API_ID}" --region "${AWS_REGION}" \
  --query "Items[?StageName=='${STAGE_NAME}'].StageName | [0]" --output text 2>/dev/null || true)

if [[ -z "${STAGE_ID}" || "${STAGE_ID}" == "None" ]]; then
  echo "  Creating stage: ${STAGE_NAME}"
  aws apigatewayv2 create-stage \
    --api-id "${API_ID}" \
    --stage-name "${STAGE_NAME}" \
    --auto-deploy \
    --region "${AWS_REGION}" >/dev/null
else
  echo "  ✓ Stage exists: ${STAGE_NAME}"
fi
echo ""

echo "=========================================="
echo "Deployment Summary"
echo "=========================================="
API_ENDPOINT="https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com/${STAGE_NAME}"
cat << EOF
✓ API Endpoint:   ${API_ENDPOINT}
✓ API ID:         ${API_ID}
✓ Bus Name:       ${BUS_NAME}
✓ Bus ARN:        ${BUS_ARN}
✓ Role ARN:       ${ROLE_ARN}
✓ Region:         ${AWS_REGION}

Export these for test script:
  export API_ID="${API_ID}"
  export BUS_NAME="${BUS_NAME}"

Test endpoint:
  bash scripts/test_ingestion.sh
EOF
