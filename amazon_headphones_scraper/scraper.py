#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Amazon Headphones Scraper (demo)
- Modes:
  - sample: parse local sample.html and print results
  - live: attempt to fetch Amazon US product page for "Beats Studio Buds".
          If blocked or parse fails, automatically fall back to sample mode.
Output: prints to console; CSV export will be added in later commits.

No third-party dependencies; only Python standard library.
"""
import argparse
import csv
import os
import re
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_FILE = os.path.join(SCRIPT_DIR, "sample.html")
DEFAULT_CSV = os.path.join(SCRIPT_DIR, "output.csv")

# Candidate Amazon US product URLs for Beats Studio Buds
CANDIDATE_URLS = [
    "https://www.amazon.com/dp/B096SV8N4C",
    "https://www.amazon.com/Beats-Studio-Buds-Noise-Cancelling/dp/B096SV8N4C",
]

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/118.0 Safari/537.36"
)
ACCEPT_LANGUAGE = "en-US,en;q=0.9"


def parse_sample_html(html: str):
    """Parse the local sample.html content.
    Expected structure:
    <div class="item">
      <span class="title">Beats Studio Buds</span>
      <span class="price">$99.99</span>
      <span class="rating">4.5 out of 5</span>
      <span class="reviews">27,532 ratings</span>
    </div>
    Returns a dict.
    """
    title_match = re.search(r'<span class="title">([^<]+)</span>', html)
    price_match = re.search(r'<span class="price">\$?([0-9,.]+)</span>', html)
    rating_match = re.search(r'<span class="rating">([0-9.]+)\s*out of\s*5</span>', html)
    reviews_match = re.search(r'<span class="reviews">([0-9,]+)\s*ratings</span>', html)

    def to_int(s):
        try:
            return int(s.replace(",", ""))
        except Exception:
            return None

    def to_float(s):
        try:
            return float(s)
        except Exception:
            return None

    return {
        "title": title_match.group(1).strip() if title_match else None,
        "price": price_match.group(1).strip() if price_match else None,
        "rating": to_float(rating_match.group(1)) if rating_match else None,
        "reviews_count": to_int(reviews_match.group(1)) if reviews_match else None,
    }


def try_fetch(url: str, timeout: int = 15) -> str:
    """Fetch URL with basic headers; returns body or empty string on failure."""
    req = Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept-Language": ACCEPT_LANGUAGE,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection": "keep-alive",
    })
    try:
        with urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return ""
            body = resp.read().decode("utf-8", errors="ignore")
            return body
    except (HTTPError, URLError):
        return ""
    except Exception:
        return ""


def parse_product_page(html: str):
    """Best-effort parse of Amazon product page for title/price/rating/reviews.
    Returns dict or None if cannot parse minimally.
    """
    # Title
    title = None
    m = re.search(r'id="productTitle"[^>]*>\s*(.*?)\s*<', html, flags=re.S)
    if m:
        title = re.sub(r'\s+', ' ', m.group(1)).strip()

    # Price: various fallbacks
    price = None
    m = re.search(r'id="priceblock_ourprice"[^>]*>\s*\$([0-9.,]+)', html)
    if not m:
        m = re.search(r'id="priceblock_dealprice"[^>]*>\s*\$([0-9.,]+)', html)
    if not m:
        # a-price structure: whole + fraction
        m_whole = re.search(r'class="a-price-whole">\s*([0-9,]+)\s*<', html)
        m_frac = re.search(r'class="a-price-fraction">\s*([0-9]{2})\s*<', html)
        if m_whole:
            whole = m_whole.group(1).replace(",", "")
            frac = m_frac.group(1) if m_frac else "00"
            price = f"{whole}.{frac}"
    else:
        price = m.group(1)

    # Rating
    rating = None
    m = re.search(r'aria-label="([0-9.]+)\s*out of\s*5\s*stars"', html)
    if m:
        rating = m.group(1)

    # Reviews count
    reviews_count = None
    m = re.search(r'id="acrCustomerReviewText"[^>]*>\s*([0-9,]+)\s*(?:ratings|reviews)\s*<', html)
    if m:
        reviews_count = m.group(1)

    def to_int(s):
        try:
            return int(s.replace(",", ""))
        except Exception:
            return None

    def to_float(s):
        try:
            return float(s)
        except Exception:
            return None

    result = {
        "title": title,
        "price": price,
        "rating": to_float(rating) if rating else None,
        "reviews_count": to_int(reviews_count) if reviews_count else None,
    }
    if not result["title"]:
        return None
    return result


def run_sample():
    if not os.path.exists(SAMPLE_FILE):
        print("sample.html not found; please ensure the file exists.")
        return None
    with open(SAMPLE_FILE, "r", encoding="utf-8") as f:
        html = f.read()
    data = parse_sample_html(html)
    print("[sample] Parsed:")
    print(data)
    return data


def run_live():
    for url in CANDIDATE_URLS:
        print(f"[live] Fetching: {url}")
        html = try_fetch(url)
        if not html:
            print("[live] Fetch failed or blocked; try next candidate...")
            time.sleep(1)
            continue
        data = parse_product_page(html)
        if data:
            print("[live] Parsed:")
            print(data)
            return data
        else:
            print("[live] Parse failed; trying next candidate...")
            time.sleep(1)
    print("[live] All candidates failed; falling back to sample mode.")
    return run_sample()


def main():
    parser = argparse.ArgumentParser(description="Amazon Headphones Scraper (demo)")
    parser.add_argument("--mode", choices=["sample", "live"], default="sample", help="Run mode")
    parser.add_argument("--out", default=DEFAULT_CSV, help="CSV output path (added in later commit)")
    args = parser.parse_args()

    if args.mode == "sample":
        run_sample()
    else:
        run_live()

if __name__ == "__main__":
    main()