"""
LLM Prompt Templates for Brand Health Tracker
==============================================

Centralized prompts used by the analyzer. Each prompt is engineered for
structured JSON output that matches the enriched_mentions schema.
"""


# Master extraction prompt - given a raw mention, extract structured insights
EXTRACTION_PROMPT = """You are a senior brand insights analyst working for a beauty/skincare consultancy. Your job is to analyze a single social media mention and extract structured insights.

You will be given:
- The brand being monitored
- The raw text of the mention
- The platform (Reddit, Instagram, TikTok, News)
- The language

Return a JSON object with EXACTLY these fields (no extra prose):

{{
  "sentiment_score": <integer 1-5, where 1=very negative, 3=neutral, 5=very positive>,
  "sentiment_label": "<one of: positive | negative | neutral | mixed>",
  "topic_tags": [<list of relevant topics from the taxonomy below>],
  "entity_product": "<specific product name mentioned, or null if none>",
  "brand_target": "<the brand actually being discussed: {brand_options} | other>",
  "language": "<ISO 639-1 code: en | de | it | fr | es>",
  "crisis_flag": <true | false>,
  "crisis_reason": "<short reason if crisis_flag is true, else null>",
  "summary": "<one-sentence summary in English of what this mention is about>",
  "actionable_insight": "<one concrete thing the brand team could learn or act on from this mention, in English>"
}}

Topic taxonomy (use only these tags):
{topic_taxonomy}

Brand options: {brand_options}

Important guidelines:
- Be conservative with sentiment: marketing copy or generic praise without specifics = neutral (3), not positive (5).
- crisis_flag is true ONLY if the mention references one of: {crisis_signals}.
- If the mention is in a non-English language, translate the essence into English for the summary and actionable_insight.
- entity_product: capture the specific SKU or product line if named (e.g. "The Cream", "Niacinamide 10% + Zinc 1%", "Boy Brow"); use null if only the brand is mentioned.
- topic_tags: pick 1-3 most relevant topics. Do not invent new tags.

Mention to analyze:
---
Platform: {platform}
Language hint: {language_hint}
Brand being monitored: {brand_target_label}
Raw text: {raw_text}
---

Return ONLY the JSON object, no markdown fences, no preamble."""


# Crisis detection prompt - applied to batches to detect emerging patterns
BATCH_CRISIS_PROMPT = """You are reviewing a batch of {batch_size} recent brand mentions for {brand_target_label}.

Look across all mentions for emerging patterns that suggest a brand crisis in progress:
- Sudden cluster of safety/irritation complaints
- Viral negative ingredient claim gaining traction
- Recall or regulatory action
- High-profile cancellation or boycott
- Supply chain collapse (widespread stockouts)
- Founder/exec scandal breaking news

Batch of mentions (JSON array):
{mentions_json}

Return JSON:
{{
  "crisis_detected": <true | false>,
  "crisis_type": "<short label if detected, else null>",
  "evidence_summary": "<2-3 sentences explaining the evidence if detected, else null>",
  "recommended_action": "<specific actionable recommendation if detected, else null>",
  "severity": "<low | medium | high | critical if detected, else null>"
}}

Return ONLY the JSON, no markdown fences."""


# Executive summary prompt - weekly rollup of all enriched data
EXECUTIVE_SUMMARY_PROMPT = """You are preparing the executive summary section of a weekly Brand Health Tracker report.

Brand being reported: {brand_target_label}
Date range: {date_range}
Compared against: {comparison_brand_options}

Aggregated data this week:
- Total mentions: {total_mentions}
- Average sentiment: {avg_sentiment} (1-5 scale)
- Top topics: {top_topics}
- Top products mentioned: {top_products}
- Crisis flags: {crisis_count}
- Volume change vs last week: {volume_change_pct}%

Write a concise executive summary (max 120 words, in English) that:
1. Opens with the week's headline finding
2. Highlights 2-3 specific insights backed by the numbers above
3. Closes with the recommended priority for next week

Style: confident, specific, suitable for a Brand Director or CMO. No fluff. Numbers when possible. No generic platitudes."""


def build_extraction_prompt(
    raw_text: str,
    platform: str,
    brand_target_key: str,
    brand_target_label: str,
    brand_options: list,
    topic_taxonomy: list,
    crisis_signals: list,
    language_hint: str = "unknown",
) -> str:
    return EXTRACTION_PROMPT.format(
        raw_text=raw_text,
        platform=platform,
        language_hint=language_hint,
        brand_target_label=brand_target_label,
        brand_options=", ".join(brand_options),
        topic_taxonomy=", ".join(topic_taxonomy),
        crisis_signals=", ".join(crisis_signals),
    )


def build_crisis_prompt(mentions: list, brand_target_label: str, batch_size: int) -> str:
    import json
    return BATCH_CRISIS_PROMPT.format(
        batch_size=batch_size,
        brand_target_label=brand_target_label,
        mentions_json=json.dumps(mentions, indent=2)[:8000],  # Truncate to avoid token overflow
    )


def build_executive_summary_prompt(
    brand_target_label: str,
    date_range: str,
    comparison_brand_options: list,
    total_mentions: int,
    avg_sentiment: float,
    top_topics: list,
    top_products: list,
    crisis_count: int,
    volume_change_pct: float,
) -> str:
    return EXECUTIVE_SUMMARY_PROMPT.format(
        brand_target_label=brand_target_label,
        date_range=date_range,
        comparison_brand_options=", ".join(comparison_brand_options) or "N/A",
        total_mentions=total_mentions,
        avg_sentiment=round(avg_sentiment, 2),
        top_topics=", ".join(top_topics[:5]) or "N/A",
        top_products=", ".join(top_products[:5]) or "N/A",
        crisis_count=crisis_count,
        volume_change_pct=round(volume_change_pct, 1),
    )
