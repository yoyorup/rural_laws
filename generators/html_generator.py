"""Jinja2-based HTML generator for the Rural Law Daily Review Dashboard."""

import logging
from datetime import datetime, date
from pathlib import Path
from typing import List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import OUTPUT_DIR, TEMPLATES_DIR
from database import db_manager
from database.models import LawWithDetails

logger = logging.getLogger(__name__)


def _create_jinja_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )

    # Custom filters
    env.filters["date_fmt"] = lambda s: s or "未知日期"
    env.filters["truncate_text"] = lambda s, n=200: (s[:n] + "…") if s and len(s) > n else (s or "")

    return env


class HtmlGenerator:
    """Generates all HTML pages from database content."""

    def __init__(self):
        self.env = _create_jinja_env()
        self.output_dir = OUTPUT_DIR

    def generate_all(self, target_date: Optional[str] = None) -> None:
        """
        Regenerate all HTML pages.
        target_date: YYYY-MM-DD string; defaults to today.
        """
        if target_date is None:
            target_date = date.today().isoformat()

        logger.info(f"Generating HTML for date: {target_date}")

        # Generate index (today's laws)
        self.generate_index(target_date)

        # Generate detail pages for today's laws
        law_details = db_manager.get_laws_with_details_by_date(target_date)
        for ld in law_details:
            self.generate_law_detail(ld, target_date)

        # Generate archive
        self.generate_archive()

        logger.info(f"HTML generation complete. Output: {self.output_dir}")

    def generate_index(self, target_date: str) -> Path:
        """Generate index.html with today's law summaries."""
        law_details = db_manager.get_laws_with_details_by_date(target_date)
        all_dates = db_manager.get_all_law_dates()

        template = self.env.get_template("index.html")
        html = template.render(
            today=target_date,
            law_details=law_details,
            all_dates=all_dates,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )

        out_path = self.output_dir / "index.html"
        out_path.write_text(html, encoding="utf-8")
        logger.info(f"Generated: {out_path}")
        return out_path

    def generate_law_detail(self, law_detail: LawWithDetails, target_date: str) -> Path:
        """Generate a detail HTML page for a single law."""
        law = law_detail.law
        date_dir = self.output_dir / "laws" / target_date
        date_dir.mkdir(parents=True, exist_ok=True)

        template = self.env.get_template("law_detail.html")
        html = template.render(
            law=law,
            clauses=law_detail.clauses,
            summary=law_detail.summary,
            news=law_detail.news,
            today=target_date,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )

        out_path = date_dir / f"{law.id}.html"
        out_path.write_text(html, encoding="utf-8")
        logger.info(f"Generated: {out_path}")
        return out_path

    def generate_archive(self) -> Path:
        """Generate archive.html listing all dates and their laws."""
        all_dates = db_manager.get_all_law_dates()
        archive_data = []

        for d in all_dates:
            laws = db_manager.get_laws_by_date(d)
            archive_data.append({"date": d, "laws": laws})

        template = self.env.get_template("archive.html")
        html = template.render(
            archive_data=archive_data,
            today=date.today().isoformat(),
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )

        out_path = self.output_dir / "archive.html"
        out_path.write_text(html, encoding="utf-8")
        logger.info(f"Generated: {out_path}")
        return out_path
