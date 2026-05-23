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


def fallback_apollo(
    enriched_leads: list[dict] | None = None,
    reason: str = "",
) -> dict:
    block: dict = {
        "authorized": True,
        "fallback": True,
        "connected_account": {
            "connection_name": "apollo-demo",
            "identifier": "demo@rivalintel.app",
            "status": "ACTIVE",
            "provider": "APOLLO",
        },
        "list_sequences": {
            "data": {
                "emailer_campaigns": [
                    {"id": "seq-demo-1", "name": "Competitor Outage Follow-up"},
                    {"id": "seq-demo-2", "name": "Payment Reliability Outreach"},
                ],
                "pagination": {
                    "total_entries": 2,
                    "page": 1,
                    "total_pages": 1,
                    "per_page": 25,
                },
            },
        },
        "fallback_reason": reason or "Apollo/Scalekit unavailable — demo Apollo block",
    }
    if enriched_leads:
        block["enriched_leads"] = enriched_leads
        block["enrichment_summary"] = {
            "attempted": len(enriched_leads),
            "matched": len(enriched_leads),
            "source": "demo_random",
            "note": "Randomized email and +1 (XXX) XXX XXXX phone for demo",
        }
    return block


def fallback_auth_link(reason: str = "") -> dict:
    return {
        "link": None,
        "already_connected": True,
        "connection_name": "apollo-demo",
        "fallback": True,
        "fallback_reason": reason or "Apollo demo mode — no OAuth link needed",
        "connected_account": {
            "identifier": "demo@rivalintel.app",
            "status": "ACTIVE",
            "provider": "APOLLO",
        },
    }


def fallback_apollo_status(reason: str = "") -> dict:
    return {
        "connection_name": "apollo-demo",
        "identifier": "demo@rivalintel.app",
        "status": "ACTIVE",
        "provider": "APOLLO",
        "fallback": True,
        "fallback_reason": reason or "Scalekit unavailable — demo status",
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
