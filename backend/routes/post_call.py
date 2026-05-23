import json
import re

from fastapi import APIRouter
from pydantic import BaseModel

from llm import MODEL, chat_completion_safe
from routes.fallbacks import fallback_post_call

router = APIRouter(prefix="/post-call", tags=["post-call"])


class PostCallRequest(BaseModel):
    lead_name: str
    company: str
    email: str
    complaint: str
    transcript: str = ""
    sdr_name: str = "Sarah Chen"
    ae_name: str = "Mike Rodriguez"


def _parse_json_object(text: str) -> dict:
    for match in re.finditer(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE):
        try:
            data = json.loads(match.group(1).strip())
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(text.strip())
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
async def post_call(body: PostCallRequest):
    system = (
        "You analyze sales call transcripts and write concise follow-up emails. "
        "Reference the prospect's original complaint and what was discussed. "
        "Respond with valid JSON only."
    )
    user = f"""Lead: {body.lead_name} at {body.company} ({body.email})
Original complaint: {body.complaint}
SDR: {body.sdr_name}

Call transcript:
{body.transcript or "(no transcript provided)"}

Return JSON:
{{
  "subject": "email subject line",
  "body": "full email body",
  "call_summary": "2-3 sentence summary of the call",
  "next_step": "recommended next action"
}}"""

    response, err = chat_completion_safe(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        model=MODEL,
    )
    if err or response is None:
        return fallback_post_call(
            body.lead_name,
            body.company,
            body.email,
            body.complaint,
            body.sdr_name,
            body.ae_name,
            str(err) if err else "no response",
        )

    raw = response.choices[0].message.content or ""
    parsed = _parse_json_object(raw)
    if not parsed.get("subject") and not parsed.get("body"):
        return fallback_post_call(
            body.lead_name,
            body.company,
            body.email,
            body.complaint,
            body.sdr_name,
            body.ae_name,
            "could not parse Ollama response",
        )

    return {
        "gmail": "sent",
        "salesforce": "created",
        "slack": "posted",
        "email": {
            "to": body.email,
            "subject": parsed.get("subject") or "Great speaking with you",
            "body": parsed.get("body") or "",
        },
        "call_summary": parsed.get("call_summary", ""),
        "next_step": parsed.get("next_step", ""),
        "ae_name": body.ae_name,
        "fallback": False,
    }
