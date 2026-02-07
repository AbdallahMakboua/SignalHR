"""
FastAPI server simulating AWS API Gateway.

Replaces API Gateway v2 HTTP API for local development.
- Accepts POST /events with JSON payloads
- Forwards events to in-memory EventBridge bus
- Returns HTTP 202 (Accepted) on success
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any, Dict, Optional
from datetime import datetime
import os
import json

# Import local simulators
from core.bus import EventBus, default_pipes_filter, default_pipes_transform
from core.queue import QueuePair


# Pydantic models for request validation
class EventPayload(BaseModel):
    """
    DC-ING-V1 schema for ingestion events.
    
    Required fields: ingestionId, schemaVersion, userId, timestamp, source, signalCounts
    Optional fields: eventType, profile (for synthetic generator)
    Privacy: signalCounts must be numeric only (no free text)
    """
    ingestionId: str
    schemaVersion: int
    userId: str
    timestamp: str
    source: str
    signalCounts: Dict[str, int]  # Only integer signal counts (privacy: no text fields)
    eventType: Optional[str] = None  # Optional; default set internally if missing
    profile: Optional[str] = None  # Optional: synthetic generator profile name
    
    class Config:
        extra = "forbid"  # Reject unexpected fields (privacy enforcement)


# Global simulator instances
app = FastAPI(title="SignalHR Local Simulator API")
bus: Optional[EventBus] = None
queue_pair: Optional[QueuePair] = None


def _sanitize_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _sanitize_payload(v) for k, v in value.items()}
    if isinstance(value, list):
        return [type(v).__name__ for v in value]
    return type(value).__name__


def _sanitize_errors(errors: Any) -> Any:
    sanitized = []
    for err in errors:
        sanitized.append({k: err.get(k) for k in ("loc", "msg", "type") if k in err})
    return sanitized


def _get_demo_dir() -> str:
    path = "/tmp/signalhr_demo_dir.txt"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read().strip()
    return "artifacts/local_demo_latest"


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    demo_dir = _get_demo_dir()
    os.makedirs(demo_dir, exist_ok=True)
    log_path = os.path.join(demo_dir, "validation_errors.log")

    try:
        body_bytes = await request.body()
        body_json = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
    except Exception:
        body_json = {"_raw": "unparseable"}

    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "path": str(request.url.path),
        "method": request.method,
        "errors": _sanitize_errors(exc.errors()),
        "body_types": _sanitize_payload(body_json),
    }

    with open(log_path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")

    print(f"422 validation error logged -> {log_path} ({len(exc.errors())} errors)")
    return JSONResponse(status_code=422, content={"detail": _sanitize_errors(exc.errors())})


@app.on_event("startup")
async def startup():
    """Initialize simulators on startup."""
    global bus, queue_pair

    bus = EventBus(name="signalhr-bus-dev")
    queue_pair = QueuePair()

    # Set up Pipes filter and transform
    bus.set_filter(default_pipes_filter)
    bus.set_transform(default_pipes_transform)

    # Subscribe to queue
    def queue_subscriber(event: Dict):
        queue_pair.send_message(event)

    bus.register_subscriber(queue_subscriber)

    print("✓ Local simulator initialized (EventBridge bus + SQS queue)")


@app.post("/events")
async def post_events(payload: EventPayload):
    """
    POST /events endpoint (replaces API Gateway).

    Accepts event payloads and routes to EventBridge bus.

    Args:
        payload: Event dict matching DC-ING-V1 schema

    Returns:
        HTTP 202 (Accepted) on success
    """
    if not bus:
        raise HTTPException(status_code=500, detail="Bus not initialized")

    event_type = payload.eventType or "signal.ingestion.v1"

    detail = payload.dict()
    if "signalCounts" in detail and "signals" not in detail:
        detail["signals"] = detail["signalCounts"]

    # Convert payload to EventBridge format
    event = {
        "Source": payload.source,
        "DetailType": event_type,
        "Detail": detail
    }

    # Put to bus (applies Pipes filter/transform)
    result = bus.put_events([event])

    if result["FailedEntryCount"] > 0:
        # Event was filtered or validation failed
        failed = result["Entries"][0]
        return JSONResponse(
            status_code=400,
            content={
                "error": failed.get("ErrorCode", "ValidationError"),
                "message": failed.get("ErrorMessage", "Event rejected")
            }
        )

    # Success: event accepted and routed to queue
    event_id = result["Entries"][0].get("EventId", "unknown")
    return JSONResponse(
        status_code=202,
        content={
            "accepted": True,
            "ingestionId": payload.ingestionId,
            "eventType": event_type
        }
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "bus": bus is not None,
        "queue": queue_pair is not None
    }


@app.get("/metrics/bus")
async def get_bus_metrics():
    """Get EventBridge bus metrics."""
    if not bus:
        return {"error": "Bus not initialized"}

    return {
        "busName": bus.name,
        "eventCount": len(bus.events),
        "events": bus.events
    }


@app.get("/metrics/queue")
async def get_queue_metrics():
    """Get SQS queue metrics."""
    if not queue_pair:
        return {"error": "Queue not initialized"}

    depth = queue_pair.get_queue_depth()
    return {
        "main": depth["main"],
        "dlq": depth["dlq"]
    }


def get_bus():
    """Get global bus instance (for external usage)."""
    return bus


def get_queue_pair():
    """Get global queue pair instance (for external usage)."""
    return queue_pair


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
