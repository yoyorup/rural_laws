"""MySQL database manager with context manager support."""

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import List, Optional, Iterator
from datetime import datetime

import pymysql
import pymysql.cursors

from config import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE, MYSQL_UNIX_SOCKET
from database.models import Law, Clause, LawSummary, NewsItem, RunLog, LawWithDetails

logger = logging.getLogger(__name__)


def _connect() -> pymysql.Connection:
    kwargs: dict = dict(
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )
    if MYSQL_UNIX_SOCKET:
        kwargs["unix_socket"] = MYSQL_UNIX_SOCKET
    else:
        kwargs["host"] = MYSQL_HOST
        kwargs["port"] = MYSQL_PORT
    return pymysql.connect(**kwargs)


def init_db() -> None:
    """Initialize the database, creating tables and indexes if they don't exist."""
    schema_path = Path(__file__).parent / "schema_mysql.sql"
    sql = schema_path.read_text(encoding="utf-8")
    conn = _connect()
    try:
        with conn.cursor() as cur:
            for statement in sql.split(";"):
                stmt = statement.strip()
                if not stmt:
                    continue
                try:
                    cur.execute(stmt)
                except pymysql.err.OperationalError as e:
                    # 1061: duplicate key name (index already exists) — safe to ignore
                    if e.args[0] == 1061:
                        logger.debug("Index already exists, skipping: %s", e.args[1])
                    else:
                        raise
        conn.commit()
    finally:
        conn.close()
    logger.info("MySQL database initialized at %s:%s/%s", MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE)


@contextmanager
def get_connection() -> Iterator[pymysql.cursors.DictCursor]:
    """Context manager that yields a MySQL DictCursor."""
    conn = _connect()
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


# ---------------------------------------------------------------------------
# Laws
# ---------------------------------------------------------------------------

def upsert_law(law: Law) -> bool:
    """Insert or update a law. Returns True if this is a new law."""
    with get_connection() as cur:
        cur.execute("SELECT content_hash FROM laws WHERE id = %s", (law.id,))
        existing = cur.fetchone()

        if existing is None:
            cur.execute(
                """INSERT INTO laws
                   (id, title, source, source_url, publish_date, effective_date,
                    content_hash, raw_text, fetched_at, is_rural, relevance_score)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (law.id, law.title, law.source, law.source_url,
                 law.publish_date, law.effective_date, law.content_hash,
                 law.raw_text, law.fetched_at, law.is_rural, law.relevance_score),
            )
            return True  # new law
        elif existing["content_hash"] != law.content_hash:
            cur.execute(
                """UPDATE laws SET title=%s, raw_text=%s, content_hash=%s,
                   fetched_at=%s, relevance_score=%s
                   WHERE id=%s""",
                (law.title, law.raw_text, law.content_hash,
                 law.fetched_at, law.relevance_score, law.id),
            )
            return False  # updated law
        return False  # no change


def get_law(law_id: str) -> Optional[Law]:
    with get_connection() as cur:
        cur.execute("SELECT * FROM laws WHERE id = %s", (law_id,))
        row = cur.fetchone()
    if row is None:
        return None
    return Law(**row)


def get_laws_by_date(target_date: str) -> List[Law]:
    """Return all laws fetched on target_date (YYYY-MM-DD)."""
    with get_connection() as cur:
        cur.execute(
            "SELECT * FROM laws WHERE DATE(fetched_at) = %s ORDER BY relevance_score DESC",
            (target_date,),
        )
        rows = cur.fetchall()
    return [Law(**r) for r in rows]


def get_all_law_dates() -> List[str]:
    """Return distinct dates (YYYY-MM-DD) that have laws, newest first."""
    with get_connection() as cur:
        cur.execute(
            "SELECT DISTINCT DATE(fetched_at) AS d FROM laws ORDER BY d DESC"
        )
        rows = cur.fetchall()
    return [r["d"].strftime("%Y-%m-%d") if hasattr(r["d"], "strftime") else r["d"] for r in rows]


# ---------------------------------------------------------------------------
# Clauses
# ---------------------------------------------------------------------------

def insert_clauses(clauses: List[Clause]) -> None:
    with get_connection() as cur:
        cur.execute("DELETE FROM clauses WHERE law_id = %s", (clauses[0].law_id,))
        cur.executemany(
            """INSERT INTO clauses (law_id, article_no, raw_text, explanation, example, created_at)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            [(c.law_id, c.article_no, c.raw_text, c.explanation, c.example, c.created_at)
             for c in clauses],
        )


def get_clauses(law_id: str) -> List[Clause]:
    with get_connection() as cur:
        cur.execute(
            "SELECT * FROM clauses WHERE law_id = %s ORDER BY id", (law_id,)
        )
        rows = cur.fetchall()
    return [Clause(**row) for row in rows]


# ---------------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------------

def upsert_summary(summary: LawSummary) -> None:
    with get_connection() as cur:
        cur.execute(
            """INSERT INTO law_summaries (law_id, summary, created_at)
               VALUES (%s, %s, %s)
               ON DUPLICATE KEY UPDATE summary=VALUES(summary)""",
            (summary.law_id, summary.summary, summary.created_at),
        )


def get_summary(law_id: str) -> Optional[LawSummary]:
    with get_connection() as cur:
        cur.execute(
            "SELECT * FROM law_summaries WHERE law_id = %s", (law_id,)
        )
        row = cur.fetchone()
    if row is None:
        return None
    return LawSummary(**row)


# ---------------------------------------------------------------------------
# News
# ---------------------------------------------------------------------------

def insert_news(items: List[NewsItem]) -> None:
    with get_connection() as cur:
        for item in items:
            cur.execute(
                """INSERT IGNORE INTO news
                   (law_id, title, url, source, published_at, snippet)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (item.law_id, item.title, item.url, item.source,
                 item.published_at, item.snippet),
            )


def get_news(law_id: str) -> List[NewsItem]:
    with get_connection() as cur:
        cur.execute(
            "SELECT * FROM news WHERE law_id = %s ORDER BY published_at DESC",
            (law_id,),
        )
        rows = cur.fetchall()
    return [NewsItem(**row) for row in rows]


# ---------------------------------------------------------------------------
# Run logs
# ---------------------------------------------------------------------------

def start_run_log(run_date: str) -> int:
    with get_connection() as cur:
        cur.execute(
            """INSERT INTO run_logs (run_date, status, started_at)
               VALUES (%s, 'running', %s)""",
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
) -> None:
    with get_connection() as cur:
        cur.execute(
            """UPDATE run_logs SET laws_fetched=%s, laws_new=%s, laws_updated=%s,
               status=%s, error_msg=%s, finished_at=%s WHERE id=%s""",
            (laws_fetched, laws_new, laws_updated, status, error_msg,
             datetime.now().isoformat(), log_id),
        )


# ---------------------------------------------------------------------------
# Aggregated queries
# ---------------------------------------------------------------------------

def get_law_with_details(law_id: str) -> Optional[LawWithDetails]:
    law = get_law(law_id)
    if law is None:
        return None
    return LawWithDetails(
        law=law,
        clauses=get_clauses(law_id),
        summary=get_summary(law_id),
        news=get_news(law_id),
    )


def get_laws_with_details_by_date(target_date: str) -> List[LawWithDetails]:
    laws = get_laws_by_date(target_date)
    return [get_law_with_details(law.id) for law in laws]
