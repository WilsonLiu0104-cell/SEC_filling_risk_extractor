"""SEC EDGAR fetcher.

Pulls Risk Factors text directly from EDGAR given a CIK and accession number.
This is the production path; for development and evaluation we use the
sample text files in data/samples/.

EDGAR requires a User-Agent header identifying the user. Set the
EDGAR_USER_AGENT environment variable to something like:
    "Wilson Liu wilson@example.com"

This module is deliberately small. PDF and HTML extraction can have many
edge cases on real 10-Ks; we punt on most of them and fall back to "give
us a text file" for anything we can't parse. The goal of the project is
the analysis layer, not extraction perfection.
"""

from __future__ import annotations

import os
import re

import requests
from bs4 import BeautifulSoup


EDGAR_BASE = "https://www.sec.gov/Archives/edgar/data"
EDGAR_INDEX = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
DEFAULT_UA = "SEC Filing Risk Extractor research@example.com"


def _user_agent() -> str:
    return os.environ.get("EDGAR_USER_AGENT", DEFAULT_UA)


def fetch_filing_index(cik: int) -> dict:
    """Get the list of recent filings for a CIK from EDGAR."""
    url = EDGAR_INDEX.format(cik=cik)
    r = requests.get(url, headers={"User-Agent": _user_agent()}, timeout=30)
    r.raise_for_status()
    return r.json()


def fetch_filing_html(cik: int, accession: str, primary_doc: str) -> str:
    """Fetch the primary document HTML for a given filing."""
    accession_clean = accession.replace("-", "")
    url = f"{EDGAR_BASE}/{cik}/{accession_clean}/{primary_doc}"
    r = requests.get(url, headers={"User-Agent": _user_agent()}, timeout=60)
    r.raise_for_status()
    return r.text


def extract_risk_factors_from_html(html: str) -> str:
    """Extract just the Item 1A. Risk Factors section from a 10-K HTML.

    Heuristic: locate the heading "Item 1A" or "Risk Factors" and capture
    text up to "Item 1B" / "Item 2" / "Unresolved Staff Comments".
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n")
    # Normalize whitespace.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    start_match = re.search(
        r"item\s*1a\.?\s*risk\s*factors", text, re.IGNORECASE
    )
    if not start_match:
        raise ValueError("Could not locate 'Item 1A. Risk Factors' in document.")
    start = start_match.start()

    end_match = re.search(
        r"item\s*1b\.?|item\s*2\.|unresolved\s+staff\s+comments",
        text[start + 100:], re.IGNORECASE,
    )
    end = (start + 100 + end_match.start()) if end_match else len(text)

    return text[start:end].strip()
