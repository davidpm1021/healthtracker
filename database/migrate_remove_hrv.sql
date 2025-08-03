-- Migration script to remove HRV from automated metrics and add manual_entries table
-- Run this on existing databases to update schema

-- Create the new manual_entries table
CREATE TABLE IF NOT EXISTS manual_entries (
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

-- Create index for the new table
CREATE INDEX IF NOT EXISTS idx_manual_entries_date_metric ON manual_entries(date, metric);

-- Migration: Move existing HRV data from raw_points to manual_entries
-- This preserves existing HRV data as manual entries
INSERT OR IGNORE INTO manual_entries (date, metric, value, unit, notes, created_at, updated_at)
SELECT 
    DATE(start_time) as date,
    'hrv' as metric,
    value,
    unit,
    'Migrated from raw_points on ' || datetime('now') as notes,
    created_at,
    datetime('now') as updated_at
FROM raw_points 
WHERE metric = 'hrv';

-- Migration: Move existing HRV data from daily_summaries to manual_entries
-- This preserves existing HRV summaries as manual entries
INSERT OR IGNORE INTO manual_entries (date, metric, value, unit, notes, created_at, updated_at)
SELECT 
    date,
    'hrv' as metric,
    value,
    unit,
    'Migrated from daily_summaries on ' || datetime('now') as notes,
    created_at,
    datetime('now') as updated_at
FROM daily_summaries 
WHERE metric = 'hrv';

-- Remove HRV data from automated tracking tables
DELETE FROM raw_points WHERE metric = 'hrv';
DELETE FROM daily_summaries WHERE metric = 'hrv';

-- Update goals table to allow HRV goals (they can reference manual entries)
-- No action needed - goals table already supports any metric string

-- Clean up: Remove any badges specifically for HRV automated tracking
-- (Keep them if they exist, they might be manually managed)
-- No automatic deletion to preserve user achievements

-- Optional: Add heart_rate support comments (no schema change needed)
-- The existing tables already support heart_rate as a metric type