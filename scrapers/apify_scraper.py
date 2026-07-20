"""
Apify Scraper Module
====================

Pulls brand mentions from Instagram, TikTok, Reddit, Google News, and YouTube
using pre-built Apify actors. Output is normalized into a single CSV schema
that the LLM analyzer can consume.

Usage:
    from scrapers.apify_scraper import BrandMentionScraper
    scraper = BrandMentionScraper()
    mentions = scraper.run_for_brand("augustinus_bader")
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import requests
import yaml
from dotenv import load_dotenv
import os

load_dotenv()


class BrandMentionScraper:
    """Orchestrates Apify scrapers across multiple platforms for a given brand."""

    # Apify actor IDs (verified working on 19 July 2026)
    ACTORS = {
        "instagram_hashtag": "reGe1ST3OBgYZSsZJ",   # apify/instagram-hashtag-scraper
        "tiktok_hashtag":    "f1ZeP0K58iwlqG2pY",   # tiktok-hashtag-scraper
        "reddit_search":     "5LOwKe4dIDEJ64I58",   # reddit-search-scraper
        "google_news":       "6vAxbA15R5J4uLKZ0",   # google-news-scraper
        "youtube_comments":  "p7UMdpQnjKmmpR21D",   # youtube-comments-scraper
        "facebook_pages":    "W45u4o0fA1lhlWnZF",   # facebook-page-posts-scraper
        "google_search":     "nFJndFXA5zjCTuudP",   # google-search-scraper
        "tumblr_search":     "D1p9GOGe2nRlViand",   # tumblr-search-scraper
    }

    APIFY_BASE = "https://api.apify.com/v2"

    def __init__(self, config_path: str = "./scrapers/config.yaml"):
        self.token = os.getenv("APIFY_TOKEN")
        if not self.token:
            raise ValueError("APIFY_TOKEN missing. Add it to your .env file.")
        self.user_id = os.getenv("APIFY_USER_ID", "")
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_for_brand(self, brand_key: str, platforms: Optional[List[str]] = None) -> pd.DataFrame:
        """Scrape mentions for a single brand across selected platforms."""
        brand = self.config["brands"][brand_key]
        platforms = platforms or ["instagram", "tiktok", "reddit", "news"]

        all_mentions: List[Dict] = []

        for platform in platforms:
            print(f"[{brand_key}] Scraping {platform}...")
            try:
                if platform == "instagram":
                    mentions = self._scrape_instagram(brand)
                elif platform == "tiktok":
                    mentions = self._scrape_tiktok(brand)
                elif platform == "reddit":
                    mentions = self._scrape_reddit(brand)
                elif platform == "news":
                    mentions = self._scrape_news(brand)
                elif platform == "youtube":
                    mentions = self._scrape_youtube(brand)
                elif platform == "facebook":
                    mentions = self._scrape_facebook(brand)
                elif platform == "blog":
                    mentions = self._scrape_blogs(brand)
                else:
                    print(f"  Unknown platform: {platform}, skipping.")
                    continue
                all_mentions.extend(mentions)
                print(f"  +{len(mentions)} mentions")
            except Exception as e:
                print(f"  ERROR on {platform}: {e}")

        df = pd.DataFrame(all_mentions)
        if not df.empty:
            df["brand_key"] = brand_key
            df = self._apply_quality_filters(df, brand)
        return df

    def run_for_all_brands(self, platforms: Optional[List[str]] = None) -> pd.DataFrame:
        """Scrape all configured brands, returns one combined DataFrame."""
        frames = []
        for brand_key in self.config["brands"]:
            df = self.run_for_brand(brand_key, platforms)
            if not df.empty:
                frames.append(df)
        if frames:
            return pd.concat(frames, ignore_index=True)
        return pd.DataFrame()

    def save_raw(self, df: pd.DataFrame, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)
        print(f"Saved {len(df)} raw mentions → {path}")

    # ------------------------------------------------------------------
    # Platform-specific scrapers
    # ------------------------------------------------------------------

    def _scrape_instagram(self, brand: Dict) -> List[Dict]:
        hashtags = brand["hashtags"]["instagram"]
        results = []
        for tag in hashtags[:3]:  # Top 3 hashtags
            posts = self._run_actor(
                self.ACTORS["instagram_hashtag"],
                input_data={
                    "hashtags": [tag],
                    "resultsLimit": 30,
                },
            )
            for post in posts:
                caption = post.get("caption", "") or post.get("text", "")
                if caption:
                    results.append({
                        "mention_id": post.get("id", f"ig_{int(time.time()*1000)}_{len(results)}"),
                        "timestamp": post.get("timestamp") or datetime.utcnow().isoformat(),
                        "source": "instagram",
                        "source_url": post.get("url", ""),
                        "language": "en",
                        "raw_text": caption[:5000],
                        "author_handle": post.get("ownerUsername", ""),
                        "engagement_likes": post.get("likesCount", 0),
                        "engagement_comments": post.get("commentsCount", 0),
                        "country_guess": "",
                    })
        return results

    def _scrape_tiktok(self, brand: Dict) -> List[Dict]:
        hashtags = brand["hashtags"]["tiktok"]
        results = []
        for tag in hashtags[:3]:
            videos = self._run_actor(
                self.ACTORS["tiktok_hashtag"],
                input_data={
                    "hashtags": [tag],
                    "resultsPerPage": 25,
                },
            )
            for v in videos:
                text = v.get("text", "") or v.get("desc", "")
                if not text:
                    continue
                results.append({
                    "mention_id": v.get("id", f"tt_{int(time.time()*1000)}_{len(results)}"),
                    "timestamp": v.get("createTime") or datetime.utcnow().isoformat(),
                    "source": "tiktok",
                    "source_url": v.get("webVideoUrl", ""),
                    "language": "en",
                    "raw_text": text[:5000],
                    "author_handle": v.get("authorMeta", {}).get("name", ""),
                    "engagement_likes": v.get("diggCount", 0),
                    "engagement_comments": v.get("commentCount", 0),
                    "country_guess": "",
                })
        return results

    def _scrape_youtube(self, brand: Dict) -> List[Dict]:
        """Scrape YouTube comments via video search."""
        results = []
        query = f"{brand['display_name']} review OR tutorial"
        try:
            # First, get top videos matching the query
            videos = self._run_actor(
                self.ACTORS["google_search"],
                input_data={
                    "query": f"site:youtube.com {query}",
                    "maxResults": 5,
                    "languageCode": "en",
                },
            )
            for v in videos[:3]:  # Top 3 videos
                video_url = v.get("url", "")
                if "watch?v=" not in video_url:
                    continue
                # Get comments for this video
                comments = self._run_actor(
                    self.ACTORS["youtube_comments"],
                    input_data={
                        "videoUrl": video_url,
                        "maxComments": 15,
                    },
                )
                for c in comments:
                    text = c.get("text", "")
                    if text and len(text) > 30:
                        results.append({
                            "mention_id": c.get("id", f"yt_{int(time.time()*1000)}_{len(results)}"),
                            "timestamp": c.get("publishedAt") or datetime.utcnow().isoformat(),
                            "source": "youtube",
                            "source_url": c.get("authorChannelUrl", video_url),
                            "language": "en",
                            "raw_text": text[:5000],
                            "author_handle": c.get("authorDisplayName", ""),
                            "engagement_likes": c.get("likeCount", 0),
                            "engagement_comments": 0,
                            "country_guess": "",
                        })
        except Exception as e:
            print(f"  YouTube scraping error: {e}")
        return results

    def _scrape_facebook(self, brand: Dict) -> List[Dict]:
        """Scrape Facebook public posts mentioning the brand."""
        results = []
        query = brand["display_name"]
        try:
            posts = self._run_actor(
                self.ACTORS["facebook_pages"],
                input_data={
                    "query": query,
                    "max_posts": 15,
                    "language": "en",
                },
            )
            for p in posts:
                text = p.get("text", "") or p.get("message", "")
                if text and len(text) > 30:
                    results.append({
                        "mention_id": p.get("id", f"fb_{int(time.time()*1000)}_{len(results)}"),
                        "timestamp": p.get("time") or datetime.utcnow().isoformat(),
                        "source": "facebook",
                        "source_url": p.get("url", ""),
                        "language": "en",
                        "raw_text": text[:5000],
                        "author_handle": p.get("pageName", ""),
                        "engagement_likes": p.get("likes", 0),
                        "engagement_comments": p.get("comments", 0),
                        "country_guess": "",
                    })
        except Exception as e:
            print(f"  Facebook scraping error: {e}")
        return results

    def _scrape_blogs(self, brand: Dict) -> List[Dict]:
        """Scrape blogs via Google search + Tumblr."""
        results = []
        try:
            # Google search for blog posts about the brand
            blog_results = self._run_actor(
                self.ACTORS["google_search"],
                input_data={
                    "query": f"{brand['display_name']} skincare review blog",
                    "maxResults": 10,
                    "languageCode": "en",
                },
            )
            for r in blog_results:
                title = r.get("title", "")
                snippet = r.get("description", "")
                if title and ("review" in title.lower() or "blog" in r.get("url", "").lower() or "review" in snippet.lower()):
                    results.append({
                        "mention_id": r.get("url", f"bl_{int(time.time()*1000)}_{len(results)}"),
                        "timestamp": datetime.utcnow().isoformat(),
                        "source": "blog",
                        "source_url": r.get("url", ""),
                        "language": "en",
                        "raw_text": f"{title} - {snippet}"[:5000],
                        "author_handle": r.get("displayedUrl", ""),
                        "engagement_likes": 0,
                        "engagement_comments": 0,
                        "country_guess": "",
                    })
        except Exception as e:
            print(f"  Blog scraping error: {e}")
        return results

    def _scrape_reddit(self, brand: Dict) -> List[Dict]:
        results = []
        # Use the first 3 keywords to build search query
        query = " OR ".join(brand["keywords"][:3])
        # Search across all of Reddit (most coverage for brands)
        for keyword in brand["keywords"][:2]:
            posts = self._run_actor(
                self.ACTORS["reddit_search"],
                input_data={
                    "query": keyword,
                    "sort": "new",
                    "time": "month",
                    "limit": 25,
                },
            )
            for p in posts:
                results.append({
                    "mention_id": p.get("id", f"rd_{int(time.time()*1000)}_{len(results)}"),
                    "timestamp": datetime.fromtimestamp(p.get("created_utc", time.time())).isoformat(),
                    "source": "reddit",
                    "source_url": f"https://reddit.com{p.get('permalink', '')}",
                    "language": "en",
                    "raw_text": f"{p.get('title','')} | {p.get('selftext','') or p.get('text','')}"[:5000],
                    "author_handle": p.get("author", ""),
                    "engagement_likes": p.get("score", 0),
                    "engagement_comments": p.get("num_comments", 0),
                    "country_guess": "",
                })
        return results

    def _scrape_news(self, brand: Dict) -> List[Dict]:
        results = []
        # Query each brand name + main keyword (more results than just brand name)
        for query in brand["news_queries"][:1] + brand["keywords"][:1]:
            articles = self._run_actor(
                self.ACTORS["google_news"],
                input_data={
                    "query": query,
                    "language": "en",
                    "maxResults": 15,
                    "time": "past_month",
                },
            )
            for a in articles:
                # Handle both "source" as string and as object
                source_field = a.get("source", "")
                if isinstance(source_field, dict):
                    source_name = source_field.get("name", "")
                else:
                    source_name = str(source_field)

                results.append({
                    "mention_id": a.get("url", f"nw_{int(time.time()*1000)}_{len(results)}"),
                    "timestamp": a.get("date") or datetime.utcnow().isoformat(),
                    "source": "news",
                    "source_url": a.get("url", ""),
                    "language": "en",
                    "raw_text": f"{a.get('title','')} - {a.get('snippet', a.get('description', ''))}"[:5000],
                    "author_handle": source_name,
                    "engagement_likes": 0,
                    "engagement_comments": 0,
                    "country_guess": "",
                })
        return results

    def _scrape_youtube(self, brand: Dict) -> List[Dict]:
        # Future: search YouTube videos mentioning brand + scrape comments
        return []

    # ------------------------------------------------------------------
    # Apify client
    # ------------------------------------------------------------------

    def _run_actor(self, actor_id: str, input_data: Dict, timeout_s: int = 300) -> List[Dict]:
        """Runs an Apify actor synchronously and returns the dataset items."""
        url = f"{self.APIFY_BASE}/acts/{actor_id}/run-sync-get-dataset-items"
        params = {"token": self.token}
        try:
            resp = requests.post(url, params=params, json=input_data, timeout=timeout_s)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.Timeout:
            print(f"  Apify actor {actor_id} timed out after {timeout_s}s.")
            return []
        except requests.exceptions.HTTPError as e:
            err_body = e.response.text[:300] if e.response.text else ""
            print(f"  Apify actor {actor_id} HTTP error: {e.response.status_code} - {err_body}")
            return []

    # ------------------------------------------------------------------
    # Filtering / normalization
    # ------------------------------------------------------------------

    def _apply_quality_filters(self, df: pd.DataFrame, brand: Dict) -> pd.DataFrame:
        qf = self.config.get("scraping", {}).get("quality_filters", {})
        before = len(df)

        # Drop empties
        df = df[df["raw_text"].fillna("").str.len() >= qf.get("min_text_length_chars", 20)]
        df = df[df["raw_text"].fillna("").str.len() <= qf.get("max_text_length_chars", 5000)]

        # Require brand mention if configured
        if qf.get("require_brand_mention_in_text", True):
            keywords = [k.lower() for k in brand["keywords"]]
            pattern = "|".join(keywords)
            mask = df["raw_text"].fillna("").str.lower().str.contains(pattern, regex=True)
            df = df[mask]

        # Exclude noise phrases (matches that contain brand keyword but aren't about the brand)
        noise_phrases = qf.get("exclude_noise_phrases", [])
        if noise_phrases:
            noise_pattern = "|".join(noise_phrases)
            noise_mask = df["raw_text"].fillna("").str.lower().str.contains(noise_pattern, regex=True)
            df = df[~noise_mask]

        after = len(df)
        if before != after:
            print(f"  Filtered {before - after} low-quality mentions (kept {after}).")
        return df.reset_index(drop=True)


if __name__ == "__main__":
    # Quick local smoke test (requires .env with real APIFY_TOKEN)
    scraper = BrandMentionScraper()
    df = scraper.run_for_brand("augustinus_bader", platforms=["news"])
    print(df.head())
    print(f"Total: {len(df)}")
    if not df.empty:
        scraper.save_raw(df, "./data/test_mentions.csv")












