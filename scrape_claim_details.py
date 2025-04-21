from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import re
import uvicorn
from transformers import pipeline

app = FastAPI()

# Configs
DEFAULT_TIMEOUT = 5000
CHUNK_SIZE = 800  # words per summarization chunk

# Load open-source LLM summarizer
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

# Prompt template for LLM extraction
EXTRACTION_PROMPT = """
Given the text of a class action or legal settlement page, extract the following structured fields:

1. Total settlement amount (in USD)
2. Maximum payout per person (if mentioned)
3. Whether proof of purchase or employment is required
4. Any tiered payout logic or rules
5. Deadline to file a claim

Return your response in this JSON format:
{
  "LawsuitAmount": "...",
  "MaxClaimAmount": "...",
  "ProofRequirement": "...",
  "TierDescriptions": ["...", "..."],
  "ClaimDeadline": "..."
}
"""

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

def chunk_text(text, chunk_size=CHUNK_SIZE):
    words = text.split()
    return [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]

def extract_info_with_llm(text):
    data = {
        "LawsuitAmount": None,
        "MaxClaimAmount": None,
        "ProofRequirement": None,
        "TierDescriptions": [],
        "ClaimDeadline": None
    }

    try:
        chunks = chunk_text(text)
        summarized_chunks = [summarizer(EXTRACTION_PROMPT + "\nText:\n" + chunk, max_length=400, min_length=100, do_sample=False)[0]['summary_text'] for chunk in chunks]
        summary = " ".join(summarized_chunks)
    except Exception as e:
        summary = text[:1000]  # fallback

    # Extract from the combined summary using regex and pattern hints
    match = re.search(r"\$\s?([\d,.]+).*settlement", summary.lower())
    if match:
        data["LawsuitAmount"] = f"${match.group(1)}"

    match = re.search(r"max(imum)?[^\d$]*\$\s?([\d,.]+)", summary.lower())
    if match:
        data["MaxClaimAmount"] = f"${match.group(2)}"

    proof_match = re.search(r"proof[^\.]+\.", summary, re.IGNORECASE)
    if proof_match:
        data["ProofRequirement"] = proof_match.group().strip()

    deadline_match = re.search(r"deadline[^\.]+\d{4}[^\.]*\.", summary, re.IGNORECASE)
    if deadline_match:
        data["ClaimDeadline"] = deadline_match.group().strip()

    for line in summary.split(". "):
        if any(kw in line.lower() for kw in ["hour", "rate", "file", "eligible", "training", "tier", "sick", "support"]):
            data["TierDescriptions"].append(line.strip())

    return data

@app.post("/scrape")
def scrape_claim_details(url: str):
    try:
        text = get_text_from_static(url) if is_static_page(url) else get_text_from_dynamic(url)
        return extract_info_with_llm(text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

# To run locally: uvicorn claim_scraper_api:app --reload