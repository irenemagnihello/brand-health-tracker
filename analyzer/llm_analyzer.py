"""
LLM-based Brand Mention Analyzer
=================================

Reads raw mentions, sends them to Claude in batches, and produces an
enriched DataFrame with sentiment, topics, entities, and crisis flags.

Output schema (CSV columns):
- mention_id
- timestamp
- source
- raw_text (kept for traceability)
- brand_key (input)
- brand_target (LLM-determined)
- sentiment_score (1-5)
- sentiment_label
- topic_tags (semicolon-separated)
- entity_product
- language
- crisis_flag (bool)
- crisis_reason
- summary
- actionable_insight
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional

import anthropic
import pandas as pd
import yaml
from dotenv import load_dotenv
import os

from analyzer.prompts import (
    build_extraction_prompt,
    build_crisis_prompt,
    build_executive_summary_prompt,
)

load_dotenv()


class BrandMentionAnalyzer:
    """Enriches raw mentions with Claude-powered structured insights."""

    def __init__(self, config_path: str = "./scrapers/config.yaml"):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY missing. Add it to your .env file.")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5")

        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        self.brand_options = list(self.config["brands"].keys())
        self.topic_taxonomy = self.config["analysis"]["topics_taxonomy"]
        self.crisis_signals = self.config["analysis"]["crisis_signals"]
        self.batch_size = self.config["analysis"]["batch_size"]
        self.temperature = self.config["analysis"]["temperature"]
        self.max_retries = int(os.getenv("LLM_MAX_RETRIES", "3"))
        self.timeout = int(os.getenv("LLM_TIMEOUT_SECONDS", "60"))

    # ------------------------------------------------------------------
    # Per-mention enrichment
    # ------------------------------------------------------------------

    def enrich_dataframe(self, df: pd.DataFrame, brand_key: str) -> pd.DataFrame:
        """Enrich a DataFrame of raw mentions for one brand with LLM analysis."""
        if df.empty:
            return df

        brand_label = self.config["brands"][brand_key]["display_name"]
        results: List[Dict] = []

        # Process in batches
        for start in range(0, len(df), self.batch_size):
            batch = df.iloc[start:start + self.batch_size]
            print(f"[{brand_key}] Enriching batch {start//self.batch_size + 1} "
                  f"({len(batch)} mentions)...")

            for _, row in batch.iterrows():
                enriched = self._enrich_single(
                    raw_text=row.get("raw_text", ""),
                    platform=row.get("source", "unknown"),
                    language_hint=row.get("language", "unknown"),
                    brand_key=brand_key,
                    brand_label=brand_label,
                )
                if enriched:
                    enriched["mention_id"] = row.get("mention_id", "")
                    enriched["timestamp"] = row.get("timestamp", "")
                    enriched["source"] = row.get("source", "")
                    enriched["source_url"] = row.get("source_url", "")
                    enriched["raw_text"] = row.get("raw_text", "")
                    enriched["brand_key"] = brand_key
                    enriched["author_handle"] = row.get("author_handle", "")
                    enriched["engagement_likes"] = row.get("engagement_likes", 0)
                    enriched["engagement_comments"] = row.get("engagement_comments", 0)
                    results.append(enriched)

        if not results:
            print(f"[{brand_key}] No successful enrichments.")
            return pd.DataFrame()

        enriched_df = pd.DataFrame(results)
        print(f"[{brand_key}] Enriched {len(enriched_df)} mentions successfully.")
        return enriched_df

    def _enrich_single(
        self,
        raw_text: str,
        platform: str,
        language_hint: str,
        brand_key: str,
        brand_label: str,
    ) -> Optional[Dict]:
        """Call Claude once for a single mention, return parsed JSON or None."""
        prompt = build_extraction_prompt(
            raw_text=raw_text,
            platform=platform,
            brand_target_key=brand_key,
            brand_target_label=brand_label,
            brand_options=self.brand_options,
            topic_taxonomy=self.topic_taxonomy,
            crisis_signals=self.crisis_signals,
            language_hint=language_hint,
        )

        for attempt in range(self.max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1024,
                    temperature=self.temperature,
                    timeout=self.timeout,
                    messages=[{"role": "user", "content": prompt}],
                )
                text = response.content[0].text.strip()
                # Strip code fences if model wraps JSON
                if text.startswith("```"):
                    text = text.split("```", 2)[1]
                    if text.startswith("json"):
                        text = text[4:]
                    text = text.strip()
                parsed = json.loads(text)
                # Normalize topic_tags to list
                if isinstance(parsed.get("topic_tags"), str):
                    parsed["topic_tags"] = [t.strip() for t in parsed["topic_tags"].split(",")]
                # Normalize crisis_flag
                if isinstance(parsed.get("crisis_flag"), str):
                    parsed["crisis_flag"] = parsed["crisis_flag"].lower() == "true"
                return parsed
            except json.JSONDecodeError as e:
                print(f"  JSON parse error (attempt {attempt+1}): {e}")
                print(f"  Raw: {text[:200]}")
            except anthropic.APIError as e:
                print(f"  API error (attempt {attempt+1}): {e}")
                time.sleep(2 ** attempt)
            except Exception as e:
                print(f"  Unexpected error (attempt {attempt+1}): {e}")
                time.sleep(1)
        return None

    # ------------------------------------------------------------------
    # Batch-level analysis
    # ------------------------------------------------------------------

    def detect_crisis(self, enriched_df: pd.DataFrame, brand_key: str) -> Dict:
        """Run crisis detection on a batch of enriched mentions for a brand."""
        if enriched_df.empty:
            return {"crisis_detected": False}

        brand_label = self.config["brands"][brand_key]["display_name"]
        # Use up to 30 most recent mentions, crisis-flagged first
        sample = enriched_df.sort_values(
            by=["crisis_flag", "timestamp"], ascending=[False, False]
        ).head(30)

        mentions_for_prompt = sample[["raw_text", "sentiment_label", "topic_tags"]].to_dict("records")

        prompt = build_crisis_prompt(
            mentions=mentions_for_prompt,
            brand_target_label=brand_label,
            batch_size=len(mentions_for_prompt),
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                temperature=0.1,
                timeout=self.timeout,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("```", 2)[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            return json.loads(text)
        except Exception as e:
            print(f"Crisis detection error: {e}")
            return {"crisis_detected": False, "error": str(e)}

    def generate_executive_summary(
        self,
        enriched_df: pd.DataFrame,
        brand_key: str,
        date_range: str,
        comparison_brands: Optional[List[str]] = None,
        previous_volume: Optional[int] = None,
    ) -> str:
        """Generate a 100-120 word executive summary for the report."""
        if enriched_df.empty:
            return "No mentions recorded this week."

        brand_label = self.config["brands"][brand_key]["display_name"]
        total = len(enriched_df)
        avg_sent = enriched_df["sentiment_score"].mean()
        crisis_count = int(enriched_df["crisis_flag"].sum())

        all_topics = []
        for tags in enriched_df["topic_tags"].dropna():
            if isinstance(tags, list):
                all_topics.extend(tags)
            elif isinstance(tags, str):
                all_topics.extend([t.strip() for t in tags.split(";")])
        topic_counts = pd.Series(all_topics).value_counts()
        top_topics = topic_counts.head(5).index.tolist()

        top_products = (
            enriched_df["entity_product"]
            .dropna()
            .value_counts()
            .head(5)
            .index.tolist()
        )

        current_volume = total
        if previous_volume and previous_volume > 0:
            volume_change_pct = ((current_volume - previous_volume) / previous_volume) * 100
        else:
            volume_change_pct = 0.0

        prompt = build_executive_summary_prompt(
            brand_target_label=brand_label,
            date_range=date_range,
            comparison_brand_options=comparison_brands or [],
            total_mentions=total,
            avg_sentiment=avg_sent,
            top_topics=top_topics,
            top_products=top_products,
            crisis_count=crisis_count,
            volume_change_pct=volume_change_pct,
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                temperature=0.4,
                timeout=self.timeout,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()
        except Exception as e:
            print(f"Executive summary error: {e}")
            return "Executive summary unavailable due to processing error."

    def save_enriched(self, df: pd.DataFrame, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)
        print(f"Saved {len(df)} enriched mentions → {path}")


if __name__ == "__main__":
    # Smoke test on the sample data
    analyzer = BrandMentionAnalyzer()
    raw = pd.read_csv("./data/sample_mentions.csv")
    raw = raw[raw["brand_key"] == "augustinus_bader"].head(5)
    enriched = analyzer.enrich_dataframe(raw, "augustinus_bader")
    print(enriched[["raw_text", "sentiment_score", "topic_tags", "crisis_flag"]].head())


