"""
Live pipeline: scrape real mentions via Apify, analyze with Claude,
and write results to Google Sheets via service account.

Triggered by GitHub Action 'Brand Health Tracker - LIVE'.
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

# Reuse modules from the demo pipeline
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scrapers.apify_scraper import BrandMentionScraper  # noqa
from analyzer.llm_analyzer import BrandMentionAnalyzer  # noqa
from report_generator.pdf_generator import WeeklyReportGenerator  # noqa

load_dotenv()


def write_to_google_sheets(df: pd.DataFrame, sheet_id: str) -> int:
    """Write enriched mentions to the LIVE Google Sheet via service account."""
    import gspread
    from google.oauth2.service_account import Credentials

    creds_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not creds_json:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON missing")

    # Write JSON to temp file (gspread expects file path)
    creds_path = "/tmp/gcp-sa.json"
    with open(creds_path, "w") as f:
        f.write(creds_json)

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    client = gspread.authorize(creds)

    # Open the sheet by ID
    sheet = client.open_by_key(sheet_id).sheet1

    # Clear existing data (header + all rows)
    sheet.clear()

    # Prepare DataFrame for writing
    # Columns we expect in the LIVE sheet
    expected_cols = [
        "date", "timestamp", "brand_key", "brand_label", "source",
        "sentiment_score", "sentiment_label", "topic_tags",
        "entity_product", "language", "country_guess",
        "engagement_likes", "engagement_comments", "engagement_total",
        "crisis_flag", "crisis_reason", "summary",
        "author_handle", "source_url", "raw_text",
    ]

    # Ensure all expected cols exist
    for col in expected_cols:
        if col not in df.columns:
            df[col] = ""

    df = df[expected_cols].copy()

    # Convert to list of lists (header + rows)
    values = [expected_cols] + df.fillna("").astype(str).values.tolist()

    # Write in one batch (faster + atomic)
    sheet.update(values=values, range_name="A1")

    print(f"Wrote {len(df)} rows + header to Google Sheet {sheet_id}")
    return len(df)


def run_live_pipeline(brands: list = None, platforms: list = None) -> dict:
    """Full live pipeline: scrape → analyze → write to Google Sheets."""
    print("=" * 70)
    print("LIVE PIPELINE — scraping real mentions + Claude analysis")
    print("=" * 70)

    sheet_id = os.getenv("GOOGLE_SHEETS_ID")
    if not sheet_id:
        raise ValueError("GOOGLE_SHEETS_ID missing")

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

        # Save raw locally (debug)
        scraper.save_raw(raw_df, f"./output/raw_{brand_key}_{datetime.now():%Y%m%d_%H%M}.csv")

        print(f"\n[{brand_key}] === Enriching with Claude ===")
        enriched_df = analyzer.enrich_dataframe(raw_df, brand_key)

        if enriched_df.empty:
            print(f"[{brand_key}] No successful enrichments. Skipping.")
            continue

        analyzer.save_enriched(enriched_df, f"./output/enriched_{brand_key}_{datetime.now():%Y%m%d_%H%M}.csv")

        # Collect for batch Google Sheets write
        all_enriched.append(enriched_df)

        print(f"\n[{brand_key}] === Generating PDF report ===")
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

    if not all_enriched:
        print("\nNo mentions collected across any brand. Skipping Sheets write.")
        return {}

    # Combine all enriched data
    combined = pd.concat(all_enriched, ignore_index=True)

    # Compute additional columns for Sheets
    combined["date"] = pd.to_datetime(combined["timestamp"]).dt.strftime("%Y-%m-%d")
    combined["brand_label"] = combined["brand_key"].map({
        "augustinus_bader": "Augustinus Bader",
        "the_ordinary": "The Ordinary",
        "glossier": "Glossier",
    })
    combined["engagement_total"] = (
        combined["engagement_likes"].fillna(0) + combined["engagement_comments"].fillna(0)
    )

    print(f"\n=== Writing {len(combined)} enriched mentions to Google Sheets ===")
    n_written = write_to_google_sheets(combined, sheet_id)

    return {
        "rows_written": n_written,
        "brands_processed": list(all_enriched[0]["brand_key"].unique()) if all_enriched else [],
        "reports": report_paths,
    }


def main():
    parser = argparse.ArgumentParser(description="Brand Health Tracker LIVE pipeline")
    parser.add_argument("--brands", nargs="+", help="Brand keys to process (default: all)")
    parser.add_argument("--platforms", nargs="+",
                        choices=["instagram", "tiktok", "reddit", "news", "youtube"])
    args = parser.parse_args()

    try:
        result = run_live_pipeline(brands=args.brands, platforms=args.platforms)
        print("\n" + "=" * 70)
        print("LIVE PIPELINE COMPLETE")
        print("=" * 70)
        print(f"  Rows written to Sheets: {result.get('rows_written', 0)}")
        print(f"  Brands processed: {result.get('brands_processed', [])}")
        for brand, path in result.get("reports", {}).items():
            print(f"  Report: {brand} → {path}")
        return 0
    except Exception as e:
        print(f"\nFATAL ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
