import json
import re

from fastapi import APIRouter
from pydantic import BaseModel

from llm import MODEL, chat_completion_safe
from routes.fallbacks import fallback_analyze

router = APIRouter(prefix="/analyze", tags=["analyze"])


class Lead(BaseModel):
    id: str = ""
    platform: str = ""
    username: str = ""
    complaint: str = ""
    url: str = ""


class AnalyzeRequest(BaseModel):
    competitor: str = ""
    leads: list[Lead]


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


@router.post("")
async def analyze(body: AnalyzeRequest):
    leads_payload = [lead.model_dump() for lead in body.leads]
    competitor = body.competitor.strip() or "the competitor"

    system = (
        "You are a sales intelligence analyst. Rank leads by urgency and buying intent. "
        "Identify the single best emotional angle to use in outreach. "
        "Respond with valid JSON only."
    )
    user = f"""Competitor context: {competitor}

Leads:
{json.dumps(leads_payload, indent=2)}

Return JSON:
{{
  "ranked_lead_ids": ["id1", "id2", ...],
  "emotional_angle": "one sentence describing the emotional hook",
  "ranking_rationale": "brief explanation"
}}"""

    response, err = chat_completion_safe(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        model=MODEL,
    )
    if err or response is None:
        return fallback_analyze(leads_payload, competitor, str(err) if err else "no response")

    raw = response.choices[0].message.content or ""
    parsed = _parse_json_object(raw)
    if not parsed.get("ranked_lead_ids") and not parsed.get("emotional_angle"):
        return fallback_analyze(
            leads_payload,
            competitor,
            "could not parse Ollama response",
        )

    id_order = parsed.get("ranked_lead_ids") or []
    lead_map = {lead.get("id") or str(i): lead for i, lead in enumerate(leads_payload)}
    ranked = []
    for lead_id in id_order:
        if lead_id in lead_map:
            ranked.append(lead_map[lead_id])
    for lead in leads_payload:
        if lead not in ranked:
            ranked.append(lead)

    return {
        "ranked_leads": ranked,
        "emotional_angle": parsed.get("emotional_angle", ""),
        "ranking_rationale": parsed.get("ranking_rationale", ""),
        "fallback": False,
    }
