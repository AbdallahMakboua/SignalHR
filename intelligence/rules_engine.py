"""
Deterministic rules engine for SignalHR MVP.

Generates privacy-safe AI outputs:
- Burnout risk alerts
- HiPo (High Potential) alerts
- Performance drift signals

All scoring is rule-based and explainable (no ML/black-box).
"""

import json
from typing import Dict, Any, List
from datetime import datetime
from uuid import uuid4


def score_user(aggregate: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score a single user aggregate and generate alert payload.
    
    Args:
        aggregate: User aggregate with userId, weekId, signalCounts, features
        
    Returns:
        Alert dict with burnout/hipo/drift scores and explainable reasons
    """
    user_id = aggregate.get("userId", "unknown")
    week_id = aggregate.get("weekId", "unknown")
    signal_counts = aggregate.get("signalCounts", {})
    
    # Extract computed features
    overload_trend = aggregate.get("overload_trend", 0.0)
    context_switch_rate = aggregate.get("context_switch_rate", 0.0)
    collaboration_index = aggregate.get("collaboration_index", 0.0)
    growth_index = aggregate.get("growth_index", 0.0)
    
    # Extract top signals
    meetings = signal_counts.get("meetings", 0)
    messages = signal_counts.get("messages", 0)
    prs = signal_counts.get("prs", 0)
    
    # Burnout scoring (deterministic rules)
    burnout_score = 0.0
    burnout_reasons = []
    
    if meetings >= 4:
        burnout_score += 0.4
        burnout_reasons.append(f"High meeting load ({meetings} meetings)")
    
    if messages >= 30:
        burnout_score += 0.4
        burnout_reasons.append(f"High message volume ({messages} messages)")
    
    if context_switch_rate >= 1.5:
        burnout_score += 0.2
        burnout_reasons.append(f"Elevated context switching (rate: {context_switch_rate:.2f})")
    
    burnout_score = min(burnout_score, 1.0)
    
    # HiPo (High Potential) scoring
    hipo_score = 0.0
    hipo_reasons = []
    
    if prs >= 3:
        hipo_score += 0.5
        hipo_reasons.append(f"Strong contribution velocity ({prs} PRs)")
    
    if growth_index >= 0.3:
        hipo_score += 0.3
        hipo_reasons.append(f"High growth trajectory (index: {growth_index:.2f})")
    
    if collaboration_index >= 1.0:
        hipo_score += 0.2
        hipo_reasons.append(f"Strong collaboration patterns (index: {collaboration_index:.2f})")
    
    hipo_score = min(hipo_score, 1.0)
    
    # Performance drift scoring (proxy)
    drift_score = 0.0
    drift_reasons = []
    
    if meetings >= 4 and prs == 0:
        drift_score = 0.5
        drift_reasons.append("High meetings with no deliverables (potential calendar overload)")
    else:
        drift_score = 0.1
        drift_reasons.append("Baseline variance (no significant drift detected)")
    
    drift_score = min(drift_score, 1.0)
    
    # Generate alert payload
    alert = {
        "alertId": str(uuid4()),
        "userId": user_id,
        "weekId": week_id,
        "burnout": {
            "score": round(burnout_score, 2),
            "reasons": burnout_reasons if burnout_reasons else ["No burnout indicators detected"]
        },
        "hipo": {
            "score": round(hipo_score, 2),
            "reasons": hipo_reasons if hipo_reasons else ["No HiPo signals detected"]
        },
        "performance_drift": {
            "score": round(drift_score, 2),
            "reasons": drift_reasons
        },
        "topSignals": {
            "meetings": meetings,
            "messages": messages,
            "prs": prs
        },
        "createdAt": datetime.utcnow().isoformat() + "Z"
    }
    
    return alert


def score_aggregates(aggregates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Score multiple user aggregates.
    
    Args:
        aggregates: List of user aggregates
        
    Returns:
        List of alert payloads
    """
    alerts = []
    for aggregate in aggregates:
        try:
            alert = score_user(aggregate)
            alerts.append(alert)
        except Exception as e:
            print(f"Error scoring user {aggregate.get('userId', 'unknown')}: {e}")
    
    return alerts


if __name__ == "__main__":
    # Test with sample aggregate
    sample = {
        "userId": "test-user-123",
        "weekId": "2026-W06",
        "signalCounts": {"meetings": 5, "messages": 35, "prs": 4},
        "overload_trend": 4.4,
        "context_switch_rate": 2.2,
        "collaboration_index": 3.52,
        "growth_index": 1.32,
        "createdAt": "2026-02-07T03:00:00Z"
    }
    
    alert = score_user(sample)
    print(json.dumps(alert, indent=2))
