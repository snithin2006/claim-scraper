from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware
from scrape_claim_details import scrape_claim_details
from pydantic import BaseModel

app = FastAPI()

class ClaimRequest(BaseModel):
    url: str

@app.post("/scrape")
def scrape(claim: ClaimRequest):
    return scrape_claim_details(claim.url)