"""
Integration test: Full pipeline from event ingestion to aggregates.

Tests the local simulator end-to-end:
1. Create event
2. POST to /events (API)
3. Verify event routed to queue (bus → Pipes → queue)
4. Process queue with normalize handler
5. Verify aggregates stored
"""

import pytest
import json
import sys
from datetime import datetime
from pathlib import Path

# Add repo to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from core.bus import EventBus, default_pipes_filter, default_pipes_transform
from core.queue import QueuePair
from store.aggregates_store import AggregatesStore
from lambdas.normalize_handler import normalize_event


def test_full_pipeline():
    """Test complete flow: event → bus → queue → normalize → aggregates."""

    # Initialize simulators
    bus = EventBus(name="test-bus")
    bus.set_filter(default_pipes_filter)
    bus.set_transform(default_pipes_transform)

    queue_pair = QueuePair()
    store = AggregatesStore(db_path="/tmp/test_aggregates.db")
    store.clear()

    # Subscribe queue to bus
    def queue_subscriber(event):
        queue_pair.send_message(event)

    bus.register_subscriber(queue_subscriber)

    # Register Lambda consumer (normalize + aggregate)
    def lambda_consumer(event):
        try:
            # Normalize the event
            normalized = normalize_event(event)

            # Compute simple aggregate (sum signals)
            user_id = normalized.get("userId", "unknown")
            week_id = "2026-W06"

            signals = normalized.get("signals", {})
            total_signals = sum(v for v in signals.values() if isinstance(v, (int, float)))

            # Store aggregate
            aggregate = {
                "userId": user_id,
                "weekId": week_id,
                "signalCounts": signals,
                "overload_trend": total_signals * 0.1,  # Simple heuristic
                "context_switch_rate": total_signals * 0.05,
                "collaboration_index": total_signals * 0.08,
                "growth_index": total_signals * 0.03,
                "createdAt": datetime.utcnow().isoformat()
            }
            store.put_item(aggregate)
            return True
        except Exception as e:
            print(f"Lambda error: {e}")
            return False

    queue_pair.register_consumer(lambda_consumer)

    # Create test event (matching DC-ING-V1)
    test_event = {
        "Source": "synthetic-generator",
        "DetailType": "signal_event",
        "Detail": {
            "schemaVersion": 1,
            "ingestionId": "evt-test-001",
            "userId": "alice-uuid",
            "timestamp": datetime.utcnow().isoformat(),
            "source": "generator",
            "eventType": "signal_event",
            "signals": {
                "meetings": 5,
                "messages": 10,
                "prs": 2
            },
            "metadata": "should be dropped"  # Non-signal field
        }
    }

    # PUT event to bus
    result = bus.put_events([test_event])
    assert result["FailedEntryCount"] == 0, "Event should be accepted by bus"
    assert len(result["Entries"]) == 1, "One entry should be returned"

    # Verify event in bus
    bus_events = bus.get_events()
    assert len(bus_events) == 1, "Event should be in bus"
    assert bus_events[0]["Detail"]["signals"] == {"meetings": 5, "messages": 10, "prs": 2}, \
        "Signals should be preserved"
    assert "metadata" not in bus_events[0]["Detail"], \
        "Non-signal fields should be dropped by Pipes transform"

    # Verify queue received event
    queue_depth = queue_pair.get_queue_depth()
    assert queue_depth["main"] == 1, "Event should be in queue"
    assert queue_depth["dlq"] == 0, "No events should be in DLQ yet"

    # Process queue (run Lambda consumer)
    stats = queue_pair.process_messages()
    assert stats["processed"] == 1, "Event should be processed"
    assert stats["failed"] == 0, "No events should fail"
    assert stats["dlq"] == 0, "No events should go to DLQ"

    # Verify aggregate stored
    aggregate = store.get_item("alice-uuid", "2026-W06")
    assert aggregate is not None, "Aggregate should be stored"
    assert aggregate["userId"] == "alice-uuid"
    assert aggregate["weekId"] == "2026-W06"
    assert aggregate["signalCounts"]["meetings"] == 5
    assert aggregate["signalCounts"]["messages"] == 10
    assert aggregate["signalCounts"]["prs"] == 2
    assert aggregate["overload_trend"] == 1.7, "Overload trend should be calculated"

    # Verify normalize dropped non-numeric fields
    stored_signals = aggregate["signalCounts"]
    assert isinstance(stored_signals["meetings"], int)
    assert "metadata" not in stored_signals, "Metadata should not be in aggregate"

    print("✓ Full pipeline test PASSED")


def test_invalid_event_to_dlq():
    """Test that invalid events go to DLQ."""

    bus = EventBus(name="test-bus")
    bus.set_filter(default_pipes_filter)
    bus.set_transform(default_pipes_transform)

    queue_pair = QueuePair()

    def queue_subscriber(event):
        queue_pair.send_message(event)

    bus.register_subscriber(queue_subscriber)

    # Create invalid event (missing required field)
    invalid_event = {
        "Source": "test",
        "DetailType": "test",
        "Detail": {
            "schemaVersion": 1,
            # Missing ingestionId, userId, etc.
            "signals": {"test": 1}
        }
    }

    # PUT to bus
    result = bus.put_events([invalid_event])
    assert result["FailedEntryCount"] == 1, "Invalid event should be rejected"

    # Verify queue is empty (event was filtered)
    queue_depth = queue_pair.get_queue_depth()
    assert queue_depth["main"] == 0, "Invalid event should not reach queue"
    assert queue_depth["dlq"] == 0, "Invalid event filtered at bus level, not in DLQ"

    print("✓ Invalid event filtering test PASSED")


if __name__ == "__main__":
    test_full_pipeline()
    test_invalid_event_to_dlq()
    print("\n✓ All integration tests PASSED")
