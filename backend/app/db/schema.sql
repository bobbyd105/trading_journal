PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    broker TEXT,
    base_currency TEXT NOT NULL DEFAULT 'USD',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS playbooks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS instruments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL UNIQUE,
    name TEXT,
    asset_class TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
    instrument_id INTEGER REFERENCES instruments(id) ON DELETE SET NULL,
    playbook_id INTEGER REFERENCES playbooks(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'closed', 'reviewed', 'archived')),
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('long', 'short')),
    entry_price REAL,
    exit_price REAL,
    quantity REAL,
    pnl REAL,
    risk REAL,
    notes TEXT,
    opened_at TEXT,
    closed_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trade_tags (
    trade_id INTEGER NOT NULL REFERENCES trades(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (trade_id, tag_id)
);

CREATE TABLE IF NOT EXISTS attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attachment_type TEXT NOT NULL CHECK (attachment_type IN ('before_screenshot', 'after_screenshot')),
    file_name TEXT NOT NULL,
    file_path TEXT,
    content_type TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trade_attachments (
    trade_id INTEGER NOT NULL REFERENCES trades(id) ON DELETE CASCADE,
    attachment_id INTEGER NOT NULL REFERENCES attachments(id) ON DELETE CASCADE,
    PRIMARY KEY (trade_id, attachment_id)
);

CREATE TABLE IF NOT EXISTS psychology_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id INTEGER NOT NULL UNIQUE REFERENCES trades(id) ON DELETE CASCADE,
    confidence_score INTEGER NOT NULL CHECK (confidence_score BETWEEN 1 AND 5),
    fear_score INTEGER NOT NULL CHECK (fear_score BETWEEN 1 AND 5),
    fomo_score INTEGER NOT NULL CHECK (fomo_score BETWEEN 1 AND 5),
    discipline_score INTEGER NOT NULL CHECK (discipline_score BETWEEN 1 AND 5),
    clarity_score INTEGER NOT NULL CHECK (clarity_score BETWEEN 1 AND 5),
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trade_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id INTEGER NOT NULL UNIQUE REFERENCES trades(id) ON DELETE CASCADE,
    review_status TEXT NOT NULL DEFAULT 'not_started'
        CHECK (review_status IN ('not_started', 'in_progress', 'complete')),
    summary TEXT,
    setup_quality_score INTEGER CHECK (setup_quality_score BETWEEN 1 AND 5),
    entry_quality_score INTEGER CHECK (entry_quality_score BETWEEN 1 AND 5),
    exit_quality_score INTEGER CHECK (exit_quality_score BETWEEN 1 AND 5),
    risk_management_score INTEGER CHECK (risk_management_score BETWEEN 1 AND 5),
    discipline_score INTEGER CHECK (discipline_score BETWEEN 1 AND 5),
    followed_playbook TEXT NOT NULL DEFAULT 'not_applicable'
        CHECK (followed_playbook IN ('yes', 'partial', 'no', 'not_applicable')),
    what_went_well TEXT,
    what_to_improve TEXT,
    lesson_learned TEXT,
    reviewed_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_instruments_symbol ON instruments(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
CREATE INDEX IF NOT EXISTS idx_trades_instrument_id ON trades(instrument_id);
CREATE INDEX IF NOT EXISTS idx_trades_playbook_id ON trades(playbook_id);
CREATE INDEX IF NOT EXISTS idx_trades_closed_at ON trades(closed_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_psychology_entries_trade_id ON psychology_entries(trade_id);
