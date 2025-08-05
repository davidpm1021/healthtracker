"""
Database connection and basic operations for Health Tracker.
"""
import sqlite3
import os
from pathlib import Path
from typing import List, Dict, Optional, Any
from contextlib import contextmanager
from datetime import datetime, date
from .models import RawPoint, DailySummary, Goal, Badge, SyncLog, ManualEntry


class DatabaseManager:
    """Manages SQLite database connections and operations."""
    
    def __init__(self, db_path: str = "healthtracker.db"):
        """Initialize database manager with path to database file."""
        self.db_path = db_path
        self.schema_path = Path(__file__).parent.parent / "database" / "schema.sql"
    
    def initialize_database(self) -> None:
        """Create database and tables if they don't exist."""
        if not os.path.exists(self.db_path):
            self._create_database()
        else:
            # Verify tables exist
            self._verify_tables()
        
        # Run goals system migration if needed
        self._run_goals_migration()
    
    def _create_database(self) -> None:
        """Create database from schema file."""
        if not self.schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {self.schema_path}")
        
        with open(self.schema_path, 'r') as f:
            schema_sql = f.read()
        
        with self.get_connection() as conn:
            conn.executescript(schema_sql)
            conn.commit()
    
    def _verify_tables(self) -> None:
        """Verify all required tables exist and run migrations if needed."""
        required_tables = ['raw_points', 'daily_summaries', 'manual_entries', 'goals', 'badges', 'sync_log']
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            missing_tables = set(required_tables) - set(existing_tables)
            if missing_tables:
                raise RuntimeError(f"Missing database tables: {missing_tables}")
    
    def _run_goals_migration(self) -> None:
        """Run goals system migration if needed."""
        migration_path = Path(__file__).parent / "database" / "migrations" / "add_goals_tables.sql"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if new goals tables exist (streaks table is a good indicator)
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='streaks'")
            if not cursor.fetchone():
                # Run the migration
                if migration_path.exists():
                    with open(migration_path, 'r') as f:
                        migration_sql = f.read()
                    
                    cursor.executescript(migration_sql)
                    conn.commit()
                    print("Goals system migration completed successfully")
                else:
                    print(f"Warning: Migration file not found: {migration_path}")
    
    @contextmanager
    def get_connection(self):
        """Get database connection with automatic cleanup."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
        finally:
            conn.close()
    
    # Raw Points Operations
    def insert_raw_point(self, raw_point: RawPoint) -> Optional[int]:
        """Insert a raw data point. Returns the row ID or None if duplicate."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if record already exists
            cursor.execute("""
                SELECT id FROM raw_points 
                WHERE metric = ? AND start_time = ? AND source = ?
            """, (raw_point.metric, raw_point.start_time, raw_point.source))
            
            existing = cursor.fetchone()
            if existing:
                return None  # Duplicate found
            
            # Insert new record
            cursor.execute("""
                INSERT INTO raw_points (metric, start_time, end_time, value, unit, source)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                raw_point.metric,
                raw_point.start_time,
                raw_point.end_time,
                raw_point.value,
                raw_point.unit,
                raw_point.source
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_raw_points(self, metric: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Get raw points for a metric within date range."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM raw_points 
                WHERE metric = ? AND start_time >= ? AND start_time <= ?
                ORDER BY start_time
            """, (metric, start_date, end_date))
            return [dict(row) for row in cursor.fetchall()]
    
    # Daily Summaries Operations
    def upsert_daily_summary(self, summary: DailySummary) -> int:
        """Insert or update a daily summary. Returns row ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            data = summary.to_dict()
            cursor.execute("""
                INSERT OR REPLACE INTO daily_summaries 
                (date, metric, value, unit, avg_7day, avg_30day, trend_slope, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data['date'], data['metric'], data['value'], data['unit'],
                data['avg_7day'], data['avg_30day'], data['trend_slope'], data['updated_at']
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_daily_summaries(self, metric: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Get daily summaries for a metric within date range."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM daily_summaries 
                WHERE metric = ? AND date >= ? AND date <= ?
                ORDER BY date
            """, (metric, start_date, end_date))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_latest_summary(self, metric: str) -> Optional[Dict[str, Any]]:
        """Get the most recent daily summary for a metric."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM daily_summaries 
                WHERE metric = ? 
                ORDER BY date DESC 
                LIMIT 1
            """, (metric,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_daily_summaries_for_metric(self, metric: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Get daily summaries for a specific metric within date range."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM daily_summaries 
                WHERE metric = ? AND date >= ? AND date <= ?
                ORDER BY date
            """, (metric, start_date, end_date))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_daily_summaries_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Get all daily summaries within date range."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM daily_summaries 
                WHERE date >= ? AND date <= ?
                ORDER BY date, metric
            """, (start_date, end_date))
            return [dict(row) for row in cursor.fetchall()]
    
    # Goals Operations
    def insert_goal(self, goal: Goal) -> int:
        """Insert a new goal. Returns row ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            data = goal.to_dict()
            cursor.execute("""
                INSERT INTO goals (metric, period, target_value, unit, active, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                data['metric'], data['period'], data['target_value'],
                data['unit'], data['active'], data['updated_at']
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_active_goals(self, metric: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all active goals, optionally filtered by metric."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if metric:
                cursor.execute("SELECT * FROM goals WHERE active = 1 AND metric = ?", (metric,))
            else:
                cursor.execute("SELECT * FROM goals WHERE active = 1")
            return [dict(row) for row in cursor.fetchall()]
    
    # Badges Operations
    def insert_badge(self, badge: Badge) -> int:
        """Insert a new badge. Returns row ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            data = badge.to_dict()
            cursor.execute("""
                INSERT INTO badges (name, metric, description, criteria, earned_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                data['name'], data['metric'], data['description'],
                data['criteria'], data['earned_at']
            ))
            conn.commit()
            return cursor.lastrowid
    
    def earn_badge(self, badge_id: int, earned_at: str) -> bool:
        """Mark a badge as earned. Returns True if successful."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE badges SET earned_at = ? WHERE id = ? AND earned_at IS NULL
            """, (earned_at, badge_id))
            conn.commit()
            return cursor.rowcount > 0
    
    # Manual Entries Operations
    def insert_manual_entry(self, entry: ManualEntry) -> int:
        """Insert or update a manual entry. Returns row ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            data = entry.to_dict()
            cursor.execute("""
                INSERT OR REPLACE INTO manual_entries 
                (date, metric, value, unit, text_value, notes, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                data['date'], data['metric'], data['value'], data['unit'],
                data['text_value'], data['notes'], data['updated_at']
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_manual_entry(self, date: str, metric: str) -> Optional[Dict[str, Any]]:
        """Get a specific manual entry by date and metric."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM manual_entries 
                WHERE date = ? AND metric = ?
            """, (date, metric))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_manual_entries(self, metric: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Get manual entries for a metric within date range."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM manual_entries 
                WHERE metric = ? AND date >= ? AND date <= ?
                ORDER BY date DESC
            """, (metric, start_date, end_date))
            return [dict(row) for row in cursor.fetchall()]
    
    def delete_manual_entry(self, date: str, metric: str) -> bool:
        """Delete a manual entry. Returns True if successful."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM manual_entries WHERE date = ? AND metric = ?
            """, (date, metric))
            conn.commit()
            return cursor.rowcount > 0
    
    # Sync Log Operations
    def insert_sync_log(self, sync_log: SyncLog) -> int:
        """Insert a sync log entry. Returns row ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            data = sync_log.to_dict()
            cursor.execute("""
                INSERT INTO sync_log 
                (source, sync_type, start_time, end_time, records_processed, 
                 records_added, records_updated, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data['source'], data['sync_type'], data['start_time'], data['end_time'],
                data['records_processed'], data['records_added'], data['records_updated'],
                data['status'], data['error_message']
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_recent_sync_logs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent sync log entries."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM sync_log 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    # Utility Operations
    def test_connection(self) -> bool:
        """Test database connection and basic functionality."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                return cursor.fetchone()[0] == 1
        except Exception:
            return False
    
    def get_table_counts(self) -> Dict[str, int]:
        """Get row counts for all tables."""
        counts = {}
        tables = ['raw_points', 'daily_summaries', 'goals', 'badges', 'sync_log']
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cursor.fetchone()[0]
        
        return counts


    # ====== GOALS AND STREAKS METHODS ======
    
    def create_goal(self, goal: NewGoal) -> int:
        """Create a new goal and return its ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO goals (goal_type, target_value, frequency, status, start_date, end_date, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                goal.goal_type,
                goal.target_value,
                goal.frequency,
                goal.status,
                goal.start_date.isoformat() if goal.start_date else None,
                goal.end_date.isoformat() if goal.end_date else None,
                goal.description
            ))
            return cursor.lastrowid
    
    def get_goal(self, goal_id: int) -> Optional[NewGoal]:
        """Get a goal by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM goals WHERE id = ?", (goal_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_goal(row)
        return None
    
    def get_goals(self, status: Optional[str] = None, goal_type: Optional[str] = None) -> List[NewGoal]:
        """Get goals with optional filtering."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM goals WHERE 1=1"
            params = []
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            if goal_type:
                query += " AND goal_type = ?"
                params.append(goal_type)
                
            query += " ORDER BY created_date DESC"
            
            cursor.execute(query, params)
            return [self._row_to_goal(row) for row in cursor.fetchall()]
    
    def update_goal(self, goal: NewGoal) -> bool:
        """Update an existing goal."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE goals 
                SET goal_type = ?, target_value = ?, frequency = ?, status = ?, 
                    start_date = ?, end_date = ?, description = ?
                WHERE id = ?
            """, (
                goal.goal_type,
                goal.target_value,
                goal.frequency,
                goal.status,
                goal.start_date.isoformat() if goal.start_date else None,
                goal.end_date.isoformat() if goal.end_date else None,
                goal.description,
                goal.id
            ))
            return cursor.rowcount > 0
    
    def delete_goal(self, goal_id: int) -> bool:
        """Delete a goal and its associated data."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
            return cursor.rowcount > 0
    
    def get_streak(self, goal_id: int) -> Optional[Streak]:
        """Get streak for a goal."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM streaks WHERE goal_id = ?", (goal_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_streak(row)
        return None
    
    def update_streak(self, streak: Streak) -> bool:
        """Update a streak record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE streaks 
                SET current_count = ?, best_count = ?, last_achieved_date = ?, 
                    is_active = ?, freeze_tokens_used = ?, last_updated = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                streak.current_count,
                streak.best_count,
                streak.last_achieved_date.isoformat() if streak.last_achieved_date else None,
                streak.is_active,
                streak.freeze_tokens_used,
                streak.id
            ))
            return cursor.rowcount > 0
    
    def record_goal_achievement(self, achievement: GoalAchievement) -> int:
        """Record a goal achievement."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO goal_achievements 
                (goal_id, achieved_date, actual_value, notes)
                VALUES (?, ?, ?, ?)
            """, (
                achievement.goal_id,
                achievement.achieved_date.isoformat() if achievement.achieved_date else None,
                achievement.actual_value,
                achievement.notes
            ))
            return cursor.lastrowid
    
    def get_available_freeze_tokens(self, streak_id: int) -> List[FreezeToken]:
        """Get available freeze tokens for a streak."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM freeze_tokens 
                WHERE streak_id = ? AND is_used = FALSE AND expires_date >= CURRENT_DATE
                ORDER BY issued_date
            """, (streak_id,))
            
            return [self._row_to_freeze_token(row) for row in cursor.fetchall()]
    
    def use_freeze_token(self, token_id: int, used_date: date) -> bool:
        """Mark a freeze token as used."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE freeze_tokens 
                SET is_used = TRUE, used_date = ?
                WHERE id = ? AND is_used = FALSE
            """, (used_date.isoformat(), token_id))
            return cursor.rowcount > 0
    
    def _row_to_goal(self, row) -> NewGoal:
        """Convert database row to Goal object."""
        return NewGoal(
            id=row[0],
            goal_type=row[1],
            target_value=row[2],  
            frequency=row[3],
            status=row[4],
            created_date=datetime.fromisoformat(row[5]).date() if row[5] else None,
            start_date=datetime.fromisoformat(row[6]).date() if row[6] else None,
            end_date=datetime.fromisoformat(row[7]).date() if row[7] else None,
            description=row[8]
        )
    
    def _row_to_streak(self, row) -> Streak:
        """Convert database row to Streak object."""
        return Streak(
            id=row[0],
            goal_id=row[1],
            current_count=row[2],
            best_count=row[3],
            last_achieved_date=datetime.fromisoformat(row[4]).date() if row[4] else None,
            last_updated=datetime.fromisoformat(row[5]) if row[5] else None,
            is_active=bool(row[6]),
            freeze_tokens_used=row[7]
        )
    
    def _row_to_freeze_token(self, row) -> FreezeToken:
        """Convert database row to FreezeToken object."""
        return FreezeToken(
            id=row[0],
            streak_id=row[1],
            issued_date=datetime.fromisoformat(row[2]).date() if row[2] else None,
            used_date=datetime.fromisoformat(row[3]).date() if row[3] else None,
            expires_date=datetime.fromisoformat(row[4]).date() if row[4] else None,
            is_used=bool(row[5])
        )


def get_db_connection():
    """Get a simple database connection for scripts."""
    return sqlite3.connect("healthtracker.db")