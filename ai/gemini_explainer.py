"""
Google Vertex AI Gemini Explainer for SignalHR

This module uses Google Cloud Vertex AI (Gemini) to generate HR-safe, explainable
explanations for burnout, HiPo, and performance drift alerts.

Privacy-First Design:
- Input to Gemini: ONLY aggregated metrics, computed features, alert scores
- NEVER sent: Raw events, messages, user identifiers (except hashed/opaque ID)
- Output: Coaching suggestions, not judgments

Determinism & HR Safety:
- Gemini is non-deterministic (different responses for same input)
- Mitigated by: Consistent prompt structure, temperature=0 (deterministic mode)
- HR-safe guardrails: Prompt explicitly prevents punitive advice

Fallback:
If Gemini is unavailable (no credentials, API errors), falls back to rule-based
explanations (same as intelligence/explainer.py)
"""

import json
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class ExplanationConfig:
    """Configuration for Gemini explanations."""
    project_id: Optional[str] = None  # GCP project ID (optional if set via credentials)
    location: str = "us-central1"      # Vertex AI location
    model_name: str = "gemini-pro"     # Model to use
    temperature: float = 0.0            # Deterministic mode (0.0)
    max_tokens: int = 500              # Response length
    use_gemini: bool = True            # Toggle between Gemini and fallback rule-based


def explain_alert(
    alert: Dict[str, Any],
    aggregate: Dict[str, Any],
    config: Optional[ExplanationConfig] = None
) -> Dict[str, Any]:
    """
    Generate an HR-safe explanation for a single alert using Vertex AI Gemini.

    Args:
        alert: Alert dict with fields:
            - userId: User ID (opaque/hashed)
            - weekId: ISO week ID (e.g., "2026-W06")
            - alertType: "burnout", "hipo", "drift", or "baseline"
            - burnout/hipo/drift: {score: float, reasons: List[str]}
        aggregate: User aggregate dict with fields:
            - signalCounts: {meetings, messages, prs, ...}
            - features: {overload_trend, context_switch_rate, ...}
            - cohort_stats: {meetings_avg, messages_avg, ...}
        config: ExplanationConfig (optional)

    Returns:
        Explanation dict:
        {
            "userId": "...",
            "weekId": "...",
            "alertType": "burnout" | "hipo" | "drift" | "baseline",
            "summary": "Human-readable 1-2 sentence summary",
            "why_flagged": ["Reason 1", "Reason 2", ...],
            "next_best_actions": ["Action 1", "Action 2", ...],
            "ai_confidence": 0.0-1.0 (estimated confidence),
            "generated_at": "ISO timestamp"
        }
    """
    if config is None:
        config = ExplanationConfig()

    # Extract safe fields only (no raw text, messages, or PII)
    user_id = alert.get("userId", "unknown")
    week_id = alert.get("weekId", "unknown")
    alert_type = alert.get("alertType", "baseline")

    # Determine which score to use
    scores = {}
    if "burnout" in alert:
        scores["burnout"] = alert["burnout"].get("score", 0.0)
    if "hipo" in alert:
        scores["hipo"] = alert["hipo"].get("score", 0.0)
    if "drift" in alert:
        scores["drift"] = alert["drift"].get("score", 0.0)

    # Get reasons (already rule-generated, safe to include)
    reasons = []
    if "burnout" in alert and alert["burnout"].get("reasons"):
        reasons.extend(alert["burnout"]["reasons"])
    if "hipo" in alert and alert["hipo"].get("reasons"):
        reasons.extend(alert["hipo"]["reasons"])

    # Safe aggregate data (numeric only)
    signal_counts = aggregate.get("signalCounts", {})
    features = aggregate.get("features", {})
    cohort_stats = aggregate.get("cohort_stats", {})

    # Try Gemini first
    if config.use_gemini:
        try:
            explanation = _call_gemini(
                alert_type=alert_type,
                scores=scores,
                reasons=reasons,
                signal_counts=signal_counts,
                features=features,
                cohort_stats=cohort_stats,
                week_id=week_id,
                config=config
            )
        except Exception as e:
            print(f"⚠️  Gemini unavailable ({str(e)}). Falling back to rule-based explanation.")
            explanation = _fallback_rule_based(
                alert_type=alert_type,
                scores=scores,
                reasons=reasons,
                signal_counts=signal_counts
            )
    else:
        explanation = _fallback_rule_based(
            alert_type=alert_type,
            scores=scores,
            reasons=reasons,
            signal_counts=signal_counts
        )

    # Wrap in result envelope
    return {
        "userId": user_id,
        "weekId": week_id,
        "alertType": alert_type,
        "summary": explanation["summary"],
        "why_flagged": explanation["why_flagged"],
        "next_best_actions": explanation["next_best_actions"],
        "ai_confidence": explanation.get("confidence", 0.7),  # Gemini confidence estimate
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }


