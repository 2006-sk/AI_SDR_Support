"""Run all configured Apify scrapers and print results. Usage: python test_scrapers.py [competitor]"""

import asyncio
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from routes.scraper_runner import scrape_all_sources
from routes.scrapers_config import SCRAPERS, search_terms


def main() -> None:
    competitor = sys.argv[1] if len(sys.argv) > 1 else "Stripe"
    api_key = os.getenv("APIFY_API_KEY", "").strip()
    if not api_key:
        print("ERROR: APIFY_API_KEY not set in backend/.env")
        sys.exit(1)

    print("=" * 72)
    print(f"RIVAL INTEL — Apify scraper test for: {competitor}")
    print("=" * 72)
    print("\nConfigured actors (Llama no longer picks these — they are fixed in code):\n")
    for s in SCRAPERS:
        print(f"  • {s['platform'].upper():8} {s['actor_id']}")
    print(f"\nSearch terms: {search_terms(competitor)}\n")
    print("Running scrapers (this may take 1–3 minutes)...\n")

    results = asyncio.run(scrape_all_sources(api_key, competitor))

    total_leads = 0
    for r in results:
        print("-" * 72)
        print(f"## {r['platform'].upper()} — {r['actor_id']}")
        print(f"   Raw items from Apify: {r['raw_count']}")
        print(f"   Leads after filter:  {r['lead_count']}")
        if r.get("error"):
            print(f"   Error: {r['error']}")

        if r["sample_raw"]:
            print("\n   Sample raw item (first):")
            print("   " + json.dumps(r["sample_raw"][0], default=str)[:500].replace("\n", "\n   "))

        if r["leads"]:
            print("\n   Mapped leads:")
            for i, lead in enumerate(r["leads"][:5], 1):
                uname = lead.get("username", "unknown")
                if not uname.startswith("@") and not uname.startswith("u/"):
                    uname = f"@{uname}"
                print(f"\n   [{i}] {uname} ({lead.get('platform')})")
                print(f"       {lead.get('complaint', '')[:200]}")
                print(f"       {lead.get('url', '')}")
            total_leads += len(r["leads"])
        else:
            print("\n   (no leads matched competitor filter)")

    print("\n" + "=" * 72)
    print(f"TOTAL LEADS: {total_leads}")
    print("=" * 72)

    print("\nNotes:")
    print("  • apify/reddit-scraper and apify/g2-reviews-scraper return 404 on the Apify API.")
    print("  • G2 store actors often return demo Slack reviews regardless of product URL.")
    print("  • Twitter (kaitoeasyapi) is the most reliable source for real complaint text.")

    if total_leads == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
