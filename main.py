import subprocess
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from scrape_claim_details import scrape_claim_details

# ✅ Install Chromium on startup (works for Railway)
def ensure_chromium_installed():
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except Exception as e:
        print("Chromium install failed:", e)

ensure_chromium_installed()

# ✅ FastAPI app init
app = FastAPI()

# ✅ Define input schema
class ClaimRequest(BaseModel):
    url: str

# ✅ Accept JSON with field { "url": "..." }
@app.post("/scrape")
def scrape(claim: ClaimRequest):
    try:
        return scrape_claim_details(claim.url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
