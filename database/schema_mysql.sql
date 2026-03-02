-- Rural Law Daily Review System - MySQL Schema
-- Adapted from SQLite version

CREATE DATABASE IF NOT EXISTS rural_law_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE rural_law_db;

-- 法律主表
CREATE TABLE IF NOT EXISTS laws (
    id              VARCHAR(64) PRIMARY KEY,       -- URL hash (MD5)
    title           TEXT NOT NULL,
    source          VARCHAR(32),                   -- npc / moa / gov
    source_url      TEXT,
    publish_date    VARCHAR(10),                   -- YYYY-MM-DD
    effective_date  VARCHAR(10),                   -- YYYY-MM-DD
    content_hash    VARCHAR(64),                   -- detect content changes
    raw_text        LONGTEXT,
    fetched_at      VARCHAR(32),                   -- ISO datetime
    is_rural        TINYINT(1) DEFAULT 1,
    relevance_score DOUBLE DEFAULT 0.0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 条文解读表
CREATE TABLE IF NOT EXISTS clauses (
    id           INT PRIMARY KEY AUTO_INCREMENT,
    law_id       VARCHAR(64),
    article_no   VARCHAR(32),                      -- 第X条
    raw_text     LONGTEXT,
    explanation  LONGTEXT,                         -- Claude 生成的解读
    example      LONGTEXT,                         -- Claude 生成的举例
    created_at   VARCHAR(32),                      -- ISO datetime
    CONSTRAINT fk_clauses_law FOREIGN KEY (law_id) REFERENCES laws(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 法律摘要表（Claude 生成）
CREATE TABLE IF NOT EXISTS law_summaries (
    law_id      VARCHAR(64) PRIMARY KEY,
    summary     LONGTEXT,
    created_at  VARCHAR(32),
    CONSTRAINT fk_law_summaries_law FOREIGN KEY (law_id) REFERENCES laws(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 相关新闻表
CREATE TABLE IF NOT EXISTS news (
    id           INT PRIMARY KEY AUTO_INCREMENT,
    law_id       VARCHAR(64),
    title        TEXT,
    url          TEXT,
    source       VARCHAR(64),
    published_at VARCHAR(32),
    snippet      TEXT,
    UNIQUE KEY uk_news_url (url(512)),
    CONSTRAINT fk_news_law FOREIGN KEY (law_id) REFERENCES laws(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 每日运行日志
CREATE TABLE IF NOT EXISTS run_logs (
    id           INT PRIMARY KEY AUTO_INCREMENT,
    run_date     VARCHAR(10),                      -- YYYY-MM-DD
    laws_fetched INT DEFAULT 0,
    laws_new     INT DEFAULT 0,
    laws_updated INT DEFAULT 0,
    status       VARCHAR(16),                      -- success / error
    error_msg    TEXT,
    started_at   VARCHAR(32),
    finished_at  VARCHAR(32)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Indexes
CREATE INDEX idx_laws_publish_date ON laws(publish_date);
CREATE INDEX idx_laws_source ON laws(source);
CREATE INDEX idx_clauses_law_id ON clauses(law_id);
CREATE INDEX idx_news_law_id ON news(law_id);
CREATE INDEX idx_run_logs_date ON run_logs(run_date);
