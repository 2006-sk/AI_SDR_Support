from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.agent_scrape import router as agent_scrape_router
from routes.analyze import router as analyze_router
from routes.call import router as call_router
from routes.post_call import router as post_call_router

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(call_router)
app.include_router(analyze_router)
app.include_router(agent_scrape_router)
app.include_router(post_call_router)
