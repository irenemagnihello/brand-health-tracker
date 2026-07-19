# Architecture Deep Dive: Brand Health Tracker

This document explains the technical decisions, trade-offs, and operational considerations behind the Brand Health Tracker. Intended for technical interviewers and engineers who want to understand *why* things are built the way they are.

---

## System overview

The system runs as a weekly batch job orchestrated by GitHub Actions. Each run has four phases:

```
Phase 1: SCRAPE        Phase 2: ENRICH        Phase 3: ANALYZE      Phase 4: DELIVER
Apify actors          Claude API              Crisis detection       PDF + Dashboard
Multi-platform        Per-mention extraction  Batch-level pattern    Outputs published
~5-10 minutes         ~3-5 minutes            ~30 seconds            ~1 minute
```

Total runtime: ~15 minutes for 3 brands at ~50 mentions each.

---

## Phase 1: Scraping (Apify)

### Why Apify over custom scrapers?

Custom Instagram/TikTok scrapers break weekly as platforms update their anti-scraping measures. Apify maintains a catalog of community-vetted actors that handle authentication, rotation, and rate limiting. For a portfolio project, paying $0.30/run is cheaper than engineering a robust custom solution.

### Actors used

| Platform | Actor | Cost/run |
|---|---|---|
| Instagram | `apify/instagram-hashtag-scraper` | ~$0.05 |
| TikTok | `apify/tiktok-hashtag-scraper` | ~$0.05 |
| Reddit | `apify/reddit-search-scraper` | ~$0.10 |
| News | `apify/google-news-scraper` | ~$0.10 |

Each actor runs with a small `resultsLimit` (20-50) to stay within the free tier while providing enough signal.

### Output schema

Raw mentions are normalized to a common schema before analysis:

```python
{
    "mention_id": str,         # unique identifier
    "timestamp": str,          # ISO 8601
    "source": str,             # "instagram" | "tiktok" | "reddit" | "news"
    "source_url": str,         # link back to original post
    "language": str,           # ISO 639-1
    "raw_text": str,           # caption / title+body / article snippet
    "author_handle": str,
    "engagement_likes": int,
    "engagement_comments": int,
    "country_guess": str,      # best-effort inference
    "brand_key": str           # added after scraping
}
```

This normalization lets the analyzer and report generator work source-agnostically.

---

## Phase 2: Enrichment (Claude)

### Why Claude over GPT for this?

For brand analysis, Claude Sonnet 4 has a few advantages:

- **Better instruction following** for structured JSON output
- **Larger context window** (200k tokens) for batch-level analysis
- **More nuanced sentiment scoring** — distinguishes marketing copy from genuine opinion
- **Less likely to refuse** ambiguous brand critique content

For this portfolio piece, the choice is largely interchangeable, but the prompt engineering is tuned to Claude's style of JSON responses.

### Prompt design

Three distinct prompts:

**Per-mention extraction** (`analyzer/prompts.py:EXTRACTION_PROMPT`):
- Single mention → structured JSON with 11 fields
- Includes explicit topic taxonomy to constrain output
- Asks for both `summary` and `actionable_insight` to force operational thinking

**Batch crisis detection** (`analyzer/prompts.py:BATCH_CRISIS_PROMPT`):
- 30 mentions at a time → crisis verdict
- Asks for evidence and recommended action, not just label
- Critical for catching patterns that single-mention analysis misses

**Executive summary** (`analyzer/prompts.py:EXECUTIVE_SUMMARY_PROMPT`):
- Aggregated metrics → 100-120 word CMO-style summary
- Explicit style guidance: "specific, no fluff, numbers when possible"

### Cost control

- **Batch size**: 20 mentions per call (tuned to balance latency vs. cost)
- **Max tokens**: 1024 per response (enough for the JSON, prevents runaway)
- **Temperature**: 0.1 for analysis (consistency), 0.4 for summary (some variation)
- **Retries**: 3 attempts with exponential backoff

---

## Phase 3: Crisis Detection

This is the most operationally important phase. Single-mention sentiment can be misleading (one bad review ≠ crisis), but pattern detection across batches catches emerging issues.

The approach:

