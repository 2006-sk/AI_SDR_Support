"""Run all API endpoint smoke tests. Usage: python test_endpoints.py [--live URL]"""

import argparse
import json
import sys

import httpx
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


def _ok(name: str, status: int, detail: str = "") -> None:
    mark = "OK" if status == 200 else "FAIL"
    extra = f" {detail}" if detail else ""
    print(f"  [{mark}] {name} HTTP {status}{extra}")


def test_health(c: TestClient | httpx.Client, base: str = "") -> None:
    path = f"{base}/health" if base else "/health"
    r = c.get(path) if base else c.get(path)
    assert r.status_code == 200, r.text
    _ok("GET /health", r.status_code)


def test_call(c: TestClient | httpx.Client, base: str = "") -> None:
    path = f"{base}/call" if base else "/call"
    r = c.post(path, json=CALL_BODY)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("assistant_id"), data
    _ok("POST /call", r.status_code, f"assistant_id={data.get('assistant_id', '')[:8]}...")


def test_analyze(c: TestClient | httpx.Client, base: str = "") -> None:
    path = f"{base}/analyze" if base else "/analyze"
    r = c.post(path, json={"competitor": "Stripe", "leads": HARDCODED_LEADS})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "ranked_leads" in data
    _ok("POST /analyze", r.status_code, f"leads={len(data['ranked_leads'])}")


def test_post_call(c: TestClient | httpx.Client, base: str = "") -> None:
    path = f"{base}/post-call" if base else "/post-call"
    r = c.post(path, json=POST_CALL_BODY)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("email", {}).get("body")
    _ok("POST /post-call", r.status_code)


def test_scrape_test(c: TestClient | httpx.Client, base: str = "") -> None:
    path = f"{base}/scrape/test" if base else "/scrape/test"
    r = c.get(path, timeout=120.0)
    assert r.status_code == 200, r.text
    data = r.json()
    _ok("GET /scrape/test", r.status_code, f"raw={data.get('raw_count', '?')}")


def test_enrich_auth(c: TestClient | httpx.Client, base: str = "") -> None:
    path = f"{base}/enrich/auth" if base else "/enrich/auth"
    r = c.get(path)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("link") or data.get("already_connected") or data.get("fallback")
    _ok("GET /enrich/auth", r.status_code, f"fallback={data.get('fallback', False)}")


def test_enrich_status(c: TestClient | httpx.Client, base: str = "") -> None:
    path = f"{base}/enrich/apollo/status" if base else "/enrich/apollo/status"
    r = c.get(path)
    assert r.status_code == 200, r.text
    data = r.json()
    _ok("GET /enrich/apollo/status", r.status_code, f"status={data.get('status')}")


def test_enrich(c: TestClient | httpx.Client, base: str = "") -> None:
    path = f"{base}/enrich" if base else "/enrich"
    r = c.post(
        path,
        json={"competitor": "Stripe", "max_tweets": 2, "enrich_emails": True},
        timeout=120.0,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["twitter"]["lead_count"] >= 1
    assert data["twitter"]["leads"][0].get("email")
    _ok("POST /enrich", r.status_code, f"leads={data['twitter']['lead_count']}")


def test_scrape(c: TestClient | httpx.Client, base: str = "") -> None:
    path = f"{base}/scrape" if base else "/scrape"
    r = c.post(path, json={"competitor": "Stripe"}, timeout=120.0)
    assert r.status_code == 200, r.text
    data = r.json()
    _ok("POST /scrape", r.status_code, f"raw={data.get('raw_count')}")


def test_agent_scrape(c: TestClient | httpx.Client, base: str = "") -> None:
    path = f"{base}/agent-scrape" if base else "/agent-scrape"
    leads = None
    if base:
        with httpx.stream(
            "POST",
            path,
            json={"competitor": "Stripe"},
            timeout=180.0,
            headers={"ngrok-skip-browser-warning": "true"},
        ) as r:
            assert r.status_code == 200, r.text
            for line in r.iter_lines():
                if not line.startswith("data:"):
                    continue
                event = json.loads(line[5:].strip())
                if event.get("type") == "done":
                    leads = event.get("leads")
    else:
        with c.stream("POST", "/agent-scrape", json={"competitor": "Stripe"}) as r:
            assert r.status_code == 200, r.text
            for line in r.iter_lines():
                if not line.startswith("data:"):
                    continue
                event = json.loads(line[5:].strip())
                if event.get("type") == "done":
                    leads = event.get("leads")
    assert leads and len(leads) >= 1
    _ok("POST /agent-scrape", 200, f"leads={len(leads)}")


def test_cors_preflight(live_base: str) -> None:
    r = httpx.options(
        f"{live_base}/call",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
        timeout=10.0,
    )
    assert r.status_code in (200, 204), r.text
    assert "access-control-allow-origin" in {k.lower() for k in r.headers}
    _ok("OPTIONS /call (CORS)", r.status_code)


TESTS = [
    ("health", test_health),
    ("call", test_call),
    ("analyze", test_analyze),
    ("post-call", test_post_call),
    ("scrape-test", test_scrape_test),
    ("enrich-auth", test_enrich_auth),
    ("enrich-status", test_enrich_status),
    ("enrich", test_enrich),
    ("scrape", test_scrape),
    ("agent-scrape", test_agent_scrape),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", metavar="URL", help="Also hit live server e.g. http://localhost:8000")
    args = parser.parse_args()

    print("=== In-process tests (TestClient) ===")
    failed: list[str] = []
    for name, fn in TESTS:
        try:
            fn(client)
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            failed.append(name)

    if args.live:
        print(f"\n=== Live tests ({args.live}) ===")
        live = args.live.rstrip("/")
        hc = httpx.Client(
            base_url=live,
            headers={"ngrok-skip-browser-warning": "true"},
            timeout=120.0,
        )
        try:
            test_cors_preflight(live)
            for name, fn in TESTS:
                try:
                    fn(hc, base="")
                except Exception as e:
                    print(f"  [FAIL] {name}: {e}")
                    failed.append(f"live:{name}")
        finally:
            hc.close()

    if failed:
        print(f"\nFailed: {', '.join(failed)}")
        sys.exit(1)
    print("\nAll endpoint checks passed.")


if __name__ == "__main__":
    main()
