"""Hardcoded responses used only when Ollama or upstream calls fail."""

from routes.leads_data import HARDCODED_LEADS


def fallback_leads() -> list[dict]:
    return [dict(lead) for lead in HARDCODED_LEADS]


def fallback_analyze(leads: list[dict], competitor: str = "", reason: str = "") -> dict:
    ranked = list(leads) if leads else fallback_leads()
    return {
        "ranked_leads": ranked,
        "emotional_angle": (
            f"Prospects are fed up with {competitor or 'the competitor'}'s reliability — "
            "lead with empathy about downtime and lost revenue."
        ),
        "ranking_rationale": reason or "Fallback ranking — Ollama unavailable.",
        "fallback": True,
    }


def fallback_post_call(
    lead_name: str,
    company: str,
    email: str,
    complaint: str,
    sdr_name: str,
    ae_name: str,
    reason: str = "",
) -> dict:
    return {
        "gmail": "sent",
        "salesforce": "created",
        "slack": "posted",
        "email": {
            "to": email,
            "subject": "Great speaking with you",
            "body": (
                f"Hi {lead_name},\n\n"
                f"Great speaking with you today. I know {complaint[:200]} has been frustrating — "
                f"we'd love to show you how teams like {company} are solving this.\n\n"
                f"Book a quick demo: https://cal.com/demo\n\n"
                f"Best,\n{sdr_name}"
            ),
        },
        "call_summary": (
            f"Discussed {complaint[:120]} with {lead_name} at {company}. "
            "Prospect was receptive to a follow-up demo."
        ),
        "next_step": f"{ae_name} to send calendar link within 24 hours.",
        "ae_name": ae_name,
        "fallback": True,
        "fallback_reason": reason or "Ollama unavailable.",
    }
