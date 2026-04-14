-- Multi-Agent Learning System Database Schema
-- SQLite compatible schema

-- Documents table
CREATE TABLE IF NOT EXISTS docs (
    doc_id TEXT PRIMARY KEY,
    title TEXT,
    source TEXT,
    source_type TEXT,  -- pdf, html, text, docx, pptx, xlsx, xls, markdown, csv, json, xml
    lang TEXT,
    created_at TEXT,
    updated_at TEXT,
    metadata TEXT  -- JSON
);

-- Sections table (document segments)
CREATE TABLE IF NOT EXISTS sections (
    sec_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    idx INTEGER,
    title TEXT,
    text TEXT,
    topic_tags TEXT,  -- JSON array
    created_at TEXT,
    FOREIGN KEY (doc_id) REFERENCES docs(doc_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sections_doc_id ON sections(doc_id);

-- Concepts table (knowledge graph nodes)
CREATE TABLE IF NOT EXISTS concepts (
    cid TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    term TEXT NOT NULL,
    aliases TEXT,  -- JSON array
    definition TEXT,
    refs TEXT,  -- JSON array of section ids
    created_at TEXT,
    FOREIGN KEY (doc_id) REFERENCES docs(doc_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_concepts_doc_id ON concepts(doc_id);
CREATE INDEX IF NOT EXISTS idx_concepts_term ON concepts(term);

-- Relations table (knowledge graph edges)
CREATE TABLE IF NOT EXISTS relations (
    id TEXT PRIMARY KEY,
    src TEXT NOT NULL,  -- source concept id
    rel TEXT NOT NULL,  -- relation type
    dst TEXT NOT NULL,  -- destination concept id
    weight REAL DEFAULT 1.0,
    created_at TEXT,
    FOREIGN KEY (src) REFERENCES concepts(cid) ON DELETE CASCADE,
    FOREIGN KEY (dst) REFERENCES concepts(cid) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_relations_src ON relations(src);
CREATE INDEX IF NOT EXISTS idx_relations_dst ON relations(dst);

-- Cards table (quiz cards)
CREATE TABLE IF NOT EXISTS cards (
    card_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    type TEXT NOT NULL,  -- cloze, mcq, short
    stem TEXT NOT NULL,  -- question text
    choices TEXT,  -- JSON array for MCQ
    answer TEXT NOT NULL,
    explanation TEXT,
    source_ref TEXT,  -- section id
    concept_refs TEXT,  -- JSON array of concept ids
    difficulty TEXT,  -- L, M, H
    created_at TEXT,
    FOREIGN KEY (doc_id) REFERENCES docs(doc_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_cards_doc_id ON cards(doc_id);
CREATE INDEX IF NOT EXISTS idx_cards_type ON cards(type);
CREATE INDEX IF NOT EXISTS idx_cards_difficulty ON cards(difficulty);

-- Reviews table (user practice records)
CREATE TABLE IF NOT EXISTS reviews (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    card_id TEXT NOT NULL,
    ts TEXT NOT NULL,  -- timestamp
    response TEXT,
    score REAL,
    is_correct INTEGER,  -- 0 or 1
    error_type TEXT,
    latency_ms INTEGER,
    next_due TEXT,  -- next review date
    ef REAL,  -- easiness factor
    interval_days INTEGER,
    repetitions INTEGER,
    FOREIGN KEY (card_id) REFERENCES cards(card_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_reviews_user_id ON reviews(user_id);
CREATE INDEX IF NOT EXISTS idx_reviews_card_id ON reviews(card_id);
CREATE INDEX IF NOT EXISTS idx_reviews_next_due ON reviews(next_due);

-- User profiles table
CREATE TABLE IF NOT EXISTS profiles (
    user_id TEXT PRIMARY KEY,
    username TEXT,
    email TEXT,
    mastery TEXT,  -- JSON: concept -> mastery score
    prefs TEXT,  -- JSON: user preferences
    created_at TEXT,
    updated_at TEXT
);

-- Learning progress table (保存学习进度)
CREATE TABLE IF NOT EXISTS learning_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    doc_id TEXT NOT NULL,
    current_card_idx INTEGER DEFAULT 0,  -- 当前学习到第几题
    total_cards INTEGER DEFAULT 0,  -- 总卡片数
    last_updated TEXT,  -- 最后更新时间
    UNIQUE(user_id, doc_id),
    FOREIGN KEY (doc_id) REFERENCES docs(doc_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_progress_user_id ON learning_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_progress_doc_id ON learning_progress(doc_id);

-- Audit logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    stage TEXT NOT NULL,
    doc_id TEXT,
    user_id TEXT,
    action TEXT,
    input_summary TEXT,
    output_summary TEXT,
    status TEXT,
    error TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_stage ON audit_logs(stage);

