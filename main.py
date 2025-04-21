import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from scrape_claim_details import scrape_claim_details
from playwright.__main__ import main as playwright_main
import subprocess

# Optional: Install Chromium browser on cold start
def ensure_chromium_installed():
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except Exception as e:
        print("Chromium install failed:", e)

ensure_chromium_installed()

# FastAPI app
app = FastAPI()

class ClaimRequest(BaseModel):
    url: str

@app.post("/scrape")
def scrape(claim: ClaimRequest):
    try:
        return scrape_claim_details(claim.url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))