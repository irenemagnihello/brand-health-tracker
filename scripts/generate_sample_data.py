"""
Generates a realistic sample dataset for the Brand Health Tracker demo.
Produces ~150 enriched mentions across 3 brands with varied sentiment,
topics, sources, and languages. This dataset is what the dashboard
and PDF reports render in demo mode.

Run: python scripts/generate_sample_data.py
"""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)  # Reproducibility


# ---- Templates per source -----------------------------------------------

REDDIT_TEMPLATES = {
    "augustinus_bader": [
        ("Has anyone tried The Cream for like 4+ weeks? I'm on week 3 and the texture is amazing but not sure I see $200 worth of difference yet.", 3, ["efficacy_results", "price_value", "texture_consistency"]),
        ("Augustinus Bader review after 3 months: my skin barrier is stronger, redness is down. Worth the money if you can afford it IMO.", 5, ["efficacy_results", "price_value"]),
        ("I keep seeing The Rich Cream everywhere but $290 for 50ml feels insane. Are there real dupes?", 2, ["price_value", "duplicates_dupes"]),
        ("Used AB The Cream for 6 months. Scent is subtle, packaging is gorgeous. Skin looks good but not transformative.", 3, ["packaging_design", "scent_fragrance", "efficacy_results"]),
        ("Got a sample from Space NK. The Cream is thick but absorbs well. Not convinced on the science claims though.", 3, ["efficacy_results", "ingredients_formulation"]),
        ("Honestly Augustinus Bader works but it's just good basic skincare with great marketing. Save your money.", 2, ["price_value", "ingredients_formulation"]),
        ("My dermatologist recommended The Cream for my eczema-prone skin. It's helped more than anything else. Expensive but worth it.", 4, ["efficacy_results", "comparison_vs_competitor"]),
        ("Started The Rich Cream last month. I love the packaging but my skin broke out a little. Maybe too rich for me.", 2, ["packaging_design", "irritation_reactions"]),
        ("AB skincare is luxury with substance. The science behind TFC8 is solid. Stop hating and read the patents.", 4, ["ingredients_formulation", "efficacy_results"]),
        ("Anyone tried both The Cream and La Mer? Going to AB after years of La Mer. Initial impression is positive.", 4, ["comparison_vs_competitor", "routine_layering"]),
    ],
    "the_ordinary": [
        ("The Ordinary Niacinamide is a game-changer for oily skin. $5 and it actually works.", 5, ["ingredients_formulation", "price_value", "efficacy_results"]),
        ("Started Glycolic Acid 7% Toning Solution last week. Tingled at first but skin looks brighter now.", 4, ["efficacy_results", "texture_consistency", "irritation_reactions"]),
        ("My skin got irritated from the AHA 30% + BHA 2% peel. Used too often. Now I do it once a month.", 2, ["irritation_reactions", "routine_layering"]),
        ("Retinol 0.5% in Squalane is great for beginners. Cheap and effective.", 5, ["ingredients_formulation", "price_value"]),
        ("Deciem is taking over my whole routine. The Ordinary + NIOD covers everything I need.", 5, ["brand_aesthetic", "price_value"]),
        ("Has anyone else gotten tiny white bumps from The Ordinary's Hyaluronic Acid? It broke me out weird.", 2, ["irritation_reactions", "texture_consistency"]),
        ("Buffet serum is overhyped IMO. It's fine, not amazing. Save your $30.", 2, ["price_value", "efficacy_results"]),
        ("The Ordinary vs The Inkey List: Ordinary has better formulations for the same price point. Just my experience.", 4, ["comparison_vs_competitor", "price_value", "ingredients_formulation"]),
        ("EU has more restrictions on what's allowed so some products differ. Make sure you check your region.", 3, ["sustainability_ethics", "comparison_vs_competitor"]),
        ("Multi-Peptide + HA is great for anti-aging without irritation. Been using 6 months.", 5, ["efficacy_results", "ingredients_formulation"]),
        ("Their customer service is awful. Wrong order, no reply for 2 weeks. Product is fine though.", 2, ["customer_service", "shipping_delivery"]),
        ("Marine Hyaluronics is way underrated. Light, hydrating, plays well with everything.", 5, ["texture_consistency", "routine_layering"]),
    ],
    "glossier": [
        ("Boy Brow is my holy grail. Have repurchased 4 times. Makes brows look natural and full.", 5, ["efficacy_results", "comparison_vs_competitor"]),
        ("Cloud Paint in Beam is perfect for a natural flush. Tiny bottle though, runs out fast.", 4, ["efficacy_results", "texture_consistency"]),
        ("Glossier You fragrance is so unique. Warm, skin-scent, gets compliments constantly.", 5, ["scent_fragrance", "comparison_vs_competitor"]),
        ("Honestly disappointed with Glossier lately. Products are mid and customer service has gone downhill.", 2, ["customer_service", "brand_aesthetic"]),
        ("Generation G is the best tinted lip balm I've tried. Shade range is inclusive and the texture is perfect.", 5, ["texture_consistency", "color_range"]),
        ("The pink packaging is iconic but quality control has slipped. My last Lash Slick was clumpy.", 2, ["packaging_design", "texture_consistency"]),
        ("Glossier is overpriced for what you get. Their marketing is brilliant but the products are basic.", 2, ["price_value", "brand_aesthetic"]),
        ("Invisible Shield SPF is great under makeup. No white cast, layers well. Worth the price.", 4, ["routine_layering", "texture_consistency"]),
        ("Solution exfoliator has changed my skin. Gentle but effective. Use it 3x a week.", 5, ["efficacy_results", "routine_layering"]),
        ("Their recent rebrand feels directionless. Lost the millennial pink magic that made them special.", 1, ["brand_aesthetic", "customer_service"]),
        ("Stretch concealer is so creamy and natural-looking. Shade match is perfect for my skin tone.", 5, ["texture_consistency", "color_range", "efficacy_results"]),
    ],
}

