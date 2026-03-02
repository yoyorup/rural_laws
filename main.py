#!/usr/bin/env python3
"""
CLI entry point for the Rural Law Daily Review System.

Usage:
  python main.py --run-now          # Run the full pipeline immediately
  python main.py --run-now --date 2026-02-27   # Run for a specific date
  python main.py --generate-only    # Re-generate HTML from existing DB data
  python main.py --schedule         # Start the nightly 00:00 scheduler
  python main.py --init-db          # Initialize the database only
"""

import argparse
import logging
import sys
from datetime import date

from config import LOG_LEVEL, MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE


def setup_logging(level: str = LOG_LEVEL) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )


def cmd_run_now(target_date: str, provider_name: str = None) -> None:
    from pipeline import run_pipeline
    print(f"\n=== Running pipeline for {target_date} ===\n")
    stats = run_pipeline(target_date=target_date, provider_name=provider_name)
    print("\n=== Pipeline complete ===")
    print(f"  Laws fetched  : {stats['laws_fetched']}")
    print(f"  Laws new      : {stats['laws_new']}")
    print(f"  Laws updated  : {stats['laws_updated']}")
    print(f"  Claude processed: {stats['laws_processed']}")
    print(f"  Status        : {stats['status']}")
    if stats.get("error"):
        print(f"  Error         : {stats['error']}")
    print(f"\n  Open output/index.html in your browser to view the dashboard.")


def cmd_generate_only(target_date: str) -> None:
    from database import db_manager
    from generators.html_generator import HtmlGenerator
    db_manager.init_db()
    print(f"\n=== Generating HTML for {target_date} ===\n")
    gen = HtmlGenerator()
    gen.generate_all(target_date)
    print("  Done. Open output/index.html in your browser.")


def cmd_schedule() -> None:
    from scheduler.cron_job import start_scheduler
    print("\n=== Starting scheduler (Ctrl+C to stop) ===")
    print("  Will run daily at 00:00 Asia/Shanghai\n")
    start_scheduler()


def cmd_init_db() -> None:
    from database import db_manager
    db_manager.init_db()
    print(f"  Database initialized at: {MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="农村法律每日速览系统 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--run-now", action="store_true",
        help="Run the full fetch+process+generate pipeline immediately",
    )
    parser.add_argument(
        "--date", metavar="YYYY-MM-DD",
        default=date.today().isoformat(),
        help="Target date for the pipeline (default: today)",
    )
    parser.add_argument(
        "--generate-only", action="store_true",
        help="Re-generate HTML from existing database data (no fetching)",
    )
    parser.add_argument(
        "--schedule", action="store_true",
        help="Start the nightly 00:00 scheduler",
    )
    parser.add_argument(
        "--init-db", action="store_true",
        help="Initialize the SQLite database schema",
    )
    parser.add_argument(
        "--ai-provider",
        metavar="PROVIDER",
        default=None,
        help=(
            "AI provider to use for law processing: claude | openai | qwen | glm | gemini "
            "(default: reads DEFAULT_AI_PROVIDER from config / .env)"
        ),
    )
    parser.add_argument(
        "--log-level", default=LOG_LEVEL,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )

    args = parser.parse_args()
    setup_logging(args.log_level)

    if args.init_db:
        cmd_init_db()
    elif args.run_now:
        cmd_run_now(args.date, provider_name=args.ai_provider)
    elif args.generate_only:
        cmd_generate_only(args.date)
    elif args.schedule:
        cmd_schedule()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
