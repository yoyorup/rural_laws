"""SQLite database manager with context manager support."""

import sqlite3
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import List, Optional, Iterator
from datetime import datetime, date

from config import DB_PATH
from database.models import Law, Clause, LawSummary, NewsItem, RunLog, LawWithDetails

logger = logging.getLogger(__name__)


def init_db(db_path: Path = DB_PATH) -> None:
    """Initialize the database, creating tables if they don't exist."""
    schema_path = Path(__file__).parent / "schema.sql"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema_path.read_text(encoding="utf-8"))
        conn.commit()
    logger.info(f"Database initialized at {db_path}")


@contextmanager
def get_connection(db_path: Path = DB_PATH) -> Iterator[sqlite3.Connection]:
    """Context manager that yields a SQLite connection with row factory."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Laws
# ---------------------------------------------------------------------------

def upsert_law(law: Law, db_path: Path = DB_PATH) -> bool:
    """Insert or update a law. Returns True if this is a new law."""
    with get_connection(db_path) as conn:
        existing = conn.execute(
            "SELECT content_hash FROM laws WHERE id = ?", (law.id,)
        ).fetchone()

        if existing is None:
            conn.execute(
                """INSERT INTO laws
                   (id, title, source, source_url, publish_date, effective_date,
                    content_hash, raw_text, fetched_at, is_rural, relevance_score)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (law.id, law.title, law.source, law.source_url,
                 law.publish_date, law.effective_date, law.content_hash,
                 law.raw_text, law.fetched_at, law.is_rural, law.relevance_score),
            )
            return True  # new law
        elif existing["content_hash"] != law.content_hash:
            conn.execute(
                """UPDATE laws SET title=?, raw_text=?, content_hash=?,
                   fetched_at=?, relevance_score=?
                   WHERE id=?""",
                (law.title, law.raw_text, law.content_hash,
                 law.fetched_at, law.relevance_score, law.id),
            )
            return False  # updated law
        return False  # no change


def get_law(law_id: str, db_path: Path = DB_PATH) -> Optional[Law]:
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM laws WHERE id = ?", (law_id,)).fetchone()
    if row is None:
        return None
    return Law(**dict(row))


def get_laws_by_date(target_date: str, db_path: Path = DB_PATH) -> List[Law]:
    """Return all laws fetched on target_date (YYYY-MM-DD)."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM laws WHERE DATE(fetched_at) = ? ORDER BY relevance_score DESC",
            (target_date,),
        ).fetchall()
    return [Law(**dict(r)) for r in rows]


def get_all_law_dates(db_path: Path = DB_PATH) -> List[str]:
    """Return distinct dates (YYYY-MM-DD) that have laws, newest first."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT DISTINCT DATE(fetched_at) as d FROM laws ORDER BY d DESC"
        ).fetchall()
    return [r["d"] for r in rows]


# ---------------------------------------------------------------------------
# Clauses
# ---------------------------------------------------------------------------

def insert_clauses(clauses: List[Clause], db_path: Path = DB_PATH) -> None:
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM clauses WHERE law_id = ?", (clauses[0].law_id,))
        conn.executemany(
            """INSERT INTO clauses (law_id, article_no, raw_text, explanation, example, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [(c.law_id, c.article_no, c.raw_text, c.explanation, c.example, c.created_at)
             for c in clauses],
        )


def get_clauses(law_id: str, db_path: Path = DB_PATH) -> List[Clause]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM clauses WHERE law_id = ? ORDER BY id", (law_id,)
        ).fetchall()
    return [Clause(**{k: row[k] for k in row.keys()}) for row in rows]


# ---------------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------------

def upsert_summary(summary: LawSummary, db_path: Path = DB_PATH) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            """INSERT INTO law_summaries (law_id, summary, created_at)
               VALUES (?, ?, ?)
               ON CONFLICT(law_id) DO UPDATE SET summary=excluded.summary""",
            (summary.law_id, summary.summary, summary.created_at),
        )


def get_summary(law_id: str, db_path: Path = DB_PATH) -> Optional[LawSummary]:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM law_summaries WHERE law_id = ?", (law_id,)
        ).fetchone()
    if row is None:
        return None
    return LawSummary(**dict(row))


# ---------------------------------------------------------------------------
# News
# ---------------------------------------------------------------------------

def insert_news(items: List[NewsItem], db_path: Path = DB_PATH) -> None:
    with get_connection(db_path) as conn:
        for item in items:
            conn.execute(
                """INSERT OR IGNORE INTO news
                   (law_id, title, url, source, published_at, snippet)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (item.law_id, item.title, item.url, item.source,
                 item.published_at, item.snippet),
            )


def get_news(law_id: str, db_path: Path = DB_PATH) -> List[NewsItem]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM news WHERE law_id = ? ORDER BY published_at DESC",
            (law_id,),
        ).fetchall()
    return [NewsItem(**{k: row[k] for k in row.keys()}) for row in rows]


# ---------------------------------------------------------------------------
# Run logs
# ---------------------------------------------------------------------------

def start_run_log(run_date: str, db_path: Path = DB_PATH) -> int:
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """INSERT INTO run_logs (run_date, status, started_at)
               VALUES (?, 'running', ?)""",
            (run_date, datetime.now().isoformat()),
        )
        return cur.lastrowid


def finish_run_log(
    log_id: int,
    laws_fetched: int,
    laws_new: int,
    laws_updated: int,
    status: str,
    error_msg: Optional[str] = None,
    db_path: Path = DB_PATH,
) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            """UPDATE run_logs SET laws_fetched=?, laws_new=?, laws_updated=?,
               status=?, error_msg=?, finished_at=? WHERE id=?""",
            (laws_fetched, laws_new, laws_updated, status, error_msg,
             datetime.now().isoformat(), log_id),
        )


# ---------------------------------------------------------------------------
# Aggregated queries
# ---------------------------------------------------------------------------

def get_law_with_details(law_id: str, db_path: Path = DB_PATH) -> Optional[LawWithDetails]:
    law = get_law(law_id, db_path)
    if law is None:
        return None
    return LawWithDetails(
        law=law,
        clauses=get_clauses(law_id, db_path),
        summary=get_summary(law_id, db_path),
        news=get_news(law_id, db_path),
    )


def get_laws_with_details_by_date(
    target_date: str, db_path: Path = DB_PATH
) -> List[LawWithDetails]:
    laws = get_laws_by_date(target_date, db_path)
    return [get_law_with_details(law.id, db_path) for law in laws]
