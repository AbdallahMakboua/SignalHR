"""
SignalHR AI Intelligence Layer

Uses Google Vertex AI (Gemini) for explainable, HR-safe explanations of burnout, HiPo, and drift alerts.
No LLM access to raw events or PII; only aggregated features and computed scores.
"""

from ai.gemini_explainer import explain_alert, explain_alerts, ExplanationConfig

__all__ = ["explain_alert", "explain_alerts", "ExplanationConfig"]
