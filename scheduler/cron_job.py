"""APScheduler-based daily cron job (runs at 00:00 Asia/Shanghai)."""

import logging
from datetime import date

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


def run_daily_pipeline() -> None:
    """
    Full daily pipeline:
    fetch → filter → deduplicate → claude_process → fetch_news → generate_html
    """
    # Import here to avoid circular imports and to ensure .env is loaded first
    from pipeline import run_pipeline
    today = date.today().isoformat()
    logger.info(f"[Scheduler] Starting daily pipeline for {today}")
    run_pipeline(target_date=today)


def start_scheduler() -> None:
    """Start the blocking APScheduler running at 00:00 Asia/Shanghai."""
    scheduler = BlockingScheduler(timezone="Asia/Shanghai")

    scheduler.add_job(
        run_daily_pipeline,
        trigger=CronTrigger(hour=0, minute=0, timezone="Asia/Shanghai"),
        id="daily_law_fetch",
        name="Daily Rural Law Fetch",
        replace_existing=True,
        misfire_grace_time=3600,  # allow 1-hour grace window if missed
    )

    logger.info("Scheduler started. Waiting for 00:00 Asia/Shanghai...")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")