def explain_alerts(
    alerts: List[Dict[str, Any]],
    aggregates: Dict[str, Dict[str, Any]],
    config: Optional[ExplanationConfig] = None
) -> List[Dict[str, Any]]:
    """
    Generate explanations for multiple alerts.

    Args:
        alerts: List of alert dicts
        aggregates: Dict mapping userId -> aggregate dict
        config: ExplanationConfig (optional)

    Returns:
        List of explanation dicts (one per alert)
    """
    explanations = []
    for alert in alerts:
        user_id = alert.get("userId", "unknown")
        aggregate = aggregates.get(user_id, {})
        explanation = explain_alert(alert, aggregate, config)
        explanations.append(explanation)
    return explanations


def _call_gemini(
    alert_type: str,
    scores: Dict[str, float],
    reasons: List[str],
    signal_counts: Dict[str, int],
    features: Dict[str, float],
    cohort_stats: Dict[str, float],
    week_id: str,
    config: ExplanationConfig
) -> Dict[str, Any]:
    """
    Call Vertex AI Gemini with a safe, privacy-respecting prompt.

    Note: Requires GOOGLE_APPLICATION_CREDENTIALS environment variable set.
    """
    try:
        from google.cloud import aiplatform
        from google.cloud.aiplatform.gapic.services.prediction_service import PredictionServiceClient
    except ImportError:
        raise ImportError(
            "google-cloud-aiplatform not installed. "
            "Install with: pip install google-cloud-aiplatform"
        )

    # Initialize Vertex AI (requires GOOGLE_APPLICATION_CREDENTIALS)
    try:
        aiplatform.init(project=config.project_id, location=config.location)
    except Exception as e:
        raise RuntimeError(
            f"Failed to initialize Vertex AI. Ensure GOOGLE_APPLICATION_CREDENTIALS is set. Error: {e}"
        )

    # Build safe prompt (no user IDs, messages, or raw content)
    prompt = _build_prompt(
        alert_type=alert_type,
        scores=scores,
        reasons=reasons,
        signal_counts=signal_counts,
        features=features,
        cohort_stats=cohort_stats,
        week_id=week_id
    )

    try:
        # Call Gemini
        model = aiplatform.GenerativeModel(config.model_name)
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": config.temperature,
                "max_output_tokens": config.max_tokens,
            }
        )

        # Parse response (Gemini should return valid JSON)
        response_text = response.text.strip()

        # Try to extract JSON from response (may be wrapped in markdown code blocks)
        if "```json" in response_text:
            json_start = response_text.index("```json") + 7
            json_end = response_text.index("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.index("```") + 3
            json_end = response_text.index("```", json_start)
            response_text = response_text[json_start:json_end].strip()

        result = json.loads(response_text)

        # Validate required fields
        required_fields = ["summary", "why_flagged", "next_best_actions"]
        for field in required_fields:
            if field not in result:
                raise ValueError(f"Gemini response missing required field: {field}")

        result["confidence"] = 0.85  # Gemini confidence estimate
        return result

    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Failed to parse Gemini response as JSON. Response: {response_text}. Error: {e}"
        )


def _build_prompt(
    alert_type: str,
    scores: Dict[str, float],
    reasons: List[str],
    signal_counts: Dict[str, int],
    features: Dict[str, float],
    cohort_stats: Dict[str, float],
    week_id: str
) -> str:
    """
    Build a safe, privacy-respecting prompt for Gemini.

    PRIVACY GUARANTEE:
    - No user identifiers (except opaque IDs)
    - No raw events or messages
    - No timestamps or sequences
    - Only aggregated metrics and computed features
    """

    # Format safe metrics
    metrics_str = f"""
**Signal Counts (This Week):**
- Meetings: {signal_counts.get('meetings', 0)}
- Messages: {signal_counts.get('messages', 0)}
- PRs/Contributions: {signal_counts.get('prs', 0)}
- Context Switches: {signal_counts.get('context_switches', 0)}

**Computed Features:**
- Overload Trend: {features.get('overload_trend', 0.0):.2f}
- Context Switch Rate: {features.get('context_switch_rate', 0.0):.2f}
- Collaboration Index: {features.get('collaboration_index', 0.0):.2f}
- Growth Index: {features.get('growth_index', 0.0):.2f}

**Team Averages (for context):**
- Avg Meetings: {cohort_stats.get('meetings_avg', 0):.1f}
- Avg Messages: {cohort_stats.get('messages_avg', 0):.1f}
- Avg PRs: {cohort_stats.get('prs_avg', 0):.1f}
"""

    # Alert summary
    alert_str = f"**Alert Type:** {alert_type.upper()}\n**Score:** {scores.get(alert_type, 0.0):.1f} / 1.0\n"
    if reasons:
        alert_str += f"**Triggered By:** {', '.join(reasons)}\n"

    # Build prompt
    prompt = f"""You are an HR coaching assistant for a tech company. You help managers understand employee wellbeing signals in a compassionate, non-judgmental way.

**Employee Alert Summary (Week {week_id}):**
{alert_str}
{metrics_str}

**Your Task:**
1. Write a 1-2 sentence summary of what this alert means (in plain English)
2. Explain why this person was flagged (point to specific signal differences vs. team average)
3. Suggest 2-3 concrete, supportive coaching actions (NOT punitive measures)

**IMPORTANT GUIDELINES:**
- Focus on COACHING and WELLBEING, never discipline or judgment
- This is DECISION SUPPORT ONLY, not a diagnosis or mandate
- Avoid medical claims, legal language, or assumptions about performance
- Suggest actions that emphasize balance, growth, and support
- Always frame as "consider" or "explore", never "must"

Return your response as a valid JSON object with this exact structure (no markdown backticks):
{{
  "summary": "1-2 sentence summary of alert meaning",
  "why_flagged": [
    "First reason with data (e.g., 'Meetings (5) exceed team average (2.1) by 2.4x')",
    "Second reason with data",
    "Third reason if applicable"
  ],
  "next_best_actions": [
    "Action 1: Specific, supportive, actionable (e.g., 'Schedule 1:1 to discuss workload')",
    "Action 2: Specific, supportive, actionable",
    "Action 3: Specific, supportive, actionable (optional)"
  ],
  "confidence": 0.8
}}

Remember: You are generating decision support to help managers support their team, not making judgments about performance."""

    return prompt


