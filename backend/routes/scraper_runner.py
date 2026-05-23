"""Run configured Apify actors and map raw items to lead dicts."""

from __future__ import annotations

import re
from typing import Any

import httpx

from routes.scrapers_config import SCRAPERS


async def run_apify_actor(
    client: httpx.AsyncClient,
    api_key: str,
    actor_id: str,
    payload: dict,
    *,
    wait_seconds: int = 90,
) -> tuple[list[dict], str | None]:
    actor_path = actor_id.replace("/", "~")
    url = f"https://api.apify.com/v2/acts/{actor_path}/runs?token={api_key}&waitForFinish={wait_seconds}"
    try:
        response = await client.post(url, json=payload, timeout=wait_seconds + 60)
        response.raise_for_status()
        run_data = response.json()
        dataset_id = run_data.get("data", {}).get("defaultDatasetId")
        if not dataset_id:
            return [], "no dataset id"
        items_resp = await client.get(
            f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={api_key}&limit=50",
            timeout=60.0,
        )
        items_resp.raise_for_status()
        items = items_resp.json()
        if not isinstance(items, list):
            return [], "invalid dataset response"
        return items, None
    except Exception as exc:
        return [], str(exc)


def _mentions_competitor(text: str, competitor: str) -> bool:
    if not text:
        return False
    # Word boundary avoids false positives (e.g. "stripes" matching Stripe)
    pattern = re.compile(rf"\b{re.escape(competitor.strip())}\b", re.IGNORECASE)
    return bool(pattern.search(text))


_COMPLAINT_HINTS = re.compile(
    r"\b(problem|broken|outage|issue|bug|down|failed|error|support|refund|charge|payment)\b",
    re.IGNORECASE,
)


def map_reddit_item(item: dict, competitor: str) -> dict | None:
    title = (item.get("title") or "").strip()
    body = (item.get("body") or "").strip()
    blob = f"{title} {body}"
    complaint = title
    if body and body not in title:
        complaint = f"{title}. {body}" if title else body
    if not complaint:
        return None
    if not _mentions_competitor(blob, competitor):
        return None
    if not _COMPLAINT_HINTS.search(blob):
        return None
    username = item.get("username") or item.get("author") or "unknown"
    return {
        "platform": "reddit",
        "username": username if username.startswith("u/") else f"u/{username}",
        "complaint": complaint[:500],
        "url": item.get("url") or item.get("link") or "",
    }


def map_twitter_item(item: dict, competitor: str) -> dict | None:
    text = (item.get("text") or "").strip()
    if not text or not _mentions_competitor(text, competitor):
        return None
    author = item.get("author") or {}
    handle = (author.get("userName") or item.get("username") or "unknown").lstrip("@")
    handle = f"@{handle}"
    return {
        "platform": "twitter",
        "username": handle,
        "complaint": text[:500],
        "url": item.get("url") or item.get("twitterUrl") or "",
    }


def map_g2_item(item: dict, competitor: str) -> dict | None:
    review = (item.get("reviewText") or item.get("review") or "").strip()
    title = (item.get("title") or "").strip()
    product = (item.get("productName") or "").strip()
    complaint = review or title
    if not complaint:
        return None
    # G2 actors often mislabel productName; require competitor in review or product
    blob = f"{product} {title} {review}"
    if not _mentions_competitor(blob, competitor):
        return None
    username = item.get("reviewerName") or item.get("author") or "G2 Verified Buyer"
    rating = item.get("rating") or item.get("starRating")
    if rating and "Verified" not in username:
        username = f"G2 Review ({rating}★)"
    return {
        "platform": "g2",
        "username": username,
        "complaint": complaint[:500],
        "url": item.get("reviewUrl") or item.get("url") or "",
    }


def map_items(platform: str, items: list[dict], competitor: str) -> list[dict]:
    mapper = {
        "reddit": map_reddit_item,
        "twitter": map_twitter_item,
        "g2": map_g2_item,
    }.get(platform)
    if not mapper:
        return []
    leads = []
    for item in items:
        if not isinstance(item, dict):
            continue
        mapped = mapper(item, competitor)
        if mapped:
            leads.append(mapped)
    return leads


async def scrape_all_sources(
    api_key: str,
    competitor: str,
) -> list[dict[str, Any]]:
    """Run all scrapers; return per-source result summaries."""
    results: list[dict[str, Any]] = []
    async with httpx.AsyncClient() as client:
        for scraper in SCRAPERS:
            payload = scraper["build_input"](competitor)
            raw, err = await run_apify_actor(
                client, api_key, scraper["actor_id"], payload
            )
            leads = map_items(scraper["platform"], raw, competitor)[:15]
            results.append(
                {
                    "source": scraper["key"],
                    "platform": scraper["platform"],
                    "actor_id": scraper["actor_id"],
                    "raw_count": len(raw),
                    "lead_count": len(leads),
                    "error": err,
                    "sample_raw": raw[:2],
                    "leads": leads,
                }
            )
    return results
