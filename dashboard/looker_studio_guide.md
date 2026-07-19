# Looker Studio Dashboard Guide

This guide walks you through building a live, public dashboard for the Brand Health Tracker in ~30 minutes. The dashboard connects to your enriched mentions CSV (or Google Sheet) and renders 5 visualizations that update automatically.

---

## Step 0 — Prerequisites

- A Google account
- The enriched CSV file at `./data/sample_mentions.csv` (already in this repo for demo)
- For live data: a Google Sheet with the same column structure (see schema below)

---

## Step 1 — Create the Looker Studio report

1. Go to https://lookerstudio.google.com
2. Click **"Blank Report"** → choose **"Create new data source"**
3. Pick **"Upload a CSV"** (for demo) or **"Google Sheets"** (for live)
4. Upload `./data/sample_mentions.csv` from this repo
5. Click **"Connect"** → **"Create Report"**

You now have an empty canvas.

---

## Step 2 — Build the 5 core visualizations

### 📊 Chart 1: Sentiment Over Time (Score Trend Line)

- **Chart type**: Time series
- **Dimension**: `timestamp` (Date)
- **Metric**: Average of `sentiment_score`
- **Breakdown**: `brand_target`
- **Date range**: Last 14 days
- **Style**: Solid lines, distinct colors per brand (Augustinus Bader = black, The Ordinary = blue, Glossier = pink)
- **Title**: "Sentiment Score Trend — All Brands"

### 🥧 Chart 2: Sentiment Distribution (Donut Chart)

- **Chart type**: Pie chart (donut)
- **Dimension**: `sentiment_label`
- **Metric**: Record count
- **Filter**: `brand_target = [selected brand]`
- **Title**: "Sentiment Distribution — [Brand]"
- **Color hint**: green for positive, gray for neutral, red for negative

### ☁️ Chart 3: Top Topics (Horizontal Bar)

- **Chart type**: Horizontal bar chart
- **Dimension**: `topic_tags` (you may need to flatten this in Sheets first, see Step 3)
- **Metric**: Record count
- **Sort**: By metric descending, top 10
- **Filter**: `brand_target = [selected brand]`
- **Title**: "Top Topics Discussed — [Brand]"

### 📈 Chart 4: Volume by Source (Stacked Bar)

- **Chart type**: Stacked bar chart
- **Dimension**: `source`
- **Metric**: Record count
- **Breakdown**: `brand_target`
- **Title**: "Mention Volume by Platform"

### 🚨 Chart 5: Crisis Alerts Table

- **Chart type**: Table
- **Dimension columns**: `brand_target`, `source`, `timestamp`, `crisis_reason`
- **Filter**: `crisis_flag = true`
- **Sort**: `timestamp` descending
- **Title**: "Crisis Alerts (Action Required)"
- **Style**: Red header background, conditional formatting on `crisis_flag`

---

## Step 3 — (Optional) Flatten the `topic_tags` column for Looker Studio

Looker Studio doesn't natively parse semicolon-separated values. To enable topic-based filtering in Chart 3:

1. In your Google Sheet, add a new sheet called `topics_long`
2. Use this formula in cell A1:

```
=ARRAYFORMULA(IFERROR(SPLIT(flatten_data!A:A, ";")))
```

3. Or use the helper Python script:

```bash
python scripts/flatten_topics.py
```

This creates one row per (mention, topic) pair, which Looker Studio can aggregate cleanly.

---

## Step 4 — Add a date range control

- **Insert** → **Date range control**
- Place it at the top of the dashboard
- Default range: Last 7 days
- This lets viewers filter everything by date

---

## Step 5 — Add a brand filter

- **Insert** → **Drop-down list**
- Control field: `brand_target`
- Place it next to the date range
- This lets viewers isolate one brand's data

---

## Step 6 — Style the dashboard

- **Theme**: "Simple Light" or "Axiom" for clean look
- **Page background**: `#fafafa` (light gray)
- **Title font**: Roboto, 24px, bold
- **Brand colors** (use throughout):
  - Augustinus Bader: `#1a1a1a`
  - The Ordinary: `#4a90e2`
  - Glossier: `#e91e63`
  - Accent: `#d4a574` (gold)

---

## Step 7 — Publish and share

1. Click **"Share"** → **"Get report link"**
2. Under "Who can view this report", select **"Anyone with the link"**
3. Copy the public URL
4. Add it to your portfolio site and README as the live dashboard link

---

## Going live with real data

When you switch from sample data to live data:

1. **Option A (simpler)**: Keep uploading the latest CSV weekly. Looker Studio will pick it up automatically if you overwrite the same file ID.
2. **Option B (better)**: Set up Google Sheets as the data source. Each pipeline run writes enriched data to the sheet, Looker Studio auto-refreshes.
3. **Option C (best)**: Use BigQuery. Load `enriched_mentions.csv` to a BigQuery table on each run, point Looker Studio there. This gives you SQL-level control over aggregations.

The `orchestrator/main.py` includes optional Google Sheets integration via `gspread` — see commented-out sections in `analyzer/llm_analyzer.py` for how to wire it up.

---

## Sample dashboard URL

A reference dashboard built from the sample data in this repo:
> *(Add your published URL here once built)*

---

**Total time to build**: 30 minutes
**Total time to maintain**: 5 minutes/week (auto-refresh handles it)
