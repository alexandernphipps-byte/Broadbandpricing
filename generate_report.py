#!/usr/bin/env python3
"""Generate a PDF report of broadband pricing data."""

import os
from collections import defaultdict
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image,
    PageBreak,
    KeepTogether,
)

from broadband_pricing.config import PROVIDER_TYPE_NAMES, OUTPUT_DIR
from broadband_pricing.database import init_db, get_latest_pricing

OUTPUT_PDF = os.path.join(OUTPUT_DIR, "broadband_pricing_report.pdf")

TYPE_COLORS = {
    "cable": colors.HexColor("#2196F3"),
    "ilec_fiber": colors.HexColor("#4CAF50"),
    "starlink": colors.HexColor("#FF9800"),
    "fwa": colors.HexColor("#9C27B0"),
}

LIGHT_TYPE_COLORS = {
    "cable": colors.HexColor("#E3F2FD"),
    "ilec_fiber": colors.HexColor("#E8F5E9"),
    "starlink": colors.HexColor("#FFF3E0"),
    "fwa": colors.HexColor("#F3E5F5"),
}


def speed_label(speed_down):
    if speed_down >= 1000:
        gig = speed_down / 1000
        return f"{int(gig)} Gig" if gig == int(gig) else f"{gig:.1f} Gig"
    return f"{speed_down} Mbps"


