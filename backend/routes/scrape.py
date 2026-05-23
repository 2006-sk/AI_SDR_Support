import os

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.twitter_apify import scrape_twitter

load_dotenv()

router = APIRouter(prefix="/scrape", tags=["scrape"])


class ScrapeRequest(BaseModel):
    competitor: str


def _api_key() -> str:
    key = os.getenv("APIFY_API_KEY", "").strip()
    if not key:
        raise HTTPException(status_code=500, detail="APIFY_API_KEY not set")
    return key


@router.post("")
def scrape(body: ScrapeRequest):
    competitor = body.competitor.strip()
    if not competitor:
        raise HTTPException(status_code=400, detail="competitor is required")

    leads, raw_results, err = scrape_twitter(_api_key(), competitor, max_items=10)
    print(raw_results)

    return {"leads": leads, "raw_count": len(raw_results), "error": err}


@router.get("/test")
def scrape_test():
    leads, raw_results, err = scrape_twitter(_api_key(), "Stripe", max_items=10)

    if not raw_results:
        return {"error": err or "no results"}

    first = raw_results[0]
    print(first)
    return {
        "first_raw_item": first,
        "parsed_leads_sample": leads[:3],
        "raw_count": len(raw_results),
        "lead_count": len(leads),
        "error": err,
    }
