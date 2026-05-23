# Rival Intel (AI SDR)

Sales intelligence hackathon project: find unhappy competitor customers, enrich leads, run a live AI SDR voice call in the browser, and automate post-call follow-up.

**Repository:** [github.com/2006-sk/AI_SDR_Support](https://github.com/2006-sk/AI_SDR_Support)

---

## What it does

| Stage | Description |
|-------|-------------|
| **Agent scrape** | Ollama plans Apify actor runs, scrapes public complaints (Reddit, G2, Twitter, etc.), returns leads via SSE |
| **Analyze** | Ollama ranks leads and suggests an emotional outreach angle |
| **Call** | Vapi web voice call using your dashboard assistant + per-lead overrides |
| **Post-call** | Ollama drafts follow-up email content from call context |

Hardcoded demo data is used only when Ollama or upstream APIs fail.

---

## Architecture

```
┌─────────────────┐     REST / SSE      ┌──────────────────┐
│  React frontend │ ◄──────────────────► │  FastAPI backend │
│  (port 3000)    │                      │  (port 8000)     │
└────────┬────────┘                      └────────┬─────────┘
         │                                        │
         │ @vapi-ai/web                           ├── Ollama (llama3.2)
         ▼                                        ├── Apify (agent-scrape)
┌─────────────────┐                               └── Vapi (assistant config)
│  Vapi + Daily   │
│  voice call     │
└─────────────────┘
```

---

## Tech stack

**Backend**

- FastAPI, Uvicorn, httpx, python-dotenv
- [OpenAI Python SDK](https://github.com/openai/openai-python) → **Ollama** at `http://localhost:11434/v1` (model: `llama3.2`)
- Apify REST API (agent-scrape)
- Vapi assistant ID + overrides (call route)

**Frontend**

- React 18 (JavaScript, no TypeScript)
- [@vapi-ai/web](https://www.npmjs.com/package/@vapi-ai/web) for browser voice calls
- Inline styles only (no Tailwind / component libraries)

---

## Project structure

```
AI_SDR/
├── backend/
│   ├── main.py                 # FastAPI app + CORS
│   ├── llm.py                    # Ollama client (OpenAI-compatible)
│   ├── requirements.txt
│   ├── .env.example
│   ├── test_endpoints.py         # Smoke tests for all routes
│   ├── test_vapi_call.py         # Vapi call flow validation
│   └── routes/
│       ├── call.py               # POST /call → assistant_id + overrides
│       ├── agent_scrape.py       # POST /agent-scrape (SSE)
│       ├── analyze.py            # POST /analyze
│       ├── post_call.py          # POST /post-call
│       ├── fallbacks.py          # Demo data on errors
│       └── leads_data.py
│
└── frontend/
    ├── public/index.html
    ├── package.json
    ├── .env.example
    └── src/
        ├── App.jsx               # Vapi test UI (Call Alex Chen)
        ├── index.js
        └── components/
            └── VapiCall.jsx      # Live call UI + transcript
```

---

## Prerequisites

1. **Python 3.11+**
2. **Node.js 18+**
3. **Ollama** — `ollama pull llama3.2` and `ollama serve` on port `11434`
4. **Vapi account** — [dashboard.vapi.ai](https://dashboard.vapi.ai)
   - Private key → `VAPI_API_KEY`
   - Public key → `VAPI_PUBLIC_KEY` and `REACT_APP_VAPI_PUBLIC_KEY`
   - Assistant (default): `791be032-20cc-418c-aa77-fd3e3c7e1bce` (Meeting Mind)
5. **Apify** (optional, for live agent-scrape) — `APIFY_API_KEY`

---

## Setup

### 1. Clone and configure

```bash
git clone https://github.com/2006-sk/AI_SDR_Support.git
cd AI_SDR_Support
```

### 2. Backend

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r backend/requirements.txt

cp backend/.env.example backend/.env
# Edit backend/.env with your keys
```

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env
# Set REACT_APP_VAPI_PUBLIC_KEY to the same value as VAPI_PUBLIC_KEY
```

---

## Running locally

**Terminal 1 — Ollama**

```bash
ollama serve
```

**Terminal 2 — Backend**

```bash
source venv/bin/activate
cd backend
uvicorn main:app --reload --port 8000
```

**Terminal 3 — Frontend**

```bash
cd frontend
npm start
```

Open [http://localhost:3000](http://localhost:3000), click **Call Alex Chen**, and allow microphone access.

---

## API reference

### `POST /call`

Starts a Vapi web call configuration for the browser SDK.

**Body**

```json
{
  "lead_name": "Alex Chen",
  "company": "Acme Corp",
  "complaint": "Stripe webhooks have been timing out",
  "sdr_name": "Sarah Chen"
}
```

**Response**

```json
{
  "assistant_id": "791be032-20cc-418c-aa77-fd3e3c7e1bce",
  "assistant_overrides": {
    "firstMessage": "...",
    "variableValues": {
      "lead_name": "Alex Chen",
      "company": "Acme Corp",
      "complaint": "...",
      "sdr_name": "Sarah Chen",
      "system_prompt": "..."
    }
  },
  "fallback": false
}
```

The frontend calls `vapi.start(assistant_id, assistant_overrides)`.

> **Note:** Do not pass a partial `model` override without `provider` — Vapi returns 400 and the SDK shows `start-method-error`.

---

### `POST /agent-scrape`

Server-Sent Events stream. Ollama plans scrapers; Apify runs when `APIFY_API_KEY` is set.

**Body:** `{ "competitor": "Stripe" }`

**SSE events:** `reasoning`, `tool`, `done` (includes `leads` array)

---

### `POST /analyze`

**Body:** `{ "competitor": "Stripe", "leads": [...] }`

**Response:** `{ "ranked_leads", "emotional_angle", "ranking_rationale", "fallback" }`

---

### `POST /post-call`

**Body:** `{ "lead_name", "company", "email", "complaint", "transcript", "sdr_name", "ae_name" }`

**Response:** Gmail/Salesforce/Slack status flags + generated `email` object

---

## Testing

```bash
# All backend routes
cd backend && python test_endpoints.py

# Vapi call + call/web API
cd backend && python test_vapi_call.py
```

---

## Environment variables

| Variable | Where | Purpose |
|----------|--------|---------|
| `VAPI_API_KEY` | backend | Private key (admin API, e.g. list assistants) |
| `VAPI_PUBLIC_KEY` | backend | Public key for `POST /call/web` validation |
| `VAPI_ASSISTANT_ID` | backend | Dashboard assistant UUID |
| `APIFY_API_KEY` | backend | Apify scraper runs |
| `REACT_APP_VAPI_PUBLIC_KEY` | frontend | Browser Vapi SDK |
| `REACT_APP_API_URL` | frontend | Backend URL (default `http://localhost:8000`) |

Ollama uses a fixed local config in `backend/llm.py` (`base_url=http://localhost:11434/v1`, `api_key=ollama`, model `llama3.2`). No cloud LLM API keys required.

---

## Troubleshooting

### `start-method-error` (Vapi)

Usually caused by invalid `assistantOverrides`. Use only `firstMessage` and `variableValues` unless you include a full `model` with `provider`.

### Call connects then disconnects immediately

- Ensure React StrictMode is not calling `vapi.stop()` on mount cleanup (fixed in `VapiCall.jsx`).
- Use `vapi.start(assistantId, overrides)` — not server `reconnect()` for new calls.

### `401` on Vapi

- `POST /call/web` requires the **public** key, not the private key.
- Keys are swapped easily — verify in the [Vapi dashboard](https://dashboard.vapi.ai).

### Ollama / agent-scrape falls back to demo leads

- Run `ollama serve` and `ollama pull llama3.2`.
- Check `APIFY_API_KEY` for live scraping.

---

## License

MIT — see [LICENSE](LICENSE).
