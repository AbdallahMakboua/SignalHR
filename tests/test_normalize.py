import json
from lambdas.normalize_handler import normalize_event


def test_normalize_basic():
    raw = {
        "ingestionId": "ing-1",
        "schemaVersion": 1,
        "timestamp": "2026-02-07T00:00:00Z",
        "userId": "550e8400-e29b-41d4-a716-446655440000",
        "signals": {"meetings": "5", "messages": "20", "notes": "should be dropped"},
        "profile": "alice",
    }

    out = normalize_event(raw)
    assert out["ingestionId"] == "ing-1"
    assert out["schemaVersion"] == 1
    assert out["signals"]["meetings"] == 5
    assert out["signals"]["messages"] == 20
    assert "notes" not in out["signals"]
