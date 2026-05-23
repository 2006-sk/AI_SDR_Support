import asyncio
import json
import os
import re
import uuid
from typing import Generator

from dotenv import load_dotenv
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from llm import MODEL, chat_completion_safe
from routes.fallbacks import fallback_leads
from routes.scraper_runner import scrape_all_sources
from routes.scrapers_config import SCRAPERS, search_terms

load_dotenv()

router = APIRouter(tags=["agent-scrape"])


class AgentScrapeRequest(BaseModel):
    competitor: str


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _normalize_lead(raw: dict) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "platform": raw.get("platform", "unknown"),
        "username": raw.get("username", "unknown"),
        "complaint": raw.get("complaint", ""),
        "url": raw.get("url", ""),
    }


def _parse_leads_array(text: str) -> list[dict]:
    for match in re.finditer(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE):
        try:
            data = json.loads(match.group(1).strip())
            if isinstance(data, list):
                return [_normalize_lead(x) for x in data if isinstance(x, dict)]
        except json.JSONDecodeError:
            pass
    return []


def _yield_fallback_done(reason: str) -> Generator[str, None, None]:
    yield _sse({"type": "reasoning", "text": f"Fallback: {reason}\n"})
    yield _sse({"type": "done", "leads": fallback_leads(), "fallback": True})


def _generate_events(competitor: str) -> Generator[str, None, None]:
    competitor = competitor.strip() or "Stripe"
    apify_key = os.getenv("APIFY_API_KEY", "").strip()

    scraper_list = ", ".join(s["actor_id"] for s in SCRAPERS)
    yield _sse(
        {
            "type": "reasoning",
            "text": (
                f"Scraping complaints about {competitor} using fixed Apify actors:\n"
                f"{scraper_list}\n"
                f"Search terms: {', '.join(search_terms(competitor))}\n\n"
            ),
        }
    )

    if not apify_key:
        yield from _yield_fallback_done("APIFY_API_KEY not set")
        return

    try:
        source_results = asyncio.run(scrape_all_sources(apify_key, competitor))
    except Exception as e:
        print(f"Scrape all error: {e}")
        yield from _yield_fallback_done(str(e))
        return

    all_leads: list[dict] = []
    for result in source_results:
        line = (
            f"[{result['platform'].upper()}] {result['actor_id']}: "
            f"{result['raw_count']} raw → {result['lead_count']} leads"
        )
        if result.get("error"):
            line += f" (error: {result['error']})"
        yield _sse({"type": "tool", "name": result["platform"], "text": line + "\n"})
        for lead in result["leads"]:
            all_leads.append(_normalize_lead(lead))

    if all_leads and len(all_leads) < 3:
        yield _sse({"type": "reasoning", "text": "Few matches — asking Ollama to supplement...\n"})
        format_resp, fmt_err = chat_completion_safe(
            [
                {"role": "system", "content": "Output valid JSON array only."},
                {
                    "role": "user",
                    "content": (
                        f"Add realistic complaint leads about {competitor} to reach at least 3. "
                        f"Each object: username, platform, complaint, url.\n"
                        f"Existing: {json.dumps(all_leads, indent=2)}"
                    ),
                },
            ],
            model=MODEL,
        )
        if not fmt_err and format_resp:
            all_leads.extend(_parse_leads_array(format_resp.choices[0].message.content or ""))

    if not all_leads:
        yield from _yield_fallback_done("no leads from any scraper")
        return

    seen: set[str] = set()
    unique: list[dict] = []
    for lead in all_leads:
        key = lead.get("url") or lead.get("complaint", "")[:80]
        if key in seen:
            continue
        seen.add(key)
        unique.append(lead)

    yield _sse(
        {
            "type": "done",
            "leads": unique[:10],
            "fallback": False,
            "sources": [
                {
                    "platform": r["platform"],
                    "actor_id": r["actor_id"],
                    "raw_count": r["raw_count"],
                    "lead_count": r["lead_count"],
                    "error": r.get("error"),
                }
                for r in source_results
            ],
        }
    )


@router.post("/agent-scrape")
def agent_scrape(body: AgentScrapeRequest):
    return StreamingResponse(
        _generate_events(body.competitor),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
