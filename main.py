"""
backend/main.py — FastAPI server for the Music Theory Voice Agent.

Responsibilities:
  - Mint short-lived AssemblyAI Voice Agent tokens for browser clients
  - Keep the API key server-side only (set via environment variable on Render)

Deploy on Render:
  - Runtime: Python 3.11
  - Build command: pip install -r requirements.txt
  - Start command: uvicorn main:app --host 0.0.0.0 --port $PORT
  - Environment variable: ASSEMBLYAI_API_KEY = your_key_here
"""

import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow requests from GitHub Pages and localhost for local dev.
# Replace YOUR_GITHUB_USERNAME with your actual GitHub username.
ALLOWED_ORIGINS = [
    "https://YOUR_GITHUB_USERNAME.github.io",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5500",   # VS Code Live Server
    "http://127.0.0.1:5500",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)

TOKEN_URL = "https://agents.assemblyai.com/v1/token"


@app.get("/token")
async def get_token():
    """Mint a single-use Voice Agent token for the browser client."""
    api_key = os.environ.get("ASSEMBLYAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="API key not configured")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            TOKEN_URL,
            params={
                "expires_in_seconds": 300,          # token valid for 5 min
                "max_session_duration_seconds": 3600, # session cap: 1 hour
            },
            headers={"Authorization": f"Bearer {api_key}"},
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to mint token")

    return resp.json()  # { "token": "..." }


@app.get("/health")
async def health():
    return {"status": "ok"}
