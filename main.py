from fastapi import FastAPI
from pydantic import BaseModel
from scrape_claim_details import scrape_claim_details

app = FastAPI()

class ClaimRequest(BaseModel):
    url: str

@app.post("/scrape")  # This MUST be a POST endpoint
def scrape(claim: ClaimRequest):
    return scrape_claim_details(claim.url)