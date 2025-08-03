-- Health Tracker Database Schema
-- Supports the core data model for health metrics tracking

-- Table for optional raw time-series data
CREATE TABLE raw_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric TEXT NOT NULL,           -- steps, sleep, weight, heart_rate
    start_time TEXT NOT NULL,       -- ISO 8601 timestamp
    end_time TEXT,                  -- ISO 8601 timestamp (null for point-in-time metrics)
    value REAL NOT NULL,            -- numeric value
    unit TEXT NOT NULL,             -- steps, minutes, kg, bpm, etc.
    source TEXT NOT NULL,           -- health_connect, manual, etc.
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(metric, start_time, source) ON CONFLICT IGNORE
);

-- Table for per-day aggregates and last-value metrics
CREATE TABLE daily_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,             -- YYYY-MM-DD format
    metric TEXT NOT NULL,           -- steps, sleep, weight, heart_rate
    value REAL NOT NULL,            -- aggregated or last value
    unit TEXT NOT NULL,             -- consistent unit for the metric
    avg_7day REAL,                  -- 7-day moving average
    avg_30day REAL,                 -- 30-day moving average
    trend_slope REAL,               -- simple trend indicator
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(date, metric) ON CONFLICT REPLACE
);

-- Table for user-input data like HRV and other manual entries
CREATE TABLE manual_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,             -- YYYY-MM-DD format
    metric TEXT NOT NULL,           -- hrv, mood, energy, notes, etc.
    value REAL,                     -- numeric value (null for text-only entries)
    unit TEXT,                      -- unit for numeric values (ms, score, etc.)
    text_value TEXT,                -- text value for non-numeric entries
    notes TEXT,                     -- additional notes or context
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(date, metric) ON CONFLICT REPLACE
);

-- Table for targets by metric and period
CREATE TABLE goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric TEXT NOT NULL,           -- steps, sleep, weight, heart_rate, hrv
    period TEXT NOT NULL,           -- daily, weekly
    target_value REAL NOT NULL,     -- goal target
    unit TEXT NOT NULL,             -- matching metric unit
    active BOOLEAN NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Table for earned milestones
CREATE TABLE badges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,             -- badge identifier
    metric TEXT NOT NULL,           -- associated metric
    description TEXT NOT NULL,      -- human readable description
    earned_at TEXT,                 -- when earned (null if not earned)
    criteria TEXT NOT NULL,         -- JSON criteria for earning
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Table for ingestion status, record counts, and windows
CREATE TABLE sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,           -- health_connect, manual, etc.
    sync_type TEXT NOT NULL,        -- full, incremental
    start_time TEXT NOT NULL,       -- sync window start
    end_time TEXT NOT NULL,         -- sync window end
    records_processed INTEGER NOT NULL DEFAULT 0,
    records_added INTEGER NOT NULL DEFAULT 0,
    records_updated INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,           -- success, error, partial
    error_message TEXT,             -- error details if status = error
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Indexes for performance
CREATE INDEX idx_raw_points_metric_time ON raw_points(metric, start_time);
CREATE INDEX idx_daily_summaries_date_metric ON daily_summaries(date, metric);
CREATE INDEX idx_manual_entries_date_metric ON manual_entries(date, metric);
CREATE INDEX idx_goals_metric_active ON goals(metric, active);
CREATE INDEX idx_sync_log_source_time ON sync_log(source, created_at);