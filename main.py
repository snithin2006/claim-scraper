import subprocess
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from scrape_claim_details import scrape_claim_details

# Optional: install Chromium at startup
def ensure_chromium_installed():
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except Exception as e:
        print("Chromium install failed:", e)

ensure_chromium_installed()

# FastAPI setup
app = FastAPI()

class ClaimRequest(BaseModel):
    url: str

@app.post("/scrape")
def scrape(claim: ClaimRequest):
    try:
        return scrape_claim_details(claim.url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
