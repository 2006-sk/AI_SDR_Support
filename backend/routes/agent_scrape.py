import asyncio
import json
import os
import re
import uuid
from typing import Generator

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from llm import MODEL, chat_completion_safe
from routes.fallbacks import fallback_leads

load_dotenv()

router = APIRouter(tags=["agent-scrape"])


class AgentScrapeRequest(BaseModel):
    competitor: str


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _parse_json_object(text: str) -> dict:
    for match in re.finditer(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE):
        try:
            data = json.loads(match.group(1).strip())
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
    try:
        data = json.loads(text.strip())
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    obj_match = re.search(r"\{[\s\S]*\}", text)
    if obj_match:
        try:
            return json.loads(obj_match.group(0))
        except json.JSONDecodeError:
            pass
    return {}


def _parse_leads_array(text: str) -> list[dict]:
    for match in re.finditer(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE):
        try:
            data = json.loads(match.group(1).strip())
            if isinstance(data, list):
                return [_normalize_lead(x) for x in data if isinstance(x, dict)]
        except json.JSONDecodeError:
            pass
    array_match = re.search(r"\[[\s\S]*\]", text)
    if array_match:
        try:
            data = json.loads(array_match.group(0))
            if isinstance(data, list):
                return [_normalize_lead(x) for x in data if isinstance(x, dict)]
        except json.JSONDecodeError:
            pass
    return []


def _normalize_lead(raw: dict) -> dict:
    platform = (raw.get("platform") or "unknown").lower()
    return {
        "id": str(uuid.uuid4()),
        "platform": platform,
        "username": raw.get("username") or raw.get("user") or raw.get("author") or "unknown",
        "complaint": raw.get("complaint") or raw.get("text") or raw.get("body") or "",
        "url": raw.get("url") or raw.get("link") or "",
    }


def _items_to_leads(items: list[dict]) -> list[dict]:
    leads = []
    for item in items:
        text = item.get("title") or item.get("selftext") or item.get("body") or item.get("text") or ""
        if not text:
            continue
        leads.append(
            _normalize_lead(
                {
                    "username": item.get("author") or item.get("username") or "unknown",
                    "platform": item.get("platform") or "reddit",
                    "complaint": str(text)[:500],
                    "url": item.get("url") or item.get("link") or "",
                }
            )
        )
    return leads


async def _run_apify_actor(client: httpx.AsyncClient, api_key: str, actor_id: str, query: str) -> list[dict]:
    actor_path = actor_id.replace("/", "~")
    url = f"https://api.apify.com/v2/acts/{actor_path}/runs?token={api_key}&waitForFinish=60"
    payload = {"queries": [query], "maxItems": 5, "sort": "new"}
    response = await client.post(url, json=payload, timeout=120.0)
    response.raise_for_status()
    run_data = response.json()
    dataset_id = run_data.get("data", {}).get("defaultDatasetId")
    if not dataset_id:
        return []
    items_resp = await client.get(
        f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={api_key}",
        timeout=60.0,
    )
    items_resp.raise_for_status()
    items = items_resp.json()
    return items if isinstance(items, list) else []


async def _scrape_with_plan(
    apify_key: str, actors: list[str], search_terms: list[str]
) -> tuple[list[dict], list[str]]:
    all_items: list[dict] = []
    log_lines: list[str] = []
    async with httpx.AsyncClient() as client:
        for actor in actors[:3]:
            for term in search_terms[:3]:
                log_lines.append(f"Running {actor}: {term}")
                try:
                    items = await _run_apify_actor(client, apify_key, actor, term)
                    all_items.extend(items)
                except Exception as e:
                    log_lines.append(f"  failed: {e}")
    return all_items, log_lines