def generate_pdf():
    init_db()
    records = get_latest_pricing()
    if not records:
        print("No pricing data found. Run 'python app.py check' first.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    check_date = records[0]["check_date"]

    doc = SimpleDocTemplate(
        OUTPUT_PDF,
        pagesize=landscape(letter),
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Title"], fontSize=22, spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"], fontSize=12,
        textColor=colors.gray, spaceAfter=20, alignment=1,
    )
    city_style = ParagraphStyle(
        "CityHeader", parent=styles["Heading2"], fontSize=14,
        spaceAfter=8, spaceBefore=14, textColor=colors.HexColor("#1a237e"),
    )
    section_style = ParagraphStyle(
        "Section", parent=styles["Heading1"], fontSize=16,
        spaceBefore=20, spaceAfter=10, textColor=colors.HexColor("#0d47a1"),
    )

    elements = []

    # --- Title ---
    elements.append(Paragraph("Broadband Pricing Report", title_style))
    elements.append(Paragraph(
        f"Generated {datetime.now().strftime('%B %d, %Y at %I:%M %p')} &bull; "
        f"Data from {check_date} &bull; "
        f"{len(records)} plans across {len(set(r['city'] for r in records))} cities",
        subtitle_style,
    ))
    elements.append(Spacer(1, 10))

    # --- Summary table ---
    elements.append(Paragraph("Summary", section_style))
    providers = sorted(set(r["provider"] for r in records))
    cities = sorted(set(f"{r['city']}, {r['state']}" for r in records))

    summary_data = [["Metric", "Value"]]
    summary_data.append(["Cities Tracked", str(len(cities))])
    summary_data.append(["Providers", str(len(providers))])
    summary_data.append(["Total Plans", str(len(records))])
    summary_data.append(["Provider Types", "Cable, ILEC Fiber, Starlink, FWA"])
    summary_data.append(["Cheapest Plan", ""])
    cheapest = min(records, key=lambda r: r["monthly_price"])
    summary_data[-1][1] = (
        f"${cheapest['monthly_price']:.2f}/mo - {cheapest['provider']} "
        f"({cheapest['plan_name']}) in {cheapest['city']}, {cheapest['state']}"
    )
    summary_data.append(["Most Expensive", ""])
    priciest = max(records, key=lambda r: r["monthly_price"])
    summary_data[-1][1] = (
        f"${priciest['monthly_price']:.2f}/mo - {priciest['provider']} "
        f"({priciest['plan_name']}) in {priciest['city']}, {priciest['state']}"
    )

    summary_table = Table(summary_data, colWidths=[2 * inch, 7 * inch])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a237e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#E8EAF6")),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BDBDBD")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 10))

    # --- Per-city pricing tables ---
    elements.append(Paragraph("Pricing by City", section_style))

    by_city = defaultdict(list)
    for r in records:
        by_city[f"{r['city']}, {r['state']}"].append(r)

    type_order = {"cable": 0, "ilec_fiber": 1, "starlink": 2, "fwa": 3}

    for city_name in sorted(by_city.keys()):
        city_records = sorted(
            by_city[city_name],
            key=lambda r: (type_order.get(r["provider_type"], 9), r["provider"], r["speed_down"]),
        )

        city_elements = []
        city_elements.append(Paragraph(city_name, city_style))

        header = ["Type", "Provider", "Plan", "Down", "Up", "$/mo"]
        table_data = [header]

        prev_type = None
        for r in city_records:
            ptype = PROVIDER_TYPE_NAMES.get(r["provider_type"], r["provider_type"])
            type_display = ptype if prev_type != r["provider_type"] else ""
            prev_type = r["provider_type"]

            table_data.append([
                type_display,
                r["provider"],
                r["plan_name"],
                speed_label(r["speed_down"]),
                speed_label(r["speed_up"]),
                f"${r['monthly_price']:.2f}",
            ])

        col_widths = [1.1 * inch, 1.8 * inch, 2.2 * inch, 1.1 * inch, 1.1 * inch, 0.9 * inch]
        t = Table(table_data, colWidths=col_widths)

        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a237e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BDBDBD")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 4),
            ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
        ]

        # Color-code rows by provider type
        for i, r in enumerate(city_records, start=1):
            bg = LIGHT_TYPE_COLORS.get(r["provider_type"], colors.white)
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), bg))

        t.setStyle(TableStyle(style_cmds))
        city_elements.append(t)
        city_elements.append(Spacer(1, 8))
        elements.append(KeepTogether(city_elements))

    # --- Comparison tables ---
    elements.append(PageBreak())
    elements.append(Paragraph("Cross-City Comparison", section_style))

    speed_tiers = [
        ("Basic (< 150 Mbps)", 0, 150),
        ("Mid (150-500 Mbps)", 150, 500),
        ("Fast (500-1000 Mbps)", 500, 1100),
        ("Gigabit+ (1+ Gbps)", 1100, 100000),
    ]

    for tier_name, min_s, max_s in speed_tiers:
        tier_elements = []
        tier_elements.append(Paragraph(tier_name, city_style))

        header = ["City", "Cable", "ILEC Fiber", "Starlink", "FWA"]
        table_data = [header]

        for city_name in sorted(by_city.keys()):
            row = [city_name]
            for ptype in ["cable", "ilec_fiber", "starlink", "fwa"]:
                matches = [
                    r for r in by_city[city_name]
                    if r["provider_type"] == ptype and min_s <= r["speed_down"] < max_s
                ]
                if matches:
                    best = min(matches, key=lambda r: r["monthly_price"])
                    row.append(f"${best['monthly_price']:.2f}\n{speed_label(best['speed_down'])}")
                else:
                    row.append("-")
            table_data.append(row)

        col_widths = [1.8 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch]
        t = Table(table_data, colWidths=col_widths)
        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a237e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BDBDBD")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 4),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
        ]
        t.setStyle(TableStyle(style_cmds))
        tier_elements.append(t)
        tier_elements.append(Spacer(1, 12))
        elements.append(KeepTogether(tier_elements))

    # --- Charts ---
    chart_files = [
        ("by_city_comparison.png", "Cheapest Plan by City & Provider Type"),
        ("cheapest_by_tier.png", "Cheapest Plan by Speed Tier"),
    ]
    for fname, chart_title in chart_files:
        fpath = os.path.join(OUTPUT_DIR, fname)
        if os.path.exists(fpath):
            elements.append(PageBreak())
            elements.append(Paragraph(chart_title, section_style))
            elements.append(Image(fpath, width=9 * inch, height=5.5 * inch))

    # Build PDF
    doc.build(elements)
    print(f"PDF report saved to: {OUTPUT_PDF}")


if __name__ == "__main__":
    generate_pdf()
