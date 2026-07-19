"""
Weekly Report PDF Generator
=============================

Produces a 2-page executive-style PDF report per brand, suitable for
sending to a CMO or Brand Director. Uses ReportLab for layout.

Output: ./output/{brand_key}_{YYYYMMDD}.pdf
"""

from datetime import datetime
from pathlib import Path
from typing import Dict

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    KeepTogether
)


class WeeklyReportGenerator:
    """Renders a weekly brand health report as a 2-page PDF."""

    BRAND_COLORS = {
        "augustinus_bader": colors.HexColor("#1a1a1a"),
        "the_ordinary":     colors.HexColor("#4a90e2"),
        "glossier":         colors.HexColor("#e91e63"),
    }
    ACCENT = colors.HexColor("#d4a574")  # Warm gold accent

    def __init__(self, output_dir: str = "./output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.styles = self._build_styles()

    def _build_styles(self):
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontSize=24,
            textColor=colors.HexColor("#1a1a1a"),
            spaceAfter=8,
        ))
        styles.add(ParagraphStyle(
            name="ReportSubtitle",
            parent=styles["Normal"],
            fontSize=11,
            textColor=colors.HexColor("#666666"),
            spaceAfter=18,
        ))
        styles.add(ParagraphStyle(
            name="SectionHeader",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=colors.HexColor("#1a1a1a"),
            spaceBefore=14,
            spaceAfter=8,
        ))
        styles.add(ParagraphStyle(
            name="Body",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            spaceAfter=8,
        ))
        styles.add(ParagraphStyle(
            name="MentionText",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#333333"),
            spaceAfter=4,
        ))
        styles.add(ParagraphStyle(
            name="CrisisAlert",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#c0392b"),
            backColor=colors.HexColor("#fadbd8"),
            borderPadding=8,
            spaceAfter=10,
        ))
        return styles

    def generate(
        self,
        enriched_df: pd.DataFrame,
        brand_key: str,
        executive_summary: str,
        crisis_info: Dict,
        date_range: str = None,
    ) -> str:
        """Render the PDF and return the file path."""
        if date_range is None:
            today = datetime.now()
            week_ago = today - pd.Timedelta(days=7)
            date_range = f"{week_ago.strftime('%Y-%m-%d')} → {today.strftime('%Y-%m-%d')}"

        brand_label = brand_key.replace("_", " ").title()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        output_path = self.output_dir / f"{brand_key}_report_{timestamp}.pdf"

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            topMargin=0.6 * inch,
            bottomMargin=0.6 * inch,
            leftMargin=0.7 * inch,
            rightMargin=0.7 * inch,
        )

        story = []

        # --- HEADER ---
        story.append(Paragraph(f"Brand Health Tracker", self.styles["ReportTitle"]))
        story.append(Paragraph(
            f"{brand_label} &nbsp;|&nbsp; {date_range} &nbsp;|&nbsp; Generated {datetime.now():%Y-%m-%d %H:%M}",
            self.styles["ReportSubtitle"]
        ))

        # --- EXECUTIVE SUMMARY ---
        story.append(Paragraph("Executive Summary", self.styles["SectionHeader"]))
        story.append(Paragraph(executive_summary, self.styles["Body"]))

        # --- KEY METRICS TABLE ---
        story.append(Paragraph("Key Metrics This Week", self.styles["SectionHeader"]))
        metrics_table = self._build_metrics_table(enriched_df)
        story.append(metrics_table)
        story.append(Spacer(1, 0.15 * inch))

        # --- CRISIS ALERT (if any) ---
        if crisis_info.get("crisis_detected"):
            alert_text = (
                f"<b>⚠ CRISIS ALERT:</b> {crisis_info.get('crisis_type', 'Unknown type')} "
                f"(severity: {crisis_info.get('severity', 'unknown')}).<br/>"
                f"<b>Evidence:</b> {crisis_info.get('evidence_summary', 'N/A')}<br/>"
                f"<b>Recommended action:</b> {crisis_info.get('recommended_action', 'N/A')}"
            )
            story.append(Paragraph(alert_text, self.styles["CrisisAlert"]))

        # --- TOPICS BREAKDOWN ---
        story.append(Paragraph("Top Topics", self.styles["SectionHeader"]))
        topics_table = self._build_topics_table(enriched_df)
        story.append(topics_table)
        story.append(Spacer(1, 0.15 * inch))

        story.append(PageBreak())

        # --- PAGE 2: TRENDING MENTIONS ---
        story.append(Paragraph("Trending Mentions", self.styles["SectionHeader"]))
        story.append(Paragraph(
            "Most engaged mentions this week, ordered by reach (likes + comments).",
            self.styles["Body"]
        ))

        for _, row in self._top_mentions(enriched_df).iterrows():
            block = self._build_mention_block(row, brand_key)
            story.append(KeepTogether(block))

        doc.build(story)
        print(f"  PDF written: {output_path}")
        return str(output_path)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_metrics_table(self, df: pd.DataFrame) -> Table:
        total = len(df)
        avg_sent = df["sentiment_score"].mean() if total else 0
        positive = (df["sentiment_label"] == "positive").sum() if total else 0
        negative = (df["sentiment_label"] == "negative").sum() if total else 0
        neutral = (df["sentiment_label"] == "neutral").sum() if total else 0
        crisis = int(df["crisis_flag"].sum()) if total else 0
        avg_eng = ((df["engagement_likes"].fillna(0) + df["engagement_comments"].fillna(0)).mean()
                   if total else 0)

        data = [
            ["Total Mentions", "Avg Sentiment", "Positive", "Negative", "Neutral", "Crisis Flags"],
            [
                str(total),
                f"{avg_sent:.2f}/5",
                str(positive),
                str(negative),
                str(neutral),
                f"{crisis} ⚠" if crisis > 0 else "0",
            ],
        ]
        t = Table(data, colWidths=[1.2*inch, 1.3*inch, 0.9*inch, 0.9*inch, 0.9*inch, 1.2*inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), self.ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
        ]))
        return t

    def _build_topics_table(self, df: pd.DataFrame) -> Table:
        all_topics = []
        for tags in df["topic_tags"].dropna():
            if isinstance(tags, list):
                all_topics.extend(tags)
            elif isinstance(tags, str):
                all_topics.extend([t.strip() for t in tags.split(";") if t.strip()])
        topic_counts = pd.Series(all_topics).value_counts().head(8)

        data = [["Topic", "Count", "% of Mentions"]]
        total = max(len(df), 1)
        for topic, count in topic_counts.items():
            pct = (count / total) * 100
            data.append([topic.replace("_", " ").title(), str(count), f"{pct:.0f}%"])

        if len(data) == 1:
            data.append(["—", "0", "0%"])

        t = Table(data, colWidths=[3*inch, 1*inch, 1.5*inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), self.ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return t

    def _top_mentions(self, df: pd.DataFrame, n: int = 6) -> pd.DataFrame:
        if df.empty:
            return df
        df = df.copy()
        df["engagement_total"] = (
            df["engagement_likes"].fillna(0) + df["engagement_comments"].fillna(0)
        )
        return df.sort_values("engagement_total", ascending=False).head(n)

    def _build_mention_block(self, row, brand_key: str) -> list:
        sentiment_emoji = {
            5: "😍", 4: "🙂", 3: "😐", 2: "🙁", 1: "😡"
        }.get(int(row.get("sentiment_score", 3)), "")
        crisis_badge = " <b>[CRISIS FLAG]</b>" if row.get("crisis_flag") else ""

        blocks = []
        header = (
            f"<b>{row.get('source', 'unknown').upper()}</b> &nbsp;|&nbsp; "
            f"@{row.get('author_handle', '?')} &nbsp;|&nbsp; "
            f"{sentiment_emoji} {row.get('sentiment_label', 'unknown').title()} "
            f"({int(row.get('sentiment_score', 0))}/5){crisis_badge}"
        )
        blocks.append(Paragraph(header, self.styles["MentionText"]))

        text = (row.get("raw_text") or "")[:400]
        if len(row.get("raw_text", "") or "") > 400:
            text += "..."
        blocks.append(Paragraph(f"&ldquo;{text}&rdquo;", self.styles["MentionText"]))

        topics = row.get("topic_tags", "")
        if isinstance(topics, list):
            topics = ", ".join(topics)
        elif pd.isna(topics):
            topics = ""
        if topics:
            blocks.append(Paragraph(
                f"<i>Topics:</i> {topics}", self.styles["MentionText"]
            ))
        if row.get("summary"):
            blocks.append(Paragraph(
                f"<i>Insight:</i> {row['summary']}", self.styles["MentionText"]
            ))
        blocks.append(Spacer(1, 0.1 * inch))
        return blocks


if __name__ == "__main__":
    # Demo: render the sample data into a PDF
    from scrapers.apify_scraper import BrandMentionScraper  # noqa
    gen = WeeklyReportGenerator()
    raw = pd.read_csv("./data/sample_mentions.csv")
    for brand_key, group in raw.groupby("brand_key"):
        exec_summary = (
            f"Weekly demo report for {brand_key} based on {len(group)} mentions. "
            f"Average sentiment score: {group['sentiment_score'].mean():.2f}/5. "
            f"Crisis flags: {int(group['crisis_flag'].sum())}."
        )
        path = gen.generate(
            enriched_df=group,
            brand_key=brand_key,
            executive_summary=exec_summary,
            crisis_info={"crisis_detected": False},
        )
        print(f"Generated: {path}")
