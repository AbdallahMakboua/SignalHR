"""
In-memory SQS queue simulator with DLQ.

Replaces AWS SQS for local development.
- FIFO queue semantics
- Optional redrive to DLQ on processing failure
- Consumer interface for Lambda subscriptions
"""

import json
from typing import Any, Callable, Dict, List, Optional
from collections import deque
from datetime import datetime


class Queue:
    """In-memory queue simulating AWS SQS."""

    def __init__(self, name: str = "signalhr-ingest-queue-dev", max_receive_count: int = 3):
        self.name = name
        self.messages: deque = deque()  # FIFO
        self.dlq: Optional["Queue"] = None
        self.max_receive_count = max_receive_count
        self.consumer: Optional[Callable] = None
        self.message_counter = 0

    def attach_dlq(self, dlq: "Queue"):
        """Attach a dead-letter queue."""
        self.dlq = dlq

    def register_consumer(self, handler: Callable[[Dict], bool]):
        """Register a Lambda consumer. Handler returns True if successful."""
        self.consumer = handler

    def send_message(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate SQS SendMessage API.

        Args:
            body: Message dict (typically event from EventBridge)

        Returns:
            Response with MessageId
        """
        message_id = f"msg-{self.message_counter}"
        self.message_counter += 1

        message = {
            "MessageId": message_id,
            "Body": body,
            "Attributes": {
                "ApproximateReceiveCount": "0"
            },
            "Timestamp": datetime.utcnow().isoformat()
        }

        self.messages.append(message)
        return {"MessageId": message_id}

    def receive_messages(self, max_messages: int = 1) -> List[Dict[str, Any]]:
        """
        Simulate SQS ReceiveMessage API.

        Args:
            max_messages: Max messages to receive

        Returns:
            List of messages
        """
        received = []
        for _ in range(min(max_messages, len(self.messages))):
            if self.messages:
                msg = self.messages.popleft()
                received.append(msg)
        return received

    def process_messages(self) -> Dict[str, Any]:
        """
        Process all messages in queue using registered consumer.

        Returns:
            Stats dict with processed, failed, dlq counts
        """
        if not self.consumer:
            return {"processed": 0, "failed": 0, "dlq": 0}

        processed = 0
        failed = 0
        dlq_count = 0

        while self.messages:
            msg = self.messages.popleft()
            try:
                success = self.consumer(msg["Body"])
                if success:
                    processed += 1
                else:
                    failed += 1
                    # Send to DLQ if available
                    if self.dlq:
                        self.dlq.send_message(msg["Body"])
                        dlq_count += 1
            except Exception as e:
                failed += 1
                print(f"Consumer error: {e}")
                if self.dlq:
                    self.dlq.send_message(msg["Body"])
                    dlq_count += 1

        return {
            "processed": processed,
            "failed": failed,
            "dlq": dlq_count
        }

    def get_message_count(self) -> int:
        """Get number of messages in queue."""
        return len(self.messages)

    def clear(self):
        """Clear all messages (for testing)."""
        self.messages.clear()
        self.message_counter = 0


class QueuePair:
    """Main queue with attached DLQ."""

    def __init__(self, main_name: str = "signalhr-ingest-queue-dev",
                 dlq_name: str = "signalhr-ingest-dlq-dev"):
        self.main = Queue(name=main_name)
        self.dlq = Queue(name=dlq_name)
        self.main.attach_dlq(self.dlq)

    def send_message(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Send message to main queue."""
        return self.main.send_message(body)

    def register_consumer(self, handler: Callable[[Dict], bool]):
        """Register Lambda consumer."""
        self.main.register_consumer(handler)

    def process_messages(self) -> Dict[str, Any]:
        """Process all messages and return stats."""
        return self.main.process_messages()

    def get_queue_depth(self) -> Dict[str, int]:
        """Get message counts for both queues."""
        return {
            "main": self.main.get_message_count(),
            "dlq": self.dlq.get_message_count()
        }

    def get_dlq_messages(self) -> List[Dict[str, Any]]:
        """Get all DLQ messages (for inspection)."""
        # Return without removing (DLQ is for inspection)
        return list(self.dlq.messages)

    def clear(self):
        """Clear both queues."""
        self.main.clear()
        self.dlq.clear()
