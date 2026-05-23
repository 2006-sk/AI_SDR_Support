# AI SDR — API Endpoints

**Base URL (local):** `http://localhost:8000`  
**Base URL (ngrok):** `https://submammary-correlatively-irma.ngrok-free.dev`

> Ngrok is running: `ngrok http 8000`  
> Interactive docs: `{BASE}/docs`  
> OpenAPI JSON: `{BASE}/openapi.json`  
> Free ngrok may show a browser warning page on first visit; API clients should send header `ngrok-skip-browser-warning: true`.

**Required env (backend `.env`):** `APIFY_API_KEY`, `VAPI_PUBLIC_KEY`, `VAPI_ASSISTANT_ID` — plus Ollama at `http://localhost:11434` for `/analyze`, `/post-call`, and optional `/agent-scrape` supplement.

---

## Endpoints

### `POST /call`

Returns Vapi assistant config for the frontend to start a voice call (no server-side dial).

**Request body (JSON):**
```json
{
  "lead_name": "Alex Chen",
  "company": "Acme Corp",
  "complaint": "Stripe webhooks keep failing on retry",
  "sdr_name": "Sarah Chen"
}
```
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `lead_name` | string | yes | Prospect name |
| `company` | string | yes | Company name |
| `complaint` | string | yes | Public complaint text for the script |
| `sdr_name` | string | no | Default `"Sarah Chen"` |

**Response (JSON):**
```json
{
  "assistant_id": "791be032-20cc-418c-aa77-fd3e3c7e1bce",
  "assistant_overrides": {
    "firstMessage": "...",
    "variableValues": { "lead_name": "...", "company": "...", "complaint": "...", "sdr_name": "...", "system_prompt": "..." }
  },
  "fallback": false
}
```

---

### `POST /analyze`

Ranks scraped leads by urgency using Ollama; falls back to rule-based ranking if LLM fails.

**Request body (JSON):**
```json
{
  "competitor": "Stripe",
  "leads": [
    {
      "id": "uuid",
      "platform": "twitter",
      "username": "@user",
      "complaint": "Stripe checkout timed out",
      "url": "https://x.com/..."
    }
  ]
}
```

**Response (JSON):**
```json
{
  "ranked_leads": [ /* same lead objects, reordered */ ],
  "emotional_angle": "one sentence hook",
  "ranking_rationale": "brief explanation",
  "fallback": false
}
```

---

### `POST /post-call`

Drafts follow-up email and mock CRM actions from call transcript via Ollama.

**Request body (JSON):**
```json
{
  "lead_name": "Alex Chen",
  "company": "Acme Corp",
  "email": "alex@acme.com",
  "complaint": "Stripe webhooks failing",
  "transcript": "SDR: Hi...\nProspect: ...",
  "sdr_name": "Sarah Chen",
  "ae_name": "Mike Rodriguez"
}
```
| Field | Type | Required |
|-------|------|----------|
| `lead_name`, `company`, `email`, `complaint` | string | yes |
| `transcript` | string | no (default `""`) |
| `sdr_name`, `ae_name` | string | no |

**Response (JSON):**
```json
{
  "gmail": "sent",
  "salesforce": "created",
  "slack": "posted",
  "email": { "to": "alex@acme.com", "subject": "...", "body": "..." },
  "call_summary": "...",
  "next_step": "...",
  "ae_name": "Mike Rodriguez",
  "fallback": false
}
```

---

### `POST /agent-scrape`

Streams multi-source Apify scrape (Reddit, Twitter, G2) as Server-Sent Events (~1–3 min).

**Request body (JSON):**
```json
{ "competitor": "Stripe" }
```

**Response:** `text/event-stream` — lines like `data: {"type":"reasoning"|"tool"|"done", ...}`

**Final event (`type: "done"`):**
```json
{
  "type": "done",
  "leads": [
    { "id": "uuid", "platform": "twitter", "username": "@user", "complaint": "...", "url": "..." }
  ],
  "fallback": false,
  "sources": [
    { "platform": "twitter", "actor_id": "...", "raw_count": 50, "lead_count": 15, "error": null }
  ]
}
```

