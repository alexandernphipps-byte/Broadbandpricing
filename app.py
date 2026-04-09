#!/usr/bin/env python3
"""Broadband Pricing Checker - CLI entry point."""

import logging
import sys
from datetime import datetime

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.logging import RichHandler

from broadband_pricing.config import LOCATIONS, PROVIDER_NAMES, DAILY_CHECK_TIME
from broadband_pricing.database import init_db, store_plans, log_check
from broadband_pricing.providers import get_provider
from broadband_pricing.visualization import (
    print_current_pricing,
    print_comparison_table,
    print_price_changes,
    print_summary,
    generate_charts,
)
from broadband_pricing.scheduler import run_scheduler

console = Console()


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.CRITICAL
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(rich_tracebacks=True, show_time=False)],
    )


def run_price_check(cities: list[str] | None = None, verbose: bool = False):
    """Run a pricing check across all configured locations."""
    init_db()

    locations = LOCATIONS
    if cities:
        city_set = {c.lower() for c in cities}
        locations = [loc for loc in LOCATIONS if loc.city.lower() in city_set]
        if not locations:
            console.print(f"[red]No matching cities found. Available: {', '.join(l.city for l in LOCATIONS)}[/red]")
            return

    total_plans = 0
    total_providers = 0
    errors = []

    console.print(f"\n[bold blue]Broadband Pricing Check - {datetime.now().strftime('%Y-%m-%d %H:%M')}[/bold blue]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        total_tasks = sum(len(loc.providers) for loc in locations)
        task = progress.add_task("Checking prices...", total=total_tasks)

        for location in locations:
            for ptype, provider_key in location.providers.items():
                provider_name = PROVIDER_NAMES.get(provider_key, provider_key)
                progress.update(
                    task,
                    description=f"[cyan]{location.city}[/cyan] - {provider_name}",
                )

                try:
                    provider = get_provider(provider_key)

                    # Try scraping first
                    source = "published"
                    try:
                        plans = provider.scrape_plans(location)
                        if plans:
                            source = "scraped"
                    except Exception:
                        plans = None

                    # Fall back to published pricing
                    if not plans:
                        plans = provider.published_plans(location)

                    if plans:
                        store_plans(location, plans, source=source)
                        total_plans += len(plans)
                        total_providers += 1

                        if verbose:
                            for plan in plans:
                                console.print(
                                    f"  [dim]{plan.provider} - {plan.plan_name}: "
                                    f"${plan.monthly_price:.2f}/mo ({plan.speed_down} Mbps)[/dim]"
                                )

                except Exception as e:
                    error_msg = f"{provider_name} in {location.city}: {e}"
                    errors.append(error_msg)
                    if verbose:
                        console.print(f"  [red]Error: {error_msg}[/red]")

                progress.advance(task)

    # Log the check
    status = "success" if not errors else ("partial" if total_plans > 0 else "failed")
    log_check(status, len(locations), total_providers, total_plans, "; ".join(errors))

    console.print(f"\n[green]Done![/green] Found {total_plans} plans from {total_providers} providers across {len(locations)} cities.")
    if errors:
        console.print(f"[yellow]{len(errors)} error(s) occurred (using published pricing as fallback).[/yellow]")


# --- CLI Commands ---

@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx, verbose):
    """Broadband Pricing Checker - Track ISP pricing across US cities."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    setup_logging(verbose)


@cli.command()
@click.option("--city", "-c", multiple=True, help="Filter by city name (can specify multiple)")
@click.pass_context
def check(ctx, city):
    """Run a pricing check now."""
    run_price_check(cities=list(city) if city else None, verbose=ctx.obj["verbose"])


@cli.command()
@click.option("--city", "-c", default=None, help="Filter by city name")
def show(city):
    """Show the latest pricing data."""
    init_db()
    print_summary()
    console.print()
    print_current_pricing(city)


@cli.command()
def compare():
    """Show a comparison table across cities and provider types."""
    init_db()
    print_comparison_table()


@cli.command()
@click.option("--days", "-d", default=30, help="Number of days to look back")
def changes(days):
    """Show detected price changes."""
    init_db()
    print_price_changes(days)


@cli.command()
@click.option("--days", "-d", default=30, help="Number of days of history")
@click.option("--city", "-c", default=None, help="Filter by city name")
def charts(days, city):
    """Generate pricing trend charts (saved to output/)."""
    init_db()
    generate_charts(days=days, city=city)


@cli.command()
@click.option("--time", "-t", "check_time", default=DAILY_CHECK_TIME, help="Time to run daily check in ET (HH:MM)")
def schedule(check_time):
    """Start the daily scheduler (runs at 9 AM ET by default)."""
    init_db()
    console.print(f"[bold]Starting daily pricing scheduler at {check_time} ET...[/bold]")
    run_scheduler(lambda: run_price_check(), check_time=check_time)


@cli.command()
def cities():
    """List all configured cities and their providers."""
    from rich.table import Table
    from rich import box

    table = Table(
        title="[bold]Configured Locations[/bold]",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold white on dark_blue",
    )
    table.add_column("City", min_width=18)
    table.add_column("Address", min_width=24)
    table.add_column("ZIP", min_width=6)
    table.add_column("Cable", min_width=12)
    table.add_column("ILEC Fiber", min_width=16)
    table.add_column("Starlink", min_width=10)
    table.add_column("FWA", min_width=22)

    for loc in LOCATIONS:
        table.add_row(
            f"{loc.city}, {loc.state}",
            loc.address,
            loc.zip_code,
            PROVIDER_NAMES.get(loc.providers.get("cable", ""), "—"),
            PROVIDER_NAMES.get(loc.providers.get("ilec_fiber", ""), "—"),
            PROVIDER_NAMES.get(loc.providers.get("starlink", ""), "—"),
            PROVIDER_NAMES.get(loc.providers.get("fwa", ""), "—"),
        )

    console.print(table)


if __name__ == "__main__":
    cli()
