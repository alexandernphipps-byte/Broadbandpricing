"""Visualization module - terminal tables and charts."""

import os
from collections import defaultdict
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from broadband_pricing.config import (
    PROVIDER_NAMES,
    PROVIDER_TYPE_NAMES,
    OUTPUT_DIR,
)
from broadband_pricing.database import (
    get_latest_pricing,
    get_pricing_history,
    get_price_changes,
    get_all_check_dates,
)

console = Console(width=140)


def _speed_label(speed_down: int) -> str:
    if speed_down >= 1000:
        gig = speed_down / 1000
        if gig == int(gig):
            return f"{int(gig)} Gig"
        return f"{gig:.1f} Gig"
    return f"{speed_down} Mbps"


def _type_color(provider_type: str) -> str:
    return {
        "cable": "cyan",
        "ilec_fiber": "green",
        "starlink": "yellow",
        "fwa": "magenta",
    }.get(provider_type, "white")


def print_current_pricing(city: Optional[str] = None):
    """Print a formatted table of current pricing."""
    records = get_latest_pricing(city)

    if not records:
        console.print("[red]No pricing data found. Run a check first.[/red]")
        return

    check_date = records[0]["check_date"]
    title = f"Broadband Pricing - {check_date}"
    if city:
        title += f" - {city}"

    # Group by city
    by_city = defaultdict(list)
    for r in records:
        by_city[f"{r['city']}, {r['state']}"].append(r)

    for city_name, city_records in sorted(by_city.items()):
        table = Table(
            title=f"[bold]{city_name}[/bold]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold white on dark_blue",
            title_style="bold",
            border_style="blue",
            padding=(0, 1),
        )

        table.add_column("Type", style="bold", min_width=10)
        table.add_column("Provider", min_width=18)
        table.add_column("Plan", min_width=22)
        table.add_column("Down", justify="right", min_width=8)
        table.add_column("Up", justify="right", min_width=8)
        table.add_column("$/mo", justify="right", style="bold green", min_width=7)
        table.add_column("Src", min_width=6)

        # Sort by provider type order, then by speed
        type_order = {"cable": 0, "ilec_fiber": 1, "starlink": 2, "fwa": 3}
        city_records.sort(
            key=lambda r: (type_order.get(r["provider_type"], 9), r["provider"], r["speed_down"])
        )

        prev_type = None
        for r in city_records:
            ptype = PROVIDER_TYPE_NAMES.get(r["provider_type"], r["provider_type"])
            color = _type_color(r["provider_type"])

            # Add separator between provider types
            if prev_type and prev_type != r["provider_type"]:
                table.add_section()

            type_display = f"[{color}]{ptype}[/{color}]" if prev_type != r["provider_type"] else ""
            prev_type = r["provider_type"]

            source_style = "green" if r["source"] == "scraped" else "dim"

            table.add_row(
                type_display,
                r["provider"],
                r["plan_name"],
                _speed_label(r["speed_down"]),
                _speed_label(r["speed_up"]),
                f"${r['monthly_price']:.2f}",
                f"[{source_style}]{r['source']}[/{source_style}]",
            )

        console.print(table)
        console.print()


def print_comparison_table():
    """Print a provider comparison table across all cities."""
    records = get_latest_pricing()
    if not records:
        console.print("[red]No pricing data found.[/red]")
        return

    # Build comparison: for each city, show the cheapest plan per provider type
    # at different speed tiers
    speed_tiers = [
        ("Basic", 0, 150),
        ("Mid", 150, 500),
        ("Fast", 500, 1100),
        ("Gigabit+", 1100, 100000),
    ]

    for tier_name, min_speed, max_speed in speed_tiers:
        table = Table(
            title=f"[bold]Price Comparison - {tier_name} Tier ({min_speed}-{max_speed} Mbps)[/bold]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold white on dark_blue",
            border_style="blue",
            padding=(0, 1),
        )

        table.add_column("City", style="bold", width=16)
        table.add_column("Cable", justify="right", width=14)
        table.add_column("ILEC Fiber", justify="right", width=14)
        table.add_column("Starlink", justify="right", width=14)
        table.add_column("FWA", justify="right", width=14)

        by_city = defaultdict(list)
        for r in records:
            by_city[f"{r['city']}, {r['state']}"].append(r)

        has_data = False
        for city_name in sorted(by_city.keys()):
            city_records = by_city[city_name]
            row = {"cable": "-", "ilec_fiber": "-", "starlink": "-", "fwa": "-"}

            for ptype in row:
                type_records = [
                    r
                    for r in city_records
                    if r["provider_type"] == ptype
                    and min_speed <= r["speed_down"] < max_speed
                ]
                if type_records:
                    cheapest = min(type_records, key=lambda r: r["monthly_price"])
                    row[ptype] = (
                        f"${cheapest['monthly_price']:.2f}\n"
                        f"[dim]{_speed_label(cheapest['speed_down'])}[/dim]"
                    )
                    has_data = True

            table.add_row(
                city_name,
                row["cable"],
                row["ilec_fiber"],
                row["starlink"],
                row["fwa"],
            )

        if has_data:
            console.print(table)
            console.print()


