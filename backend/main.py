import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.agent_scrape import router as agent_scrape_router
from routes.analyze import router as analyze_router
from routes.call import router as call_router
from routes.enrich import router as enrich_router
from routes.post_call import router as post_call_router
from routes.scrape import router as scrape_router

load_dotenv()

app = FastAPI()

# CORS — frontend (localhost:3000) + ngrok + any origin in dev
_cors_raw = os.getenv("CORS_ORIGINS", "*").strip()
if _cors_raw == "*":
    _allow_origins = ["*"]
    _allow_credentials = False
else:
    _allow_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()]
    _allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(call_router)
app.include_router(analyze_router)
app.include_router(agent_scrape_router)
app.include_router(post_call_router)
app.include_router(scrape_router)
app.include_router(enrich_router)


@app.get("/health")
def health():
    return {"status": "ok"}
