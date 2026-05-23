"""Run: python test_endpoints.py (from backend/)"""

import json
import sys

from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv()

from main import app  # noqa: E402
from routes.leads_data import HARDCODED_LEADS  # noqa: E402

client = TestClient(app)

SAMPLE_LEAD = HARDCODED_LEADS[0]
CALL_BODY = {
    "lead_name": "Alex Chen",
    "company": "Acme Corp",
    "complaint": SAMPLE_LEAD["complaint"],
    "sdr_name": "Sarah Chen",
}
POST_CALL_BODY = {
    **CALL_BODY,
    "email": "demo@acmecorp.com",
    "transcript": "SDR: Thanks for taking my call. Lead: Yeah the webhook issue is killing us.",
}


def test_analyze():
    r = client.post(
        "/analyze",
        json={"competitor": "Stripe", "leads": HARDCODED_LEADS},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "ranked_leads" in data
    assert "emotional_angle" in data
    print(f"  analyze OK fallback={data.get('fallback')} leads={len(data['ranked_leads'])}")
    return data


def test_post_call():
    r = client.post("/post-call", json=POST_CALL_BODY)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("email", {}).get("body")
    print(f"  post-call OK fallback={data.get('fallback')}")
    return data


def test_agent_scrape():
    leads = None
    fallback = None
    with client.stream("POST", "/agent-scrape", json={"competitor": "Stripe"}) as r:
        assert r.status_code == 200, r.text
        for line in r.iter_lines():
            if not line.startswith("data:"):
                continue
            event = json.loads(line[5:].strip())
            if event.get("type") == "done":
                leads = event.get("leads")
                fallback = event.get("fallback")
    assert leads and len(leads) >= 1
    print(f"  agent-scrape OK fallback={fallback} leads={len(leads)}")
    return leads


def test_call():
    r = client.post("/call", json=CALL_BODY)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "token" in data
    print(f"  call OK fallback={data.get('fallback')} has_token={bool(data.get('token'))}")
    return data


def main():
    print("Testing endpoints...")
    failed = []
    for name, fn in [
        ("analyze", test_analyze),
        ("post-call", test_post_call),
        ("agent-scrape", test_agent_scrape),
        ("call", test_call),
    ]:
        try:
            fn()
        except Exception as e:
            print(f"  {name} FAILED: {e}")
            failed.append(name)
    if failed:
        print(f"\nFailed: {', '.join(failed)}")
        sys.exit(1)
    print("\nAll endpoint checks passed.")


if __name__ == "__main__":
    main()
