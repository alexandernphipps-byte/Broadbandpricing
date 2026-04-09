"""Scheduler for daily pricing checks at 9 AM ET."""

import logging
import time
from datetime import datetime, timezone, timedelta

import schedule

from broadband_pricing.config import DAILY_CHECK_TIME

logger = logging.getLogger(__name__)

# US Eastern Time offset (handles EST/EDT roughly)
ET = timezone(timedelta(hours=-5))


def _get_et_schedule_time(check_time: str) -> str:
    """Convert desired ET time to local system time for scheduling."""
    # Parse the desired ET hour/minute
    hour, minute = map(int, check_time.split(":"))
    # Build a datetime in ET
    now_utc = datetime.now(timezone.utc)
    et_target = now_utc.replace(hour=hour, minute=minute, second=0, tzinfo=ET)
    # Convert to local system time
    local_target = et_target.astimezone()
    return local_target.strftime("%H:%M")


def run_scheduler(check_fn, check_time: str = DAILY_CHECK_TIME):
    """Run the scheduler that checks pricing daily at the configured ET time."""
    from rich.console import Console

    console = Console()

    local_time = _get_et_schedule_time(check_time)
    schedule.every().day.at(local_time).do(check_fn)

    console.print(f"[green]Scheduler started. Pricing check scheduled daily at {check_time} ET (system time: {local_time}).[/green]")
    console.print("[dim]Press Ctrl+C to stop.[/dim]")

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        console.print("\n[yellow]Scheduler stopped.[/yellow]")