1. Sort mentions by `crisis_flag = true` first, then by recency
2. Take top 30 mentions as input
3. Ask Claude: "Is there a crisis emerging? What type? What's the evidence?"
4. If `crisis_detected = true`, the report gets a red alert box

This was directly inspired by the brand crisis playbooks I used at TLGG (Mercedes-Benz social listening) — except now it runs in 30 seconds instead of requiring a team meeting.

---

## Phase 4: Delivery

### PDF report

Built with **ReportLab**, not WeasyPrint or browser-based renderers. Why?

- Pure Python, no system dependencies (no Chromium needed)
- Reproducible across environments
- Tables and styling are explicit code, not CSS magic
- Output is ~50KB per PDF (vs. ~500KB for browser-rendered HTML)

The report layout is intentionally minimal:
- Page 1: Executive summary + metrics + crisis alert + topics
- Page 2: 6 highest-engagement mentions with full context

This matches how senior marketing leaders actually consume reports: skimmable first, deep-dive on demand.

### Looker Studio dashboard

Chosen over Tableau, PowerBI, or custom dashboards because:

- **Free** (no per-user licensing)
- **Real-time connection** to Google Sheets / BigQuery
- **Stakeholder-friendly**: marketing teams already know it
- **Public sharing** by default (good for portfolio link)

Build guide: `dashboard/looker_studio_guide.md`

---

## Data flow & storage

### Demo mode
```
sample_mentions.csv → orchestrator → report_generator → output/*.pdf
```

### Live mode
```
Apify → raw CSV (data/raw/) → Claude → enriched CSV (data/enriched/) → 
       → report_generator → output/*.pdf
       → Looker Studio (via Google Sheets or BigQuery)
```

### Storage choice rationale

For a portfolio piece, **CSV + Google Sheets** is the right choice:

- No database to provision or maintain
- Easy to inspect during interviews
- Looker Studio connects natively
- Git tracks history (good for showing iteration)

If this were going into production at scale, I'd migrate to **BigQuery** with dbt models — but that's a different project.

---

## Orchestration: GitHub Actions

### Why not AWS Lambda, GCP Cloud Functions, Vercel Cron?

- **GitHub Actions is free** for public repos (2,000 minutes/month)
- **No separate IAM/auth setup** — secrets live in repo settings
- **Native git integration** — pipeline can commit updated data back
- **Visible to anyone** — recruiters can see the cron is real and runs

The trade-off is cold start latency (~30 seconds) and a 30-minute timeout, but neither matters for a weekly batch job.

### Schedule choice: Monday 8am UTC

- Weekend social activity captured (peak engagement for beauty content)
- Team has the report when they start the week
- 8am UTC = 9am Berlin, 10am Dubai, midnight Pacific (acceptable trade-off)

---

## Trade-offs & future work

### What I'd add for production

| Component | Current | Production |
|---|---|---|
| Scraping | Apify actors | Custom scrapers + rotating proxies |
| Storage | CSV + Google Sheets | BigQuery with dbt models |
| LLM | Direct Claude API | LiteLLM with model fallback |
| Cost tracking | Manual | OpenLLMetry + Datadog |
| Crisis alerts | Weekly batch | Streaming via webhook |
| Languages | EN mostly | Multi-lingual full pipeline |

### Known limitations

- **TikTok engagement metrics** are noisy — flagged comments can skew numbers
- **Crisis detection** needs tuning per brand — current thresholds are generic
- **Multi-market comparison** is currently sequential; parallel processing would cut runtime by 3x
- **Sarcasm detection** is approximate — Claude gets ~85% right, humans ~95%

### What I'd never change

- **Apify for scraping** — the maintenance cost of custom scrapers isn't worth it for this scale
- **PDF + dashboard dual output** — different stakeholders want different formats
- **GitHub Actions for orchestration** — free, visible, simple

---

## Interview talking points

When walking through this with a hiring manager, the key technical stories are:

1. **Scraper resilience** — how I handle rate limits, partial failures, schema drift
2. **Prompt engineering** — why three separate prompts instead of one mega-prompt
3. **Crisis detection** — the pattern recognition approach vs. simple sentiment alerts
4. **Cost discipline** — $2.80/month to run, demonstrated in code
5. **Operational concerns** — secrets, scheduling, monitoring, failure modes

The code is structured so each of these is easy to point at during a screen share.
