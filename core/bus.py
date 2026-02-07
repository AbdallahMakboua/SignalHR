"""
In-memory EventBridge simulator.

Replaces AWS EventBridge for local development.
- Accepts events via put_events()
- Applies Pipes filter/transform logic
- Routes to consumers (queue, handlers)
"""

import json
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime


class EventBus:
    """In-memory event bus simulating AWS EventBridge."""

    def __init__(self, name: str = "signalhr-bus-dev"):
        self.name = name
        self.events: List[Dict[str, Any]] = []
        self.subscribers: List[Callable] = []
        self.filter_func: Optional[Callable] = None
        self.transform_func: Optional[Callable] = None

    def register_subscriber(self, handler: Callable):
        """Register a function to be called when events are put."""
        self.subscribers.append(handler)

    def set_filter(self, func: Callable[[Dict], bool]):
        """Set Pipes filter function (returns True to keep event)."""
        self.filter_func = func

    def set_transform(self, func: Callable[[Dict], Dict]):
        """Set Pipes transform function (modifies event)."""
        self.transform_func = func

    def put_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Simulate EventBridge PutEvents API.

        Args:
            events: List of event dicts with Source, DetailType, Detail

        Returns:
            Response with FailedEntryCount and Entries
        """
        failed_count = 0
        entries = []

        for i, event in enumerate(events):
            # Validate required fields
            if "Source" not in event or "DetailType" not in event or "Detail" not in event:
                failed_count += 1
                entries.append({
                    "ErrorCode": "MissingRequiredParameter",
                    "ErrorMessage": "Source, DetailType, and Detail are required"
                })
                continue

            # Apply Pipes filter (whitelist pattern)
            if self.filter_func and not self.filter_func(event):
                failed_count += 1
                entries.append({
                    "ErrorCode": "FilteredOut",
                    "ErrorMessage": "Event filtered by Pipes"
                })
                continue

            # Apply Pipes transform
            transformed_event = event
            if self.transform_func:
                transformed_event = self.transform_func(event)

            # Store event
            event_id = f"evt-{len(self.events)}-{i}"
            transformed_event["_eventId"] = event_id
            transformed_event["_timestamp"] = datetime.utcnow().isoformat()
            self.events.append(transformed_event)

            entries.append({"EventId": event_id})

            # Notify subscribers
            for subscriber in self.subscribers:
                try:
                    subscriber(transformed_event)
                except Exception as e:
                    print(f"Subscriber error: {e}")

        return {
            "FailedEntryCount": failed_count,
            "Entries": entries
        }

    def get_events(self) -> List[Dict[str, Any]]:
        """Retrieve all events stored in the bus."""
        return self.events

    def clear(self):
        """Clear all events (for testing)."""
        self.events = []


def default_pipes_filter(event: Dict) -> bool:
    """
    Default Pipes filter: whitelist schema validation.
    
    Accept events matching DC-ING-V1 schema.
    Reject events with missing required fields.
    """
    detail = event.get("Detail", {})
    if isinstance(detail, str):
        try:
            detail = json.loads(detail)
        except:
            return False

    required_fields = ["schemaVersion", "ingestionId", "userId", "timestamp", "source", "signals"]
    for field in required_fields:
        if field not in detail:
            return False

    if detail.get("schemaVersion") != 1:
        return False

    if not isinstance(detail.get("signals"), dict):
        return False

    return True


def default_pipes_transform(event: Dict) -> Dict:
    """
    Default Pipes transform: enforce numeric-only signals.
    
    Drops non-numeric signal fields (privacy rule).
    """
    detail = event.get("Detail", {})
    if isinstance(detail, str):
        detail = json.loads(detail)

    signals = detail.get("signals", {})
    # Keep only numeric signals
    numeric_signals = {k: v for k, v in signals.items() if isinstance(v, (int, float))}
    detail["signals"] = numeric_signals

    event["Detail"] = detail
    return event
