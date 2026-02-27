-- Rural Law Daily Review System - SQLite Schema

-- 法律主表
CREATE TABLE IF NOT EXISTS laws (
    id              TEXT PRIMARY KEY,       -- URL hash (MD5)
    title           TEXT NOT NULL,
    source          TEXT,                   -- npc / moa / gov
    source_url      TEXT,
    publish_date    TEXT,                   -- YYYY-MM-DD
    effective_date  TEXT,                   -- YYYY-MM-DD
    content_hash    TEXT,                   -- detect content changes
    raw_text        TEXT,
    fetched_at      TEXT,                   -- ISO datetime
    is_rural        INTEGER DEFAULT 1,
    relevance_score REAL DEFAULT 0.0
);

-- 条文解读表
CREATE TABLE IF NOT EXISTS clauses (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    law_id       TEXT REFERENCES laws(id) ON DELETE CASCADE,
    article_no   TEXT,                      -- 第X条
    raw_text     TEXT,
    explanation  TEXT,                      -- Claude 生成的解读
    example      TEXT,                      -- Claude 生成的举例
    created_at   TEXT                       -- ISO datetime
);

-- 法律摘要表（Claude 生成）
CREATE TABLE IF NOT EXISTS law_summaries (
    law_id      TEXT PRIMARY KEY REFERENCES laws(id) ON DELETE CASCADE,
    summary     TEXT,
    created_at  TEXT
);

-- 相关新闻表
CREATE TABLE IF NOT EXISTS news (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    law_id       TEXT REFERENCES laws(id) ON DELETE CASCADE,
    title        TEXT,
    url          TEXT UNIQUE,
    source       TEXT,
    published_at TEXT,
    snippet      TEXT
);

-- 每日运行日志
CREATE TABLE IF NOT EXISTS run_logs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date     TEXT,                      -- YYYY-MM-DD
    laws_fetched INTEGER DEFAULT 0,
    laws_new     INTEGER DEFAULT 0,
    laws_updated INTEGER DEFAULT 0,
    status       TEXT,                      -- success / error
    error_msg    TEXT,
    started_at   TEXT,
    finished_at  TEXT
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_laws_publish_date ON laws(publish_date);
CREATE INDEX IF NOT EXISTS idx_laws_source ON laws(source);
CREATE INDEX IF NOT EXISTS idx_clauses_law_id ON clauses(law_id);
CREATE INDEX IF NOT EXISTS idx_news_law_id ON news(law_id);
CREATE INDEX IF NOT EXISTS idx_run_logs_date ON run_logs(run_date);
