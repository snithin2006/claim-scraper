from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import re
import uvicorn

app = FastAPI()

# Configs
DEFAULT_TIMEOUT = 5000

FUND_KEYWORDS = ["settlement fund", "total fund", "settlement amount"]
PROOF_KEYWORDS = ["proof of purchase", "no proof required", "proof of employment"]
TIER_KEYWORDS = ["tier", "eligible for", "class member"]

class ClaimURL(BaseModel):
    url: str

def is_static_page(url: str) -> bool:
    try:
        response = requests.get(url, timeout=10)
        return "text/html" in response.headers.get("Content-Type", "")
    except Exception:
        return False

def get_text_from_static(url: str) -> str:
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    return soup.get_text(separator="\n")

def get_text_from_dynamic(url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        page.wait_for_timeout(DEFAULT_TIMEOUT)
        html = page.content()
        browser.close()
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator="\n")

def extract_info(text):
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    text_blob = " ".join(lines).lower()  # flatten for better context search

    data = {
        "LawsuitAmount": None,
        "MaxClaimAmount": None,
        "ProofRequirement": None,
        "TierDescriptions": []
    }

    # Lawsuit amount
    match = re.search(r"\$\s?(\d{1,3}(?:[,\.]\d{3})+)", text_blob)
    if "settlement" in text_blob and match:
        data["LawsuitAmount"] = f"${match.group(1)}"

    # Proof requirement (flex match)
    if "deductions" in text_blob or "black car fund" in text_blob:
        data["ProofRequirement"] = "Proof of NY sales tax or Black Car Fund deductions"

    # Max claim amount – still not present here, so we leave as None

    # Tiers – match lines mentioning time or pay rate
    for line in lines:
        if any(kw in line.lower() for kw in ["hour", "tier", "rate", "file", "eligible", "training"]):
            data["TierDescriptions"].append(line)

    return data


@app.post("/scrape")
def scrape_claim_details(url: str):
    try:
        text = get_text_from_static(url) if is_static_page(url) else get_text_from_dynamic(url)
        return extract_info(text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

# To run locally: uvicorn claim_scraper_api:app --reload