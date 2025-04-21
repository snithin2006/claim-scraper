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

def extract_info(text: str) -> dict:
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    data = {
        "LawsuitAmount": None,
        "MaxClaimAmount": None,
        "ProofRequirement": None,
        "TierDescriptions": []
    }

    for line in lines:
        if any(k in line.lower() for k in FUND_KEYWORDS):
            match = re.search(r"\$\d[\d,\.]*", line)
            if match:
                data["LawsuitAmount"] = match.group()
                break

    for line in lines:
        if any(k in line.lower() for k in PROOF_KEYWORDS):
            data["ProofRequirement"] = line
            break

    for line in lines:
        if "per person" in line.lower() or "maximum" in line.lower():
            match = re.search(r"\$\d[\d,\.]*", line)
            if match:
                data["MaxClaimAmount"] = match.group()
                break

    for line in lines:
        if any(k in line.lower() for k in TIER_KEYWORDS):
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