def print_price_changes(days: int = 30):
    """Print any detected price changes."""
    changes = get_price_changes(days)

    if not changes:
        console.print(f"[green]No price changes detected in the last {days} days.[/green]")
        return

    table = Table(
        title=f"[bold]Price Changes (Last {days} Days)[/bold]",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold white on dark_red",
        border_style="red",
    )

    table.add_column("Date", width=12)
    table.add_column("City", width=16)
    table.add_column("Provider", width=20)
    table.add_column("Plan", width=24)
    table.add_column("Old Price", justify="right", width=10)
    table.add_column("New Price", justify="right", width=10)
    table.add_column("Change", justify="right", width=10)

    for c in changes:
        diff = c["monthly_price"] - c["prev_price"]
        change_str = f"+${diff:.2f}" if diff > 0 else f"-${abs(diff):.2f}"
        change_style = "red" if diff > 0 else "green"

        table.add_row(
            c["check_date"],
            f"{c['city']}, {c['state']}",
            c["provider"],
            c["plan_name"],
            f"${c['prev_price']:.2f}",
            f"${c['monthly_price']:.2f}",
            f"[{change_style}]{change_str}[/{change_style}]",
        )

    console.print(table)


def generate_charts(days: int = 30, city: Optional[str] = None):
    """Generate pricing trend charts using matplotlib."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
    except ImportError:
        console.print("[red]matplotlib is required for charts. Install with: pip install matplotlib[/red]")
        return

    history = get_pricing_history(days=days, city=city)
    if not history:
        console.print("[yellow]Not enough historical data for charts yet.[/yellow]")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Chart 1: Average price by provider type over time
    _chart_avg_by_type(history, days, city, plt, mdates)

    # Chart 2: Price by city for each provider type
    _chart_by_city(history, days, city, plt, mdates)

    # Chart 3: Cheapest option per city over time
    _chart_cheapest(history, days, city, plt, mdates)

    console.print(f"[green]Charts saved to {OUTPUT_DIR}/[/green]")


def _chart_avg_by_type(history, days, city, plt, mdates):
    """Average price per provider type over time."""
    # Group: date -> provider_type -> list of prices
    data = defaultdict(lambda: defaultdict(list))
    for r in history:
        data[r["check_date"]][r["provider_type"]].append(r["monthly_price"])

    if len(data) < 2:
        return

    fig, ax = plt.subplots(figsize=(14, 7))

    type_colors = {
        "cable": "#2196F3",
        "ilec_fiber": "#4CAF50",
        "starlink": "#FF9800",
        "fwa": "#9C27B0",
    }

    for ptype, color in type_colors.items():
        dates = []
        avg_prices = []
        for date_str in sorted(data.keys()):
            if ptype in data[date_str]:
                dates.append(datetime.strptime(date_str, "%Y-%m-%d"))
                prices = data[date_str][ptype]
                avg_prices.append(sum(prices) / len(prices))

        if dates:
            label = PROVIDER_TYPE_NAMES.get(ptype, ptype)
            ax.plot(dates, avg_prices, marker="o", color=color, label=label, linewidth=2)

    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Average Monthly Price ($)", fontsize=12)
    title = "Average Broadband Pricing by Provider Type"
    if city:
        title += f" - {city}"
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    fig.autofmt_xdate()
    plt.tight_layout()

    suffix = f"_{city.lower().replace(' ', '_')}" if city else ""
    fig.savefig(os.path.join(OUTPUT_DIR, f"avg_by_type{suffix}.png"), dpi=150)
    plt.close(fig)


def _chart_by_city(history, days, city_filter, plt, mdates):
    """Price comparison across cities for each provider type."""
    if city_filter:
        return  # Skip city comparison when filtering by city

    type_order = ["cable", "ilec_fiber", "starlink", "fwa"]
    type_names = {t: PROVIDER_TYPE_NAMES.get(t, t) for t in type_order}

    # For each provider type, find the cheapest "gig" tier plan per city on latest date
    latest_records = get_latest_pricing()
    if not latest_records:
        return

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    for idx, ptype in enumerate(type_order):
        ax = axes[idx // 2][idx % 2]

        type_records = [r for r in latest_records if r["provider_type"] == ptype]

        # Group by city, get cheapest plan
        by_city = defaultdict(list)
        for r in type_records:
            by_city[f"{r['city']}, {r['state']}"].append(r)

        cities = []
        prices = []
        labels = []
        for city_name in sorted(by_city.keys()):
            cheapest = min(by_city[city_name], key=lambda r: r["monthly_price"])
            cities.append(city_name.split(",")[0])
            prices.append(cheapest["monthly_price"])
            labels.append(f"${cheapest['monthly_price']:.0f}\n{_speed_label(cheapest['speed_down'])}")

        if cities:
            type_colors = {
                "cable": "#2196F3",
                "ilec_fiber": "#4CAF50",
                "starlink": "#FF9800",
                "fwa": "#9C27B0",
            }
            bars = ax.bar(cities, prices, color=type_colors.get(ptype, "gray"), alpha=0.8)
            ax.set_title(type_names[ptype], fontsize=13, fontweight="bold")
            ax.set_ylabel("Monthly Price ($)")
            ax.tick_params(axis="x", rotation=45)

            for bar_item, label in zip(bars, labels):
                ax.text(
                    bar_item.get_x() + bar_item.get_width() / 2.0,
                    bar_item.get_height() + 1,
                    label,
                    ha="center",
                    va="bottom",
                    fontsize=8,
                )

    fig.suptitle("Cheapest Plan by City & Provider Type", fontsize=15, fontweight="bold")
    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "by_city_comparison.png"), dpi=150)
    plt.close(fig)


def _chart_cheapest(history, days, city_filter, plt, mdates):
    """Cheapest option per provider type at each speed tier."""
    latest = get_latest_pricing(city_filter)
    if not latest:
        return

    speed_tiers = [
        ("Basic\n(< 150 Mbps)", 0, 150),
        ("Mid\n(150-500 Mbps)", 150, 500),
        ("Fast\n(500-1000 Mbps)", 500, 1100),
        ("Gig+\n(1+ Gbps)", 1100, 100000),
    ]

    fig, ax = plt.subplots(figsize=(14, 8))

    type_order = ["cable", "ilec_fiber", "starlink", "fwa"]
    type_colors = {
        "cable": "#2196F3",
        "ilec_fiber": "#4CAF50",
        "starlink": "#FF9800",
        "fwa": "#9C27B0",
    }

    import numpy as np

    x = np.arange(len(speed_tiers))
    width = 0.2

    for i, ptype in enumerate(type_order):
        prices = []
        for _, min_s, max_s in speed_tiers:
            tier_records = [
                r for r in latest if r["provider_type"] == ptype and min_s <= r["speed_down"] < max_s
            ]
            if tier_records:
                prices.append(min(r["monthly_price"] for r in tier_records))
            else:
                prices.append(0)

        label = PROVIDER_TYPE_NAMES.get(ptype, ptype)
        bars = ax.bar(x + i * width, prices, width, label=label, color=type_colors.get(ptype), alpha=0.85)

        for bar_item, price in zip(bars, prices):
            if price > 0:
                ax.text(
                    bar_item.get_x() + bar_item.get_width() / 2.0,
                    bar_item.get_height() + 1,
                    f"${price:.0f}",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                )

    ax.set_xlabel("Speed Tier", fontsize=12)
    ax.set_ylabel("Cheapest Monthly Price ($)", fontsize=12)
    title = "Cheapest Plan by Speed Tier & Provider Type"
    if city_filter:
        title += f" - {city_filter}"
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels([t[0] for t in speed_tiers])
    ax.legend(fontsize=11)
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()

    suffix = f"_{city_filter.lower().replace(' ', '_')}" if city_filter else ""
    fig.savefig(os.path.join(OUTPUT_DIR, f"cheapest_by_tier{suffix}.png"), dpi=150)
    plt.close(fig)


def print_summary():
    """Print a quick summary of the pricing data."""
    records = get_latest_pricing()
    if not records:
        console.print("[red]No pricing data found.[/red]")
        return

    check_date = records[0]["check_date"]
    dates = get_all_check_dates()

    console.print(
        Panel(
            f"[bold]Latest check:[/bold] {check_date}\n"
            f"[bold]Total checks:[/bold] {len(dates)} day(s)\n"
            f"[bold]Plans tracked:[/bold] {len(records)}\n"
            f"[bold]Cities:[/bold] {len(set(r['city'] for r in records))}\n"
            f"[bold]Providers:[/bold] {len(set(r['provider'] for r in records))}",
            title="[bold]Broadband Pricing Tracker[/bold]",
            border_style="blue",
        )
    )
