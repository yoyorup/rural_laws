"""
Core pipeline orchestrator.
fetch → filter → deduplicate → ai_process → fetch_news → generate_html
"""

import logging
from datetime import date
from typing import Optional

from database import db_manager
from fetchers.npc_fetcher import NpcFetcher
from fetchers.moa_fetcher import MoaFetcher
from fetchers.news_fetcher import NewsFetcher
from processors.law_filter import filter_laws
from processors.deduplicator import classify_laws, deduplicate_within_batch, LawStatus
from generators.html_generator import HtmlGenerator

logger = logging.getLogger(__name__)


def run_pipeline(target_date: Optional[str] = None, provider_name: Optional[str] = None) -> dict:
    """
    Run the full daily pipeline.
    Returns a stats dict with counts and status.
    """
    if target_date is None:
        target_date = date.today().isoformat()

    stats = {
        "target_date": target_date,
        "laws_fetched": 0,
        "laws_new": 0,
        "laws_updated": 0,
        "laws_processed": 0,
        "status": "success",
        "error": None,
    }

    # Ensure DB is initialized
    db_manager.init_db()
    log_id = db_manager.start_run_log(target_date)

    try:
        # ── Step 1: Fetch ────────────────────────────────────
        logger.info("Step 1: Fetching laws...")
        all_laws = []

        npc = NpcFetcher()
        npc_laws = npc.fetch_recent_laws()
        logger.info(f"  NPC: {len(npc_laws)} laws")
        all_laws.extend(npc_laws)

        # 关闭 Playwright
        npc.playwright.close()

        moa = MoaFetcher()
        moa_laws = moa.fetch_recent_laws()
        logger.info(f"  MOA: {len(moa_laws)} laws")
        all_laws.extend(moa_laws)

        # 关闭 Playwright
        moa.playwright.close()

        stats["laws_fetched"] = len(all_laws)

        if not all_laws:
            logger.warning("No laws fetched. Proceeding to HTML generation.")
            _generate(target_date)
            db_manager.finish_run_log(log_id, 0, 0, 0, "success")
            return stats

        # ── Step 2: Within-batch dedup ───────────────────────
        all_laws = deduplicate_within_batch(all_laws)

        # ── Step 3: Filter for rural relevance ───────────────
        logger.info("Step 3: Filtering for rural relevance...")
        relevant_laws = filter_laws(all_laws)
        logger.info(f"  {len(relevant_laws)} / {len(all_laws)} laws are rural-relevant")

        # ── Step 4: DB dedup (new vs updated vs unchanged) ───
        logger.info("Step 4: Deduplicating against database...")
        classified = classify_laws(relevant_laws)
        new_laws = [(law, st) for law, st in classified if st == LawStatus.NEW]
        updated_laws = [(law, st) for law, st in classified if st == LawStatus.UPDATED]

        stats["laws_new"] = len(new_laws)
        stats["laws_updated"] = len(updated_laws)
        logger.info(f"  New: {len(new_laws)}, Updated: {len(updated_laws)}")

        # ── Step 5: Persist laws ─────────────────────────────
        for law, _ in new_laws + updated_laws:
            db_manager.upsert_law(law)

        laws_to_process = [law for law, _ in new_laws + updated_laws]

        # ── Step 6: AI processing ──────────────────────────────
        if laws_to_process:
            from processors.ai_providers.factory import get_provider
            from processors.law_processor import LawProcessor
            provider = get_provider(provider_name)
            logger.info(
                f"Step 6: Processing {len(laws_to_process)} laws with {provider.name}..."
            )
            try:
                if not provider.is_available():
                    raise ValueError(
                        f"API key for provider '{provider.name}' is not configured."
                    )
                processor = LawProcessor(provider)
                for law in laws_to_process:
                    clauses, summary = processor.process_law(law)
                    if clauses:
                        db_manager.insert_clauses(clauses)
                    if summary:
                        db_manager.upsert_summary(summary)
                    stats["laws_processed"] += 1
                    logger.info(f"  Processed: {law.title}")
            except ValueError as e:
                # API key not set — skip AI processing
                logger.warning(f"AI processing skipped: {e}")
        else:
            logger.info("Step 6: No new/updated laws to process with AI.")

        # ── Step 7: Fetch news ────────────────────────────────
        if laws_to_process:
            logger.info("Step 7: Fetching related news...")
            news_fetcher = NewsFetcher()
            for law in laws_to_process:
                news_items = news_fetcher.fetch_news_for_law(law.id, law.title)
                if news_items:
                    db_manager.insert_news(news_items)
                    logger.info(f"  {len(news_items)} news items for: {law.title}")

        # ── Step 8: Generate HTML ─────────────────────────────
        logger.info("Step 8: Generating HTML...")
        _generate(target_date)

        db_manager.finish_run_log(
            log_id,
            stats["laws_fetched"],
            stats["laws_new"],
            stats["laws_updated"],
            "success",
        )
        logger.info(f"Pipeline complete: {stats}")

    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        stats["status"] = "error"
        stats["error"] = str(e)
        db_manager.finish_run_log(log_id, 0, 0, 0, "error", str(e))

    return stats


def _generate(target_date: str) -> None:
    gen = HtmlGenerator()
    gen.generate_all(target_date)
