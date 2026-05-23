"""Twitter complaint scrape via Apify (kaitoeasyapi — works on free Apify tier)."""

from __future__ import annotations

import re

import httpx

TWITTER_ACTOR = "kaitoeasyapi/twitter-x-data-tweet-scraper-pay-per-result-cheapest"


def search_terms(competitor: str) -> list[str]:
    c = competitor.strip()
    return [f"{c} problems", f"{c} broken", f"{c} outage"]


def _author_value(author: object, *keys: str) -> str:
    if not isinstance(author, dict):
        return ""
    for key in keys:
        val = author.get(key)
        if val is not None and val != "":
            return str(val)
    return ""


def _is_no_results(item: dict) -> bool:
    return item.get("noResults") is True


def _mentions_competitor(text: str, competitor: str) -> bool:
    if not text:
        return False
    pattern = re.compile(rf"\b{re.escape(competitor.strip())}\b", re.IGNORECASE)
    return bool(pattern.search(text))


def parse_tweet(item: dict, competitor: str) -> dict | None:
    if _is_no_results(item):
        return None
    text = (item.get("text") or item.get("full_text") or item.get("content") or "").strip()
    if not text or not _mentions_competitor(text, competitor):
        return None
    author = item.get("author") or {}
    handle = (_author_value(author, "userName", "username", "screen_name") or "unknown").lstrip(
        "@"
    )
    return {
        "id": item.get("id") or item.get("tweet_id") or "",
        "platform": "twitter",
        "username": f"@{handle}",
        "display_name": _author_value(author, "name", "displayName"),
        "bio": _author_value(author, "description", "bio"),
        "complaint": text[:500],
        "url": item.get("url") or item.get("twitterUrl") or item.get("tweet_url") or "",
        "profile_image": _author_value(author, "profilePicture", "profile_image_url"),
    }


def scrape_twitter(
    api_key: str,
    competitor: str,
    *,
    max_items: int = 10,
    wait_seconds: int = 90,
) -> tuple[list[dict], list[dict], str | None]:
    """
    Run Apify Twitter actor and return (parsed_leads, raw_items, error).
    """
    actor_path = TWITTER_ACTOR.replace("/", "~")
    payload = {
        "searchTerms": search_terms(competitor),
        "maxItems": max(max_items * 2, 15),
    }
    run_url = (
        f"https://api.apify.com/v2/acts/{actor_path}/runs"
        f"?token={api_key}&waitForFinish={wait_seconds}"
    )

    try:
        with httpx.Client(timeout=wait_seconds + 60) as client:
            run_resp = client.post(run_url, json=payload)
            run_resp.raise_for_status()
            dataset_id = run_resp.json().get("data", {}).get("defaultDatasetId")
            if not dataset_id:
                return [], [], "Apify run succeeded but no dataset id"

            items_resp = client.get(
                f"https://api.apify.com/v2/datasets/{dataset_id}/items"
                f"?token={api_key}&limit={max_items * 3}",
                timeout=60.0,
            )
            items_resp.raise_for_status()
            raw = items_resp.json()
    except Exception as exc:
        return [], [], str(exc)

    if not isinstance(raw, list):
        return [], [], "invalid Apify dataset response"

    leads: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        parsed = parse_tweet(item, competitor)
        if parsed:
            leads.append(parsed)
        if len(leads) >= max_items:
            break

    return leads[:max_items], raw, None
