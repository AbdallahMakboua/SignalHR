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
from datetime import datetime


def normalize_event(event: Dict[str, Any]) -> Dict[str, Any]:
    # Log incoming keys for debugging (no values to preserve privacy)
    try:
        print(f"normalize_event keys: {sorted(event.keys())}")
    except Exception:
        print("normalize_event keys: <unavailable>")

    # Basic validation
    if event.get("schemaVersion") != 1:
        raise ValueError("Unsupported schemaVersion")

    user_id = event.get("userId")
    if not user_id:
        raise ValueError("Missing userId")

    timestamp = event.get("timestamp")
    if not timestamp:
        raise ValueError("Missing timestamp")

    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        iso_year, iso_week, _ = dt.isocalendar()
        week_id = f"{iso_year}-W{iso_week:02d}"
    except Exception as exc:
        raise ValueError(f"Invalid timestamp: {timestamp}") from exc

    normalized = {
        "ingestionId": event.get("ingestionId"),
        "schemaVersion": 1,
        "timestamp": timestamp,
        "userId": user_id,
        "weekId": week_id,
        "profile": event.get("profile"),
        "source": event.get("source"),
    }

    signals = event.get("signals") or event.get("signalCounts") or {}
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

    normalized["signalCounts"] = cleaned
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