INSTAGRAM_TEMPLATES = {
    "augustinus_bader": [
        ("✨ My skin is glowing after 2 weeks of The Cream. The texture is unlike anything else. #augustinusbader #luxuryskincare", 5, ["efficacy_results", "texture_consistency", "influencer_recommendation"]),
        ("The packaging of Augustinus Bader is unmatched. It feels like jewelry on my vanity 💎 #abskincare", 4, ["packaging_design"]),
        ("Honest review: AB is good but not life-changing. Save your money and try Drunk Elephant first.", 2, ["price_value", "comparison_vs_competitor"]),
        ("My aesthetician recommended The Rich Cream for dry skin. Game changer for winter. #augustinusbader", 5, ["efficacy_results", "influencer_recommendation"]),
        ("💸 Yes it's expensive but my skin has never looked better. Worth every penny. #thecream", 5, ["price_value", "efficacy_results"]),
        ("Got AB as a gift. The packaging is so heavy and luxurious. The Cream feels divine on the skin.", 4, ["packaging_design", "texture_consistency"]),
    ],
    "the_ordinary": [
        ("My entire skincare routine is The Ordinary. Affordable and effective. Period. #theordinary #deciem", 5, ["price_value", "ingredients_formulation"]),
        ("💧 Niacinamide 10% saved my oily T-zone. $5 bottle lasts 6 months. #theordinaryhack", 5, ["efficacy_results", "price_value"]),
        ("Mixing Buffet + Hyaluronic Acid = 💦 skin. Try it. #skincaretok #deciem", 5, ["routine_layering", "ingredients_formulation"]),
        ("Their new EU formulations are different from US ones. Check ingredients carefully.", 3, ["sustainability_ethics", "comparison_vs_competitor"]),
        ("Started with Glycolic Acid, my skin is so much brighter. #skincaretransformation #theordinary", 4, ["efficacy_results"]),
    ],
    "glossier": [
        ("Boy Brow + Cloud Paint + Lash Slick = my entire makeup look. Clean girl aesthetic on point 💕 #glossier #boybrow", 5, ["brand_aesthetic", "routine_layering"]),
        ("New Glossier You EDP smells like warm skin and cashmere. Obsessed. #glossier #fragrance", 5, ["scent_fragrance", "new_launch"]),
        ("Stretch Concealer shade match is so perfect. My under-eye area looks awake for once ✨ #glossier #cleanbeauty", 4, ["texture_consistency", "color_range"]),
        ("Honest review: Glossier is way overpriced for drugstore quality products. Pretty packaging only.", 2, ["price_value", "brand_aesthetic"]),
        ("Their Milky Oil cleanser is so gentle. Removes everything without stripping. #glossierreview", 5, ["efficacy_results", "texture_consistency"]),
    ],
}

