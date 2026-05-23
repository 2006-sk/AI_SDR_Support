"""Fixed Apify actors for competitor complaint scraping.

Note: `apify/reddit-scraper` and `apify/g2-reviews-scraper` are not available on the
Apify Store (404). We use the closest working actors below (verified via API runs).
"""

from __future__ import annotations

# Reddit — user asked apify/reddit-scraper; store has trudax/reddit-scraper-lite instead
REDDIT_ACTOR = "trudax/reddit-scraper-lite"

# Twitter/X — kaitoeasyapi (hackathon: cheaper per user spec)
TWITTER_ACTOR = "kaitoeasyapi/twitter-x-data-tweet-scraper-pay-per-result-cheapest"

# G2 — apify/g2-reviews-scraper 404 on store; zhorex returns structured reviews (see test notes)
G2_ACTOR = "zhorex/g2-reviews-scraper"


def search_terms(competitor: str) -> list[str]:
    c = competitor.strip()
    return [f"{c} problems", f"{c} broken", f"{c} outage"]


def g2_reviews_url(competitor: str) -> str:
    slug = competitor.strip().lower().replace(" ", "-")
    return f"https://www.g2.com/products/{slug}/reviews"


def reddit_input(competitor: str) -> dict:
    return {
        "searches": search_terms(competitor),
        "searchPosts": True,
        "searchComments": False,
        "searchCommunities": False,
        "searchUsers": False,
        "sort": "new",
        "time": "year",
        "maxItems": 15,
        "maxPostCount": 15,
    }


def twitter_input(competitor: str) -> dict:
    return {
        "searchTerms": search_terms(competitor),
        "maxItems": 15,
    }


def g2_input(competitor: str) -> dict:
    slug = competitor.strip().lower().replace(" ", "-")
    return {
        "productSlug": slug,
        "startUrls": [{"url": g2_reviews_url(competitor)}],
        "maxReviews": 15,
    }


SCRAPERS = [
    {
        "key": "reddit",
        "platform": "reddit",
        "actor_id": REDDIT_ACTOR,
        "build_input": reddit_input,
    },
    {
        "key": "twitter",
        "platform": "twitter",
        "actor_id": TWITTER_ACTOR,
        "build_input": twitter_input,
    },
    {
        "key": "g2",
        "platform": "g2",
        "actor_id": G2_ACTOR,
        "build_input": g2_input,
    },
]
