-- Goals and Streaks System Database Schema
-- Migration: Add goals, streaks, freeze tokens, and achievements tables

-- Goals table: Core goal definitions and tracking
CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_type TEXT NOT NULL CHECK(goal_type IN ('steps', 'sleep_duration', 'weight_logging', 'hrv_entry', 'heart_rate_zone')),
    target_value REAL NOT NULL CHECK(target_value > 0),
    frequency TEXT NOT NULL DEFAULT 'daily' CHECK(frequency IN ('daily', 'weekly')),
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'paused', 'completed', 'archived')),
    created_date DATE NOT NULL DEFAULT CURRENT_DATE,
    start_date DATE NOT NULL DEFAULT CURRENT_DATE,
    end_date DATE,
    description TEXT,
    
    -- Ensure only one active goal per type and frequency
    UNIQUE(goal_type, frequency, status) ON CONFLICT IGNORE
);

-- Streaks table: Track consecutive goal achievements
CREATE TABLE IF NOT EXISTS streaks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_id INTEGER NOT NULL,
    current_count INTEGER NOT NULL DEFAULT 0 CHECK(current_count >= 0),
    best_count INTEGER NOT NULL DEFAULT 0 CHECK(best_count >= 0),
    last_achieved_date DATE,
    last_updated DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    freeze_tokens_used INTEGER NOT NULL DEFAULT 0 CHECK(freeze_tokens_used >= 0),
    
    FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE,
    
    -- Ensure one streak per goal
    UNIQUE(goal_id)
);

-- Freeze tokens table: Monthly streak preservation tokens
CREATE TABLE IF NOT EXISTS freeze_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    streak_id INTEGER NOT NULL,
    issued_date DATE NOT NULL DEFAULT CURRENT_DATE,
    used_date DATE,
    expires_date DATE NOT NULL,
    is_used BOOLEAN NOT NULL DEFAULT FALSE,
    
    FOREIGN KEY (streak_id) REFERENCES streaks(id) ON DELETE CASCADE
);

-- Goal achievements table: Record of successful goal completions
CREATE TABLE IF NOT EXISTS goal_achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_id INTEGER NOT NULL,
    achieved_date DATE NOT NULL DEFAULT CURRENT_DATE,
    actual_value REAL NOT NULL CHECK(actual_value >= 0),
    notes TEXT,
    
    FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE,
    
    -- Prevent duplicate achievements on same date
    UNIQUE(goal_id, achieved_date)
);

-- Indexes for performance optimization
CREATE INDEX IF NOT EXISTS idx_goals_type_status ON goals(goal_type, status);
CREATE INDEX IF NOT EXISTS idx_goals_start_date ON goals(start_date);
CREATE INDEX IF NOT EXISTS idx_streaks_goal_id ON streaks(goal_id);
CREATE INDEX IF NOT EXISTS idx_streaks_last_achieved ON streaks(last_achieved_date);
CREATE INDEX IF NOT EXISTS idx_freeze_tokens_streak_id ON freeze_tokens(streak_id);
CREATE INDEX IF NOT EXISTS idx_freeze_tokens_issued_date ON freeze_tokens(issued_date);
CREATE INDEX IF NOT EXISTS idx_achievements_goal_date ON goal_achievements(goal_id, achieved_date);
CREATE INDEX IF NOT EXISTS idx_achievements_date ON goal_achievements(achieved_date DESC);

-- Views for common queries
CREATE VIEW IF NOT EXISTS active_goals AS
SELECT 
    g.*,
    s.current_count as streak_count,
    s.best_count as best_streak,
    s.is_active as streak_active,
    s.last_achieved_date as last_streak_date,
    (
        SELECT COUNT(*) 
        FROM freeze_tokens ft 
        WHERE ft.streak_id = s.id 
        AND ft.is_used = FALSE 
        AND ft.expires_date >= CURRENT_DATE
    ) as available_freeze_tokens
FROM goals g
LEFT JOIN streaks s ON g.id = s.goal_id
WHERE g.status = 'active';

-- View for goal progress calculation
CREATE VIEW IF NOT EXISTS goal_progress_summary AS
SELECT 
    g.id,
    g.goal_type,
    g.target_value,
    g.frequency,
    COUNT(ga.id) as total_achievements,
    MAX(ga.achieved_date) as last_achievement_date,
    s.current_count as current_streak,
    s.best_count as best_streak,
    CASE 
        WHEN g.frequency = 'daily' THEN 
            CASE WHEN EXISTS(
                SELECT 1 FROM goal_achievements ga2 
                WHERE ga2.goal_id = g.id 
                AND ga2.achieved_date = CURRENT_DATE
            ) THEN 1 ELSE 0 END
        WHEN g.frequency = 'weekly' THEN
            CASE WHEN COUNT(
                CASE WHEN ga.achieved_date >= date('now', 'weekday 0', '-6 days') 
                THEN 1 END
            ) >= 1 THEN 1 ELSE 0 END
        ELSE 0
    END as is_achieved_current_period
FROM goals g
LEFT JOIN goal_achievements ga ON g.id = ga.goal_id
LEFT JOIN streaks s ON g.id = s.goal_id
WHERE g.status = 'active'
GROUP BY g.id, g.goal_type, g.target_value, g.frequency, s.current_count, s.best_count;

-- Triggers for automatic streak management
CREATE TRIGGER IF NOT EXISTS create_streak_on_goal_insert
AFTER INSERT ON goals
WHEN NEW.status = 'active'
BEGIN
    INSERT INTO streaks (goal_id, current_count, best_count, is_active)
    VALUES (NEW.id, 0, 0, TRUE);
    
    -- Issue first freeze token for the month
    INSERT INTO freeze_tokens (
        streak_id, 
        issued_date, 
        expires_date
    )
    SELECT 
        last_insert_rowid(),
        CURRENT_DATE,
        date(CURRENT_DATE, 'start of month', '+1 month', '-1 day');
END;

-- Trigger to update streak best_count when current_count increases
CREATE TRIGGER IF NOT EXISTS update_best_streak
AFTER UPDATE OF current_count ON streaks
WHEN NEW.current_count > OLD.best_count
BEGIN
    UPDATE streaks 
    SET best_count = NEW.current_count,
        last_updated = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;

-- Trigger to automatically issue monthly freeze tokens
CREATE TRIGGER IF NOT EXISTS issue_monthly_freeze_token
AFTER UPDATE OF last_achieved_date ON streaks
WHEN NEW.last_achieved_date IS NOT NULL
AND (
    OLD.last_achieved_date IS NULL 
    OR strftime('%m', NEW.last_achieved_date) != strftime('%m', OLD.last_achieved_date)
)
BEGIN
    INSERT OR IGNORE INTO freeze_tokens (
        streak_id,
        issued_date,
        expires_date
    )
    VALUES (
        NEW.id,
        NEW.last_achieved_date,
        date(NEW.last_achieved_date, 'start of month', '+1 month', '-1 day')
    );
END;

-- Insert default goals for common metrics (optional starter goals)
INSERT OR IGNORE INTO goals (goal_type, target_value, frequency, description) VALUES
('steps', 10000, 'daily', 'Walk 10,000 steps per day'),
('sleep_duration', 8, 'daily', 'Get 8 hours of sleep per night'),
('weight_logging', 1, 'daily', 'Log weight daily for consistency');

PRAGMA user_version = 3; -- Update schema version