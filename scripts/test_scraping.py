#!/usr/bin/env python3
"""Diagnostic: test Apify scraping with minimal filters to see what comes back."""

import os
import sys
from dotenv import load_dotenv
sys.path.insert(0, '.')
load_dotenv()

from scrapers.apify_scraper import BrandMentionScraper

# Test 1: Instagram hashtag directly
print("=" * 60)
print("Test 1: Direct Instagram hashtag scrape (no filters)")
print("=" * 60)

import requests

token = os.getenv("APIFY_TOKEN")
# Use correct actor ID (verified working)
actor_id = "reGe1ST3OBgYZSsZJ"  # apify/instagram-hashtag-scraper

url = f"https://api.apify.com/v2/acts/{actor_id}/run-sync-get-dataset-items"
params = {"token": token}
input_data = {"hashtags": ["augustinusbader"], "resultsLimit": 20}

try:
    resp = requests.post(url, params=params, json=input_data, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    print(f"Got {len(data)} raw posts for #augustinusbader")
    if data:
        print(f"Sample keys: {list(data[0].keys())}")
        print(f"Sample caption: {(data[0].get('caption') or data[0].get('text') or '')[:200]}")
except Exception as e:
    print(f"Error: {e}")

# Test 2: Reddit search directly
print()
print("=" * 60)
print("Test 2: Direct Reddit search (no filters)")
print("=" * 60)

actor_id_reddit = "5LOwKe4dIDEJ64I58"  # reddit-search-scraper
input_data_reddit = {
    "search": "augustinus bader",
    "subreddit": "SkincareAddiction",
    "sort": "new",
    "time": "month",
    "limit": 20,
}

try:
    resp = requests.post(
        f"https://api.apify.com/v2/acts/{actor_id_reddit}/run-sync-get-dataset-items",
        params={"token": token},
        json=input_data_reddit,
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    print(f"Got {len(data)} Reddit posts mentioning 'augustinus bader' in r/SkincareAddiction (last month)")
    if data:
        print(f"Sample keys: {list(data[0].keys())}")
        title = data[0].get('title', '')
        text = data[0].get('selftext', '') or data[0].get('text', '')
        print(f"Sample title: {title[:120]}")
        print(f"Sample text: {text[:200]}")
except Exception as e:
    print(f"Error: {e}")

# Test 3: Google News
print()
print("=" * 60)
print("Test 3: Direct Google News search")
print("=" * 60)

actor_id_news = "6vAxbA15R5J4uLKZ0"  # google-news-scraper
input_data_news = {"query": "Augustinus Bader", "language": "en", "maxResults": 10}

try:
    resp = requests.post(
        f"https://api.apify.com/v2/acts/{actor_id_news}/run-sync-get-dataset-items",
        params={"token": token},
        json=input_data_news,
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    print(f"Got {len(data)} news articles for 'Augustinus Bader'")
    if data:
        print(f"Sample: {str(data[0])[:300]}")
except Exception as e:
    print(f"Error: {e}")
