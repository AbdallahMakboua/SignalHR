#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

API_ENDPOINT="http://127.0.0.1:8000/events"
PAYLOAD_FILE="/tmp/test_event.json"

if [[ ! -f "${PAYLOAD_FILE}" ]]; then
    echo "ERROR: ${PAYLOAD_FILE} not found"
    echo "Create it first (example payload in /tmp/test_event.json)"
    exit 1
fi

echo "Posting ${PAYLOAD_FILE} to ${API_ENDPOINT}"

RESPONSE_FILE="/tmp/test_ingestion_response.json"
HTTP_STATUS=$(curl -s -o "${RESPONSE_FILE}" -w "%{http_code}" \
    -X POST "${API_ENDPOINT}" \
    -H "Content-Type: application/json" \
    --data-binary "@${PAYLOAD_FILE}")

echo "HTTP Status: ${HTTP_STATUS}"

echo "Response (first 200 chars):"
head -c 200 "${RESPONSE_FILE}"
echo ""