**Example:**
```bash
curl -N -X POST "https://submammary-correlatively-irma.ngrok-free.dev/agent-scrape" \
  -H "Content-Type: application/json" \
  -H "ngrok-skip-browser-warning: true" \
  -d '{"competitor":"Stripe"}'
```

---

### `POST /enrich`

Scrapes Twitter complaints via Apify (**kaitoeasyapi**) then calls Apollo through Scalekit (`apollo_list_sequences`, optional `apollo_search_contacts`).

**Request body (JSON):**
```json
{
  "competitor": "Stripe",
  "identifier": "user_123",
  "connection_name": "apollo",
  "max_tweets": 10,
  "run_apollo_search": true
}
```

**Response (JSON):**
```json
{
  "competitor": "Stripe",
  "twitter": {
    "actor": "kaitoeasyapi/twitter-x-data-tweet-scraper-pay-per-result-cheapest",
    "search_terms": ["Stripe problems", "Stripe broken", "Stripe outage"],
    "raw_count": 20,
    "lead_count": 10,
    "leads": [{ "id", "platform", "username", "display_name", "bio", "complaint", "url", "profile_image" }],
    "error": null
  },
  "apollo": {
    "authorized": true,
    "list_sequences": { "data": {} },
    "search_contacts": { "data": {} }
  }
}
```

If Apollo is not authorized, `apollo.authorization_link` contains the OAuth URL (same as Scalekit quickstart).

**Authorize Apollo first:**
```bash
curl "http://localhost:8000/enrich/auth?identifier=user_123&connection_name=apollo"
```

---

### `GET /enrich/auth`

Returns Scalekit magic link to connect Apollo for a user identifier.

**Query params:** `identifier` (default `user_123`), `connection_name` (default `apollo`)

**Response:** `{ "link": "https://...", "expires_at": "..." }`

---

### `POST /scrape`

Runs Apify **kaitoeasyapi** Twitter scraper for complaint tweets about a competitor (~30–90s).

**Request body (JSON):**
```json
{ "competitor": "Stripe" }
```

**Response (JSON):**
```json
{
  "raw_count": 10,
  "leads": [
    {
      "id": "",
      "platform": "twitter",
      "username": "",
      "display_name": "",
      "bio": "",
      "complaint": "",
      "url": "",
      "profile_image": ""
    }
  ]
}
```

---

### `GET /scrape/test`

Runs Twitter scrape for **Stripe**; returns first raw Apify item plus parsed lead samples.

**Request body:** none

**Response (JSON):** raw Apify tweet object, e.g. `{ "id", "text", "author": { ... }, "url", ... }` or `{ "noResults": true }`

**Example:**
```bash
curl "https://submammary-correlatively-irma.ngrok-free.dev/scrape/test" \
  -H "ngrok-skip-browser-warning: true"
```

---

## Quick reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/call` | Build Vapi `assistant_id` + overrides for browser voice call |
| `POST` | `/analyze` | Rank leads + emotional angle (Ollama) |
| `POST` | `/post-call` | Post-call email + summary (Ollama) |
| `POST` | `/agent-scrape` | SSE stream: Apify Reddit/Twitter/G2 → leads |
| `POST` | `/enrich` | Twitter Apify scrape + Apollo via Scalekit |
| `GET` | `/enrich/auth` | Scalekit OAuth link for Apollo |
| `POST` | `/scrape` | Apify Twitter-only scrape → parsed leads |
| `GET` | `/scrape/test` | Twitter scrape debug (raw + parsed sample) |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/openapi.json` | OpenAPI schema |

---

## Ngrok commands

```bash
# Terminal 1 — backend (from project root)
cd backend && source ../bob/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — tunnel
ngrok http 8000
```

Public URL (current session): **https://submammary-correlatively-irma.ngrok-free.dev**  
Inspect tunnel: http://127.0.0.1:4040
