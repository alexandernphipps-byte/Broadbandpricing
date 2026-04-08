"""Scheduler for daily pricing checks."""

import logging
import time

import schedule

from broadband_pricing.config import DAILY_CHECK_TIME

logger = logging.getLogger(__name__)


def run_scheduler(check_fn, check_time: str = DAILY_CHECK_TIME):
    """Run the scheduler that checks pricing daily at the configured time."""
    from rich.console import Console

    console = Console()

    schedule.every().day.at(check_time).do(check_fn)

    console.print(f"[green]Scheduler started. Pricing check scheduled daily at {check_time}.[/green]")
    console.print("[dim]Press Ctrl+C to stop.[/dim]")

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        console.print("\n[yellow]Scheduler stopped.[/yellow]")
