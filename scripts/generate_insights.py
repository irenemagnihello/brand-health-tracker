"""Generate AI-powered insights from the brand tracker CSV.
Run: python3 scripts/generate_insights.py
"""

import os
import anthropic
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

CSV_PATH = "./output/combined_for_sheets_20260721_1642.csv"


def main():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5")

    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set in .env")
        return

    if not os.path.exists(CSV_PATH):
        print(f"ERROR: {CSV_PATH} not found. Run local_pipeline.py first.")
        return

    print(f"Using model: {model}\n")
    df = pd.read_csv(CSV_PATH)
    client = anthropic.Anthropic(api_key=api_key)

    for brand in df["brand_label"].unique():
        sub = df[df["brand_label"] == brand]

        avg_sentiment = sub["sentiment_score"].mean()
        total = len(sub)
        by_source = sub["source"].value_counts().to_dict()
        top_topics = sub["topic_tags"].value_counts().head(3).to_dict()
        crisis_count = int(sub["crisis_flag"].sum()) if "crisis_flag" in sub.columns else 0

        prompt = f"""You are a senior brand strategist analyzing social listening data.

Brand: {brand}
Total mentions: {total}
Avg sentiment (1-5): {avg_sentiment:.2f}
By source: {by_source}
Top topics: {top_topics}
Crisis mentions: {crisis_count}

Generate 3 actionable insights for a brand manager. Each insight should be:
- 1 sentence max
- Specific (with number/metric)
- Action-oriented (what to do)
- In English

Format: just 3 bullets, no intro, no conclusion."""

        msg = client.messages.create(
            model=model,
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )

        print(f"\n=== {brand} ({total} mentions, sentiment {avg_sentiment:.2f}/5) ===")
        print(msg.content[0].text)
        print()


if __name__ == "__main__":
    main()
