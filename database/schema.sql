-- Health Tracker MVP Database Schema
-- Simple, clean schema with only essential tables

-- Raw data points from ingestion
CREATE TABLE raw_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT,
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    source TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(metric, start_time, value) ON CONFLICT IGNORE
);

-- Daily summaries computed from raw data
CREATE TABLE daily_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    source TEXT DEFAULT 'computed',
    moving_avg_7d REAL,
    moving_avg_30d REAL,
    trend_slope REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, metric) ON CONFLICT REPLACE
);

-- Manual entries (HRV, mood, notes, etc.)
CREATE TABLE manual_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL,
    text_value TEXT,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Simplified goals table
CREATE TABLE goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric TEXT NOT NULL,
    target_value REAL NOT NULL,
    frequency TEXT NOT NULL, -- 'daily', 'weekly', 'monthly'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Basic badges/achievements
CREATE TABLE badges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    metric TEXT,
    condition_value REAL,
    earned_date TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Sync logging
CREATE TABLE sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    sync_type TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT,
    records_processed INTEGER DEFAULT 0,
    records_added INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    status TEXT NOT NULL,
    error_message TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_raw_points_metric_date ON raw_points(metric, date(start_time));
CREATE INDEX idx_daily_summaries_date_metric ON daily_summaries(date, metric);
CREATE INDEX idx_manual_entries_date_metric ON manual_entries(date, metric);
CREATE INDEX idx_sync_log_source_date ON sync_log(source, date(start_time));