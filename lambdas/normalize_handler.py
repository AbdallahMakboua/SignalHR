"""Minimal normalization Lambda handler for Slice 0.

Implements:
- validate schemaVersion == 1
- ensure signals are numeric
- remove any text fields
- return normalized dict

This module is unit-testable and intentionally minimal for the hackathon Slice 0.
"""
import json
from typing import Dict, Any


def normalize_event(event: Dict[str, Any]) -> Dict[str, Any]:
    # Basic validation
    if event.get("schemaVersion") != 1:
        raise ValueError("Unsupported schemaVersion")

    normalized = {
        "ingestionId": event.get("ingestionId"),
        "schemaVersion": 1,
        "timestamp": event.get("timestamp"),
        # userId is considered sensitive; do not include in normalized output for dashboards
        # keep cohortId generation in later tasks; for now we forward profile as metadata
        "profile": event.get("profile"),
        "source": event.get("source"),
    }

    signals = event.get("signals") or {}
    cleaned = {}
    for k, v in signals.items():
        # coerce numeric-like values, drop anything not numeric
        try:
            num = int(v)
            cleaned[k] = num
        except Exception:
            try:
                num = float(v)
                cleaned[k] = num
            except Exception:
                # skip non-numeric fields
                continue

    normalized["signals"] = cleaned
    return normalized


def lambda_handler(event, context):
    # Wrapper to be used as AWS Lambda entry point
    try:
        body = event.get("body")
        if isinstance(body, str):
            payload = json.loads(body)
        else:
            payload = body or event

        norm = normalize_event(payload)
        # In real deployment: write to S3 and emit metrics. For Slice 0 we return normalized object.
        return {"statusCode": 200, "body": json.dumps(norm)}
    except Exception as e:
        return {"statusCode": 400, "body": json.dumps({"error": str(e)})}
