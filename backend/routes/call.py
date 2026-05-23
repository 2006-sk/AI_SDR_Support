import os

from dotenv import load_dotenv
from fastapi import APIRouter
from pydantic import BaseModel

load_dotenv()

router = APIRouter(prefix="/call", tags=["call"])

DEFAULT_ASSISTANT_ID = "791be032-20cc-418c-aa77-fd3e3c7e1bce"


class CallRequest(BaseModel):
    lead_name: str
    company: str
    complaint: str
    sdr_name: str = "Sarah Chen"


def _system_prompt(req: CallRequest) -> str:
    return f"""You are {req.sdr_name}, an SDR on a live call.

You are speaking with {req.lead_name} from {req.company}.

They recently posted this complaint publicly:
"{req.complaint}"

Open by referencing their complaint naturally. Be empathetic, not salesy.
Your goal is to book a 15-minute demo. Keep the call under 2 minutes."""


def _first_message(req: CallRequest) -> str:
    snippet = req.complaint[:100].rstrip()
    if len(req.complaint) > 100:
        snippet += "..."
    return (
        f"{req.lead_name.split()[0] if req.lead_name else 'there'}, "
        f"I saw your post about {snippet} — I'm {req.sdr_name}, "
        f"and we've helped teams at companies like {req.company} get past exactly this."
    )


def _build_overrides(req: CallRequest) -> dict:
    # Only firstMessage + variableValues — partial model override without
    # provider causes Vapi 400 and SDK "start-method-error".
    return {
        "firstMessage": _first_message(req),
        "variableValues": {
            "lead_name": req.lead_name,
            "company": req.company,
            "complaint": req.complaint,
            "sdr_name": req.sdr_name,
            "system_prompt": _system_prompt(req),
        },
    }


@router.post("")
async def create_call(body: CallRequest):
    public_key = os.getenv("VAPI_PUBLIC_KEY", "").strip()
    assistant_id = os.getenv("VAPI_ASSISTANT_ID", DEFAULT_ASSISTANT_ID).strip()

    if not public_key:
        return {
            "assistant_id": None,
            "assistant_overrides": None,
            "fallback": True,
            "error": "VAPI_PUBLIC_KEY not set",
        }

    return {
        "assistant_id": assistant_id,
        "assistant_overrides": _build_overrides(body),
        "fallback": False,
    }