TIKTOK_TEMPLATES = {
    "augustinus_bader": [
        ("POV: you saved up for Augustinus Bader The Cream and it actually changed your skin 😭✨ #skincaretok #augustinusbader", 5, ["efficacy_results", "price_value", "influencer_recommendation"]),
        ("Hot take: AB is overpriced moisturizer with fancy packaging. Save your $290.", 1, ["price_value", "packaging_design"]),
        ("Augustinus Bader vs La Mer - which luxury skincare is actually worth it? Full comparison in bio 📲", 4, ["comparison_vs_competitor", "price_value"]),
        ("Why I switched from Augustinus Bader to Tatcha (and saved $200) #skintok #luxuryskincare", 3, ["comparison_vs_competitor", "price_value"]),
    ],
    "the_ordinary": [
        ("The Ordinary dupes that work just as well as luxury brands 💸 #skintok #theordinaryhack", 5, ["duplicates_dupes", "price_value"]),
        ("Wait this $6 serum is better than my $80 one??? The Ordinary always wins #deciem", 5, ["price_value", "comparison_vs_competitor"]),
        ("How to layer The Ordinary without breaking out ✨ (full routine in bio) #skincareroutine", 4, ["routine_layering", "irritation_reactions"]),
        ("The Ordinary Glycolic Acid transformed my texture in 2 weeks 😍 #theordinary", 5, ["efficacy_results", "texture_consistency"]),
    ],
    "glossier": [
        ("Glossier is the brand of girlboss burnout and I'm so here for it 💕 #cleanbeauty #glossier", 4, ["brand_aesthetic"]),
        ("Honest Glossier review: pretty packaging, mid products, $$$ price tag. Save your coins 🪙", 2, ["price_value", "brand_aesthetic"]),
        ("Makeup routine in 5 minutes using only Glossier ✨ #glossier #cleanbeauty", 4, ["routine_layering", "brand_aesthetic"]),
        ("Glossier Lash Slick vs Maybelline Sky High - which wins? 👀 #makeuptok", 3, ["comparison_vs_competitor"]),
    ],
}

NEWS_TEMPLATES = {
    "augustinus_bader": [
        ("Augustinus Bader reports record Q3 growth driven by hero product The Cream expansion in Asia-Pacific markets.", 4, ["new_launch", "sustainability_ethics"]),
        ("Luxury skincare brand Augustinus Bader valued at $1B+ in latest funding round, with celebrity investors joining.", 4, ["new_launch", "celebrity_endorsement"]),
        ("Augustinus Bader launches new sustainable packaging line, commits to refillable containers by 2026.", 4, ["sustainability_ethics", "new_launch"]),
    ],
    "the_ordinary": [
        ("Deciem announces expanded EU product line following regulatory compliance investments.", 3, ["sustainability_ethics", "new_launch"]),
        ("The Ordinary parent company Deciem opens first flagship retail store in London.", 3, ["new_launch", "brand_aesthetic"]),
        ("Estée Lauder increases stake in Deciem, signaling long-term commitment to The Ordinary brand.", 4, ["new_launch"]),
    ],
    "glossier": [
        ("Glossier announces strategic refocus on core hero products after 2024 sales dip.", 3, ["new_launch", "customer_service"]),
        ("Glossier reports customer service overhaul following 2023 backlash over shipping delays.", 2, ["customer_service", "shipping_delivery"]),
        ("Emily Weiss steps back from Glossier daily operations, brand enters new leadership phase.", 3, ["founders_leaving", "new_launch"]),
    ],
}

