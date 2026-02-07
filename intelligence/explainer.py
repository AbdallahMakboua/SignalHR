"""
AI Explainability layer for SignalHR.

Converts rule-based alerts into human-readable explanations
suitable for managers and HR stakeholders.

No LLM required - uses deterministic templates with alert data.
"""

from typing import Dict, Any, List


def explain_alert(alert: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate human-readable explanation for an alert.
    
    Args:
        alert: Alert dict with burnout/hipo/drift scores and reasons
        
    Returns:
        Explanation dict with summary, why_flagged, and next_best_actions
    """
    user_id = alert.get("userId", "unknown")
    week_id = alert.get("weekId", "unknown")
    
    burnout = alert.get("burnout", {})
    hipo = alert.get("hipo", {})
    drift = alert.get("performance_drift", {})
    top_signals = alert.get("topSignals", {})
    
    burnout_score = burnout.get("score", 0.0)
    hipo_score = hipo.get("score", 0.0)
    drift_score = drift.get("score", 0.0)
    
    # Determine primary alert type
    primary_type = "baseline"
    if burnout_score >= 0.7:
        primary_type = "burnout"
    elif hipo_score >= 0.7:
        primary_type = "hipo"
    elif drift_score >= 0.5:
        primary_type = "drift"
    
    # Generate summary
    if primary_type == "burnout":
        summary = f"This team member is showing elevated burnout risk indicators during {week_id}. Immediate attention recommended to prevent escalation."
    elif primary_type == "hipo":
        summary = f"This team member is demonstrating high-potential (HiPo) signals during {week_id}. Consider growth opportunities and retention strategies."
    elif primary_type == "drift":
        summary = f"This team member's performance patterns show signs of drift during {week_id}. Calendar optimization may be needed."
    else:
        summary = f"This team member's activity patterns during {week_id} are within normal operating ranges. No immediate action required."
    
    # Generate why_flagged explanations (convert reasons to sentences)
    why_flagged = []
    
    if burnout_score >= 0.5:
        for reason in burnout.get("reasons", []):
            if "meeting load" in reason.lower():
                why_flagged.append(f"Meeting volume exceeds healthy thresholds ({top_signals.get('meetings', 0)} meetings this week).")
            elif "message volume" in reason.lower():
                why_flagged.append(f"Communication load is unsustainably high ({top_signals.get('messages', 0)} messages this week).")
            elif "context switching" in reason.lower():
                why_flagged.append("Frequent task switching patterns detected, indicating potential cognitive overload.")
    
    if hipo_score >= 0.5:
        for reason in hipo.get("reasons", []):
            if "contribution velocity" in reason.lower():
                why_flagged.append(f"Strong delivery output with {top_signals.get('prs', 0)} contributions this week.")
            elif "growth trajectory" in reason.lower():
                why_flagged.append("Sustained upward performance trend indicates high growth potential.")
            elif "collaboration patterns" in reason.lower():
                why_flagged.append("Demonstrates strong cross-functional collaboration and influence.")
    
    if drift_score >= 0.5 and "calendar overload" in str(drift.get("reasons", [])).lower():
        why_flagged.append("High meeting density with reduced deliverable output suggests calendar is blocking productive work.")
    
    if not why_flagged:
        why_flagged.append("Activity patterns align with expected norms for role and tenure.")
    
    # Generate next best actions
    next_best_actions = []
    
    if primary_type == "burnout":
        next_best_actions.extend([
            "Schedule 1:1 check-in to discuss workload and priorities",
            "Review calendar for non-essential meetings that can be delegated or declined",
            "Explore options for temporary workload redistribution",
            "Ensure PTO balance is healthy and encourage time off if needed"
        ])
    elif primary_type == "hipo":
        next_best_actions.extend([
            "Initiate career development conversation to understand growth aspirations",
            "Identify stretch assignments or leadership opportunities",
            "Ensure compensation and recognition align with performance level",
            "Consider for succession planning and key talent retention programs"
        ])
    elif primary_type == "drift":
        next_best_actions.extend([
            "Conduct calendar audit to identify time-wasting meetings",
            "Set clear priorities and shield focus time for deep work",
            "Review project scope to ensure alignment with strategic goals"
        ])
    else:
        next_best_actions.extend([
            "Continue current management approach",
            "Schedule regular check-ins to maintain engagement"
        ])
    
    return {
        "userId": user_id,
        "weekId": week_id,
        "alertType": primary_type,
        "summary": summary,
        "why_flagged": why_flagged,
        "next_best_actions": next_best_actions,
        "scores": {
            "burnout": burnout_score,
            "hipo": hipo_score,
            "performance_drift": drift_score
        }
    }


def explain_alerts(alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Generate explanations for multiple alerts.
    
    Args:
        alerts: List of alert dicts
        
    Returns:
        List of explanation dicts
    """
    explanations = []
    for alert in alerts:
        try:
            explanation = explain_alert(alert)
            explanations.append(explanation)
        except Exception as e:
            print(f"Error explaining alert for user {alert.get('userId', 'unknown')}: {e}")
    
    return explanations


if __name__ == "__main__":
    # Test with sample alert
    import json
    
    sample_alert = {
        "alertId": "test-123",
        "userId": "user-456",
        "weekId": "2026-W06",
        "burnout": {
            "score": 0.8,
            "reasons": [
                "High meeting load (5 meetings)",
                "High message volume (35 messages)"
            ]
        },
        "hipo": {
            "score": 0.3,
            "reasons": ["High growth trajectory (index: 1.26)"]
        },
        "performance_drift": {
            "score": 0.1,
            "reasons": ["Baseline variance (no significant drift detected)"]
        },
        "topSignals": {
            "meetings": 5,
            "messages": 35,
            "prs": 2
        },
        "createdAt": "2026-02-07T03:00:00Z"
    }
    
    explanation = explain_alert(sample_alert)
    print(json.dumps(explanation, indent=2))
