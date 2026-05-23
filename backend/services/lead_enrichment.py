"""Assign demo email + phone to Twitter leads (hackathon / demo)."""

from __future__ import annotations

import random
import re

_DOMAINS = ("inbox.io", "contact.co", "mailhub.net", "reach.dev", "leads.app")


def _slug(lead: dict) -> str:
    handle = (lead.get("username") or "user").lstrip("@").lower()
    handle = re.sub(r"[^a-z0-9]", "", handle)
    if handle:
        return handle[:24]
    name = (lead.get("display_name") or "lead").lower()
    return re.sub(r"[^a-z0-9]", "", name.split()[0])[:24] or "lead"


def mock_contact_for_lead(lead: dict) -> dict:
    """Stable random email + US phone per lead id/handle."""
    seed_src = str(lead.get("id") or lead.get("username") or lead.get("url") or "")
    rng = random.Random(hash(seed_src) & 0xFFFFFFFF)

    slug = _slug(lead)
    email = f"{slug}{rng.randint(10, 99)}@{rng.choice(_DOMAINS)}"

    area = rng.randint(200, 999)
    prefix = rng.randint(200, 999)
    line = rng.randint(1000, 9999)
    phone = f"+1 ({area}) {prefix} {line}"

    display = (lead.get("display_name") or slug).strip()
    return {
        "email": email,
        "phone": phone,
        "name": display,
        "status": "demo",
    }


def enrich_twitter_leads(
    leads: list[dict],
    *,
    max_leads: int = 10,
    **_kwargs,
) -> list[dict]:
    """Attach randomized email and phone to each lead."""
    enriched: list[dict] = []
    for lead in leads[:max_leads]:
        contact = mock_contact_for_lead(lead)
        enriched.append(
            {
                **lead,
                "email": contact["email"],
                "phone": contact["phone"],
                "contact": contact,
            }
        )
    return enriched
