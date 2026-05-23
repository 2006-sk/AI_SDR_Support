import os

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from routes.fallbacks import fallback_apollo, fallback_apollo_status, fallback_auth_link
from services.lead_enrichment import enrich_twitter_leads
from services.scalekit_apollo import (
    apollo_connection_name,
    apollo_list_sequences,
    get_auth_link,
    resolve_apollo_account,
    scalekit_configured,
)
from services.twitter_apify import scrape_twitter

load_dotenv()

router = APIRouter(prefix="/enrich", tags=["enrich"])


class EnrichRequest(BaseModel):
    competitor: str
    identifier: str | None = None
    connection_name: str | None = None
    max_tweets: int = Field(default=10, ge=1, le=25)
    enrich_emails: bool = Field(
        default=True,
        description="Attach randomized demo email + phone to each Twitter lead",
    )


def _apify_key() -> str:
    key = os.getenv("APIFY_API_KEY", "").strip()
    if not key:
        raise HTTPException(status_code=500, detail="APIFY_API_KEY not set")
    return key


def _attach_enrichment_summary(apollo_block: dict, enriched_leads: list[dict]) -> None:
    apollo_block["enriched_leads"] = enriched_leads
    apollo_block["enrichment_summary"] = {
        "attempted": len(enriched_leads),
        "matched": len(enriched_leads),
        "source": "demo_random",
        "note": "Randomized email and +1 (XXX) XXX XXXX phone for demo",
    }


def _apollo_block_from_scalekit(
    conn: str,
    identifier: str | None,
    enriched_leads: list[dict],
) -> dict:
    account = resolve_apollo_account(conn, identifier)
    sequences = apollo_list_sequences(conn, identifier)
    block: dict = {
        "authorized": True,
        "fallback": False,
        "connected_account": account,
        "list_sequences": sequences,
    }
    if enriched_leads:
        _attach_enrichment_summary(block, enriched_leads)
    return block


@router.get("/auth")
def enrich_auth_link(
    connection_name: str | None = Query(default=None),
    identifier: str | None = Query(default=None),
):
    """Return Scalekit OAuth link, or demo response if Apollo already connected / Scalekit fails."""
    conn = connection_name or apollo_connection_name()

    if scalekit_configured():
        try:
            account = resolve_apollo_account(conn, identifier)
            if str(account.get("status", "")).upper() == "ACTIVE":
                return {
                    "link": None,
                    "already_connected": True,
                    "connection_name": conn,
                    "connected_account": account,
                }
        except ValueError:
            pass
        except Exception:
            return fallback_auth_link("Could not resolve account — demo mode")

        try:
            return get_auth_link(connection_name=conn, identifier=identifier)
        except Exception as exc:
            return fallback_auth_link(str(exc)[:200])

    return fallback_auth_link("Scalekit not configured")


@router.get("/apollo/status")
def apollo_status(
    connection_name: str | None = Query(default=None),
    identifier: str | None = Query(default=None),
):
    """Check Apollo connected account; hardcoded demo if Scalekit fails."""
    if not scalekit_configured():
        return fallback_apollo_status("Scalekit not configured")
    try:
        return resolve_apollo_account(connection_name, identifier)
    except Exception as exc:
        return fallback_apollo_status(str(exc)[:200])


@router.post("")
def enrich(body: EnrichRequest):
    """Scrape Twitter via Apify; Apollo via Scalekit with hardcoded fallback on failure."""
    competitor = body.competitor.strip()
    if not competitor:
        raise HTTPException(status_code=400, detail="competitor is required")

    conn = body.connection_name or apollo_connection_name()

    leads, raw_items, twitter_err = scrape_twitter(
        _apify_key(),
        competitor,
        max_items=body.max_tweets,
    )

    enriched_leads: list[dict] = []
    if body.enrich_emails and leads:
        enriched_leads = enrich_twitter_leads(leads, max_leads=body.max_tweets)

    twitter_block: dict = {
        "actor": "kaitoeasyapi/twitter-x-data-tweet-scraper-pay-per-result-cheapest",
        "search_terms": [f"{competitor} problems", f"{competitor} broken", f"{competitor} outage"],
        "raw_count": len(raw_items),
        "lead_count": len(enriched_leads) or len(leads),
        "leads": enriched_leads or leads,
        "error": twitter_err,
    }

    apollo_block: dict
    if scalekit_configured():
        try:
            apollo_block = _apollo_block_from_scalekit(conn, body.identifier, enriched_leads)
        except Exception as exc:
            apollo_block = fallback_apollo(enriched_leads, str(exc)[:200])
    else:
        apollo_block = fallback_apollo(enriched_leads, "Scalekit not configured")

    return {
        "competitor": competitor,
        "twitter": twitter_block,
        "apollo": apollo_block,
    }