def _fallback_rule_based(
    alert_type: str,
    scores: Dict[str, float],
    reasons: List[str],
    signal_counts: Dict[str, int]
) -> Dict[str, Any]:
    """
    Fallback to rule-based explanation if Gemini is unavailable.

    This ensures the demo continues even if Google Cloud credentials are missing.
    """
    templates = {
        "burnout": {
            "summary": f"This team member is showing elevated burnout risk indicators (score {scores.get('burnout', 0):.1f}/1.0). Immediate attention recommended to prevent escalation.",
            "why_flagged": reasons or ["High workload detected based on signal analysis"],
            "next_best_actions": [
                "Schedule 1:1 check-in to discuss workload and priorities",
                "Review calendar for non-essential meetings that can be delegated or declined",
                "Explore options for temporary workload redistribution",
                "Ensure PTO balance is healthy and encourage time off if needed"
            ],
            "confidence": 0.7
        },
        "hipo": {
            "summary": f"This team member is demonstrating high-potential (HiPo) signals (score {scores.get('hipo', 0):.1f}/1.0). Consider growth opportunities and retention strategies.",
            "why_flagged": reasons or ["Strong contribution velocity and growth trajectory detected"],
            "next_best_actions": [
                "Initiate career development conversation to understand growth aspirations",
                "Identify stretch assignments or leadership opportunities",
                "Ensure compensation and recognition align with performance level",
                "Consider for succession planning and key talent retention programs"
            ],
            "confidence": 0.7
        },
        "drift": {
            "summary": f"This team member's performance patterns show signs of drift (score {scores.get('drift', 0):.1f}/1.0). Review recent changes and offer support.",
            "why_flagged": reasons or ["Performance pattern change detected"],
            "next_best_actions": [
                "Conduct calendar audit to understand time allocation changes",
                "Shield focus time for deep work if meetings increased",
                "Check in on project scope and dependencies",
                "Offer resources or mentoring if needed"
            ],
            "confidence": 0.6
        },
        "baseline": {
            "summary": f"This team member's signals are within normal operating ranges (score {scores.get('burnout', 0):.1f}/1.0 burnout risk).",
            "why_flagged": ["Signals align with team baseline"],
            "next_best_actions": [
                "Continue regular 1:1s to stay connected",
                "Monitor for any changes in patterns",
                "Celebrate balance and sustainable pace"
            ],
            "confidence": 0.8
        }
    }

    return templates.get(alert_type, templates["baseline"])


if __name__ == "__main__":
    # Test with sample alert and aggregate
    sample_alert = {
        "userId": "test-user-123",
        "weekId": "2026-W06",
        "alertType": "burnout",
        "burnout": {
            "score": 1.0,
            "reasons": ["High meeting load (5 meetings)", "High communication load (37 messages)"]
        }
    }

    sample_aggregate = {
        "signalCounts": {
            "meetings": 5,
            "messages": 37,
            "prs": 2,
            "context_switches": 8
        },
        "features": {
            "overload_trend": 0.8,
            "context_switch_rate": 0.6,
            "collaboration_index": 0.7,
            "growth_index": 0.4
        },
        "cohort_stats": {
            "meetings_avg": 2.1,
            "messages_avg": 15.0,
            "prs_avg": 1.5
        }
    }

    # Test with rule-based fallback (Gemini disabled)
    config = ExplanationConfig(use_gemini=False)
    result = explain_alert(sample_alert, sample_aggregate, config)
    print("Rule-based explanation:")
    print(json.dumps(result, indent=2))

    # To test with real Gemini:
    # 1. Set GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
    # 2. Change use_gemini=True
    # 3. Run: python3 -c "from ai.gemini_explainer import explain_alert; ..."
