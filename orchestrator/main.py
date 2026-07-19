"""
Main pipeline orchestrator for the Brand Health Tracker
========================================================

Coordinates: scrape → analyze → crisis detection → executive summary → report

Usage:
    python -m orchestrator.main                 # full pipeline for all brands
    python -m orchestrator.main --brands augustinus_bader --platforms reddit news
    python -m orchestrator.main --demo          # use mock data, skip scraping
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from scrapers.apify_scraper import BrandMentionScraper
from analyzer.llm_analyzer import BrandMentionAnalyzer
from report_generator.pdf_generator import WeeklyReportGenerator


def run_demo_pipeline() -> dict:
    """Run the full pipeline using the bundled sample data, no API calls."""
    print("=" * 70)
    print("DEMO MODE: using bundled sample data, no API calls to Apify/Claude.")
    print("=" * 70)

    raw = pd.read_csv("./data/sample_mentions.csv")
    print(f"Loaded {len(raw)} sample mentions across {raw['brand_key'].nunique()} brands.")

    # In demo mode, raw data already has the enrichment columns (pre-computed)
    # so we skip the LLM call to avoid costs. Real run will call LLM.
    enriched_df = raw.copy()
    enriched_df["topic_tags"] = enriched_df["topic_tags"].fillna("")

    report_paths = {}
    analyzer = BrandMentionAnalyzer.__new__(BrandMentionAnalyzer)  # bypass __init__
    report_gen = WeeklyReportGenerator()

    for brand_key, group in enriched_df.groupby("brand_key"):
        print(f"\n[{brand_key}] Generating report for {len(group)} mentions...")
        crisis_info = {"crisis_detected": False}
        exec_summary = (
            f"Demo report for {brand_key} based on {len(group)} pre-enriched mentions. "
            f"Average sentiment: {group['sentiment_score'].mean():.2f}. "
            f"Crisis flags: {int(group['crisis_flag'].sum())}."
        )
        report_path = report_gen.generate(
            enriched_df=group,
            brand_key=brand_key,
            executive_summary=exec_summary,
            crisis_info=crisis_info,
        )
        report_paths[brand_key] = report_path

    return report_paths


def run_live_pipeline(brands: list = None, platforms: list = None) -> dict:
    """Full live pipeline: scrape → analyze → report."""
    print("=" * 70)
    print("LIVE MODE: scraping real mentions and calling Claude.")
    print("=" * 70)

    scraper = BrandMentionScraper()
    analyzer = BrandMentionAnalyzer()
    report_gen = WeeklyReportGenerator()

    brand_keys = brands or list(scraper.config["brands"].keys())
    report_paths = {}

    for brand_key in brand_keys:
        print(f"\n[{brand_key}] === Scraping ===")
        raw_df = scraper.run_for_brand(brand_key, platforms)

        if raw_df.empty:
            print(f"[{brand_key}] No mentions scraped. Skipping.")
            continue

        scraper.save_raw(raw_df, f"./data/raw/{brand_key}_{datetime.now():%Y%m%d_%H%M}.csv")

        print(f"\n[{brand_key}] === Enriching with LLM ===")
        enriched_df = analyzer.enrich_dataframe(raw_df, brand_key)

        if enriched_df.empty:
            print(f"[{brand_key}] No successful enrichments. Skipping report.")
            continue

        analyzer.save_enriched(enriched_df, f"./data/enriched/{brand_key}_{datetime.now():%Y%m%d_%H%M}.csv")

        print(f"\n[{brand_key}] === Crisis detection ===")
        crisis_info = analyzer.detect_crisis(enriched_df, brand_key)
        print(f"  Crisis detected: {crisis_info.get('crisis_detected', False)}")
        if crisis_info.get("crisis_detected"):
            print(f"  Type: {crisis_info.get('crisis_type')}")
            print(f"  Severity: {crisis_info.get('severity')}")

        print(f"\n[{brand_key}] === Executive summary ===")
        date_range = (
            f"{(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')} "
            f"to {datetime.now().strftime('%Y-%m-%d')}"
        )
        exec_summary = analyzer.generate_executive_summary(
            enriched_df=enriched_df,
            brand_key=brand_key,
            date_range=date_range,
            comparison_brands=[b for b in brand_keys if b != brand_key],
        )
        print(f"  {exec_summary[:200]}...")

        print(f"\n[{brand_key}] === Generating PDF report ===")
        report_path = report_gen.generate(
            enriched_df=enriched_df,
            brand_key=brand_key,
            executive_summary=exec_summary,
            crisis_info=crisis_info,
            date_range=date_range,
        )
        report_paths[brand_key] = report_path

    return report_paths


def main():
    parser = argparse.ArgumentParser(description="Brand Health Tracker pipeline")
    parser.add_argument("--brands", nargs="+", help="Brand keys to process (default: all)")
    parser.add_argument("--platforms", nargs="+", help="Platforms to scrape",
                        choices=["instagram", "tiktok", "reddit", "news", "youtube"])
    parser.add_argument("--demo", action="store_true",
                        help="Run demo pipeline using bundled sample data (no API calls)")
    args = parser.parse_args()

    try:
        if args.demo:
            reports = run_demo_pipeline()
        else:
            reports = run_live_pipeline(brands=args.brands, platforms=args.platforms)

        print("\n" + "=" * 70)
        print("PIPELINE COMPLETE")
        print("=" * 70)
        for brand, path in reports.items():
            print(f"  {brand}: {path}")

        return 0
    except Exception as e:
        print(f"\nFATAL ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
