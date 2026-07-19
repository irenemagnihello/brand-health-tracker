# Brand Health Tracker

> An AI-powered brand monitoring system that turns social media noise into weekly executive briefings for beauty brands.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Live Demo](https://img.shields.io/badge/demo-online-green.svg)](https://irenemagnihello.github.io/brand-health-tracker/)

**Built by [Irene Magni](https://www.linkedin.com/in/irenemagni)** · Senior Marketing & Data Consultant · Berlin

---

## What this does

Automatically monitors brand perception across Instagram, TikTok, Reddit, and news. Every week, it:

1. **Scrapes** mentions for 3 beauty brands (Augustinus Bader, The Ordinary, Glossier)
2. **Analyzes** each mention with Claude AI: sentiment, topics, entities, crisis signals
3. **Detects** emerging crises via batch pattern recognition
4. **Generates** a 2-page executive PDF report per brand
5. **Updates** a live Looker Studio dashboard

**Time to insight**: 12 minutes (vs. 8-15 hours manually).
**Cost to run**: ~$0.50 per full run across 3 brands.
**Human effort**: zero after initial setup.

---

## Why this exists

As a senior consultant who led brand tracking for Mercedes-Benz, BMW, and L'Oréal, I spent years building these reports by hand. The workflow was always the same: collect mentions, tag sentiment, group themes, write a narrative, ship a PDF. The bottleneck was never analysis — it was collection and synthesis.

This project shows how 2025's AI stack collapses that workflow:

- **Apify** for reliable, affordable social scraping (no brittle custom scrapers)
- **Claude Sonnet 4** for nuanced brand understanding (better than naive sentiment libraries)
- **GitHub Actions** for free, scheduled orchestration
- **Looker Studio** for stakeholder-facing dashboards (no UI work)
- **ReportLab** for executive PDF output

The result: a portfolio piece that demonstrates I can ship AI-augmented analytics, not just talk about them.

---

## Architecture

```
Apify Schedules (Instagram, TikTok, Reddit, News)
            ↓
      Raw JSON → CSV
            ↓
Python Orchestrator (GitHub Actions cron)
            ↓
Claude API: sentiment + topics + entities + crisis
            ↓
   Enriched CSV → Google Sheets / BigQuery
            ↓              ↓              ↓
Looker Studio   Weekly PDF    Slack/Email
 (live dashboard)  (executive)   (crisis alerts)
```

Full architecture deep-dive: [docs/architecture.md](docs/architecture.md)

---

## Quick start

### Demo mode (no API keys needed — uses bundled sample data)

```bash
git clone https://github.com/irenemagnihello/brand-health-tracker.git
cd brand-health-tracker
pip install -r requirements.txt
python -m orchestrator.main --demo
```

Three PDF reports will land in `./output/`.

### Live mode (real scraping + AI analysis)

1. **Get API keys** (free tiers available):
   - Apify: https://console.apify.com/sign-up (gives $5/month free)
   - Anthropic: https://console.anthropic.com/ (pay-as-you-go, $5 minimum)

2. **Configure**:
   ```bash
   cp .env.example .env
   # Edit .env with your APIFY_TOKEN and ANTHROPIC_API_KEY
   ```

3. **Run**:
   ```bash
   python -m orchestrator.main
   ```

4. **Build the dashboard**: follow [dashboard/looker_studio_guide.md](dashboard/looker_studio_guide.md) (~30 min)

---

## Project structure

```
brand-health-tracker/
├── scrapers/
│   ├── apify_scraper.py       # Multi-platform scraping via Apify
│   └── config.yaml            # Brand keywords, subreddits, hashtags
├── analyzer/
│   ├── llm_analyzer.py        # Claude-powered enrichment
│   └── prompts.py             # Structured prompt templates
├── orchestrator/
│   └── main.py                # Pipeline coordinator (CLI + demo mode)
├── report_generator/
│   ├── pdf_generator.py       # 2-page executive PDF builder
│   └── template.html          # HTML template for web reports
├── dashboard/
│   └── looker_studio_guide.md # Step-by-step dashboard build guide
├── data/
│   └── sample_mentions.csv    # ~100 demo mentions across 3 brands
├── scripts/
│   └── generate_sample_data.py
├── .github/workflows/
│   └── brand_tracker.yml      # Weekly GitHub Actions cron
├── portfolio/                 # Portfolio site (this README's web twin)
├── docs/
│   ├── architecture.md        # Technical deep dive
│   └── medium_article.md      # The companion Medium piece
├── output/                    # Generated PDFs land here
├── requirements.txt
├── .env.example
└── README.md
```

---

## What it produces

### 1. Weekly PDF report (2 pages per brand)

Sample output: `./output/augustinus_bader_report_*.pdf`

Page 1: Executive summary + key metrics + crisis alerts + topic breakdown
Page 2: Trending mentions (highest engagement first), with full text and insights

### 2. Live Looker Studio dashboard

Five visualizations:
- Sentiment over time (line chart, by brand)
- Sentiment distribution (donut chart)
- Top topics (horizontal bar)
- Mention volume by platform (stacked bar)
- Crisis alerts table

[Build instructions →](dashboard/looker_studio_guide.md)

### 3. Enriched CSV

One row per mention, with: sentiment score (1-5), sentiment label, topics, entities, language, crisis flag, summary, actionable insight.

---

## Cost breakdown

| Component | Cost per run | Frequency | Monthly |
|---|---|---|---|
| Apify scraping | ~$0.30 | Weekly | ~$1.20 |
| Claude API (analysis) | ~$0.40 | Weekly | ~$1.60 |
| Looker Studio | Free | — | Free |
| GitHub Actions | Free (under 2000 min) | Weekly | Free |
| **Total** | **~$0.70** | **Weekly** | **~$2.80** |

A junior analyst doing this work costs ~$1,500/month. ROI: 500x.

---

## The case study story

This project lives at the intersection of three trends hiring managers care about in 2025:

1. **AI-augmented marketing operations** — every brand team is rebuilding around LLM workflows
2. **Senior generalists with technical range** — leaders who can ship, not just strategize
3. **Beauty & lifestyle sector growth** — €500B+ globally, hiring aggressively in Berlin and DACH

When I send this to a Brand Director or CMO, the message is: *I don't just understand brand tracking — I've rebuilt it for the AI era.*

---

## Methodology note (honest disclosure)

The bundled sample data in `data/sample_mentions.csv` is **synthetic**, created by `scripts/generate_sample_data.py`. It is designed to:

- Reflect realistic distribution of sentiment, topics, and engagement patterns
- Include one crisis scenario per brand (so the alert system can be demonstrated)
- Span 7 days for trend visualization

When you run `--demo` mode, the pipeline reads this sample data and generates reports without making API calls. When you run without `--demo`, the pipeline scrapes real mentions and calls Claude for analysis.

This dual-mode approach lets the portfolio piece work for hiring managers who just want to see the output, and for technical interviewers who want to inspect the code path end-to-end.

---

## License

MIT — see [LICENSE](LICENSE).

---

## Contact

**Irene Magni** · Berlin · irene.magni1@gmail.com · [LinkedIn](https://www.linkedin.com/in/irenemagni)

Other projects & writing: [portfolio site](https://irenemagnihello.github.io/brand-health-tracker/) · [Medium](https://medium.com/@irenemagni)
