# How I Built an AI Brand Tracker That Runs Itself for $3/month

*A senior marketing consultant's case study in shipping AI-augmented operations, not just talking about them*

---

I spent the last decade building brand tracking reports for Mercedes-Benz, BMW, and L'Oréal. Every week, the same ritual: collect mentions from five platforms, tag them by hand, group them by topic, write a narrative, ship a PDF. A team of two, 15 hours per brand.

Earlier this year, after a corporate restructuring left me unemployed for the second time, I decided to build the version I always wanted: a brand tracker that runs itself. Not a hackathon demo. A real, scheduled, cost-efficient system that produces the same reports I used to build manually.

This is the story of how I built it — and what it taught me about AI-augmented marketing work.

---

## The setup

The premise was simple: **monitor three beauty brands — Augustinus Bader, The Ordinary, and Glossier — and produce weekly executive briefings without human effort.**

The constraints were tighter:

- **Cost under €5/month** (I needed to demonstrate efficiency, not vanity)
- **Reproducible by anyone** (no proprietary APIs, no custom ML models)
- **Production-ready** (runs on a schedule, not on-demand)
- **Portfolio-grade output** (something I could show a hiring manager with pride)

Three brands, not one, because comparison is where brand tracking gets interesting. When you see The Ordinary trending on TikTok with a sentiment of 4.8 and Augustinus Bader sitting at 3.2, the conversation changes from "is the brand okay?" to "where is the market going?"

---

## The stack

I chose tools I could defend in any interview:

**Apify** for scraping. Custom scrapers break weekly as platforms tighten anti-bot measures. Apify maintains community-vetted actors with rotation, rate limiting, and auth handled. $0.30 per run across four platforms.

**Claude Sonnet 4** for analysis. For brand understanding, Claude beats naive sentiment libraries because it can distinguish marketing copy from genuine opinion. It also handles sarcasm reasonably well, which matters when 40% of TikTok comments are ironic.

**GitHub Actions** for orchestration. Free for public repos, no separate auth setup, and visible to anyone who clicks the Actions tab. The visibility matters for a portfolio piece — recruiters can see the cron is real.

**ReportLab** for PDF. No browser dependencies, no CSS magic. Pure Python that produces ~50KB PDFs vs. ~500KB for browser-rendered HTML.

**Looker Studio** for dashboards. Free, stakeholder-friendly (marketing teams already know it), and shares publicly with one click.

The total monthly cost: €2.80.

---

## What surprised me

### The bottleneck was never analysis

When I built brand reports manually at TLGG and Reply, the slow part wasn't the thinking. It was collecting mentions across five platforms, copying them into a spreadsheet, deduplicating, and getting them into a format the team could work with.

LLMs don't accelerate analysis by 10x — they accelerate it by maybe 2x. But they eliminate the collection and synthesis work entirely. **The pipeline went from 15 hours of human effort to 12 minutes of compute.**

That's not AI-augmented work. That's AI-replaced work, with the human moving to judgment.

### Sentiment scoring is harder than it looks

My first prompt just asked for "positive, negative, or neutral." The model labeled almost everything positive because most mentions contain some positive content ("the packaging is nice BUT the price is too high"). 

The fix was three things:
1. **Anchor to a 1-5 scale** instead of a 3-class label
2. **Distinguish marketing/promo copy from genuine opinion** explicitly in the prompt
3. **Require specific evidence** (a topic tag) to back the score

After the change, the model's accuracy on a sample I manually labeled went from 62% to 89%. Still imperfect, but usable.

### Crisis detection is the highest-value feature

I almost skipped it. Then I remembered the time a client called on a Sunday morning because a Reddit thread about their sunscreen was trending toward "this gave me a chemical burn." The reaction cost them 4% market share over six weeks.

The crisis detection layer does this automatically: it sorts mentions by `crisis_flag = true` first, then by recency, then asks Claude to look across the batch and answer: "Is there an emerging crisis? What type? What's the evidence?"

A red alert box appears at the top of the PDF if one is found. For hiring managers, this is the part that sells the project — it's not a sentiment dashboard, it's an operational tool.

### I had to write three different prompts, not one

The temptation was a single mega-prompt: "analyze this batch of mentions and give me everything." That's how you get hallucinated JSON fields and inconsistent outputs.

Instead I separated the work:
- **One prompt per mention** for structured extraction (sentiment, topics, entities)
- **One prompt per batch** for crisis pattern detection
- **One prompt per brand per week** for executive summary generation

Each prompt is short, focused, and easy to debug. Total prompt engineering time: about 4 hours. That's where the work is, not in the code.

---

## What I'd do differently

A few things I'd change if I were rebuilding this:

**Stream the alerts instead of batching weekly.** If the goal is operational response, daily — or even hourly — is better. The architecture supports it; I just didn't prioritize it for v1.

**Build a real evaluation set.** Right now I'm testing on my own subjective read of what "good" looks like. For a production system, I'd label 500 mentions manually and benchmark the prompt changes against that.

**Add a "what changed this week" diff view.** Right now the report shows absolute numbers. The interesting question is: what's different from last week? That's a feature for v2.

**Integrate with the brand team's existing tools.** Slack alerts for crises, Notion sync for the report, Linear tickets for follow-up actions. The hardest part of AI-augmented work isn't the AI — it's the integration into how teams actually operate.

---

## Why this matters for the job search

Here's what I want a hiring manager to think when they see this project:

> *"She's been on the inside of brand tracking at Mercedes, BMW, and L'Oréal. She knows what good looks like. And instead of just talking about AI, she built a working system that produces the same output her previous teams did manually, at 1/1000th the cost."*

That's the pitch. Not "I know AI tools" — every marketing candidate says that now. **"I've shipped an AI-augmented workflow that demonstrates exactly the work your team needs done, faster and cheaper than your current process."**

The job market for marketing in 2025 is brutal. The candidates winning aren't the ones with the longest resumes. They're the ones who can show they understand both the strategic context *and* the operational reality of AI-augmented work.

This project is my way of showing both.

---

## Try it yourself

The full code is open source: **[github.com/irenemagnihello/brand-health-tracker](https://github.com/irenemagnihello/brand-health-tracker)**

It runs in demo mode with bundled sample data, or in live mode with real scraping and Claude analysis. Setup takes about 30 minutes. Cost is €2.80/month if you run it weekly.

If you build something with it, or have questions about how to adapt it to your own brand tracking workflow, find me on LinkedIn — I'm always up for a conversation about AI-augmented marketing operations.

---

*Irene Magni is a senior marketing and data consultant based in Berlin. Previously: Zalando Marketing Services, TLGG (Mercedes-Benz), TD Reply (BMW), Houzz. Currently open to senior brand, marketing, or insights roles in DACH and remote-friendly European markets.*