# Crisis scenario templates (sparse, ~3% of mentions)
CRISIS_TEMPLATES = [
    ("URGENT: Avoid The Ordinary AHA 30% peel if you have sensitive skin. My face is burned and peeling. Where's the recall?", 1, ["irritation_reactions", "safety_alert"], True, "Multiple reports of chemical burns from AHA peel"),
    ("Augustinus Bader recall notice: certain batches of The Rich Cream contaminated per FDA warning.", 1, ["safety_alert", "product_recall"], True, "FDA recall notice on specific batch"),
    ("Glossier customer data breach exposed — my email and order history leaked. Their security is embarrassing.", 1, ["customer_service", "regulatory_warning"], True, "Customer data breach"),
]


def generate_mentions():
    """Build the full sample dataset."""
    rows = []
    base_time = datetime(2025, 6, 9, 12, 0, 0)  # ~1 week ago

    brand_keys = ["augustinus_bader", "the_ordinary", "glossier"]

    for brand_key in brand_keys:
        # Reddit: ~25 mentions per brand
        for text, sentiment, topics in REDDIT_TEMPLATES[brand_key]:
            for _ in range(2):  # Duplicate to get volume
                ts = base_time + timedelta(days=random.uniform(0, 6), hours=random.uniform(0, 23))
                rows.append({
                    "mention_id": f"rd_{len(rows):04d}",
                    "timestamp": ts.isoformat(),
                    "source": "reddit",
                    "source_url": f"https://reddit.com/r/SkincareAddiction/comments/{len(rows)}",
                    "language": random.choices(["en", "de"], weights=[0.85, 0.15])[0],
                    "raw_text": text,
                    "brand_key": brand_key,
                    "author_handle": f"user_{random.randint(1000, 99999)}",
                    "engagement_likes": random.randint(5, 800),
                    "engagement_comments": random.randint(0, 120),
                    "country_guess": random.choice(["US", "UK", "DE", "FR", "IT"]),
                    "sentiment_score": sentiment,
                    "sentiment_label": "positive" if sentiment >= 4 else ("negative" if sentiment <= 2 else "neutral"),
                    "topic_tags": ";".join(topics),
                    "entity_product": None,
                    "crisis_flag": False,
                    "crisis_reason": None,
                    "summary": text[:80] + "...",
                    "actionable_insight": None,
                })

        # Instagram: ~15 mentions per brand
        for text, sentiment, topics in INSTAGRAM_TEMPLATES[brand_key]:
            ts = base_time + timedelta(days=random.uniform(0, 6), hours=random.uniform(0, 23))
            rows.append({
                "mention_id": f"ig_{len(rows):04d}",
                "timestamp": ts.isoformat(),
                "source": "instagram",
                "source_url": f"https://instagram.com/p/{len(rows)}",
                "language": "en",
                "raw_text": text,
                "brand_key": brand_key,
                "author_handle": f"@influencer_{random.randint(100, 9999)}",
                "engagement_likes": random.randint(200, 25000),
                "engagement_comments": random.randint(5, 500),
                "country_guess": random.choice(["US", "UK", "DE", "FR", "IT"]),
                "sentiment_score": sentiment,
                "sentiment_label": "positive" if sentiment >= 4 else ("negative" if sentiment <= 2 else "neutral"),
                "topic_tags": ";".join(topics),
                "entity_product": None,
                "crisis_flag": False,
                "crisis_reason": None,
                "summary": text[:80] + "...",
                "actionable_insight": None,
            })

        # TikTok: ~10 mentions per brand
        for text, sentiment, topics in TIKTOK_TEMPLATES[brand_key]:
            ts = base_time + timedelta(days=random.uniform(0, 6), hours=random.uniform(0, 23))
            rows.append({
                "mention_id": f"tt_{len(rows):04d}",
                "timestamp": ts.isoformat(),
                "source": "tiktok",
                "source_url": f"https://tiktok.com/@user/video/{len(rows)}",
                "language": "en",
                "raw_text": text,
                "brand_key": brand_key,
                "author_handle": f"@tiktoker_{random.randint(100, 9999)}",
                "engagement_likes": random.randint(1000, 500000),
                "engagement_comments": random.randint(20, 5000),
                "country_guess": random.choice(["US", "UK", "DE"]),
                "sentiment_score": sentiment,
                "sentiment_label": "positive" if sentiment >= 4 else ("negative" if sentiment <= 2 else "neutral"),
                "topic_tags": ";".join(topics),
                "entity_product": None,
                "crisis_flag": False,
                "crisis_reason": None,
                "summary": text[:80] + "...",
                "actionable_insight": None,
            })

        # News: ~3 mentions per brand
        for text, sentiment, topics in NEWS_TEMPLATES[brand_key]:
            ts = base_time + timedelta(days=random.uniform(0, 6), hours=random.uniform(0, 23))
            rows.append({
                "mention_id": f"nw_{len(rows):04d}",
                "timestamp": ts.isoformat(),
                "source": "news",
                "source_url": f"https://news.example.com/article/{len(rows)}",
                "language": "en",
                "raw_text": text,
                "brand_key": brand_key,
                "author_handle": random.choice(["Vogue Business", "WWD", "Glossy", "Allure", "BoF"]),
                "engagement_likes": 0,
                "engagement_comments": random.randint(0, 50),
                "country_guess": random.choice(["US", "UK", "DE"]),
                "sentiment_score": sentiment,
                "sentiment_label": "positive" if sentiment >= 4 else ("negative" if sentiment <= 2 else "neutral"),
                "topic_tags": ";".join(topics),
                "entity_product": None,
                "crisis_flag": False,
                "crisis_reason": None,
                "summary": text[:80] + "...",
                "actionable_insight": None,
            })

    # Add 1 crisis mention per brand (sparse but real)
    for brand_key, crisis in zip(brand_keys, CRISIS_TEMPLATES):
        text, sentiment, topics, crisis_flag, reason = crisis
        ts = base_time + timedelta(days=random.uniform(1, 5), hours=random.uniform(0, 23))
        rows.append({
            "mention_id": f"cr_{len(rows):04d}",
            "timestamp": ts.isoformat(),
            "source": random.choice(["reddit", "instagram", "news"]),
            "source_url": f"https://example.com/post/{len(rows)}",
            "language": "en",
            "raw_text": text,
            "brand_key": brand_key,
            "author_handle": f"@urgent_{random.randint(100, 999)}",
            "engagement_likes": random.randint(500, 50000),
            "engagement_comments": random.randint(50, 2000),
            "country_guess": "US",
            "sentiment_score": sentiment,
            "sentiment_label": "negative",
            "topic_tags": ";".join(topics),
            "entity_product": None,
            "crisis_flag": crisis_flag,
            "crisis_reason": reason,
            "summary": text[:80] + "...",
            "actionable_insight": None,
        })

    return rows


def main():
    rows = generate_mentions()
    output_path = Path("./data/sample_mentions.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "mention_id", "timestamp", "source", "source_url", "language",
        "raw_text", "brand_key", "author_handle", "engagement_likes",
        "engagement_comments", "country_guess", "sentiment_score",
        "sentiment_label", "topic_tags", "entity_product", "crisis_flag",
        "crisis_reason", "summary", "actionable_insight",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} sample mentions → {output_path}")
    print(f"Brands: {set(r['brand_key'] for r in rows)}")
    print(f"Sources: {set(r['source'] for r in rows)}")
    print(f"Crisis flags: {sum(1 for r in rows if r['crisis_flag'])}")


if __name__ == "__main__":
    main()