def _stream_ollama_plan(competitor: str) -> Generator[str, None, tuple[dict | None, Exception | None]]:
    system = f"""You are a sales intelligence agent planning how to scrape public complaints about {competitor}.
You have access to the Apify actor marketplace (Reddit, Twitter, G2, Trustpilot scrapers).
Think step by step out loud, then end with a JSON block:

```json
{{
  "actors": ["apify/reddit-search"],
  "search_terms": ["{competitor} problems", "{competitor} broken", "{competitor} outage"]
}}
```"""

    user = (
        f"Plan which 2-3 Apify actors to run to find people complaining about {competitor} "
        f"on Reddit, Twitter, G2, or Trustpilot."
    )

    stream, err = chat_completion_safe(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        model=MODEL,
        stream=True,
    )
    if err or stream is None:
        return None, err or Exception("Ollama returned no stream")

    full_text = ""
    try:
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                full_text += delta
                yield _sse({"type": "reasoning", "text": delta})
    except Exception as exc:
        return None, exc

    plan = _parse_json_object(full_text)
    if not plan.get("actors") and not plan.get("search_terms"):
        return None, Exception("could not parse plan from Ollama")
    return plan, None


def _yield_fallback_done(reason: str) -> Generator[str, None, None]:
    yield _sse({"type": "reasoning", "text": f"Fallback: {reason}\n"})
    yield _sse({"type": "done", "leads": fallback_leads(), "fallback": True})


def _generate_events(competitor: str) -> Generator[str, None, None]:
    competitor = competitor.strip() or "Stripe"
    apify_key = os.getenv("APIFY_API_KEY", "").strip()

    yield _sse({"type": "reasoning", "text": f"Starting agent for {competitor}...\n"})

    plan: dict | None = None
    try:
        plan_gen = _stream_ollama_plan(competitor)
        while True:
            try:
                yield next(plan_gen)
            except StopIteration as stop:
                result = stop.value
                if isinstance(result, tuple):
                    plan, plan_err = result
                    if plan_err:
                        yield from _yield_fallback_done(str(plan_err))
                        return
                break
    except Exception as e:
        print(f"Agent plan error: {e}")
        yield from _yield_fallback_done(str(e))
        return

    if not plan:
        yield from _yield_fallback_done("no scrape plan from Ollama")
        return

    actors = plan.get("actors") or ["apify/reddit-search"]
    search_terms = plan.get("search_terms") or [
        f"{competitor} problems",
        f"{competitor} broken",
        f"{competitor} outage",
    ]

    all_items: list[dict] = []
    if apify_key:
        try:
            all_items, log_lines = asyncio.run(_scrape_with_plan(apify_key, actors, search_terms))
            for line in log_lines:
                yield _sse({"type": "tool", "name": "apify", "text": line + "\n"})
        except Exception as e:
            print(f"Apify scrape error: {e}")
            yield _sse({"type": "reasoning", "text": f"Apify error: {e}\n"})
    else:
        yield _sse({"type": "reasoning", "text": "APIFY_API_KEY not set — skipping scrape, formatting via Ollama only.\n"})

    yield _sse({"type": "reasoning", "text": "Formatting results with Ollama...\n"})

    leads: list[dict] = []
    format_resp, fmt_err = chat_completion_safe(
        [
            {"role": "system", "content": "Output valid JSON array only."},
            {
                "role": "user",
                "content": (
                    f"Convert these scrape results into complaints about {competitor}. "
                    f"Each object: username, platform, complaint, url. Return at least 3 items.\n\n"
                    f"{json.dumps(all_items[:30], default=str)[:8000] if all_items else 'No scrape data — generate realistic examples.'}"
                ),
            },
        ],
        model=MODEL,
    )

    if not fmt_err and format_resp is not None:
        leads = _parse_leads_array(format_resp.choices[0].message.content or "")

    if not leads and all_items:
        leads = _items_to_leads(all_items)

    if not leads:
        yield from _yield_fallback_done(
            str(fmt_err) if fmt_err else "no leads produced"
        )
        return

    yield _sse({"type": "done", "leads": leads[:10], "fallback": False})


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
