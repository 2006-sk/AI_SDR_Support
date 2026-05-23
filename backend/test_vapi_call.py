"""End-to-end Vapi call flow test. Run: python test_vapi_call.py"""

import json
import os
import sys

import httpx
from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv()

from main import app  # noqa: E402

CALL_BODY = {
    "lead_name": "Alex Chen",
    "company": "Acme Corp",
    "complaint": "Stripe webhooks have been timing out for 3 days",
    "sdr_name": "Sarah Chen",
}
EXPECTED_ASSISTANT = "791be032-20cc-418c-aa77-fd3e3c7e1bce"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def main() -> None:
    public_key = os.getenv("VAPI_PUBLIC_KEY", "").strip()
    private_key = os.getenv("VAPI_API_KEY", "").strip()
    if not public_key:
        fail("VAPI_PUBLIC_KEY not set in .env")
    ok(f"VAPI_PUBLIC_KEY set ({public_key[:8]}...)")

    # 1) Backend /call
    client = TestClient(app)
    r = client.post("/call", json=CALL_BODY)
    if r.status_code != 200:
        fail(f"POST /call returned {r.status_code}: {r.text}")
    data = r.json()
    if data.get("fallback"):
        fail(f"POST /call fallback: {data.get('error')}")
    if data.get("assistant_id") != EXPECTED_ASSISTANT:
        fail(f"assistant_id mismatch: {data.get('assistant_id')}")
    ok(f"POST /call → assistant_id {data['assistant_id']}")

    overrides = data.get("assistant_overrides") or {}
    if "model" in overrides:
        fail("assistant_overrides must not include partial model (causes start-method-error)")
    if not overrides.get("firstMessage"):
        fail("missing firstMessage in overrides")
    if not overrides.get("variableValues"):
        fail("missing variableValues in overrides")
    ok("assistant_overrides valid (firstMessage + variableValues only)")

    # 2) Vapi GET assistant (private key)
    if private_key:
        ar = httpx.get(
            f"https://api.vapi.ai/assistant/{EXPECTED_ASSISTANT}",
            headers={"Authorization": f"Bearer {private_key}"},
            timeout=30,
        )
        if ar.status_code != 200:
            fail(f"GET assistant {ar.status_code}: {ar.text[:200]}")
        name = ar.json().get("name", "?")
        ok(f"Vapi assistant exists: {name}")

    # 3) Vapi POST call/web (what SDK does on vapi.start)
    vr = httpx.post(
        "https://api.vapi.ai/call/web",
        headers={
            "Authorization": f"Bearer {public_key}",
            "Content-Type": "application/json",
        },
        json={
            "assistantId": data["assistant_id"],
            "assistantOverrides": overrides,
        },
        timeout=60,
    )
    if vr.status_code != 201:
        fail(f"POST call/web {vr.status_code}: {vr.text[:400]}")
    web_call = vr.json()
    if not web_call.get("webCallUrl"):
        fail("call/web missing webCallUrl")
    ok(f"POST call/web → webCallUrl {web_call['webCallUrl'][:50]}...")
    ok(f"call id {web_call.get('id')}")

    # 4) Live backend URL
    try:
        lr = httpx.post("http://localhost:8000/call", json=CALL_BODY, timeout=10)
        if lr.status_code == 200 and not lr.json().get("fallback"):
            ok("live backend http://localhost:8000/call")
        else:
            print(f"WARN: live backend returned {lr.status_code} {lr.text[:100]}")
    except Exception as e:
        print(f"WARN: live backend not reachable ({e})")

    print("\nAll Vapi call checks passed. Open http://localhost:3000 and click Call Alex Chen.")


if __name__ == "__main__":
    main()
