"""Generate enriched CSVs locally + commit. No Google Sheets (auth issues).

This is the production pipeline for the Brand Health Tracker.
Generates enriched CSVs that the user can manually upload to Google Sheets.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scrapers.apify_scraper import BrandMentionScraper  # noqa
from analyzer.llm_analyzer import BrandMentionAnalyzer  # noqa
from report_generator.pdf_generator import WeeklyReportGenerator  # noqa

load_dotenv()


def run_pipeline(brands: list = None, platforms: list = None) -> dict:
    """Full pipeline: scrape → analyze → CSV + PDF output."""
    print("=" * 70)
    print("BRAND HEALTH TRACKER - Pipeline (local output)")
    print("=" * 70)

    scraper = BrandMentionScraper()
    analyzer = BrandMentionAnalyzer()
    report_gen = WeeklyReportGenerator()

    brand_keys = brands or list(scraper.config["brands"].keys())
    all_enriched = []
    report_paths = {}

    for brand_key in brand_keys:
        print(f"\n[{brand_key}] === Scraping ===")
        raw_df = scraper.run_for_brand(brand_key, platforms)

        if raw_df.empty:
            print(f"[{brand_key}] No mentions scraped. Skipping.")
            continue

        scraper.save_raw(raw_df, f"./data/raw/{brand_key}_{datetime.now():%Y%m%d_%H%M}.csv")

        print(f"\n[{brand_key}] === Enriching with Claude ===")
        enriched_df = analyzer.enrich_dataframe(raw_df, brand_key)

        if enriched_df.empty:
            print(f"[{brand_key}] No successful enrichments. Skipping.")
            continue

        # Add columns needed for Google Sheets / dashboard
        # Parse timestamps - handle mixed formats (ISO + Unix epoch)
        enriched_df["date"] = pd.to_datetime(
            enriched_df["timestamp"], format="mixed", errors="coerce"
        ).dt.strftime("%Y-%m-%d")
        enriched_df["brand_label"] = enriched_df["brand_key"].map({
            "augustinus_bader": "Augustinus Bader",
            "the_ordinary": "The Ordinary",
            "glossier": "Glossier",
        })
        enriched_df["engagement_total"] = (
            enriched_df["engagement_likes"].fillna(0) + enriched_df["engagement_comments"].fillna(0)
        )

        analyzer.save_enriched(enriched_df, f"./data/enriched/{brand_key}_{datetime.now():%Y%m%d_%H%M}.csv")

        # CSV ready for manual upload to Google Sheets
        output_cols = [
            "date", "timestamp", "brand_key", "brand_label", "source",
            "sentiment_score", "sentiment_label", "topic_tags",
            "entity_product", "language", "country_guess",
            "engagement_likes", "engagement_comments", "engagement_total",
            "crisis_flag", "crisis_reason", "summary",
            "author_handle", "source_url", "raw_text",
        ]
        for col in output_cols:
            if col not in enriched_df.columns:
                enriched_df[col] = ""
        enriched_df[output_cols].to_csv(
            f"./output/{brand_key}_for_sheets_{datetime.now():%Y%m%d_%H%M}.csv",
            index=False,
        )

        # PDF report
        date_range = (
            f"{(datetime.now() - pd.Timedelta(days=7)).strftime('%Y-%m-%d')} "
            f"to {datetime.now().strftime('%Y-%m-%d')}"
        )
        exec_summary = analyzer.generate_executive_summary(
            enriched_df=enriched_df,
            brand_key=brand_key,
            date_range=date_range,
            comparison_brands=[b for b in brand_keys if b != brand_key],
        )
        crisis_info = analyzer.detect_crisis(enriched_df, brand_key)
        report_path = report_gen.generate(
            enriched_df=enriched_df,
            brand_key=brand_key,
            executive_summary=exec_summary,
            crisis_info=crisis_info,
            date_range=date_range,
        )
        report_paths[brand_key] = report_path

        all_enriched.append(enriched_df)

    if not all_enriched:
        print("\nNo mentions collected.")
        return {}

    combined = pd.concat(all_enriched, ignore_index=True)

    # Combined CSV for dashboard upload
    combined_csv = f"./output/combined_for_sheets_{datetime.now():%Y%m%d_%H%M}.csv"
    combined.to_csv(combined_csv, index=False)
    print(f"\n=== Combined CSV saved: {combined_csv} ===")
    print(f"Total mentions: {len(combined)}")

    return {
        "rows_total": len(combined),
        "brands_processed": list(combined["brand_key"].unique()),
        "reports": report_paths,
    }


def main():
    parser = argparse.ArgumentParser(description="Brand Health Tracker pipeline (local output)")
    parser.add_argument("--brands", nargs="+", help="Brand keys to process (default: all)")
    parser.add_argument("--platforms", nargs="+",
                        choices=["instagram", "tiktok", "reddit", "news", "youtube"])
    args = parser.parse_args()

    try:
        result = run_pipeline(brands=args.brands, platforms=args.platforms)
        print("\n" + "=" * 70)
        print("PIPELINE COMPLETE")
        print("=" * 70)
        print(f"  Total rows: {result.get('rows_total', 0)}")
        print(f"  Brands: {result.get('brands_processed', [])}")
        return 0
    except Exception as e:
        print(f"\nFATAL ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

